from setuptools import setup, find_packages
import codecs
import os
import importlib

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "readme.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

VERSION = '0.0.11'
DESCRIPTION = 'Automated python exercise evaluations with AI.'
LONG_DESCRIPTION = 'PyEvalAI offers automated python exercise evaluations with LLMs and unit tests.'

install_requires = [
	'numpy', 
	'tornado', 
	'cloudpickle', 
	'ipywidgets', 
	'natsort', 
	'jinja2', 
	'markdown2>=2.4.0'
	]

# Setting up
setup(
    name="pyevalai",
    version=VERSION,
    author="Nils Wandel",
    author_email="<wandeln@cs.uni-bonn.de>",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    project_urls={
        'Source Code': 'https://github.com/wandeln/pyevalai',
    },
    packages=find_packages(),
    install_requires=install_requires,
    python_requires=">=3.8",
    keywords=['jupyter', 'exercise', 'evaluation', 'AI', 'LLM'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ]
) 
