#!/usr/bin/env python3
"""Select DEC12 fold-gather masters in a logical, face-bound S81 top before die_plan bind.

Input must already have role-specific face masters (svc_rs_face_bind.py). Only the
11 directed gather folds are replaced; full-width dn/scatter/PV buses remain intact.
The new gh wires are LOGICAL crossings: tools/die_plan/bind.py must insert the
current plan's boundary flops, feedthrough stations and R8 pads before simulation
or physical implementation. This pass does not create a timing-qualified die.
"""
import argparse
import json
from pathlib import Path
import re

import svc_rs_faces as F
from svc_rs_face_bind import conns

ROOT = Path(__file__).resolve().parents[3]
INSTANCE = re.compile(r"^(\s*)(dsdv_svc_rs(?:_pvso_entry)?_fv_[0-9a-f]{10})(\s*#\((?:[^()]|\([^()]*\))*\))?\s+(u_rsv_(\d+))\s*\((.*)\);\s*$")
OPP = {'n': 's', 's': 'n'}


def rewrite(text, plan, root=ROOT):
    root = Path(root)
    ms, fhs = F.masks(str(root)), F.fh_masks(str(root))
    manifest = json.loads((root / 'results/arch/s81_dv_1016/svc_rs/embed_f2b.json').read_text())
    lanes = {l['id']: l for l in plan['lanes']}
    ports = {p['id']: p for p in plan['ports']}
    folds = []
    bindings = {}
    for hop in manifest['fold_hops']:
        src, dst, face = hop['src'], hop['dst'], hop['face'].lower()
        assert face in OPP and src // 2 == dst // 2 and src != dst, hop
        lane = hop['lane']
        assert lane == f'attnh__svc_{src}__svc_{dst}', hop
        lp = lanes[lane]
        assert lp.get('beats') == 2 and lp.get('word_bits') == 2133, lp
        assert len(lp['ports']) == 1, lp
        pp = ports[lp['ports'][0]]
        assert pp['src']['part'] == f'svc_{src}' and pp['dst']['part'] == f'svc_{dst}', pp
        assert pp['width'] == 1068 and pp['face'].lower() == face, pp
        wire = f'w_f2b_{lane}'
        assert wire not in text, 'already rewritten: ' + wire
        for sid, direction, f in ((src, 'o', face), (dst, 'i', OPP[face])):
            key = (sid, direction, f)
            assert key not in bindings, key
            fi = F.FACES.index(f)
            assert fhs[sid] >> (fi + (4 if direction == 'i' else 0)) & 1, key
            bindings[key] = wire
        folds.append(dict(lane=lane, src=src, dst=dst, face=face.upper(), wire=wire, width=1068))
    assert len(folds) == 11, folds
    lines = text.split('\n')
    report = dict(stage='LOGICAL_PREBIND', contract='DEC12_FOLD_2BEAT', instances={}, folds=folds,
                  required_next='fresh die_plan bind with current station cycles and R8, then verify',
                  physical_approval=False)
    for i, line in enumerate(lines):
        m = INSTANCE.match(line)
        if not m:
            continue
        ind, mod, params, inst, sid_text, body = m.groups()
        sid = int(sid_text)
        assert sid not in report['instances'], inst
        assert mod == F.variant(sid, ms[sid]), (inst, mod)
        cs = conns(body)
        old = dict(cs)
        assert len(old) == len(cs), inst
        remove, add = set(), {}
        for (s, direction, face), wire in bindings.items():
            if s != sid:
                continue
            prefix = 'gi' if direction == 'i' else 'go'
            for suffix in ('v', 'd'):
                p = f'{prefix}_{suffix}_{face}'
                assert p in old and old[p], (inst, p)
                remove.add(p)
            add[f'gh_{direction}_{face}'] = wire
        out = [(p, e) for p, e in cs if p not in remove] + sorted(add.items())
        newmod = F.variant_f2b(sid, ms[sid], fhs[sid])
        lines[i] = f"{ind}{newmod}{params or ''} {inst} ({', '.join('.%s(%s)' % c for c in out)});"
        report['instances'][sid] = dict(instance=inst, old=mod, new=newmod, removed=sorted(remove), added=add)
    assert sorted(report['instances']) == list(range(16)), sorted(report['instances'])
    header = next(i for i, line in enumerate(lines) if line.lstrip().startswith('module dv_die'))
    # Declarations may precede the instance connections but follow the complete module header.
    while ');' not in lines[header]:
        header += 1
    declarations = ['  // LOGICAL F2B crossings: final die_plan bind must replace with plan stations.']
    declarations += [f"  wire [1067:0] {f['wire']};" for f in folds]
    lines[header + 1:header + 1] = declarations
    return '\n'.join(lines), report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('die_in', type=Path)
    ap.add_argument('die_plan', type=Path)
    ap.add_argument('die_out', type=Path)
    ap.add_argument('--report', type=Path, required=True)
    ap.add_argument('--root', type=Path, default=ROOT)
    a = ap.parse_args()
    out, report = rewrite(a.die_in.read_text(), json.loads(a.die_plan.read_text()), a.root)
    a.die_out.write_text(out)
    a.report.write_text(json.dumps(report, indent=2) + '\n')
    print('F2B_LOGICAL_BIND PASS: 16 masters, 11 directed folds; physical rebind REQUIRED')


if __name__ == '__main__':
    main()
