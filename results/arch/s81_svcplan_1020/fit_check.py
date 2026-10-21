#!/usr/bin/env python3
"""DRIVE-S81-SVCPLAN 10-20: MODEL arithmetic (no tool run) -- (1) the Codex G4_split112 rest<->engine cut,
(2) die width with the real slice parent kits (SLICEP k8a), per cluster-column count.  Numbers from dv_plan p4l
constants (run_mu7b.sh args) and RTL dsdv_svc_att.sv engine ports (H 16, D 32, TD 32, NL 4)."""
import json
H, D, TD, NL = 16, 32, 32, 4; NT = NL * (D // TD)
cut = {'q_w': D * 16 + 1, 'kv_w+m+v': NL * 265 + NL + 1, 'sc (l_d)': 16 + NL + NL * H * 32 + NL * H,
       'p_w+v': 2 * TD * 16 + 1, 'pv_c+y+f+v': 8 + NT * H * 32 + NT * H + 1, 'job/ready': 17 + 4}
bits = sum(cut.values())
# Codex g4_split112: rest at y 1771..3326, attention islands at y >= 10066 in the slice columns -> >= 6.7 mm vertical
# each, crossing frame row 1 (3000 tall) or the S-tier slice body (4600 tall): no relay site (FRAME_PITCH-FRAME_W 8.7 um,
# slice-column side strips 25 um; 562 relay is 62.6 um across)
split = dict(cut_bits_per_service=bits, cut=cut, min_vertical_um=10066 - 3326,
             bit_mm_16=round(16 * bits * (10066 - 3326) / 1000), die_bit_mm_mu7v2c=402790,
             longest_unsited_body_um=4600, gen_W2='FAIL by construction (body crossing > 405 um with no site)')
FW = 1436.832 + 8.7; EDGE = 600 + 240
def die_w(ncol, mid_col, end_col):
    return EDGE + ncol * 2 * FW + (ncol - 2) * mid_col + 2 * end_col
cols = {}
for n in (8, 7, 6):
    cols[n] = dict(today=round(die_w(n, 1000, 1000)), k8a_mid_lepmu_end=round(die_w(n, 1252.8 + 50, 2462.4 + 50)),
                   k8a_all=round(die_w(n, 1252.8 + 50, 1252.8 + 50)), frames_max=16 * n, slices=2 * n)
out = dict(scope='MODEL arithmetic only', split=split, die_width_um=cols, reticle_die_w_max_um=32000,
           slice_kits='SLICEP claude/drive-s81-slicep-1020 @6ccaf9472: k8a 1252.8 x 6739.2, lepmu d1a/b 2462.4 x 5788.8; '
                      'today slot 950 x 4600 (+50 margin = 1000 column)')
print(json.dumps(out, indent=1))
