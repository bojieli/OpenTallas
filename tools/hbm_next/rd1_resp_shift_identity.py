#!/usr/bin/env python3
"""Byte-identity check for the default-off rd1 response calendar shift (COMPILER-CAL-3).

  python3 -I tools/hbm_next/rd1_resp_shift_identity.py BASE_REV [WORKDIR]

Builds the old tree (current inputs, modified tools files restored from BASE_REV) and compares, with the
shift OFF, the old and the current tree: (1) hbm_idx_topk_static_vectors.py output (cal.mem, rec.txt, pre/chk.mem)
for pin_in 0 and 1; (2) idx_images.topk_record() for every IDX.TOPK record of the committed L02 fixture (events and
checks, sha256 of the JSON), pin_in 1 and 0; (3) hbm_vm_static_calendar.compile_schedule on those calendars, with the
resp_shift key absent and 0.  Prints one sha line per artefact and exits 1 on any difference.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPORT = ['tools', 'results/arch/hbm_vm_static_1014', 'rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar.sv']

PROBE = r'''
import hashlib, json, sys
from pathlib import Path
import numpy as np
root = Path(sys.argv[1]); fx = Path(sys.argv[2])
sys.path.insert(0, str(root / "tools"))
from hbm_layer_vehicle import idx_images as II
meta = json.loads((fx / "records.json").read_text()); z = np.load(fx / "operands.npz")
out = {}
for x in meta["records"]["0"]:
    if x["op"] != "IDX.TOPK": continue
    A = np.asarray(z[x["inputs"]["A"]["array"]]).view(np.uint32); O = np.asarray(z[x["outputs"]["O"]["array"]]).view(np.uint32)
    k = len(O); order = 1 if np.all(np.diff(O.astype(np.int64)) > 0) else 0
    for pin_in in (1, 0):
        g = II.topk_record(A, O, 7, k, order, pin_in=pin_in)
        out[f"topk_record_pin{pin_in}"] = hashlib.sha256(json.dumps(g, sort_keys=True, default=str).encode()).hexdigest()
print(json.dumps(out))
'''


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout


def digest_dir(d):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(d).iterdir())}


def run_tree(root, work, tag, fx):
    res = {}
    for pin_in in (0, 1):
        o = work / f'{tag}_vec{pin_in}'
        sh([sys.executable, '-I', str(root / 'tools/hbm_idx_topk_static_vectors.py'), str(o), '24', '0', str(pin_in)],
           env={'PYTHONPATH': str(root / 'tools')})
        res.update({f'vec_pin{pin_in}/{k}': v for k, v in digest_dir(o).items()})
    res.update(json.loads(sh([sys.executable, '-I', '-c', PROBE, str(root), str(fx)],
                             env={'PYTHONPATH': str(root / 'tools')})))
    return res


def main():
    base = sys.argv[1]
    work = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(tempfile.mkdtemp(prefix='rd1_identity_'))
    old = work / 'old'
    old.mkdir(parents=True, exist_ok=True)
    # old tree = a copy of the checked-out inputs with every tools file this change modified restored from BASE_REV
    # (git archive of the whole tree would fetch every blob of a sparse partial clone)
    for rel in EXPORT:
        src, dst = ROOT / rel, old / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
        else:
            shutil.copy2(src, dst)
    changed = sh(['git', '-C', str(ROOT), 'diff', '--name-only', base, '--', 'tools']).split()
    for rel in changed:
        blob = subprocess.run(['git', '-C', str(ROOT), 'show', f'{base}:{rel}'], capture_output=True)
        if blob.returncode == 0:
            (old / rel).write_bytes(blob.stdout)
    print('old tree: restored from', base, [Path(r).name for r in changed])
    fx = ROOT / 'results/rtl/hbm_ds_layer_tput_1018/fixtures/L02'
    a, b = run_tree(old, work, 'old', fx), run_tree(ROOT, work, 'new', fx)
    bad = 0
    for k in sorted(a):
        same = a[k] == b.get(k)
        bad += not same
        print(('SAME ' if same else 'DIFF ') + k, a[k][:16], (b.get(k) or '-')[:16])
    print('RD1_RESP_SHIFT_OFF_IDENTITY', 'PASS' if not bad and a.keys() == b.keys() else 'FAIL', len(a), 'artefacts')
    sys.exit(1 if bad or a.keys() != b.keys() else 0)


if __name__ == '__main__':
    main()
