from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

project = Path(SPECPATH)
datas = []
binaries = []
hiddenimports = []
for package in ('pymobiledevice3', 'ttkbootstrap', 'readchar', 'pytun_pmd3', 'sslpsk_pmd3'):
    package_data, package_binaries, package_imports = collect_all(package)
    datas.extend(package_data)
    binaries.extend(package_binaries)
    hiddenimports.extend(package_imports)

# readchar obtains its version using importlib.metadata at import time.
datas.extend(copy_metadata('readchar'))
datas.extend(copy_metadata('pymobiledevice3', recursive=True))
datas.extend(copy_metadata('ttkbootstrap', recursive=True))

a = Analysis(
    [str(project / 'gui.py')],
    pathex=[str(project)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['pytest', 'coverage', 'pip_audit', 'pywinauto'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='ZjuRun',
    debug=False,
    strip=False,
    upx=False,
    # Keep real pipes for the tunnel subprocess; hide a console owned by the GUI.
    console=True,
    hide_console='hide-early',
)
