.PHONY: install play clean

install:
	pip install -r requirements.txt

play:
	python3 main.py

clean:
	rm -rf __pycache__
	rm -rf */__pycache__
