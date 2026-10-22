"""Preserve a pre-physical interrupted case before copying fresh generated inputs.

The PHY PG adapter deliberately rejects applying its transform twice. rsync of
the generator's inputs does not delete that adapter's receipt, so a restart
after strict bind used to fail before it reached physical implementation.
Never archive a case with physical checkpoints: resume those through die_chain.
"""
from pathlib import Path
import argparse
import tempfile


def prepare(case):
    case = Path(case)
    if not (case / 'assumed_phy_pg_access.json').exists():
        case.mkdir(parents=True, exist_ok=True)
        return None
    checkpoints = list(case.rglob('*.odb'))
    if checkpoints:
        raise ValueError(f'physical case already exists ({checkpoints[0]}); resume die_chain instead of regenerating inputs')
    archive = Path(tempfile.mkdtemp(prefix=case.name + '.prephysical.', dir=case.parent))
    archive.rmdir()
    case.rename(archive)
    case.mkdir()
    return archive


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('case', type=Path)
    a = ap.parse_args()
    archive = prepare(a.case)
    if archive:
        print(f'Preserved interrupted pre-physical case: {archive}')
