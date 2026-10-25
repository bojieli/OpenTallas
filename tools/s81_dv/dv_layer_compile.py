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
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))

from xr_timing import source_contract

DIE_REF = 'origin/main'   # p4l bind9 / plan / land plan / unit RTL of record (main 711fb3da3+ = die7 77083deda; byte-identical to die6 3923ae6de)
DIE_PATHS = ['results/arch/s81_dv_1016/bind9', 'results/arch/s81_dv_1016/p4l', 'results/arch/s81_dv_1016/landing/p4l',
             'tools/s81_dv', 'rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host.sv', 'rtl/dsrom_sys/s81_dv/unit/ot_dsdv_fixed_issue.sv', 'rtl/dsrom_sys/s81_dv/unit/ot_dsdv_walk_issue.sv',
             'rtl/dsrom_sys/s81_dv/slice', 'rtl/dsrom_sys/s81_dv/unit/dsdv_gunit.sv']
LAYERS = {'L0': 0, 'L2': 2, 'L14': 14, 'L20': 20}
SPECIAL = ('mtp_draft', 'head')

# ------------------------------------------------------------------------------------------------ fixed unit latencies
# dsdv_seq_host header (asserted by tb_dsdv_seq_host): f_ks captured at t -> issuer samples job_v at t + 3 -> command of
# calendar age a leaves the issuer register at t + 4 + a; V command register -> vo pin + 7; svc command -> s_j + 2;
# gunit job -> cw pin + 3; issuer KIT -> t_kd pin + 3.  Calendar done rows: V / gunit = issue + 5 (posted).
SEQ = dict(fks_to_job=3, job_to_age0=4, v_cmd_to_vo=7, svc_to_sj=2, gunit_to_cw=3, kit_to_tkd=3, done_v=5, vo_s_land=1)
# vo_s_land (S81-SHLK2 10-18): dsdv_sh_lk RL 1 lands the rung at both faces of the L0 leaf (+1 edge each way of the rung);
# a V SOUTH command leaves vo_s at v_cmd_to_vo + vo_s_land (V north on vo_n unchanged).
# ot_s81sl_rstop: line in pin -> line out pin 2 edges a stop.
RSTOP_HOP = 2
# V CTL injection is source-qualified by xr_timing.source_contract (XR2: seven edges).
# dsdv_bk_sel rung transit vi -> vo: 3 edges since S81-TILES8/bk (10-18: one 276-b relay per input direction inside the
# cluster, u_rn on vi_n; was ot_dsdv_vstop's 2).
BKSEL_TRANSIT = 3
# tb_s81sl_beat on the current vp (S81-SLICE NORMR, Verilator 5.050): results/rtl/s81_slice_1017/beat/g_b37 (op 7 NORMR,
# hc_pre = G-unit leaf row R: SLBEAT go_to_partial=115 rstd_to_y0=18 rstd_to_xq=59 post_cmd_to_last_hw=63, PASS) and g_b37i
# (op 5 NORM imm: go_to_partial=112); mutants g_mni (NORMR ignores the row) / g_mpl (old POST row order) FAIL.  (Was the
# pre-NORMR bt_base: 111 / 18 / 47.)  The bench's proven command spacing HLOAD -> GAIN 40, GAIN -> NORM 20 is kept.
BEAT = dict(go_to_partial=112, go_to_partial_normr=115, rstd_to_y0=18, rstd_to_xq=59, post_cmd_to_last_hw=63,
            hload_slot=40, gain_slot=20)
# dv_price.py (S81-DV measured): beat partial -> xfin DL 4 + collector 5; xfin last partial -> rstd 234 (tb_s81dv_xfin16);
# rstd -> XQ complete at the ring stop 59 + 4 * 4 (last leaf) + DL 4.
XFIN = dict(dl=4, collector=5, last_partial_to_rstd=234, rstd_to_xq_ring=59 + 16 + 4)
# TOK-DS NORM-DESKEW 10-25 (COORD ruling 01:34; claude/s81-norm-deskew-1025): ot_s81sl_xrt1 / xrt3 PDSK = leaf 0..4
# depth 4, 3, 2, 1, 0 -- the per-leaf NORMRs must reach the slice on 5 consecutive edges in leaf order (lower_norm_smoke
# issues them on t .. t + 4) and the partial set leaves xr 4 edges after the first one would have.
XR_DESKEW = 4
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
        self.timing_contract = source_contract(tree, ROOT, self.inst)
        self.plan = json.loads((self.tree / 'results/arch/s81_dv_1016/p4l/plan.json').read_text())
        self.land = json.loads((self.tree / 'results/arch/s81_dv_1016/landing/p4l/land_plan.json').read_text())
        self.E = {l['link']: l for l in self.land['links']}
        self.blocks = {b_['name']: b_ for b_ in self.plan['blocks']}
        self._links()
        try:                                    # S81-RATE3: physical frames per slice for the field dealing
            import xs_topo
        except ImportError:
            sys.path.insert(0, str(ROOT / 'tools/s81_dv/layer_prog'))
            import xs_topo
        xs_topo.set_from_die(self)

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
            internal = None
            row = self.E.get(lk, {})
            if lk not in ld and row.get('cls') == 'x_frame':
                match = re.fullmatch(r'.+_l(\d+)', lk)
                receiver = 'u_' + row['dst'].split('.')[0]
                strap = self.strap(receiver, 'lk') if receiver in self.inst else None
                if match and strap is not None:
                    k = (strap >> (3 * int(match.group(1)))) & 7
                    internal = receiver
            age = (math.ceil(n / 2) + (k if k is not None else e) + 1) if lk in ld or internal else n / 2
            self.links[lk] = dict(stations=n, landing=ld.get(lk), internal_landing=internal, K=k, E=e,
                                  src=src, dst=dst, age_edges=age,
                                  land_master=self.inst[ld[lk]]['master'] if lk in ld else None)
        # TOK-FUNC-S81 (10-21): the 72-frame die abuts neighbour slices (plan links with 0 stations, no landing): the
        # sink port names the source wire w_<link>_src directly -> age 0 edges; endpoints from the plan's block pair.
        B = self.plan['blocks']
        for pl in self.plan['links']:
            lk = pl['i'].replace('-', '_')
            if lk in self.links or pl.get('s', 0) > 0:
                continue
            a, b = 'u_' + B[pl['e'][0][0]]['name'], 'u_' + B[pl['e'][1][0]]['name']
            us = users.get((lk, 'src'), []) + users.get((lk, 'dst'), []) + users.get((lk, 'lnd'), [])
            src = [u for u in us if u[0] == a]
            dst = [u for u in us if u[0] == b]
            if src and dst:
                self.links[lk] = dict(stations=0, landing=None, internal_landing=None, K=None, E=None, src=src, dst=dst,
                                      age_edges=0, land_master=None, abutted=True)

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


VP = dict(GAIN=1, POST=2, HLOAD=3, HSTORE=4, NORM=5, RDOUT=6, NORMR=7)


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
    # CAPC5k with explicit C->CAP and CAP->C landings: six child edges plus
    # three edges in each direction. Keep dependent issues behind capture.
    # Opt-in must match ot_s81sl_slice_c1x_k8_cap5_lp; old parents unchanged.
    cap5_extra = 12 if os.environ.get('OT_S81_CAP5_C', '0') == '1' else 0
    if cap5_extra:
        from layer_prog.lower_xs import OPS as capture_ops
        for node in doc['nodes']:
            if any(re.search(pattern, node.get('op', '')) for pattern in capture_ops):
                delta[node['id']] = delta.get(node['id'], 0.0) + cap5_extra
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
    # S81-L20 10-19: the layer span runs from the layer entry (t0 = 0) to the layer exit.  Off-path prefetches that
    # start before the entry (the Engram E<L>.* chain, which the token runs during EARLIER layers) are NOT part of the
    # layer: they were counted here before (span = max end - min start), which priced AR L14 at 318,272.6 cycles
    # (Engram lead_flit -290,190.7) instead of 28,081.9.  The prefetch lead is reported separately.
    span = max(o['end'] for o in ops)
    prefetch_lead = -min(0.0, min(o['start'] for o in ops))
    crit = sum(o['cycles'] for o in ops if o['critical'])
    return dict(layer=layer, workload=workload, span=round(span, 1), crit=round(crit, 1),
                capture_extra_edges=cap5_extra,
                prefetch_lead=round(prefetch_lead, 1), ops=ops, deps=deps,
                price_source='tools/s81_dv/dv_layer_price.py facts + dv_price.dv_deltas dv_base + accepted_cost.solve')


# ================================================================================================= op -> DV unit map
# SPEC.md section 3 (DV dataflow per layer type) + the unit contracts.  status: LOWERED (this compiler emits the unit
# programme), PARTIAL (programme emitted, a named field is runtime data with no on-die path), GAP (no unit contract /
# encoder for this op on the DV die yet: the precise missing piece is named).
GAP_NORM_PRE = ('ot_s81sl_xr / ot_s81sl_rstop (xfin NX snake, XQ all-gather)', '16-slice norm composition',
                'hc_pre reaches vn through vp op 7 NORMR from the G-unit L5 leaf row R (S81-SLICE 10-18, beat bench g_b37 '
                'PASS / g_mni FAIL) and the compiler issues it (lower_norm_smoke); the norm is still compiled on ONE '
                'slice: the xfin NX snake + XQ all-gather beats of all 16 slices (rstd, act-quant x) are not composed')
GAP_QNORM = ('tools/s81_dv/frame_return_plan.py + xfin over 4 slices', 'q_lora (qa) rows -> vn h copy 0',
             'q_norm is a plain RMSNorm of qa (no HC mix: pre = one-hot, a static NORM imm / boot row); the qa rows '
             'are the a_proj return rows, whose frame placement is not compiled (GAP_FRAME_PLACE), and the 4-slice '
             'xfin composition is not compiled')
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
GAP_KV_UNIT = ('p4l die.v (no KV / compressor norm unit) / ot_s81sl_vs',
               'SPEC section 2 slice SU lanes "KV 32" (RMSNorm -> RoPE -> FP8 QDQ, D 512)',
               'TOK-S81-GAPS/VS 10-18: NOT a compiler encoder gap -- no unit on the p4l die computes these ops.  ot_s81sl_vs '
               'ops are SW / QB / RA / RB / QR / MOE / ENG (no RMSNorm, no KV QDQ); vn NORM is the hc_pre-mixed h norm '
               '(4 HC copies, 64-element beats); the hub KV unit ot_s81_su_kv (rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_kv.sv: '
               'kvt / kve / qnh / qnr / kvq masters, D 512 exact) has 0 instances in bind_p4l3_g8 die.v.  Die decision '
               'owed (S81-DIE8 / S81-SLICE): instantiate the KV unit on the die (fed by the kv / compressed rows, result rows '
               'to the svc KV write) or add a vs RMS / KVQDQ op; then this compiler lowers it')
OPMAP = [
    (r'^(head\.|draft\.|token\.return)', 'head die', 'GAP', GAP_HEAD),
    (r'attn\.(cmp\.wk|idx\.q)$', 'frames (cfg7) + slice xs / cap (compressor / indexer projections)', 'GAP', GAP_XS_ROM),
    (r'attn\.cmp\.(k_norm\..*|norm\..*|k_rope_qdq|row_qdq|pool)$', 'slice vn / vs (compressor norms, QDQ, pool)', 'GAP',
     GAP_KV_UNIT),
    # TOK-S81-GAPS/IDX 10-18: topk_local / topk_final / cand.* are lowered by layer_prog/lower_bk.py (bk_sel job);
    # what stays here has NO unit on the p4l3 die (bind_p4l3_g8 masters: no index scan, no mix4)
    (r'attn\.idx\.score$', 'DV index scan (none on the die)', 'GAP',
     ('bind_p4l3_g8 (no index-score unit)', 'HBM index-key scan q.k -> BF16 scores -> u_bk_sel vi_s',
      'no DV unit computes the indexer scores: dsdv_svc_rs (x16) has attention (svc_att / svc_sx / su_sms) only, the '
      'hub-era scan dsfd_svc_idx (rtl/dsrom_sys/s81_ph/svc) is not instantiated; the scan must also emit BK-format beats '
      '(lower_bk GAPS producer).  Rate: 131,072 scores / die at the 276-b rung = 8 scores / edge -> >= 16,388 edges')),
    (r'attn\.idx\.newkey$', 'svc_rs HBM index-key append (none on the die)', 'GAP',
     ('dsdv_svc_rs', 's_j job (index-key row write)', 'no svc job writes the new index key row into the HBM index '
      'cache (dsdv_svc_rs job table: attention window / own row only); the key itself (idx.q . wk path) is a slice op')),
    (r'attn\.(idx\.topk_merge)$', 'TP4 collective of the local selections (end-slice lep)', 'GAP',
     ('u_s_4S rstop V receive -> end-slice lep', 'bk_sel egress kind 5 words', 'no path carries the bk_sel IDX words to '
      'an end slice for the cross-die merge (lower_bk GAPS consumer); collective owned by TOKEN-XDIE-S81')),
    (r'attn\.gather$', 'selected-row gather (svc HBM read by index; bk_col frame merge)', 'GAP',
     ('dsdv_svc_rs / dsdv_bk_col', 'svc row-read job by index list + bk_col frames', 'no svc job reads HBM rows by a '
      'runtime index list, and nothing produces bk_col frames on the column-1 rung; the 512 selected rows (fixture '
      'attn.gather 512 x 512) would also cost >= 2 V beats per 512-b word at the rung (bk_col ingress + egress)')),
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
    (r'attn\.q_norm\.|attn\.q_quant$', 'slice vn/vq over 4 adjacent slices (q_lora norm, xfin)', 'PARTIAL', GAP_QNORM),
    (r'attn\.(q_rope|kv_rope_qdq|kv_norm\..*)$', 'KV RMSNorm -> RoPE -> FP8 QDQ (no die unit)', 'GAP', GAP_KV_UNIT),
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
    (r'^eng\.knorm$', 'Engram key RMSNorm (no die unit)', 'GAP', GAP_KV_UNIT),
    (r'eng\.', 'slice vs op 14 ENG + ve + xfin ENG + eg (Engram mix)', 'GAP',
     ('ot_s81sl_vs', 'op 14 REDUCE / ADD words (tb_s81sl_slice_eng)', 'encoder exists only inside the slice bench; HBM '
      'Engram rows via svc not lowered')),
]


# ================================================================================================= family lowerings
# LB2-S81/CC (10-18): each unit family lowers its ops in tools/s81_dv/layer_prog/lower_<family>.py:
#   OPS = [regex ...];  lower(die, op, ctx) -> dict(status, unit, insts, gap, rows, templates, gunit_rows, svc_jobs,
#   files, events, bench).  A family result replaces the OPMAP row for the ops it claims; it may report LOWERED only
#   with a committed unit / slice bench (bench = its results dir, check.json PASS + a mutant fail witness).
def family_lowerings():
    import importlib.util
    out = []
    for f in sorted((ROOT / 'tools/s81_dv/layer_prog').glob('lower_*.py')):
        spec = importlib.util.spec_from_file_location(f.stem, f)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        out.append((f.stem[len('lower_'):], m))
    return out


def bench_ok(rel):
    """a family's LOWERED claim needs its committed bench: check.json with pass true and >= 1 failing mutant witness"""
    if not rel:
        return False, 'no bench'
    d = ROOT / rel
    c = d / 'check.json'
    if not c.exists():
        return False, f'{rel}/check.json missing'
    j = json.loads(c.read_text())
    if not j.get('pass'):
        return False, f'{rel}/check.json pass != true'
    muts = j.get('mutants') or []
    if not any(m.get('failed') and m.get('witness') and (ROOT / m['witness']).exists() for m in muts):
        return False, f'{rel}: no failing mutant with a committed witness'
    return True, rel


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
        self.files = {}
        self.port_valid = []         # [{inst, ports, bit}]: the valid bit of a lane bundle (LB2-S81/EVENTS strict check)
        self.retire_fences = []      # static END minima; never change real per-command ACK edges
        self.retire_not_before = 0

    def template(self, name, payload):
        if payload in self.templates:
            return self.templates.index(payload)
        # TOK-S81-GAPS (10-18): the table is per JOB (128 x 186 b, re-booted with each job's calendar over the host lane:
        # dsdv_seq_host 0x13, a write is legal while no job is held).  The layer's table is virtual here; finish() boots
        # only the templates a job's rows use, re-indexed (row 'tix' = the global index), and split_jobs cuts on both
        # budgets.  ctl_templates.json / events keep the global index.
        assert len(self.templates) < 1024, 'CTL template table: > 1024 distinct beats in one layer'
        self.templates.append(payload)
        self.tnames.append(name)
        return len(self.templates) - 1

    def absorb(self, fam, op, r):
        """merge one family lowering into the die programme: CTL templates are re-indexed into the shared table and
        V-row args re-pointed (arg[6:0] = the family's template index), gunit job args likewise (arg[6:0])"""
        remap = {i: self.template(f'{fam}.{n}', p) for i, (n, p) in enumerate(r.get('templates', []))}
        if 'retire_not_before' in r:
            edge = r['retire_not_before']
            if type(edge) is not int or edge < 0 or not r.get('rows'):
                raise ValueError('native static END floor requires actual rows and an integer source minimum')
            self.retire_fences.append(dict(op=op['id'], edge=edge,
                                          lifetime_qualified=bool(r.get('lifetime_qualified', False))))
            self.retire_not_before = max(self.retire_not_before, edge)
        for row in r.get('rows', []):
            row = dict(row)
            if row['eng'] in (ENG['VN'], ENG['VS'], ENG['GUNIT']) and remap and not row.get('raw_arg'):
                row['tix'] = remap[row.get('template_index', row['arg'] & 0x7F)]
                row['arg'] = (row['arg'] & ~0x7F) | (row['tix'] & 0x7F)
            row.setdefault('done', row['issue'] + SEQ['done_v'])
            if r.get('atomic'):
                row['grp'] = op['id']           # MU-DIE-S81/HOP: the op's rows stay in one issuer job (split_jobs)
            if 'retire_not_before' in r:
                row['lifetime_id'] = op['id']
            row['what'] = f"{op['id']}: {row.get('what', '')}"
            self.rows.append(row)
        self.gunit_rows += [tuple(x) for x in r.get('gunit_rows', [])]
        self.svc += r.get('svc_jobs', [])
        self.port_valid += [d for d in r.get('port_valid', []) if d not in self.port_valid]
        # family events name the family's own template index ('template N'): re-point them into the shared table
        # (LB2-S81/EVENTS: was copied unmapped -- right only while the family's templates came first)
        for e in r.get('events', []):
            e = dict(e)
            for f in ('payload', 'carried_by'):
                m = re.match(r'template (\d+)(.*)$', str(e.get(f, '')))
                if m and e['kind'] in ('CTL', 'VS') and remap:
                    e[f] = f'template {remap[int(m.group(1))]}{m.group(2)}'
            self.events.append(e)
        self.files.update(r.get('files', {}))

    def vrow(self, eng, issue, tix, ctx=0, what=''):
        assert eng in (ENG['VN'], ENG['VS'])
        self.rows.append(dict(eng=eng, issue=issue, done=issue + SEQ['done_v'], arg=(tix & 0x7F) | (ctx & 3) << 7, tix=tix,
                              what=what))


def ctl_path(die, sl):
    """seq_host vo_n / vo_s -> the slice's control plane: per-hop edges (contract model, asserted by the bench).
    V north reaches s_4N (tvN_seqhost), V south bk_sel then s_4S (tvS_seqhost, tvS_bk_sel); the column-4 slice
    re-injects on its tier line both ways (V pin -> line out V_CTL_INJECT edges through xr), rstop 2 edges a stop + the
    xr / xrE link ages between slices."""
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
    t = SEQ['v_cmd_to_vo'] + (SEQ['vo_s_land'] if tier == 'S' else 0)
    path = [dict(at='u_seqhost.vo', edge=t)]
    for where, lk in hops:
        L = die.links.get(lk)
        t += (L['age_edges'] if L else 0)
        path.append(dict(at=f'{lk} landed' if L else f'{lk} (abutted, no station / landing)', link=lk, edge=t,
                         stations=L['stations'] if L else 0, E=L['E'] if L else None))
        if where == 'u_seqhost.vo_s':
            t += BKSEL_TRANSIT                       # bk_sel rung transit: relay u_rn + ot_dsdv_vstop (dsdv_bk_sel)
    # the column-4 slice: V pin -> control plane -> line out (V_CTL_INJECT edges), then one stop per column.  An event edge
    # is the slice's landed CTL pin + RSTOP_HOP (dv_cut_replay PIN_OFFSET), so the column-4 slice's own event is vi + 2.
    t_vi = t
    t += die.timing_contract["v_ctl_inject"]
    path.append(dict(at=f'{entry} line inject', edge=t))
    if col == 4:
        t = t_vi + RSTOP_HOP
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
                'ot_s81_land E + 1 + half-cycle stations + bk_sel 3 + V inject 6 + rstop 2/stop; G8 cut_3S_ctl L0 replay measured)')


def norm_eps_bits():
    """The released checkpoint's RMSNorm epsilon, encoded as binary32."""
    config = json.loads((ROOT / 'compiler/models/deepseek-v4.1-flash/inference_config.json').read_text())
    return struct.unpack('<I', struct.pack('<f', config['norm_eps']))[0]


def lower_norm_smoke(die, prog, sl, t0, eps=None, r_h=0, r_gain=64, which='attn'):
    """slice-local hc_pre + RMSNorm + act-quant on ONE slice (the beat bench's proven sequence, issued through the
    seq_host calendar as CTL beats): HLOAD (5 leaves) -> GAIN -> NORMR per leaf (a0 = G-unit row R, a1 = global beat 5 sid + k, n = 3:
    q + BF16 family) -> xfin go (eps).  The partial / rstd / XQ edges follow from the unit latencies."""
    eps = norm_eps_bits() if eps is None else eps
    s = die.slices()[sl]
    sid, smask = s['sid'], 1 << s['sid']
    eng = ENG['VN'] if sl.endswith('N') else ENG['VS']
    cp = ctl_path(die, sl)
    lat = cp['edges']
    th = prog.template(f'{which}.HLOAD', ctl_payload(smask, 0, 0x1F, vp_cmd(VP['HLOAD'], a0=r_h)))
    tg = prog.template(f'{which}.GAIN', ctl_payload(smask, 0, 0x1F, vp_cmd(VP['GAIN'], a0=r_gain)))
    # HC pre is produced by the PREVIOUS sublayer, while post/comb are current.
    # This is the model's delayed-pre contract (run_layer: cx['pre'], then a_pre).
    # Distinct GU rows retain the previous ffn pre during the next attn HC job.
    GU_ROWS = dict(family_lowerings())['gu'].GU_ROWS
    is_ffn = which.endswith('ffn')
    r_pre = GU_ROWS['attn' if is_ffn else 'ffn']
    pre_source = 'attn.hc.coef_row0' if is_ffn else 'entry.previous_ffn.hc.coef_row0'
    tn = [prog.template(f'{which}.NORMR.k{k}', ctl_payload(smask, 0, 1 << k, vp_cmd(VP['NORMR'], a0=r_pre, a1=5 * sid + k,
                                                                                   n=3)))
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
    # A local ffn consumes attn's emitted coefficient. Attn consumes the entry
    # previous-ffn row, whose producer/transfer has NOT yet been bound by this
    # layer compiler. Never wait for current attn HC or call an absent entry
    # producer ready. The smoke calendar remains diagnostic until it is bound.
    rows_out = [e['cycle'] for e in prog.events if e.get('tag') == pre_source
                and e.get('port') == ('vo_n' if sl.endswith('N') else 'vo_s')]
    dep_shift, row_land = 0, None
    if rows_out:
        tier = 'N' if sl.endswith('N') else 'S'
        head = SEQ['v_cmd_to_vo'] + (die.links.get(f'tv{tier}_seqhost') or {}).get('age_edges', 0)
        gl = (die.links.get(f'tv{tier}_gunit') or {}).get('age_edges', 0)
        row_land = max(rows_out) + gl + (lat - head)
        need = row_land + 1 - lat                    # issue edge whose CTL beat reaches the slice after the row
        if need > t:
            dep_shift, t = need - t, need
    # one CTL beat a cycle (two CTL beats in one cycle are a sticky fault in xr); the 5 NORMs go on 5 edges
    go = []
    for k in range(5):
        prog.vrow(eng, t + k, tn[k], what=f'{which} NORMR leaf {k} {sl} (hc_pre = leaf row {r_pre})')
        prog.events.append(dict(cycle=t + k + lat, inst=sl, port=cp['entry_port'], dir='in', kind='CTL',
                                tag=f'{which}.NORMR.k{k}', payload=f'template {tn[k]}; hc_pre leaf row {r_pre}'))
        go.append(t + k + lat)
    prog.vrow(eng, t + 5, tx, what=f'{which} XFIN_GO {sl}')
    prog.events.append(dict(cycle=t + 5 + lat, inst=sl, port=cp['entry_port'], dir='in', kind='CTL', tag=f'{which}.XFIN_GO',
                            payload=f'template {tx}'))
    # derived internal / outgoing edges (plan values the bench checks at the slice boundary where they are visible)
    # NORM-DESKEW (10-25): xrt delays leaf k by 4 - k edges, the 5 partials meet on leaf 4's edge; the collector then
    # serialises them, so the last partial reaches xfin XR_DESKEW edges after the old staggered (faulting) collection
    last_partial = go[-1] + BEAT['go_to_partial_normr'] + XFIN['dl'] + XFIN['collector'] + XR_DESKEW
    rstd = last_partial + XFIN['last_partial_to_rstd']
    xq = rstd + XFIN['rstd_to_xq_ring']
    gap16 = ('the norm is lowered on ONE slice (smoke); the xfin NX snake (rstop K_NX) and the XQ all-gather are '
             'exchanges among all 16 slices whose beat cycles follow from every slice\'s go edge: the words need the '
             '16-slice norm composition (lower_norm on every slice + the snake / all-gather schedule), not compiled')
    prog.events.append(dict(cycle=last_partial, inst=sl, port='(xfin NX exchange out: ro_e / ro_w / vo)', dir='out',
                            kind='NX', tag=f'{which}.partial_roots', payload='golden-subtree roots (fixture)', plan_only=True,
                            gap=gap16))
    prog.events.append(dict(cycle=xq, inst=sl, port='ro_e / ro_w', dir='out', kind='XQ', tag=f'{which}.x_allgather',
                            payload='act-quant x beats of the slice (fixture: golden FP8 codes)', plan_only=True, gap=gap16))
    return dict(slice=sl, sid=sid, ctl_latency=cp, t_issue0=t0, last_partial=last_partial, rstd=rstd, xq_at_ring=xq,
                end=xq, templates=[th, tg] + tn + [tx], hc_pre_row=r_pre, hc_pre_row_land=row_land, dep_shift=dep_shift,
                hc_pre_source=pre_source, hc_pre_source_event_present=bool(rows_out), hc_pre_source_bound=False,
                qualification='PARTIAL: previous-sublayer pre row must have a source-bound producer and transfer')


BK_SEL_INST = 'u_bk_sel'
BK_SEL_UID = 0x5B            # die strap u_bk_sel.uid (lower_bk asserts it on the build)


def bk_drain_consumed(die, payload186):
    """RTL rule of ot_dsdv_vstop with BK_DRAIN_SINK=1 (canonical 10-24): a kind-0 V CTL beat whose payload
    p[7:0] = the BK uid and p[10:8] = op 1 (drain) is removed from the S rung at u_bk_sel (beat [28:21] / [31:29])."""
    try:
        uid = die.strap(BK_SEL_INST, 'uid')
    except (KeyError, AttributeError):
        uid = None
    return (payload186 & 0xFF) == (BK_SEL_UID if uid is None else uid) and (payload186 >> 8) & 7 == 1


def row_ctl_events(die, prog):
    """LB2-S81/EVENTS: every V calendar row (engine VN / VS) puts its CTL template on the slice control plane: the beat
    arrives at each slice of its slice mask (on the engine's tier) at issue + ctl_path edges, on the ctl_path entry port.
    Families that already state the arrival (norm smoke, vpx legs) must agree with this derivation (asserted); rows
    whose family states only the unit-side effect (vs: the s_d command, slice-internal) get their CTL event here, and
    the internal event records the arrival it rides on.  Returns the number of CTL events added."""
    have = {}
    for e in prog.events:
        if e['kind'] == 'CTL' and e['dir'] == 'in':
            have.setdefault((e['inst'], int(e['payload'].split()[1].rstrip(';'))), []).append(e['cycle'])
    sid_of = {v['sid']: k for k, v in die.slices().items()}
    added, paths = 0, {}
    arrive = {}
    for r in prog.rows:
        if r['eng'] not in (ENG['VN'], ENG['VS']):
            continue
        ti = r.get('tix', r['arg'] & 0x7F)
        mask = prog.templates[ti] & 0xFFFF
        tier = 'N' if r['eng'] == ENG['VN'] else 'S'
        if tier == 'S' and bk_drain_consumed(die, prog.templates[ti]):
            # canonical BK addressed-drain sink (COORD ruling 2026-10-24 18:55; ot_dsdv_vstop BK_DRAIN_SINK=1): the
            # u_bk_sel rung stop between u_seqhost and u_s_4S consumes a kind-0 CTL beat addressed to its uid with op 1,
            # so the beat never reaches a slice (no vi / line arrival); record the consumption only.
            prog.events.append(dict(cycle=r['issue'], inst=BK_SEL_INST, port='vi_n', dir='internal', kind='BKDRAIN',
                                    tag=f"{prog.tnames[ti]}", payload=f'template {ti}', from_row=r['issue'],
                                    note='consumed at the BK stop (addressed drain sink); no slice CTL arrival'))
            continue
        for sid in range(16):
            sl = sid_of.get(sid)
            if not (mask >> sid) & 1 or sl is None or not sl.endswith(tier):
                continue
            cp = paths.setdefault(sl, ctl_path(die, sl))
            c = r['issue'] + cp['edges']
            arrive[(r['issue'], ti, sl)] = c
            got = have.get((sl, ti), [])
            if got:
                assert c in got, f'CTL template {ti} at {sl}: family arrival {got} != row issue {r["issue"]} + path ' \
                                 f'{cp["edges"]} = {c}'
                continue
            prog.events.append(dict(cycle=c, inst=sl, port=cp['entry_port'], dir='in', kind='CTL',
                                    tag=f"{prog.tnames[ti]}", payload=f'template {ti}', from_row=r['issue']))
            have.setdefault((sl, ti), []).append(c)
            added += 1
    for e in prog.events:
        if e['kind'] == 'VS' and e.get('carried_by'):
            ti = int(e['carried_by'].split()[1])
            sl = e['inst'].split('.')[0]
            e['ctl_at'] = arrive.get((e.get('issue', e['cycle']), ti, sl))
            if e['ctl_at'] is None:
                e['why'] = f'no calendar row issues template {ti} to {sl} at {e.get("issue")}'
    return added


def _line_hop(die, tier, a, b):
    """one line stop a -> b on a tier: the slowest lane of the 1,104-b bundle + the rstop (as ctl_path)"""
    cand = [L for L in die.links.values() if any(x[0] == f'u_s_{a}{tier}' for x in L['src'])
            and any(x[0] == f'u_s_{b}{tier}' for x in L['dst'])]
    assert cand, f'no line link u_s_{a}{tier} -> u_s_{b}{tier}'
    return max(L['age_edges'] for L in cand) + RSTOP_HOP


def line_slot_conflicts(die, prog):
    """S81d-TOK 10-22 (cap30 L0..L20): the column-3 slice re-injects EVERY G-unit V CTL beat (vo_s -> u_s_3S, vo_n ->
    u_s_3N) on its tier line both ways (ot_s81sl_xr ci_dir 3'b011, hops 0), while every seq_host V calendar row's beat
    is injected both ways at column 4 (ctl_path).  ot_s81sl_rstop takes ONE source per line side and cycle (two = sticky
    fault), so a seq_host beat forwarded through column 3 (W) on the edge column 3 injects a G-unit beat -- or a G-unit
    beat forwarded through column 4 (E) on the edge column 4 injects a calendar beat -- is a static-schedule collision.
    Both copies then travel the same stops on the same edges, so an equal landed edge at any stop beyond both injectors
    (W: columns 2..0 on ri_e, E: columns 5..7 on ri_w) is the collision test.  G-unit beat model = dv_cut_replay
    derive_vctl_line_events (V landed edge = vo edge + tv<T>_gunit age; line out = landed - RSTOP_HOP + v_ctl_inject).
    Returns [(row issue, engine tier, stop, port, edge, G-unit tag, row what)]."""
    inj = die.timing_contract['v_ctl_inject']
    occ = {}
    for e in prog.events:
        if e.get('inst') != 'u_gunit' or e.get('dir') != 'out' or e.get('kind') != 'CTL' or e.get('port') not in ('vo_s', 'vo_n'):
            continue
        tier = 'S' if e['port'] == 'vo_s' else 'N'
        L = die.links.get(f'tv{tier}_gunit')
        if L is None:
            continue
        t_out = e['cycle'] + L['age_edges'] - RSTOP_HOP + inj
        for path, port in ((range(2, -1, -1), 'ri_e'), (range(4, 8), 'ri_w')):
            t, prev = t_out, 3
            for c in path:
                t += _line_hop(die, tier, prev, c)
                prev = c
                occ.setdefault((tier, c, port), {})[t] = e['tag']
    if not occ:
        return []
    paths, out = {}, []
    for r in prog.rows:
        if r['eng'] not in (ENG['VN'], ENG['VS']):
            continue
        tier = 'N' if r['eng'] == ENG['VN'] else 'S'
        for c in (2, 1, 0, 5, 6, 7):
            cp = paths.setdefault((tier, c), ctl_path(die, f'u_s_{c}{tier}'))
            t = r['issue'] + cp['edges'] - RSTOP_HOP      # the row's CTL event edge is the landed line pin + RSTOP_HOP
            tag = occ.get((tier, c, cp['entry_port']), {}).get(t)
            if tag is not None:
                out.append((r['issue'], tier, c, cp['entry_port'], t, tag, r.get('what', '')))
                break
    return out


class CalendarFull(Exception):
    pass


def split_jobs(prog, cap=NOPS - 2):
    """a layer whose calendar exceeds one ot_dsdv_fixed_issue job (NOPS rows incl. KIT / END) runs as consecutive jobs:
    rows cut in issue order, each job's issue / done rebased to its first issue (the host re-boots the next calendar
    after END: the reload is a host-lane cost the price must carry, reported in calendar.json)"""
    rows = sorted(prog.rows, key=lambda r: (r['issue'], r['eng']))
    from layer_prog.aproj_native import atomic_chunks
    chunks = atomic_chunks(rows, cap, NOPS)
    jobs = []
    for k, ch in enumerate(chunks):
        t0 = ch[0]['issue']
        jp = Prog(prog.die)
        jp.templates, jp.tnames, jp.gunit_rows = prog.templates, prog.tnames, (prog.gunit_rows if k == 0 else [])
        jp.virtual = True
        jp.rows = [dict(r, issue=r['issue'] - t0, done=(r['done'] - t0) if r['done'] else 0) for r in ch]
        ids = {r.get('lifetime_id') for r in ch}
        jp.retire_fences = [dict(f, edge=f['edge']-t0) for f in prog.retire_fences if f['op'] in ids]
        jp.retire_not_before = max((f['edge'] for f in jp.retire_fences), default=0)
        jobs.append((t0, jp))
    return jobs


def finish(prog, stage=0, kit_lead=20):
    """KIT / END rows + the host boot stream (length, BEGIN, rows, SEAL, templates, gunit rows)"""
    rows = [dict(r) for r in sorted(prog.rows, key=lambda r: (r['issue'], r['eng']))]
    seen = {}
    for r in rows:   # one command per engine per edge (fixed_issue code 9 duplicate issue)
        key = (r['eng'], r['issue'])
        assert key not in seen, f'duplicate issue engine {r["eng"]} at {r["issue"]}'
        seen[key] = 1
    endage = max(max(r['done'] for r in rows) + 4, prog.retire_not_before)
    # S81-SAFE-FIX/SH 10-19 (ot_dsdv_walk_issue, the dsdv_sh_sq ordered SRAM walker; its seal scan refuses anything else,
    # code 3): rows in non-decreasing issue order (KIT included; END last, alone), at most TWO rows on one edge, one row
    # per engine per edge, per-engine done strictly increasing, <= 8 commands of an engine outstanding.  KIT moves to the
    # first edge at or after endage - kit_lead that carries fewer than two rows; more than two native rows on one edge are
    # a schedule error here (the lowering must stagger them).
    per_edge = {}
    for r in rows:
        per_edge[r['issue']] = per_edge.get(r['issue'], 0) + 1
    bad = sorted(t for t, n in per_edge.items() if n > 2)
    if bad:
        raise SystemExit(f'walker calendar: > 2 rows on edges {bad[:8]} (ot_dsdv_walk_issue issues <= 2 rows an edge)')
    kit = max(0, endage - kit_lead)
    while per_edge.get(kit, 0) >= 2:
        kit += 1
    if kit >= endage:
        raise SystemExit(f'walker calendar: no KIT edge in [{endage - kit_lead}, {endage})')
    rows.append(dict(eng=ENG['KIT'], issue=kit, done=0, arg=0, what='KIT'))
    rows.sort(key=lambda r: (r['issue'], r['eng']))
    rows.append(dict(eng=ENG['END'], issue=endage, done=0, arg=0, what='END'))
    last_done, live = {}, {}
    for r in rows:
        if r['eng'] < ENG['KIT']:
            if r['eng'] in last_done and r['done'] <= last_done[r['eng']]:
                raise SystemExit(f'walker calendar: engine {r["eng"]} done {r["done"]} not after {last_done[r["eng"]]} '
                                 f'({r.get("what", "")})')
            last_done[r['eng']] = r['done']
            live[r['eng']] = [d for d in live.get(r['eng'], []) if d >= r['issue']] + [r['done']]
            if len(live[r['eng']]) > 8:
                raise SystemExit(f'walker calendar: engine {r["eng"]} has > 8 commands outstanding at edge {r["issue"]}')
    if len(rows) > NOPS:
        raise CalendarFull(len(rows))
    tsel = list(range(len(prog.templates)))
    if len(prog.templates) > NOPS or getattr(prog, 'virtual', False):
        tsel = sorted({r['tix'] for r in rows if 'tix' in r})
        if len(tsel) > NOPS:
            raise CalendarFull(f'{len(tsel)} templates')
        loc = {g: i for i, g in enumerate(tsel)}
        for r in rows:
            if 'tix' in r:
                r['arg'] = (r['arg'] & ~0x7F) | loc[r['tix']]
    prog.job_templates = tsel
    hs = [csr_len(len(rows)), csr_pw(0, pw_header(len(rows), stage))]
    for i, r in enumerate(rows):
        r['row76'] = pack_row(r['done'], r['issue'], r['eng'], r['arg'])
        hs += [csr_pw(a, d) for a, d in pw_row_words(i, r['row76'])]
    hs.append(csr_pw(0, pw_header(len(rows), stage, seal=True)))
    hs += [csr_template(i, prog.templates[g]) for i, g in enumerate(tsel)]
    hs += [csr_gunit(a, d) for a, d in prog.gunit_rows]
    return rows, hs, endage


def dense_stage_schedule(sched, half):
    """Select actual split-stage operations; preserve external dependency obligations.

    A owns only its a_proj subset. B owns the remaining subset and reachable
    downstream operations. These are source compilation schedules; inherited
    model ages do not establish a measured stage completion time.
    """
    assert half in ('A', 'B')
    ap = [o for o in sched['ops'] if o['op'] == 'attn.a_proj']
    if len(ap) != 1:
        raise ValueError('DENSE2 stage selection requires exactly one attn.a_proj')
    ids = {ap[0]['id']}
    if half == 'B':
        while True:
            nxt = ids | {d['dst'] for d in sched['deps'] if d['src'] in ids}
            if nxt == ids:
                break
            ids = nxt
    t0 = ap[0]['start']
    ops = [dict(o, start=round(o['start']-t0, 1), end=round(o['end']-t0, 1))
           for o in sched['ops'] if o['id'] in ids]
    boundary = dict(half=half, full_stage_qualified=False, date_status='INHERITED_MODEL_ONLY',
                    original_aproj_start=t0,
                    incoming=[d for d in sched['deps'] if d['dst'] in ids and d['src'] not in ids],
                    outgoing=[d for d in sched['deps'] if d['src'] in ids and d['dst'] not in ids],
                    excluded=[o['id'] for o in sched['ops'] if o['id'] not in ids],
                    obligation='actual input arrival, A-to-B row carriage, source capture completion and local static dates remain required')
    return dict(sched, ops=ops, deps=[d for d in sched['deps'] if d['src'] in ids and d['dst'] in ids],
                span=max(o['end'] for o in ops), crit=sum(o['cycles'] for o in ops if o['critical']),
                dense_stage=boundary)


def compile_layer(layer, out, tree, sl='s_0S', smoke=True, workload=None, fixtures=None, svc_tag=0, mu_ctx=False, svc_owner_epoch=None, dense_stage=None, line_avoid=None, entry_norm=False):
    if entry_norm and not fixtures:
        raise ValueError('--entry-norm-check needs --fixtures (the layer-entry inputs and the reference model checks)')
    if dense_stage is not None and mu_ctx:
        raise ValueError('DENSE2 MU requires the corrected per-position static stage graph binding')
    if svc_owner_epoch is not None and mu_ctx:
        raise ValueError('SO source-owner fields require per-user MU remapping before admission')
    out = Path(out)
    (out / 'prog' / 'frame_cfg7').mkdir(parents=True, exist_ok=True)
    die = Die(tree)
    wl = workload or ('mtp' if layer == 'mtp_draft' else 'ar')
    sched = layer_schedule(tree, layer, wl)
    if dense_stage is not None:
        required = dict(OT_XS_DENSE_SPLIT2=dense_stage, OT_XS_APROJ_TOPO='1',
                        OT_XS_APROJ_ALIGN4='1', OT_XS_APROJ_RANK_TAGS='1', OT_XS_APROJ_CAP_PLAN='1')
        if any(os.environ.get(k) != v for k, v in required.items()):
            raise ValueError('configured DENSE2 stage requires explicit aligned topology/rank/capture options: '+str(required))
        sched = dense_stage_schedule(sched, dense_stage)
        (out / 'prog/dense_stage_boundary.json').write_text(json.dumps(sched['dense_stage'], indent=1)+'\n')
    sl = sl if sl.startswith('u_') else f'u_{sl}'
    prog = Prog(die)
    prog.mu_ctx = mu_ctx
    low = []
    fams = family_lowerings()
    ctx = dict(layer=layer, slice=sl, sched=sched, fixtures=Path(fixtures) if fixtures else None, svc_tag=svc_tag,
               svc_owner_epoch=svc_owner_epoch, line_avoid={k: frozenset(v) for k, v in (line_avoid or {}).items()})
    for o in sched['ops']:
        unit, st, gap = op_unit(o['op'])
        rec = dict(id=o['id'], op=o['op'], start=o['start'], end=o['end'], unit=unit, status=st,
                   gap=dict(module=gap[0], port=gap[1], missing=gap[2]) if gap and st != 'LOWERED' else None)
        for fam, m in fams:
            if not any(re.search(rx, o['op']) for rx in m.OPS):
                continue
            r = m.lower(die, o, dict(ctx, t_issue=int(math.floor(o['start']))))
            st = r.get('status', 'GAP')
            if st == 'LOWERED':
                ok, why = bench_ok(r.get('bench'))
                if not ok:
                    st, r['gap'] = 'PARTIAL', dict(module=f'lower_{fam}', port='bench', missing=why)
            rec.update(unit=r.get('unit', unit), status=st, family=fam, insts=r.get('insts', []), bench=r.get('bench'),
                       gap=r.get('gap') if st != 'LOWERED' else None)
            if r.get('native_programme'):
                rec.update(native_rows=len(r['rows']), sealed_programme_held=True,
                           lifetime_qualified=bool(r.get('lifetime_qualified', False)),
                           retire_not_before=r['retire_not_before'])
            prog.absorb(fam, o, r)
            break
        low.append(rec)
    sub = None
    if layer != 'head' and not any(x.get('family') for x in low if x['op'].endswith('attn.quant')):
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
    n_row_ctl = row_ctl_events(die, prog)
    clash = line_slot_conflicts(die, prog)
    if clash:
        # the vs calendar rows are free to move (their unit-side events follow the row); any other V row is pinned by a
        # family-stated arrival -> fail closed.  Re-lower with the clashing issue edges reserved (lower_vs skips them).
        pinned = [c for c in clash if ': vs ' not in c[6]]
        if pinned:
            raise ValueError(f'line slot collision of a pinned V calendar row with a G-unit V CTL re-injection: {pinned[:4]}')
        avoid = {k: set(v) for k, v in (line_avoid or {}).items()}
        for issue, tier, *_ in clash:
            avoid.setdefault(tier, set()).add(issue)
        if sum(len(v) for v in avoid.values()) > 64:
            raise ValueError(f'line slot reservation does not converge: {clash[:4]}')
        return compile_layer(layer, out, tree, sl, smoke=smoke, workload=workload, fixtures=fixtures, svc_tag=svc_tag,
                             mu_ctx=mu_ctx, svc_owner_epoch=svc_owner_epoch, dense_stage=dense_stage, line_avoid=avoid,
                             entry_norm=entry_norm)
    prog.line_avoid = {k: sorted(v) for k, v in (line_avoid or {}).items()}
    if entry_norm:
        # TOK-DS-GAPS 10-24 (opt-in; default byte-identical): layer-entry residency of the smoke slice as pre-layer CTL
        # target-5 events + the xfin NX flit as checked output words (layer_prog/norm_nx.py).  After row_ctl_events
        # and the line-slot pass: the entry beats are not calendar rows and carry an explicit payload186.
        if sub is None or not str(sub.get('hc_pre_source', '')).startswith('entry.'):
            raise ValueError('--entry-norm-check: no attn norm smoke on this layer (the NX flit needs the attn norm)')
        sys.path.insert(0, str(ROOT / 'tools/s81_dv/layer_prog'))
        import norm_nx
        if entry_norm == 'all':
            # the 16-slice composition: every slice's norm + entry state + the snake flit words (own + forwards)
            sub['entry_norm'] = norm_nx.emit_all(die, prog, sub, fixtures, sys.modules[__name__])
            clash = line_slot_conflicts(die, prog)
            if clash:
                raise ValueError(f'--entry-norm-check all: line slot collision of the 16-slice norm rows: {clash[:4]}')
        else:
            sub['entry_norm'] = norm_nx.emit(die, prog, sub, fixtures,
                                             [e['cycle'] for e in prog.events if e['kind'] == 'CTL'])
    files = {}
    for rel, text in prog.files.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(text)
    if prog.rows:
        # S81-SAFE-FIX/SH 10-19: off-path rows before the layer entry (S81-L20: the entry is t0 = 0, Engram prefetch rows
        # start earlier) have NEGATIVE issue edges; packed as 24-b rows they read as ~16.7M and never issue on any issuer
        # (ot_dsdv_walk_issue refuses the seal, code 3).  A single job is rebased to its first issue, as split_jobs does.
        t0s = min(0, min(r['issue'] for r in prog.rows))
        if t0s < 0:
            for r in prog.rows:
                r['issue'] -= t0s
                r['done'] -= t0s
            if prog.retire_fences:
                prog.retire_not_before -= t0s
            prog.retire_fences = [dict(f, edge=f['edge']-t0s) for f in prog.retire_fences]
        try:
            jobs = [(t0s, prog, finish(prog))]
        except CalendarFull:
            if t0s < 0:
                for r in prog.rows:
                    r['issue'] += t0s
                    r['done'] += t0s
                if prog.retire_fences:
                    prog.retire_not_before += t0s
                prog.retire_fences = [dict(f, edge=f['edge']+t0s) for f in prog.retire_fences]
            jobs = [(t0, jp, finish(jp)) for t0, jp in split_jobs(prog)]
        # TOK-S81-GAPS/CTL (10-19): the svc job tag is {issuer context slot, calendar row index} (dsdv_seq_host j_o =
        # {v, arg, cd[83] slot, cd[6:0] op}; ot_dsdv_fixed_issue OP_BASE 0), known only once the calendar is sorted;
        # the q-frame headers and the SVCJ words carry it (lower_svc tag_rule).  G8 cut_3S_ctl L0: s_j left with tag
        # 0x5c (row 92) against the compiled 0x00.  Re-lower once with the final tag (row order does not depend on it).
        need = {(k & 1) << 7 | i for k, (_, _, (rows, _, _)) in enumerate(jobs) for i, r in enumerate(rows)
                if r['eng'] == ENG['SVC']}
        assert len(need) <= 1, f'more than one svc job row ({sorted(need)}): one tag per layer is modelled'
        if need and need != {svc_tag} and prog.svc:
            return compile_layer(layer, out, tree, sl, smoke=smoke, workload=workload, fixtures=fixtures,
                                 svc_tag=need.pop(), mu_ctx=mu_ctx, svc_owner_epoch=svc_owner_epoch, dense_stage=dense_stage, line_avoid=line_avoid,
                                 entry_norm=entry_norm)
        cal = []
        for k, (t0, jp, (rows, hs, endage)) in enumerate(jobs):
            jd = '' if len(jobs) == 1 else f'job{k}/'
            (out / 'prog' / jd).mkdir(parents=True, exist_ok=True)
            (out / f'prog/{jd}host_boot.memh').write_text(memh(hs, 515))
            files[f'prog/{jd}host_boot.memh'] = len(hs)
            cal.append(dict(job=k, layer_issue0=t0, nops=len(rows), end_age=endage, host_words=len(hs),
                            retire_not_before=jp.retire_not_before, retire_fences=jp.retire_fences,
                            sealed_programme_held=any(not f['lifetime_qualified'] for f in jp.retire_fences),
                            templates=list(jp.job_templates),
                            reload_edges=len(hs) * HOST_SLOT,
                            rows=[dict(i=i, issue=r['issue'], done=r['done'], engine=r['eng'], arg=r['arg'],
                                       row76=f"{r['row76']:019x}", what=r['what']) for i, r in enumerate(rows)]))
        (out / 'prog/calendar.json').write_text(json.dumps(dict(
            schema='opentallas.s81_dv.calendar.v2', jobs=len(cal), stage=0, rows_total=len(prog.rows),
            sealed_programme_held=any(not f['lifetime_qualified'] for f in prog.retire_fences),
            note='one ot_dsdv_fixed_issue job holds NOPS = 128 rows incl. KIT / END; more rows = consecutive jobs, '
                 'each re-booted over the host lane after the previous END (reload_edges = host words x HOST_SLOT)',
            nops=cal[0]['nops'], end_age=cal[0]['end_age'], rows=cal[0]['rows'], job=cal), indent=1) + '\n')
    (out / 'prog/ctl_templates.json').write_text(json.dumps(dict(
        schema='opentallas.s81_dv.ctl_templates.v1', n=len(prog.templates),
        templates=[dict(i=i, name=n, payload186=f'{p:047x}', beat=f'{ctl_line_beat(p):053x}')
                   for i, (n, p) in enumerate(zip(prog.tnames, prog.templates))]), indent=1) + '\n')
    (out / 'prog/gunit_rows.json').write_text(json.dumps(dict(rows=[dict(a=a, d=f'{d:064x}') for a, d in prog.gunit_rows],
                                                             note=f'{len(prog.gunit_rows)} rows'), indent=1) + '\n')
    (out / 'prog/svc_jobs.json').write_text(json.dumps(dict(jobs=prog.svc, note=f'{len(prog.svc)} jobs'),
                                                       indent=1) + '\n')
    stat = {}
    for x in low:
        stat[x['status']] = stat.get(x['status'], 0) + 1
    links = {k: v for k, v in die.links.items() if any(s_[0] in (sl, 'u_seqhost', 'u_bk_sel') for s_ in v['src'] + v['dst'])
             or k.startswith(('tvS_seqhost', 'tvN_seqhost', 'tvS_bk_sel'))}
    (out / 'schedule.json').write_text(json.dumps(dict(
        schema='opentallas.s81_dv.layer_schedule.v1', layer=layer, workload=wl, slice=sl,
        dense_stage=sched.get('dense_stage'),
        timing_contract=die.timing_contract,
        composition='the layer = the slowest (critical) slice under the fixed schedule: every slice runs the same '
                    'calendar shifted by its CTL arrival; the layer span is max over slices and units of the last '
                    'scheduled event (op schedule span below = the priced critical slice)',
        price=dict(span=sched['span'], crit=sched['crit'], source=sched['price_source'],
                   capture_extra_edges=sched['capture_extra_edges']),
        ops=sched['ops'], deps=sched['deps'], smoke=sub, line_slot_reserved=getattr(prog, 'line_avoid', {}), events=sorted(prog.events, key=lambda e: e['cycle']),
        event_words='LB2-S81/EVENTS: an encoded boundary event carries words [[edge, value hex, mask hex]] on `ports` '
                    '(LSB-first); dir in: the edge the consumer pin\'s landed register takes the value; dir out: the '
                    'edge the producer\'s output register takes it; boundary offdie = beyond the die\'s elastic link '
                    'layer (no fixed-cycle cut word); dir internal = inside one instance, carried_by its CTL template',
        row_ctl_events=n_row_ctl, port_valid=prog.port_valid, links=links), indent=1) + '\n')
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
               timing_contract=die.timing_contract,
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
    ap.add_argument('--fixtures', default=None, help='the layer fixture dir (dv_layer_fixtures.py output)')
    ap.add_argument('--svc-owner-epoch', type=int, choices=range(4), default=None,
                    help='Opt-in static SO launch-owner fields in CFG; source binding required')
    ap.add_argument('--dense-stage', choices=('A', 'B'),
                    help='Actual DENSE2 stage operation selection; requires explicit topology/alignment/rank/capture env options')
    ap.add_argument('--entry-norm-check', nargs='?', const='smoke', choices=('smoke', 'all'), default=None,
                    help='TOK-DS-GAPS: emit the smoke slice\'s layer-entry rows (pre-layer CTL target 5) and its attn '
                         'xfin NX flit as checked output words (needs --fixtures; layer_prog/norm_nx.py); "all" = every '
                         'slice\'s norm + entry state + the 16-flit snake words')
    a = ap.parse_args(argv)
    if a.dense_stage is not None and (a.mu_cal or a.mu_ctx):
        ap.error('--dense-stage MU requires corrected per-position static stage graph binding')
    if a.svc_owner_epoch is not None and a.mu_cal:
        ap.error('--svc-owner-epoch requires per-user owner remapping before --mu-cal')
    if a.mu_cal:
        t = mu_slot_tables(json.loads(Path(a.mu_cal).read_text()), a.layer)
        Path(a.out, 'prog').mkdir(parents=True, exist_ok=True)
        Path(a.out, 'prog/mu_slots.json').write_text(json.dumps(t, indent=1) + '\n')
        print(f"MU {a.layer} {t['group']}: {len(t['rows'])} slots, copies {t['copies']} {t['users_per_copy']}, "
              f"lemma {t['lemma']}")
        if a.layer not in LAYERS:
            return
    tree = die_tree(a.die_ref, a.die_src)
    r = compile_layer(a.layer, a.out, tree, a.slice, workload=a.workload, fixtures=a.fixtures, mu_ctx=a.mu_ctx,
                      svc_owner_epoch=a.svc_owner_epoch, dense_stage=a.dense_stage, entry_norm=a.entry_norm_check)
    print(json.dumps(dict((k, v) for k, v in r.items() if k != 'smoke'), indent=None))
    if r['smoke']:
        s = r['smoke']
        print(f"SMOKE {s['slice']} sid {s['sid']}: CTL latency {s['ctl_latency']['edges']} edges, last partial "
              f"{s['last_partial']}, rstd {s['rstd']}, XQ at ring {s['xq_at_ring']}")


if __name__ == '__main__':
    main()
