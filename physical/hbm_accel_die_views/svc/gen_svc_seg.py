#!/usr/bin/env python3
"""CLAUDE HBM-ABSTRACTS (svcidx): SEGMENT SPLIT of the stream service hfd_svc_{SW,SE,NW,NE} (coordinator decision
2026-10-06: one ck pin per ~1 mm segment master, registered faces).

Two families: SW (= NW, identical pin plan, NW placed MX) and SE (= NE).  Each family is cut along x at free gaps of
its pin plan (no die pin, no PHY pin cluster under a cut) into 8 segment masters hfd_svc_<fam>_s0..s7.  Units of
rtl/ot_hbm_svc_seg_lib.sv sit where their pins / partners are (SM port + line assembler at the SM port, SM arbiter
at the centre of its four pseudo-channels, PC pin unit / W lane unit at their PHY pins, W unit at the PHY W port,
e dispatcher at the e port, KV / IK assemblers at their ports); units talk only through wire-stage chains
(ot_svc_vpipe).  A chain that crosses a cut has a flop at the out pin of one segment and at the in pin of the next
(zero-length die net between abutting segments); every hop <= HOP um (Manhattan).  Segment-local ck / rst pins.

Writes (all under physical/hbm_accel_die_views/svc/):
  rtl/seg/hfd_svc_<fam>_s<j>.sv      segment masters
  rtl/seg/hfd_svc_<st>_seg.sv        the segments joined with the parent's ports (bench vehicle, st = SW/SE/NW/NE)
  sdc/hfd_svc_<fam>_s<j>_fwd.sdc     forwarded input clocks of a segment (if any)
  split/hfd_svc_<fam>_s<j>/{ports.json, io_place.tcl, ws.tcl}   derived master record, wire-stage endpoints
  split/split.json                   bands, parent-port -> band-port map (bit ranges for phy), cross buses
  seg_stages.json                    per-chain stage plan and the cycle ledger vs the one-slot margin view
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_die_views as V  # noqa: E402
import hbm_die_wrap as Wr  # noqa: E402

S, H, L = V.S, V.H, V.L
PS = '--ps' in sys.argv          # hbm-forks 2026-10-09: per-PC stream successor (ot_hbm_svc_ps_lib.sv); outputs *_ps
SEGD, SPLD, SDCD, STG = (('rtl/seg_ps', 'split_ps', 'sdc_ps', 'seg_stages_ps.json') if PS else
                         ('rtl/seg', 'split', 'sdc', 'seg_stages.json'))
PS_PORTS_BITS = dict(ks=1102, kq=2, kd=3)
HOP = 380.0                      # um per wire-stage hop (index_q b4 sign-off reg-to-reg +135 ps at 323 um, 1.135 ps/um -> ~+70 ps at 380)
XST = 2                          # the one-slot margin view's extra stages per chain (ledger)
PITCH = 0.096                    # cross-bus pins: M4 on the E / W faces, every other track
CUTS = {'SW': [1017.024, 2322.96, 3379.968, 4452.96, 5238.96, 6301.968, 7363.968],
        'SE': [1017.024, 2318.016, 3379.968, 4761.984, 5770.992, 6865.968, 7629.984, 8100.0]}   # r23: SE_s7 split at the 8,088-8,234 um free gap (coordinator 2026-10-07)
FAM = {'SW': ['hfd_svc_SW', 'hfd_svc_NW'], 'SE': ['hfd_svc_SE', 'hfd_svc_NE']}
PHY_BB = 'physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/ot_hbm3e_phy_v41x_aw30_e8p5_bb.v'
Y_LO, Y_MID, Y_HI = 5.0, 130.0, 254.0


def _committed_parent(name):
    """hbm-forks 2026-10-09: the parent hfd_svc_<st> record rebuilt from the COMMITTED legacy split (split/split.json +
    split/<band>/ports.json): the current die model no longer carries the unsplit parent (master_record KeyError), so
    the committed split is the authority for the parent's pins, faces, directions and forwarded-clock bits."""
    sp = json.loads((HERE / 'split/split.json').read_text())
    par = sp['parents'][name]
    ports, fclk, r0 = {}, {}, None
    for band in par['bands']:
        r = json.loads((HERE / 'split' / band / 'ports.json').read_text())
        r0 = r0 or r
        x0 = sp['bands'][band]['x0_um']
        for bn, pm in par['port_map'][band].items():
            pn, (lo, hi) = pm['parent_port'], pm['parent_bits']
            if pn == '<new>':
                continue
            src = r['ports'][bn]
            dst = ports.setdefault(pn, dict(bits=0, layer=src['layer'], pins=[], face=src['face']))
            for q in src['pins']:
                i = int(re.search(r'\[(\d+)\]', q[0]).group(1)) + lo
                dst['pins'].append([f'{pn}[{i}]', q[1], round(q[2] + x0, 4), q[3], round(q[4] + x0, 4), q[5]])
            dst['bits'] = max(dst['bits'], hi + 1)
            if pn == 'phy':
                dst.setdefault('_dirs', []).extend((lo + a, lo + b, d) for a, b, d in src['dir_segments'])
            else:
                dst['dir_segments'] = src['dir_segments']; dst['direction'] = src['direction']
            if bn in r.get('fclk', {}):
                fclk[pn] = {int(b): v for b, v in r['fclk'][bn].items()}
    ph = ports['phy']
    ph['pins'].sort(key=lambda q: int(re.search(r'\[(\d+)\]', q[0]).group(1)))
    segs_ = sorted(ph.pop('_dirs'))
    merged = []
    for a, b, d in segs_:
        if merged and merged[-1][2] == d and merged[-1][1] == a:
            merged[-1][1] = b
        else:
            merged.append([a, b, d])
    ph['dir_segments'] = merged; ph['direction'] = 'inout'
    w = max(sp['bands'][b]['x0_um'] + sp['bands'][b]['w_um'] for b in par['bands'])
    return dict(master=name, kind='svc', w_um=round(w, 4), h_um=r0['h_um'], obs_top=r0['obs_top'],
                note='parent rebuilt from the committed split', instances=1, orients=['R0'], inst_names=[name],
                ports=ports, generator=r0['generator']), fclk


_PARENTS = {}


def _mrec(name, _orig=V.master_record):
    if name in ('hfd_svc_SW', 'hfd_svc_SE', 'hfd_svc_NW', 'hfd_svc_NE'):
        if name not in _PARENTS:
            _PARENTS[name] = _committed_parent(name)
        return json.loads(json.dumps(_PARENTS[name][0]))
    return _orig(name)


def _fclk(name, _orig=Wr.fclk_bits):
    if name in ('hfd_svc_SW', 'hfd_svc_SE', 'hfd_svc_NW', 'hfd_svc_NE'):
        _mrec(name)
        return _PARENTS[name][1]
    return _orig(name)


V.master_record = _mrec
Wr.fclk_bits = _fclk


def cx(port):
    xs = [(p[2] + p[4]) / 2 for p in port['pins']]
    return sum(xs) / len(xs)


def ceil_hops(d):
    return max(1, math.ceil(d / HOP - 1e-9))


PS_NEW = {}


def ps_ports(P, parent, segs, seg_of, H_um, wants):
    """PS row ports ks<k> (1,102 out: line + 3 forwarded clocks), credit ports kq<k> (2 in: {fclk, v}) and the
    stream-done port kd (2 out: {fclk, done}): N-face M5 pins at 0.192 um pitch (the l<k> line ports' density, 5.2 b/um),
    in the free N-face span nearest the unit inside the unit's segment."""
    PITCH_N = 0.192
    def merged(iv):
        out = []
        for a_, b_ in sorted(iv):
            if out and a_ <= out[-1][1] + 1.0:
                out[-1][1] = max(out[-1][1], b_)
            else:
                out.append([a_, b_])
        return [tuple(x) for x in out]
    occl = {L_: merged((q[2], q[4]) for v in P.values() for q in v['pins'] if v.get('face') == 'N' and q[1] == L_)
            for L_ in ('M5',)}
    fk = _PARENTS[parent][1]
    for name, xc in wants:
        bits = PS_PORTS_BITS[name[:2]]
        j = seg_of(xc)
        a, b = segs[j]
        best = None
        # M5 at the line ports' pitch (0.192 um, 5.2 b/um); where the segment's N face is full, M5 at 0.096 um (10.4 b/um,
        # under the 12 b/um fail line; the die generator's split views take N-face pins on M5 only)
        for L_, PITCH_N in (('M5', 0.192), ('M5', 0.096)):
            need = bits * PITCH_N + 2.0
            occ = occl[L_]
            cands = sorted({round(x, 3) for x in [xc - need / 2, a + 2.0] + [e + 1.0 for _, e in occ] +
                            [s_ - need - 1.0 for s_, _ in occ]})
            for x0 in cands:
                x0 = max(x0, a + 2.0)
                x1 = x0 + need
                if x1 > b - 2.0 or any(not (x1 <= s_ - 0.5 or x0 >= e + 0.5) for s_, e in occ):
                    continue
                d = abs(x0 + need / 2 - xc)
                if best is None or d < best[0]:
                    best = (d, x0, L_, PITCH_N)
            if best is not None:
                break
        assert best is not None, (parent, name, xc, 'no free N-face span in segment', j)
        L_, PITCH_N = best[2], best[3]
        x0 = round(round((best[1] + 1.0) / 0.048) * 0.048, 4)
        wpin = 0.024
        pins = [[f'{name}[{i}]', L_, round(x0 + i * PITCH_N, 4), round(H_um - 0.192, 4), round(x0 + i * PITCH_N + wpin, 4),
                 H_um] for i in range(bits)]
        d_ = 'in' if name.startswith('kq') else 'out'
        P[name] = dict(bits=bits, layer=L_, pins=pins, face='N', dir_segments=[[0, bits, d_]],
                       direction='input' if d_ == 'in' else 'output')
        occl[L_] = merged(occl[L_] + [(pins[0][2], pins[-1][4])])
        fk[name] = ({1099: 'out', 1100: 'out', 1101: 'out'} if name.startswith('ks') else
                    {1: 'in'} if name.startswith('kq') else {2: 'out'})
        PS_NEW[name] = (bits, P[name]['direction'])


def plan_family(fam):
    geo = json.loads((HERE / 'svc_geometry.json').read_text())
    parent = FAM[fam][0]
    g = geo[parent]
    rec = V.master_record(parent)
    P = rec['ports']
    W_um, H_um = rec['w_um'], rec['h_um']
    cuts = CUTS[fam]
    edges = [0.0] + cuts + [W_um]
    # band j = [cut_j, cut_{j+1} - 0.024] (cuts on the 0.048 um grid, 0.024 gap as the index_q split)
    segs = [(round(edges[j], 4), round(edges[j + 1] - (0.024 if j + 1 < len(edges) - 1 else 0.0), 4))
            for j in range(len(edges) - 1)]

    def seg_of(x):
        for j, (a, b) in enumerate(segs):
            if a - 1e-6 <= x <= b + 1e-6:
                return j
        raise ValueError(x)
    # every parent pin lies inside one segment
    for n, p in P.items():
        for q in p['pins']:
            assert seg_of(q[2]) == seg_of(q[4]), (fam, n, q)
    pcx, lx = g['pc_x'], g['lane_x']
    arb = [sum(pcx[4 * k:4 * k + 4]) / 4 for k in range(8)]
    smx = [cx(P[n]) for n in g['order']]
    kvx, ikx, ex = cx(P['kv']), cx(P['ik']), cx(P['e'])
    phy = S.real_lef(S.PHY_LEF)
    wx = phy['pins']['w_v'][1][0]
    KV, IK = g['kv_pc'], g['ik_pc']
    U = {}                                            # unit -> (x, y)
    for k in range(8):
        U[f'sp{k}'] = (smx[k], Y_HI); U[f'as{k}'] = (smx[k], Y_HI); U[f'ar{k}'] = (arb[k], Y_MID)
    for p in range(32):
        U[f'pc{p}'] = (pcx[p], Y_LO)
    for l in range(8):
        U[f'ln{l}'] = (lx[l], Y_LO)
    U['w'] = (wx, Y_LO); U['e'] = (ex, Y_HI); U['kv'] = (kvx, Y_HI); U['ik'] = (ikx, Y_HI)
    if PS:
        for k in range(8):
            U[f'gp{k}'] = (smx[k], Y_HI)          # beside SM k's line assembler: the c_rs chains end there
        ps_ports(P, parent, segs, seg_of, H_um, [('ks%d' % k, smx[k]) for k in range(8)] +
                 [('kq%d' % k, smx[k]) for k in range(8)] + [('kd', ex)])
    C = []                                            # chains: name, W (payload), src unit, src v, src d, dst unit, dst v, dst d

    def ch(name, w, su, sv, sd, du, dv, dd, kind):
        C.append(dict(name=name, w=w, su=su, sv=sv, sd=sd, du=du, dv=dv, dd=dd, kind=kind))
    for k in range(8):
        ch(f'c_rq{k}', 42, f'sp{k}', f'sp{k}_iv', f'sp{k}_id', f'ar{k}', f'ar{k}_sv', f'ar{k}_sd', 'req')
        ch(f'c_tb{k}', 1, f'ar{k}', f'ar{k}_take', "1'b0", f'sp{k}', f'sp{k}_tk', None, 'req_tok')
    for p in range(32):
        o, j = divmod(p, 4)
        ch(f'c_is{p}', 51, f'ar{o}', f'ar{o}_iv[{j}]', f'ar{o}_id[{j*51+50}:{j*51}]', f'pc{p}', f'pc{p}_iv', f'pc{p}_id', 'iss')
        if PS:      # every beat; SM (tag 00) and stream (tag 11) beats split at the assembler / group unit
            ch(f'c_rs{p}', 277, f'pc{p}', f'pc{p}_bv', f'{{pc{p}_bt, pc{p}_bb, pc{p}_bd}}', f'as{o}', f'rs{p}_v', f'rs{p}_d',
               'rsp')
        else:
            ch(f'c_rs{p}', 277, f'pc{p}', f"pc{p}_bv && (pc{p}_bt[16:15] == 2'b00)", f'{{pc{p}_bt, pc{p}_bb, pc{p}_bd}}',
               f'as{o}', f'as{o}_sv[{j}]', f'as{o}_sq[{j*277+276}:{j*277}]', 'rsp')
        ch(f'c_dn{p}', 1, f'as{o}', f'as{o}_kt[{j}]', "1'b0", f'ar{o}', f'dn{p}_o', None, 'rsp_tok')
    for nm, pc, x_, tg in (('kv', KV, kvx, "2'b01"), ('ik', IK, ikx, "2'b10")):
        ch(f'c_{nm}r', 277, f'pc{pc}', f"pc{pc}_bv && (pc{pc}_bt[16:15] == {tg})", f'{{pc{pc}_bt, pc{pc}_bb, pc{pc}_bd}}',
           nm, f'{nm}_sv', f'{nm}_sq', nm)
        ch(f'c_{nm}d', 1, nm, f'{nm}_dn', "1'b0", f'ar{pc // 4}', f'{nm}d_o', None, nm + '_tok')
    for l in range(8):
        ch(f'c_wl{l}', 271, f'ln{l}', f'ln{l}_v', f'ln{l}_d', f'as{l}', f'as{l}_wsv', f'as{l}_wsq', 'wl')
        ch(f'c_wd{l}', 1, f'as{l}', f'as{l}_wt', "1'b0", 'w', f'w_ld[{l}]', None, 'wl_tok')
        ch(f'c_wr{l}', 1, f'ln{l}', f'ln{l}_rq', "1'b0", 'w', f'w_room[{l}]', None, 'room')
    ch('c_ew', 40, 'e', 'e_ow', 'e_od', 'w', 'w_cv', 'w_cd', 'e_w')
    ch('c_ewb', 1, 'w', 'w_ct', "1'b0", 'e', 'e_bw', None, 'e_w_tok')
    ch('c_ek', 40, 'e', 'e_ok', 'e_od', f'ar{KV // 4}', f'ar{KV // 4}_kcv', f'ar{KV // 4}_kcd', 'e_kv')
    ch('c_ekb', 1, f'ar{KV // 4}', f'ar{KV // 4}_kt', "1'b0", 'e', 'e_bk', None, 'e_kv_tok')
    ch('c_ei', 40, 'e', 'e_oi', 'e_od', f'ar{IK // 4}', f'ar{IK // 4}_icv', f'ar{IK // 4}_icd', 'e_ik')
    ch('c_eib', 1, f'ar{IK // 4}', f'ar{IK // 4}_it', "1'b0", 'e', 'e_bi', None, 'e_ik_tok')
    ps_lists = {}
    if PS:
        west = sorted((p for p in range(32) if pcx[p] < ex), key=lambda p: -pcx[p])
        east = sorted((p for p in range(32) if pcx[p] >= ex), key=lambda p: pcx[p])
        ps_lists = dict(w=west, e=east)
        for side, Ls in ps_lists.items():
            for i, p in enumerate(Ls):
                src = ('e', 'e_sdv', 'e_sdd') if i == 0 else (f'pc{Ls[i-1]}', f'pc{Ls[i-1]}_dov', f'pc{Ls[i-1]}_dod')
                ch(f'c_sd{p}', 124, src[0], src[1], src[2], f'pc{p}', f'pc{p}_div', f'pc{p}_did', 'ps_desc')
                dst = ('e', f'e_d{side}ok', f'e_d{side}ph') if i == 0 else (f'pc{Ls[i-1]}', f'pc{Ls[i-1]}_dniok', f'pc{Ls[i-1]}_dniph')
                ch(f'c_dd{p}', 1, f'pc{p}', f'pc{p}_dnook', f'pc{p}_dnoph', dst[0], dst[1], dst[2], 'ps_done')
                # indexed id-FIFO pop credits back to the e port (32-bit OR chain, same direction as the done chain)
                dsti = ('e', None, f'e_ic{side}') if i == 0 else (f'pc{Ls[i-1]}', None, f'pc{Ls[i-1]}_ici')
                ch(f'c_ic{p}', 32, f'pc{p}', "1'b1", f'pc{p}_ico', dsti[0], f'pc{p}_icv', dsti[2], 'ps_icr')
        for p in range(32):
            o, j = divmod(p, 4)
            ch(f'c_cr{p}', 1, f'gp{o}', f'gp{o}_cr[{j}]', "1'b0", f'pc{p}', f'pc{p}_crv', None, 'ps_cr')
        for k in range(8):          # the stream's load tag (ATT ld fields, compiler-supplied) to each group unit
            ch(f'c_sg{k}', 13, 'e', 'e_sgv', 'e_sgd', f'gp{k}', f'gp{k}_sgv', f'gp{k}_sgd', 'ps_tag')
    for c in C:
        c['xa'], c['ya'] = U[c['su']]; c['xb'], c['yb'] = U[c['du']]
        c['sa'], c['sb'] = seg_of(c['xa']), seg_of(c['xb'])
    # cross lists per cut: rightward (seg j -> j+1) and leftward
    cross = {j: dict(r=[], l=[]) for j in range(len(cuts))}
    for c in C:
        a, b = c['sa'], c['sb']
        for j in range(min(a, b), max(a, b)):
            cross[j]['r' if b > a else 'l'].append(c['name'])
    byname = {c['name']: c for c in C}
    # pin runs on each cut face: order by the chain's mean y (PHY side low), rightward run then leftward run
    face = {}
    for j, d in cross.items():
        y = 1.0
        for dirn in ('r', 'l'):
            names = sorted(d[dirn], key=lambda n: (byname[n]['ya'] + byname[n]['yb'], n))
            off = 0
            runs = {}
            for n in names:
                wb = byname[n]['w'] + 1
                runs[n] = (off, wb)
                off += wb
            face[(j, dirn)] = dict(names=names, runs=runs, bits=off, y0=y)
            y += off * PITCH + 1.0
        assert y < H_um - 1.0, (fam, j, y)
    # stage plan per chain portion
    for c in C:
        a, b = c['sa'], c['sb']
        step = 1 if b >= a else -1
        portions = []
        if a == b:
            d = abs(c['xb'] - c['xa']) + abs(c['yb'] - c['ya'])
            portions.append(dict(seg=a, N=ceil_hops(d), A=('u', c['xa'], c['ya']), B=('u', c['xb'], c['yb']), d=d))
        else:
            segl = list(range(a, b + step, step))
            for i, s in enumerate(segl):
                def pin_y(cut, dirn):
                    f = face[(cut, dirn)]
                    o, wb = f['runs'][c['name']]
                    return f['y0'] + (o + wb / 2) * PITCH
                dirn = 'r' if step > 0 else 'l'
                if i == 0:
                    cut = s if step > 0 else s - 1
                    xp = segs[s][1] if step > 0 else segs[s][0]
                    A, B = ('u', c['xa'], c['ya']), ('p', xp, pin_y(cut, dirn))
                elif i == len(segl) - 1:
                    cut = s - 1 if step > 0 else s
                    xp = segs[s][0] if step > 0 else segs[s][1]
                    A, B = ('p', xp, pin_y(cut, dirn)), ('u', c['xb'], c['yb'])
                else:
                    c_in = s - 1 if step > 0 else s
                    c_out = s if step > 0 else s - 1
                    xi = segs[s][0] if step > 0 else segs[s][1]
                    xo = segs[s][1] if step > 0 else segs[s][0]
                    A, B = ('p', xi, pin_y(c_in, dirn)), ('p', xo, pin_y(c_out, dirn))
                d = abs(B[1] - A[1]) + abs(B[2] - A[2])
                if A[0] == 'p' and B[0] == 'p':
                    N = math.ceil(d / HOP - 1e-9) + 1
                else:
                    N = ceil_hops(d)
                portions.append(dict(seg=s, N=N, A=A, B=B, d=round(d, 1)))
        c['portions'] = portions
        c['stages'] = sum(p_['N'] for p_ in portions)
    return dict(ps_lists=ps_lists, fam=fam, parent=parent, rec=rec, g=g, segs=segs, cuts=cuts, U=U, C=C, cross=cross, face=face,
                KV=KV, IK=IK, wx=wx, arb=arb, smx=smx, H=H_um, W=W_um, seg_of=seg_of)


def phy_bits(pl):
    """per phy bit: (x, PHY pin name, PHY direction) in the parent's phy port order."""
    rec = pl['rec']
    pins = sorted(rec['ports']['phy']['pins'], key=lambda q: int(re.search(r'\[(\d+)\]', q[0]).group(1)))
    phy = S.real_lef(S.PHY_LEF)
    dfi = H.real_ports()[phy['name']]['dfi']
    bb = L.parse_module(PHY_BB, 'ot_hbm3e_phy_v41x_aw30_e8p5')['ports']
    assert len(dfi) == len(pins)
    out = []
    for i, n in enumerate(dfi):
        m = re.match(r'(\w+)\[(\d+)\]$', n)
        b, ix = (m.group(1), int(m.group(2))) if m else (n, 0)
        out.append(((pins[i][2] + pins[i][4]) / 2, b, ix, bb[b][0]))
    return out


def phy_expr(b, ix):
    """svc-side signal of a PHY pin (PHY input: what drives it; PHY output: the wire it feeds), or None (unused)."""
    pcw = dict(k_addr=30, k_len=4, k_tag=17, kr_tag=17, kr_beat=4, kr_data=256)
    if b in ('k_v', 'k_rdy', 'kr_v'):
        return f'pc{ix}_{b}'
    if b in pcw:
        p, i = divmod(ix, pcw[b])
        return f'pc{p}_{b}[{i}]'
    if b in ('k_we', 'k_wdata', 'k_wstrb'):
        return "1'b0"
    if b in ('kr_rdy', 'wr_rdy'):
        return 'rdy_q'
    lw = dict(wr_tag=10, wr_beat=5, wr_data=256)
    if b in ('wr_v', 'w_room'):
        return f'ln{ix}_{b}'
    if b in lw:
        l, i = divmod(ix, lw[b])
        return f'ln{l}_{b}[{i}]'
    if b == 'w_v':
        return 'w_wv'
    if b in ('w_addr', 'w_len', 'w_tag'):
        return f'{b}_s[{ix}]'
    if b == 'w_rdy':
        return 'w_rdy_s'
    if b == 'clk':
        return 'phy_clk'
    if b == 'rst_n':
        return 'phy_rst_n'
    return None


# views agent 2026-10-07: SE_s7 aggressive variant (SLOT 3: kept grant copies + one more line register, +1 cycle per line)
ASM_SLOT = {'hfd_svc_SE_s7': 4, 'hfd_svc_SW_s5': 4}


def build(pl):
    fam, rec, g = pl['fam'], pl['rec'], pl['g']
    P = rec['ports']
    fck = Wr.fclk_bits(pl['parent'])
    segs, C, face = pl['segs'], pl['C'], pl['face']
    order = g['order']
    rank = {n: k for k, n in enumerate(order)}
    pb = phy_bits(pl)
    seg_of = pl['seg_of']
    phy_rng = {}
    for i, (x, b, ix, d) in enumerate(pb):
        s = seg_of(x)
        lo, hi = phy_rng.get(s, (i, i))
        phy_rng[s] = (min(lo, i), max(hi, i))
    for s, (lo, hi) in phy_rng.items():
        assert all(seg_of(pb[i][0]) == s for i in range(lo, hi + 1)), (fam, s)
    unit_seg = {u: seg_of(x) for u, (x, y) in pl['U'].items()}
    # the PC / lane / W units must own their PHY pins
    for i, (x, b, ix, d) in enumerate(pb):
        e = phy_expr(b, ix)
        if e and re.match(r'(pc|ln)\d+_', e):
            u = re.match(r'((?:pc|ln)\d+)_', e).group(1)
            assert unit_seg[u] == seg_of(x), (fam, u, b, ix)
        if e in ('w_wv',) or (e or '').startswith(('w_addr', 'w_len', 'w_tag', 'w_rdy')):
            assert unit_seg['w'] == seg_of(x), (fam, b)
    clk_seg = seg_of(next(x for x, b, ix, d in pb if b == 'clk'))
    names = [f'hfd_svc_{fam}_s{j}' for j in range(len(segs))]
    port_map = {}                    # band -> {band port: (parent port, lo, hi)}
    recs = {}
    for j, (x0, x1) in enumerate(segs):
        w = round(x1 - x0, 4)
        ports, fc, pm = {}, {}, {}
        for n, p in P.items():
            if n == 'phy' or seg_of(p['pins'][0][2]) != j:
                continue
            if n in ('ck', 'rst'):
                bn = n
            elif n.startswith(('lsm', 'qsm')):
                bn = n[0] + str(rank['lsm' + n[3:]])
            else:
                bn = n
            v = json.loads(json.dumps(p))
            for q in v['pins']:
                q[0] = q[0].replace(n + '[', bn + '[', 1)
                q[2] = round(q[2] - x0, 4); q[4] = round(q[4] - x0, 4)
            ports[bn] = v
            pm[bn] = (n, 0, p['bits'] - 1)
            if n in fck:
                fc[bn] = {str(k): d for k, d in fck[n].items()}
        lo, hi = phy_rng[j]
        pp = json.loads(json.dumps(P['phy']))
        pins = sorted(pp['pins'], key=lambda q: int(re.search(r'\[(\d+)\]', q[0]).group(1)))[lo:hi + 1]
        for k, q in enumerate(pins):
            q[0] = f'phy[{k}]'; q[2] = round(q[2] - x0, 4); q[4] = round(q[4] - x0, 4)
        dirs = [('out' if pb[i][3] == 'input' else 'in') for i in range(lo, hi + 1)]
        dseg = []
        for k, d in enumerate(dirs):
            if dseg and dseg[-1][2] == d:
                dseg[-1][1] = k + 1
            else:
                dseg.append([k, k + 1, d])
        ports['phy'] = dict(bits=hi - lo + 1, layer=pp['layer'], pins=pins, face=pp['face'], dir_segments=dseg,
                            direction='inout' if len(dseg) > 1 else ('output' if dseg[0][2] == 'out' else 'input'))
        pm['phy'] = ('phy', lo, hi)
        if 'ck' not in ports:          # new die clock leaf / reset pins on the N face at a free spot near the middle
            occ = sorted((q[2], q[4]) for v in ports.values() for q in v['pins'] if v['face'] == 'N')
            xc = w / 2
            while any(a - 1.0 < xc < b + 1.0 or a - 1.0 < xc + 0.384 < b + 1.0 for a, b in occ):
                xc += 1.0
            xc = round(round(xc / 0.048) * 0.048, 4)
            for nm_, xx in (('ck', xc), ('rst', xc + 0.384)):
                ports[nm_] = dict(bits=1, layer='M5', pins=[[f'{nm_}[0]', 'M5', round(xx, 4), round(pl['H'] - 0.192, 4),
                                                             round(xx + 0.024, 4), pl['H']]],
                                  face='N', dir_segments=[[0, 1, 'in']], direction='input')
                pm[nm_] = ('<new>', 0, 0)
        for (cut, dirn), f in face.items():
            if cut not in (j - 1, j) or not f['bits']:
                continue
            east = cut == j
            nm_ = ('eo' if dirn == 'r' else 'ei') if east else ('wi' if dirn == 'r' else 'wo')
            xa_, xb_ = (w - 0.192, w) if east else (0.0, 0.192)
            pins_ = [[f'{nm_}[{k}]', 'M4', round(xa_, 4), round(f['y0'] + k * PITCH, 4), round(xb_, 4),
                      round(f['y0'] + k * PITCH + 0.024, 4)] for k in range(f['bits'])]
            d_ = 'out' if nm_ in ('eo', 'wo') else 'in'
            ports[nm_] = dict(bits=f['bits'], layer='M4', pins=pins_, face='E' if east else 'W',
                              dir_segments=[[0, f['bits'], d_]], direction='output' if d_ == 'out' else 'input')
        r = dict(master=names[j], kind='svc', w_um=w, h_um=pl['H'], obs_top=rec['obs_top'],
                 note=f"derived master: band x {x0} .. {x1} um of {FAM[fam]} (svc/gen_svc_seg.py)",
                 instances=len(FAM[fam]), orients=['R0', 'MX'], inst_names=[f'{FAM[fam][0]}_s{j}', f'{FAM[fam][1]}_s{j}'],
                 ports=ports, generator=rec['generator'], fclk=fc,
                 derived_from=dict(parent=FAM[fam], x0_um=x0, axis='x', spec='physical/hbm_accel_die_views/svc/gen_svc_seg.py',
                                   generator=rec['generator']))
        recs[names[j]] = r
        port_map[names[j]] = pm
    # ---------------------------------------------------------------- RTL per segment
    lib_units = {}
    for j in range(len(segs)):
        r = recs[names[j]]
        Lx = ['`timescale 1ps/1fs', '`default_nettype none',
              f'// GENERATED by physical/hbm_accel_die_views/svc/gen_svc_seg.py (CLAUDE HBM-ABSTRACTS svcidx): segment {j} of the',
              f'// {fam} stream-service family {FAM[fam]} (x {segs[j][0]} .. {segs[j][1]} um).  Units of ot_hbm_svc_seg_lib.sv,',
              '// wire-stage chain portions (ot_svc_vpipe, cross-face flops at both pins), own ck / rst synchroniser.',
              f'module {names[j]} (', V.svh(r).rstrip(), ');']
        A = Lx.append
        A('  wire c = ck[0]; wire rn, rdy_q, rdy_q2;')
        A('  ot_svs_rsync u_rs (.ck(c), .rst(rst[0]), .rn(rn));')
        A('  ot_svs_rdy u_rd (.ck(c), .rn(rn), .rdy_q(rdy_q), .rdy_q2(rdy_q2));')
        units = sorted(u for u, s in unit_seg.items() if s == j)
        lib_units[j] = units
        decl = []
        body = []
        for u in units:
            if u.startswith('sp'):
                k = int(u[2:]); fwd = g['fwd'][k]
                q = f'q{k}'
                decl.append(f'  wire sp{k}_iv, sp{k}_tk, sp{k}_qrdy; wire [41:0] sp{k}_id;')
                body.append(f'  ot_svs_smport #(.FWD({int(fwd)})) u_sp{k} (.ck(c), .rst(rst[0]), .rn(rn), .q_d({q}[42:1]), '
                            f'.q_v({q}[0]), .q_fclk({q + "[44]" if fwd else "1b0"}), .q_rdy(sp{k}_qrdy), .iv(sp{k}_iv), '
                            f'.id(sp{k}_id), .tk_back(sp{k}_tk));'.replace('1b0', "1'b0"))
                if not fwd:
                    body.append(f'  assign {q}[43] = sp{k}_qrdy;')
            elif u.startswith('as'):
                k = int(u[2:]); fwd = g['fwd'][k]
                decl.append(f'  wire [3:0] as{k}_sv, as{k}_kt; wire [1107:0] as{k}_sq; wire as{k}_wsv, as{k}_wt; '
                            f'wire [270:0] as{k}_wsq; wire [1098:0] as{k}_line;')
                if PS:
                    for jj in range(4):
                        pp = 4 * k + jj
                        decl.append(f'  wire rs{pp}_v; wire [276:0] rs{pp}_d;')
                        body.append(f"  assign as{k}_sv[{jj}] = rs{pp}_v && (rs{pp}_d[276:275] == 2'b00); "
                                    f"assign as{k}_sq[{jj*277+276}:{jj*277}] = rs{pp}_d;")
                body.append(f'  ot_svs_asm #(.SLOT({ASM_SLOT.get(names[j], 4)})) u_as{k} (.ck(c), .rn(rn), .sv(as{k}_sv), .sq(as{k}_sq), .wsv(as{k}_wsv), '
                            f'.wsq(as{k}_wsq), .k_take(as{k}_kt), .w_take(as{k}_wt), .line(as{k}_line));')
                if fwd:
                    body.append(f'  wire fck{k}; ot_svc_fclk_buf u_fc{k} (.a(c), .y(fck{k}));')
                    body.append(f'  assign l{k} = {{fck{k}, fck{k}, fck{k}, as{k}_line}};')
                else:
                    body.append(f'  assign l{k} = as{k}_line;')
            elif u.startswith('ar'):
                k = int(u[2:])
                kvi = pl['KV'] - 4 * k if pl['KV'] // 4 == k else -1
                iki = pl['IK'] - 4 * k if pl['IK'] // 4 == k else -1
                decl.append(f'  wire ar{k}_sv, ar{k}_take, ar{k}_kcv, ar{k}_kt, ar{k}_icv, ar{k}_it; wire [41:0] ar{k}_sd; '
                            f'wire [39:0] ar{k}_kcd, ar{k}_icd; wire [3:0] ar{k}_iv; wire [203:0] ar{k}_id;')
                dn = []
                for jj in range(4):
                    p = 4 * k + jj
                    t = f'dn{p}_o'
                    if p == pl['KV']:
                        t += ' | kvd_o'
                    if p == pl['IK']:
                        t += ' | ikd_o'
                    dn.append(t)
                    decl.append(f'  wire dn{p}_o;')
                if kvi >= 0:
                    decl.append('  wire kvd_o;')
                else:
                    body.append(f"  assign ar{k}_kcv = 1'b0; assign ar{k}_kcd = 40'd0;")
                if iki >= 0:
                    decl.append('  wire ikd_o;')
                else:
                    body.append(f"  assign ar{k}_icv = 1'b0; assign ar{k}_icd = 40'd0;")
                body.append(f'  ot_svs_arb #(.S({k}), .KVI({kvi}), .IKI({iki})) u_ar{k} (.ck(c), .rn(rn), .sv(ar{k}_sv), '
                            f'.sd(ar{k}_sd), .rq_take(ar{k}_take), .kvc_v(ar{k}_kcv), .kvc_d(ar{k}_kcd), .kv_take(ar{k}_kt), '
                            f'.ikc_v(ar{k}_icv), .ikc_d(ar{k}_icd), .ik_take(ar{k}_it), '
                            f".done({{{', '.join(reversed(dn))}}}), .iss_v(ar{k}_iv), .iss_d(ar{k}_id));")
            elif u.startswith('pc') and PS:
                p = int(u[2:])
                side = 'w' if p in pl['ps_lists']['w'] else 'e'
                Ls = pl['ps_lists'][side]
                end = int(Ls.index(p) == len(Ls) - 1)
                decl.append(f'  wire pc{p}_iv, pc{p}_k_v, pc{p}_k_rdy, pc{p}_kr_v, pc{p}_bv; wire [50:0] pc{p}_id; '
                            f'wire [29:0] pc{p}_k_addr; wire [3:0] pc{p}_k_len, pc{p}_kr_beat, pc{p}_bb; '
                            f'wire [16:0] pc{p}_k_tag, pc{p}_kr_tag, pc{p}_bt; wire [255:0] pc{p}_kr_data, pc{p}_bd; '
                            f'wire pc{p}_div, pc{p}_dov, pc{p}_dniok, pc{p}_dniph, pc{p}_dnook, pc{p}_dnoph, pc{p}_crv; '
                            f'wire [123:0] pc{p}_did, pc{p}_dod; wire [31:0] pc{p}_ici, pc{p}_ico;')
                if end:
                    body.append(f"  assign pc{p}_dniok = 1'b0; assign pc{p}_dniph = 1'b0; assign pc{p}_ici = 32'd0;   // chain end (END = 1)")
                body.append(f'  ot_svs_pcs #(.PCID({p}), .END({end})) u_pc{p} (.ck(c), .rn(rn), .rdy_q2(rdy_q2), .iss_v(pc{p}_iv), '
                            f'.iss_d(pc{p}_id), .k_v(pc{p}_k_v), .k_rdy(pc{p}_k_rdy), .k_addr(pc{p}_k_addr), .k_len(pc{p}_k_len), '
                            f'.k_tag(pc{p}_k_tag), .kr_v(pc{p}_kr_v), .kr_tag(pc{p}_kr_tag), .kr_beat(pc{p}_kr_beat), '
                            f'.kr_data(pc{p}_kr_data), .b_v(pc{p}_bv), .b_t(pc{p}_bt), .b_b(pc{p}_bb), .b_d(pc{p}_bd), '
                            f'.di_v(pc{p}_div), .di_d(pc{p}_did), .do_v(pc{p}_dov), .do_d(pc{p}_dod), .dni_ok(pc{p}_dniok), '
                            f'.dni_ph(pc{p}_dniph), .dno_ok(pc{p}_dnook), .dno_ph(pc{p}_dnoph), .ici(pc{p}_ici), .ico(pc{p}_ico), '
                            f'.cr_v(pc{p}_crv));')
            elif u.startswith('gp'):
                k = int(u[2:])
                decl.append(f'  wire [3:0] gp{k}_sv, gp{k}_cr; wire [1107:0] gp{k}_sq; wire gp{k}_ovf, gp{k}_sgv; wire [12:0] gp{k}_sgd;')
                for jj in range(4):
                    pp = 4 * k + jj
                    body.append(f"  assign gp{k}_sv[{jj}] = rs{pp}_v && (rs{pp}_d[276:275] == 2'b11); "
                                f"assign gp{k}_sq[{jj*277+276}:{jj*277}] = rs{pp}_d;")
                body.append(f'  ot_svs_grp #(.K({k})) u_gp{k} (.ck(c), .rst(rst[0]), .rn(rn), .sv(gp{k}_sv), .sq(gp{k}_sq), '
                            f'.kq(kq{k}), .sg_v(gp{k}_sgv), .sg_d(gp{k}_sgd), .cr(gp{k}_cr), .ks(ks{k}), .ovf(gp{k}_ovf));')
            elif u.startswith('pc'):
                p = int(u[2:])
                decl.append(f'  wire pc{p}_iv, pc{p}_k_v, pc{p}_k_rdy, pc{p}_kr_v, pc{p}_bv; wire [50:0] pc{p}_id; '
                            f'wire [29:0] pc{p}_k_addr; wire [3:0] pc{p}_k_len, pc{p}_kr_beat, pc{p}_bb; '
                            f'wire [16:0] pc{p}_k_tag, pc{p}_kr_tag, pc{p}_bt; wire [255:0] pc{p}_kr_data, pc{p}_bd;')
                body.append(f'  ot_svs_pc u_pc{p} (.ck(c), .rn(rn), .rdy_q2(rdy_q2), .iss_v(pc{p}_iv), .iss_d(pc{p}_id), '
                            f'.k_v(pc{p}_k_v), .k_rdy(pc{p}_k_rdy), .k_addr(pc{p}_k_addr), .k_len(pc{p}_k_len), '
                            f'.k_tag(pc{p}_k_tag), .kr_v(pc{p}_kr_v), .kr_tag(pc{p}_kr_tag), .kr_beat(pc{p}_kr_beat), '
                            f'.kr_data(pc{p}_kr_data), .b_v(pc{p}_bv), .b_t(pc{p}_bt), .b_b(pc{p}_bb), .b_d(pc{p}_bd));')
            elif u.startswith('ln'):
                l = int(u[2:])
                decl.append(f'  wire ln{l}_wr_v, ln{l}_w_room, ln{l}_v, ln{l}_rq; wire [9:0] ln{l}_wr_tag; '
                            f'wire [4:0] ln{l}_wr_beat; wire [255:0] ln{l}_wr_data; wire [270:0] ln{l}_d;')
                body.append(f'  ot_svs_lane u_ln{l} (.ck(c), .rn(rn), .rdy_q2(rdy_q2), .wr_v(ln{l}_wr_v), .wr_tag(ln{l}_wr_tag), '
                            f'.wr_beat(ln{l}_wr_beat), .wr_data(ln{l}_wr_data), .w_room(ln{l}_w_room), .o_v(ln{l}_v), '
                            f'.o_d(ln{l}_d), .room_q(ln{l}_rq));')
            elif u == 'w':
                decl.append('  wire w_cv, w_ct, w_wv, w_rdy_s; wire [39:0] w_cd; wire [7:0] w_room, w_ld; '
                            'wire [23:0] w_addr_s; wire [5:0] w_len_s; wire [9:0] w_tag_s;')
                body.append('  ot_svs_w u_w (.ck(c), .rn(rn), .cv(w_cv), .cd(w_cd), .c_take(w_ct), .room(w_room), '
                            '.lane_done(w_ld), .w_v(w_wv), .w_rdy(w_rdy_s), .w_addr(w_addr_s), .w_len(w_len_s), .w_tag(w_tag_s));')
            elif u == 'e' and PS:
                we, ee = int(not pl['ps_lists']['w']), int(not pl['ps_lists']['e'])
                decl.append('  wire e_ow, e_ok, e_oi, e_bw, e_bk, e_bi; wire [39:0] e_od; wire e_sdv; wire [61:0] e_sdd; '
                            'wire e_dwok, e_dwph, e_deok, e_deph, e_sgv; wire [12:0] e_sgd; wire [31:0] e_icw, e_ice; '
                            '')
                if we:
                    body.append("  assign e_dwok = 1'b0; assign e_dwph = 1'b0; assign e_icw = 32'd0;   // no PC west of the e port")
                if ee:
                    body.append("  assign e_deok = 1'b0; assign e_deph = 1'b0; assign e_ice = 32'd0;   // no PC east of the e port")
                body.append(f'  ot_svs_eps #(.WEMPTY({we}), .EEMPTY({ee})) u_e (.ck(c), .rst(rst[0]), .rn(rn), .e_d(e[127:0]), '
                            '.e_fclk(e[128]), .ow_v(e_ow), .ok_v(e_ok), .oi_v(e_oi), .o_d(e_od), .bw(e_bw), .bk(e_bk), .bi(e_bi), '
                            '.sd_v(e_sdv), .sd_d(e_sdd), .dw_ok(e_dwok), .dw_ph(e_dwph), .de_ok(e_deok), .de_ph(e_deph), .kd(kd), '
                            '.sg_v(e_sgv), .sg_d(e_sgd), .icw(e_icw), .ice(e_ice));')
            elif u == 'e':
                decl.append('  wire e_ow, e_ok, e_oi, e_bw, e_bk, e_bi; wire [39:0] e_od;')
                body.append('  ot_svs_e u_e (.ck(c), .rst(rst[0]), .rn(rn), .e_d(e[127:0]), .e_fclk(e[128]), .ow_v(e_ow), '
                            '.ok_v(e_ok), .oi_v(e_oi), .o_d(e_od), .bw(e_bw), .bk(e_bk), .bi(e_bi));')
            elif u in ('kv', 'ik'):
                decl.append(f'  wire {u}_sv, {u}_dn; wire [276:0] {u}_sq; wire [1037:0] {u}_kvo; wire [1023:0] {u}_iko;')
                body.append(f'  ot_svs_kvasm #(.KV({int(u == "kv")})) u_{u} (.ck(c), .rn(rn), .sv({u}_sv), .sq({u}_sq), '
                            f'.dn({u}_dn), .kv({u}_kvo), .ik({u}_iko));')
                body.append(f'  wire fck_{u}; ot_svc_fclk_buf u_fc_{u} (.a(c), .y(fck_{u}));')
                if u == 'kv':
                    body.append('  assign kv = {fck_kv, fck_kv, fck_kv, kv_kvo};')
                else:
                    body.append('  assign ik = {fck_ik, fck_ik, ik_iko};')
        if j == clk_seg:
            decl.append('  wire phy_clk, phy_rst_n; reg prst;')
            body.append('  ot_svc_fclk_buf u_phy_ck (.a(c), .y(phy_clk));')
            body.append("  always @(posedge c or negedge rn) if (!rn) prst <= 1'b0; else prst <= 1'b1;")
            body.append('  assign phy_rst_n = prst;')
        # chain portions
        for cc in C:
            for k_, po in enumerate(cc['portions']):
                if po['seg'] != j:
                    continue
                wb = cc['w']
                if po['A'][0] == 'u':
                    vin, din = cc['sv'], cc['sd']
                else:
                    f_ = face[(j - 1, 'r')] if cc['sb'] > cc['sa'] else face[(j, 'l')]
                    pn = 'wi' if cc['sb'] > cc['sa'] else 'ei'
                    o, n_ = f_['runs'][cc['name']]
                    vin, din = f'{pn}[{o}]', f'{pn}[{o + n_ - 1}:{o + 1}]'
                nm = f"{cc['name']}_{k_}"
                decl.append(f'  wire {nm}_v; wire [{wb - 1}:0] {nm}_d;')
                body.append(f"  ot_svc_vpipe #(.W({wb}), .N({po['N']})) {nm} (.ck(c), .rst_n(rn), .v({vin}), .d({din}), "
                            f".qv({nm}_v), .q({nm}_d));")
                if po['B'][0] == 'u' and cc['kind'] == 'ps_icr':     # credit masks count only while valid
                    body.append(f"  assign {cc['dd']} = {nm}_v ? {nm}_d : {wb}'d0;")
                elif po['B'][0] == 'u':
                    body.append(f"  assign {cc['dv']} = {nm}_v;")
                    if cc['dd']:
                        body.append(f"  assign {cc['dd']} = {nm}_d;")
                else:
                    f_ = face[(j, 'r')] if cc['sb'] > cc['sa'] else face[(j - 1, 'l')]
                    pn = 'eo' if cc['sb'] > cc['sa'] else 'wo'
                    o, n_ = f_['runs'][cc['name']]
                    body.append(f'  assign {pn}[{o + n_ - 1}:{o}] = {{{nm}_d, {nm}_v}};')
        # PHY bundle
        lo, hi = phy_rng[j]
        for i in range(lo, hi + 1):
            x, b, ix, d = pb[i]
            e_ = phy_expr(b, ix)
            if e_ is None:
                continue
            if d == 'input':
                body.append(f'  assign phy[{i - lo}] = {e_};')
            else:
                body.append(f'  assign {e_} = phy[{i - lo}];')
        Lx += decl + body + ['endmodule', '`default_nettype wire', '']
        (HERE / SEGD).mkdir(parents=True, exist_ok=True)
        (HERE / SEGD / f'{names[j]}.sv').write_text('\n'.join(Lx))
        # forwarded input clocks of this segment
        sdc, cl = [], []
        for bn, (pn, lo_, hi_) in port_map[names[j]].items():
            if bn.startswith('q') and g['fwd'][int(bn[1:])]:
                # 18:55 fix: SDC time unit is ps (core_clk -period 833): the forwarded clocks were 0.833 ps, and their
                # data bits were timed against vclk (v2 routes: -1006 ps).  Data in relative to its own forwarded clock.
                sdc.append(f'create_clock -name f{bn} -period 833 [get_ports {{{bn}[44]}}]'); cl.append(f'f{bn}')
                sdc.append(f'for {{set i 0}} {{$i < 44}} {{incr i}} {{ set_input_delay -clock f{bn} 166.6 [get_ports [format {{{bn}[%d]}} $i]] }}')
            if PS and bn.startswith('kq'):
                sdc.append(f'create_clock -name f{bn} -period 833 [get_ports {{{bn}[1]}}]'); cl.append(f'f{bn}')
                sdc.append(f'set_input_delay -clock f{bn} 166.6 [get_ports {{{bn}[0]}}]')
            if bn == 'e':
                sdc.append('create_clock -name fe -period 833 [get_ports {e[128]}]'); cl.append('fe')
                sdc.append('for {set i 0} {$i < 128} {incr i} { set_input_delay -clock fe 166.6 [get_ports [format {e[%d]} $i]] }')
        # DRIVE-1113 2026-10-08: forwarded-clock OUTPUT bits (fck<k> on l<k>[1101:1099], fck_kv on kv[1040:1038],
        # fck_ik on ik[1025:1024]) are clocks, not data: the receiver captures the line with them (its own fwd SDC).
        # The budget SDC put them under vclk output delays like data bits (hfd_svc_SW_s3: FF hold ck -> l4[1100]
        # -198 ps through the clock tree); exclude them from the data checks.
        fo = []
        for bn in port_map[names[j]]:
            if bn[0] == 'l' and bn[1:].isdigit() and g['fwd'][int(bn[1:])] and f'as{bn[1:]}' in units:
                fo += [f'{bn}[{i}]' for i in (1099, 1100, 1101)]
            elif bn == 'kv' and 'kv' in units:
                fo += [f'kv[{i}]' for i in (1038, 1039, 1040)]
            elif bn == 'ik' and 'ik' in units:
                fo += [f'ik[{i}]' for i in (1024, 1025)]
            elif PS and bn.startswith('ks'):
                fo += [f'{bn}[{i}]' for i in (1099, 1100, 1101)]
            elif PS and bn == 'kd':
                fo += ['kd[2]']
        if fo:
            sdc.append('set_false_path -to [get_ports -quiet {' + ' '.join(fo) + '}]')
        if PS:      # PS row / done outputs: the consistent die-link split (S = R = 254.7 ps) until the rebudget covers them
            for bn in port_map[names[j]]:
                if bn.startswith('ks'):
                    sdc.append(f'set_output_delay -clock vclk 254.7 [get_ports -quiet {{{bn}[*]}}]')
                    sdc.append(f'set_false_path -to [get_ports -quiet {{{bn}[1099] {bn}[1100] {bn}[1101]}}]')
                elif bn == 'kd':
                    sdc.append('set_output_delay -clock vclk 254.7 [get_ports -quiet {kd[0] kd[1]}]')
        if cl:
            sdc += ['set_clock_uncertainty -setup 60 [get_clocks {' + ' '.join(cl) + '}]',
                    'set_clock_uncertainty -hold 25 [get_clocks {' + ' '.join(cl) + '}]',
                    'set_clock_groups -asynchronous -group [get_clocks {core_clk vclk}] ' + ' '.join(f'-group [get_clocks {n}]' for n in cl)]
        if sdc:
            (HERE / SDCD).mkdir(exist_ok=True)
            (HERE / SDCD / f'{names[j]}_fwd.sdc').write_text(
                f'# {names[j]}: forwarded input clocks (two-clock FIFO writes, asynchronous to ck); forwarded-clock output bits\n' + '\n'.join(sdc) + '\n')
        # wire-stage endpoints (common/wire_stage_fence.tcl OT_WS_FILE), segment-local um
        x0 = segs[j][0]
        ws = [f'# {names[j]}: chain-portion endpoints (gen_svc_seg.py)']
        for cc in C:
            for k_, po in enumerate(cc['portions']):
                if po['seg'] != j:
                    continue
                A_, B_ = po['A'], po['B']
                ws.append(f"set ws_ab({cc['name']}_{k_}) {{{A_[1] - x0:.3f} {A_[2]:.3f} {B_[1] - x0:.3f} {B_[2]:.3f} "
                          f"{int(A_[0] == 'p')} {int(B_[0] == 'p')}}}")
        d_ = HERE / SPLD / names[j]
        d_.mkdir(parents=True, exist_ok=True)
        (d_ / 'ports.json').write_text(json.dumps(r, indent=0) + '\n')
        (d_ / 'io_place.tcl').write_text(V.io_tcl(r).replace("(tools/hbm_die_views.py ports",
                                                             "(svc/gen_svc_seg.py, derived master; generator"))
        (d_ / 'ws.tcl').write_text('\n'.join(ws) + '\n')
    # ---------------------------------------------------------------- joined tops (bench vehicles)
    for st in FAM[fam]:
        prec = V.master_record(st)
        for n_, (b_, d_) in PS_NEW.items():
            prec['ports'][n_] = dict(bits=b_, direction=d_)
        pg = json.loads((HERE / 'svc_geometry.json').read_text())[st]
        rk = {n: k for k, n in enumerate(pg['order'])}
        T = ['`default_nettype none', f'// GENERATED (gen_svc_seg.py): the {fam} segments joined with the ports of {st} (bench vehicle)',
             f'module {st}_seg (', V.svh(prec).rstrip(), ');']
        for jc in range(len(segs) - 1):
            for dirn in ('r', 'l'):
                f_ = face[(jc, dirn)]
                if f_['bits']:
                    T.append(f"  wire [{f_['bits'] - 1}:0] x{dirn}{jc};")
        for j in range(len(segs)):
            con = []
            for bn, (pn, lo_, hi_) in port_map[names[j]].items():
                if pn == '<new>':
                    con.append(f'.{bn}({bn})')
                elif bn == 'phy':
                    con.append(f'.phy(phy[{hi_}:{lo_}])')
                elif pn.startswith(('lsm', 'qsm')):
                    k = int(bn[1:])
                    pref = 'lsm' if bn[0] == 'l' else 'qsm'
                    pnm = pref + pg['order'][k][3:]
                    con.append(f'.{bn}({pnm})')
                else:
                    con.append(f'.{bn}({pn})')
            for (cut, dirn), f_ in face.items():
                if not f_['bits'] or cut not in (j - 1, j):
                    continue
                east = cut == j
                bn = ('eo' if dirn == 'r' else 'ei') if east else ('wi' if dirn == 'r' else 'wo')
                con.append(f'.{bn}(x{dirn}{cut})')
            T.append(f'  {names[j]} u_s{j} ({", ".join(con)});')
        T += ['endmodule', '`default_nettype wire', '']
        (HERE / SEGD / f'{st}_seg.sv').write_text('\n'.join(T))
    return names, recs, port_map, phy_rng


def ledger(pl):
    g = pl['g']
    st = {c['name']: c['stages'] for c in pl['C']}
    req, rsp, w = g['req_st'], g['rsp_st'], g['w_st']
    rows = {}
    for k in range(8):
        # K line: request chain + (arbiter issue register + issue chain) + response chain, vs the one-slot margin view
        new = max(st[f'c_rq{k}'] + 1 + st[f'c_is{p}'] + st[f'c_rs{p}'] for p in range(4 * k, 4 * k + 4))
        old = max((req[k] + XST) + (rsp[p] + XST) for p in range(4 * k, 4 * k + 4))
        rows[f'sm{k}_k_line'] = dict(new=new, old=old, added=new - old)
        rows[f'sm{k}_w_line'] = dict(new=st['c_ew'] + st[f'c_wl{k}'], old=(g['e_st'] + XST) + (w[k] + XST),
                                     added=st['c_ew'] + st[f'c_wl{k}'] - (g['e_st'] + XST) - (w[k] + XST))
    for nm, pc, st_ in (('kv', pl['KV'], g['kv_st']), ('ik', pl['IK'], g['ik_st'])):
        new = st[f'c_e{nm[0]}'] + 1 + st[f'c_is{pc}'] + st[f'c_{nm}r']
        old = (g['e_st'] + XST) + (st_ + XST)
        rows[f'{nm}_read'] = dict(new=new, old=old, added=new - old)
    return rows


def main():
    out = {}
    split = dict(schema='opentallas.hbm_die_split_x.v1', axis='x',
                 note='svc SEGMENT SPLIT (coordinator DECISION 2026-10-06): x-bands of the 8500 x 259 um service slot; '
                      'NW / NE reuse the SW / SE segment masters (identical pin plans, placed MX); band ports renamed by '
                      'core SM rank (l<k> = line, q<k> = request); phy split by bit range; every band gets its own die '
                      'clock leaf ck / reset rst (new N-face pins, except the band holding the parent ck / rst); cross '
                      'buses eo->wi (eastward) and wo->ei (westward) abut at the same y on the shared edge (M4, 0.096 um '
                      'pitch, zero-length die nets).', parents={}, bands={}, cross=[])
    for fam in ('SW', 'SE'):
        pl = plan_family(fam)
        names, recs, pm, rng = build(pl)
        for j, n in enumerate(names):
            split['bands'][n] = dict(x0_um=pl['segs'][j][0], w_um=recs[n]['w_um'], h_um=pl['H'],
                                     ports={k: dict(bits=v['bits'], direction=v['direction'], face=v['face']) for k, v in recs[n]['ports'].items()})
        for st in FAM[fam]:
            pg = json.loads((HERE / 'svc_geometry.json').read_text())[st]
            mp = {}
            for j, n in enumerate(names):
                for bn, (pn, lo, hi) in pm[n].items():
                    if pn.startswith(('lsm', 'qsm')):
                        pn = ('lsm' if bn[0] == 'l' else 'qsm') + pg['order'][int(bn[1:])][3:]
                    mp.setdefault(n, {})[bn] = dict(parent_port=pn, parent_bits=[lo, hi])
            split['parents'][st] = dict(bands=names, port_map=mp)
        for jc in range(len(pl['cuts'])):
            for dirn in ('r', 'l'):
                f_ = pl['face'][(jc, dirn)]
                if f_['bits']:
                    a, b = (names[jc], names[jc + 1]) if dirn == 'r' else (names[jc + 1], names[jc])
                    split['cross'].append(dict(family=fam, frm=f"{a}.{'eo' if dirn == 'r' else 'wo'}",
                                               to=f"{b}.{'wi' if dirn == 'r' else 'ei'}", bits=f_['bits'],
                                               chains=f_['names']))
        out[fam] = dict(cuts=pl['cuts'], segments=[dict(name=n, x0=pl['segs'][j][0], x1=pl['segs'][j][1],
                                                        units=sorted(u for u, (x, y) in pl['U'].items() if pl['seg_of'](x) == j))
                                                   for j, n in enumerate(names)],
                        chains={c['name']: dict(stages=c['stages'], portions=[(p['seg'], p['N'], p['d']) for p in c['portions']])
                                for c in pl['C']},
                        cross_bits={str(j): [pl['face'][(j, 'r')]['bits'], pl['face'][(j, 'l')]['bits']] for j in range(len(pl['cuts']))},
                        cycles=ledger(pl))
    (HERE / SPLD).mkdir(exist_ok=True)
    (HERE / SPLD / 'split.json').write_text(json.dumps(split, indent=1) + '\n')
    (HERE / STG).write_text(json.dumps(dict(hop_um=HOP, xst_ledger=XST, families=out), indent=1) + '\n')
    for fam, o in out.items():
        print(fam, 'cross bits (r,l):', o['cross_bits'])
        print(' cycles:', {k: v['added'] for k, v in o['cycles'].items()})


if __name__ == '__main__':
    main()
