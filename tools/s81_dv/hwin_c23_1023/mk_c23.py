#!/usr/bin/env python3
"""STW-S81e-FP 10-23: dsdv_mu_hwin c23 floorplan = c22r RTL / params / benches, outline from content.

c21n/c22r: 84 x 64x16 SRAMs on a 12 x 7 grid at 43.2 um (561.6 x 388.8), halo 8.64 -> 7.5 um of cell row per
channel, so all logic was forced into ONE row band y 160-206 and every macro / pin flop reached it across the array
(pin->reg p90 234 um, 87 % empty, band-wide 561 um broadcast = the c21q/c21r TT -148 class).

c23: the macro has ALL signal pins on its W (read port, addresses, clk) and E (write data / mask) faces, N / S bare.
So each event lane = an abutted N-S bank of its 5 macros (payload banks 0..3 + attr), two lanes per column
(10 high = 207.9 um).  Columns alternate R0 / MY so two columns face their WRITE faces into one shared write
channel and their READ faces into the lane-logic channels; 4 columns W of a central spine, 4 E (mirror).  The spine
(86.4 um, exactly under the unchanged N / S pin windows) holds the shared record / select / cfg logic, the pin flops
and the gap / retire bank (4 macros, read faces W / E into the spine).  Every macro pin <= one channel (<= 28 um)
from its logic; widest logic span = outline width 449 um (was 561.6).
"""
import json, sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent
s = json.load(open(HERE / 'c22r_spec.json'))
MW, MH = 18.36, 20.79
PITCH = 20.832       # abutted N-S stack pitch: 434 M4 tracks (20.79 + 0.042 <= ABUT 0.1); every pin on track
V = 'physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1'
CORE = 2.16
RCH = 28.08          # read / lane-logic channel (macro face to macro face); 13 x 2.16
WCH = 25.92          # shared write channel
OCH = 25.92          # outer (W / E edge) read channel, tile face carries no pin
SPINE = 86.4         # spine between the two inner columns (pin windows are 84.8 um)
Y0 = 23.76           # S pin face: >= 20 um + core margin, on the 2.16 lattice
snap = lambda v, g: round(round(v / g) * g, 4)
# W side x positions (macro origins), columns 0..3 from W edge: R0, MY, R0, MY
xs = []; x = CORE + OCH
for c in range(4):
    xs.append(snap(x, 0.432)); x += MW + (WCH if c % 2 == 0 else RCH)
x_spine0 = xs[3] + MW + 0.0  # MY column 3: read face (LEF W) ends up E -> spine
spine_lo = snap(x_spine0 + 0.0, 0.432)
spine_hi = spine_lo + SPINE
# E side mirrored about the spine centre
ctr = (spine_lo + spine_hi) / 2
W = snap(2 * ctr, 8.64)
if W < 2 * ctr: W += 8.64
shift = (W - 2 * ctr) / 2
xs = [snap(v + shift, 0.432) for v in xs]; spine_lo += shift; spine_hi += shift; ctr += shift
xe = [snap(2 * ctr - v - MW, 0.432) for v in xs]       # mirrored origins
H = snap(Y0 + 9 * PITCH + MH + 22.0 + CORE, 8.64)
if H < Y0 + 9 * PITCH + MH + 20 + CORE: H += 8.64
orient_w = ['R0', 'MY', 'R0', 'MY']
orient_e = ['MY', 'R0', 'MY', 'R0']                   # mirror of the W side (read faces outward / into the spine)
macros = []
def lane_bank(se):
    return [f'*g_event_mem?{se}?.g_early.u_payload.g_bank?{b}?.u_m' for b in range(4)] + \
           [f'*g_event_mem?{se}?.g_early.u_attr.g_bank?0?.u_m']
cols = [(xs[c], orient_w[c]) for c in range(4)] + [(xe[c], orient_e[c]) for c in range(4)]
for ci, (cx, o) in enumerate(cols):
    for k, se in enumerate((2 * ci, 2 * ci + 1)):
        for j, inst in enumerate(lane_bank(se)):
            macros.append({'view': V, 'inst': inst, 'at': [cx, round(Y0 + (5 * k + j) * PITCH, 4)], 'orient': o,
                           'at_exact': True})
# gap / retire bank in the spine centre (R0: read face W, write face E; channels >= 20 on both sides inside the spine)
gx = snap(ctr - MW / 2, 0.432)
gy0 = round(Y0 + 3 * PITCH, 4)   # on the same track phase as the lane banks, centred
for j, inst in enumerate(['*u_gap.g_bank?0?.u_m', '*u_gap.g_bank?1?.u_m', '*u_retire.g_bank?0?.u_m', '*u_retire.g_bank?1?.u_m']):
    macros.append({'view': V, 'inst': inst, 'at': [gx, round(gy0 + j * PITCH, 4)], 'orient': 'R0', 'at_exact': True})
assert len(macros) == 84
# pin windows: same widths, centred on the spine (was centred at x 280.8 of 561.6)
dx = ctr - 280.8
pr = {k: [round(a + dx, 3), round(b + dx, 3)] for k, (a, b) in s['pin_ranges'].items()}
c = dict(s)
for k in ('orfs_vars', 'fill_reason'):
    c.pop(k, None)
c['name'] = 'dsdv_mu_hwin_c23'
c['outline'] = {'w': round(W, 3), 'h': round(H, 3)}
c['macros'] = macros
c['pin_ranges'] = pr
c['route'] = dict(s['route']); c['route']['macro_halo_um'] = 2.16; c['route']['tag'] = 'c23'
c['owner'] = 'Claude:STW-S81e-FP'
c['structural_change'] = (
    f"STW-S81e-FP c23 (COORD tile review 10-23 BAD on c21n: 36 macros 'face away', pin->reg p90 234 um, 87 % empty, "
    f"logic forced into one 46-um row band by the 8.64 halo + 24.8 channels; c21q/c21r TT -148 = the band-wide 561-um "
    f"duplicate broadcast). Same RTL / params / benches as c22r (LOCAL_RECORD=1, NEV 16). Geometry from content: "
    f"each event lane = abutted N-S bank of its 5 SRAMs (pins only on W / E, N / S bare), 2 lanes per column, 8 columns "
    f"alternating R0 / MY so write faces share one write channel ({WCH} um) and read faces open into the lane-logic "
    f"channels ({RCH} um); central {SPINE}-um spine under the unchanged N / S pin windows holds record / select / cfg, "
    f"the pin flops and the gap / retire bank. Halo 2.16 (was 8.64). Outline {W} x {H} (was 561.6 x 388.8, "
    f"-{100 - 100 * W * H / (561.6 * 388.8):.0f} % area); widest logic span {W} um.")
c['slot_change_request'] = (
    f"STW-S81e-FP 10-23 (lanes/STW-S81-DIE.md): hwin outline 561.6x388.8 -> {W}x{H}; N / S pin windows keep their "
    f"widths and order and stay centred on the tile (die x unchanged if the slot origin moves by +{280.8 - ctr:.2f} um); "
    f"ports / widths / pin faces unchanged.")
c['job'] = dict(s['job']); c['job'].update({'owner': 'Claude:STW-S81e-FP', 'branch': 'claude/s81e-fp-hwin-1023', 'tag': 'c23',
    'purpose': 'HWIN c23: c22r RTL on a content-derived lane-bank floorplan (abutted 5-SRAM lane banks, R0/MY write-channel pairs, central spine under the pin windows).'})
for b in c['job'].get('benches', []):
    b['cmd'] = b['cmd'].replace('physical/ref_tile/dsdv_mu_hwin_c22r/', 'physical/ref_tile/dsdv_mu_hwin_c22r/')
json.dump(c, open(HERE / 'dsdv_mu_hwin_c23.json', 'w'), indent=1)
print('outline', W, H, 'spine', round(spine_lo, 3), round(spine_hi, 3), 'cols W', xs, 'E', xe, 'gap bank', gx, gy0)
print('pins', pr)
