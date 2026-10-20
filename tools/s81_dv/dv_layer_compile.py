#!/usr/bin/env python3
"""LAYERBENCH-S81 (10-18): the S81-DV layer-programme compiler (TOK.DS.BENCH.1).

Lowers one representative layer of the DeepSeek-V4.1 token path onto the p4l DV die (bind9 netlist of the die of record,
results/fleet_viz/die_sources.json -> origin/claude/s81-die6-1018) and emits the images the die would load plus the
static schedule a slice bench replays / asserts:

  DIR/prog/host_boot.memh   host-lane words in host-slot order, the format dsdv_seq_host L0 intercepts (515 b =
                            {type 2, x 512, v}; CSR class 0: 0x11 length, 0x10 calendar PW words, 0x13 CTL templates,
                            0x14 gunit rows) -- the exact packing of rtl/dsrom_sys/s81_dv/unit/test/tb_dsdv_seq_host.sv
  DIR/prog/calendar.json    ot_dsdv_fixed_issue rows {done 24, issue 24, engine 4, arg 24} (+ KIT / END rows)
  DIR/prog/ctl_templates.json   CTL template table (186-b payload {body 160, leaf mask 5, target 5, slice mask 16})
  DIR/prog/gunit_rows.json  0x14 boot rows (cw a / d)
  DIR/prog/frame_cfg7/<die frame inst>.json   frame programme placement record (+ memh banks when lowered)
  DIR/prog/svc_jobs.json    svc_rs jobs (engine 4)
  DIR/schedule.json         op-level static schedule (the priced p4l solve, rebased to the layer entry) + every lowered
                            event at a die instance boundary port {cycle, inst, port, dir, kind, tag, payload}
  DIR/lowering.json         per op: unit, status (LOWERED / PARTIAL / GAP) and the precise gap (module, port, missing)
  DIR/manifest.json         sha256 of every emitted file + the source pins (die ref sha, die.v sha, land plan sha)

Instance names are the bind9 die.v instance names (u_s_0S, u_f_0L00, u_seqhost, u_gunit, ...); link ages come from the
die.v relay stations (st_<link>_<i>, half-cycle dsfd_dvrlyh_*) and landings (ld_<link>, K strap) with the p4l land plan
E (ot_s81_land: last station -> o = E + 1 edges).  Every encoding is the one a committed unit bench already proves (the
docstring of each encoder names the bench).  Nothing here is a measurement: schedule cycles are the compiler's static
plan; the slice bench asserts them on the real RTL.

  dv_layer_compile.py --layer L0 --out DIR [--slice s_0S] [--smoke] [--die-src DIR | --die-ref REF]
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))

DIE_REF = 'origin/claude/s81-die6-1018'
DIE_PATHS = ['results/arch/s81_dv_1016/bind9', 'results/arch/s81_dv_1016/p4l', 'results/arch/s81_dv_1016/landing/p4l',
             'tools/s81_dv', 'rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host.sv', 'rtl/dsrom_sys/s81_dv/unit/ot_dsdv_fixed_issue.sv',
             'rtl/dsrom_sys/s81_dv/slice', 'rtl/dsrom_sys/s81_dv/unit/dsdv_gunit.sv']
LAYERS = {'L0': 0, 'L2': 2, 'L14': 14, 'L20': 20}
SPECIAL = ('mtp_draft', 'head')

# ------------------------------------------------------------------------------------------------ fixed unit latencies
# dsdv_seq_host header (asserted by tb_dsdv_seq_host): f_ks captured at t -> issuer samples job_v at t + 3 -> command of
# calendar age a leaves the issuer register at t + 4 + a; V command register -> vo pin + 7; svc command -> s_j + 2;
# gunit job -> cw pin + 3; issuer KIT -> t_kd pin + 3.  Calendar done rows: V / gunit = issue + 5 (posted).
SEQ = dict(fks_to_job=3, job_to_age0=4, v_cmd_to_vo=7, svc_to_sj=2, gunit_to_cw=3, kit_to_tkd=3, done_v=5)
# ot_s81sl_rstop: line in pin -> line out pin 2 edges a stop.
RSTOP_HOP = 2
# tb_s81sl_beat (results/rtl/s81_slice_1017/beat/bt_base: SLBEAT go_to_partial=111 rstd_to_y0=18 rstd_to_xq=47, PASS);
# the bench's proven command spacing HLOAD -> GAIN 40, GAIN -> NORM 20 (the compiler keeps the proven slots).
BEAT = dict(go_to_partial=111, rstd_to_y0=18, rstd_to_xq=47, hload_slot=40, gain_slot=20)
# dv_price.py (S81-DV measured): beat partial -> xfin DL 4 + collector 5; xfin last partial -> rstd 234 (tb_s81dv_xfin16);
# rstd -> XQ complete at the ring stop 59 + 4 * 4 (last leaf) + DL 4.
XFIN = dict(dl=4, collector=5, last_partial_to_rstd=234, rstd_to_xq_ring=59 + 16 + 4)
HOST_SLOT = 5            # tb_dsdv_seq_host: one host word every 5th edge (the compiler's host slots)
NOPS = 128               # ot_dsdv_fixed_issue calendar rows per job (NOPS <= 128) and CTL templates (128 x 186 b)
ENG = dict(VN=0, VS=1, GUNIT=2, SVC=4, KIT=14, END=15)


# ================================================================================================= die source of record
def die_tree(ref=DIE_REF, src=None, cache=None):
    """an extracted copy of the die ref's netlist, plans and unit contracts (never committed here)"""
    if src:
        return Path(src)
    sha = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', ref], text=True).strip()
    d = Path(cache or (Path.home() / 'scratch/layerbench-s81/dieref')) / sha[:12]
    if not (d / '.done').exists():
        d.mkdir(parents=True, exist_ok=True)
        ar = subprocess.run(['git', '-C', str(ROOT), 'archive', sha] + DIE_PATHS, check=True, capture_output=True).stdout
        subprocess.run(['tar', '-x', '-C', str(d)], input=ar, check=True)
        (d / '.done').write_text(sha + '\n')
    return d


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ================================================================================================= die netlist model
INST_RE = re.compile(r'^\s*(\w+)\s+(?:#\((.*?)\)\s+)?(\w+)\s*\((.*)\);\s*(?://.*)?$')
CONN_RE = re.compile(r'\.(\w+)\(\{?([^(){}]*(?:\{[^{}]*\})?[^(){}]*)\}?\)')


class Die:
    """bind9 die.v: instances (master, params, port expressions, straps) and the relay / landing links"""

    def __init__(self, tree):
        self.tree = Path(tree)
        b = self.tree / 'results/arch/s81_dv_1016/bind9'
        raw = gzip.decompress((b / 'die.v.gz').read_bytes()).decode()
        self.die_sha = hashlib.sha256(raw.encode()).hexdigest()
        self.inst = {}
        for line in raw.splitlines():
            m = INST_RE.match(line)
            if not m or m.group(1) in ('module', 'wire', 'input', 'output', 'assign', 'reg'):
                continue
            master, params, name, body = m.groups()
            conns = {}
            for c in CONN_RE.finditer(body):
                conns[c.group(1)] = c.group(2).strip()
            self.inst[name] = dict(master=master, params=params or '', conns=conns)
        self.plan = json.loads((self.tree / 'results/arch/s81_dv_1016/p4l/plan.json').read_text())
        self.land = json.loads((self.tree / 'results/arch/s81_dv_1016/landing/p4l/land_plan.json').read_text())
        self.E = {l['link']: l for l in self.land['links']}
        self.blocks = {b_['name']: b_ for b_ in self.plan['blocks']}
        self._links()

    def strap(self, inst, port):
        v = self.inst[inst]['conns'].get(port)
        m = re.fullmatch(r"(\d+)'[dh]([0-9a-fA-F]+)", v or '')
        if not m:
            return None
        return int(m.group(2), 16 if "'h" in v else 10)

    def _links(self):
        st, ld = {}, {}
        for n, i in self.inst.items():
            m = re.fullmatch(r'st_(.+)_(\d+)', n)
            if m and i['master'].startswith('dsfd_dvrlyh'):
                st.setdefault(m.group(1), []).append(int(m.group(2)))
            m = re.fullmatch(r'ld_(.+)', n)
            if m and i['master'].startswith('dsfd_dvland'):
                ld[m.group(1)] = n
        # endpoints: the instance whose port expression names w_<link>_src (source) and w_<link>_lnd / _dst (sink)
        users = {}
        for n, i in self.inst.items():
            if n.startswith(('st_', 'ld_', 'fwd_')):
                continue
            for p, e in i['conns'].items():
                for w in re.findall(r'\bw_(\w+?)_(src|lnd|dst)\b', e):
                    users.setdefault(w, []).append((n, p))
        self.links = {}
        for lk in set(st) | set(ld):
            src = [u for u in users.get((lk, 'src'), [])]
            dst = [u for u in users.get((lk, 'lnd'), []) + users.get((lk, 'dst'), [])]
            k = self.strap(ld[lk], 'k') if lk in ld else None
            e = self.E.get(lk, {}).get('E')
            n = len(st.get(lk, []))
            # half-cycle stations: one T/2 each; landing: last station -> o = K + 1 edges (ot_s81_land contract, gate
            # calendar R0 = G + N mod 2).  S81-LBGAP/G8: the die.v K strap (bundle age), E only when no strap is bound
            age = (math.ceil(n / 2) + (k if k is not None else e) + 1) if lk in ld else n / 2
            self.links[lk] = dict(stations=n, landing=ld.get(lk), K=k, E=e, src=src, dst=dst, age_edges=age,
                                  land_master=self.inst[ld[lk]]['master'] if lk in ld else None)

    def unlanded(self):
        """land-plan lanes (an E is planned) that bind9 die.v leaves WITHOUT a landing tile; x_frame lanes land inside
        the frame _l4 successors (lk strap) and are excluded"""
        out = []
        for l in self.land['links']:
            L = self.links.get(l['link'])
            if l['cls'] != 'x_frame' and (L is None or L['landing'] is None):
                out.append(dict(link=l['link'], cls=l['cls'], dst=l['dst'], E=l['E'], stations=L['stations'] if L else None))
        return out

    def slices(self):
        out = {}
        for n, i in self.inst.items():
            if i['master'].startswith('ot_s81sl_slice'):
                out[n] = dict(master=i['master'], sid=self.strap(n, 'sid'), params=i['params'],
                              block=n[2:], group=self.blocks.get(n[2:], {}).get('group'))
        return out

    def frames_of(self, slice_inst):
        g = self.blocks[slice_inst[2:]]['group']
        return sorted('u_' + b_['name'] for b_ in self.plan['blocks'] if b_['kind'] == 'frame' and b_['group'] == g
                      and 'u_' + b_['name'] in self.inst)


# ================================================================================================= encoders (bit exact)
def host_word(typ, x):
    """dsdv_seq_host f_host word {type 2, x 512, v 1} (tb_dsdv_seq_host push())"""
    return (typ << 513) | ((x & ((1 << 512) - 1)) << 1) | 1


def csr_len(n):
    """0x11 calendar length d[39:32] (tb_dsdv_seq_host: x[7:0] = 8'h11, x[39:32] = nrow)"""
    return host_word(0, 0x11 | (n & 0xFF) << 32)


def csr_pw(a, d28):
    """0x10 calendar PW word {a = x[102:96], d28 = x[59:32]} (tb_dsdv_seq_host push_pw)"""
    return host_word(0, 0x10 | (d28 & 0xFFFFFFF) << 32 | (a & 0x7F) << 96)


def csr_template(i, payload186):
    """0x13 CTL template {index = x[14:8], payload = x[16 +: 186]}"""
    return host_word(0, 0x13 | (i & 0x7F) << 8 | (payload186 & ((1 << 186) - 1)) << 16)


def csr_gunit(a10, d256):
    """0x14 gunit table row: x[17:8] = a (a[9] must be 0), x[32 +: 256] = d -> cw {1, a, d} (dsdv_seq_host L0)"""
    assert not (a10 >> 9) & 1, 'gunit row a[9] must be 0'
    return host_word(0, 0x14 | (a10 & 0x3FF) << 8 | (d256 & ((1 << 256) - 1)) << 32)


def pw_header(n, stage=0, start_phase=0, seal=False):
    """ot_dsdv_fixed_issue page-3 word {3 [27:26], seal [25], 0 [24:17], length [16:9], start_phase [8:7], stage [6:0]}"""
    assert 0 < n <= NOPS
    return (3 << 26) | (int(seal) << 25) | (n << 9) | ((start_phase & 3) << 7) | (stage & 0x7F)


def pack_row(done, issue, eng, arg):
    """calendar row {done24 [75:52], issue24 [51:28], engine4 [27:24], arg24 [23:0]}"""
    return (done & 0xFFFFFF) << 52 | (issue & 0xFFFFFF) << 28 | (eng & 0xF) << 24 | (arg & 0xFFFFFF)


def pw_row_words(i, row76):
    """three PW parts {k [27:26], row[26k +: 26]} (tb_dsdv_seq_host; part 2 loads row[75:52] from d[23:0])"""
    return [(i, (k << 26) | ((row76 >> (26 * k)) & ((1 << 26) - 1))) for k in range(3)]


def ctl_payload(slice_mask, target, leaf_mask, body160):
    """CTL beat payload p = beat[21 +: 186]: [15:0] slice mask, [20:16] target, [25:21] leaf mask, [185:26] body
    (ot_s81sl_xr CTL decode; dsdv_seq_host header 'payload {body 160, leaf mask 5, target 5, slice mask 16}')"""
    return (slice_mask & 0xFFFF) | (target & 0x1F) << 16 | (leaf_mask & 0x1F) << 21 | (body160 & ((1 << 160) - 1)) << 26


def ctl_line_beat(payload186, src=4, hops=0):
    """CTL beat as injected by seq_host / carried on a tier line: [0] 1, [3:1] kind 0, [8:4] hops, [12:9] src,
    [20:13] 0, [21 +: 186] payload (dsdv_seq_host header; tb_s81sl_slice_eng ctl())"""
    return 1 | (hops & 0x1F) << 4 | (src & 0xF) << 9 | payload186 << 21


def vp_cmd(op, a0=0, a1=0, n=0, imm=0):
    """ot_s81sl_vp command c_d: [3:0] op, [13:4] a0, [23:14] a1, [31:24] n, [159:32] imm (tb_s81sl_beat cmd())"""
    return (op & 0xF) | (a0 & 0x3FF) << 4 | (a1 & 0x3FF) << 14 | (n & 0xFF) << 24 | (imm & ((1 << 128) - 1)) << 32


VP = dict(GAIN=1, POST=2, HLOAD=3, HSTORE=4, NORM=5, RDOUT=6)


def xfin_go(eps32, eng=False, eng_scale=0):
    """CTL target 1 body: [31:0] eps, [32] mode ENG, [95:64] Engram scale (ot_s81sl_xr; tb_s81sl_slice_eng)"""
    return (eps32 & 0xFFFFFFFF) | int(eng) << 32 | (eng_scale & 0xFFFFFFFF) << 64


def xs_issue(go=0, ph=0, np_=0, xbase=0, xps=0, obase=0, ops=0, fmt=0, prime=0, start=0, cal_base=0, cal_len=0,
             win=None, off=None):
    """ot_s81sl_xs is_d[159:0]: [92:0] f_iss {f_fault, fmt 2, ops 19, obase 19, xps 19, xbase 19, np 3, ph 10, go},
    [93] prime, [94] start, [106:95] cal base, [119:107] cal length, [120] gather window open [121] fam [122] parity,
    [123] load offset [131:124]; [159:132] 0"""
    f = (go & 1) | (ph & 0x3FF) << 1 | (np_ & 7) << 11 | (xbase & 0x7FFFF) << 14 | (xps & 0x7FFFF) << 33 | \
        (obase & 0x7FFFF) << 52 | (ops & 0x7FFFF) << 71 | (fmt & 3) << 90
    w = f | (prime & 1) << 93 | (start & 1) << 94 | (cal_base & 0xFFF) << 95 | (cal_len & 0x1FFF) << 107
    if win is not None:
        fam, par = win
        w |= 1 << 120 | (fam & 1) << 121 | (par & 1) << 122
    if off is not None:
        w |= 1 << 123 | (off & 0xFF) << 124
    return w


def cap_cfg(obase=0, ops=0, np_=0, fmt=1, rbase=0, rcnt=0, rsplit=0, fp32_lo=0, fp32_hi=0):
    """ot_s81sl_cap cfg_d: [11:0] obase [23:12] ops [26:24] np [28:27] fmt [44:29] rbase [55:45] rcnt [71:56] rsplit
    [72] fp32 rows < rsplit [73] fp32 rows >= rsplit"""
    assert fmt != 3 and rcnt < (1 << 11)
    return (obase & 0xFFF) | (ops & 0xFFF) << 12 | (np_ & 7) << 24 | (fmt & 3) << 27 | (rbase & 0xFFFF) << 29 | \
        (rcnt & 0x7FF) << 45 | (rsplit & 0xFFFF) << 56 | (fp32_lo & 1) << 72 | (fp32_hi & 1) << 73


SEND_DIR = dict(E=1, W=2, V=4, B=8)
B_MAX_PAIRS = 2          # BIND mu4 10-19: the C3 band word B is 513 b = {pk[511:0], valid} (point-to-point to entry q)


def send_cfg(dirs, kind=0, hops=0, dst_mask=0, dst_leaf=0, dst_row=0, pairs=1, sc_relay=0):
    """ot_s81sl_xr send config (CTL target 4) body: [3:0] dir {B, V, W, E}, [6:4] kind, [11:7] hops, [27:12] dst slice
    mask, [30:28] dst leaf, [40:31] dst row, [42:41] pairs - 1, [43] SC relay to V.  A send on B (C3 band port -> svc_rs
    entry q) carries at most B_MAX_PAIRS row pairs; xr faults (sticky) on a B config with pairs > 2."""
    d = 0
    for x in dirs:
        d |= SEND_DIR[x]
    assert 1 <= pairs <= 4, pairs
    assert not (d & SEND_DIR['B']) or pairs <= B_MAX_PAIRS, f'B send with {pairs} pairs > {B_MAX_PAIRS} (513-b band word)'
    return d | (kind & 7) << 4 | (hops & 0x1F) << 7 | (dst_mask & 0xFFFF) << 12 | (dst_leaf & 7) << 28 | \
        (dst_row & 0x3FF) << 31 | (pairs - 1) << 41 | (sc_relay & 1) << 43


def memh(words, width):
    return ''.join(f'{w:0{(width + 3) // 4}x}\n' for w in words)


# ================================================================================================= op-level schedule
def layer_schedule(tree, layer, workload='ar'):
    """the priced p4l static schedule of one layer (dv_layer_price.py: dv_price dv_base deltas + p4l land plan,
    half-cycle), node start / end rebased to the layer's first start"""
    import dv_layer_price as lp
    import dv_price as dp
    from throughput import accepted_cost as ac
    plan = tree / 'results/arch/s81_dv_1016/p4l/plan.json'
    land = tree / 'results/arch/s81_dv_1016/landing/p4l/land_plan.json'
    g = lp.facts(plan, land, True)
    doc = json.loads((dp.TP / ('ds_rom.json' if workload == 'ar' else 'ds_rom_mtp.json')).read_text())
    delta, _ = dp.dv_deltas(doc, g, 8, 0.0, 1.0, False, ())
    _, end = ac.solve(doc['nodes'], doc['edges'], delta)
    by = {n['id']: n for n in doc['nodes']}
    if layer in LAYERS:
        sel = [n for n in doc['nodes'] if n.get('layer') == LAYERS[layer]]
    elif layer == 'head':
        heads = {gg['id'] for gg in doc['groups'] if gg['kind'] == 'head'}
        sel = [n for n in doc['nodes'] if n.get('group') in heads]
    elif layer == 'mtp_draft':
        sel = [n for n in doc['nodes'] if 'mtp' in str(n.get('cls', '')).lower() or str(n.get('op', '')).startswith(('mtp', 'draft'))]
    else:
        raise SystemExit(f'unknown layer {layer}')
    if not sel:
        raise SystemExit(f'layer {layer}: no nodes in the {workload} token path')
    ops = []
    for n in sel:
        c = n['cycles'] + delta.get(n['id'], 0.0)
        ops.append(dict(id=n['id'], op=n.get('op', ''), cls=n.get('cls'), start=end[n['id']] - c, end=end[n['id']],
                        cycles=round(c, 1), delta=round(delta.get(n['id'], 0.0), 1), critical=bool(n.get('critical'))))
    # layer entry = the first start on the token's critical path (off-path prefetches, e.g. the Engram lookups, may
    # start earlier and get a negative start)
    t0 = min((o['start'] for o in ops if o['critical']), default=min(o['start'] for o in ops))
    for o in ops:
        o['start'] = round(o['start'] - t0, 1)
        o['end'] = round(o['end'] - t0, 1)
    ops.sort(key=lambda o: (o['start'], o['id']))
    ids = {o['id'] for o in ops}
    deps = [dict(src=e[0] if isinstance(e, list) else e.get('src'), dst=e[1] if isinstance(e, list) else e.get('dst'))
            for e in doc['edges']]
    deps = [d for d in deps if d['src'] in ids and d['dst'] in ids]
    span = max(o['end'] for o in ops) - min(0.0, min(o['start'] for o in ops))
    crit = sum(o['cycles'] for o in ops if o['critical'])
    return dict(layer=layer, workload=workload, span=round(span, 1), crit=round(crit, 1), ops=ops, deps=deps,
                price_source='tools/s81_dv/dv_layer_price.py facts + dv_price.dv_deltas dv_base + accepted_cost.solve')


# ================================================================================================= op -> DV unit map
# SPEC.md section 3 (DV dataflow per layer type) + the unit contracts.  status: LOWERED (this compiler emits the unit
# programme), PARTIAL (programme emitted, a named field is runtime data with no on-die path), GAP (no unit contract /
# encoder for this op on the DV die yet: the precise missing piece is named).
GAP_NORM_PRE = ('ot_s81sl_vp', 'c_d[159:32] (OP_NORM imm = hc_pre coefficients)',
                'NORM takes hc_pre only as the command immediate; dsdv_gunit_l5 delivers the 24 HC coefficients as six '
                'leaf-store row writes (CTL target 5, rows R..R+5) and no vp op loads hc_pre from a leaf-store row '
                '(POST reads post/comb rows only), so a boot-loaded CTL template cannot carry the runtime coefficients')
GAP_XS_ROM = ('ot_s81sl_xs', 'calendar / phase / stream ROMs (OT_ROM_DIR images)',
              'no DV field placement compiler: the stream / phase / calendar ROM images exist only for the c26l hub '
              'stage catalog (results/rtl/dsrom_recovery_20261004/immutable_fullcatalog, 81 stages); the DV rule '
              '"rows in the owning slice\'s frames" (SPEC section 2) needs a re-placement and re-emitted ROM images')
GAP_FRAME_PLACE = ('tools/s81_dv/frame_return_plan.py', 'plan_phase(rows = 2 * 12 / nseg)',
                   'the frame return legaliser places only rows = 2 x (12 q elements / nseg) per frame; a_proj puts 28 '
                   'rows on a slice\'s 8 frames (4,4,4,4,3,3,3,3), wq_b 512, wo_b 320, router 6 rows per slice')
GAP_XDIE = ('ot_s81sl_slice_lep* / ot_pdie_serdes', 'cross-die collective lanes',
            'TP4 collective: owned by TOKEN-XDIE-S81 (TOK.DS.XDIE); the slice bench replays the remote partials at '
            'their scheduled cycles at the end-slice lep port')
GAP_HEAD = ('head die (separate die type)', 'no netlist in the p4l DV bind',
            'head.* / draft.* / token.return run on the head dies (LM head 129,280 rows, argmax, MTP draft heads); the '
            'p4l DV die does not contain them, so their programme needs the head-die netlist of record and RTL (not in '
            'results/fleet_viz/die_sources.json), then this compiler targets it the same way')
OPMAP = [
    (r'^(head\.|draft\.|token\.return)', 'head die', 'GAP', GAP_HEAD),
    (r'attn\.(cmp\.wk|idx\.q)$', 'frames (cfg7) + slice xs / cap (compressor / indexer projections)', 'GAP', GAP_XS_ROM),
    (r'attn\.cmp\.(k_norm\..*|norm\..*|k_rope_qdq|row_qdq|pool)$', 'slice vn / vs (compressor norms, QDQ, pool)', 'GAP',
     ('ot_s81sl_vs', 'SU op codes 8..15 (s_d)', 'no compiler encoder for the vs SU op words yet')),
    (r'attn\.(idx\.(newkey|score|topk_local|topk_merge|topk_final)|cand\..*|gather)$',
     'bk units dsdv_bk_sel / dsdv_bk_col (index scan, top-k, candidate merge, sparse gather) + svc', 'GAP',
     ('dsdv_bk_sel / dsdv_bk_col', 'bk job / HBM index rows', 'no compiler ABI for the bk index-select / collect jobs '
      '(rtl/dsrom_sys/s81_dv/unit/bk/test/run_bk_bench.sh drives them directly)')),
    (r'^eng\.(lead_flit|hash|hbm_read)$', 'svc_rs HBM service (Engram rows) + lep stage hop', 'GAP',
     ('dsdv_svc_rs', 's_j job (Engram row read)', 'svc job ABI for the Engram HBM row read is not documented as a compiler '
      'ABI; Engram table image belongs to the fixtures')),
    # (regex on op, unit, status, gap or note)
    (r'(attn|ffn)\.hc_pre$|(attn|ffn)\.norm\.(sumsq|rsqrt|scale)$|attn\.quant$|ffn\.quant$',
     'slice vp/vn/vq + xr + xfin (NORM, xfin go, rstd fan, act-quant)', 'PARTIAL', GAP_NORM_PRE),
    (r'\.(a_proj|wq_b|wo_a|wo_b|router|experts_gu|down|shared_gu|wkv|compressor.*|indexer.*|eng\.proj.*)$',
     'frames (cfg7 programme) + slice xs (is_d phase start) + slice cap (cfg_d)', 'GAP', GAP_XS_ROM),
    (r'\.(a_allgather|out_allreduce|router_allgather|combine_allreduce|rows_allgather)$',
     'end-slice lep link endpoints + ring (cross-die)', 'GAP', GAP_XDIE),
    (r'attn\.q_norm\.|attn\.q_quant$', 'slice vn/vq over 4 adjacent slices (q_lora norm, xfin)', 'PARTIAL', GAP_NORM_PRE),
    (r'attn\.(q_rope|kv_rope_qdq|kv_norm\..*)$', 'slice vs SU ops (RoPE / QDQ)', 'GAP',
     ('ot_s81sl_vs', 'SU op codes 8..15 (s_d)', 'no compiler encoder for the vs SU op words yet (tools/s81_slice/vs_gold.py '
      'drives the leaf bench only); RoPE tables / positions are runtime context (seq_host context splice 1/2)')),
    (r'attn\.(window_load|own_row_write|scores|max|exp|den|sink|normalize|pv)$',
     'svc_rs HBM service + ot_s81_su_sm attention (svc jobs, engine 4)', 'GAP',
     ('dsdv_svc_rs / dsdv_svc_att', 's_j job {arg 24, tag {slot, op 7}}',
      'svc job op table for the attention pass is not documented as a compiler ABI (dsdv_svc_rs.sv / tools/s81_dv/svc_rs '
      'benches drive it directly); HBM KV image placement belongs to the fixtures')),
    (r'(attn|ffn)\.hc\.(sumsq|rsqrt|fn|pre_post|sinkhorn)$', 'gunit HC job (cw job + HP beats + L5 CTL rows)', 'GAP',
     ('dsdv_gunit_l0', 'HC JOB cw {which, set, row, lmask, smask}', 'job word is documented; the slice HP send '
      '(send config, CTL target 4) per accumulation is not lowered yet')),
    (r'ffn\.(softplus_sqrt|bias|weights)$', 'slice vs (softplus) + gunit router L1/L3', 'GAP',
     ('dsdv_gunit_l1 / ot_s81sl_vs', 'SC beats (kind 5) + router job', 'router lowering not written')),
    (r'ffn\.(top6|top6_order)$', 'gunit router (ot_hdc_select_tree) -> ids CTL rows', 'GAP',
     ('dsdv_gunit_l1', 'router job cw / ids CTL rows R..R+2', 'router lowering not written')),
    (r'ffn\.(swiglu|route_w|quant2|shared_swiglu|shared_quant)$|attn\.z_quant$', 'slice vs/vsw (SwiGLU, qbank)', 'GAP',
     ('ot_s81sl_vs / ot_s81sl_vsw', 'SU op words', 'no compiler encoder for the vs SU op words yet')),
    (r'(attn|ffn)\.hc_post$', 'slice vp POST (hc_post lanes)', 'PARTIAL',
     ('ot_s81sl_vp', 'POST a0 (coefficient rows) / a1 (y rows)', 'POST is a static template; the coefficient rows are '
      'written by the gunit L5 CTL rows (target 5) at their scheduled edge')),
    (r'substage_hop\d+$|head\.hop$', 'end-slice lep stage hop (h ring to the edge link)', 'GAP', GAP_XDIE),
    (r'eng\.', 'slice vs op 14 ENG + ve + xfin ENG + eg (Engram mix)', 'GAP',
     ('ot_s81sl_vs', 'op 14 REDUCE / ADD words (tb_s81sl_slice_eng)', 'encoder exists only inside the slice bench; HBM '
      'Engram rows via svc not lowered')),
]


def op_unit(op):
    for rx, unit, st, gap in OPMAP:
        if re.search(rx, op):
            return unit, st, gap
    return 'unmapped', 'GAP', ('-', '-', f'no DV unit mapping for op {op}')


# ================================================================================================= smoke lowering
class Prog:
    def __init__(self, die):
        self.die = die
        self.templates = []          # payload ints
        self.tnames = []
        self.rows = []               # dict(done, issue, eng, arg, what)
        self.events = []
        self.gunit_rows = []
        self.svc = []
        self.notes = []
        self.mu_ctx = False          # MU-S81/TOK: the layer's first V command carries the user context (context 1)

    def template(self, name, payload):
        if payload in self.templates:
            return self.templates.index(payload)
        assert len(self.templates) < NOPS, 'CTL template table full (128)'
        self.templates.append(payload)
        self.tnames.append(name)
        return len(self.templates) - 1

    def vrow(self, eng, issue, tix, ctx=0, what=''):
        assert eng in (ENG['VN'], ENG['VS'])
        self.rows.append(dict(eng=eng, issue=issue, done=issue + SEQ['done_v'], arg=(tix & 0x7F) | (ctx & 3) << 7,
                              what=what))


def ctl_path(die, sl):
    """seq_host vo_n / vo_s -> the slice's control plane: per-hop edges (contract model, asserted by the bench).
    V north reaches s_4N (tvN_seqhost), V south bk_sel then s_4S (tvS_seqhost, tvS_bk_sel); the column-4 slice
    re-injects on its tier line both ways, rstop 2 edges a stop + the xr / xrE link ages between slices."""
    info = die.slices()[sl]
    sid = info['sid']
    tier = 'N' if sl.endswith('N') else 'S'
    col = int(sl[4])
    hops = []
    if tier == 'N':
        hops.append(('u_seqhost.vo_n', 'tvN_seqhost'))
        entry = 'u_s_4N'
    else:
        hops.append(('u_seqhost.vo_s', 'tvS_seqhost'))
        hops.append(('u_bk_sel', 'tvS_bk_sel'))
        entry = 'u_s_4S'
    t = SEQ['v_cmd_to_vo']
    path = [dict(at='u_seqhost.vo', edge=t)]
    for where, lk in hops:
        L = die.links.get(lk)
        t += (L['age_edges'] if L else 0)
        path.append(dict(at=f'{lk} landed' if L else f'{lk} (abutted, no station / landing)', link=lk, edge=t,
                         stations=L['stations'] if L else 0, E=L['E'] if L else None))
        if where == 'u_seqhost.vo_s':
            t += 2                                   # bk_sel rung transit: ot_dsdv_vstop forward 2 edges (dsdv_bk_g)
    # the column-4 slice: rstop V deliver -> line inject (2 edges), then one stop per column
    t += RSTOP_HOP
    path.append(dict(at=f'{entry} line inject', edge=t))
    step = -1 if col < 4 else 1
    c = 4
    while c != col:
        nxt = c + step
        # a 1,104-b line beat = 4 x 276-b lanes; the beat is whole when its slowest lane lands
        cand = [(k, L) for k, L in die.links.items() if any(x[0] == f'u_s_{c}{tier}' for x in L['src'])
                and any(x[0] == f'u_s_{nxt}{tier}' for x in L['dst'])]
        assert cand, f'no line link u_s_{c}{tier} -> u_s_{nxt}{tier}'
        lk, L = max(cand, key=lambda kv: kv[1]['age_edges'])
        t += L['age_edges'] + RSTOP_HOP
        path.append(dict(at=f'u_s_{nxt}{tier} line', link=lk, lanes=sorted(k for k, _ in cand), edge=t))
        c = nxt
    port = 'ri_e' if col < 4 else ('ri_w' if col > 4 else 'vi')
    return dict(slice=sl, sid=sid, entry_port=port, edges=t, path=path, model='contract (dsdv_seq_host header + '
                'ot_s81_land E + 1 + half-cycle stations + rstop 2/stop); the bench asserts the arrival edge')


def lower_norm_smoke(die, prog, sl, t0, eps=0x358637BD, r_h=0, r_gain=64, which='attn'):
    """slice-local hc_pre + RMSNorm + act-quant on ONE slice (the beat bench's proven sequence, issued through the
    seq_host calendar as CTL beats): HLOAD (5 leaves) -> GAIN -> NORM per leaf (a1 = global beat 5 sid + k, n = 3:
    q + BF16 family) -> xfin go (eps).  The partial / rstd / XQ edges follow from the unit latencies."""
    s = die.slices()[sl]
    sid, smask = s['sid'], 1 << s['sid']
    eng = ENG['VN'] if sl.endswith('N') else ENG['VS']
    cp = ctl_path(die, sl)
    lat = cp['edges']
    th = prog.template(f'{which}.HLOAD', ctl_payload(smask, 0, 0x1F, vp_cmd(VP['HLOAD'], a0=r_h)))
    tg = prog.template(f'{which}.GAIN', ctl_payload(smask, 0, 0x1F, vp_cmd(VP['GAIN'], a0=r_gain)))
    tn = [prog.template(f'{which}.NORM.k{k}', ctl_payload(smask, 0, 1 << k, vp_cmd(VP['NORM'], a1=5 * sid + k, n=3, imm=0)))
          for k in range(5)]
    tx = prog.template(f'{which}.XFIN_GO', ctl_payload(smask, 1, 0, xfin_go(eps)))
    t = t0
    # MU-S81/TOK (--mu-ctx, default off = byte-identical): the HLOAD beat carries the user's context header
    # body[159:108] = {user 10, pos 21, tok 21} (seq_host context 1; HLOAD's template leaves those bits 0)
    prog.vrow(eng, t, th, ctx=1 if prog.mu_ctx else 0, what=f'{which} HLOAD {sl}' + (' +ctx' if prog.mu_ctx else ''))
    prog.events.append(dict(cycle=t + lat, inst=sl, port=cp['entry_port'],
                            dir='in', kind='CTL', tag=f'{which}.HLOAD', payload=f'template {th}'))
    t += BEAT['hload_slot']
    prog.vrow(eng, t, tg, what=f'{which} GAIN {sl}')
    prog.events.append(dict(cycle=t + lat, inst=sl, port=cp['entry_port'], dir='in', kind='CTL', tag=f'{which}.GAIN',
                            payload=f'template {tg}'))
    t += BEAT['gain_slot']
    # one CTL beat a cycle (two CTL beats in one cycle are a sticky fault in xr); the 5 NORMs go on 5 edges
    go = []
    for k in range(5):
        prog.vrow(eng, t + k, tn[k], what=f'{which} NORM leaf {k} {sl} (imm = hc_pre: RUNTIME, see gap)')
        prog.events.append(dict(cycle=t + k + lat, inst=sl, port=cp['entry_port'], dir='in', kind='CTL',
                                tag=f'{which}.NORM.k{k}', payload=f'template {tn[k]}; imm hc_pre RUNTIME'))
        go.append(t + k + lat)
    prog.vrow(eng, t + 5, tx, what=f'{which} XFIN_GO {sl}')
    prog.events.append(dict(cycle=t + 5 + lat, inst=sl, port=cp['entry_port'], dir='in', kind='CTL', tag=f'{which}.XFIN_GO',
                            payload=f'template {tx}'))
    # derived internal / outgoing edges (plan values the bench checks at the slice boundary where they are visible)
    last_partial = go[-1] + BEAT['go_to_partial'] + XFIN['dl'] + XFIN['collector']
    rstd = last_partial + XFIN['last_partial_to_rstd']
    xq = rstd + XFIN['rstd_to_xq_ring']
    prog.events.append(dict(cycle=last_partial, inst=sl, port='(xfin NX exchange out: ro_e / ro_w / vo)', dir='out',
                            kind='NX', tag=f'{which}.partial_roots', payload='golden-subtree roots (fixture)', plan_only=True))
    prog.events.append(dict(cycle=xq, inst=sl, port='ro_e / ro_w', dir='out', kind='XQ', tag=f'{which}.x_allgather',
                            payload='act-quant x beats of the slice (fixture: golden FP8 codes)', plan_only=True))
    return dict(slice=sl, sid=sid, ctl_latency=cp, t_issue0=t0, last_partial=last_partial, rstd=rstd, xq_at_ring=xq,
                end=xq, templates=[th, tg] + tn + [tx])


def finish(prog, stage=0, kit_lead=20):
    """KIT / END rows + the host boot stream (length, BEGIN, rows, SEAL, templates, gunit rows)"""
    rows = sorted(prog.rows, key=lambda r: (r['issue'], r['eng']))
    seen = {}
    for r in rows:   # one command per engine per edge (fixed_issue code 9 duplicate issue)
        key = (r['eng'], r['issue'])
        assert key not in seen, f'duplicate issue engine {r["eng"]} at {r["issue"]}'
        seen[key] = 1
    endage = max(r['done'] for r in rows) + 4
    rows.append(dict(eng=ENG['KIT'], issue=max(0, endage - kit_lead), done=0, arg=0, what='KIT'))
    rows.append(dict(eng=ENG['END'], issue=endage, done=0, arg=0, what='END'))
    if len(rows) > NOPS:
        raise SystemExit(f'calendar {len(rows)} rows > NOPS {NOPS}: split the layer into jobs')
    hs = [csr_len(len(rows)), csr_pw(0, pw_header(len(rows), stage))]
    for i, r in enumerate(rows):
        r['row76'] = pack_row(r['done'], r['issue'], r['eng'], r['arg'])
        hs += [csr_pw(a, d) for a, d in pw_row_words(i, r['row76'])]
    hs.append(csr_pw(0, pw_header(len(rows), stage, seal=True)))
    hs += [csr_template(i, p) for i, p in enumerate(prog.templates)]
    hs += [csr_gunit(a, d) for a, d in prog.gunit_rows]
    return rows, hs, endage


def compile_layer(layer, out, tree, sl='s_0S', smoke=True, workload=None, mu_ctx=False):
    out = Path(out)
    (out / 'prog' / 'frame_cfg7').mkdir(parents=True, exist_ok=True)
    die = Die(tree)
    wl = workload or ('mtp' if layer == 'mtp_draft' else 'ar')
    sched = layer_schedule(tree, layer, wl)
    sl = sl if sl.startswith('u_') else f'u_{sl}'
    prog = Prog(die)
    prog.mu_ctx = mu_ctx
    low = []
    for o in sched['ops']:
        unit, st, gap = op_unit(o['op'])
        low.append(dict(id=o['id'], op=o['op'], start=o['start'], end=o['end'], unit=unit, status=st,
                        gap=dict(module=gap[0], port=gap[1], missing=gap[2]) if gap and st != 'LOWERED' else None))
    sub = None
    if layer != 'head':
        qop = next((o for o in sched['ops'] if o['op'] in ('attn.quant', 'mtp.attn.quant') or o['op'].endswith('attn.quant')), None)
        if qop is not None:
            sub = lower_norm_smoke(die, prog, sl, t0=int(qop['start']), which=qop['op'].rsplit('.', 1)[0] or 'attn')
            for x in low:
                if x['id'] == qop['id']:
                    x['emitted'] = dict(slice=sl, rows=len(prog.rows), templates=len(prog.templates))
    # frames of the slice: placement record for the first matvec (programme blocked on GAP_FRAME_PLACE / GAP_XS_ROM)
    frames = die.frames_of(sl)
    mv = next((o for o in sched['ops'] if re.search(r'\.(a_proj|router|eng\.proj)', o['op'])), None)
    for f in frames:
        rec = dict(frame=f, master=die.inst[f]['master'], slice=sl, first_matvec=mv and mv['op'],
                   status='GAP', gaps=[dict(zip(('module', 'port', 'missing'), GAP_FRAME_PLACE)),
                                        dict(zip(('module', 'port', 'missing'), GAP_XS_ROM))])
        (out / 'prog/frame_cfg7' / f'{f}.json').write_text(json.dumps(rec, indent=1) + '\n')
    files = {}
    if prog.rows:
        rows, hs, endage = finish(prog)
        (out / 'prog/host_boot.memh').write_text(memh(hs, 515))
        files['prog/host_boot.memh'] = len(hs)
        (out / 'prog/calendar.json').write_text(json.dumps(dict(
            schema='opentallas.s81_dv.calendar.v1', nops=len(rows), stage=0, end_age=endage,
            rows=[dict(i=i, issue=r['issue'], done=r['done'], engine=r['eng'], arg=r['arg'], row76=f"{r['row76']:019x}",
                       what=r['what']) for i, r in enumerate(rows)]), indent=1) + '\n')
    (out / 'prog/ctl_templates.json').write_text(json.dumps(dict(
        schema='opentallas.s81_dv.ctl_templates.v1', n=len(prog.templates),
        templates=[dict(i=i, name=n, payload186=f'{p:047x}', beat=f'{ctl_line_beat(p):053x}')
                   for i, (n, p) in enumerate(zip(prog.tnames, prog.templates))]), indent=1) + '\n')
    (out / 'prog/gunit_rows.json').write_text(json.dumps(dict(rows=[dict(a=a, d=f'{d:064x}') for a, d in prog.gunit_rows],
                                                             note='none lowered (HC / router GAP)'), indent=1) + '\n')
    (out / 'prog/svc_jobs.json').write_text(json.dumps(dict(jobs=prog.svc, note='none lowered (attention / HBM GAP)'),
                                                       indent=1) + '\n')
    stat = {}
    for x in low:
        stat[x['status']] = stat.get(x['status'], 0) + 1
    links = {k: v for k, v in die.links.items() if any(s_[0] in (sl, 'u_seqhost', 'u_bk_sel') for s_ in v['src'] + v['dst'])
             or k.startswith(('tvS_seqhost', 'tvN_seqhost', 'tvS_bk_sel'))}
    (out / 'schedule.json').write_text(json.dumps(dict(
        schema='opentallas.s81_dv.layer_schedule.v1', layer=layer, workload=wl, slice=sl,
        composition='the layer = the slowest (critical) slice under the fixed schedule: every slice runs the same '
                    'calendar shifted by its CTL arrival; the layer span is max over slices and units of the last '
                    'scheduled event (op schedule span below = the priced critical slice)',
        price=dict(span=sched['span'], crit=sched['crit'], source=sched['price_source']),
        ops=sched['ops'], deps=sched['deps'], smoke=sub, events=sorted(prog.events, key=lambda e: e['cycle']),
        links=links), indent=1) + '\n')
    ul = die.unlanded()
    die_gaps = [dict(module='results/arch/s81_dv_1016/bind9/die.v (S81 die GEN, lead S81-DIE6/7)',
                     port=', '.join(sorted(x['link'] for x in ul)),
                     missing=f'{len(ul)} lanes with relay stations and a planned landing E in the p4l land plan have no '
                             f'ld_<link> landing tile in die.v (the last station ck_o is left open; the end-slice lep '
                             f'masters ot_s81sl_slice_lep* contain no ot_s81_land): they enter the receiving root '
                             f'domain unlanded', lanes=ul)] if ul else []
    (out / 'lowering.json').write_text(json.dumps(dict(
        schema='opentallas.s81_dv.lowering.v1', layer=layer, status_counts=stat, die_gaps=die_gaps, ops=low,
        gaps=sorted({(x['gap']['module'], x['gap']['port'], x['gap']['missing']) for x in low if x['gap']})), indent=1) + '\n')
    man = dict(schema='opentallas.s81_dv.layer_prog_manifest.v1', layer=layer, die_ref=DIE_REF,
               die_ref_sha=(tree / '.done').read_text().strip() if (tree / '.done').exists() else None,
               die_v_sha256=die.die_sha,
               land_plan_sha256=sha256(tree / 'results/arch/s81_dv_1016/landing/p4l/land_plan.json'),
               plan_sha256=sha256(tree / 'results/arch/s81_dv_1016/p4l/plan.json'),
               compiler_sha256=sha256(Path(__file__)), files={})
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name != 'manifest.json':
            man['files'][str(p.relative_to(out))] = sha256(p)
    (out / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n')
    return dict(layer=layer, ops=len(low), status=stat, rows=len(prog.rows), templates=len(prog.templates), smoke=sub)


# ================================================================================================= multi-user (MU-S81)
# MU-S81 10-18: the layer programme is ONE per-stage programme for every user (the shift lemma: user k = the reference
# schedule shifted by k slots, tools/s81_dv/dv_mu_calendar.py).  What changes per slot is data, not the calendar rows:
# the V-command context body {user 10, pos 21, tok 21} (dsdv_seq_host context 1 = body[159:108]) and the per-user HBM
# region bases the svc job words carry (WB window ring, SB compressed rows, IKB index keys) on the user's group copy.
MU_LAYER_GROUP = {'L0': 'S000', 'L2': 'S002', 'L14': 'S020', 'L20': 'S029'}


def mu_ctx_body(user, pos, tok=0):
    """dsdv_seq_host V context 1: body[159:108] = {user 10, pos 21, tok 21} (seq_host header, arg [8:7] = 1)"""
    assert 0 <= user < 1 << 10 and 0 <= pos < 1 << 21 and 0 <= tok < 1 << 21
    return ((user << 42) | (pos << 21) | tok) << 108


def mu_slot_tables(cal, layer, pos0=0):
    """per-slot rows of this layer's stage group from a dv_mu_calendar record: {slot, user, kind, copy, local, start,
    pos0, stride, wb/sb/ikb, ctx_body (hex)}; the latency user is slot 0 on copy A"""
    gid = MU_LAYER_GROUP[layer]
    tab = cal['tables'][gid]
    stride = cal['pos']['stride']
    slot_of = {s_['user']: s_['slot'] for s_ in cal['slots']}
    rows = []
    for r in tab['rows']:
        p0 = pos0                       # every user starts its own context at pos0 (per-user KV state)
        rows.append(dict(slot=slot_of[r['user']], **r, pos0=p0, stride=stride,
                         ctx_body=f"{mu_ctx_body(r['user'], p0):040x}"))
    assert rows and rows[0]['user'] == 0 and rows[0]['copy'] == 'A' and rows[0]['start'] == min(x['start'] for x in rows)
    return dict(schema='opentallas.s81_dv.mu_slots.v1', layer=layer, group=gid, mode=cal['mode'],
                period=cal['period'], slot=cal['slot'], copies=tab['copies'], users_per_copy=tab['users_per_copy'],
                lemma=cal['lemma']['brute_force']['result'], rows=rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--layer', required=True, choices=list(LAYERS) + list(SPECIAL))
    ap.add_argument('--out', required=True)
    ap.add_argument('--slice', default='s_0S')
    ap.add_argument('--die-ref', default=DIE_REF)
    ap.add_argument('--die-src', default=None, help='an extracted die-ref tree (else git archive of --die-ref)')
    ap.add_argument('--workload', default=None, choices=('ar', 'mtp'))
    ap.add_argument('--mu-cal', default=None, help='MU-S81: a dv_mu_calendar record -> DIR/prog/mu_slots.json')
    ap.add_argument('--mu-ctx', action='store_true', help='MU-S81/TOK: HLOAD carries the user context (context 1)')
    a = ap.parse_args(argv)
    if a.mu_cal:
        t = mu_slot_tables(json.loads(Path(a.mu_cal).read_text()), a.layer)
        Path(a.out, 'prog').mkdir(parents=True, exist_ok=True)
        Path(a.out, 'prog/mu_slots.json').write_text(json.dumps(t, indent=1) + '\n')
        print(f"MU {a.layer} {t['group']}: {len(t['rows'])} slots, copies {t['copies']} {t['users_per_copy']}, "
              f"lemma {t['lemma']}")
        if a.layer not in LAYERS:
            return
    tree = die_tree(a.die_ref, a.die_src)
    r = compile_layer(a.layer, a.out, tree, a.slice, workload=a.workload, mu_ctx=a.mu_ctx)
    print(json.dumps(dict((k, v) for k, v in r.items() if k != 'smoke'), indent=None))
    if r['smoke']:
        s = r['smoke']
        print(f"SMOKE {s['slice']} sid {s['sid']}: CTL latency {s['ctl_latency']['edges']} edges, last partial "
              f"{s['last_partial']}, rstd {s['rstd']}, XQ at ring {s['xq_at_ring']}")


if __name__ == '__main__':
    main()
