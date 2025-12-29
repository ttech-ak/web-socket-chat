.PHONY: all
all:
	mypy *.py
	./server.py
