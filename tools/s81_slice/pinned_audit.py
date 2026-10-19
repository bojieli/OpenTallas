#!/usr/bin/env python3
"""pinned_audit.py -- S81-LBGAP G7 (2026-10-18): do hardened tiles built from PINNED copies elaborate the same RTL as the
rtl/ definitions a flat die elaboration takes?

A flat elaboration (die probe, layer-bench slice cut) holds ONE definition per module name.  Several closed tiles were
built from pinned copies (physical/<flow>/pinned/rtl/..., physical/s81_pq_tiles/rtl/...) of modules that also live in
rtl/ (layer bench cut_3S: 5 prefer conflicts, e.g. ot_hdc_fp32_mul_lat rtl/hdc vs physical/s81_pq_hier/pinned).  For
every tile spec (physical/ref_tile/*/spec.json) whose sources include a file outside rtl/ (macro black boxes excepted),
this walks the TILE TOP's real child closure (die_port_bind.instantiated, generate labels included) over the spec's own
sources, and for every module of that closure defined outside rtl/ compares the definition (comment-stripped body,
parameters, ports) with the rtl/ definition of the same name (die_port_bind.rtl_index over rtl/, i.e. what a flat
elaboration without a prefer rule takes):

  same      identical text: the conflict is moot for this tile
  DIFF      the closed view's RTL differs from rtl/: a flat elaboration does NOT reproduce this tile -> the tile owner
            either renames the pinned module (unique name) or proves equivalence with a lockstep bench
  NO_RTL    defined only outside rtl/ (no conflict; the die must index the pinned file)
Spec source files whose modules are NOT in the top's closure are listed as unused_sources (over-inclusive source lists;
their name conflicts are moot).

Usage: pinned_audit.py [--tiles a,b,...] [--prefix s81] --out JSON     (cwd anywhere; repo = this file's tree)
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as D  # noqa: E402


def mods(path, defines):
    t = D.preprocess(D.strip_comments(Path(path).read_text(errors='replace')), dict(defines))
    return {m.name: m for m in D.parse_modules(t, str(path))}


def key(m):
    return (re.sub(r'\s+', ' ', m.body).strip(), tuple(sorted(m.params.items())),
            tuple(sorted((k, str(v)) for k, v in m.ports.items())))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--tiles', help='comma list of ref_tile names (default: every spec with a non-rtl/ source)')
    ap.add_argument('--prefix', default='', help='only tiles whose name starts with this')
    ap.add_argument('--out', required=True)
    a = ap.parse_args(argv)
    rtl_idx, _ = D.rtl_index(['rtl'], [], {}, [])
    want = set(a.tiles.split(',')) if a.tiles else None
    rows, tot = [], dict(tiles=0, diff_tiles=0, diff_modules=set(), moot_conflicts=0)
    for sp in sorted((ROOT / 'physical/ref_tile').glob('*/spec.json')):
        name = sp.parent.name
        if (want and name not in want) or not name.startswith(a.prefix):
            continue
        try:
            sj = json.loads(sp.read_text())
        except Exception:
            continue
        srcs = [x for x in sj.get('sources', []) if isinstance(x, str)]
        outside = [x for x in srcs if not x.startswith('rtl/') and not x.endswith('_bb.v')]
        if not outside or not sj.get('top'):
            continue
        missing = [x for x in srcs if not (ROOT / x).is_file()]
        files = [str(ROOT / x) for x in srcs if (ROOT / x).is_file() and not x.endswith('_bb.v')]
        defines = {d: '' for d in sj.get('defines', []) if isinstance(d, str)}
        idx, _ = D.rtl_index([], files, defines, files)
        seen, traps = set(), {}
        unres, _m, _n = D.child_closure(idx, {sj['top']}, set(), seen, traps)
        used_files = {str(Path(idx[m].path).resolve()) for m in seen}
        unused = sorted(x for x in outside if str((ROOT / x).resolve()) not in used_files and (ROOT / x).is_file())
        per = {}
        for m in sorted(seen):
            p = Path(idx[m].path).resolve()
            rel = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
            if rel.startswith('rtl/'):
                continue
            r = rtl_idx.get(m)
            if r is None:
                per[m] = dict(file=rel, verdict='NO_RTL')
                continue
            tm = mods(p, defines).get(m)
            rm = mods(r.path, {}).get(m)
            same = tm is not None and rm is not None and key(tm) == key(rm)
            per[m] = dict(file=rel, rtl=str(Path(r.path).relative_to(ROOT)), verdict='same' if same else 'DIFF')
        # name conflicts the kit saw that are NOT in the top's closure (moot)
        moot = 0
        for x in unused:
            for m in mods(ROOT / x, defines):
                if m in rtl_idx and m not in seen:
                    moot += 1
        diff = sorted(m for m, v in per.items() if v['verdict'] == 'DIFF')
        rows.append(dict(tile=name, top=sj['top'], closure=len(seen), unresolved=unres, missing_sources=missing,
                         outside_modules=per, diff=diff, unused_sources=unused, moot_name_conflicts=moot))
        tot['tiles'] += 1
        tot['diff_tiles'] += bool(diff)
        tot['diff_modules'] |= set(diff)
        tot['moot_conflicts'] += moot
    tot['diff_modules'] = sorted(tot['diff_modules'])
    rec = dict(schema='opentallas.s81_slice.pinned_audit.v1', summary=tot, tiles=rows)
    Path(a.out).write_text(json.dumps(rec, indent=1) + '\n')
    for r in rows:
        if r['diff']:
            print(f"DIFF {r['tile']} ({r['top']}): {', '.join(r['diff'])}")
    print(f"PINNED_AUDIT tiles {tot['tiles']} with_diff {tot['diff_tiles']} diff_modules {len(tot['diff_modules'])} "
          f"moot_conflicts {tot['moot_conflicts']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
