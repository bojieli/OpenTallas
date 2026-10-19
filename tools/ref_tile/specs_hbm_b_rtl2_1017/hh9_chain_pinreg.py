"""HH-9 10-19: structural fix of hbm_hcq_bank_{e0,ca,cb,b0}_1017 after hbm_hcq_bank_e0_1017-ring1-47247cc08 FLOORPLAN_MARGIN
bank_distance (no lint override).  Run in the worktree root; edits the four specs in place (idempotent).

Why RTL chain pin registers (option B) and not the MX middle band (option A):
  * MX/R180 of hc_lanes_ref is impossible for ANY re-export that keeps W/E pins on both M4 and M6: mirrored about x the
    pins need an origin y shift = 24 mod 48 (M4, tracks 12 + 48k) AND = 32 mod 64 (M6, tracks 16 + 64k), which differ
    mod 16.  Only a one-layer re-export + leaf re-route would make it legal -- and even then only e0 is fixed:
  * bank_distance measures each lane leaf against the centroid of the block pins it is wired to.  e0 (N in / S out)
    passes with a 2-row middle band, but a corner bank (ca S->E, cb W->S; E/W ranges fixed by e2) has no 8-leaf
    placement on the 43.2 lattice within 100 um (exhaustive search, scratch/hh9/search.py: 0 solutions for any full or
    3.5 b/um range), and b0 (chain out N only) cannot hold 8 leaves of 138 um within 100 um of one 734 um face.
  * physically the defect is the hop: the leaves' chain flops sit inside the leaves, so a bank->bank hop was
    leaf -> 550 um -> face -> face -> 550 um -> leaf (~1.1 mm, > the 405 um planning reach).
  => chain pin registers at the bank faces (ot_hbm_hc_bankq_core CPI/CPO): every hop is face flop -> face flop, every
     in-tile segment one register stage (<= ~600 um repeated), no leaf is wired to a block pin.  Cost: +2 edges on
     banks 1, 3, 4, 5, 7, +1 on bank 0 (out only), e2 (banks 2 / 6) unchanged = +11 edges per HC pass (centre CHX,
     root QCHX = 11, programme RAW0 165 -> 176).
Pins: every chain face spread over the full face in e2's convention (descriptor 130-139.8, 2,048-b sum 139.8-730.4
= 3.5 b/um, flag 730.4-731.4, write/feed port 3-120), so b0 N == ca S, cb S == e0 N and ca E / cb W == e2 W / E align.
"""
import json
from pathlib import Path
RT = Path('physical/ref_tile')
D = [('d_v', 130, 131.0), ('d_ss', 131.0, 132.0), ('d_nv', 132.0, 134.019), ('d_wa', 134.019, 136.903),
     ('d_xa', 136.903, 139.786)]
def chain(inp, sumn, flag):
    pre = 'd' if inp else 'o'
    r = {f'{pre}{n[1:]}': [a, b] for n, a, b in D}
    r[sumn] = [139.786, 730.4]
    r[flag] = [730.4, 731.4]
    return r
WRITE = {'xb_v': [3, 4.0], 'xb_beat': [4.0, 5.0], 'xb_d': [5.0, 110.865], 'wv': [110.865, 111.865],
         'xv': [111.865, 112.865], 'j': [112.865, 113.865], 'wa': [113.865, 118.0], 'rst_n': [118.0, 119.0],
         'wfault': [119.0, 120.0], 'clk': [121.0, 122.0]}
CIN, COUT = chain(True, 'sum_in', 'f_in'), chain(False, 'sum_out', 'f_out')
B0E = dict(WRITE, **{k: v for k, v in chain(True, 's_o', 'x').items() if k != 'x'})
B0E['s_o'] = [139.786, 731.4]
KITS = {
 'hbm_hcq_bank_e0_1017': ({'CPI': 1, 'CPO': 1}, {**CIN, **COUT}, 'e0 (b4): chain in N / out S, hub W'),
 'hbm_hcq_bank_ca_1017': ({'CPI': 1, 'CPO': 1}, {**CIN, **COUT, **WRITE}, 'ca (b1 / b5): chain in S / out E (= e2 W)'),
 'hbm_hcq_bank_cb_1017': ({'CPI': 1, 'CPO': 1}, {**CIN, **COUT, **WRITE}, 'cb (b3 / b7): chain in W (= e2 E) / out S'),
 'hbm_hcq_bank_b0_1017': ({'CPO': 1}, {**COUT, **B0E, 's_i': [139.786, 731.4]}, 'b0: chain out N; exit relay S -> E'),
}
WIT = 'results/rtl/hbm_hc_ring_1019_cpr/ring_mut1.log'
NOTE = (' HH-9 10-19 (47247cc08 FLOORPLAN_MARGIN bank_distance, no lint override): CHAIN PIN REGISTERS at the tile faces '
        '(RTL ot_hbm_hc_bankq_core CPI/CPO; qeng CPR 1, centre CHX / root QCHX 11): the chain flops were inside the lane '
        'leaves, 550 um from the faces (bank->bank hop ~1.1 mm); now every hop is face flop -> face flop and no leaf is '
        'wired to a block pin. Chain pins spread over the full faces (3.5 b/um, e2 convention). MX middle band rejected: '
        'M4+M6 W/E leaf pins cannot be mirrored on track; corner/b0 banks have no 100 um leaf placement at all.')
for name, (params, rng, what) in KITS.items():
    p = RT / name / 'spec.json'
    s = json.loads(p.read_text())
    s['params'] = params
    face_of = {n: f for f, ns in s['pins'].items() for n in ns}
    s['pin_ranges'] = {k: v for k, v in rng.items() if k in face_of}
    missing = [k for k in rng if k not in face_of]
    assert not [k for k in missing if k not in ('xb_v', 'xb_beat', 'xb_d', 'wv', 'xv', 'j', 'wa', 'rst_n', 'wfault', 'clk')], (name, missing)
    s['pin_regs']['reason'] = ('every bank-tile input lands in an RTL flop and every output is a flop: the chain pins in the '
                               'CPI/CPO face registers (HH-9), the write/beat pins in the landing/write-port flops; a kit flop '
                               'stage would shift the compiled systolic schedule')
    if 'HH-9' not in s['structural_change']:
        s['structural_change'] += NOTE
    s['route']['peak_ram_gb'] = 96
    j = s['job']
    j.update(owner='Claude:HH-9', branch='claude/hh9-hcbank-1019', tag='cpr1',
             purpose=f'HC ring bank {what}; HH-9 chain pin registers (successor of 47247cc08 FLOORPLAN_MARGIN)')
    for b in j['benches']:
        if b['name'] == 'hc_ring_mut1':
            b['fail_witness'] = WIT
        b['peak_ram_gb'] = 64
    if 'results/rtl/hbm_hc_ring_1019_cpr' not in j['extra_paths']:
        j['extra_paths'] = j['extra_paths'] + ['results/rtl/hbm_hc_ring_1019_cpr']
    p.write_text(json.dumps(s, indent=1) + '\n')
    print(p, params, len(s['pin_ranges']), 'ranged ports')
