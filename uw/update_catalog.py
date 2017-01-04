#!/usr/bin/env python2
# -*- coding: utf8 -*-
#
#  Copyright (c) 2015, 2016 unfoldingWord
#  http://creativecommons.org/licenses/MIT/
#  See LICENSE file for details.
#
#  Contributors:
#  Jesse Griffin <jesse@distantshores.org>
#  Phil Hopper <phillip_hopper@wycliffeassociates.org>


"""
Updates the catalog for the translationStudio and unfoldingWord v2 APIs.
"""
from __future__ import unicode_literals
import argparse
import os
import json
import time
import datetime as dt
from copy import deepcopy
import sys
from general_tools.file_utils import write_file, load_json_object
from general_tools.url_utils import get_url


PY3 = sys.version_info[0] == 3
if PY3:
    unicode_type = str,
else:
    unicode_type = unicode,


bible_stat = '/var/www/vhosts/api.unfoldingword.org/httpdocs/{0}/txt/1/{1}-{2}/status.json'
lang_url = 'http://td.unfoldingword.org/exports/langnames.json'


class CatalogUpdater(object):

    project_dirs = ['obs']
    bible_dirs = [
        '1ch', '1co', '1jn', '1ki', '1pe', '1sa', '1th', '1ti', '2ch',
        '2co', '2jn', '2ki', '2pe', '2sa', '2th', '2ti', '3jn', 'act',
        'amo', 'col', 'dan', 'deu', 'ecc', 'eph', 'est', 'exo', 'ezk',
        'ezr', 'gal', 'gen', 'hab', 'hag', 'heb', 'hos', 'jas', 'jdg',
        'jer', 'jhn', 'job', 'jol', 'jon', 'jos', 'jud', 'lam', 'lev',
        'luk', 'mal', 'mat', 'mic', 'mrk', 'nam', 'neh', 'num', 'oba',
        'phm', 'php', 'pro', 'rev', 'rom', 'rut', 'sng', 'tit', 'zec',
        'zep', 'isa', 'psa'
    ]

    usfm_api = 'https://api.unfoldingword.org/{0}/txt/1/{1}-{2}/{3}'

    api_path = '/var/www/vhosts/api.unfoldingword.org/httpdocs'
    obs_v1_local = api_path+'/obs/txt/1'
    obs_v1_api = 'https://api.unfoldingword.org/obs/txt/1'
    obs_v1_url = '{0}/obs-catalog.json'.format(obs_v1_api)
    obs_v2_local = api_path+'/ts/txt/2'
    obs_v2_api = 'https://api.unfoldingword.org/ts/txt/2'
    obs_audio_url = 'https://api.unfoldingword.org/obs/mp3/1/en/en-obs-v4/status.json'

    uw_v2_local = api_path+'/uw/txt/2/catalog.json'
    ts_obs_langs_url = 'https://api.unfoldingword.org/ts/txt/2/obs/languages.json'

    def __init__(self, domain, slug, lang):
        # format of bible_slug ('domain', 'slug', 'lang-code')
        if domain and slug and lang:
            self.bible_slugs = [(domain, slug, lang), ]
        else:
            self.bible_slugs = CatalogUpdater.get_bibles(self.api_path)

    @staticmethod
    def get_bibles(api_path):

        dir_base = api_path+'/{0}/txt/1/'
        slugs = []

        # ulb = Unlocked Literal Bible
        # udb = Unlocked Dynamic Bible
        # pdb = Public Domain Bibles
        for domain in ['ulb', 'udb', 'pdb']:
            dir_name = dir_base.format(domain)
            if not os.path.isdir(dir_name):
                continue

            for sub_dir in os.listdir(dir_name):
                parts = sub_dir.split('-', 1)

                if len(parts) == 2:
                    # ('domain', 'slug', 'lang-code')
                    slugs.append((domain, parts[0], parts[1]))

        return slugs

    @staticmethod
    def obs(obs_v1_cat):

        langs_cat = []
        # Write OBS catalog for each language
        for e in obs_v1_cat:
            file_name = '{0}/{1}/obs-{1}-front-matter.json'.format(CatalogUpdater.obs_v1_local, e['language'])
            if not os.path.isfile(file_name):
                continue

            front_json = load_json_object(file_name)
            lang_entry = {'language': {'slug': e['language'],
                                       'name': e['string'],
                                       'direction': e['direction'],
                                       'date_modified': e['date_modified']
                                       },
                          'project': {'name': front_json['name'],
                                      'desc': front_json['tagline'],
                                      'meta': []
                                      }
                          }
            lang = e['language']
            del e['language']
            del e['string']
            del e['direction']
            e['slug'] = 'obs'
            e['name'] = 'Open Bible Stories'
            e['source'] = CatalogUpdater.add_date('{0}/{1}/obs-{1}.json'.format(CatalogUpdater.obs_v1_api, lang))

            if lang == 'en':
                e['terms'] = CatalogUpdater.add_date('{0}/{1}/kt-{1}.json'.format(CatalogUpdater.obs_v1_api, lang))
                e['notes'] = CatalogUpdater.add_date('{0}/{1}/tN-{1}.json'.format(CatalogUpdater.obs_v1_api, lang))
                e['tw_cat'] = CatalogUpdater.add_date('{0}/{1}/tw_cat-{1}.json'.format(CatalogUpdater.obs_v1_api, lang))
                e['checking_questions'] = CatalogUpdater.add_date('{0}/{1}/CQ-{1}.json'.format(
                    CatalogUpdater.obs_v1_api, lang))
            else:
                e['terms'] = ''
                e['notes'] = ''
                e['tw_cat'] = ''
                e['checking_questions'] = ''

            e['date_modified'] = CatalogUpdater.most_recent(e)
            outfile = '{0}/obs/{1}/resources.json'.format(CatalogUpdater.obs_v2_local, lang)

            write_file(outfile, [e])

            lang_entry['res_catalog'] = '{0}/obs/{1}/resources.json?date_modified={2}'.format(CatalogUpdater.obs_v2_api,
                                                                                              lang, e['date_modified'])
            langs_cat.append(lang_entry)

        # Write global OBS catalog
        outfile = '{0}/obs/languages.json'.format(CatalogUpdater.obs_v2_local)
        write_file(outfile, langs_cat)

    @staticmethod
    def add_date(url):
        """
        Adds 'date_modified=datestamp' to URL based on value found in the url.'
        :param url:
        """
        src_str = get_url(url, True)
        if not src_str:
            return url
        src = json.loads(src_str)
        if type(src) == dict:
            date_mod = src['date_modified']
        else:
            date_mod = [x['date_modified'] for x in src if 'date_modified' in x][0]
        return '{0}?date_modified={1}'.format(url, date_mod)

    @staticmethod
    def most_recent(cat):
        """
        Returns date_modified string that matches the most recent sub catalog.
        :param cat:
        """
        try:
            date_mod = cat['date_modified']
        except KeyError:
            date_mod = cat['language']['date_modified']
        for k in cat.keys():
            if 'date_modified' not in cat[k]:
                continue

            if not type(cat[k]) == unicode_type:
                continue

            item_date_mod = cat[k].split('date_modified=')[1]
            if int(item_date_mod) > int(date_mod):
                date_mod = item_date_mod

        return date_mod

    def bible(self, lang_names, bible_status, bible_bks, langs):

        bks_set = set(bible_bks)
        for bk in bks_set:
            for lang_iter in langs:
                resources_cat = []
                for domain, slug, lang in self.bible_slugs:

                    if (domain, slug, lang) not in bible_status:
                        continue

                    this_status = bible_status[(domain, slug, lang)]
                    if bk not in this_status['books_published'].keys():
                        continue

                    if lang != lang_iter:
                        continue

                    lang = this_status['lang']
                    slug_cat = deepcopy(this_status)

                    # add link to source
                    if os.path.isfile('{0}/{1}/{2}/{3}/source.json'.format(self.obs_v2_local, bk, lang, slug)):
                        slug_cat['source'] = CatalogUpdater.add_date('{0}/{1}/{2}/{3}/source.json'
                                                                     .format(self.obs_v2_api, bk, lang, slug))
                    else:
                        slug_cat['source'] = ''

                    source_date = ''
                    if '?' in slug_cat['source']:
                        source_date = slug_cat['source'].split('?')[1]
                    usfm_name = '{0}-{1}.usfm'.format(this_status['books_published'][bk]['sort'], bk.upper())

                    # add link to usfm
                    slug_cat['usfm'] = self.usfm_api.format(domain, slug, lang, usfm_name) + '?' + source_date

                    # add link to terms
                    if slug == 'ulb' and os.path.isfile('{0}/bible/{1}/terms.json'.format(self.obs_v2_local, lang)):
                        slug_cat['terms'] = CatalogUpdater.add_date('{0}/bible/{1}/terms.json'.format(self.obs_v2_api,
                                                                                                      lang))
                    else:
                        slug_cat['terms'] = ''

                    # add link to notes
                    if slug == 'ulb' and os.path.isfile('{0}/{1}/{2}/notes.json'.format(self.obs_v2_local, bk, lang)):
                        slug_cat['notes'] = CatalogUpdater.add_date('{0}/{1}/{2}/notes.json'.format(self.obs_v2_api, bk,
                                                                                                    lang))
                    else:
                        slug_cat['notes'] = ''

                    # add link to tW
                    if slug == 'ulb' and os.path.isfile('{0}/{1}/{2}/tw_cat.json'.format(self.obs_v2_local, bk, lang)):
                        slug_cat['tw_cat'] = CatalogUpdater.add_date('{0}/{1}/{2}/tw_cat.json'.format(self.obs_v2_api,
                                                                                                      bk, lang))
                    else:
                        slug_cat['tw_cat'] = ''

                    # add link to tQ
                    if slug == 'ulb' and os.path.isfile('{0}/{1}/{2}/questions.json'.format(self.obs_v2_local, bk, lang)):
                        slug_cat['checking_questions'] = CatalogUpdater.add_date('{0}/{1}/{2}/questions.json'
                                                                                 .format(self.obs_v2_api, bk, lang))
                    else:
                        slug_cat['checking_questions'] = ''

                    del slug_cat['books_published']
                    del slug_cat['lang']
                    slug_cat['date_modified'] = CatalogUpdater.most_recent(slug_cat)

                    # 2016-05-21, Phil Hopper: The slug value from status.json might have the language code appended
                    slug_cat['slug'] = slug

                    resources_cat.append(slug_cat)

                # only write the file if there is something to publish
                if resources_cat:
                    outfile = '{0}/{1}/{2}/resources.json'.format(self.obs_v2_local, bk, lang_iter)
                    write_file(outfile, resources_cat)

        for bk in bks_set:
            languages_cat = []
            langs_processed = []
            for lang_iter in langs:
                for domain, slug, lang in self.bible_slugs:
                    if lang in langs_processed:
                        continue
                    if lang != lang_iter:
                        continue
                    if (domain, slug, lang_iter) not in bible_status:
                        continue

                    this_status = bible_status[(domain, slug, lang_iter)]

                    if bk not in this_status['books_published'].keys():
                        continue
                    lang_info = CatalogUpdater.get_lang_info(lang_iter, lang_names)
                    res_info = {'project': this_status['books_published'][bk],
                                'language': {'slug': lang_info['lc'],
                                             'name': lang_info['ln'],
                                             'direction': lang_info['ld'],
                                             'date_modified': this_status['date_modified'],
                                             },
                                'res_catalog': CatalogUpdater.add_date(
                                    '{0}/{1}/{2}/resources.json'.format(
                                        self.obs_v2_api, bk, lang_info['lc']))
                                }
                    res_info['language']['date_modified'] = CatalogUpdater.most_recent(res_info)
                    languages_cat.append(res_info)
                    langs_processed.append(lang)
            outfile = '{0}/{1}/languages.json'.format(self.obs_v2_local, bk)
            write_file(outfile, languages_cat)

    @staticmethod
    def get_lang_info(lc, lang_names):
        lang_info = [x for x in lang_names if x['lc'] == lc][0]
        return lang_info

    @staticmethod
    def ts_cat():

        ts_categories = []
        for x in CatalogUpdater.bible_dirs:
            CatalogUpdater.project_dirs.append(x)
        for p in CatalogUpdater.project_dirs:
            file_name = '{0}/{1}/languages.json'.format(CatalogUpdater.obs_v2_local, p)
            proj_cat = load_json_object(file_name)
            if not proj_cat:
                continue

            proj_url = '{0}/{1}/languages.json'.format(CatalogUpdater.obs_v2_api, p)
            dates = set([x['language']['date_modified'] for x in proj_cat])
            dates_list = list(dates)
            dates_list.sort(reverse=True)
            sort = '01'
            if p in CatalogUpdater.bible_dirs:
                sort = [x['project']['sort'] for x in proj_cat if 'project' in x][0]
            meta = []
            if proj_cat[0]['project']['meta']:
                if 'Bible: OT' in proj_cat[0]['project']['meta']:
                    meta += ['bible-ot']
                if 'Bible: NT' in proj_cat[0]['project']['meta']:
                    meta += ['bible-nt']
            ts_categories.append({'slug': p,
                                  'date_modified': dates_list[0],
                                  'lang_catalog': '{0}?date_modified={1}'.format(
                                      proj_url, dates_list[0]),
                                  'sort': sort,
                                  'meta': meta
                                  })
        # Write global catalog
        outfile = '{0}/catalog.json'.format(CatalogUpdater.obs_v2_local)
        write_file(outfile, ts_categories)

    def uw_cat(self, obs_v1_cat, bible_status):

        # Create Bible section
        uw_bible = {'title': 'Bible',
                    'slug': 'bible',
                    'langs': []
                    }
        lang_cat = {}
        for domain, slug, lang in self.bible_slugs:

            if (domain, slug, lang) not in bible_status:
                continue

            this_status = bible_status[(domain, slug, lang)]
            date_mod = CatalogUpdater.get_seconds(this_status['date_modified'])
            if lang not in lang_cat:
                lang_cat[lang] = {'lc': lang,
                                  'mod': date_mod,
                                  'vers': []
                                  }
            ver = {'name': this_status['name'],
                   'slug': this_status['slug'],
                   'mod': date_mod,
                   'status': this_status['status'],
                   'toc': []
                   }
            bk_pub = this_status['books_published']

            for x in bk_pub:
                usfm_name = '{0}-{1}.usfm'.format(bk_pub[x]['sort'], x.upper())
                source = self.usfm_api.format(domain, slug, lang, usfm_name)
                source_sig = source.replace('.usfm', '.sig')
                pdf = source.replace('.usfm', '.pdf')
                ver['toc'].append({'title': bk_pub[x]['name'],
                                   'slug': x,
                                   'mod': date_mod,
                                   'desc': bk_pub[x]['desc'],
                                   'sort': bk_pub[x]['sort'],
                                   'src': source,
                                   'src_sig': source_sig,
                                   'pdf': pdf
                                   })
            ver['toc'].sort(key=lambda s: s['sort'])
            for x in ver['toc']:
                del x['sort']
            lang_cat[lang]['vers'].append(ver)
        uw_bible['langs'] = [lang_cat[k] for k in lang_cat]
        uw_bible['langs'].sort(key=lambda c: c['lc'])

        # Create OBS section
        uw_obs = {'title': 'Open Bible Stories',
                  'slug': 'obs',
                  'langs': []
                  }
        ts_obs_langs_str = get_url(self.ts_obs_langs_url, True)
        ts_obs_langs = json.loads(ts_obs_langs_str)
        for e in obs_v1_cat:
            date_mod = CatalogUpdater.get_seconds(e['date_modified'])
            desc = ''
            name = ''
            for x in ts_obs_langs:
                if x['language']['slug'] == e['language']:
                    desc = x['project']['desc']
                    name = x['project']['name']
            slug = 'obs-{0}'.format(e['language'])
            source = '{0}/{1}/{2}.json'.format(self.obs_v1_api, e['language'], slug)
            source_sig = source.replace('.json', '.sig')
            media = CatalogUpdater.get_media(e['language'])
            entry = {'lc': e['language'],
                     'mod': date_mod,
                     'vers': [{'name': name,
                               'slug': slug,
                               'mod': date_mod,
                               'status': e['status'],
                               'toc': [{'title': '',
                                        'slug': '',
                                        'media': media,
                                        'mod': date_mod,
                                        'desc': desc,
                                        'src': source,
                                        'src_sig': source_sig
                                        }]
                               }]
                     }
            uw_obs['langs'].append(entry)
        uw_obs['langs'].sort(key=lambda c: c['lc'])

        # Write combined uW catalog
        # noinspection PyTypeChecker
        mods = [int(x['mod']) for x in uw_bible['langs']]
        # noinspection PyTypeChecker
        mods += [int(x['mod']) for x in uw_obs['langs']]
        mods.sort(reverse=True)
        uw_category = {'cat': [uw_bible, uw_obs], 'mod': mods[0]}
        write_file(self.uw_v2_local, uw_category)

    @staticmethod
    def get_media(lang):

        media = {'audio': {},
                 'video': {},
                 }
        if lang == 'en':
            obs_audio = get_url(CatalogUpdater.obs_audio_url, True)
            media['audio'] = json.loads(obs_audio)
            del media['audio']['slug']
        return media

    @staticmethod
    def get_seconds(date_str):
        today = ''.join(str(dt.date.today()).rsplit('-')[0:3])
        date_secs = time.mktime(dt.datetime.strptime(date_str,
                                                     "%Y%m%d").timetuple())
        if date_str == today:
            date_secs = time.mktime(dt.datetime.now().timetuple())
        return str(int(date_secs))


def update_catalog(domain=None, slug=None, lang=None):
    global bible_stat, lang_url

    updater = CatalogUpdater(domain, slug, lang)

    # OBS
    obs_v1 = get_url(CatalogUpdater.obs_v1_url, True)
    obs_v1_catalog = json.loads(obs_v1)
    CatalogUpdater.obs(deepcopy(obs_v1_catalog))

    # Bible
    lang_names = json.loads(get_url(lang_url, True))
    bible_status = {}
    bible_bks = []
    langs = set([x[2] for x in updater.bible_slugs])
    for domain, slug, lang in updater.bible_slugs:
        file_name = bible_stat.format(domain, slug, lang)
        if not os.path.isfile(file_name):
            continue

        bible_status[(domain, slug, lang)] = load_json_object(file_name)
        bible_bks += bible_status[(domain, slug, lang)]['books_published'].keys()

    updater.bible(lang_names, bible_status, bible_bks, langs)

    # Global
    CatalogUpdater.ts_cat()
    updater.uw_cat(obs_v1_catalog, bible_status)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-d', '--domain', dest='domain', choices=['udb', 'ulb', 'pdb'], default=False,
                        required=False, help='ulb, udb or pdb')
    parser.add_argument('-l', '--lang', dest="lang", default=False,
                        required=False, help="Language code of resource.")
    parser.add_argument('-s', '--slug', dest="slug", default=False,
                        required=False, help="Slug of resource name (e.g. ulb).")

    args = parser.parse_args(sys.argv[1:])

    update_catalog(args.domain, args.slug, args.lang)
