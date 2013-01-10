# Specify defaults for testing
PREFIX = $(PWD)/prefix
PYTHON = dls-python
MODULEVER = 0.0

# Override with any release info
-include Makefile.private

# This is run when we type make
# It can depend on other targets e.g. the .py files produced by pyuic4 
dist: setup.py $(wildcard dls_pmacanalyse/*.py) $(wildcard dls_pmacanalyse/*.pmc)
	MODULEVER=$(MODULEVER) $(PYTHON) setup.py bdist_egg
	touch dist
	$(MAKE) -C documentation 

# Clean the module
clean:
	$(PYTHON) setup.py clean
	-rm -rf build dist *egg-info installed.files
	-find -name '*.pyc' -exec rm {} \;
	$(MAKE) -C documentation clean

# Install the built egg and keep track of what was installed
install: dist
	$(PYTHON) setup.py easy_install -m \
		--record=installed.files \
		--prefix=$(PREFIX) dist/*.egg        
