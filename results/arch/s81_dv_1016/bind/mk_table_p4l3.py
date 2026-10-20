#!/usr/bin/env python3
"""S81-LBGAP/G3 (10-18): bind_table_p4l3.json = bind_table_p4l2.json with the LAYERBENCH-S81 die gaps G3/G4/G5 closed and
the S81-LINKTO corrected S-tier port map (coordinator 0hn decision 2) applied.

G3  the end-slice masters (dsdv_slice_lepw / _lepe / _lepe_nh: u_s_0S/0N/7S/7N) had no "land" on their inbound lane
    rules, so 44 staged inbound lanes (xrW_0S/0N_l0..3, xrE_6S/6N_l0..3, tvN/tvS rungs, r_f_0*/7* returns) ran straight
    from the last relay station into the slice pins; the link-tile tx rules (ot_pdie_serdes / ot_pdie_ucie tx.i) had no
    "land" either, so the 8 slice -> PHY lanes lt_lk_* (3 stations) were unlanded.  52 lanes, every one with a land-plan
    E (landing/p4l2/land_plan.json).  Now the same rules as ot_s81sl_slice (land: true) / a dsfd_dvland_512 tile per
    lt_lk lane.  0-stage returns (r_f_*2, the frame abutting its slice) stay unlanded (no station, as every slice).
G4  frames (col_h9 / col_h10 / col_h9_MX -> *_l4) get .INSTANCE("u_<inst>") (bind-table "instance_param"), the naming
    the slice cutter uses with --rom-instance: each frame loads its own ROM image <OT_ROM_DIR>/<INSTANCE>_cX_Y.viamap.hex.
G5  the lep masters are parameter-free tops (rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv): no hb_param (die.v
    passed #(.HB(0)); die_port_bind now reports inline params that are not in the RTL).
S-TIER (S81-LINKTO 10-18 10:05, coordinator 0hn decision 2): UCIe cannot cross the switch; every S81 end-slice port
    crosses it -> lk_WS0 / lk_ES0 bind ot_pdie_serdes (plan masters edited, same 260 x 2250 footprint; dv_plan.py too),
    ot_pdie_ucie drops out of the p4l bind, ch_b strap 1'b1 (SerDes basis) on the three lep masters.
"""
import copy, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
B = ROOT / 'results/arch/s81_dv_1016/bind'
T = json.load(open(B / 'bind_table_p4l2.json'))
M = T['masters']
for mm in ('dsdv_slice_lepw', 'dsdv_slice_lepe', 'dsdv_slice_lepe_nh'):
    m = M[mm]
    for r in ('xrE.i', 'xrW.i', 'vN.i', 'vS.i', 'ret.i'):
        m['ports'][r]['land'] = True                       # G3: as ot_s81sl_slice
    m.pop('hb_param', None)                                # G5: parameter-free top
    m['strap_values']['ch_b'] = "1'b1"                     # S-tier: SerDes basis on every end-slice port
    m['port_note'] = (m['port_note'].replace('ch_b strap 0 (UCIe basis)', "ch_b strap 1 (SerDes basis: every end-slice port "
                      "crosses the switch, S81-LINKTO corrected S-tier map)") +
                      '; S81-LBGAP/G3: inbound line / rung / return lanes landed (dsfd_dvland_276 / 276l / 70); parameter-free (no HB)')
for mm in ('ot_pdie_serdes', 'ot_pdie_ucie'):
    M[mm]['ports']['tx.i']['land'] = True                  # G3: slice tx -> PHY lane (3 stations) lands on the PHY root
for mm in ('col_h9', 'col_h10', 'col_h9_MX'):
    M[mm]['instance_param'] = 'INSTANCE'                   # G4
    M[mm]['port_note'] += '; INSTANCE = "u_<die instance>" (per-frame ROM image, as dv_slice_cut --rom-instance)'
T['rtl_widths']['dsfd_dvland_512'] = dict(ck_f=1, i=512, ck=1, rs=1, k=3, o=512, fault=1)
T['land_plan'] = 'results/arch/s81_dv_1016/landing/p4l3/land_plan.json'   # S81-LBGAP/G8: p4l2 + bundle-age K (dv_land_pilot.py agebundle)
T['note'] = (T['note'] + '; S81-LBGAP/G3 10-18: end-slice + link-tile inbound lanes landed, frame INSTANCE, lep masters '
             'parameter-free, S-tier ports all SerDes (bind/mk_table_p4l3.py)')
(B / 'bind_table_p4l3.json').write_text(json.dumps(T, indent=1) + '\n')

# plan: the two S-tier lane-0 link tiles bind SerDes (no geometry change)
pp = ROOT / 'results/arch/s81_dv_1016/p4l/plan.json'
txt = pp.read_text()
plan = json.loads(txt)
ucie = [b['name'] for b in plan['blocks'] if b['master'] == 'ot_pdie_ucie']
assert set(ucie) <= {'lk_WS0', 'lk_ES0'}, ucie
n = txt.count('"master": "ot_pdie_ucie"')
assert n == len(ucie), (n, ucie)
if n:      # text edit keeps the plan file byte-identical elsewhere
    pp.write_text(txt.replace('"master": "ot_pdie_ucie"', '"master": "ot_pdie_serdes"'))
print('bind_table_p4l3.json written; plan S-tier masters changed:', n)
