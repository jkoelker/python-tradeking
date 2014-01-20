# -*- coding: utf-8 -*-

from setuptools import setup

version = '0.1'

setup(name='tradeking',
      version=version,
      description="Python wrapper around Tradeking's API",
      long_description=open('README.rst').read(),
      keywords='',
      author='Jason Kölker',
      author_email='jason@koelker.net',
      url='https://github.com/jkoelker/python-tradeking',
      license='MIT',
      packages=['tradeking'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'requests',
          'requests_oauthlib',
      ],
      )
