#!/usr/bin/env python3
"""Die-top interface / connectivity lint (CLAUDE DIE-LINT, 2026-10-06).

Elaboration / lint only.  The die tops are the structural netlists the die floorplan generators emit
(tools/dsrom_s81_fulldie.py write_netlist, tools/hbm_accel_die_fp.py write_netlist): every die-level bus, every block
instance, no top-level ports.  This tool rebuilds each die model exactly as the generator does, binds

  * REAL blocks (the RTL or hardened black-box view exists) by their real port declarations, and
  * every placeholder master by a PORT-IDENTICAL REGISTERED STUB (its generated abstract's ports and widths; outputs
    from flops),

and checks: port lists against definitions, undriven / unloaded / multi-driven / floating net bits, width truncation,
duplicate port bindings, clock and reset connectivity, top I/O, the meso-FIFO / forwarded-link instantiation gap,
and the physical defect classes found on the DS dies (replicated copies missing their own pins, compute abutting the
hub band without a channel, pin faces oriented away from their peer, pin spread against the macro face).

Directions of placeholder ports are not in the generated abstracts (every generated pin is INOUT); they are declared
here per bus class (DIRECTION MODEL below), from the generator's own comments and port names.  A real endpoint always
uses its RTL direction; a placeholder peer of a real endpoint takes the complement.

Modes:
  lint  --die {s81_layer,s81_head,hbm} [--top-fix] --out DIR   python graph + physical lint, findings JSON,
                                                              Verilog die top + stubs + file list for Verilator
  abstracts --out DIR                                          HBM die: hardened abstracts the real placement needs
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as S  # noqa: E402
import hbm_accel_die_fp as H  # noqa: E402
import qwen_rom_fulldie as Q  # noqa: E402

OUT = 'results/rtl/die_top_lint_20261006'


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ RTL port parser
def clog2(v):
    v = int(v)
    return 0 if v <= 1 else (v - 1).bit_length()


def _strip(t):
    t = re.sub(r'/\*.*?\*/', '', t, flags=re.S)
    t = re.sub(r'//[^\n]*', '', t)
    return re.sub(r'^\s*`(ifdef|ifndef|else|endif|elsif)\b[^\n]*', '', t, flags=re.M)


def _eval(expr, env):
    e = expr.replace('$clog2', 'clog2')
    e = re.sub(r"\d+'[dD](\d+)", r'\1', e)
    return int(eval(e, {'clog2': clog2, '__builtins__': {}}, dict(env)))  # noqa: S307


def parse_module(path, module, params=None):
    """{'params': {...}, 'ports': {name: (dir, width)}} of an ANSI module header."""
    t = _strip((ROOT / path).read_text())
    mm = re.search(r'\bmodule\s+' + re.escape(module) + r'\b', t)
    if not mm:
        raise KeyError(f'{module} not in {path}')
    i = mm.end()
    env = {}
    rest = t[i:]
    k = 0
    while rest[k].isspace():
        k += 1
    if rest[k] == '#':
        j = rest.index('(', k)
        depth, q = 0, j
        while True:
            c = rest[q]
            depth += c == '('
            depth -= c == ')'
            if depth == 0:
                break
            q += 1
        ptxt = rest[j + 1:q]
        for pm in re.finditer(r'parameter\s+(?:integer|int|bit|logic|signed|unsigned|\s)*\s*([A-Za-z_]\w*)\s*=\s*([^,;]+)',
                              ptxt):
            try:
                env[pm.group(1)] = _eval(pm.group(2).strip(), env)
            except Exception:  # noqa: BLE001  string parameters
                env[pm.group(1)] = pm.group(2).strip()
        k = q + 1
    env.update(params or {})
    j = rest.index('(', k)
    depth, q = 0, j
    while True:
        c = rest[q]
        depth += c == '('
        depth -= c == ')'
        if depth == 0:
            break
        q += 1
    body = rest[j + 1:q]
    ports = {}
    cur_dir, cur_w = None, 1
    for ent in re.split(r',(?![^\[]*\])', body):
        ent = ent.strip()
        if not ent:
            continue
        dm = re.match(r'(input|output|inout)\b\s*(?:wire|reg|logic|var)?\s*(?:signed|unsigned)?\s*(\[[^\]]+\])?\s*'
                      r'([A-Za-z_]\w*)$', ent)
        if dm:
            cur_dir = dm.group(1)
            if dm.group(2):
                hi, lo = dm.group(2)[1:-1].split(':')
                cur_w = abs(_eval(hi, env) - _eval(lo, env)) + 1
            else:
                cur_w = 1
            ports[dm.group(3)] = (cur_dir, cur_w)
        else:
            nm = re.match(r'([A-Za-z_]\w*)$', ent)
            if nm and cur_dir:
                ports[nm.group(1)] = (cur_dir, cur_w)
            else:
                raise ValueError(f'{path}:{module}: cannot parse port entry {ent!r}')
    return dict(params={k_: v for k_, v in env.items()}, ports=ports)


# ------------------------------------------------------------------------------------------------ real blocks
def _bus(base, n):
    return [f'{base}[{i}]' for i in range(n)]


def _pin_base(pn):
    mm = re.match(r'^(.*)\[(\d+)\]$', pn)
    return (mm.group(1), int(mm.group(2))) if mm else (pn, 0)


# SM element layouts of the die bundles (bit 0 first).  None = no RTL pin behind that bundle bit.
SM_LAYOUT = dict(
    d=['rsp_v'] + _bus('rsp_tag', 10) + _bus('rsp_data', 1088) + [None],                 # W_LINE 1100: +ready
    q=['req_v'] + _bus('req_addr', 32) + _bus('req_tag', 10) + ['req_ready'] + [None] * 4,  # W_REQ 48
    x=['xw_en'] + _bus('xw_addr', 7) + _bus('xw_grp', 7) + _bus('xw_data', 2048),         # W_X 2063
    r=['rv'] + _bus('rrow', 12) + _bus('rdata', 256) + ['fault'],                          # W_RES 270
    c=['start'] + _bus('op_rows', 13) + _bus('op_c', 16) + _bus('op_g', 8) + ['op_gs'] + _bus('op_fmt', 2)
      + ['release_in', 'busy', 'arrive', 'released'],                                     # W_CTL 45
    ck=['clk', 'rst_n', None])
RETN_LAYOUT = {p: [f'{p}_v'] + _bus(f'{p}_t', 32) + _bus(f'{p}_d', 32) + [f'{p}_e'] for p in 'abo'}


def real_blocks(die):
    """master -> dict(module, file, params, ports, binding{die port: [rtl pin names or None]}, kind)."""
    out = {}
    if die.startswith('s81r8'):
        return real_blocks_r8(die)
    if die.startswith('s81'):
        rp = S.real_ports()
        files = {S.real_lef(S.Q_LEF)['name']: ('rtl/v41rom/ot_v41_rom_elem_q_qp_w10.sv', 'routed RTL (NB=2 receipt params)',
                                                dict(NB=2, MTP=1, EARLY=1, FAST=1, PP=1, QTIMING_FIX=1, QPIPE=1, QP_XS=1,
                                                     QP_CAP=0, QP_P1=1, QP_CSAM=10)),
                 'ot_rom_4096x72_m8': ('physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v',
                                       'hard macro black box', {}),
                 'ot_hbm3e_phy_v41x_aw30_e8p5': ('physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/'
                                                 'ot_hbm3e_phy_v41x_aw30_e8p5_bb.v', 'hard macro black box', {}),
                 'ot_pdie_serdes': ('physical/asap7_v41x_pdie_macros_v2/ot_pdie_serdes/ot_pdie_serdes_bb.v',
                                    'placeholder hard macro black box', {}),
                 'ot_pdie_ucie': ('physical/asap7_v41x_pdie_macros_v2/ot_pdie_ucie/ot_pdie_ucie_bb.v',
                                  'placeholder hard macro black box', {})}
        for mst, (f, kind, prm) in files.items():
            pm = parse_module(f, mst, prm)
            out[mst] = dict(module=mst, file=f, kind=kind, params=prm, ports=pm['ports'], binding=rp[mst])
        pm = parse_module('rtl/v41die/ot_v41_retn_w17w10.sv', 'ot_v41_retn_w17w10')
        out['dsfd_node'] = dict(module='ot_v41_retn_w17w10', file='rtl/v41die/ot_v41_retn_w17w10.sv',
                                kind='RTL (the slot is sized for this node; the die master dsfd_node is its placeholder)',
                                params={}, ports=pm['ports'], binding=RETN_LAYOUT)
    else:
        rp = {k_: dict(v_) for k_, v_ in H.real_ports().items()}
        for mst in ('ot_pdie_serdes', 'ot_pdie_ucie'):     # TF5: even tx / rx split of a narrower chain
            rp[mst]['iox'] = SplitIO()
        for mst, f, kind in (('ot_hbm3e_phy_v41x_aw30_e8p5', 'physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/'
                              'ot_hbm3e_phy_v41x_aw30_e8p5_bb.v', 'hard macro black box'),
                             ('ot_pdie_serdes', 'physical/asap7_v41x_pdie_macros_v2/ot_pdie_serdes/ot_pdie_serdes_bb.v',
                              'placeholder hard macro black box'),
                             ('ot_pdie_ucie', 'physical/asap7_v41x_pdie_macros_v2/ot_pdie_ucie/ot_pdie_ucie_bb.v',
                              'placeholder hard macro black box')):
            pm = parse_module(f, mst)
            out[mst] = dict(module=mst, file=f, kind=kind, params={}, ports=pm['ports'], binding=rp[mst])
        prm = json.loads((ROOT / H.PORTMAP).read_text())['DS']['SM_parameters']
        prm.update(DS=3, DG=3, DW=4, PIO=2)          # sm_r2 capture.json (the placed context's selection)
        pm = parse_module('rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv', 'ot_hbm_accel_sm_v', prm)
        lay = dict(SM_LAYOUT)
        if TOP_FIX:          # TF7
            lay['d'] = SM_LAYOUT['d'][:-1]
            lay['q'] = SM_LAYOUT['q'][:44]
        out['hfd_sm'] = dict(module='ot_hbm_accel_sm_v', file='rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv',
                             kind='RTL (sm_r2 parameters; hardened sub-views tc16 / bd_col / ring SRAM only)',
                             params=prm, ports=pm['ports'], binding=lay)
    return out


R8 = {}      # die -> built r8 model (real_blocks_r8 needs the generated glue port lists)


def real_blocks_r8(die):
    """S81 r8 (S81-DIE): q element, cfg ROM, PHY, links by their RTL / bb ports (r8 binding); the cfg sequencer
    (hand RTL) and every generated glue master (results/.../r8/dsfd_glue.sv) by their own port lists."""
    m = R8[die]
    rp = S.real_ports_r8()
    out = {}
    files = {S.real_lef(S.Q_LEF)['name']: ('rtl/v41rom/ot_v41_rom_elem_q_qp_w10.sv', 'routed RTL (NB=2 receipt params)',
                                            dict(NB=2, MTP=1, EARLY=1, FAST=1, PP=1, QTIMING_FIX=1, QPIPE=1, QP_XS=1,
                                                 QP_CAP=0, QP_P1=1, QP_CSAM=10)),
             'ot_rom_4096x72_m8': ('physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8_bb.v',
                                   'hard macro black box', {}),
             'ot_hbm3e_phy_v41x_aw30_e8p5': ('physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/'
                                             'ot_hbm3e_phy_v41x_aw30_e8p5_bb.v', 'hard macro black box', {}),
             'ot_pdie_serdes': ('physical/asap7_v41x_pdie_macros_v2/ot_pdie_serdes/ot_pdie_serdes_bb.v',
                                'placeholder hard macro black box', {}),
             'ot_pdie_ucie': ('physical/asap7_v41x_pdie_macros_v2/ot_pdie_ucie/ot_pdie_ucie_bb.v',
                              'placeholder hard macro black box', {})}
    for mst, (f, kind, prm) in files.items():
        pm = parse_module(f, mst, prm)
        out[mst] = dict(module=mst, file=f, kind=kind, params=prm, ports=pm['ports'], binding=rp[mst])
    used = {it.master for it in m['insts']}
    for mst in sorted(used):
        if S.is_glue(mst) or mst == 'ot_s81_cfg7_seq':
            f = S.CFG7_RTL if mst == 'ot_s81_cfg7_seq' else S.GLUE_RTL
            pm = parse_module(f, mst)
            out[mst] = dict(module=mst, file=f, kind='glue RTL (S81-DIE)', params={}, ports=pm['ports'],
                            binding={p: (_bus(p, w) if w > 1 or True else [p]) for p, (d, w) in pm['ports'].items()})
    return out


class SplitIO(list):
    """Binding list whose prefix [:n] is tx[0:n/2] + rx[0:n/2] (what a chain of n bits needs)."""
    def __getitem__(self, k):
        if isinstance(k, slice) and k.start is None and k.step is None:
            n = k.stop
            h = (n + 1) // 2
            return _bus('tx', 512)[:h] + _bus('rx', 512)[:n - h]
        raise TypeError('SplitIO supports [:n] only')

    def __len__(self):
        return 1024


# Placeholder masters with an RTL counterpart that is NOT bound here (no die-bundle binding is defined): their port
# lists are compared by bit totals only.
COUNTERPARTS = {
    'hbm': {
        'hfd_coll': ('rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv', 'ot_hbm_accel_tu_endpoint'),
        'hfd_loader': ('rtl/hbm_accel/loader/ot_hbm_accel_loader_host.sv', 'ot_hbm_accel_loader_host'),
        'hfd_index_q': ('rtl/hbm_accel/index/ot_hbm_accel_index_path.sv', 'ot_hbm_accel_index_path'),
        'hfd_attn_tile': ('rtl/hbm_accel/ot_attn_tile_registered_parent.sv', 'ot_attn_tile_registered_parent'),
    },
    's81': {},
}
FWD_STAGE = ('rtl/common/ot_fwd_link_stage.sv', 'ot_fwd_link_stage')
MESO = ('rtl/common/ot_meso_fifo.sv', 'ot_meso_fifo')


# ------------------------------------------------------------------------------------------------ die models
TOP_FIX = False
# Top-level instantiation fixes (--top-fix).  Each one changes only die-top connectivity / instance orientation, never a
# block; the generators' adopted records are untouched (their owners port these, see FINDINGS.md).
TOP_FIXES = {
    'TF1_clock_domain_nets': 'one 1-bit PLL output port and ONE multi-load net per clock domain (stream / serial / hbm; the '
                             '2 shield tracks are a routing rule, not netlist bits) instead of '
                             'N two-pin nets all bound to the single port pll (duplicate named-port connection: the '
                             'generated top does not elaborate)',
    'TF2_all_sms_clocked': 'HBM: every SM of a group on the clk_stream net (generated: sms[0] of each group only, 28 of 32 '
                           'SMs unclocked)',
    'TF3_tiles_clocked': 'HBM: the 64 attention tiles on clk_stream (generated: not on any clock net)',
    'TF4_link_macro_clk': 'SerDes / UCIe parallel-side clk on clk_stream (generated: unbound on every link macro)',
    'TF5_link_tx_rx_split': 'HBM: link chain 971 -> 974 b bound tx[486:0] + rx[486:0] per macro (generated: tx[511:0] + '
                            'rx[458:0]: RX 9 x 459 = 4,131 b < 8 TU ports x (545 flit + valid + credit) = 4,376 b, the '
                            'ot_hbm_accel_tu_endpoint ph_rx side); host chain 512 b bound '
                            'tx[255:0] + rx[255:0] (generated: tx[511:0], NO receive pins)',
    'TF6_sm_orientation': 'HBM: S-side SM groups un-mirrored about x (generator flip = (side == N) != (None and ...) is '
                          'True for S too: all 16 S SMs placed MX / R180, d / q faces away from their stream service, '
                          'c away from the hub); fixed by passing row1_flip=False',
    'TF7_sm_bundle_widths': 'HBM: weight line 1100 -> 1099 b and request 48 -> 44 b to match ot_hbm_accel_sm_v (no '
                            'rsp_ready pin; 4 unused request bits)',
}


def fix_clock_nets(m, die):
    by = {it.name: it for it in m['insts']}
    B = [b for b in m['buses'] if b[1] != 'clock_trunk']
    if die.startswith('s81'):
        src = m['hub']['collective'].name
        dom = defaultdict(list)
        for b in m['buses']:
            if b[1] == 'clock_trunk':
                for inst, port in b[3]:
                    if port == 'ck':
                        dom['serial' if by[inst].domain == 'serial_0p9' else 'stream'].append((inst, 'ck'))
        dom['stream'] += [(lk.name, 'ck') for lk in m['links']]
    else:
        src = m['hub']['coll'].name
        dom = defaultdict(list)
        for it in m['insts']:
            if it.kind == 'sm' or it.kind == 'attn_tile' or it.kind == 'link':
                dom['stream'].append((it.name, 'ck'))
            elif it.kind in ('hub', 'spine') and it.name != src:
                dom['serial' if it.domain == 'serial_0p9' else 'stream'].append((it.name, 'ck'))
            elif it.kind == 'svc':
                dom['hbm'].append((it.name, 'ck'))
    for d, eps in sorted(dom.items()):
        B.append((f'clk_{d}', 'clock_trunk', 1, [(src, f'pll_{d}')] + eps))    # one clock signal (shields: route rule)
    m['buses'] = B


def fix_hbm_links(m):
    B = []
    for bid, cls, bits, eps in m['buses']:
        if cls == 'link':           # per direction: 8 ports x (545 flit + valid + credit) = 4,376 b (TU endpoint RTL)
            bits = 2 * math.ceil(H.TU_PORTS * (545 + 2) / len(m['links']))
        if cls in ('link', 'host'):
            eps = [(i, 'iox' if p == 'io' else p) for i, p in eps]
        if cls == 'weight':
            bits = H.W_LINE - 1
        if cls == 'weight_req':
            bits = 44
        B.append((bid, cls, bits, eps))
    m['buses'] = B


def build(die, top_fix=False):
    global TOP_FIX
    TOP_FIX = top_fix
    if die.startswith('s81r8'):
        S.configure('layer' if die == 's81r8_layer' else 'head', 'r8')
        m = S.build()
        S.finalize_r8(m)
        R8[die] = m
        return m, S.port_widths(m, 1), S.masters(m, 1), 'tools/dsrom_s81_fulldie.py --gen r8'
    if die.startswith('s81'):
        S.configure('layer' if die == 's81_layer' else 'head')
        m = S.build()
        if top_fix:
            fix_clock_nets(m, die)
        ports_w = S.port_widths(m, 1)
        M = S.masters(m, 1)
        if top_fix:
            col = M[m['hub']['collective'].master]
            col.face('pll_stream', 1, 'E', 'M4', col.h * 0.25 - 20.0, 1)
            col.face('pll_serial', 1, 'E', 'M4', col.h * 0.25 + 20.0, 1)
        tool = 'tools/dsrom_s81_fulldie.py'
    else:
        m = H.build(dict(H.ADOPTED, row1_flip=False) if top_fix else None)
        if top_fix:
            fix_clock_nets(m, die)
            fix_hbm_links(m)
        ports_w = H.port_widths(m, 1)
        M = H.masters(m, 1)
        tool = 'tools/hbm_accel_die_fp.py'
    return m, ports_w, M, tool


# ------------------------------------------------------------------------------------------------ DIRECTION MODEL
R8_ACTIVE = [False]


def flow(j, bits, down, first_up=True):
    """2-sided bundle, endpoint 0 upstream: bits [0, down) flow downstream, [down, bits) upstream."""
    up_, dn_ = ('out', 'in') if j == 0 else ('in', 'out')
    seg = []
    if down > 0:
        seg.append((0, min(down, bits), up_))
    if bits > down:
        seg.append((down, bits, dn_))
    return seg


def dirs_s81(bid, cls, bits, eps, j, port):
    if R8_ACTIVE[0]:                  # r8 convention: endpoint 0 drives every net; the PHY DFI bundle is complemented
        if cls == 'phy_dfi':
            return 'complement'
        return [(0, bits, 'out' if j == 0 else 'in')]
    if cls in ('x_entry', 'x_chain', 'lane_ctl', 'ret_leaf', 'ret_tree', 'ret_root', 'x_root', 'hbm_read', 'band',
               'nv_local'):
        return [(0, bits, 'out' if j == 0 else 'in')]
    if cls == 'cfg':
        return [(0, bits, 'in')]                     # the element / BF reads its cfg word; ROM ends are real
    if cls == 'trunk':
        if bid.endswith('_r'):
            return [(0, bits, 'out' if j == 0 else 'in')]
        return flow(j, bits, 2 * S.LANE_X)          # x out (VM -> field), return roots back
    if cls == 'trunk_tap':
        return flow(j, bits, 2 * S.LANE_X)
    if cls == 'svc_hub':
        if bid in ('sel_vm', 'col_vm'):
            return [(0, bits, 'out' if j == 0 else 'in')]
        return flow(j, bits, 512)[::-1] if False else [(0, 512, 'in' if j == 0 else 'out'),
                                                      (512, bits, 'out' if j == 0 else 'in')]  # q to svc, ao+ix back
    if cls == 'hub':
        return [(0, bits, 'out' if port.startswith('t_') else 'in')]
    if cls == 'link':
        return flow(j, bits, 512)                    # endpoint 0 = collective side: tx out, rx in
    if cls == 'clock_trunk':
        return [(0, bits, 'out' if port.startswith('pll') else 'in')]
    if cls == 'phy_dfi':
        return 'complement'
    raise KeyError(f'no direction rule for S81 class {cls} ({bid})')


def dirs_hbm(bid, cls, bits, eps, j, port):
    if cls in ('x_trunk', 'x_leaf', 'result_leaf', 'result_trunk', 'expert_req', 'kv_rows', 'attn_chain', 'attn_root',
               'attn_kv', 'attn_out', 'attn_operand', 'attn_input'):
        return [(0, bits, 'out' if j == 0 else 'in')]
    if cls == 'weight':
        return flow(j, bits, bits if TOP_FIX else bits - 1)    # line + tag + valid down, ready back (TF7: no ready)
    if cls in ('weight_req', 'control_leaf', 'phy_dfi'):
        return 'complement'
    if cls == 'control':
        seg = []
        n = bits // H.W_CTL
        for s_ in range(n):
            b0 = s_ * H.W_CTL
            seg += flow(j, H.W_CTL, 42)
            seg[-2:] = [(a + b0, b + b0, d) for a, b, d in seg[-2:]]
        return seg
    if cls == 'hub':
        return [(0, bits, 'out' if port.startswith('t_') else 'in')]
    if cls in ('link', 'host'):                     # endpoint 0 = collective / loader: tx out, rx in
        return flow(j, bits, (bits + 1) // 2 if TOP_FIX else min(512, bits))
    if cls == 'clock_trunk':
        return [(0, bits, 'out' if port.startswith('pll') else 'in')]
    raise KeyError(f'no direction rule for HBM class {cls} ({bid})')


# ------------------------------------------------------------------------------------------------ connectivity lint
def endpoint_dirs(die, real, by, bus, j):
    """[(lo, hi, dir)] per net bit range for endpoint j, plus (rtl pin per net bit or None) for real endpoints."""
    bid, cls, bits, eps = bus
    inst, port = eps[j]
    mst = by[inst].master
    if mst in real:
        rb = real[mst]
        names = rb['binding'].get(port)
        if names is None:
            return None, ('port_not_in_binding', port)
        names = list(names[:bits])
        seg, pins = [], []
        for i in range(bits):
            pn = names[i] if i < len(names) else None
            pins.append(pn)
            if pn is None:
                continue
            base, _ = _pin_base(pn)
            d = rb['ports'].get(base, (None,))[0]
            if d is None:
                seg.append((i, i + 1, 'missing'))
            else:
                seg.append((i, i + 1, {'input': 'in', 'output': 'out', 'inout': 'io'}[d]))
        return seg, pins
    rule = (dirs_s81 if die.startswith('s81') else dirs_hbm)(bid, cls, bits, eps, j, port)
    if rule == 'complement':
        others = [k for k in range(len(eps)) if k != j and by[eps[k][0]].master in real]
        assert len(others) == 1, (bid, j)
        oseg, _ = endpoint_dirs(die, real, by, bus, others[0])
        flip = {'in': 'out', 'out': 'in', 'io': 'io', 'missing': 'missing'}
        cov = np.zeros(bits, bool)
        seg = []
        for a, b, d in oseg:
            seg.append((a, b, flip[d]))
            cov[a:b] = True
        # bits with no real pin on the peer: the placeholder side has nothing to talk to (left undirected)
        return seg, None
    return rule, None


def lint_connectivity(die, m, real, ports_w):
    by = {it.name: it for it in m['insts']}
    F = defaultdict(lambda: dict(nets=0, bits=0, examples=[]))   # (check, class, signature) -> agg

    def add(check, cls, sig, bid, nbits):
        k = (check, cls, sig)
        F[k]['nets'] += 1
        F[k]['bits'] += int(nbits)
        if len(F[k]['examples']) < 3:
            F[k]['examples'].append(bid)
    top_ports = []
    bound = defaultdict(set)          # real inst -> rtl pin names bound
    pin_use = Counter()               # (inst, port) -> number of buses
    port_dirs = defaultdict(lambda: defaultdict(set))   # placeholder (master, port) -> bit-dir signatures
    for bus in m['buses']:
        bid, cls, bits, eps = bus
        drv = np.zeros(bits, np.int32)
        ld = np.zeros(bits, np.int32)
        for j, (inst, port) in enumerate(eps):
            if inst == 'TOP':                 # a die top input port drives this net
                drv[:] += 1
                continue
            pin_use[(inst, port)] += 1
            seg, pins = endpoint_dirs(die, real, by, bus, j)
            mst = by[inst].master
            if seg is None:
                add('port_not_found', cls, f'{mst}.{port}', bid, bits)
                continue
            cov = np.zeros(bits, bool)
            for a, b, d in seg:
                cov[a:b] = True
                if d in ('out', 'io'):
                    drv[a:b] += 1
                if d in ('in', 'io'):
                    ld[a:b] += 1
                if d == 'missing':
                    add('pin_not_in_rtl', cls, f'{mst}.{port}', bid, b - a)
            if pins is not None:
                for pn in pins:
                    if pn is not None:
                        bound[inst].add(pn)
                nb = sum(p is None for p in pins)
                if nb:
                    add('net_bits_without_rtl_pin', cls, f'{mst}.{port}', bid, nb)
            else:
                port_dirs[mst][port].add(tuple(seg))
                pw = ports_w.get((mst, port), bits)
                if pw > bits:
                    add('width_port_wider_than_net', cls, f'{mst}.{port} ({pw} > {bits})', bid, pw - bits)
            if (~cov).sum():
                add('undirected_bits', cls, f'{mst}.{port}', bid, int((~cov).sum()))
        sig = ' + '.join(sorted({(by[i].master if i != 'TOP' else 'TOP') + '.' + re.sub(r'[SN][WE]$|\d+$', '*', p)
                                 for i, p in eps}))
        for check, mask in (('undriven', (ld > 0) & (drv == 0)), ('unloaded', (drv > 0) & (ld == 0)),
                            ('multi_driven', drv > 1), ('floating', (drv == 0) & (ld == 0))):
            n = int(mask.sum())
            if n:
                add(check, cls, sig, bid, n)
        if len(eps) == 1:
            add('single_endpoint_net', cls, sig, bid, bits)
        if cls == 'top_in':
            top_ports.append(bid)
    # duplicate port bindings
    for (inst, port), n in pin_use.items():
        if n > 1:
            add('duplicate_port_binding', 'any', f'{by[inst].master}.{port} x{n}', f'{inst}.{port}', n)
    # unbound real pins
    unb = defaultdict(lambda: dict(insts=0, bits=0, dir=None))
    for it in m['insts']:
        if it.master not in real:
            continue
        rb = real[it.master]
        got = bound.get(it.name, set())
        for p, (d, w) in rb['ports'].items():
            if R8_ACTIVE[0] and it.master == 'ot_rom_4096x72_m8' and p == 'rd_out':
                w = 48          # rd_out[71:48]: spare macro columns, no consumer by design (48-b cfg payload)
            if w == 1:
                miss = [] if (p in got or f'{p}[0]' in got) else [p]
            else:
                miss = [i for i in range(w) if f'{p}[{i}]' not in got]
            if miss:
                k = (it.master, p)
                unb[k]['insts'] += 1
                unb[k]['bits'] += len(miss)
                unb[k]['dir'] = d
                unb[k]['width'] = w
    conflicting = {}
    for mst, pd in port_dirs.items():
        for p, sigs in pd.items():
            if len(sigs) > 1:
                conflicting[f'{mst}.{p}'] = len(sigs)
    LAST_TOP[:] = top_ports
    return F, unb, conflicting


LAST_TOP = []


# ------------------------------------------------------------------------------------------------ clock / reset / top I/O
def clock_reset(die, m, real):
    by = {it.name: it for it in m['insts']}
    ck_ports = defaultdict(set)
    for bid, cls, bits, eps in m['buses']:
        for inst, port in eps:
            if cls in ('clock_trunk', 'clock', 'col_clock', 'fclk') and inst != 'TOP':
                ck_ports[inst].add(port)
    rows = Counter()
    rst = Counter()
    for it in m['insts']:
        mst = it.master
        if mst in real and R8_ACTIVE[0]:
            rows[(mst, 'real', 'clock_bound' if inst_has_ck(it.name, ck_ports) or mst == 'ot_hbm3e_phy_v41x_aw30_e8p5'
                  else 'NO_CLOCK')] += 1
        elif mst in real:
            rb = real[mst]
            has_clk = any(p in rb['ports'] for p in ('clk', 'wclk', 'fclk_i'))
            rows[(mst, 'real', 'has_clock_port' if has_clk else 'no_clock_port')] += 1
        else:
            rows[(mst if not re.match(r'hfd_(stn|mcast|gath|cdist)_\d+$', mst) else re.sub(r'_\d+$', '_*', mst),
                  'placeholder', 'clock_trunk' if inst_has_ck(it.name, ck_ports) else 'NO_CLOCK')] += 1
    return rows, ck_ports


def inst_has_ck(name, ck_ports):
    return bool(ck_ports.get(name))


# ------------------------------------------------------------------------------------------------ physical classes
FLIP = {'R0': (False, False), 'MX': (False, True), 'MY': (True, False), 'R180': (True, True)}


def to_die(it, x, y):
    fx, fy = FLIP[it.orient]
    return (it.x + (it.w - x if fx else x), it.y + (it.h - y if fy else y))


def face_of(it, x, y, w, h):
    d = dict(W=x, E=w - x, S=y, N=h - y)
    f = min(d, key=d.get)
    fx, fy = FLIP[it.orient]
    if fx:
        f = {'E': 'W', 'W': 'E'}.get(f, f)
    if fy:
        f = {'N': 'S', 'S': 'N'}.get(f, f)
    return f


NORMAL = dict(E=(1, 0), W=(-1, 0), N=(0, 1), S=(0, -1))


def pin_table(die, m, M, ports_w, real):
    """(master, port) -> [(x, y)] master-frame pin centres in net-bit order."""
    tab = {}
    for name, mst in M.items():
        rects = S.pin_rects(mst, 1, {p: ports_w.get((name, p), 0) for p in mst.order})
        g = defaultdict(dict)
        for nm, ly, (a, b, c, d) in rects:
            base, i = _pin_base(nm)
            g[base][i] = ((a + c) / 2, (b + d) / 2)
        for base, dd in g.items():
            tab[(name, base)] = [dd[i] for i in sorted(dd)]
    # real LEF macros
    lefs = (S.Q_LEF, S.CFG_LEF, S.PHY_LEF, S.SERDES_LEF, S.UCIE_LEF)
    for rel in lefs:
        r = S.real_lef(rel)
        if r['name'] not in real:
            continue
        for port, names in real[r['name']]['binding'].items():
            pts = []
            for pn in names[:max(ports_w.get((r['name'], port), 0), 1)]:
                if pn in r['pins']:
                    a, b, c, d = r['pins'][pn][1]
                    pts.append(((a + c) / 2, (b + d) / 2))
                else:
                    pts.append(None)
            tab[(r['name'], port)] = pts
    return tab


def physical(die, m, M, ports_w, real):
    by = {it.name: it for it in m['insts']}
    tab = pin_table(die, m, M, ports_w, real)
    dims = {}
    for it in m['insts']:
        dims[it.master] = (it.w, it.h)
    for rel in (S.Q_LEF, S.CFG_LEF, S.PHY_LEF, S.SERDES_LEF, S.UCIE_LEF):
        r = S.real_lef(rel)
        dims[r['name']] = (r['w'], r['h'])
    missing = defaultdict(lambda: dict(endpoints=0, bits=0, examples=[]))
    away = defaultdict(lambda: dict(endpoints=0, bits=0, examples=[]))
    spread = []
    ep_geo = {}
    for bid, cls, bits, eps in m['buses']:
        for inst, port in eps:
            it = by[inst]
            pts = tab.get((it.master, port))
            have = 0 if pts is None else sum(p is not None for p in pts[:bits])
            if have < bits:
                k = (it.master, port)
                missing[k]['endpoints'] += 1
                missing[k]['bits'] += bits - have
                if len(missing[k]['examples']) < 3:
                    missing[k]['examples'].append(f'{inst}.{port} ({have}/{bits}) in {bid}')
            if not have:
                continue
            w, h = dims[it.master]
            P = [p for p in pts[:bits] if p is not None]
            fc = Counter(face_of(it, x, y, w, h) for x, y in P)
            face = fc.most_common(1)[0][0]
            D = [to_die(it, x, y) for x, y in P]
            cx = sum(x for x, _ in D) / len(D)
            cy = sum(y for _, y in D) / len(D)
            along = [y for _, y in D] if face in 'EW' else [x for x, _ in D]
            ep_geo[(bid, inst, port)] = (cx, cy, face, max(along) - min(along), it)
    for bid, cls, bits, eps in m['buses']:
        if len(eps) < 2 or cls in ('clock_trunk', 'clock', 'col_clock', 'reset', 'col_reset', 'top_in'):  # CTS / reset trees
            continue
        for inst, port in eps:
            g = ep_geo.get((bid, inst, port))
            if g is None:
                continue
            cx, cy, face, span, it = g
            peers = [ep_geo[(bid, o, p)] for o, p in eps if (o, p) != (inst, port) and (bid, o, p) in ep_geo]
            if R8_ACTIVE[0] and (inst, port) != eps[0] and (bid,) + tuple(eps[0]) in ep_geo:
                peers = [ep_geo[(bid,) + tuple(eps[0])]]      # r8: a load faces its driver, the driver its loads
            if not peers:
                continue
            px, py = min(((q[0], q[1]) for q in peers), key=lambda q: abs(q[0] - cx) + abs(q[1] - cy))
            nx, ny = NORMAL[face]
            dist = abs(px - cx) + abs(py - cy)
            # away: the peer lies behind the face by more than half the block depth along the normal
            depth = it.w if face in 'EW' else it.h
            behind = -((px - cx) * nx + (py - cy) * ny)
            if behind > 0.5 * depth and it.kind not in ('waypoint',):
                k = (it.master, re.sub(r'\d+$', '*', port), it.orient)
                away[k]['endpoints'] += 1
                away[k]['bits'] += bits
                if len(away[k]['examples']) < 3:
                    away[k]['examples'].append(f'{inst}.{port} face {face} peer {behind:.0f} um behind ({bid})')
            if span > 1000.0 or (span > 250.0 and span > 2 * dist):
                spread.append(dict(bus=bid, cls=cls, inst=inst, master=it.master, port=port, face=face,
                                   span_um=round(span, 1), peer_manhattan_um=round(dist, 1), bits=bits))
    return missing, away, spread


def abut(die, m):
    """compute instances whose facing edge is within a channel of a hub / band / service block."""
    if die.startswith('s81'):
        comp = {'q', 'bf', 'bf_nv', 'nvx', 'cfg', 'node', 'seq', 'sstn', 'rstg'}
        hubk = {'hub', 'band_blk', 'svc', 'ctrl'}
    else:
        comp = {'sm'}
        hubk = {'hub', 'spine', 'attn_tile', 'svc'}
    C = [it for it in m['insts'] if it.kind in comp]
    Hh = [it for it in m['insts'] if it.kind in hubk]
    res = defaultdict(lambda: dict(pairs=0, min_gap_um=1e9, examples=[]))
    for h in Hh:
        hx0, hy0, hx1, hy1 = h.x, h.y, h.x + h.w, h.y + h.h
        for c in C:
            cx0, cy0, cx1, cy1 = c.x, c.y, c.x + c.w, c.y + c.h
            ox = min(hx1, cx1) - max(hx0, cx0)
            oy = min(hy1, cy1) - max(hy0, cy0)
            if ox > 0:          # stacked vertically
                gap = max(cy0 - hy1, hy0 - cy1)
            elif oy > 0:
                gap = max(cx0 - hx1, hx0 - cx1)
            else:
                continue
            if gap < S.CH - 1e-6:
                k = (c.kind, h.kind, h.name if die == 'hbm' else re.sub(r'_[SN][WE]$', '', h.name))
                r = res[k]
                r['pairs'] += 1
                r['min_gap_um'] = round(min(r['min_gap_um'], gap), 3)
                if len(r['examples']) < 2:
                    r['examples'].append(f'{c.name} / {h.name} gap {gap:.2f} um')
    return res


# ------------------------------------------------------------------------------------------------ meso / forwarded gap
def gap_r8(m):
    """r8: what is instantiated (stations, ot_fwd_link_stage slices, meso / ratio FIFOs) and the per-chain hops"""
    st = [it for it in m['insts'] if it.kind == 'stn']
    pd = m['pdir']
    slices = sum(math.ceil(pd[it.master][p][1] / 512) for it in st for p in pd[it.master] if p.startswith('di'))
    meso = sum(1 for it in m['insts'] if it.kind == 'cfifo') + sum(
        len(m['glue'][it.master]['lanes']) for it in m['insts'] if it.kind == 'hend' and m['glue'][it.master]['kind'] == 'm2l')
    ratio = sum(1 for it in m['insts'] if it.kind == 'hend' and m['glue'][it.master]['kind'] != 'm2l')
    ch = m['chains']
    return dict(stations=len(st), ot_fwd_link_stage_instantiated=slices, meso_fifos_instantiated=meso,
                ratio_cdc_fifos_instantiated=ratio, chains=len(ch), max_hop_um=max(c['max_hop_um'] for c in ch),
                hops_over_430p56=sum(c['max_hop_um'] > S.LINK_STAGE_UM for c in ch))


def gap(die, m, ports_w):
    st = Counter()
    bits_stage = 0
    n_fwd = 0
    for it in m['insts']:
        if it.kind == 'waypoint':
            st[re.sub(r'_\d+$', '', it.master)] += 1
    by = {it.name: it for it in m['insts']}
    # every waypoint = 4 forwarded stages of its widest bus (generator docstrings); ot_fwd_link_stage W=512 slices
    wp_bits = {}
    for bid, cls, bits, eps in m['buses']:
        for inst, port in eps:
            if by[inst].kind == 'waypoint':
                wp_bits[inst] = max(wp_bits.get(inst, 0), bits)
    for inst, b in wp_bits.items():
        n_fwd += 4 * math.ceil(b / 512)
        bits_stage += 4 * b
    fifo = Counter(it.master for it in m['insts'] if it.kind in ('fifo_blk', 'hub_fifo'))
    return dict(waypoint_masters=dict(st), waypoints=len(wp_bits), forwarded_stage_bits=bits_stage,
                ot_fwd_link_stage_W512_needed=n_fwd, fifo_placeholders=dict(fifo))


def region_crossings(die, m):
    """buses whose endpoints sit in different clock regions (each needs a meso / ratio / async FIFO)."""
    if die.startswith('s81'):
        regs = [(r['name'], r['rect']) for r in m['cregions']]
        dom = lambda it: it.domain  # noqa: E731
    else:
        regs = [(r['name'], r['rect']) for r in H.clock_regions(m)]
        dom = lambda it: it.domain  # noqa: E731
    by = {it.name: it for it in m['insts']}

    def reg(it):
        cx, cy = it.x + it.w / 2, it.y + it.h / 2
        for n, (a, b, c, d) in regs:
            if a <= cx <= c and b <= cy <= d:
                return n
        return f'other:{it.kind}'
    rof = {it.name: reg(it) for it in m['insts']}
    out = Counter()
    bits = Counter()
    for bid, cls, nb, eps in m['buses']:
        if cls == 'clock_trunk':
            continue
        rs = {rof[i] for i, _ in eps}
        ds = {by[i].domain for i, _ in eps}
        if len(rs) > 1:
            kind = 'domain' if len(ds) > 1 else 'region'
            key = (cls, kind)
            out[key] += 1
            bits[key] += nb
    return {f'{c}|{k}': dict(buses=out[(c, k)], bits=bits[(c, k)]) for c, k in out}


# ------------------------------------------------------------------------------------------------ Verilog emission
def vid(n):
    return Q.esc(n)


def emit_verilog(die, m, real, ports_w, out_dir, top):
    by = {it.name: it for it in m['insts']}
    # placeholder stub port directions: union over endpoints
    pdir = defaultdict(lambda: defaultdict(lambda: None))      # master -> port -> per-bit dir array (object)
    conns = defaultdict(list)
    narrow = set()          # (master, port) bound to a net narrower than the abstract port on some instance
    for bus in m['buses']:
        bid, cls, bits, eps = bus
        for j, (inst, port) in enumerate(eps):
            if inst == 'TOP':
                continue
            mst = by[inst].master
            conns[inst].append((port, f'n_{bid}', bits, j, bus))
            if mst in real:
                continue
            seg, _ = endpoint_dirs(die, real, by, bus, j)
            w = ports_w.get((mst, port), bits)
            cur = pdir[mst][port]
            if cur is None:
                cur = ['?'] * w
                pdir[mst][port] = cur
            if bits < w:
                narrow.add((mst, port))
            for a, b, d in seg:
                for i in range(a, b):
                    cur[i] = d if cur[i] in ('?', d) else 'x'
    # stubs
    stubs = ['// die_top_lint: port-identical REGISTERED STUBS of every placeholder master (generated abstract ports and',
             '// widths; directions from the DIRECTION MODEL in tools/die_top_lint.py; x = conflicting across instances',
             '// -> inout).  Outputs come from flops on the stub clock (ck[0] when the abstract has a clock port).', '']
    for it in m['insts']:
        if it.master not in real:
            pdir[it.master]
    for mst in sorted(pdir):
        ports = pdir[mst]
        decl, ins, outs = [], [], []
        for p in sorted(ports):
            arr = ports[p]
            w = len(arr)
            kinds = set(arr)
            if kinds <= {'in', '?'} or (len(kinds - {'?'}) > 1 and (mst, p) in narrow):
                # mixed-direction port that some instance binds to a narrower net (role-dependent master, S13):
                # Verilator cannot connect a narrower net to an inout, so the stub declares it input
                d = 'input'
                ins.append((p, w))
            elif kinds <= {'out'}:
                d = 'output'
                outs.append((p, w, [(0, w)]))
            else:
                d = 'inout'
                ins.append((p, w))
                segs, i = [], 0
                while i < w:
                    if arr[i] == 'out':
                        j_ = i
                        while j_ < w and arr[j_] == 'out':
                            j_ += 1
                        segs.append((i, j_))
                        i = j_
                    else:
                        i += 1
                if segs:
                    outs.append((p, w, segs))
            decl.append(f'    {d} wire [{w - 1}:0] {p}')
        ck = 'ck' if 'ck' in ports else None
        body = [f'module {mst} (', ',\n'.join(decl), ');' + ('  // NO PORTS: reservation slab, no die net' if not decl else ''),
                '    wire lint_clk = ' + (ck + '[0]' if ck else "1'b0") + ';  // '
                + ('stub clock = abstract ck port' if ck else 'NO CLOCK PORT ON THIS ABSTRACT')]
        red = ', '.join(f'^{p}' for p, _ in ins) or "1'b0"
        body.append(f'    wire lint_in = ^{{{red}}};')
        for p, w, segs in outs:
            for a, b in segs:
                body.append(f'    reg [{b - a - 1}:0] r_{p}_{a}; always @(posedge lint_clk) r_{p}_{a} <= {{{b - a}{{lint_in}}}};'
                            f' assign {p}[{b - 1}:{a}] = r_{p}_{a};')
        body.append('endmodule\n')
        stubs.append('\n'.join(body))
    (out_dir / f'{top}_stubs.sv').write_text('\n'.join(stubs))
    # top
    tops = [b[0] for b in m['buses'] if b[1] == 'top_in']
    V = [f'// die_top_lint: {die} die top (generator netlist, real blocks bound by RTL port, placeholders by stub)',
         f'module {top} (' + ', '.join(tops) + ');']
    V += [f'  input wire {p};' for p in tops]
    for bid, cls, bits, eps in m['buses']:
        V.append(f'  wire [{bits - 1}:0] n_{bid};')
        if cls == 'top_in':
            V.append(f'  assign n_{bid} = {bid};')
    nfl = 0
    for it in m['insts']:
        mst = it.master
        parts = []
        if mst in real:
            rb = real[mst]
            bitmap = defaultdict(dict)        # rtl port -> bit -> expr
            for port, net, bits, j, bus in conns.get(it.name, []):
                names = rb['binding'].get(port)
                if names is None:
                    continue
                for i, pn in enumerate(names[:bits]):
                    if pn is None:
                        continue
                    base, b = _pin_base(pn)
                    if base in rb['ports']:
                        bitmap[base][b] = f'{net}[{i}]'
            fl = []
            for p, (d, w) in rb['ports'].items():
                bm = bitmap.get(p)
                if not bm:
                    continue                               # unbound port: left unconnected (lint PINCONNECTEMPTY)
                raw = []
                for b in range(w - 1, -1, -1):
                    if b in bm:
                        nn, ii = bm[b].rsplit('[', 1)
                        raw.append((nn, int(ii[:-1])))
                    else:
                        raw.append((f'lint_nc_{nfl}', None))
                        fl.append(f'lint_nc_{nfl}')
                        nfl += 1
                cat, k_ = [], 0
                while k_ < len(raw):          # compress descending runs of one net into a part-select
                    nn, ii = raw[k_]
                    e_ = k_
                    while ii is not None and e_ + 1 < len(raw) and raw[e_ + 1][0] == nn and raw[e_ + 1][1] == raw[e_][1] - 1:
                        e_ += 1
                    cat.append(nn if ii is None else (f'{nn}[{ii}]' if e_ == k_ else f'{nn}[{ii}:{raw[e_][1]}]'))
                    k_ = e_ + 1
                lines_ = [', '.join(cat[i:i + 64]) for i in range(0, len(cat), 64)]
                parts.append(f'.{p}({{' + ',\n      '.join(lines_) + '})')
            for f_ in fl:
                V.append(f'  wire {f_};')
            prm = ', '.join(f'.{k_}({v_})' for k_, v_ in rb['params'].items())
            V.append(f'  {rb["module"]} ' + (f'#({prm}) ' if prm else '') + f'{vid(it.name)} (\n    ' + ',\n    '.join(parts) + ');')
        else:
            for port, net, bits, j, bus in conns.get(it.name, []):
                parts.append(f'.{port}({net})')
            V.append(f'  {mst} {vid(it.name)} (' + ', '.join(parts) + ');')
    V.append('endmodule\n')
    (out_dir / f'{top}.sv').write_text('\n'.join(V))
    return dict(top=top, stubs=len(pdir), nc_wires=nfl)


def write_shells(real, path):
    """Exact interface shell of every real RTL block (not the hard-macro black boxes): the RTL's own ports, widths and
    directions at the instantiated parameters, parameters declared so the instantiation binds; outputs registered."""
    V = ['// die_top_lint: REAL-INTERFACE shells (port lists parsed from the RTL named in each header; interiors are',
         '// the element owners\' lint scope).', '']
    done = set()
    for rb in real.values():
        if rb['file'].endswith('_bb.v') or rb['module'] in done or rb['kind'].startswith('glue'):
            continue
        done.add(rb['module'])
        prm = ', '.join(f'parameter {k} = {v}' for k, v in rb['params'].items())
        decl, ins, outs = [], [], []
        for p, (d, w) in rb['ports'].items():
            decl.append(f'    {d} wire [{w - 1}:0] {p}')
            (ins if d == 'input' else outs).append((p, w))
        clk = 'clk' if 'clk' in rb['ports'] else "1'b0"
        V.append(f'// {rb["file"]}')
        V.append(f'module {rb["module"]} ' + (f'#({prm}) ' if prm else '') + '(\n' + ',\n'.join(decl) + ');')
        red = ', '.join('^' + p for p, _ in ins) or "1'b0"
        V.append('    wire lint_in = ^{' + red + '};')
        for p, w in outs:
            V.append(f'    reg [{w - 1}:0] r_{p}; always @(posedge {clk}) r_{p} <= {{{w}{{lint_in}}}}; assign {p} = r_{p};')
        V.append('endmodule\n')
    Path(path).write_text('\n'.join(V))


def rtl_closure(tops, extra=()):
    """module -> file over rtl/ and physical/ (first definition by sorted path, test benches excluded); recursive file
    list from the given top modules."""
    defs = {}
    for rel in extra:
        for mm in re.finditer(r'^\s*module\s+([A-Za-z_]\w*)', _strip((ROOT / rel).read_text()), re.M):
            defs.setdefault(mm.group(1), rel)
    for f in sorted(list((ROOT / 'rtl').rglob('*.sv')) + list((ROOT / 'rtl').rglob('*.v'))):
        rel = f.relative_to(ROOT).as_posix()
        if '/test/' in rel or rel.split('/')[-1].startswith('tb'):
            continue
        for mm in re.finditer(r'^\s*module\s+([A-Za-z_]\w*)', _strip(f.read_text(errors='ignore')), re.M):
            defs.setdefault(mm.group(1), rel)
    for pat in ('asap7_memory_macros/*/*.v', 'hbm_accel_macros/*/*.v', 'asap7_memory_macros_v2/*/*.v'):
        # macros inside a real block: the functional model (<name>.v), whose parameters match the RTL that uses it
        for f in sorted((ROOT / 'physical').glob(pat), key=lambda f_: f_.name.endswith('_bb.v')):
            mm = re.search(r'^\s*module\s+([A-Za-z_]\w*)', f.read_text(errors='ignore'), re.M)
            if mm:
                defs.setdefault(mm.group(1), f.relative_to(ROOT).as_posix())
    # NOTE: the SM's hardened sub-macro views (physical/hbm_accel_sm_views/*_bb.v) declare no parameters while
    # ot_hbm_accel_sm_v instantiates them with #(.LB, .IL, .TAGW): Verilator rejects that (PINNOTFOUND), so the
    # sub-macros elaborate from their RTL here (finding H17).
    files, todo, seen = [], list(tops), set()
    while todo:
        mod = todo.pop()
        if mod in seen or mod not in defs:
            seen.add(mod)
            continue
        seen.add(mod)
        f = defs[mod]
        if f not in files:
            files.append(f)
            t = _strip((ROOT / f).read_text(errors='ignore'))
            for im in re.finditer(r'^\s*([A-Za-z_]\w*)\s+(?:#\s*\(|[A-Za-z_\\][\w\\\[\].]*\s*\()', t, re.M):
                if im.group(1) in defs and im.group(1) not in seen:
                    todo.append(im.group(1))
    return files, sorted(s for s in seen if s not in defs)


# ------------------------------------------------------------------------------------------------ abstract list (HBM)
def hbm_abstracts():
    m, pw, M, tool = build('hbm')
    real = real_blocks('hbm')
    cnt = Counter(it.master for it in m['insts'])
    first = {}
    for it in m['insts']:
        first.setdefault(it.master, it)
    led = {f'hfd_{k}': v for k, v in H.BLOCKS.items()}
    rtl = {'hfd_sm': 'ot_hbm_accel_sm_v (rtl/hbm_accel/sm)', 'hfd_coll': 'ot_hbm_accel_tu_endpoint (rtl/hbm_accel/tu)',
           'hfd_loader': 'ot_hbm_accel_loader_host (rtl/hbm_accel/loader)',
           'hfd_index_q': 'ot_hbm_accel_index_path (rtl/hbm_accel/index)',
           'hfd_attn_tile': 'ot_attn_tile_registered_parent / leaf ot_attn_hgrp_m6h1b7p (HBM-ATTN, leaf closed)',
           'hfd_router': 'ot_gpu_router_topk_f topk_f3 (routed) + expert workgroup (not built)',
           'hfd_barrier': 'ot_hbm_accel barrier_k32 (routed)',
           'hfd_cmdproc': 'ot_ds_hbm_cmdproc20 + pipelined issue (no area record)',
           'hfd_quant': 'ot_hdc_actquant', 'hfd_su': 'SU lane array N1024 quarter (HBM-SU lanes closed) + fused chains',
           'hfd_sfu': 'SFU quarter (model ledger)', 'hfd_hc': 'HC / mHC quarter (model ledger)',
           'hfd_vm': 'VM / activation-multicast root (no RTL top)',
           'hfd_svc_SW': 'stream service: 32 x ot_hbm_accel_stream_pc_wb + ot_hbm_accel_cdc_fifo + expert fetch',
           'hfd_serdes_slab': 'TU SerDes reservation slab (no logic)', 'hfd_host_slab': 'host link reservation slab'}
    rows = []
    fam = defaultdict(list)
    for mst, n in cnt.items():
        f = re.sub(r'_\d+$', '_*', mst) if re.match(r'hfd_(stn|mcast|gath|cdist)_\d+$', mst) else \
            ('hfd_svc_*' if mst.startswith('hfd_svc_') else mst)
        fam[f].append((mst, n))
    for f, lst in sorted(fam.items()):
        it = first[lst[0][0]]
        ports = {}
        if lst[0][0] in M:
            mm = M[lst[0][0]]
            for p in mm.order:
                sp = mm.ports[p]
                ports[p] = dict(bits=pw.get((lst[0][0], p), 0), face=sp[2] if sp[0] == 'face' else sp[0])
        status = ('REAL hardened view' if lst[0][0] in ('ot_hbm3e_phy_v41x_aw30_e8p5',) else
                  'REAL pin macro, placeholder content (ot_pdie_*)' if lst[0][0].startswith('ot_pdie') else
                  'NEEDS hardened abstract')
        ms_ = {x for x, _ in lst}
        sizes = sorted({(round(i_.w, 3), round(i_.h, 3)) for i_ in m['insts'] if i_.master in ms_})
        rows.append(dict(family=f, masters=len(lst), instances=sum(n for _, n in lst), status=status,
                         rtl=rtl.get(f if f != 'hfd_svc_*' else 'hfd_svc_SW', ''),
                         ledger=list(led[f][:3]) if f in led else None,
                         size_um=sizes[:4], distinct_sizes=len(sizes), ports=ports if len(ports) <= 40 else
                         dict(count=len(ports), sample=dict(list(ports.items())[:8])), kind=it.kind))
    return rows, m


def block_shape(die, m, real):
    """placeholder masters whose die ports are all inputs (sinks) or all outputs (sources), clock excluded."""
    by = {it.name: it for it in m['insts']}
    io = defaultdict(lambda: [0, 0])
    for bus in m['buses']:
        bid, cls, bits, eps = bus
        if cls == 'clock_trunk':
            continue
        for j, (inst, port) in enumerate(eps):
            mst = by[inst].master
            if mst in real or by[inst].kind == 'waypoint':
                continue
            seg, _ = endpoint_dirs(die, real, by, bus, j)
            for a, b, d in seg or []:
                if d in ('in', 'io'):
                    io[mst][0] += b - a
                if d in ('out', 'io'):
                    io[mst][1] += b - a
    allm = {it.master for it in m['insts'] if it.master not in real and it.kind != 'waypoint'}
    out = {}
    for mst in sorted(allm):
        i, o = io.get(mst, [0, 0])
        if i == 0 or o == 0:
            out[mst] = dict(in_bits=i, out_bits=o, shape='no die nets' if i == o == 0 else
                            ('sink: no output net' if o == 0 else 'source: no input net'))
    return out


def counterparts(die, m, ports_w):
    """placeholder abstract port bits against the RTL top that implements the block (bit totals; no binding)."""
    out = {}
    for mst, (f, mod) in COUNTERPARTS['hbm' if die == 'hbm' else 's81'].items():
        tot = sum(w for (ms, p), w in ports_w.items() if ms == mst and p != 'ck')
        try:
            pm = parse_module(f, mod)['ports']
            out[mst] = dict(rtl=f'{mod} ({f})', die_abstract_bits=tot,
                            rtl_in_bits=sum(w for d, w in pm.values() if d == 'input'),
                            rtl_out_bits=sum(w for d, w in pm.values() if d == 'output'),
                            rtl_ports={p: f'{d} {w}' for p, (d, w) in pm.items()},
                            die_ports={p: w for (ms, p), w in sorted(ports_w.items()) if ms == mst})
        except Exception as e:  # noqa: BLE001
            out[mst] = dict(rtl=f'{mod} ({f})', die_abstract_bits=tot, error=f'interface not parsed: {e}')
    for f, mod in (FWD_STAGE, MESO):
        try:
            pm = parse_module(f, mod)['ports']
            out[mod] = dict(rtl=f, rtl_ports={p: f'{d} {w}' for p, (d, w) in pm.items()},
                            instantiated_in_die_top=0)
        except Exception as e:  # noqa: BLE001
            out[mod] = dict(rtl=f, error=str(e))
    return out


def vlsum(log, top):
    """Verilator log -> {severity-code: {where: count}} with where = top / stubs / rtl, plus first examples."""
    agg = defaultdict(Counter)
    ex = defaultdict(list)
    for ln in Path(log).read_text(errors='ignore').splitlines():
        mm = re.match(r'%(Warning|Error)(?:-([A-Z0-9_]+))?: ([^:]+):(\d+):\d+: (.*)', ln)
        if not mm:
            continue
        sev, code, f, line, msg = mm.groups()
        where = 'top' if f.endswith(f'{top}.sv') else ('stubs' if f.endswith('_stubs.sv') else 'rtl:' + Path(f).name)
        key = f'{sev}-{code or "ERR"}'
        agg[key][where] += 1
        if len(ex[key]) < 4 and not where.startswith('rtl'):
            ex[key].append(msg[:220])
    rc = re.findall(r'rc=(\d+)', Path(log).read_text(errors='ignore'))
    tm = re.findall(r'VLTIME ([\d.]+) s (\d+) KB', Path(log).read_text(errors='ignore'))
    return dict(rc=int(rc[-1]) if rc else None, time_s=float(tm[-1][0]) if tm else None,
                peak_GB=round(int(tm[-1][1]) / 1e6, 2) if tm else None,
                counts={k: dict(v) for k, v in sorted(agg.items())}, examples=dict(ex))


# ------------------------------------------------------------------------------------------------ main
def run_lint(die, out, top_fix=False):
    m, pw, M, tool = build(die, top_fix)
    R8_ACTIVE[0] = die.startswith('s81r8')
    real = real_blocks(die)
    F, unb, conflicting = lint_connectivity(die, m, real, pw)
    ck_rows, ck_ports = clock_reset(die, m, real)
    mp = dict(m, buses=[(b[0], b[1], b[2], [e for e in b[3] if e[0] != 'TOP']) for b in m['buses']])
    missing, away, spread = physical(die, mp, M, pw, real)
    ab = abut(die, mp)
    gp = gap(die, mp, pw) if not R8_ACTIVE[0] else gap_r8(mp)
    xr = region_crossings(die, mp)
    out.mkdir(parents=True, exist_ok=True)
    top = f'{die}_lint_top' + ('_fix' if top_fix else '')
    em = emit_verilog(die, m, real, pw, out, top)
    extra = (S.GLUE_RTL, S.CFG7_RTL) if R8_ACTIVE[0] else ()
    files, unresolved = rtl_closure([v['module'] for v in real.values() if not v['file'].endswith('_bb.v')], extra)
    bb = sorted({rb['file'] for rb in real.values() if rb['file'].endswith('_bb.v')})
    if R8_ACTIVE[0]:
        # die-level list: the q element by its interface shell, every glue master and primitive by its full RTL
        qn = S.real_lef(S.Q_LEF)['name']
        gl, _ = rtl_closure([v['module'] for k_, v in real.items() if v['kind'].startswith('glue')], extra)
        (out / f'{die}_lint_top.f').write_text('\n'.join([str(ROOT / f_) for f_ in bb] + [f'{die}_lint_top_real_shells.sv'] + [str(ROOT / f_) for f_ in gl]
                                                        + [f'{die}_lint_top_stubs.sv', f'{die}_lint_top.sv']) + '\n')
    # full-RTL file list (element interiors elaborate per instance: 24-65 GB on these dies) and the die-level list,
    # where each real RTL block is its exact interface shell (ports, widths, directions and parameters of the RTL)
    (out / f'{top}_fullrtl.f').write_text('\n'.join(bb + files + [f'{top}_stubs.sv', f'{top}.sv']) + '\n')
    write_shells(real, out / f'{top}_real_shells.sv')
    if not R8_ACTIVE[0]:
        (out / f'{top}.f').write_text('\n'.join(bb + [f'{top}_real_shells.sv', f'{top}_stubs.sv', f'{top}.sv']) + '\n')
    rec = dict(
        schema='opentallas.die_top_lint.v1', die=die, top_fix=top_fix, generator=tool, generator_sha256=sha(tool.split()[0]),
        lint_tool_sha256=sha('tools/die_top_lint.py'), variant=m.get('variant'),
        census=dict(instances=len(m['insts']), buses=len(m['buses']), net_bits=int(sum(b[2] for b in m['buses'])),
                    masters=len({it.master for it in m['insts']}),
                    real_instances=sum(it.master in real for it in m['insts']),
                    placeholder_instances=sum(it.master not in real for it in m['insts'])),
        real_blocks={k: dict(module=v['module'], file=v['file'], kind=v['kind'], params=v['params'],
                             instances=sum(it.master == k for it in m['insts'])) for k, v in real.items()},
        connectivity=[dict(check=k[0], cls=k[1], signature=k[2], **v) for k, v in sorted(F.items())],
        unbound_real_pins=[dict(master=k[0], port=k[1], **v) for k, v in sorted(unb.items())],
        placeholder_port_direction_conflicts=conflicting,
        clocking=[dict(master=k[0], view=k[1], clock=k[2], instances=n) for k, n in sorted(ck_rows.items())],
        clock_sources={i: sorted(p) for i, p in ck_ports.items() if any(x.startswith('pll') for x in p)},
        top_ports=list(LAST_TOP),
        physical=dict(missing_pins=[dict(master=k[0], port=k[1], **v) for k, v in sorted(missing.items())],
                      face_away=[dict(master=k[0], port=k[1], orient=k[2], **v) for k, v in sorted(away.items())],
                      pin_spread=sorted(spread, key=lambda r: -r['span_um'])[:60],
                      pin_spread_count=len(spread),
                      abut_without_channel=[dict(compute=k[0], hub_kind=k[1], hub=k[2], **v) for k, v in sorted(ab.items())]),
        meso_forwarded_gap=dict(gp, clock_region_crossings=xr),
        block_shape=block_shape(die, mp, real), counterparts=counterparts(die, m, pw),
        top_fixes=TOP_FIXES if top_fix else {},
        verilog=dict(em, filelist=f'{top}.f', rtl_files=len(files), unresolved_modules=unresolved))
    (out / f'{top}_lint.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['lint', 'abstracts', 'vlsum'])
    ap.add_argument('--top')
    ap.add_argument('--die', choices=['s81_layer', 's81_head', 'hbm', 's81r8_layer', 's81r8_head'])
    ap.add_argument('--top-fix', action='store_true')
    ap.add_argument('--out', type=Path, default=ROOT / OUT)
    a = ap.parse_args(argv)
    if a.mode == 'vlsum':
        s = vlsum(a.out / f'{a.top}.verilator.log', a.top)
        (a.out / f'{a.top}_verilator_summary.json').write_text(json.dumps(s, indent=1) + '\n')
        print(json.dumps(s, indent=1))
        return 0
    if a.mode == 'lint':
        rec = run_lint(a.die, a.out, a.top_fix)
        print(json.dumps(rec['census']))
    else:
        rows, m = hbm_abstracts()
        a.out.mkdir(parents=True, exist_ok=True)
        (a.out / 'hbm_die_abstract_list.json').write_text(json.dumps(dict(
            schema='opentallas.hbm_die_abstract_list.v1', generator='tools/hbm_accel_die_fp.py', round=H.FINAL_ROUND,
            generator_sha256=sha('tools/hbm_accel_die_fp.py'), die_um=[m['geo']['W'], m['geo']['H']], families=rows),
            indent=1) + '\n')
        print(len(rows))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
