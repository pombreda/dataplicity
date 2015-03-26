#!/usr/bin/env python

from setuptools import setup, find_packages
from dataplicity import __version__ as VERSION

classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Programming Language :: Python',
]

with open('README.txt') as f:
    long_desc = f.read()

setup(name='dataplicity',
      version=VERSION,
      description="Platform for connected devices",
      long_description=long_desc,
      author='WildFoundry',
      author_email='support@dataplicity.com',
      url='http://www.dataplicity.com',
      platforms=['any'],
      packages=find_packages(),
      classifiers=classifiers,

      entry_points={
          "console_scripts": [
              'dataplicity = dataplicity.app.app:run',
              'dataplicity-srv = dataplicity.srv.app:run'
          ]
      },

      install_requires=['websocket-client',
                        'python-daemon==2.0.1',
                        'fs>=0.5.0',
                        'setuptools',
                        'enum34',
                        'docutils',
                        'lockfile'
                        ]
      )
