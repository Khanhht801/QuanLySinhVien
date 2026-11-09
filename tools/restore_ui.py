"""Explicitly restore the verified UI, backing up the current file first."""
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def restore():
    source = ROOT / 'backups' / 'main.verified.ui'
    target = ROOT / 'main.ui'
    root = ET.parse(source).getroot()
    for name in ['sidebarScroll', 'subjectsTable', 'resultsChart']:
        if root.find(f'.//widget[@name="{name}"]') is None:
            raise RuntimeError('Verified UI backup is incomplete: ' + name)
    if root.find('.//widget[@name="coefficientSpin"]') is not None:
        raise RuntimeError('Verified UI backup still contains the removed coefficient.')
    if target.exists():
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
        copy2(target, source.with_name('main.before-restore-' + stamp + '.ui'))
    copy2(source, target)
    print('Restored main.ui from backups/main.verified.ui; previous file backed up.')


if __name__ == '__main__':
    restore()
