# coding=utf-8
import os
from distutils.core import setup
from setuptools import find_packages
import dju_privateurl


setup(
    name='dju_privateurl',
    version=dju_privateurl.__version__,
    description='Django Utils: Private URL',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
    license='MIT',
    author='Igor Melnyk',
    author_email='liminspace@gmail.com',
    url='https://github.com/liminspace/dju-privateurl',
    packages=find_packages(),  # exclude=('tests.*', 'tests', 'example')
    include_package_data=True,
    zip_safe=False,  # тому, що вкладаємо статику
    install_requires=[
        'django<1.10',
        'simplejson',
        'dju-common',
    ],
)
