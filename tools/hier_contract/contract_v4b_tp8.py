#!/usr/bin/env python3
"""qwen_rom_tp8 contract v4, addendum b (die lead r6, 2026-10-13; coordinator questions in el1011-qwen-tp8.log):
  T12 qfd_sp_res_ser (3): cluster slot 777.6 x 518.4 = 3 x 3 abutted cells of 259.2 x 172.8 (8 x ot_qfd_res_slot_tile
      re-shaped + 1 ctl / pin-flop cell); pins as v3 plus rst_n, me_en, fault.  Coordinator decision: option B.
  T13 qfd_tt_up4: ONE cluster in slot tt_up4_0 = 4 x ot_qfd_band_upper (NL 4, NB 3, LG 12; kit qfd_tt_up4_tp8,
      64.8 x 205.2 each) + pin flops; sel 26 b (LG 12) on both ends (tt_ctlm.sel too); qfd_tt_up4_g (tt_up4_1..3: a TP4
      r22k leftover with no pins and no die net) is REMOVED.
Idempotent.  usage: contract_v4b_tp8.py CONTRACT.json   (rewrites it in place, then runs the v4 checks)"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract_v4_tp8 as V4   # noqa: E402


def apply(C):
    slots = []
    for s in C['slots']:
        if s['cell'] == 'qfd_tt_up4_g':
            continue
        if s['cell'] == 'qfd_sp_res_ser':
            s['outline'] = dict(w=777.6, h=518.4)
            s['kind'] = 'parent'
            have = {p['name'].split('[')[0] for p in s['pins']}
            for nm, face, layer, span in (('rst_n[0]', 'N', 'M5', [392.0, 392.0]), ('me_en[0]', 'N', 'M5', [396.0, 396.0]),
                                          ('fault[0]', 'E', 'M4', [360.0, 360.0])):
                if nm.split('[')[0] not in have:
                    s['pins'].append(dict(name=nm, face=face, layer=layer, span_um=span))
            s.update(pg_layer='M7', strap_layer='M7', signal_max_layer='M7', version=4,
                     layer_cap=dict(cap='M7', view_max_layer=None, conforms=True),
                     sub_layout=dict(grid=[3, 3], cell_um=[259.2, 172.8],
                                     leaves={'ot_qfd_res_slot_tile (re-shaped 259.2 x 172.8, job qfd_res_slot_rs-s1-c724a7101)': 8,
                                             'ctl + N-face pin flops of i[4424:0] + one relay stage for the bottom row': 1},
                                     wiring='i words over the tiles on M6/M7; est. cut 3 x 555 b per 259.2-um column on M7 ~ 0.4 '
                                            '(estimate of el1013-qwen-elements-r6, not gate-checked)',
                                     clock='parent flops from a delayed entry matched to the tile insertion (re-measure '
                                           'after the re-shape; rh view = 509 ps SS)'),
                     notes='v4b T12: option B (coordinator 2026-10-13); +2 capture cycles absorbed in RS (rok margin)')
            for k in ('view_layers', 'view_cap', 'view_status', 'pin_replan', 'layer_rule'):
                s.pop(k, None)
        if s['cell'] in ('qfd_tt_up4', 'qfd_tt_ctlm'):
            for p in s['pins']:
                if p['name'] == 'sel[27:0]':
                    p['name'] = 'sel[25:0]'
        if s['cell'] == 'qfd_tt_up4':
            if not any(p['name'].startswith('rst_n') for p in s['pins']):
                s['pins'].append(dict(name='rst_n[0]', face='N', layer='M5', span_um=[176.0, 176.0]))
            s.update(kind='parent', version=4,
                     sub_layout=dict(leaves={'ot_qfd_band_upper NL 4 NB 3 LG 12 (kit physical/ref_tile/qfd_tt_up4_tp8, '
                                             '64.8 x 205.2)': 4, 'pin-flop / fan-out cell': 1},
                                     params=dict(NL=4, NB=3, LG=12, leaves=4, lanes=16),
                                     ports='pw0..2[512:0] = 16 lanes x 32 b + v (4 leaves x 128 b), lf0..2, '
                                           'ty[1537:0] = 4 x 384 b + 2, sel[25:0] = 2 x (LG + 1) broadcast to the 4 leaves, '
                                           'flt = OR of the leaf faults (registered); ty stays on W (the relay channel): '
                                           "the leaves' E-face ty goes to W-face pin flops inside the cluster"),
                     notes='v4b T13: the 2 x 2 group of r22k is one cluster in this slot; qfd_tt_up4_g removed')
        slots.append(s)
    C['slots'] = slots
    oi = C.setdefault('open_items', {})
    oi.pop('qfd_tt_up4_g', None)
    oi['qfd_sp_res_ser'] = ['v4b T12: build the 3 x 3 cluster parent over the re-shaped tile (qfd_res_slot_rs); bench + mutant; '
                            'gate-check the M7 cut']
    oi['qfd_tt_up4'] = ['v4b T13: build the cluster wrapper (4 x NL-4 leaf + pin flops) at 345.576 x 388.776; confirm LG 12 '
                        '(sel 26 b) against the TP8 tt_ctlm RTL before routing; die generator: drop tt_up4_1..3 '
                        '(tools/qwen_kv_die/rom_r22k.py ups, qwen_rom_fulldie_b3r2.py lines using tt_up4_2) and narrow o4_sel']
    C['deltas'] = [d for d in C.get('deltas', []) if d.get('id') not in ('T12', 'T13')] + [
        dict(id='T12', slots=['qfd_sp_res_ser'], status='decided v4b (coordinator option B)',
             change='cluster slot 777.6 x 518.4 (3 x 3 of 259.2 x 172.8); + rst_n, me_en, fault; +2 capture cycles in RS'),
        dict(id='T13', slots=['qfd_tt_up4', 'qfd_tt_ctlm'], status='decided v4b',
             change='tt_up4 = one cluster of 4 x ot_qfd_band_upper NL 4 / NB 3 / LG 12 in slot tt_up4_0; sel 28 -> 26 b; '
                    'qfd_tt_up4_g (3 slots, no pins) removed: 0.403 mm2 back to the relay channel')]
    cl = [c for c in C.get('changelog', []) if c.get('change', '').split(':')[0] != 'v4b']
    C['changelog'] = cl + [dict(version=4, when='2026-10-13', change='v4b: T12 qfd_sp_res_ser cluster slot 777.6 x 518.4 '
                                '(option B); T13 qfd_tt_up4 cluster NL 4 / NB 3 / LG 12 x 4, sel 26 b, qfd_tt_up4_g removed '
                                '(tools/hier_contract/contract_v4b_tp8.py)')]
    return C


if __name__ == '__main__':
    p = Path(sys.argv[1])
    C = apply(json.loads(p.read_text()))
    R = json.loads((p.parent / 'qwen_rom_tp8_v4_regen.json').read_text())
    C = apply(V4.apply(C, C['updated'], R))     # the v4 patch re-derives the floorplan summary from the slots
    p.write_text(json.dumps(C, indent=1) + '\n')
    print('slots', len(C['slots']), 'schema', V4.schema_errors(C)[:3], 'overlaps', V4.overlaps(C)[:5])
