PYTHON ?= python3
TESTER_FLAGS ?=
TESTS := $(wildcard samples/*.in)

.PHONY: default check clean

default: check

check:
	$(PYTHON) tester.py $(TESTER_FLAGS) $(TESTS)

clean:
	$(RM) out.txt
