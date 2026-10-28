#!/usr/bin/env python3
"""INFRA-FIRST-QC-R33 per-bit FT pin model with SOURCE-KIT pins (COORD ruling R32 (c)).

Keeps the R32 model (results/qc_infra_r32/ft_pin_hops.py: neighbour-slot linear out pins, pessimistic window when the
in face has no abutting same-named slot) and adds, for EVERY slot instance, the kit pin table model:
  the kit generator (tools/die_plan/gen_phys.py type_pins) places bus/slot pin bit b exactly at
  schema.Plan.port_pins(port) -> (bit, layer, die coordinate along the face); both partitions of a face share it.
  real in  hop = port_pins(in_port)[bit i]  -> bank0 site(i)      (die frame, Manhattan, cell centre)
  real out hop = last bank site(i)         -> port_pins(out_port)[bit i]
The in/out ports of each (partition, slot) come from Plan.lane_crossings.  For a non-slot source this is the source
partition's declared bus (face/window/layers/order -> kit pin table); no separate per-bit pin json exists for these
types: the table is a deterministic function of the plan (UNCHECKED vs a generated kit's io until a kit is cut).
Usage: ft_pin_hops_src.py PLAN(.json|.json.gz) OUT.json [REPO_ROOT]
"""
import gzip, json, sys, importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'die_plan'))
import schema as S                                    # noqa: E402
spec = importlib.util.spec_from_file_location('r32', ROOT / 'results/qc_infra_r32/ft_pin_hops.py')
R32 = importlib.util.module_from_spec(spec); spec.loader.exec_module(R32)
LIM = R32.LIM; man = R32.man; to_die = R32.to_die


def face_xy(rect, face, c):
    x0, y0, x1, y1 = rect
    return {'N': (c, y1), 'S': (c, y0), 'E': (x1, c), 'W': (x0, c)}[face]


def main(plan, outp):
    raw = R32.load(plan)
    tmp = HERE / '_r32_rows.json'
    R32.main(plan, str(tmp))                           # unchanged R32 behaviour
    r32 = json.load(open(tmp)); tmp.unlink()
    key32 = {(r['part'], r['slot']): r for r in r32['rows']}
    P = S.Plan(raw)
    PT = raw['partition_types']; parts = {q['name']: q for q in raw['partitions']}
    cross = {}
    for lid in P.lanes:
        for part, slot, a, b in P.lane_crossings(lid):
            if slot:
                cross[(part, slot)] = (lid, a, b)
    rows = []
    for (pn, sn), r in key32.items():
        q = parts[pn]; t = PT[q['type']]; W, H = t['outline_um']
        s = next(z for z in t['ft_slots'] if z['name'] == sn)
        B = s['bit_sites_um']; n = len(B[0]); cw, ch = s.get('bit_site_cell_um', [1.404, 0.27])
        c = lambda b: to_die(q, W, H, (b[0] + cw / 2, b[1] + ch / 2))
        rect = P.rect(pn)
        lid, a, b = cross.get((pn, sn), (None, None, None))
        row = dict(r)
        if a is None:
            row.update(real_model='no lane crossing found'); rows.append(row); continue
        pa, pb = P.ports[a], P.ports[b]
        fin = S.OPP[pa['face']] if pa['src']['part'] != S.DIE_PART else pa['face']   # this part's face of in port
        fout = pb['face']
        pin_in = {bit: face_xy(rect, fin, cc) for bit, ln, cc in P.port_pins(a)}
        pin_out = {bit: face_xy(rect, fout, cc) for bit, ln, cc in P.port_pins(b)}
        src = pa['src']['part']; sb = pa['src']['bus']
        src_is_slot = sb.endswith('_o') and any(z['name'] == sb[:-2] for z in PT[parts[src]['type']].get('ft_slots') or []) \
            if src in parts else False
        hin = [(man(pin_in[i], c(B[0][i])), i) for i in range(n) if i in pin_in]
        hout = [(man(c(B[-1][i]), pin_out[i]), i) for i in range(n) if i in pin_out]
        mi, bi = max(hin); mo, bo = max(hout)
        g = P._type_geom(src, sb) if src in parts else None
        row.update(lane=lid, in_port=a, out_port=b, src_part=src, src_type=parts[src]['type'] if src in parts else src,
                   src_bus=sb, src_is_slot=src_is_slot, geom_from=pa.get('_geom_from') or 'port',
                   src_declares_geom=g is not None, n_pins_in=len(pin_in), n_pins_out=len(pin_out),
                   real_in_hop=round(mi, 3), real_in_bit=bi, real_out_hop=round(mo, 3), real_out_bit=bo,
                   real_in_worst_pin=pin_in[bi], real_in_worst_site=c(B[0][bi]),
                   real_model='kit pin table Plan.port_pins (gen_phys type_pins)')
        rows.append(row)
    ns = [r for r in rows if not r['in_model'].startswith('neighbour')]
    over = [r for r in rows if r.get('real_in_hop', 0) > LIM or r.get('real_out_hop', 0) > LIM]
    res = dict(schema='opentallas.ft_pin_hops_src.v1', plan=plan, limit_um=LIM, slots_instances=len(rows),
               r32_worst=r32['worst'], r32_over_limit=len(r32['over_limit']),
               real_worst=dict(in_hop=max(r.get('real_in_hop', 0) for r in rows), out_hop=max(r.get('real_out_hop', 0) for r in rows)),
               nonslot_src_instances=len(ns), nonslot_real_worst_in=max(r.get('real_in_hop', 0) for r in ns),
               r32_over_rows=[{k: r.get(k) for k in ('part', 'slot', 'n', 'in_hop', 'real_in_hop', 'real_in_bit', 'real_out_hop',
                                                       'src_part', 'src_type', 'src_bus', 'geom_from', 'src_declares_geom')}
                              for r in rows if (r['part'], r['slot']) in {(o['part'], o['slot']) for o in r32['over_limit']}],
               real_over_limit=over, rows=rows)
    json.dump(res, open(outp, 'w'), indent=1, default=list)
    print(json.dumps({k: v for k, v in res.items() if k not in ('rows', 'r32_over_rows', 'real_over_limit')}, indent=1))
    print('real over:', [(r['part'], r['slot'], r['real_in_hop'], r['real_out_hop']) for r in over])
    for r in res['r32_over_rows']:
        print(r)
    return 1 if over else 0


if __name__ == '__main__':
    raise SystemExit(main(*sys.argv[1:3]))
