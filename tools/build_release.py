"""Build a Windows application folder and ZIP without including student data."""

from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != 'win32':
        raise SystemExit('Build the Windows release on Windows.')
    subprocess.run([
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm', '--clean', '--onedir', '--windowed', '--name', 'QLSV',
        '--distpath', str(ROOT / 'dist'),
        '--workpath', str(ROOT / 'build'),
        '--specpath', str(ROOT / 'build'),
        '--add-data', f'{ROOT / "main.ui"};.',
        '--add-data', f'{ROOT / "login.ui"};.',
        '--hidden-import', 'PyQt5.QtSvg',
        str(ROOT / 'main.py'),
    ], cwd=ROOT, check=True)
    release_dir = ROOT / 'release'
    release_dir.mkdir(exist_ok=True)
    archive = shutil.make_archive(
        str(release_dir / 'QLSV-Windows'), 'zip',
        root_dir=ROOT / 'dist', base_dir='QLSV',
    )
    print(f'Application: {ROOT / "dist" / "QLSV" / "QLSV.exe"}')
    print(f'Release ZIP: {archive}')


if __name__ == '__main__':
    main()
