#!/usr/bin/env python3
"""H-DIE 14:05 (2026-10-15): turn v5 WINDOW slots into REAL grants wherever the owner's current static RTL master exists.

Top-down pin assignment (owner 10-13): the die assigns every RTL port of an unclosed master / cluster parent to a face,
layer and exact span in the slot's R0 frame, at the contract pitch (0.096 um/bit, face cap 0.60), from the v5 pin
windows (peer direction) and the master's real port list (tools/hbm_die_views parse_module on the pinned source).

    rtl_pin_grants_1405.py --contract results/arch/hier_contract_1015/hbm_v15.json [--out same]

Granted here (cell + params + source sha + exact pins):
  su_<q><g>   ot_hbm_su_static_pgslice #(QID, G)   cluster; die-owned 40 um feedthrough relay column x=w/2 and row y=h/2
              (relay homes for band through-traffic, results/arch/hbm_die_v15/views_v5/relay_homes.json): no pin inside
  sucore_<q>  ot_hbm_su_static_qcore               RF write / reducer result pins at su_rf_route_pins.json (channel face)
  sm_<q><i>   ot_hbm_accel_smh_static              static SM successor (83-bit command, 1099 packet, no req/d ready);
              die-owned 40 um feedthrough column x=w/2 and row y=h/2 (754 SM crossings > 480 um)
  quant_NW<k> ot_hgi_qdq_lg_port_group #(BANKS=2)  LG port group at its bank pair (<=500 um fixed LG return), 108 x 103.68
              (= the gate-clean 259.2 x 43.2 kit area, re-aspected so the 555-bit VM face fits at <=0.6)
  quant_NW_xp wires-only cluster: ot_hgi_qdq_transport_ctl + 4 rslice + 4 wslice at their gate-clean kit outlines
              (word-sliced gather/scatter reads ALL 8 banks, so the transport cannot be split per bank pair)
NOT granted (no static master on main; stay window slots, reason recorded per slot): sfu_* (4 bank-pair SFU leaves),
hc_* / hc_eng (no static HC die master), ep_* (link-capture group composition), host_cp (child only).
"""
import argparse, hashlib, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_die_views as views  # noqa: E402

STEP, CAP = 0.096, 0.60
LAYER = dict(N='M5', S='M5', E='M4', W='M4')
QID = dict(SW=0, SE=1, NW=2, NE=3)
SRC = dict(
    pgslice='rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pgslice.sv',
    qcore='rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_qcore.sv',
    sm='rtl/hbm_accel/sm/static/ot_hbm_accel_smh_static.sv',
    lgpg='rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_lg_port_group.sv',
    xport='rtl/hbm_accel/generic/qw/static/ot_hgi_qdq_transport_split.sv')
TOP = dict(pgslice='ot_hbm_su_static_pgslice', qcore='ot_hbm_su_static_qcore', sm='ot_hbm_accel_smh_static',
           lgpg='ot_hgi_qdq_lg_port_group')
RFP = 'results/arch/hbm_die_v15/compact660_v5/su_rf_route_pins.json'
FT_W, FT_MARGIN = 40.0, 10.0


def git(ref, path):
    return subprocess.run(['git', '-C', str(ROOT), 'show', f'{ref}:{path}'], capture_output=True, check=True).stdout


def ports(key, params):
    P = views.L.parse_module(str(ROOT / SRC[key]), TOP[key], params)['ports']
    return {k: (d, b) for k, (d, b) in P.items()}


def opp(f):
    return dict(N='S', S='N', E='W', W='E')[f]


def place(L, items, forbid=()):
    """items: [(pin_name, bits, desired_centre)] -> {name: (lo, hi)}; no overlap, outside forbid, inside [2, L-2].
    Forward pass places each span at its desired centre or after the previous one; when the face end is crossed, a
    backward pass packs the tail leftwards (each span ends at or before the next one's start), so windows at the far
    end of a face stay as close to their peers as the face allows."""
    order = sorted(items, key=lambda t: t[2])

    def clear(lo, span, step):
        moved = True
        while moved:
            moved = False
            for a, b in forbid:
                if lo < b and lo + span > a:
                    lo, moved = (b if step > 0 else a - span), True
        return lo
    out, cur = {}, 2.0
    for name, bits, want in order:
        span = bits * STEP
        lo = clear(max(cur, want - span / 2), span, +1)
        out[name] = [lo, lo + span]
        cur = lo + span
    if cur > L - 2.0:
        lim = L - 2.0
        for name, bits, want in reversed(order):
            span = bits * STEP
            lo, hi = out[name]
            if hi > lim:
                lo = clear(lim - span, span, -1)
                out[name] = [lo, lo + span]
            lim = out[name][0]
        if min(v[0] for v in out.values()) < 2.0:
            raise SystemExit(f'face overflow: {sum(b for _, b, _ in items) * STEP:.2f} um of pins on a {L} um face')
    return {n: (round(lo, 3), round(hi, 3)) for n, (lo, hi) in out.items()}


def mkpins(outline, faces, forbid):
    """faces: {face: [(name, bits, want)]} -> pin list + per-face density"""
    pins, dens = [], {}
    for f, items in faces.items():
        if not items:
            continue
        L = outline['w'] if f in 'NS' else outline['h']
        got = place(L, items, forbid.get(f, ()))
        used = sum(b for _, b, _ in items) * STEP
        dens[f] = round(used / L, 4)
        assert dens[f] <= CAP, (f, dens[f])
        for n, (lo, hi) in got.items():
            pins.append(dict(name=n, face=f, layer=LAYER[f], offset=round((lo + hi) / 2, 3), span_um=[lo, hi],
                             offset_pending_view=False))
    return pins, dens


def rng(port, bits, lo=0):
    return port if bits == 1 and lo == 0 else f'{port}[{lo + bits - 1}:{lo}]'


def ft_forbid(o):
    """die-owned feedthrough column (x = w/2) and row (y = h/2), 40 um + 10 um margin each side"""
    cx, cy, h = o['w'] / 2, o['h'] / 2, FT_W / 2 + FT_MARGIN
    return dict(N=[(cx - h, cx + h)], S=[(cx - h, cx + h)], E=[(cy - h, cy + h)], W=[(cy - h, cy + h)])


def ft_record(o):
    return [dict(kind='feedthrough_relay_column', x_um=[o['w'] / 2 - FT_W / 2, o['w'] / 2 + FT_W / 2], y_um=[0, o['h']],
                 owner='die (relay stations hfd_stn_v15_cc2224/2248)', master_keepout='hard placement + M5/M6 route'),
            dict(kind='feedthrough_relay_row', x_um=[0, o['w']], y_um=[o['h'] / 2 - FT_W / 2, o['h'] / 2 + FT_W / 2],
                 owner='die (relay stations)', master_keepout='hard placement + M5/M6 route')]


def windows(s, cls):
    return [w for w in s.get('pin_windows', []) if w['cls'] == cls]


def common(s, key, cell, params, ref, sha, note):
    s.update(cell=cell, source=SRC[key], source_sha256=sha, source_prerequisite=ref, params=params, version=6,
             grant='real_rtl_pins_1405', pin_status='DIE_ASSIGNED_EXACT_FROM_RTL_PORTS (top-down; owner kit adopts '
             'unchanged, die re-pins only when die STA names the slot)', rtl_pin_grant_1405=True, notes=note)
    s.pop('rtl_pending', None)


def grant_su(s, P, q, g, ref, sha):
    o = s['outline']
    lg = windows(s, 'LG_SU')
    lgf = lg[0]['face']
    corex = 'E' if q in ('SW', 'NW') else 'W'       # sucore sits at the hub end of the slice row
    assert lgf != corex, (s['name'], lgf)
    bank_w = {}
    for w in lg:
        b = int(w['peer'][-1])                         # vmb_<q><b>: bank 2g or 2g+1
        bank_w[b - 2 * g] = w['offset']
    assert set(bank_w) == {0, 1}, (s['name'], bank_w)
    faces = {lgf: [], corex: [], 'N': []}
    per = dict(lg_rq=17, lg_wq=281, lg_rr=257, lg_w_done=1)
    for h in (0, 1):
        for p, b in per.items():
            assert P[p][1] == 2 * b
            faces[lgf].append((rng(p, b, h * b), b, bank_w[h]))
    mid = o['h'] / 2
    core = ['rf_bword', 'rf_bcmd', 'rf_dsec', 'red_sel', 'slice_x', 'fault']
    cmd = ['control', 'vmr_cmd', 'vmw_cmd']
    for p in core:
        faces[corex].append((rng(p, P[p][1]), P[p][1], mid + 60))
    for p in cmd:
        faces[corex].append((rng(p, P[p][1]), P[p][1], mid - 260))
    clocks = [p for p in P if p.startswith(('clk', 'pg_clk', 'rst'))]
    for p in clocks:
        faces['N'].append((rng(p, P[p][1]), P[p][1], o['w'] / 2 + 80))
    assert set(per) | set(core) | set(cmd) | set(clocks) == set(P), set(P) - (set(per) | set(core) | set(cmd) | set(clocks))
    pins, dens = mkpins(o, faces, ft_forbid(o))
    common(s, 'pgslice', TOP['pgslice'], dict(QID=QID[q], G=g, READ_RETURN=10, WRITE_RETURN=7), ref, sha,
           f'SU port-group slice G={g} of quarter {q} (banks {2*g},{2*g+1}); LG ports on {lgf} at the bank windows, '
           f'core/command ports on {corex} (toward sucore_{q}), {len(clocks)} clock/reset ports ({sum(P[p][1] for p in clocks)} '
           'bits: per-lane/bank/macro roots) on N M5; die feedthrough column+row reserved (no master cells/pins there)')
    s.update(pins=pins, face_density=dens, reserved_channels=ft_record(o),
             clock_entry=dict(pin='pg_clk', face='N', layer='M5',
                              offset=next(p['offset'] for p in pins if p['name'] == 'pg_clk')))
    return sum(P[p][1] for p in P)


def grant_core(s, P, q, rf, ref, sha):
    o = s['outline']
    slicef = 'W' if q in ('SW', 'NW') else 'E'
    chan = opp(slicef)
    y0 = s['origin']['y']
    src = [r['src_pin']['xy'][1] - y0 for r in rf['routes'] if r['src_pin']['block'] == s['name']]
    dst = [r['dst_pin']['xy'][1] - y0 for r in rf['routes'] if r['dst_pin']['block'] == s['name']]
    faces = {slicef: [], chan: [], 'N': []}
    for p in ('rf_bword', 'rf_bcmd', 'rf_dsec', 'slice_x', 'rf_drain_now'):
        faces[slicef].append((rng(p, P[p][1]), P[p][1], o['h'] / 2 - 200))
    for p in ('rf_wv', 'rf_wa', 'rf_wd'):
        faces[chan].append((rng(p, P[p][1]), P[p][1], sum(dst) / len(dst)))
    for p in ('red_sv', 'red_tag', 'red_x'):
        faces[chan].append((rng(p, P[p][1]), P[p][1], sum(src) / len(src)))
    for p in ('rf_rd_cmd', 'red_cmd', 'fault'):
        faces[slicef].append((rng(p, P[p][1]), P[p][1], o['h'] / 2 + 200))
    clocks = [p for p in P if p.startswith(('clk', 'rst'))]
    for p in clocks:
        faces['N'].append((rng(p, P[p][1]), P[p][1], o['w'] / 2))
    done = {n.split('[')[0] for f in faces.values() for n, _, _ in f}
    assert done == set(P), set(P) - done
    # keep the reducer child (17.28, 21.6) 216 x 151.2 clear of nothing: pins are on the parent boundary only
    pins, dens = mkpins(o, faces, {})
    common(s, 'qcore', TOP['qcore'], {}, ref, sha,
           f'SU quarter core {q}: slice-facing RF broadcast/drain + command ports on {slicef}, RF write (rf_w*) and reducer '
           f'result (red_*) on the channel face {chan} at su_rf_route_pins.json (RF_RELAY 36 at 480 um), 66 clock/reset '
           'ports on N; reducer child grant sucore_<q>_reducer unchanged')
    s.update(pins=pins, face_density=dens, clock_entry=dict(pin='clk_ctl', face='N', layer='M5',
             offset=next(p['offset'] for p in pins if p['name'] == 'clk_ctl')))


def grant_sm(s, P, ref, sha):
    o = s['outline']
    hbm = windows(s, 'SM_HBM')[0]
    xs = sorted(windows(s, 'SM_X'), key=lambda w: int(w['peer'][-1]))
    out = windows(s, 'SM_OUT')[0]
    kv = windows(s, 'KV_DESC')[0]
    hf = hbm['face']
    faces = {f: [] for f in 'NSEW'}
    assert len(xs) == 8, (s['name'], len(xs))
    faces[hf] += [('packet[1098:0]', 1099, hbm['offset']), ('expected_request[42:0]', 43, hbm['offset'] + 120)]
    # bank b's 256-bit word at ITS SM_X window (the windows may sit on two faces: the SM spans the band)
    for b, w in enumerate(xs):
        faces[w['face']].append((f'xw_data[{256*b+255}:{256*b}]', 256, w['offset']))
    xf = xs[0]['face']
    faces[xf] += [('xw_en', 1, xs[0]['offset'] - 30), ('xw_addr[6:0]', 7, xs[0]['offset'] - 29),
                  ('xw_grp[6:0]', 7, xs[0]['offset'] - 28)]
    faces[out['face']] += [('rv', 1, out['offset'] - 14), ('rrow[11:0]', 12, out['offset'] - 13),
                           ('rdata[255:0]', 256, out['offset']), ('fault', 1, out['offset'] + 14),
                           ('schedule_fault', 1, out['offset'] + 15)]
    faces[kv['face']] += [('command[82:0]', 83, kv['offset'] - 40), ('cg_en', 1, kv['offset'] - 35)]
    fl = o['w'] if hf in 'NS' else o['h']
    faces[hf] += [('clk', 1, fl / 2 + 80), ('rst_n', 1, fl / 2 + 81)]
    faces = {f: v for f, v in faces.items() if v}
    got = {n.split('[')[0] for f in faces.values() for n, _, _ in f}
    assert got == set(P), set(P) ^ got
    pins, dens = mkpins(o, faces, ft_forbid(o))
    common(s, 'sm', TOP['sm'], {}, ref, sha,
           'static SM successor ot_hbm_accel_smh_static (compiler 83-bit command + 1099-bit packet, no req/d ready); '
           f'packet/expected_request at the PC (SM_HBM {hf}), xw_data bank b at its SM_X window, results at SM_OUT, '
           'command at the KV_DESC/VM-hub window; die feedthrough column+row reserved. Attention ports (KV_DESC 64 b, '
           'ot_hbm_accel_smh_attn) re-pin on landing in main.')
    s.update(pins=pins, face_density=dens, clock_entry=dict(pin='clk', face=hf, layer='M5',
             offset=next(p['offset'] for p in pins if p['name'] == 'clk')), reserved_channels=ft_record(o))


def grant_quant(c, S, ref, sha_lg, sha_x):
    """4 LG port groups at the NW bank pairs + one transport cluster below bank pair 2/3 of NW (vmb_NW2/3 column)."""
    P = ports('lgpg', dict(BANKS=2))
    # 1,110 bits per side (2 banks x (17 + 257 + 281)) need >= 1110 x 0.096 / 0.60 = 177.6 um of face: VM side on the
    # bank-facing face, engine side on the opposite face, 64.8 x 194.4 (12,597 um2 ~ the gate-clean 259.2 x 43.2 kit)
    LG = dict(w=64.8, h=194.4)
    new = []
    for k in range(4):
        s = S[f'quant_NW{k}']
        vm = windows(s, 'QUANT_VM')
        vf = vm[0]['face']
        assert vf in 'EW', (s['name'], vf)
        ef = opp(vf)
        faces = {vf: [], ef: [], 'N': []}
        for p in ('rq_o', 'wq_o', 'rr_i'):
            faces[vf].append((rng(p, P[p][1]), P[p][1], LG['h'] / 2))
        for p in ('rq_i', 'wq_i', 'rr_o'):
            faces[ef].append((rng(p, P[p][1]), P[p][1], LG['h'] / 2))
        faces['N'] += [('clk', 1, LG['w'] / 2), ('rst_n', 1, LG['w'] / 2 + 1)]
        got = {n.split('[')[0] for f in faces.values() for n, _, _ in f}
        assert got == set(P), set(P) ^ got
        pins, dens = mkpins(LG, faces, {})
        po = s['outline']
        x = po['w'] - LG['w'] - 10.8 if vf == 'E' else 10.8
        new.append(dict(name=f'quant_NW{k}_lg', cell='ot_hgi_qdq_lg_port_group', source=SRC['lgpg'],
                        source_sha256=sha_lg, source_prerequisite=ref, params=dict(BANKS=2), kind='tile',
                        parent=s['name'], outline=LG, origin=dict(x=round(x, 3), y=round((po['h'] - LG['h']) / 2, 3),
                                                                  orient='R0'),
                        clock_entry=dict(pin='clk', face='N', layer='M5', offset=next(p['offset'] for p in pins
                                                                                      if p['name'] == 'clk')),
                        pins=pins, face_density=dens, pg_layer='M5', strap_layer='M6', signal_max_layer='M5',
                        layer_cap='M5', layer_rule='tile', io_budget=dict(in_delay_frac=.2, out_delay_frac=.2),
                        version=6, grant='real_rtl_pins_1405', rtl_pin_grant_1405=True,
                        kit='physical/ref_tile/hgi_qdq_lg_pg2 (gate-clean 566cdaf37 at 259.2x43.2; re-kit at 64.8x194.4, '
                            '~same area, these pins: 1,110 bits a side need 177.6 um of face at 0.60)',
                        notes=f'QUANT LG port group for NW banks {2*k},{2*k+1}: VM ports on {vf} (fixed LG return local), '
                              'engine-side rq_i/wq_i/rr_o on the opposite face toward the transport cluster'))
        s.update(kind='cluster', cell=None, layer_rule='cluster', pg_layer='M7', strap_layer='M8', signal_max_layer='M6',
                 layer_cap='M6', version=6, grant='wires_only_cluster_1405', rtl_pin_grant_1405=True,
                 notes='wires-only QUANT bank-pair group: child quant_NW%d_lg is the only cell' % k)
        s.pop('rtl_pending', None)
    # transport cluster: free 849.5 x 681 um below vmb_NW3 (x 3299.5, y 14395..15076, compact660_v5) = bank-pair-1
    # column, nearest the centre of the four NW pairs (max LG-group distance ~4.0 mm vs 5.6 mm at pair 2)
    kids = [('ctl', 'ot_hgi_qdq_transport_ctl', (86.4, 86.4), dict(RL=9, DL=25, WC=5, MUT=0), [(21.6, 21.6)]),
            ('rslice', 'ot_hgi_qdq_transport_rslice', (129.6, 86.4), dict(NW=2, MUT=0),
             [(129.6 + 21.6 * 2 + i * (129.6 + 21.6), 21.6) for i in range(4)]),
            ('wslice', 'ot_hgi_qdq_transport_wslice', (86.4, 43.2), dict(NW=2, MUT=0),
             [(129.6 + 21.6 * 2 + i * (129.6 + 21.6), 21.6 + 86.4 + 21.6) for i in range(4)])]
    W = round(129.6 + 21.6 * 2 + 4 * (129.6 + 21.6) + 21.6 - 21.6, 3)
    H = 21.6 + 86.4 + 21.6 + 43.2 + 21.6
    X0 = dict(x=3299.5 + 40.0, y=14395.133 + 120.0)
    par = dict(name='quant_NW_xp', cell=None, kind='cluster', parent='die', outline=dict(w=round(W, 3), h=round(H, 3)),
               origin=dict(x=X0['x'], y=X0['y'], orient='R0'), layer_rule='cluster', pg_layer='M7', strap_layer='M8',
               signal_max_layer='M6', layer_cap='M6', version=6, grant='wires_only_cluster_1405',
               rtl_pin_grant_1405=True, source=SRC['xport'], source_sha256=sha_x, source_prerequisite=ref,
               notes='QUANT transport (ot_hgi_qdq_static_transport_split, IO_REGS=1, wires-only parent): ctl + 4 word '
                     'slices; each word slice gathers from ALL 8 NW banks, so it stays one compact group. LG groups '
                     '-> here are feed-forward fixed-latency (compiler RL/WC) paths, up to ~4.0 mm = 9 relay stages at '
                     '480 um: H-ATTQ to measure RL/WC with these distances (cost to ledger).',
               hierarchy_gap='die contract instance hb_quant_NW = ot_hgi_qdq_host_static #(RL7,WC4,COMPACT1) has neither '
                             'TSPLIT nor LG port groups; these leaves come from ot_hgi_qdq_program_static #(TSPLIT,LG): '
                             'H-ATTQ to make the die master instantiate them (no stub)')
    new.append(par)
    for role, cell, (w, h), prm, homes in kids:
        spec = json.loads(git(ref, f'physical/ref_tile/hgi_qdq_tsplit_{role}/spec.json'))
        assert spec['top'] == cell and abs(spec['outline']['w'] - w) < 1e-6 and abs(spec['outline']['h'] - h) < 1e-6
        for i, (x, y) in enumerate(homes):
            assert x + w <= W + 1e-6 and y + h <= H + 1e-6, (role, x, y, W, H)
            new.append(dict(name=f'quant_NW_xp_{role}{i if len(homes) > 1 else ""}', cell=cell, source=SRC['xport'],
                            source_sha256=sha_x, source_prerequisite=ref, params=prm, kind='tile', parent='quant_NW_xp',
                            outline=dict(w=w, h=h), origin=dict(x=round(x, 3), y=round(y, 3), orient='R0'),
                            clock_entry=dict(pin='clk', face='W', layer='M4'), kit_pins_by_face=spec['pins'],
                            kit=f'physical/ref_tile/hgi_qdq_tsplit_{role} (gate-clean 566cdaf37, outline unchanged)',
                            pg_layer='M5', strap_layer='M6', signal_max_layer='M5', layer_cap='M5', layer_rule='tile',
                            io_budget=dict(in_delay_frac=.2, out_delay_frac=.2), version=6, grant='real_kit_slot_1405',
                            rtl_pin_grant_1405=True,
                            notes='kit outline + kit face assignment adopted unchanged (gate-clean); slot is the home'))
    return new


LINK_SRC = 'rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv'
LINK_LEF = 'physical/asap7_v41x_pdie_macros_v2/{m}/{m}.lef'


def grant_links(S, ref, sha):
    """lk_* (ot_pdie_serdes) and host_N (ot_pdie_ucie): the real digital link layers (KP4 FEC / UCIe rate matcher,
    rtl/dsrom_sys/s81_link) over the behavioural PMA = the allowed modelled analog core.  Outline = the macro LEF."""
    import re
    n = 0
    for s in S.values():
        if s.get('cell') not in ('ot_pdie_serdes', 'ot_pdie_ucie'):
            continue
        lef = LINK_LEF.format(m=s['cell'])
        w, h = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', (ROOT / lef).read_text()).groups())
        s.update(outline=dict(w=w, h=h), source=LINK_SRC, source_sha256=sha, source_prerequisite=ref, params={},
                 view=lef.rsplit('/', 1)[0], version=6, grant='hard_macro_real_rtl_1405', rtl_pin_grant_1405=True,
                 pin_status='MACRO_LEF_PINS (the macro abstract fixes its pins)')
        s.pop('rtl_pending', None)
        n += 1
    return n


def overlaps(slots):
    die = [s for s in slots if s.get('parent') in ('die', None) and s.get('origin') and s.get('kind') != 'die']
    bad = []
    for i, a in enumerate(die):
        for b in die[i + 1:]:
            ax, ay, bx, by = a['origin']['x'], a['origin']['y'], b['origin']['x'], b['origin']['y']
            if ax < bx + b['outline']['w'] and bx < ax + a['outline']['w'] and ay < by + b['outline']['h'] and \
                    by < ay + a['outline']['h']:
                bad.append((a['name'], b['name']))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--contract', type=Path, default=ROOT / 'results/arch/hier_contract_1015/hbm_v15.json')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--ref', default='HEAD')
    a = ap.parse_args()
    ref = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short=9', a.ref], capture_output=True, text=True,
                         check=True).stdout.strip()
    c = json.loads(a.contract.read_text())
    before = overlaps(c['slots'])
    c['slots'] = [s for s in c['slots'] if not (s.get('rtl_pin_grant_1405') and s.get('parent', '').startswith('quant'))]
    S = {s['name']: s for s in c['slots']}
    sha = {k: hashlib.sha256(git(ref, p)).hexdigest() for k, p in SRC.items()}
    rf = json.loads((ROOT / RFP).read_text())
    rep = dict(su=0, sucore=0, sm=0, quant_lg=0, quant_xp_leaves=0)
    for q in QID:
        for g in range(4):
            grant_su(S[f'su_{q}{g}'], ports('pgslice', dict(QID=QID[q], G=g)), q, g, ref, sha['pgslice'])
            rep['su'] += 1
        grant_core(S[f'sucore_{q}'], ports('qcore', {}), q, rf, ref, sha['qcore'])
        rep['sucore'] += 1
        for i in range(8):
            grant_sm(S[f'sm_{q}{i}'], ports('sm', {}), ref, sha['sm'])
            rep['sm'] += 1
    rep['links'] = grant_links(S, ref, hashlib.sha256(git(ref, LINK_SRC)).hexdigest())
    new = grant_quant(c, S, ref, sha['lgpg'], sha['xport'])
    rep['quant_lg'] = sum(1 for s in new if s['name'].endswith('_lg'))
    rep['quant_xp_leaves'] = sum(1 for s in new if s.get('parent') == 'quant_NW_xp')
    c['slots'] += new
    after = overlaps(c['slots'])
    assert set(after) <= set(before), set(after) - set(before)
    still = {}
    for s in c['slots']:
        if s.get('grant') == 'window':
            k = s['name'].rstrip('0123456789').split('_')[0]
            still.setdefault(k, []).append(s['name'])
    reasons = dict(sfu='no 4-leaf bank-pair SFU master on main (die instance is one ot_hgi_sfu_scheduled_engine per '
                       'quadrant; ot_hgi_sfu_static_quarter is the whole arithmetic, not a bank-pair leaf): H-ELEM-B',
                   hc='no static HC die master on main (static_hc has bank shell / weight quarter / residual leaves, no '
                      'HC tile/engine top): HC owner to be assigned by coordinator',
                   ep='endpoint = ot_hgi_coll_static_link_capture group; group composition (rails per lk) not in RTL: '
                      'H-COLL',
                   host='host_cp static ingress child granted 1319 (98ca51cf9); parent loader RTL pending')
    c['rtl_pin_grants_1405'] = dict(ref=ref, counts=rep, step_um_per_bit=STEP, face_cap=CAP,
                                    feedthrough=dict(width_um=FT_W, pin_margin_um=FT_MARGIN, on=['su_*', 'sm_*']),
                                    source_sha256=sha, still_window={k: len(v) for k, v in still.items()},
                                    still_window_reason=reasons, new_overlaps=0)
    c['version'] = 6
    c['updated'] = subprocess.run(['date', '-Iseconds'], capture_output=True, text=True).stdout.strip()
    (a.out or a.contract).write_text(json.dumps(c, indent=1) + '\n')
    print(json.dumps(c['rtl_pin_grants_1405'], indent=1))


if __name__ == '__main__':
    main()
