#!/usr/bin/env python3
"""H-DIE-CKGEN 2026-10-16: bind the hb_ckgen slot to the HARDENED hfd_ckgen parent (kit physical/ref_tile/hbm_ckgen_cl).

Slot changes (all measured / forced by the hardened layout, recorded in the kit spec slot_change_request):
  * outline 259.2 -> 267.84 x 220.32 (grows EAST, origin kept): PLL 172.8 + rel4 21.6 + 2 x (2.16 core margin + 20 um
    block-core-edge channel) + 20 um block-block channel = 258.72 um does not fit 259.2 on the child / macro lattices;
    next 8.64 track-lattice outline.  Nothing within 300 um E/W (idx_s3 is 123 um N).
  * pins moved WEST on the same faces / layer (M5, 4.8 um spans): por_* under the rel4 release pins, pll_* in the 20 um
    channel the PLL W-edge clock pins drop through, refclk / por_n at the top of that channel (the granted spans under
    the PLL cost ~27 ps of wire on every por_* launch: gate 06:33 reg->out -29.1 ps).
  * the die clock trees start at these pll_* pins (die_clock_tree.ckgen_pin_xy).
  * hardened parent: PG M7, signals <= M6 (ref_tile cluster contract); children at the routed positions; view bound.

    python3 tools/hbm_die_v15/ckgen_parent_grant_1016.py VIEW_DIR JOB RECORD_COMMIT
"""
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
SPEC = ROOT / 'tools/ref_tile/specs_hbm_v15_harden/hbm_ckgen_cl.json'


def main(view, job, record):
    d = json.loads(C.read_text())
    s = json.loads(SPEC.read_text())
    slot = next(x for x in d['slots'] if x['name'] == 'hb_ckgen')
    prev = dict(outline=slot['outline'], pins=slot['pins'], children=slot.get('children'))
    face = {}
    for f, names in s['pins'].items():
        for n in names:
            face[n] = f
    pins = []
    for n, (a, b) in sorted(s['pin_ranges'].items(), key=lambda kv: (face[kv[0]], kv[1][0])):
        pins.append(dict(name=n, face=face[n], layer='M5', span_um=[a, b], offset=round((a + b) / 2, 3)))
    vd = ROOT / view
    # offset = the ROUTED pin centre of the view LEF (the placer puts each pin inside its span, not at its middle):
    # the die trees start exactly here (die_clock_tree.ckgen_pin_xy)
    import re
    lef = (vd / f"{Path(view).name}.lef").read_text()
    for p in pins:
        m = re.search(rf"PIN {p['name']}\b.*?RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*;", lef, re.S)
        x0, y0, x1, y1 = map(float, m.groups())
        p['offset'] = round((x0 + x1) / 2, 3) if p['face'] in ('N', 'S') else round((y0 + y1) / 2, 3)
        p['offset_basis'] = 'routed view LEF pin centre'
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(vd.iterdir())
             if p.suffix in ('.lef', '.lib') or p.name == 'insertion.json'}
    ch = s['children'][0]
    mc = s['macros'][0]
    slot.update(
        outline=dict(w=s['outline']['w'], h=s['outline']['h']), pins=pins,
        pg_layer='M7', strap_layer='M8', signal_max_layer='M6', layer_cap='M6',
        grant='hardened_cluster_ckgen_1016', view=view, view_files_sha256=files,
        children=[dict(inst='u_pll', cell='ot_hbm_pll_bb', view=mc['view'], at=mc['at'], outline=dict(w=172.8, h=172.8),
                       qualification='allowed analog PHY/PLL abstract'),
                  dict(inst='u_rel', cell='hfd_ckgen_rel4', view=ch['view'], at=ch['at'], outline=dict(w=21.6, h=21.6))],
        parent_qualified=True,
        hardened=dict(job=job, record=record, kit='physical/ref_tile/hbm_ckgen_cl', owner='Claude:H-DIE-CKGEN',
                      date='2026-10-16', previous=prev,
                      clock_source='clocks created at the PLL output pins; generated clocks (divide_by 1) at the four '
                                   'pll_* outputs = die clock-tree roots; por_* timed against their own forwarded clock'),
    )
    d.setdefault('ckgen_parent_grant_1016', dict(owner='Claude:H-DIE-CKGEN', slot='hb_ckgen', job=job, record=record,
                                                  why=s['slot_change_request']))
    C.write_text(json.dumps(d, indent=1) + '\n')
    print('hb_ckgen ->', slot['outline'], [(p['name'], p['face'], p['offset']) for p in pins])


if __name__ == '__main__':
    main(*sys.argv[1:4])
