#!/usr/bin/env python3
"""HEAD-PLAN-1: apply the plan of record's published raw-start constructor (head_start_reset_aliases.patch_rtl) to every
gen.py rtl wrapper of a plan, so the completed die top binds its rst_start_raw_* exports.  On l48ve this reproduces all
25 published/ wrappers byte for byte.  --private also applies the kit-only head_start_raw_private pairs (kit export).

  head_publish_wrappers.py PLAN.json[.gz] GEN_RTL_DIR OUT_DIR [--check-published DIR]   (run from the repo root)
--check-published: report per wrapper whether the result equals DIR/<module>.sv[.gz] (the plan of record's published/).
"""
import argparse, gzip, json, shutil, sys
from pathlib import Path
sys.path[:0] = ['tools/s81_head', 'tools/die_plan']
from head_start_raw_private import prepare_plan, patch_rtl as private_patch
from head_start_reset_aliases import patch_rtl as alias_patch


def rd(p):
    p = Path(p)
    return gzip.open(p, 'rt').read() if p.suffix == '.gz' else p.read_text()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('gen'); ap.add_argument('out')
    ap.add_argument('--check-published'); ap.add_argument('--private', action='store_true'); a = ap.parse_args()
    plan = json.loads(rd(a.plan)); gen, out = Path(a.gen), Path(a.out)
    shutil.copytree(gen, out)
    types = {tn for tn, t in plan['partition_types'].items() if not t.get('hard') or (gen / (t['module'] + '.sv')).exists()}
    if a.private:
        plan, _ = prepare_plan(plan, types)
    rep = {}
    for tn in sorted(types):
        t = plan['partition_types'][tn]; f = out / (t['module'] + '.sv')
        if not f.exists():
            continue
        text = alias_patch(f.read_text(), t.get('reset_start_raw_exports', []))
        if a.private:
            text, _ = private_patch(text, t)
        f.write_text(text)
        if a.check_published:
            c = [Path(a.check_published) / (t['module'] + s) for s in ('.sv', '.sv.gz')]
            c = [x for x in c if x.exists()]
            rep[tn] = 'NO_PUBLISHED' if not c else ('EQUAL' if rd(c[0]) == text else 'DIFF')
    print(json.dumps(rep, indent=0, sort_keys=True))


if __name__ == '__main__':
    main()
