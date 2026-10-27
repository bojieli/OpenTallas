#!/usr/bin/env python3
"""HEAD-BIND-4 2026-10-27: s81_head plan delta for the two bind gaps of the adopted head bind contract
(COORD ruling ~03:25 on HEAD-CORE-R13 ASK4; results/arch/head_bind_r13/HEAD_HOST_MESH_RANKROW_CONTRACT.md (c), (d)).

    python3 tools/s81_head/head_bind4_plan_delta.py [--plan P] [--rank R] [--row-map OUT.json]   (repo root cwd; in place)

1. ID straps (OWNER 10-25 option B).  hd_tile no longer holds u_strap (ot_s81hd_strap #(ROW0 0, TEN 1): every one of the
   264 instances hard-coded vocab rows 0..127, TEN 1).  The type declares two per-instance ID strap inputs
   (id_straps: strap_row0[16:0], strap_ten), bound to u_core.row0 / u_core.ten; every hd_tile partition carries its own
   values (partitions[].id_straps), tied as literals at the die top (gen.py rtl), set_false_path -from in the kit SDC.
   VALUES = tools/s81_head/head_row_map.py build(plan) of THIS plan (directed 565-b chain walk: 6 spines x {W, E} x 22
   tiles = 264 slots; 1010 bundles of 128 rows, 253/253/252/252 active per rank): slot k of rank R gets
   strap_row0 = 128 k (the controller's LOCAL 17-b row; global = local + c_rbase) and strap_ten = 1 if k < active(R),
   else row0 0 / ten 0 (dark).  --rank selects which rank die's values the plan carries (default 0); the other ranks are
   the same layout with other strap literals (--row-map writes all four).
2. hd_serdes binding.  u_phy = ot_s81hd_serdes_link (coll_o0[513:0] = {st, rx}, 0 added cycles) instead of the bare
   ot_pdie_serdes with only .rx/.tx bound: ck = clk, rst_n = rst_n, coll_i0 / coll_o0 buses, and the PMA pins as type
   pads (pma_tx[543:0], pma_tck out, pma_rx[543:0], pma_rck in; no boundary flop, die-top ports <part>_pma_*).  The
   link closure (ot_pdie_serdes + KP4 + 2 v1 macro models) moves from tools/s81_head/head_portbind_extra.f into the type
   sources, so gen.py rtl --rtl-root checks every leaf port of u_phy.
Touches only partition_types.hd_tile.{contents, nets, sources, id_straps}, partition_types.hd_serdes.{contents, buses,
pads, sources} and partitions[hd_tile].id_straps (merges with the infra delta: clock / islands / pg untouched)."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, 'tools/s81_head')
import head_row_map  # noqa: E402

SERDES_SRC = ['rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link.sv', 'rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv',
              'rtl/dsrom_sys/s81_link/ot_s81_kp4_common.sv', 'rtl/dsrom_sys/s81_link/ot_s81_kp4_enc.sv',
              'rtl/dsrom_sys/s81_link/ot_s81_kp4_dec.sv', 'rtl/dsrom_sys/s81_link/ot_s81_kp4_bm.sv',
              'rtl/dsrom_sys/s81_link/ot_s81_kp4_dchn.sv', 'rtl/dsrom_sys/s81_link/ot_s81_kp4_ddly.sv',
              'rtl/dsrom_sys/s81_link/ot_s81_kp4_dout.sv', 'rtl/dsrom_sys/s81_link/ot_s81_kp4_dsyn.sv',
              'physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v',
              'physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v']
EXTRA = Path('tools/s81_head/head_portbind_extra.f')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plan', default='physical/die_plan/s81_head/die_plan.json')
    ap.add_argument('--rank', type=int, default=0, choices=range(4))
    ap.add_argument('--row-map', help='write head_row_map.build(plan) (all 4 ranks) here')
    a = ap.parse_args()
    pp = Path(a.plan)
    plan = json.loads(pp.read_text())
    rm = head_row_map.build(pp)          # chain walk on the plan BEFORE this delta (topology unchanged by it)
    t = plan['partition_types']['hd_tile']
    t['contents'] = [c for c in t['contents'] if c['inst'] != 'u_strap']
    core = next(c for c in t['contents'] if c['inst'] == 'u_core')
    core['bind'].update(row0='strap:strap_row0', ten='strap:strap_ten')
    t['nets'] = [n for n in t.get('nets', []) if n['name'] not in ('row0', 'ten')]
    if not t['nets']:
        del t['nets']
    t['sources'] = [s for s in t['sources'] if s != 'rtl/dsrom_sys/s81_head/ot_s81hd_strap.sv']
    t['id_straps'] = [
        dict(name='strap_row0', width=17, note='bundle first LOCAL vocab row (128 x slot; global = + c_rbase), '
             'per instance (partitions[].id_straps from tools/s81_head/head_row_map.py); 0 on a dark tile'),
        dict(name='strap_ten', width=1, note='1 = used tile, 0 = dark (head_row_map.py: slot >= active bundles of the rank)')]
    vals = {s['part']: s['mask_params'] for s in rm['ranks'][a.rank]['slots']}
    n = 0
    for p in plan['partitions']:
        if p['type'] == 'hd_tile':
            mp = vals[p['name']]
            p['id_straps'] = dict(strap_row0=int(mp['ROW0']), strap_ten=int(mp['TEN']))
            n += 1
    s = plan['partition_types']['hd_serdes']
    s['contents'] = [dict(inst='u_phy', module='ot_s81hd_serdes_link', status='reuse',
                          bind=dict(ck='clk', rst_n='rst_n', pma_tx='pad:pma_tx', pma_tck='pad:pma_tck',
                                    pma_rx='pad:pma_rx', pma_rck='pad:pma_rck'),
                          note='layer-die KP4 link (ot_pdie_serdes) + {st, rx} packing, 0 added cycles '
                               '(ot_s81hd_serdes_link); PMA pins = type pads (HEAD-BIND-4)')]
    for b in s['buses']:
        b['leaf'] = {'coll_i0': 'u_phy.coll_i0', 'coll_o0': 'u_phy.coll_o0'}[b['name']]
    s['pads'] = [dict(name='pma_tx', dir='out', width=544), dict(name='pma_tck', dir='out', width=1, clock=True),
                 dict(name='pma_rx', dir='in', width=544), dict(name='pma_rck', dir='in', width=1, clock=True,
                                                              note='recovered PMA clock (own reset sync + rate matcher)')]
    s['sources'] = list(SERDES_SRC)
    pp.write_text(json.dumps(plan, indent=1) + '\n')
    lines = EXTRA.read_text().split('\n')
    keep = [ln for ln in lines if ln.split('#')[0].strip() not in SERDES_SRC]
    EXTRA.write_text('\n'.join(keep))
    if a.row_map:
        Path(a.row_map).parent.mkdir(parents=True, exist_ok=True)
        Path(a.row_map).write_text(json.dumps(rm, indent=1) + '\n')
    act = rm['ranks'][a.rank]['active_bundles']
    print(json.dumps(dict(status='APPLIED', rank=a.rank, hd_tile_instances=n, active=act, dark=n - act,
                          extra_removed=len(lines) - len(keep))))


if __name__ == '__main__':
    main()
