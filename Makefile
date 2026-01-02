.PHONY: all
all:
	mypy *.py
	pyright
	./server.py
