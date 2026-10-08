#!/usr/bin/env bash
# Gera o executável AppImage do ES-DB (Linux x86_64).
#
# Uso:  packaging/build_appimage.sh
# Requer: Python com PySide6 + PyInstaller (use o .venv do projeto), curl.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PYTHON:-$ROOT/.venv/bin/python}"
DIST="$ROOT/dist"
APPDIR="$DIST/ES-DB.AppDir"
TOOL="$ROOT/build/appimagetool-x86_64.AppImage"
OUT="$DIST/ES-DB-x86_64.AppImage"

echo "==> 1/4 PyInstaller (bundle PySide6)"
"$PY" -m PyInstaller --noconfirm --clean --distpath "$DIST" \
    --workpath "$ROOT/build/pyi" packaging/esdb.spec

echo "==> 2/4 Montando o AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/512x512/apps"
cp -r "$DIST/esdb" "$APPDIR/usr/lib/esdb"
"$PY" packaging/make_icon.py "$APPDIR/esdb.png"
cp "$APPDIR/esdb.png" "$APPDIR/.DirIcon"
cp "$APPDIR/esdb.png" "$APPDIR/usr/share/icons/hicolor/512x512/apps/esdb.png"
install -m644 packaging/esdb.desktop "$APPDIR/esdb.desktop"
install -m644 packaging/esdb.desktop "$APPDIR/usr/share/applications/esdb.desktop"
install -m755 packaging/AppRun "$APPDIR/AppRun"

echo "==> 3/4 Obtendo o appimagetool"
if [ ! -x "$TOOL" ]; then
    mkdir -p "$ROOT/build"
    curl -L --fail -o "$TOOL" \
        https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x "$TOOL"
fi

echo "==> 4/4 Gerando o AppImage"
export ARCH=x86_64
"$TOOL" --appimage-extract-and-run "$APPDIR" "$OUT"
echo "OK: $OUT"
