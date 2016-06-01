import os
from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(f_name):
    return open(os.path.join(os.path.dirname(__file__), f_name)).read()


setup(
    name="uw_tools",
    version="0.0.3",
    author="unfoldingWord",
    author_email="unfoldingword.org",
    description="A collection of useful scripts",
    license="MIT",
    keywords="unfoldingWord python tools",
    url="https://github.org/unfoldingWord-dev/uw_tools",
    packages=['general_tools', 'uw'],
    long_description=read('README.md'),
    classifiers=[],
    requires=['pygithub', ]
)
