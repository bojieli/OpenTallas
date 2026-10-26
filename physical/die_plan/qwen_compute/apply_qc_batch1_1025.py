#!/usr/bin/env python3
"""QC PLAN-DELTA batch 1 (COORD 2026-10-25 20:44 PDT) on FROZEN plan 441d1401.

D-QC-SU1713 (INTERNAL): su_core_aspect.apply -- prog/btab hard cores of sle_su_c/slw_su_c become the
  354.24x259.2 R0 aspect (CK 177.132/0.042 M5 native profile 2bc3495e27); u_ch/u_su8 re-origin; core ck taps
  follow. Partition outline, pins, FT and partition clock/reset entry unchanged (asserted below).
  NOT included (not approved in batch 1): Codex plan_ck177's ft_corner_channels on cbn_q00/q01 and the
  reset.relay_route=core_free_bbox on cbn_q00/q01/q11/cbx_q10.
D-QC-N59-1C (interface item 1, GEOM-REVIEW-5 19:48 (1c)): native59 dr_o (520 b, E face, M6/M4) window moved
  down the E face from [283.1613,391.7373] to [115.0,223.576] (same width/density/layers/order). coll_f4
  (coll_ftc, abutting E) takes it on its W face through the FT dr_o_dr_wi in-window, which the plan derives
  from the abutting source window; out window [515.568,605.744] and the 3 stations unchanged. +0 cycles.
  Why 115 and not GEOM's y~15: the coll_ftc slot is 786.24 um wide, so a W in-window at y15-125 gives
  786+491 = 1278 um / 3 stations = 426 um > 405 (G0C ERROR stations/reach; GEOM's 320 um/hop estimate
  was off). Per-bit (lsb_low both faces) worst paired dy = 515.568 - lo, so lo >= 92.6 is needed for the
  403-um per-bit budget; lo = 115 gives (786.24 + 400.6)/3 = 395.6 um. On native59 the far dr_o source
  (vm_write_v at x195,y30) -> dr_o reg -> E pin reg (x~770, y <= 223.6) is 575 + 194 = 769 um over two
  hops (<= 810), so both hops fit 405 with the dr_o regs placed between them (or select replicas).
Usage: apply_qc_batch1_1025.py die_plan.json   (in place; writes the new child pin files next to the cores)
"""
import copy, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import su_core_aspect

DR_OLD = [283.1613, 391.7373]
DR_NEW = [115.0, 223.576]


def frozen_iface(t):
    """Everything a parent / neighbour sees of a partition type."""
    c = t.get('clock', {})
    return json.dumps(dict(outline=t['outline_um'], buses=t['buses'], ft=t.get('ft_slots'),
                           reset=t.get('reset'), ck_tap=c.get('tap_um'), ck_layer=c.get('layer'),
                           ck_ins=c.get('insertion_ps')), sort_keys=True)


def main(path):
    path = Path(path)
    raw = json.loads(path.read_text())
    base = copy.deepcopy(raw)
    plan_dir = path.parent
    prof = {k: HERE / 'native_profiles' / k / 'target_native_pins.json' for k in ('prog', 'btab')}
    rep = su_core_aspect.apply(raw, plan_dir, plan_dir, prof)
    for tn in ('sle_su_c', 'slw_su_c'):
        assert frozen_iface(raw['partition_types'][tn]) == frozen_iface(base['partition_types'][tn]), tn
    n = 0
    for b in raw['partition_types']['native59']['buses']:
        if b['name'] == 'dr_o':
            assert b['face'] == 'E' and b['window_um'] == DR_OLD and b['width'] == 520, b
            b['window_um'] = list(DR_NEW)
            n += 1
    assert n == 1
    ftc = raw['partition_types']['coll_ftc']
    assert [v['name'] for v in raw['partitions'] if v['type'] == 'coll_ftc'] == ['coll_f4']
    # only these types may differ from the frozen plan
    for tn, t in raw['partition_types'].items():
        if tn not in ('sle_su_c', 'slw_su_c', 'native59'):
            assert t == base['partition_types'][tn], tn
    for k in raw:
        if k != 'partition_types':
            assert raw[k] == base[k], k
    path.write_text(json.dumps(raw, indent=1) + '\n')
    rep['n59_1c'] = dict(type='native59', bus='dr_o', old_window_um=DR_OLD, new_window_um=DR_NEW,
                         neighbour='coll_f4 (coll_ftc) W in-window of ft dr_o_dr_wi (derived)', cycles_added=0)
    (plan_dir / 'batch1_1025_report.json').write_text(json.dumps(rep, indent=1) + '\n')
    print('batch1 applied:', len(rep['changed']), 'core moves; dr_o', DR_OLD, '->', DR_NEW)


if __name__ == '__main__':
    main(sys.argv[1])
