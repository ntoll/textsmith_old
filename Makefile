XARGS := xargs -0 $(shell test $$(uname) = Linux && echo -r)
GREP_T_FLAG := $(shell test $$(uname) = Linux && echo -T)
export PYFLAKES_BUILTINS=_

all:
	@echo "\nThere is no default Makefile target right now. Try:\n"
	@echo "make run - run the local development version of TextSmith."
	@echo "make clean - reset the project and remove auto-generated assets."
	@echo "make pyflakes - run the PyFlakes code checker."
	@echo "make pycodestyle - run the PEP8 style checker."
	@echo "make test - run the test suite."
	@echo "make coverage - view a report on test coverage."
	@echo "make check - run all the checkers and tests."

clean:
	find . \( -name '*.py[co]' -o -name dropin.cache \) -delete
	find . \( -name '*.bak' -o -name dropin.cache \) -delete
	find . \( -name '*.tgz' -o -name dropin.cache \) -delete
	find . | grep -E "(__pycache__)" | xargs rm -rf

run: clean
ifeq ($(VIRTUAL_ENV),)
    @echo "\n\nCannot run Mu. Your Python virtualenv is not activated."
else
	@echo "\nRunning on http://0.0.0.0:8000/ over http (CTRL + C to quit).\n"
	hypercorn textsmith.app:app	
endif

pyflakes:
	find . \( -name _build -o -name var -o -path ./docs -o -path \) -type d -prune -o -name '*.py' -print0 | $(XARGS) pyflakes

pycodestyle:
	find . \( -name _build -o -name var \) -type d -prune -o -name '*.py' -print0 | $(XARGS) -n 1 pycodestyle --repeat --ignore=E731,E402,W504

test: clean
	pytest --random-order

coverage: clean
	pytest --random-order --cov-config .coveragerc --cov-report term-missing --cov=textsmith tests/

check: clean pycodestyle pyflakes coverage
