from __future__ import print_function, unicode_literals
import json
import os
import tempfile
from copy import deepcopy
from unittest import TestCase
from general_tools.file_utils import load_json_object, remove_tree, copy_tree
from general_tools.url_utils import get_url
from uw.update_catalog import CatalogUpdater


class TestUpdateCatalog(TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix='updateCatalogTest_')

        # copy resources to the temp directory
        resources_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'resources', 'api')
        copy_tree(resources_dir, self.temp_dir)

    def tearDown(self):
        remove_tree(self.temp_dir, ignore_errors=True)

    def test_catalog(self):
        obs_v1_local = '{0}/obs/txt/1'.format(self.temp_dir)
        obs_v1_url = 'file://{0}/obs-catalog.json'.format(obs_v1_local)
        lang_url = 'file://{0}/td/langnames.json'.format(self.temp_dir)
        bible_stat = self.temp_dir + '/{0}/txt/1/{1}-{2}/status.json'
        uw_v2_local = '{0}/uw/txt/2/catalog.json'.format(self.temp_dir)
        ts_obs_langs_url = 'file://{0}/ts/txt/2/obs/languages.json'.format(self.temp_dir)

        # set up mocking
        CatalogUpdater.api_path = self.temp_dir
        CatalogUpdater.obs_v1_local = obs_v1_local
        CatalogUpdater.obs_v2_local = '{0}/ts/txt/2'.format(self.temp_dir)
        CatalogUpdater.uw_v2_local = uw_v2_local
        CatalogUpdater.ts_obs_langs_url = ts_obs_langs_url

        updater = CatalogUpdater(None, None, None)

        # OBS
        obs_v1 = get_url(obs_v1_url, True)
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

        # check door43.org/issues/376: remove tW, tN and tQ links from non-English OBS
        en_obs = load_json_object('{0}/ts/txt/2/obs/en/resources.json'.format(self.temp_dir))[0]
        self.assertNotEquals(en_obs['checking_questions'], '')
        self.assertNotEquals(en_obs['notes'], '')
        self.assertNotEquals(en_obs['terms'], '')
        self.assertNotEquals(en_obs['tw_cat'], '')

        fr_obs = load_json_object('{0}/ts/txt/2/obs/fr/resources.json'.format(self.temp_dir))[0]
        self.assertEquals(fr_obs['checking_questions'], '')
        self.assertEquals(fr_obs['notes'], '')
        self.assertEquals(fr_obs['terms'], '')
        self.assertEquals(fr_obs['tw_cat'], '')

        # check door43.org/issues/378: remove tW, tN and tQ links from non-ULB resources
        en_gen = load_json_object('{0}/ts/txt/2/gen/en/resources.json'.format(self.temp_dir))
        for resource in en_gen:
            if resource['slug'] != 'ulb':
                self.assertEquals(resource['checking_questions'], '')
                self.assertEquals(resource['notes'], '')
                self.assertEquals(resource['terms'], '')
                self.assertEquals(resource['tw_cat'], '')
