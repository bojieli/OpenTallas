#!/usr/bin/env python3
"""HBMc/CHAIN 10-22 (STEWARD-HBMc): strict unread manifest admission against the coordinator ADMITTED ledger.

  strict_admission.py STAGE MANIFEST_PROPOSAL.json [--ledger results/arch/hbm_release_r15_1021/strict_admissions.json]

  * sha256 of the proposal equals an ADMITTED ledger entry  -> 'STAGE_STRICT_RELEASE_ADMITTED <sha> (<chain> <stage>)', rc 0
  * a new sha: histogram its classifications against the admitted classes (union of ADMITTED entries):
      - any class not admitted, or any non-candidate entry  -> 'STAGE_STRICT_DIAG new_classes=[..] non_candidates=N', rc 1
      - all classes admitted                                -> 'STAGE_STRICT_ADMISSION_PENDING <sha> classes within the
        admitted set; renewed coordinator review owed', rc 2 (still DIAGNOSTIC: a sha is admitted only by the ledger)
"""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[2] / 'results/arch/hbm_release_r15_1021/strict_admissions.json'


def judge(stage, manifest_bytes, ledger):
    sha = hashlib.sha256(manifest_bytes).hexdigest()
    adm = [e for e in ledger if e.get('status') == 'ADMITTED']
    for e in adm:
        if e.get('manifest_sha256') == sha:
            return 0, f"{stage}_STRICT_RELEASE_ADMITTED {sha} ({e.get('chain')} {e.get('stage')}, {e.get('admitted_by')})", {}
    ok = set().union(*[set(e.get('admitted_classes') or ()) for e in adm]) if adm else set()
    ents = json.loads(manifest_bytes).get('entries', [])
    hist = collections.Counter(x.get('classification') for x in ents)
    new = sorted(c for c in hist if c not in ok)
    nonc = sum(1 for x in ents if not x.get('allowlist_candidate'))
    det = dict(sha256=sha, entries=len(ents), bits=sum(int(x.get('bit_count') or 0) for x in ents),
               class_histogram=dict(sorted(hist.items())), new_classes=new, non_candidates=nonc)
    if new or nonc:
        return 1, f'{stage}_STRICT_DIAG {sha} new_classes={new} non_candidates={nonc}', det
    return 2, (f'{stage}_STRICT_ADMISSION_PENDING {sha} entries={len(ents)} classes within the {len(ok)} admitted; '
               f'renewed coordinator review owed (DIAGNOSTIC until the ledger admits this sha)'), det


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage')
    ap.add_argument('manifest', type=Path)
    ap.add_argument('--ledger', type=Path, default=DEFAULT)
    ap.add_argument('--json', type=Path)
    a = ap.parse_args()
    rc, line, det = judge(a.stage, a.manifest.read_bytes(), json.loads(a.ledger.read_text()))
    print(line)
    if a.json:
        a.json.write_text(json.dumps(dict(det, verdict=line.split()[0], ledger=str(a.ledger)), indent=1) + '\n')
    sys.exit(rc)


if __name__ == '__main__':
    main()
