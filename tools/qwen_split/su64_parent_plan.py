#!/usr/bin/env python3
"""Q-ELEM-SUC 2026-10-16: the hardened qfd_sp_su64_sfu parent plan (Q-COMPUTE-DIE option (a)).

Outline 3240 x 3672 (the q2o1 SU frame 3239.976 x 3671.976 on the 8.64-um cluster lattice), 64 lanes in an 8 x 8 grid
(row r = lane octet r = vred region r, lanes 8r..8r+7 left to right; row 0 next to the VM on the S face).  Each lane is
four hard children: the CROM5 lane head (qfd_su_lane_h_native_crom5) and the exp / rcp / rsq native45 SFUs, packed as
the closed lane_t cluster was (head + rcp row, then a seam channel, then rsq + exp row; every child clock pin and every
head <-> SFU seam faces that channel).

Clock: 346 ports.  The 256 hard-child entries are INTERIOR pins on the block's top signal layer (M7, block cap M7)
directly over each child clock pin (entry wire <= 4 um); the die drops one V7 from its M8.  The 90 standard-cell roots
(ck, ck_lane0..63, ck_align0..15, ck_red0..8) are interior M7 pins at the centroid of their sinks.  Data faces keep the
die frame's faces and port order; every port takes two layers (S: M5 + M7, W / E: M4 + M6) at 2-track spacing
(<= 10.4 pins/um/layer), avoiding the block's own PG stripes, each port group centred on its frame window.

    su64_parent_plan.py OUTDIR   -> assigned_pins.json (opentallas.qwen-tp8.assigned-pins.v1 + per-bit positions),
                                    assigned_pins.tcl (place_pin), children.json (spec children), plan.json
"""
import json, math, sys
from pathlib import Path

W, H = 3240.0, 3672.0
CORE = 2.16
# block PG (ref_tile cluster pdn.tcl: offsets from the core origin)
def m5_bad(x):
    u = (x - CORE) % 5.4
    return 0.20 <= u <= 0.712            # VDD [.300,.420] VSS [.492,.612] +- 0.1
def m7_bad(x):
    u = (x - CORE) % 10.8
    return 0.90 <= u <= 1.388 or 6.30 <= u <= 6.788   # [1.0,1.288] / [6.4,6.688] +- 0.1
def m6_bad(y):
    u = (y - CORE) % 5.4
    return 0.413 <= u <= 1.285          # [0.513,0.801] / [0.897,1.185] +- 0.1
def m4_bad(y):
    return False
TRK = {'M4': (0.012, 0.048), 'M5': (0.012, 0.048), 'M6': (0.016, 0.064), 'M7': (0.016, 0.064)}
BAD = {'M4': m4_bad, 'M5': m5_bad, 'M6': m6_bad, 'M7': m7_bad}
FACE_LAYERS = {'S': ('M5', 'M7'), 'N': ('M5', 'M7'), 'W': ('M4', 'M6'), 'E': ('M4', 'M6')}

def slots(face, lo, hi):
    """2-track pin slots of both face layers in [lo, hi], sorted along the face"""
    out = []
    for L in FACE_LAYERS[face]:
        off, p = TRK[L]
        k = math.ceil((lo - off) / p)
        if k % 2: k += 1
        while off + k * p <= hi:
            z = round(off + k * p, 4)
            if not BAD[L](z):
                out.append((z, L))
            k += 2
    return sorted(out)

def dens(face):
    s = slots(face, 1000.0, 1100.0)
    return len(s) / 100.0

# ---- RTL ports (qfd_sp_su64_sfu) ----
PORTS = {  # name: (bits, direction)
    'external_a_re': (64, 'output'), 'external_a_addr': (1536, 'output'), 'external_a_q': (2048, 'input'),
    'external_vm_a_re': (64, 'input'), 'external_vm_a_addr': (1536, 'input'), 'external_embed_fault': (1, 'input'),
    'si': (482, 'input'), 'sd': (108, 'output'), 'acc': (24, 'output'), 'native_issue': (63, 'output'),
    'va': (2367, 'output'), 'vq': (6144, 'input'), 'cp': (56, 'input'), 'cp_active': (1, 'output'), 'cp_done': (1, 'output'),
    'xsw': (2137, 'output'), 'kv_we': (64, 'output'), 'kv_waddr': (1536, 'output'), 'kv_wdata': (2048, 'output'),
    'rst_n': (1, 'input')}
for g in range(8):
    PORTS[f'ca{g}'] = (206, 'output'); PORTS[f'cq{g}'] = (512, 'input')
CLOCKS = ['ck'] + [f'ck_{f}{i}' for f, n in [('head', 64), ('exp', 64), ('rcp', 64), ('rsq', 64), ('align', 16), ('lane', 64),
                                             ('red', 9)] for i in range(n)]
for c in CLOCKS:
    PORTS[c] = (1, 'input')
PEER = {'va': 'qfd_sp_vector_memory_par.sa', 'vq': 'qfd_sp_vector_memory_par.sq', 'si': 'qfd_seq_su_static.su',
        'sd': 'qfd_seq_su_static.sd', 'acc': 'qfd_seq_su_static.acc', 'external_a_re': 'qfd_seq_su_static.su_va_re',
        'external_a_addr': 'qfd_seq_su_static.su_va_addr', 'external_a_q': 'qfd_seq_su_static.su_va_q',
        'external_vm_a_re': 'qfd_seq_su_static.su_vm_va_re', 'external_vm_a_addr': 'qfd_seq_su_static.su_vm_va_addr',
        'external_embed_fault': 'qfd_embedding_word_provider.fault', 'native_issue': 'qfd_native59_compute_service.native_issue',
        'kv_we': 'qfd_native59_compute_service.kv_we', 'kv_waddr': 'qfd_native59_compute_service.kv_waddr',
        'kv_wdata': 'qfd_native59_compute_service.kv_wdata', 'cp': 'qfd_tt_ctlm_static_s.cp',
        'cp_active': 'qfd_tt_ctlm_static_s.cp_active', 'cp_done': None, 'xsw': 'qfd_xs_tap.sw'}
for g in range(8):
    PEER[f'ca{g}'] = 'qfd_su_cbuf_g.crom_re|crom_addr|crom_stage'; PEER[f'cq{g}'] = 'qfd_su_cbuf_g.crom_q'

# ---- face groups: (face, ports in frame order, frame window [lo, hi] whose centre is kept, min start) ----
GROUPS = [
    ('S', ['va', 'vq'], (2.028, 412.524), 30.0, None),
    ('W', ['acc', 'external_a_addr', 'external_a_q', 'external_a_re', 'external_vm_a_addr', 'external_vm_a_re', 'sd', 'si',
           'xsw'], (258.06, 1033.836), 30.0, None),
    ('W', ['cp', 'cp_active', 'cp_done'], (1638.924, 1645.26), None, None),
    ('E', ['kv_waddr', 'kv_wdata', 'kv_we', 'native_issue'], (185.484, 544.62), 30.0, None),
    ('E', ['ca0', 'ca1', 'cq0', 'cq1'], (638.124, 778.86), None, None),
    ('E', ['ca2', 'ca3', 'cq2', 'cq3'], (1193.196, 1333.932), None, None),
    ('E', ['ca4', 'ca5', 'cq4', 'cq5'], (1748.364, 1888.98), None, None),
    ('E', ['ca6', 'ca7', 'cq6', 'cq7'], (2303.436, 2444.172), None, None),
    ('N', ['rst_n', 'external_embed_fault'], (2000.268, 2001.324), None, None),
]
GAP = 0.96   # between ports of a group


def place_group(face, names, win, minstart):
    span_len = W if face in 'SN' else H
    # length needed: walk slots from 0 with the gaps
    def lay(start):
        pos = {}
        cur = start
        for n in names:
            bits = PORTS[n][0]
            s = slots(face, cur, cur + bits / 4.0 + 40)[:bits]
            if len(s) < bits:
                raise ValueError(f'{n}: slot window too short')
            pos[n] = s
            cur = s[-1][0] + GAP
        return pos, cur - GAP
    pos, end = lay(win[0])
    need = end - win[0]
    centre = (win[0] + win[1]) / 2
    start = centre - need / 2
    if minstart is not None:
        start = max(start, minstart)
    start = max(start, 2.4)
    pos, end = lay(start)
    if end > span_len - 2.4:
        raise ValueError(f'{face} group {names} overflows the face')
    return pos


def lanes():
    """lane l -> cell origin and the four children"""
    X0, PX, Y0, PY = 129.6, 388.8, 172.8, 432.0
    out = []
    for l in range(64):
        r, c = divmod(l, 8)
        x0, y0 = round(X0 + c * PX, 3), round(Y0 + r * PY, 3)
        out.append(dict(lane=l, row=r, col=c, x0=x0, y0=y0,
                        head=(x0, y0), rcp=(round(x0 + 216.0, 3), y0),
                        rsq=(x0, round(y0 + 172.8, 3)), exp=(round(x0 + 172.8, 3), round(y0 + 172.8, 3))))
    return out


VIEWS = {'head': ('physical/ref_tile/qfd_su_lane_h_native_crom5_f/views/qfd_su_lane_h_native_crom5', 'u_head', 172.8, 129.6, 88.476, 129.6),
         'rcp': ('physical/ref_tile/qfd_su_sfu_rcp_native45/views/qfd_su_sfu_rcp_native45', 'u_rcp', 108.0, 129.6, 56.124, 129.6),
         'rsq': ('physical/ref_tile/qfd_su_sfu_rsq_native45/views/qfd_su_sfu_rsq_native45', 'u_rsq', 129.6, 151.2, 62.652, 0.0),
         'exp': ('physical/ref_tile/qfd_su_sfu_exp_native45/views/qfd_su_sfu_exp_native45', 'u_exp', 129.6, 151.2, 62.652, 0.0)}


def m7_track_near(x):
    off, p = TRK['M7']
    k0 = round((x - off) / p)
    for d in (0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5, 6, -6, 7, -7, 8, -8, 9, -9, 10, -10):
        z = round(off + (k0 + d) * p, 4)
        if not m7_bad(z):
            return z
    raise ValueError(x)


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    L = lanes()
    children, interior = [], {}
    for ln in L:
        for kind in ('head', 'rcp', 'rsq', 'exp'):
            view, inst, w, h, cx, cy = VIEWS[kind]
            x, y = ln[kind]
            children.append(dict(view=view, count=1, inst=f'*g_lane?{ln["lane"]}?.g_tile.u_tile.{inst}*', at=[x, y], orient='R0'))
            px = m7_track_near(x + cx)
            py = round(y + cy + (3.0 if cy > 0 else -3.0), 3)   # in the seam channel, 3 um off the child edge
            interior[f'ck_{kind}{ln["lane"]}'] = (px, py)
        # the lane's relay root: in the channel east of the lane
        interior[f'ck_lane{ln["lane"]}'] = (m7_track_near(ln["x0"] + 324.0 + 32.4), round(ln['y0'] + 150.0, 3))
    for g in range(16):
        r, h = divmod(g, 2)
        x = 129.6 + (4 * h + 1.5) * 388.8 + 162.0
        y = 172.8 + r * 432.0 - 54.0 if r else 86.4
        interior[f'ck_align{g}'] = (m7_track_near(x), round(y, 3))
    for i in range(8):
        interior[f'ck_red{i}'] = (m7_track_near(129.6 + 3 * 388.8 + 324.0 + 32.4), round(172.8 + i * 432.0 + 324.0 + 54.0, 3))
    interior['ck_red8'] = (m7_track_near(600.0), 40.0)
    interior['ck'] = (m7_track_near(1620.0), 1836.0)
    assert len(interior) == len(CLOCKS) and set(interior) == set(CLOCKS)
    # ---- data pins ----
    bitpos = {}   # port -> list of (face, layer, x, y)
    for face, names, win, minstart, _ in GROUPS:
        pos = place_group(face, names, win, minstart)
        for n, s in pos.items():
            pts = []
            for z, Ly in s:
                x, y = {'S': (z, 0.0), 'N': (z, H), 'W': (0.0, z), 'E': (W, z)}[face]
                pts.append((face, Ly, x, y))
            bitpos[n] = pts
    for c, (x, y) in interior.items():
        bitpos[c] = [('interior', 'M7', x, y)]
    assert set(bitpos) == set(PORTS), set(PORTS) ^ set(bitpos)
    # ---- tcl ----
    tcl = ['# Q-ELEM-SUC su64_parent_plan.py: qfd_sp_su64_sfu PINREG parent pins (die option (a): interior M7 clock entries)']
    seen = {}
    for n, pts in bitpos.items():
        bits = PORTS[n][0]
        assert len(pts) == bits, n
        for i, (face, Ly, x, y) in enumerate(pts):
            name = n if bits == 1 else f'{n}[{i}]'
            wdt = 0.024 if Ly in ('M4', 'M5') else 0.032
            size = f'{wdt} 0.192' if (face in 'SN' or face == 'interior') else f'0.192 {wdt}'
            key = (Ly, round(x, 4), round(y, 4))
            if key in seen:
                raise ValueError(f'pin collision {name} {seen[key]}')
            seen[key] = name
            yy = y if face != 'interior' else y
            tcl.append(f'place_pin -pin_name {{{name}}} -layer {Ly} -location {{{x:.4f} {yy:.4f}}} -pin_size {{{size}}}')
    (out / 'assigned_pins.tcl').write_text('\n'.join(tcl) + '\n')
    # ---- json (assigned-pins.v1 + per-bit positions) ----
    faces, ranges, rec = {}, {}, {}
    for n, pts in bitpos.items():
        face = pts[0][0]
        along = [p[3] if face in 'WE' else p[2] for p in pts] if face != 'interior' else [0]
        lo, hi = min(along), max(along)
        r = dict(face=face if face != 'interior' else 'interior', layers=sorted({p[1] for p in pts}),
                 layer='+'.join(sorted({p[1] for p in pts})), bits=len(pts), range_um=[round(lo, 4), round(hi, 4)],
                 bit0_at='lo', direction=PORTS[n][1], peer=PEER.get(n),
                 positions_xy_um=[[round(p[2], 4), round(p[3], 4), p[1]] for p in pts])
        if face == 'interior':
            r.update(interior=True, layer='M7', layers=['M7'])
        else:
            faces.setdefault(face, []).append((lo, n)); ranges[n] = [round(lo, 4), round(hi, 4)]
        rec[n] = r
    data = dict(schema='opentallas.qwen-tp8.assigned-pins.v1', master='qfd_sp_su64_sfu', outline=dict(w=W, h=H),
                instances=1, pins={f: [n for _, n in sorted(v)] for f, v in faces.items()}, pin_ranges=ranges, ports=rec,
                overlapping_pin_pairs=0, source_rtl='rtl/qwen_split/qfd_sp_su64_sfu.sv', parameters=dict(PINREG=1),
                note=('Q-ELEM-SUC hardened-parent plan (Q-COMPUTE-DIE option (a), 2026-10-16): outline on the 8.64-um cluster lattice '
                      '(frame 3239.976 x 3671.976 -> 3240 x 3672); 346 clock ports are interior M7 pins (block cap M7, the die '
                      'reaches each with one V7 from M8): 256 hard-child entries <= 4 um from the child clock pin, 90 standard-cell '
                      'roots at their sink centroids; data faces as the frame, two layers per face at 2-track spacing, clear of '
                      'the block PG stripes.  Physical qualification: closure-loop job of physical/ref_tile/qfd_sp_su64_sfu_pr.'),
                density_pins_per_um=dict(S=dens('S'), W=dens('W'), E=dens('E')))
    (out / 'assigned_pins.json').write_text(json.dumps(data, indent=1) + '\n')
    (out / 'children.json').write_text(json.dumps(children, indent=1) + '\n')
    plan = dict(lanes=L, interior_clock_pins=interior,
                groups={f'{f}:{",".join(n)}': [bitpos[n[0]][0][2:], bitpos[n[-1]][-1][2:]] for f, n, *_ in GROUPS})
    (out / 'plan.json').write_text(json.dumps(plan, indent=1) + '\n')
    print(json.dumps(dict(pins=sum(len(v) for v in bitpos.values()), children=len(children), density=data['density_pins_per_um'],
                          ranges={k: v for k, v in ranges.items() if k in ('va', 'vq', 'acc', 'xsw', 'kv_waddr', 'native_issue', 'cq7', 'cp_done')})))


if __name__ == '__main__':
    main(sys.argv[1])
