from setuptools import setup
        
# these lines allow the version to be specified in Makefile.private
import os
version = os.environ.get("MODULEVER", "0.0")
        
setup(
#    install_requires = ['cothread'], # require statements go here
    install_requires = [ 'dls_pmaclib==1.9.1' ],
    name = 'dls_pmacanalyse',
    version = version,
    description = 'Module',
    author = 'fgz73762',
    author_email = 'fgz73762@rl.ac.uk',    
    packages = ['dls_pmacanalyse'],
    entry_points = {'console_scripts': [
        'dls-pmac-analyse.py = dls_pmacanalyse.dls_pmacanalyse:main']},
    package_data = {'': ['*.pmc']},
    zip_safe = False
    )        
