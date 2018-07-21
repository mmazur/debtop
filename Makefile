.PHONY: check clean

clean:
	rm -f .cache/Contents*

check:
	pylint3 debtop myaptlib

# vi: noexpandtab
