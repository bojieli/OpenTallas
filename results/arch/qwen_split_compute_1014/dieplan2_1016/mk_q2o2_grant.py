#!/usr/bin/env python3
"""Q-DIEPLAN2r 2026-10-16: q2o2 pin grant = SU on its hardened kit pins + every abutted UNCLOSED peer mirrors them.

usage: mk_q2o2_grant.py HOMES SU_KIT_PINS SEQ_PINS XS_PINS OUT [SEQ_SHIFT_UM]
  HOMES      q2o2 homes (positions of sp_su64_sfu, seq_su, native59, sp_vector_memory)
  SU_KIT     physical/ref_tile/qfd_sp_su64_sfu_pr/assigned_pins.json (claude/qelem-suc-1016)
  SEQ_PINS   a GEN's exported pins/qfd_seq_su_static.json (vrd / vwr S-face plan, uniform pitch)
  XS_PINS    a GEN's exported pins/qfd_xs_tap.json (CLOSED view: sw column, M4, uniform pitch)
Grants (per bit, exact; 'positions' along the peer's face in its master coordinates, kit layer per bit):
  seq_su (MY: die E face = master W)  su sd acc su_va_q su_va_addr su_va_re su_vm_va_addr su_vm_va_re <- kit si sd acc
      external_a_q external_a_addr external_a_re external_vm_a_addr external_vm_a_re
  native59 (R0, W face)               kv_waddr kv_wdata kv_we native_issue <- kit (same names)
  VM (N face)                         svr svw <- seq_su vrd vwr (straight drop under seq_su)
  SU seq group (die-side override of the kit, SEQ_SHIFT_UM, a multiple of 0.192): the kit's W-face seq group
      (acc .. si, 352 um at y 406.8 .. 758.8) moves down by SEQ_SHIFT_UM so it lies inside the 518-um seq_su face with
      seq_su abutting the VM in the SU-W / VM-N corner (no 240-um strip for the VM -> seq_su words); reported to Q-ELEM-SUC
  SU xsw (die-side override of the kit) <- the CLOSED xs_tap view's sw column (kit xsw 126 um M4+M6 cannot face a
      205 um M4 column with jog <= 36 um; reported to Q-ELEM-SUC)
"""
import json, sys
homes, kit, seqp, xsp, out = sys.argv[1:6]
SHIFT = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
assert abs(SHIFT / 0.192 - round(SHIFT / 0.192)) < 1e-6, 'seq shift must keep M4 / M6 tracks'
SEQ_GROUP = ('acc', 'external_a_addr', 'external_a_q', 'external_a_re', 'external_vm_a_addr', 'external_vm_a_re', 'sd', 'si')
H = json.load(open(homes))['homes']; K = json.load(open(kit))['ports']
S = json.load(open(seqp)); X = json.load(open(xsp))
su, seq, n59, vm, xs = (H[n] for n in ('sp_su64_sfu', 'seq_su', 'native59', 'sp_vector_memory', 'xs_tap'))
assert seq['o'] == 'MY' and n59['o'] == 'R0' and su['o'] == 'R0' and vm['o'] == 'R0', 'orientation assumptions'
r4 = lambda v: round(v, 4)
g = {}
def kit_y(kp):
    d = SHIFT if kp in SEQ_GROUP else 0.0
    return [(y - d, L) for _, y, L in K[kp]['positions_xy_um']]
def ew(peer, inst, pairs, face):
    for pp, kp in pairs:
        assert K[kp]['face'] in 'WE'
        pos = kit_y(kp)
        g.setdefault(peer, {})[pp] = dict(face=face, positions=[r4(y + su['y'] - inst['y']) for y, _ in pos],
                                          layers=[L for _, L in pos])
if SHIFT:
    for kp in SEQ_GROUP:
        pos = kit_y(kp)
        g.setdefault('qfd_sp_su64_sfu', {})[kp] = dict(face='W', positions=[r4(y) for y, _ in pos], layers=[L for _, L in pos])
ew('qfd_seq_su_static', seq, [('su', 'si'), ('sd', 'sd'), ('acc', 'acc'), ('su_va_q', 'external_a_q'),
   ('su_va_addr', 'external_a_addr'), ('su_va_re', 'external_a_re'), ('su_vm_va_addr', 'external_vm_a_addr'),
   ('su_vm_va_re', 'external_vm_a_re')], 'W')
ew('qfd_native59_compute_service', n59, [(p, p) for p in ('kv_waddr', 'kv_wdata', 'kv_we', 'native_issue')], 'W')
def uniform(rec):
    lo, hi = rec['range_um']; n = rec['bits']
    pts = [lo + (hi - lo) * i / (n - 1) for i in range(n)] if n > 1 else [lo]
    return pts if rec['bit0_at'] == 'lo' else pts[::-1]
for sp, vp in (('vrd', 'svr'), ('vwr', 'svw')):
    r = S['ports'][sp]; assert r['face'] == 'S'
    die_x = [seq['x'] + seq['w'] - x for x in uniform(r)]           # MY
    g.setdefault('vm', {})[vp] = dict(face='N', positions=[r4(x - vm['x']) for x in die_x], layers=[r['layer']] * r['bits'])
sw = X['ports']['sw']; assert sw['face'] == 'W'
g.setdefault('qfd_sp_su64_sfu', {})['xsw'] = dict(face='W', positions=[r4(y + xs['y'] - su['y']) for y in uniform(sw)],
                                                   layers=[sw['layer']] * sw['bits'])
# seq_su N face (die N; MY mirrors x): only local x >= 230 is open (xs_tap abuts above local 0..216). Pack, in order,
# su_vm_va_q (the VM sq broadcast branch: no SU pin faces it on the abutted E face, so it leaves N; M5+M7 2-track),
# the tt/sys_face control groups and the cbuf groups cbc / cbr (W face -> N, M5), 2 um apart.
def tracks(lo, n, lays):
    TR = {'M5': (0.012, 0.096), 'M7': (0.016, 0.128)}
    c = []
    for L in lays:
        off, st = TR[L]
        k = int((lo - off) / st) + 1
        for j in range(n):
            c.append((round(off + (k + j) * st, 4), L))
    c.sort()
    return c[:n]
N_ORDER = ['su_vm_va_q', 'xs', 'xm', 'su_observe', 'st', 'program_obs', 'dh', 'descriptor_obs', 'dc', 'cfg_image_ready'] + \
          [f'cbc{i}' for i in range(8)] + [f'cbr{i}' for i in range(8)]
at = 232.0
for pn in N_ORDER:
    r = S['ports'][pn]
    n = r['bits']
    lays = ('M5', 'M7') if n > 256 else ('M5',)
    c = tracks(at, n, lays)
    g.setdefault('qfd_seq_su_static', {})[pn] = dict(face='N', positions=[z for z, _ in c], layers=[L for _, L in c])
    at = c[-1][0] + 2.0
assert at < seq['w'] - 2.0, f'seq_su N face overflow {at}'
vm_master = 'qfd_sp_vector_memory_b2_partitioned_ro6_pin_e3'
late = {vm_master: g.pop('vm')}
json.dump(dict(schema='opentallas.qwen.split-pin-grant.v1',
               note='Q-DIEPLAN2r q2o2: SU on its hardened kit pins (qfd_sp_su64_sfu_pr); abutted unclosed peers mirror them per '
                    'bit (seq_su, native59), VM svr/svw under seq_su vrd/vwr, SU xsw = the closed xs_tap sw column. '
                    'Generated by mk_q2o2_grant.py from ' + homes.split('/')[-1],
               assigned_pins={'qfd_sp_su64_sfu': 'physical/ref_tile/qfd_sp_su64_sfu_pr/assigned_pins.json'},
               masters=g, late_masters=late), open(out, 'w'), indent=1)
print({m: {p: (len(v['positions']), min(v['positions']), max(v['positions'])) for p, v in d.items()} for m, d in {**g, **late}.items()})
