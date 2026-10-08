"""Ponto de entrada para o empacotamento (PyInstaller/AppImage)."""

import sys

from esdb.app import run

if __name__ == "__main__":
    sys.exit(run())
