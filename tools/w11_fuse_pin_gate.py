#!/usr/bin/env python3
"""Compare executable Verilator core code before/after W11's unused ME pin fix.

This is an elaboration equivalence gate, not a fresh token simulation or physical
sign-off. Only absolute worktree paths are normalised in generated C++/headers.
The baseline must be a clean, pinned checkout; existing verdicts are never edited.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--scratch', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    root = Path(__file__).resolve().parents[1]
    baseline = a.baseline.resolve()
    assert not a.out.exists(), 'Never overwrite an existing verdict'
    assert not subprocess.check_output(['git', '-C', str(baseline), 'status', '--porcelain']), 'Baseline must be clean'
    sys.path.insert(0, str(root / 'tools'))
    import w11_su_fuse_die as F
    D = F.D
    F._swap()
    D.UNITS = ('he', 'me', 'su')
    rels = [p.relative_to(root) for p in D.rtl_sources()]
    changed = [str(p) for p in rels if (root / p).read_bytes() != (baseline / p).read_bytes()]
    assert changed == ['rtl/hdc/v41x/ot_hdc_core_v41x_kr.sv'], changed
    v = Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'
    rec = dict(schema='opentallas.w11-fuse-unused-pin-equivalence.v1',
               claim_boundary='Generated executable core C++/header identity for the two reduced fused configurations; no fresh token simulation and no physical sign-off.',
               baseline_commit=subprocess.check_output(['git', '-C', str(baseline), 'rev-parse', 'HEAD'], text=True).strip(),
               candidate_commit=subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip(),
               verilator=subprocess.check_output([str(v), '--version'], text=True).strip(),
               changed_sources=changed, sources_sha256={str(p): sha((root / p).read_bytes()) for p in rels},
               normalisation='Replace the corresponding absolute worktree path with <ROOT>, and nothing else.', configurations=[])
    for name, bcast, ret in [('f00', 0, 0), ('f2517', 25, 17)]:
        cfg = dict(name=name, SUKR=40, SUBCAST=bcast, SURET=ret, SW=8, HHW=8, MG=8, SUN=16, SUM=8)
        outputs = []
        for label, tree in [('baseline', baseline), ('candidate', root)]:
            obj = a.scratch.resolve() / name / label
            obj.mkdir(parents=True, exist_ok=False)
            cmd = [str(v), '--cc', '-O2', '-Wno-fatal', *D.LINT_FLAGS, '--top-module', 'ot_hdc_core_v41x',
                   '-Mdir', str(obj), f'-I{tree / D.SVH.relative_to(root)}',
                   *[f'-G{k}={val}' for k, val in cfg.items() if k != 'name'],
                   *[f'-GX_{u.upper()}={int(u in D.UNITS)}' for u in D.X_UNITS],
                   '-Wno-TIMESCALEMOD', *[str(tree / p) for p in rels]]
            # The include path is the directory containing the ISA header.
            cmd[cmd.index(next(x for x in cmd if x.startswith('-I')))] = f'-I{tree / D.SVH.relative_to(root).parent}'
            run = subprocess.run(cmd, capture_output=True, text=True)
            (obj / 'elaboration.log').write_text(run.stdout + run.stderr)
            assert run.returncode == 0, (label, name, run.stderr[-2000:])
            outputs.append({p.name: sha(p.read_bytes().replace(str(tree).encode(), b'<ROOT>'))
                            for p in sorted(obj.iterdir()) if p.suffix in ('.cpp', '.h')})
            print(name, label, len(outputs[-1]), 'executable files', flush=True)
        mismatched = sorted(k for k in set(outputs[0]) | set(outputs[1]) if outputs[0].get(k) != outputs[1].get(k))
        rec['configurations'].append(dict(parameters=cfg, executable_files_sha256=outputs,
                                          mismatched_files=mismatched, exact=bool(outputs[0]) and not mismatched))
    rec['verdict'] = 'pass' if all(c['exact'] for c in rec['configurations']) else 'fail'
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=2) + '\n')
    print(rec['verdict'], flush=True)
    return int(rec['verdict'] != 'pass')


if __name__ == '__main__':
    sys.exit(main())
