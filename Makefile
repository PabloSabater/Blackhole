.PHONY: install play clean build-mac build-win

install:
	pip install -r requirements.txt

play:
	python3 main.py

clean:
	rm -rf __pycache__
	rm -rf */__pycache__
	rm -rf build dist *.spec

# Generar ejecutable para macOS (Debe ejecutarse en macOS)
build-mac:
	pyinstaller --noconfirm --onefile --windowed --name "Blackhole" --clean main.py

# Generar ejecutable para Windows (Debe ejecutarse en Windows)
build-win:
	pyinstaller --noconfirm --onefile --windowed --name "Blackhole" --clean main.py
