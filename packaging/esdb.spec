# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec do ES-DB (bundle onedir para AppImage)."""

import os

# SPECPATH é injetado pelo PyInstaller (diretório deste .spec = packaging/).
ROOT = os.path.abspath(os.path.join(SPECPATH, os.pardir))

block_cipher = None

# Módulos grandes do Qt que o ES-DB não usa — excluídos para reduzir o tamanho.
_EXCLUDES = [
    "tkinter",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel", "PySide6.QtWebSockets",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.Qt3DExtras",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtSql", "PySide6.QtTest",
    "PySide6.QtBluetooth", "PySide6.QtNfc", "PySide6.QtPositioning",
    "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtRemoteObjects",
    "PySide6.QtScxml", "PySide6.QtHelp", "PySide6.QtDesigner",
]

a = Analysis(
    [os.path.join(ROOT, "packaging", "launch.py")],
    pathex=[os.path.join(ROOT, "src")],
    binaries=[],
    datas=[(os.path.join(ROOT, "src", "esdb", "resources", "icon.png"),
            "esdb/resources")],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=_EXCLUDES,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="esdb",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="esdb",
)
