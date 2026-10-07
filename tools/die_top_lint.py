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
  lint  --die {s81_layer,s81_head,hbm,qwen_rom} [--top-fix] --out DIR
                                                     python graph + physical lint, findings JSON,
                                                     Verilog die top + stubs + file list for Verilator
  abstracts [--die hbm] --out DIR                    HBM die: hardened abstracts the real placement needs
  abstracts --die rom --out DIR                      ROM dies (s81_layer, s81_head, qwen_rom): block-family inventory
                                                     (*_abstract_list.json) + README.md summary tables; one command,
                                                     rerun after a generator change

Qwen ROM die (qwen_rom): tools/qwen_rom_fulldie_b3r2.py selected() with the r17b recipe (QWEN_R17B, the recipe of
tools/qwen_rom_die_path_sta.py on claude/qwen-die-rebuild-20261005 @ f76c3603b).  While that branch is not on main,
--qwen-ref REF overlays the generator files REF changed since its merge base with HEAD (tools/ only) on this tree, in
build/dielint_qsrc_<sha12>/ (relative symlinks: rsync-able; reused when present, no git needed then).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shlex
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import dsrom_s81_fulldie as S  # noqa: E402
import hbm_accel_die_fp as H  # noqa: E402

Q = S.Q          # main's qwen_rom_fulldie (esc, pin_rects); the Qwen DIE generator is loaded separately (load_qwen)

OUT = 'results/rtl/die_top_lint_20261006'
S81_OPTS = ''


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def gen_root(die):
    return Path(qwen_src()['root']) if die == 'qwen_rom' else ROOT


def sha_gen(die, tool):
    return hashlib.sha256((gen_root(die) / tool).read_bytes()).hexdigest()


def git(*a, cwd=ROOT):
    import subprocess
    try:
        return subprocess.run(['git', *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001  no git (rsync'd tree): callers fall back to recorded state
        return None


def gen_tag(rel, root=ROOT):
    """generator identity: sha256 of the file + the last commit that touched it + the tree HEAD (git, when present)."""
    p = Path(root) / rel
    tag = dict(file=rel, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    head = git('rev-parse', 'HEAD')
    sc = Path(root) / 'SOURCE_COMMIT'
    tag['tree_head'] = head or (sc.read_text().strip() if sc.exists() else None)
    tag['file_commit'] = git('log', '-1', '--format=%H', '--', rel)
    return tag


# ------------------------------------------------------------------------------------------------ Qwen ROM die source
# r17b recipe: tools/qwen_rom_die_path_sta.py main() @ f76c3603b with --slab-group-h 455.76 --cdc 183.048,183.048
# (path_sta/r17b_i5_skew*.json 'floorplan'); its write_netlist(k=1) is byte-identical to the r17b_real case die.v
# (sha256 86a9e54b..., EPYC1 /srv/opentallas/scratch-overflow/claude/qwen-die-r17/cases/r17b_real/die.v).
QWEN_R17B = dict(b3r3=True, b3r6=True, tree_cols=6, bw_align=True, bw_edge=True, io_faces=True, bw_edge_inner=True,
                 bw_sp=200, m6_strip=40, slab_group_h=455.76, cdc='183.048,183.048')
# r18 recipe (claude/qwen-die-rebuild-20261005): r17b + r18=True (findings Q1-Q14 of the first lint, main 694e21a6e)
QWEN_R18 = dict(QWEN_R17B, r18=True)
QWEN_RECIPE = 'r17b'     # --qwen-recipe
QWEN_REF = None          # --qwen-ref
QSRC = None              # dict(root, ref, commit, overlay)


def qwen_src():
    """root of the tree the Qwen die generator is imported from (ROOT, or the --qwen-ref overlay)."""
    global QSRC
    if QSRC is not None:
        return QSRC
    if QWEN_REF is None:
        QSRC = dict(root=ROOT, ref=None, commit=git('rev-parse', 'HEAD'), overlay=[])
        return QSRC
    commit = git('rev-parse', QWEN_REF + '^{commit}')
    tag = (commit or QWEN_REF)[:12]
    od = ROOT / 'build' / f'dielint_qsrc_{tag}'
    if (od / 'OVERLAY.json').exists():
        QSRC = dict(json.loads((od / 'OVERLAY.json').read_text()), root=od)
        return QSRC
    if commit is None:
        raise SystemExit(f'--qwen-ref {QWEN_REF}: no git here and no prepared overlay {od}')
    base = git('merge-base', 'HEAD', commit)
    files = [f for f in git('diff', '--name-only', base, commit, '--', 'tools').split('\n') if f.endswith('.py')]
    (od / 'tools').mkdir(parents=True, exist_ok=True)
    for e in ROOT.iterdir():
        if e.name not in ('tools', 'build', '.git'):
            (od / e.name).symlink_to(Path('..') / '..' / e.name)
    for f in (ROOT / 'tools').iterdir():
        if f.is_file() and f'tools/{f.name}' not in files:
            (od / 'tools' / f.name).symlink_to(Path('..') / '..' / '..' / 'tools' / f.name)
    for f in files:
        (od / f).write_text(git('show', f'{commit}:{f}') + '\n')
    rec = dict(ref=QWEN_REF, commit=commit, merge_base=base, overlay=files)
    (od / 'OVERLAY.json').write_text(json.dumps(rec, indent=1) + '\n')
    QSRC = dict(rec, root=od)
    return QSRC


_QW = {}


def load_qwen():
    """(v, m) of the r17b Qwen die: the generator imported from qwen_src() under private module names (the main
    tree's qwen_rom_fulldie stays bound to S.Q)."""
    if 'vm' in _QW:
        return _QW['vm']
    import importlib
    src = qwen_src()
    saved = {k: sys.modules.pop(k) for k in list(sys.modules) if k.startswith('qwen_rom_fulldie')}
    sys.path.insert(0, str(Path(src['root']) / 'tools'))
    try:
        B = importlib.import_module('qwen_rom_fulldie_b3r2')
        r = dict(QWEN_R18 if QWEN_RECIPE == 'r18' else QWEN_R17B)
        cdc = r.pop('cdc')
        v, m = B.selected(True, cdc=B._cdc_arg(cdc), **r)
    finally:
        sys.path.pop(0)
        for k in [k for k in sys.modules if k.startswith('qwen_rom_fulldie')]:
            sys.modules['_dielint_' + k] = sys.modules.pop(k)
        sys.modules.update(saved)
    # the PHY endpoint is '*dfi' (generator netlist convention for the real PHY's named pins): plain port name here
    m['buses'] = [(bid, cls, bits, [(i, p.lstrip('*')) for i, p in eps]) for bid, cls, bits, eps in m['buses']]
    _QW['vm'] = (v, m, B)
    return _QW['vm']


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
# Qwen die: STREAM4 per-PC CDC bundles in the generator's documented order (qwen_rom_fulldie_b3r2._cdc_arg, TAGW 9)
QPHY_BB = 'physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy/ot_hbm3e_phy_bb.v'
QPHY_LEF = 'physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy/ot_hbm3e_phy.lef'
QCDC_RTL = 'rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv'
CDC_LAYOUT = dict(
    h=['h_lv'] + _bus('h_lsec', 17) + _bus('h_lrow', 8) + _bus('h_ldata', 256) + _bus('h_cred', 3) + ['h_wv']
      + _bus('h_wsec', 24) + ['h_hand', 'h_wcon', 'h_cv'] + _bus('h_csec', 24) + _bus('h_cdata', 256) + _bus('h_ctag', 9)
      + ['h_av'] + _bus('h_atag', 9) + ['h_fault'],                                           # 613
    c=['l_v'] + _bus('l_sec', 17) + _bus('l_row', 8) + _bus('l_data', 256) + ['l_pop', 'w_v'] + _bus('w_sec', 24)
      + _bus('w_data', 256) + _bus('w_tag', 9) + ['w_room', 'wd_v'] + _bus('wd_tag', 9) + ['c_fault'])   # 585
assert len(CDC_LAYOUT['h']) == 613 and len(CDC_LAYOUT['c']) == 585


def real_blocks(die, m=None):
    """master -> dict(module, file, params, ports, binding{die port: [rtl pin names or None]}, kind)."""
    out = {}
    V = (m or {}).get('variant') or {}
    if die.startswith('s81r8'):
        return real_blocks_r8(die)
    if die == 'qwen_rom':
        v, m, B = load_qwen()
        out['ot_hbm3e_phy'] = dict(module='ot_hbm3e_phy', file=QPHY_BB, kind='hard macro black box (v2 E/W PHY)', params={},
                                   ports=parse_module(QPHY_BB, 'ot_hbm3e_phy')['ports'],
                                   binding=dict(dfi=[pn for pn, _ in v.phy_pins()]))
        prm = dict(TAGW=9)
        bind = dict(CDC_LAYOUT)
        if QWEN_RECIPE == 'r18':
            bind.update({p: [p] for p in ('clk', 'hclk', 'c_arst_n', 'h_arst_n')})
            out['ot_hbm3e_phy']['binding'].update(clk=['clk'], rst_n=['rst_n'])
        out['qfd_cdc'] = dict(module='ot_qwen_stream4_cdc_pc', file=QCDC_RTL,
                              kind='RTL (routed per-PC CDC element; the die master qfd_cdc is its frame)', params=prm,
                              ports=parse_module(QCDC_RTL, 'ot_qwen_stream4_cdc_pc', prm)['ports'], binding=bind)
        return out
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
        rp = {k_: dict(v_) for k_, v_ in H.real_ports(m).items()}
        for mst in ('ot_pdie_serdes', 'ot_pdie_ucie'):     # TF5: even tx / rx split of a narrower chain
            rp[mst].setdefault('iox', SplitIO())          # (r15 link_rtl: the generator's own iox binding)
        for mst, f, kind in (('ot_hbm3e_phy_v41x_aw30_e8p5', 'physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/'
                              'ot_hbm3e_phy_v41x_aw30_e8p5_bb.v', 'hard macro black box'),
                             ('ot_pdie_serdes', 'physical/asap7_v41x_pdie_macros_v2/ot_pdie_serdes/ot_pdie_serdes_bb.v',
                              'placeholder hard macro black box'),
                             ('ot_pdie_ucie', 'physical/asap7_v41x_pdie_macros_v2/ot_pdie_ucie/ot_pdie_ucie_bb.v',
                              'placeholder hard macro black box'),
                             ('ot_hbm_host_phy', 'physical/hbm_accel_die_views/phy_bb/ot_hbm_host_phy/ot_hbm_host_phy_bb.v',
                              'pin-accurate host PHY black box (tools/hbm_phy_bb.py)')):
            if mst not in rp:
                continue
            pm = parse_module(f, mst)
            out[mst] = dict(module=mst, file=f, kind=kind, params={}, ports=pm['ports'], binding=rp[mst])
        prm = json.loads((ROOT / H.PORTMAP).read_text())['DS']['SM_parameters']
        prm.update(DS=3, DG=3, DW=4, PIO=2)          # sm_r2 capture.json (the placed context's selection)
        pm = parse_module('rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv', 'ot_hbm_accel_sm_v', prm)
        lay = dict(SM_LAYOUT)
        if TOP_FIX or V.get('sm_rtl_w'):          # TF7 (r15 sm_rtl_w in the generator)
            lay['d'] = SM_LAYOUT['d'][:-1]
            lay['q'] = SM_LAYOUT['q'][:44]
        if V.get('sm_desc'):                      # r15: the bulk-copy descriptor on the control leaf
            lay['c'] = SM_LAYOUT['c'] + ['d_valid'] + _bus('d_base', 32) + _bus('d_lines', 24) + ['d_ready']
        if V.get('clk_dom'):                      # r15: one clock net, one reset net per domain
            lay['ck'] = ['clk']
            lay['rst'] = ['rst_n']
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
    qn = S.real_lef(S.Q_LEF)['name']
    qf = {'ot_v41_rom_elem_q_qx_w10': ('rtl/v41rom/ot_v41_rom_elem_q_qx_w10.sv', 'routed RTL (QELEM Z20c receipt params)',
                                       dict(MTP=1, EARLY=1, NB=2, FAST=1, PP=1, QTIMING_FIX=1, QPIPE=1, QP_XS=1, QP_CAP=0,
                                            QP_P1=1, QP_CSAM=10, QZ=1, QZ_NS=8, QZ_NE=4, QY=1, QX=10)),
          'ot_v41_rom_elem_q_qxpq_w10': ('rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv', 'routed RTL (QELEM PQ, NB=2)',
                                         dict(NB=2))}.get(qn, ('rtl/v41rom/ot_v41_rom_elem_q_qp_w10.sv',
                                                               'routed RTL (NB=2 receipt params)',
                                                               dict(NB=2, MTP=1, EARLY=1, FAST=1, PP=1, QTIMING_FIX=1,
                                                                    QPIPE=1, QP_XS=1, QP_CAP=0, QP_P1=1, QP_CSAM=10)))
    files = {qn: qf,
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
    for mst, prm in (('ot_dsrom_head_elem_A', dict(LV=8, PAD=0, JOIN=1, ROWS=32)),
                     ('ot_dsrom_head_elem_B', dict(LV=6, PAD=2, JOIN=0, ROWS=128))):
        if mst in used:
            f = 'rtl/v41rom/ot_dsrom_head_elem.sv'
            pm = parse_module(f, 'ot_dsrom_head_elem', prm)
            out[mst] = dict(module='ot_dsrom_head_elem', file=f, kind='routed RTL, closed (recovery lever head)',
                            params=prm, ports=pm['ports'], binding=rp[mst])
    for mst in sorted(used):
        if S.is_glue(mst) or mst == 'ot_s81_cfg7_seq':
            f = S.CFG7_RTL if mst == 'ot_s81_cfg7_seq' else S.GLUE_RTL.replace('/r8/', f'/{S.out_rev()}/')
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
    'qwen': {},
}
FWD_STAGE = ('rtl/common/ot_fwd_link_stage.sv', 'ot_fwd_link_stage')
MESO = ('rtl/common/ot_meso_fifo.sv', 'ot_meso_fifo')


# ------------------------------------------------------------------------------------------------ die models
TOP_FIX = False
VARIANT = ''        # hbm: --variant of tools/hbm_accel_die_fp.py ('' = its adopted default)
CUR_M = {}          # the die model being linted (forwarded-clock map, variant)
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
        if S81_OPTS:          # the die variant of a recorded case (tools/dsrom_s81_fulldie.py die options)
            S.apply_options(S.die_options(argparse.ArgumentParser()).parse_args(
                shlex.split(S81_OPTS) + ['--gen', 'r8', '--die', die.split('_', 1)[1]]))
        else:
            S.configure(die.split('_', 1)[1], 'r8')
        m = S.build()
        S.finalize_r8(m)
        R8[die] = m
        return m, S.port_widths(m, 1), S.masters(m, 1), 'tools/dsrom_s81_fulldie.py --gen r8'
    if die == 'qwen_rom':
        if top_fix:
            raise SystemExit('qwen_rom: no top fixes defined')
        v, m, B = load_qwen()
        return m, v.port_widths(m, 1), v.masters(m, 1), 'tools/qwen_rom_fulldie_b3r2.py'
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
        # --top-fix: the 2026-10-06 lint tops of r14b (generator untouched then); default: the generator's variant
        # (r15 fixes every TF in the generator itself)
        m = H.build(dict(H.R14B, row1_flip=False) if top_fix else H.variant_arg(VARIANT))
        if top_fix:
            fix_clock_nets(m, die)
            fix_hbm_links(m)
        ports_w = H.port_widths(m, 1)
        M = H.masters(m, 1)
        tool = 'tools/hbm_accel_die_fp.py'
    CUR_M.clear()
    CUR_M.update(m)
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


QLINK = 1056          # qwen_rom_fulldie LINK_TRACKS: 512 each way + 32 control (16 each way)


def dirs_qwen(bid, cls, bits, eps, j, port):
    """Qwen die (qwen_rom_fulldie buses(): endpoint 0 is always the upstream / source end)."""
    if cls in ('corridor', 'head_chain', 'tap'):
        return flow(j, bits, bits - 1)               # instruction beats + go + x + clock/reset down, ready back
    bid = bid[:-2] if bid.endswith('_x') else bid      # r18: second half of a bus through a CDC cluster
    if cls in ('tree_block', 'tree_spine', 'spine_local', 'hbm_read', 'crom', 'clock_trunk', 'reset'):
        return [(0, bits, 'out' if j == 0 else 'in')]
    if cls == 'io':
        if bid in ('ucie_tx', 'serdes_tx', 'ucie_rx', 'serdes_rx'):          # 2 x IO_BITS: the collective's link word, 512 tx + 512 rx
            return flow(j, bits, bits // 2)
        return [(0, bits, 'out' if j == 0 else 'in')]
    if cls in ('link_spine', 'link_channel', 'strip_fan'):   # hub side upstream; per link: 528 down, 528 back
        seg = []
        for k in range(bits // QLINK):
            seg += [(a + k * QLINK, b + k * QLINK, d) for a, b, d in flow(j, QLINK, QLINK // 2)]
        return seg
    if cls == 'sequencer':
        if bid in ('seq_ib', 'seq_su', 'seq_coll'):   # word + valid/go down, ready / done back
            return flow(j, bits, bits - 1)
        return [(0, bits, 'out' if j == 0 else 'in')]
    if cls in ('hbm_cdc', 'cdc_core', 'phy_dfi'):
        return 'complement'
    raise KeyError(f'no direction rule for Qwen class {cls} ({bid})')


def dirs_hbm(bid, cls, bits, eps, j, port):
    V = CUR_M.get('variant') or {}
    fc = CUR_M.get('fclk', {}).get(bid)
    if fc:                  # r15 fwd: data bits + forwarded clocks (nd downstream, nu upstream) appended
        base, nd, nu = fc
        seg = dirs_hbm_base(bid, cls, base, eps, j, port, V)
        if seg == 'complement':
            raise KeyError(f'forwarded segment {bid} with a complement rule')
        if nd:
            seg = seg + [(base, base + nd, 'out' if j == 0 else 'in')]
        if nu:
            seg = seg + [(base + nd, base + nd + nu, 'in' if j == 0 else 'out')]
        return seg
    return dirs_hbm_base(bid, cls, bits, eps, j, port, V)


def dirs_hbm_base(bid, cls, bits, eps, j, port, V):
    if cls in ('x_trunk', 'x_leaf', 'result_leaf', 'result_trunk', 'expert_req', 'kv_rows', 'attn_chain', 'attn_root',
               'attn_kv', 'attn_out', 'attn_operand', 'attn_input', 'attn_query', 'attn_packet'):
        return [(0, bits, 'out' if j == 0 else 'in')]
    if cls == 'weight':     # line + tag + valid down, ready back (TF7 / r15 sm_rtl_w: no ready)
        return flow(j, bits, bits if (TOP_FIX or V.get('sm_rtl_w')) else bits - 1)
    if cls in ('weight_req', 'control_leaf', 'phy_dfi'):
        if any(CUR_M['_by'][i].master in CUR_M['_real'] for i, _ in eps):
            return 'complement'
        return [(0, bits, 'out' if j == 0 else 'in')]       # r15 rq_chain: station -> station, SM side upstream
    if cls == 'control':
        w = H.W_CTL + (H.W_DESC if V.get('sm_desc') else 0)
        seg = []
        for s_ in range(bits // w):
            b0 = s_ * w
            part = flow(j, H.W_CTL, 42)                      # start / op / release_in down, busy / arrive / released up
            if w > H.W_CTL:                                  # r15 sm_desc: d_valid / d_base / d_lines down, d_ready up
                part += [(a + H.W_CTL, b + H.W_CTL, d) for a, b, d in flow(j, w - H.W_CTL, w - H.W_CTL - 1)]
            seg += [(a + b0, b + b0, d) for a, b, d in part]
        return seg
    if cls == 'hub':        # r17 fwd hub chains: a station's a / b port drives when it is the bus driver (j = 0)
        return [(0, bits, 'out' if port.startswith('t_') or (j == 0 and port in ('a', 'b')) else 'in')]
    if cls in ('link', 'host'):                     # endpoint 0 = collective / loader: tx out, rx in
        return flow(j, bits, (bits + 1) // 2 if (TOP_FIX or V.get('link_rtl')) else min(512, bits))
    if cls == 'clock_trunk':
        return [(0, bits, 'out' if port.startswith('pll') else 'in')]
    if cls == 'reset_tree':
        return [(0, bits, 'out' if port.startswith('por') else 'in')]
    raise KeyError(f'no direction rule for HBM class {cls} ({bid})')


# ------------------------------------------------------------------------------------------------ connectivity lint
def _binding(rb, port):
    """rtl pin names of a die port; 'p[lo:hi]' (S81 generator port slice) = bits lo..hi of port p"""
    mm = re.match(r'^(.+)\[(\d+):(\d+)\]$', port)
    if mm:
        names = rb['binding'].get(mm.group(1))
        return None if names is None else names[int(mm.group(2)):int(mm.group(3)) + 1]
    return rb['binding'].get(port)


def endpoint_dirs(die, real, by, bus, j):
    """[(lo, hi, dir)] per net bit range for endpoint j, plus (rtl pin per net bit or None) for real endpoints."""
    bid, cls, bits, eps = bus
    inst, port = eps[j]
    mst = by[inst].master
    if mst in real:
        rb = real[mst]
        names = _binding(rb, port)
        if names is None:
            return None, ('port_not_in_binding', port)
        names = [names[i] if i < len(names) else None for i in idx] if idx else list(names[:bits])
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
    rule = (dirs_s81 if die.startswith('s81') else dirs_qwen if die == 'qwen_rom' else dirs_hbm)(bid, cls, bits, eps, j, port)
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
            if R8_ACTIVE[0] and (it.master, p) in S.UNUSED_BY_DESIGN:
                continue        # head element outputs ot_dsrom_head_bundle leaves unconnected (S.UNUSED_BY_DESIGN)
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
    rst_ports = defaultdict(set)
    fwd_insts = set()
    fcl = m.get('fclk', {})
    bundle_ck = set()        # Qwen: the tile field's clock / reset ride as bits of the corridor / tap / head chain words
    for bid, cls, bits, eps in m['buses']:
        for inst, port in eps:
            if cls in ('clock_trunk', 'clock', 'col_clock', 'fclk') and inst != 'TOP':
                ck_ports[inst].add(port)
            if cls == 'reset_tree' or (R8_ACTIVE[0] and cls in ('reset', 'col_reset') and inst != 'TOP'):
                rst_ports[inst].add('rst' if R8_ACTIVE[0] else port)
            if bid in fcl:
                fwd_insts.add(inst)
            if die == 'qwen_rom' and cls in ('corridor', 'tap', 'head_chain'):
                bundle_ck.add(inst)
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
            fam = mst if not re.match(r'hfd_(stn|mcast|gath|cdist|meso)_r?\d+$', mst) else re.sub(r'_r?\d+$', '_*', mst)
            if inst_has_ck(it.name, ck_ports):
                ck = 'clock_trunk'
            elif it.kind == 'waypoint' and it.name in fwd_insts:
                ck = 'forwarded_clock'          # r15 fwd: fclk bits of its segments (ot_fwd_link_stage)
            elif it.name in bundle_ck:
                ck = 'clock_bits_in_data_bundle'
            elif it.kind in ('serdes_slab', 'host_slab'):
                ck = 'no_logic (reservation slab)'
            else:
                ck = 'NO_CLOCK'
            rows[(fam, 'placeholder', ck)] += 1
            if 'rst' in rst_ports.get(it.name, set()):
                rst[(fam, 'reset_tree')] += 1
    for it in m['insts']:
        if it.master in real and 'rst' in rst_ports.get(it.name, set()):
            rst[(it.master, 'reset_tree')] += 1
    return rows, ck_ports, rst


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


PIN_FIT_ERRORS = {}


def real_lefs(die):
    return (QPHY_LEF,) if die == 'qwen_rom' else (S.Q_LEF, S.CFG_LEF, S.PHY_LEF, S.SERDES_LEF, S.UCIE_LEF) + ((S.HEAD_A_LEF, S.HEAD_B_LEF) if S.HEAD_BUNDLES else ())


def pin_table(die, m, M, ports_w, real):
    """(master, port) -> [(x, y)] master-frame pin centres in net-bit order."""
    tab = {}
    prects = load_qwen()[0].pin_rects if die == 'qwen_rom' else S.pin_rects
    for name, mst in M.items():
        try:
            rects = prects(mst, 1, {p: ports_w.get((name, p), 0) for p in mst.order})
        except ValueError as e:          # pins do not fit the face: no pins for this master (missing_pins)
            PIN_FIT_ERRORS[name] = str(e)
            continue
        g = defaultdict(dict)
        for nm, ly, (a, b, c, d) in rects:
            base, i = _pin_base(nm)
            g[base][i] = ((a + c) / 2, (b + d) / 2)
        for base, dd in g.items():
            tab[(name, base)] = [dd[i] for i in sorted(dd)]
    # real LEF macros
    for rel in real_lefs(die):
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
    for rel in real_lefs(die):
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
        if len(eps) < 2 or cls in ('clock_trunk', 'reset', 'reset_tree', 'clock', 'col_clock', 'col_reset', 'top_in'):  # CTS / reset trees
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
            area = it.master in M and M[it.master].ports.get(port, ('',))[0] == 'area'   # M8 over-the-top pins
            if behind > 0.5 * depth and it.kind not in ('waypoint', 'link_station') and not area:
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
    elif die == 'qwen_rom':
        comp = {'tile', 'row_engine'}
        hubk = {'hub_element', 'spine_block', 'ctrl', 'io'}
    else:
        comp = {'sm'}
        hubk = {'hub', 'spine', 'attn_tile', 'svc'}
    chan = load_qwen()[0].HCH if die == 'qwen_rom' else S.CH       # Qwen: one link channel (97.2 um)
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
            if gap < chan - 1e-6:
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
    wpk = ('waypoint', 'link_station')
    for it in m['insts']:
        if it.kind in wpk:
            st[re.sub(r'_\d+$', '', it.master)] += 1
    by = {it.name: it for it in m['insts']}
    # every waypoint = 4 forwarded stages of its widest bus (generator docstrings); ot_fwd_link_stage W=512 slices
    wp_bits = {}
    for bid, cls, bits, eps in m['buses']:
        for inst, port in eps:
            if by[inst].kind in wpk:
                wp_bits[inst] = max(wp_bits.get(inst, 0), bits)
    for inst, b in wp_bits.items():
        n_fwd += 4 * math.ceil(b / 512)
        bits_stage += 4 * b
    fifo = Counter(it.master for it in m['insts'] if it.kind in ('fifo_blk', 'hub_fifo', 'link_fifo'))
    meso = m.get('meso', [])
    fcl = m.get('fclk', {})
    out = dict(waypoint_masters=dict(st), waypoints=len(wp_bits), forwarded_stage_bits=bits_stage,
               ot_fwd_link_stage_W512_needed=n_fwd, fifo_placeholders=dict(fifo))
    if m.get('fclk') or m.get('meso'):          # HBM r15+ (fwd): forwarded clocks and the meso-FIFO census
        out.update(
            station_masters=len({it.master for it in m['insts'] if it.kind == 'waypoint'}),
            forwarded_segments_with_fclk=len(fcl), forwarded_clock_wires=sum(a + b for _, a, b in fcl.values()),
            meso_fifo_W512_slices=dict(total=sum(x['slices'] for x in meso),
                                           in_stations=sum(x['slices'] for x in meso if x['where'] == 'station'),
                                           in_receiving_blocks=sum(x['slices'] for x in meso if x['where'] != 'station'),
                                           station_instances=len({x["inst"] for x in meso if x["where"] == "station"})))
    if die == 'qwen_rom':
        v, _, B = load_qwen()
        fa = B.fifo_accounting(v, m)
        out['decision_C_fifo_slots'] = dict(
            tile_tap=dict(fa['tile_tap'], instantiated=0), block_word=dict(fa['block_word'], instantiated=0),
            strip_return=dict(fa['strip_return'], instantiated=0),
            stream4_cdc=dict(count=sum(it.kind == 'cdc' for it in m['insts']), slot='qfd_cdc frames',
                             instantiated='as RTL-bound frames (qfd_cdc = ot_qwen_stream4_cdc_pc)'),
            note='tile-tap / block-word / strip-return FIFO slots are AREA inside placeholder frames (station frame '
                 'height, port slab area, strip FIFO frame); no FIFO instance or FIFO port exists in the die netlist')
        stn = sum(it.kind == 'station' for it in m['insts'])
        out['corridor_stations'] = dict(count=stn, heads=sum(it.kind == 'head' for it in m['insts']),
                                        note='one registered corridor station per tile (placeholder qfd_cst)')
    return out


HBM_CDC_HOSTS = {           # HBM die: blocks whose abstract holds the CDC of their crossings (domains.sdc H* / X* / L*)
    'hfd_svc_': 'async hbm <-> stream FIFOs inside the stream service (ledger: 8 x ot_hbm_accel_cdc_fifo_r2)',
    'hfd_su': 'ratio CDC 3:4 in the SU HUB_IN / HUB_OUT stages', 'hfd_sfu': 'ratio CDC 3:4 at the SFU hub ports',
    'hfd_hc': 'ratio CDC 3:4 at the HC hub ports', 'hfd_quant': 'ratio CDC 3:4 at the quantiser hub ports',
    'hfd_coll': 'core <-> pclk inside ot_hbm_accel_tu_endpoint'}
_DOM = {'stream': 'stream_1p2', 'serial': 'serial_0p9', 'hbm': 'hbm', 'link': 'link'}


def domain_crossings(m):
    """every non-clock bus whose endpoints sit in different clock DOMAINS (independent of region): each needs a
    ratio / async FIFO or a CDC element at one end.  HBM r15+: forwarded stations carry their source's clock (no
    domain of their own), meso / launch stations are CDC elements on their region clock, and a crossing that ends in a
    block holding the CDC (HBM_CDC_HOSTS) is listed as attributed."""
    by = {it.name: it for it in m['insts']}
    clocked = m.get('clocked', {})
    hbm = bool(m.get('fclk'))
    out = defaultdict(lambda: dict(buses=0, bits=0, examples=[]))
    att = defaultdict(lambda: dict(buses=0, bits=0, examples=[], cdc=None))
    for bid, cls, nb, eps in m['buses']:
        if cls in ('clock_trunk', 'reset', 'reset_tree'):
            continue
        if any(by[i].kind in ('cdc', 'xfifo') for i, _ in eps):
            continue                 # ends in a CDC element / CDC FIFO cluster (its two clocks are pins of it)
        if hbm and any(by[i].kind == 'waypoint' and i in clocked for i, _ in eps):
            continue                 # a meso / launch station: the FIFO / launch register is the crossing
        ds = []
        for i, _ in eps:
            if hbm and by[i].kind == 'waypoint':
                continue             # forwarded station: the clock of its source travels with the data
            ds.append(_DOM.get(clocked.get(i), by[i].domain))
        if len(set(ds)) > 1:
            host = next((v for k, v in HBM_CDC_HOSTS.items() for i, _ in eps if hbm and by[i].master.startswith(k)), None)
            r = (att if host else out)[f'{cls}|{"->".join(ds)}']
            r['buses'] += 1
            r['bits'] += nb
            if host:
                r['cdc'] = host
            if len(r['examples']) < 3:
                r['examples'].append(bid)
    res = dict(out)
    if hbm:
        res = dict(unattributed=dict(out), attributed_to_block_cdc=dict(att))
    return res


def region_crossings(die, m):
    """buses whose endpoints sit in different clock regions (each needs a meso / ratio / async FIFO)."""
    if die == 'qwen_rom':
        regs = [(r['name'], r['rect']) for r in m['clock_regions']]
        dom = lambda it: it.domain  # noqa: E731
    elif die.startswith('s81'):
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


# ------------------------------------------------------------------------------------------------ RTL interfaces (HBM)
def interfaces(die, m, pw):
    """Die ports of the placeholder masters that stand for an RTL top, against that RTL's ports (r15 coll_rtl /
    attn_rtl): every RTL bit accounted for by a die port (or a block-internal fan-in / wrapper), no die bit without one."""
    out = {}
    V = m['variant']
    tu = parse_module('rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv', 'ot_hbm_accel_tu_endpoint')['ports']
    w = {p: d_w[1] for p, d_w in tu.items()}
    die = {p: n for (ms, p), n in pw.items() if ms == 'hfd_coll'}
    nl = len(m['links'])
    q = [p for p in die if p.startswith('t_su')]
    rows = dict(
        su_delivery_and_inject_request=dict(rtl=w['del_flit'] + w['del_valid'] + w['inj_idx'] + w['inj_rd'],
                                            die=sum(die[p] for p in q) - (len(q) - 1) * (w['inj_idx'] + w['inj_rd'])
                                            if q else 0,
                                            note='4 delivery lanes (545 + valid) one per SU quarter; inj_idx / inj_rd '
                                                 'broadcast to every quarter'),
        su_inject_data=dict(rtl=w['inj_data'], die_per_quarter=sorted({die[p] for p in die if p.startswith('f_su')}),
                            note='each quarter drives inj_data; the fan-in inside the block selects one'),
        config_in=dict(rtl=w['rank'] + w['pf'] + w['go'], die=die.get('f_cmdproc')),
        status_out=dict(rtl=w['fault'] + w['stat_credit_stall'], die=die.get('t_cmdproc')),
        link_tx=dict(rtl=w['ph_tx_v'] + w['ph_tx_flit'] + w['rx_credit'],
                     die=sum(n // 2 for p, n in die.items() if p.startswith('llk_'))),
        link_rx=dict(rtl=w['ph_rx_v'] + w['ph_rx_flit'] + w['sw_cr_ret'],
                     die=sum(n - n // 2 for p, n in die.items() if p.startswith('llk_'))),
        clocks=dict(rtl='clk / rst_n / pclk / prst_n', die=sorted(p for p in die if p.startswith(('pll', 'por')))),
        unmatched_die_ports=sorted(p for p in die if not p.startswith(('t_su', 'f_su', 'f_cmdproc', 't_cmdproc', 'llk_',
                                                                        'pll', 'por'))),
    )
    for k_, r in rows.items():
        if isinstance(r, dict) and 'die' in r and isinstance(r['die'], int):
            r['match'] = r['die'] >= r['rtl'] if k_.startswith('link') else r['die'] == r['rtl']
    rows['su_inject_data']['match'] = rows['su_inject_data']['die_per_quarter'] == [w['inj_data']]
    rows['clocks']['match'] = bool(rows['clocks']['die'])
    out['hfd_coll'] = dict(rtl='ot_hbm_accel_tu_endpoint', links=nl, checks=rows,
                           pass_=all(r.get('match', True) for r in rows.values() if isinstance(r, dict))
                           and not rows['unmatched_die_ports'])
    at = parse_module('rtl/hbm_accel/ot_attn_tile_registered_parent.sv', 'ot_attn_tile_registered_parent')['ports']
    aw = {p: d_w[1] for p, d_w in at.items()}
    tdie = {p: n for (ms, p), n in pw.items() if ms == 'hfd_attn_tile'}
    ld = sum(aw[p] for p in ('ld_v', 'ld_mode', 'ld_bank', 'ld_grp', 'ld_w', 'ld_w2v'))
    qq = sum(aw[p] for p in ('iv', 'ibank', 'ib'))
    oo = sum(aw[p] for p in ('ov', 'oy', 'oflt'))
    trows = dict(packet_ld=dict(rtl=ld, die=tdie.get('k')), packet_query=dict(rtl=qq, die=tdie.get('q')),
                 result=dict(rtl=oo, die=tdie.get('o')),
                 wrapper_forward_ports={p: tdie[p] for p in ('ci', 'cf', 'ri', 'rf', 'i') if p in tdie},
                 clocks=sorted(p for p in tdie if p in ('ck', 'rst')))
    for k_ in ('packet_ld', 'packet_query', 'result'):
        trows[k_]['match'] = trows[k_]['die'] is not None and trows[k_]['die'] - \
            sum(m.get('fclk', {}).get(b, (0, 0, 0))[1] for b in []) >= trows[k_]['rtl']
    fpk = {'ci', 'cf', 'ri', 'rf'}
    trows['wrapper_note'] = ('ci / cf / ri / rf carry the 1,618 b packet (the parent\'s `launch` register, one tile hop '
                             'each) and i the upstream result: tile die-wrapper ports, not ot_attn_tile_registered_parent '
                             'ports (owner HBM-ATTN)') if fpk & set(tdie) else ''
    out['hfd_attn_tile'] = dict(rtl='ot_attn_tile_registered_parent', checks=trows,
                                pass_=all(trows[k_]['match'] for k_ in ('packet_ld', 'packet_query', 'result'))
                                and trows['clocks'] == ['ck', 'rst'])
    return out


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
                names = _binding(rb, port)
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
    real = real_blocks('hbm', m)
    CUR_M['_by'] = {it.name: it for it in m['insts']}
    CUR_M['_real'] = real
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
        f = re.sub(r'_r?\d+$', '_*', mst) if re.match(r'hfd_(stn|mcast|gath|cdist|meso)_r?\d+$', mst) else \
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
            if mst in real or by[inst].kind in ('waypoint', 'link_station'):
                continue
            seg, _ = endpoint_dirs(die, real, by, bus, j)
            for a, b, d in seg or []:
                if d in ('in', 'io'):
                    io[mst][0] += b - a
                if d in ('out', 'io'):
                    io[mst][1] += b - a
    allm = {it.master for it in m['insts'] if it.master not in real and it.kind not in ('waypoint', 'link_station')}
    out = {}
    for mst in sorted(allm):
        i, o = io.get(mst, [0, 0])
        if i == 0 or o == 0:
            out[mst] = dict(in_bits=i, out_bits=o, shape='no die nets' if i == o == 0 else
                            ('sink: no output net' if o == 0 else 'source: no input net'))
        elif o * 100 < i and o <= 8:
            out[mst] = dict(in_bits=i, out_bits=o, shape='data sink: only a status / done output')
    return out


def ports_without_net(m, M, ports_w):
    """abstract ports a master declares that no die net binds (dead pins / missing net)."""
    used = {it.master for it in m['insts']}
    out = defaultdict(list)
    for name, mst in M.items():
        if name not in used:
            continue
        for p in mst.order:
            if not ports_w.get((name, p)):
                out[name].append(p)
    return dict(out)


def counterparts(die, m, ports_w):
    """placeholder abstract port bits against the RTL top that implements the block (bit totals; no binding)."""
    out = {}
    for mst, (f, mod) in COUNTERPARTS['hbm' if die == 'hbm' else 'qwen' if die == 'qwen_rom' else 's81'].items():
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


# ------------------------------------------------------------------------------------------------ abstract list (ROM dies)
# Status of every block family placed on the ROM dies (research 2026-10-05 PT on main 4f7fe01f3 + the owners' branches).
# Status codes (one per family; the family is as weak as its weakest part):
#   REAL_VIEW            a hardened view (LEF, + LIB where noted) is in the repo and the block it abstracts is final
#   REAL_VIEW_NOT_CLOSED a LEF exists but it was extracted from a route that is NOT closed (or is a pin-only shell)
#   RTL_CLOSED           RTL closed at its clock (SS 60 ps setup >= 0, FF 25 ps hold >= 0, 0.833 ns unless noted),
#                        no hardened view written
#   RTL_OPEN             RTL exists; routed but failing, or never routed
#   NO_RTL_TOP           logic needed but no RTL top (model ledger / generator rectangle only)
#   RESERVATION_ONLY     area reservation with no logic of its own
S81R8_FAMILIES = {      # r8 / r9 die masters (--s81-opts); a landed die view (physical/s81_die_views/views) overrides
    'dsfd_stn_*': dict(rtl='glue RTL generated by tools/dsrom_s81_fulldie.py (results/rtl/dsrom_s81_fulldie_20261004/<rev>/dsfd_glue.sv): one ot_fwd_link_stage (W <= 512) per lane slice, flops at both faces (falling edge '
                       'of the forwarded clock), fo = kept inverter', status='RTL_OPEN', owner='CLAUDE S81-RERUN',
                       closure='hop reg-to-reg fwd_hop2_v11 SS +373.97 / FF +246.18; die views of the 5 most-used masters '
                               '(1,811 of 2,593 stations) are closure-loop jobs s81-dsfd-stn*-b85da0774',
                       note='21 masters by lane signature; registered die view = the station itself (no added cycle)'),
    'dsfd_hstn_*': dict(rtl='glue RTL generated by tools/dsrom_s81_fulldie.py (results/rtl/dsrom_s81_fulldie_20261004/<rev>/dsfd_glue.sv): common-clock hub-bus station (one register stage)', status='RTL_OPEN',
                        owner='CLAUDE S81-RERUN', closure='never routed standalone', note='r9 hub-bus stations (CC reach 215 um)'),
    'dsfd_cfifo': dict(rtl='glue RTL generated by tools/dsrom_s81_fulldie.py (results/rtl/dsrom_s81_fulldie_20261004/<rev>/dsfd_glue.sv): ot_meso_fifo W564 entry crossing + column region root + registered status word',
                       status='RTL_OPEN', owner='CLAUDE S81-RERUN',
                       closure='meso core meso_d4_v7 SS +10.13 / FF +9.44 (below +15/+15): calibrated re-route closure-loop '
                               'job s81-meso-d4-f21799d1c; port record physical/s81_die_views/ports/layer/dsfd_cfifo',
                       note='xa/xb/cc are the FIFO output register ANDed with its valid (one gate after the flop)'),
    'dsfd_hend_*': dict(rtl='glue RTL generated by tools/dsrom_s81_fulldie.py (results/rtl/dsrom_s81_fulldie_20261004/<rev>/dsfd_glue.sv): hub end / start blocks (ot_meso_fifo / ot_ratio_cdc_fifo)', status='RTL_OPEN',
                        owner='CLAUDE S81-RERUN', closure='meso core as dsfd_cfifo', note='one master per instance (pin faces '
                        'follow its own peers): 8 RTL shapes'),
    'dsfd_rly_*': dict(rtl='glue RTL generated by tools/dsrom_s81_fulldie.py (results/rtl/dsrom_s81_fulldie_20261004/<rev>/dsfd_glue.sv): column relays (one register stage)', status='RTL_OPEN', owner='CLAUDE S81-RERUN',
                       closure='never routed standalone', note='49 masters by width and face pair'),
    'dsfd_sstn_*': dict(rtl='glue RTL generated by tools/dsrom_s81_fulldie.py (results/rtl/dsrom_s81_fulldie_20261004/<rev>/dsfd_glue.sv): slot stations', status='RTL_OPEN', owner='CLAUDE S81-RERUN', closure='never routed',
                        note=''),
    'dsfd_qbank_*': dict(rtl='glue RTL generated by tools/dsrom_s81_fulldie.py (results/rtl/dsrom_s81_fulldie_20261004/<rev>/dsfd_glue.sv): q-element bank stations', status='RTL_OPEN', owner='CLAUDE S81-RERUN',
                         closure='never routed', note=''),
    'dsfd_rstg': dict(rtl='glue RTL generated by tools/dsrom_s81_fulldie.py (results/rtl/dsrom_s81_fulldie_20261004/<rev>/dsfd_glue.sv): return-tree root stage', status='RTL_OPEN', owner='CLAUDE S81-RERUN',
                      closure='never routed', note=''),
    'dsfd_lkck_*': dict(rtl='glue RTL generated by tools/dsrom_s81_fulldie.py (results/rtl/dsrom_s81_fulldie_20261004/<rev>/dsfd_glue.sv): link-macro forwarded-clock relay (assign fo = fi; a CTS-sized clock buffer)',
                        status='RTL_OPEN', owner='CLAUDE S81-RERUN', closure='n/a (clock buffer, sized by die CTS)',
                        note='--link-fix: the SerDes / UCIe clock source on the macro ck face'),
    'dsfd_hbglue': dict(rtl='ot_s81_head_delay8x32', status='REAL_VIEW', owner='CODEX item8 / CLAUDE',
                        view=['physical/s81_die_views/hbglue/ot_s81_head_delay8x32/ (LEF + SS/FF LIB, 8d02d5505)'],
                        closure='routed leaf, SS/FF timing models exported', note='head-bundle skew element'),
    'dsfd_sp_hc_s': dict(rtl='no slab top; ot_hdc_sinkhorn', status='NO_RTL_TOP', owner='CLAUDE S81-PH',
                         closure='never routed (S81-PH twins, built to the simplification rules)', note='HC south half'),
    'dsfd_sp_hc_n': dict(rtl='no slab top; ot_hdc_sinkhorn', status='NO_RTL_TOP', owner='CLAUDE S81-PH',
                         closure='never routed (S81-PH twins)', note='HC north half'),
    'ot_dsrom_head_elem_A': dict(rtl='ot_dsrom_head_elem (recovery lever head.json)', status='REAL_VIEW_NOT_CLOSED',
                                 owner='CLAUDE', view=['results/rtl/dsrom_recovery_20261004/physcost/abstracts/ot_dsrom_head_elem_A.lef.gz'],
                                 closure='r4_A SS +24.4 / FF +8.5 (FF below +15)', note=''),
    'ot_dsrom_head_elem_B': dict(rtl='ot_dsrom_head_elem (recovery lever head.json)', status='REAL_VIEW_NOT_CLOSED',
                                 owner='CLAUDE', view=['results/rtl/dsrom_recovery_20261004/physcost/abstracts/ot_dsrom_head_elem_B.lef.gz'],
                                 closure='r4_B (FF below +15 as A)', note=''),
    'ot_s81_cfg7_seq': dict(rtl='ot_s81_cfg7_seq (rtl/v41die/ot_s81_cfg7_seq.sv)', status='RTL_OPEN', owner='CLAUDE S81-DIE',
                            closure='never routed standalone', note='cfg ROM sequencer, one per pair'),
    'ot_v41_rom_elem_q_qx_w10': dict(rtl='ot_v41_rom_elem_q_qx_w10 (QX10, QELEM)', status='REAL_VIEW_NOT_CLOSED',
                                     owner='CLAUDE QELEM', view=['results/rtl/dsrom_qz_20261004/Z20/Z20c/routed_element.lef.gz'],
                                     closure='Z20c die-context SS -60.7 after CTS (pre-margin); PQ q-element Z24b pending',
                                     note='die cases use Z20c until the PQ q-element posts'),
    'ot_pdie_*': dict(rtl='none (placeholder pin macro)', status='REAL_VIEW_NOT_CLOSED', owner='CLAUDE S81-RERUN',
                      view=['physical/asap7_v41x_pdie_macros_v2/ot_pdie_{serdes,ucie}/ (LEF + tt/ss/ff LIB: '
                            'tools/s81_pdie_corner_libs.py, HBM3E PHY corner method)'],
                      closure='n/a: pin-only shell with corner LIBs', note='real SerDes / UCIe hard IP abstract still needed'),
}

STATUS_ORDER = ['REAL_VIEW', 'REAL_VIEW_NOT_CLOSED', 'RTL_CLOSED', 'RTL_OPEN', 'NO_RTL_TOP', 'RESERVATION_ONLY']

S81_FAMILIES = {
    'ot_v41_rom_elem_q_qp_w10': dict(
        rtl='ot_v41_rom_elem_q_qp_w10 (rtl/v41rom/ot_v41_rom_elem_q_qp_w10.sv); successor QX10 ot_v41_rom_elem_q_qx_w10',
        status='REAL_VIEW_NOT_CLOSED', owner='CLAUDE QELEM',
        view=['results/uarch/dsrom_c_w4_20261003/s82_combined_r1/routed_q/routed_element.lef.gz (no LIB)'],
        closure='R_cap0 (the routed DB the LEF was read back from): SS -236.4 / FF -215.0 ps, not_met '
                '(results/rtl/dsrom_qz_20261004/r_cap0_classification.json); QX10 Z18c SS -3.90 / FF +7.01, Z18d SS +3.67 / '
                'FF -10.84 (results/physical/dsrom_qx10_z18_20261005); owner 20:30 PT: frame-D chase stopped, taller '
                'frames Z20a/b/c routing (510.84 x 209.52 / 192.24 / 177.12)',
        note='the die abstract is a readback of a failing route; the adopted element will be a taller frame (S81-DIE slot '
             'change). Lint S2: xs_q1 is an RTL input used as the x forward'),
    'ot_rom_4096x72_m8': dict(
        rtl='compiler ROM macro (functional model physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v)',
        status='REAL_VIEW', owner='CLAUDE S81-DIE',
        view=['results/uarch/dsrom_c_w4_20261003/s82_inputs/cfg.lef (= v1 physical/asap7_memory_macros/ot_rom_4096x72_m8/'
              'ot_rom_4096x72_m8.lef, 38.016 x 62.910, + _ss/_tt/_ff.lib)',
              'v2 aligned view physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ (38.040 x 62.952, LEF + 3 LIB) NOT used'],
        closure='macro (SS clk->q in results/uarch/v41_rom_depth_study.json)',
        note='generator uses the v1 (unaligned) view; v2 is the mirror-legal one. Lint S3: clk/ce/addr undriven, 7-way '
             'multi-driven cfg nets (no cfg sequencer RTL)'),
    'ot_hbm3e_phy_v41x_aw30_e8p5': dict(
        rtl='black box only (behavioural rtl/chip/ot_chip_v41x_hbm3e_phy.sv)', status='REAL_VIEW', owner='-',
        view=['physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/ (LEF + ss/tt/ff LIB + _bb.v)'],
        closure='generated macro (tools/mem_compiler/hbm_phy_gen.py), assumed boundary timing',
        note='"PHY + controller abstract, controller-side pins": overlaps dsfd_ctrl in function (uncertain)'),
    'ot_pdie_*': dict(
        rtl='none (placeholder pin macro, tools/chip_assembly/macros.py)', status='REAL_VIEW_NOT_CLOSED', owner='CODEX',
        view=['physical/asap7_v41x_pdie_macros_v2/ot_pdie_serdes/ (LEF, _tt.lib, _bb.v)',
              'physical/asap7_v41x_pdie_macros_v2/ot_pdie_ucie/ (LEF, _tt.lib, _bb.v)'],
        closure='n/a: pin-only shell (512 tx + 512 rx), TT LIB only',
        note='real SerDes / UCIe hard IP abstract still needed (SS/FF LIB)'),
    'dsfd_bf': dict(
        rtl='BF-capable pair: ot_v41_rom_elem_w10 BF16=1 XF=8 WAKE_REG=1 '
            '(results/uarch/dsrom_noECC_complete_element_20261002/physical_source_manifest.json)',
        status='RTL_OPEN', owner='CODEX',
        closure='never routed in the 1002.89 x 157.68 outline (inputs/wake.json: BF_SS_FF_closed false, '
                'fullframe_routed_fit false); old 0.92 ns TT routes errored',
        note='outline = mapped area; pairs with the q element (same pin order per lane)'),
    'dsfd_nvx': dict(
        rtl='ot_v41_rom_elem_nv_w10 NV=5 (rtl/v41rom/ot_v41_rom_elem_nv_w10.sv)', status='RTL_OPEN', owner='CLAUDE S81-DIE',
        closure='route_r4 NV5/XS8 SS -709.75 / FF -3.39 ps, REJECT (results/physical_abi3/asap7/chip/'
                'dsrom_l2_head_20261004/route_r4/verdict.json)',
        note='SUPERSEDED: recovery lever head.json (ADOPT) replaces head-die bf + nvx + cfg by ot_dsrom_head_elem, CLOSED '
             'r4_A SS +24.4 / FF +8.5 with LEFs results/rtl/dsrom_recovery_20261004/physcost/abstracts/'
             'ot_dsrom_head_elem_{A,B}.lef.gz -- the generator has not adopted it'),
    'dsfd_node': dict(
        rtl='ot_v41_retn_w17w10 (rtl/v41die/ot_v41_retn_w17w10.sv)', status='RTL_OPEN', owner='CODEX',
        closure='RTL only, never routed standalone', note='abstract has no clock/reset pin (lint S4b); leaf 63 b -> node 66 b'),
    'dsfd_fifo': dict(
        rtl='no block top; slot = ot_meso_fifo (rtl/common/ot_meso_fifo.sv) x3 + region fan-out', status='NO_RTL_TOP',
        owner='CLAUDE S81-DIE',
        closure='slot meso_d4_v7 CLOSED SS +10.13 / FF +9.44, 4,842 um2 (results/uarch/meso_fifo_20261004/verdict.json); '
                'the 3-slot + fan-out block is not built',
        note='generator area constant still names meso_d4_v3 (not closed); no wclk/rclk pins (lint S12a)'),
    'dsfd_mfifo': dict(
        rtl='no block top; slot = ot_meso_fifo (rtl/common/ot_meso_fifo.sv)', status='NO_RTL_TOP', owner='CLAUDE S81-DIE',
        closure='slot meso_d4_v7 CLOSED (as dsfd_fifo); the hub-side block is not built', note='hub-side meso / async slot'),
    'dsfd_stn_*': dict(
        rtl='no block top; stage = ot_fwd_link_stage (rtl/common/ot_fwd_link_stage.sv) x4 per waypoint x ceil(W/512)',
        status='NO_RTL_TOP', owner='CLAUDE S81-DIE',
        closure='fwd_hop2_v11 hop reg-to-reg SS +373.97 / FF +246.18; fixture port boundary not_met (-426.15 ps) '
                '(results/uarch/meso_fifo_20261004/verdict.json)',
        note='parameterised waypoint family (h: 1536 b + 836 tap, l: 1024 b, v: 1536 b); 2,304 W512 stage slices needed, '
             '0 instantiated, no forwarded-clock pin (lint S12b)'),
    'dsfd_svc': dict(
        rtl='no service top; parts ot_hdc_v41x_attn_tile_s / ot_attn_hgrp_m6h1 + ot_hdc_v41x_idx_*', status='NO_RTL_TOP',
        owner='CODEX',
        view=['leaf only: physical/hbm_fmax_attn/ot_attn_hgrp_m6h1/ (LEF + ss/ff LIB; HBM-die leaf, contextual tile not closed)'],
        closure='no block closure; WINDOW screen SS -1175.2 pre-layout (results/rtl/dsrom_window_full_block_screen_20261005)',
        note='16 attention tiles + pooled indexer ring reader per stack'),
    'dsfd_ctrl': dict(rtl='none (only the behavioural PHY model)', status='NO_RTL_TOP', owner='CODEX',
                      closure='none', note='streaming HBM3E controller + async FIFOs; no clock port (lint S7). The Qwen '
                      'ROM stream controller (qwen_hbm_sustained_bw ck2 r6, closed at 1.024 ns) is the nearest RTL'),
    'dsfd_sp_vm': dict(rtl='no slab top (behavioural ot_chip_v41x_tile u_tile.vm; SRAM ot_sram_1r1w_512x128_m4_r2c2)',
                       status='NO_RTL_TOP', owner='CODEX',
                       closure='none (old 0.92 ns TT slices only)', note='WFC child allocated beside it (codex ds-wfc)'),
    'dsfd_sp_su_*': dict(rtl='no slab top; lanes rtl/hdc/v41x/ot_dsrom_su_*.sv', status='NO_RTL_TOP', owner='CLAUDE SU-FUSION',
                         closure='lanes only: su_routeract SS +17.0 / FF +3.74 at 1.111 ns; su_hcpost +0.23 / +1.69; '
                                 'norm / swiglu / softmax components closed, levers PENDING_SSFF',
                         note='serial 0.9 GHz domain; su_n / su_s halves'),
    'dsfd_sp_hc': dict(rtl='no slab top; ot_hdc_sinkhorn (rtl/hdc/v41/ot_hdc_sinkhorn.sv) / ot_a3_hc_sinkhorn20_rne_pipe',
                       status='NO_RTL_TOP', owner='CODEX',
                       closure='ot_hdc_sinkhorn TT 4 ns setup -2.58 ns; a3 pipe closes at TT 3.7 / 4.0 ns only',
                       note='no output net (lint S9)'),
    'dsfd_sp_gather': dict(rtl='none (field spine ot_v41_spine_pqc_w17w10 may cover it: unconfirmed)', status='NO_RTL_TOP',
                           owner='CLAUDE FIELD-SPINE', closure='none (spine c0r16_h20 PASS_SCREEN_ONLY, not adopted)',
                           note='return gather of the 12 tier roots'),
    'dsfd_sp_capture': dict(rtl='none', status='NO_RTL_TOP', owner='CLAUDE FIELD-SPINE', closure='none', note=''),
    'dsfd_sp_collective': dict(rtl='ot_dsrom_link_rt (rtl/dsrom_sys/ot_dsrom_link_rt.sv)', status='RTL_OPEN', owner='CODEX',
                               closure='context_r1 SS -176.57 / FF -44.74, FAIL_CONTEXT_CLOCK (results/rtl/'
                                       'dsrom_baseline_link_clock_20261004/context_r1_FAIL/verdict.json)',
                               note='duplicate pll binding (lint S1)'),
    'dsfd_bk_selector': dict(rtl='none', status='NO_RTL_TOP', owner='CODEX', closure='none', note='band block'),
    'dsfd_bk_collector': dict(rtl='none', status='NO_RTL_TOP', owner='CODEX', closure='none',
                              note='band block; only its SRAM body has a retained macro abstract'),
}

QWEN_FAMILIES = {
    'ot_hbm3e_phy': dict(
        rtl='black box physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy/ot_hbm3e_phy_bb.v', status='REAL_VIEW', owner='-',
        view=['physical/asap7_memory_macros_v2_ew/ot_hbm3e_phy/ot_hbm3e_phy.lef + _ss/_tt/_ff.lib'],
        closure='generated macro (tools/mem_compiler/hbm_phy_gen.py), assumed boundary timing',
        note='"PHY + controller abstract": its clk / rst_n are bits of the dfi bundle from qfd_ctrl'),
    'qfd_cdc': dict(
        rtl='ot_qwen_stream4_cdc_pc (rtl/hdc/kv/ot_qwen_stream4_cdc_pc.sv; r7 RTL claude/qwen-stream4-cdc-20261005 @ '
            'ae2227660)', status='RTL_OPEN', owner='CLAUDE QWEN-PHYS',
        closure='core 0.833 / HBM 1.024 ns: r5 timing met but 12/34 slew pins REJECT (results/rtl/qwen_stream4_cdc_20261005/'
                'takeover_r5/verdict.json); r7c_u50 SS -1.06 (1 endpoint) / FF +10.14, slew 0 (EPYC1, uncommitted)',
        note='bound to its RTL ports here: clk / hclk / c_arst_n / h_arst_n have no die net'),
    'qfd_tile': dict(
        rtl='ot_qwen_rom_tile_w12 / logic ot_qwen_rom_tile_logic_w12 (rtl/hdc/ot_qwen_rom_tile_w12.sv) + 10 x '
            'ot_rom_4096x266_m8', status='RTL_OPEN', owner='CLAUDE QWEN-PHYS',
        view=['sub-view only: physical/asap7_memory_macros_v2/ot_rom_4096x266_m8/ (ROM macro LEF)'],
        closure='logic-only tile routes tp4_t4 SS -18.9 / FF -1.64 (6 slew), tp2_t4 SS -83.8 / FF +0.93 '
                '(results/rtl/hbm_accel_fmax_inventory_20261004/qwen_me/tile_failures_r1.json); full tile i605 failed',
        note='the re-framed die tile (centred tap row, M8 tree pins) was never routed'),
    'qfd_cst': dict(
        rtl='no station module; corridor-gate vehicle qcg_tile_column (rtl/chip/physical/qcg/qcg_tile_column.v)',
        status='RTL_OPEN', owner='CLAUDE QWEN-PHYS',
        closure='corridor segment D_tile_r2 (430.56 um, 637 signals) SS +11.85 / FF +29.7 but 20 max-slew pins, '
                'driver not_met (results/rtl/qwen_corridor_gate_20261003/D_tile_r2_released.json)',
        note='measures a corridor span, not the station frame (388-bit F2 station + tap FIFO slot)'),
    'qfd_chead': dict(rtl='none (column head = head-chain station + corridor split)', status='NO_RTL_TOP',
                      owner='CLAUDE QWEN-PHYS', closure='none', note='shares the station frame'),
    'qfd_reng': dict(
        rtl='ot_qwen_nearhbm_row_engine{,_p,_vp} (rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack*.sv)', status='RTL_OPEN',
        owner='OWNER DECISION (near-HBM attention DROPPED)',
        closure='DROPPED: r6 placement SS -2,700 ps; r8 retry never reached CTS (results/uarch/qwen_nearhbm_attn_rtl_20261003/'
                'pnr/retry_20261004/verdict.json, verdict DROP, c8d7ab368)',
        note='the die still places 24 row-engine frames (r1 328.32 x 1,998) of a dropped block'),
    'qfd_hub': dict(
        rtl='ot_qwen_nearhbm_attn_hub{,_p} (rtl/hdc/nearhbm/) + 4 link endpoints + X3 staging', status='RTL_OPEN',
        owner='OWNER DECISION (near-HBM attention DROPPED)',
        closure='hub_r7 SS -1,036.9 / FF -16.4, 2,473 slew; hub_r9 post-CTS -88.95 stopped, DROP (same verdict.json)',
        note='near-HBM combine of a dropped block; also the die clock root (ck_root -> ck_* trunks)'),
    'qfd_lfifo': dict(rtl='ot_meso_fifo (rtl/common/ot_meso_fifo.sv), probable', status='RTL_OPEN', owner='CLAUDE QWEN-PHYS',
                      closure='slot meso_d4_v7 closed (DS record results/uarch/meso_fifo_20261004); this 1,056-b strip-end '
                              'endpoint never routed',
                      note='strip-end mesochronous link endpoint, depth 8 + KV-new write'),
    'qfd_ctrl': dict(
        rtl='ot_hbm_r14_stream_stack (rtl/model_ready_hbm_r14/) + per-PC KV service rtl/hdc/kv/ot_qwen_rt_kv_stream*_service.sv',
        status='RTL_OPEN', owner='CODEX',
        closure='controller ck2 r6 CLOSED at 1.024 ns SS +19.0 / FF +2.94 (results/uarch/qwen_hbm_sustained_bw_20261003/'
                'physical-ss-ck2-r6-PASS.json); merge_r8 +25.57 / +3.86; the per-PC KV service (11.878 mm2/die) never routed',
        note='HBM 976.6 MHz domain; no clock net on the die (NO_CLOCK)'),
    'qfd_lst_*': dict(
        rtl='link span vehicle qcg_link_span430 (rtl/chip/physical/qcg/qcg_link_span430.v); station = 4 registered stages',
        status='RTL_CLOSED', owner='CLAUDE QWEN-PHYS',
        closure='E_tile_r2 SS +63.8 / FF +172.6, E_strip_r2 SS +69.3 / FF +141.4, slew 0 (results/rtl/qwen_corridor_gate_20261003/'
                'item7_E_*_r2_terminal)',
        note='parameterised link-station family (v: 2 x 1056, c: corner split, h: 1056, v_split / c_split: one link); '
             'the station master is not hardened'),
    'qfd_sp_vector_memory': dict(rtl='ot_qwen_rom_w1_frame_leaf (rtl/rom/qwen_vm_active_frame_20261005/)', status='RTL_OPEN',
                                 owner='CODEX', closure='exact bench PASS, no physical claim '
                                 '(results/rtl/qwen_rom_w1_frame_leaf_20261005/README.md)', note='serial 0.9 GHz; x root'),
    'qfd_sp_su64_sfu': dict(rtl='ot_hdc_vstream_rt SW64 (generated) + ot_hdc_sfu', status='RTL_OPEN', owner='CODEX',
                            closure='never measured (vstream_sw64 screen never committed)', note='serial 0.9 GHz'),
    'qfd_sp_tree_top': dict(rtl='ot_qwen_me_sptree_w12 (rtl/hdc/ot_qwen_me_spine_h_w12.sv)', status='RTL_OPEN',
                            owner='CLAUDE QWEN-PHYS', closure='sptree_tp2_t3 timed out: partial SS -8.76 / FF +1.88; ME spine '
                            'never synthesised (24 h yosys timeout)', note='ME result compaction'),
    'qfd_sp_constants_sequencer': dict(
        rtl='ot_qwen_rom_core (rtl/experimental/qwen_decode_pipe_20261004/ot_qwen_rom_core.sv) + VP sequencer '
            'ot_qwen_tp_seq_w12_vp (rtl/rom/) + constant ROM', status='RTL_OPEN', owner='CLAUDE QWEN-PHYS',
        closure='core CLOSED r5b_f3ba SS +0.87 / FF +7.12 in die context (results/rtl/qwen_core_decode_closure_20261004/'
                'claude_context_20261005/verdict.json, main c694570d6); sequencer CLOSED SS +4.56 / FF +14.32 '
                '(results/rtl/qwen_dspark_closure_20261004/routes/seqvp_la*_0833); constant ROM not routed',
        note='core + sequencer closed (no hardened view); the slab is open only on its constant ROM'),
    'qfd_port_tiles_*': dict(
        rtl='8 x ot_qwen_slab_port_group (rtl/physical/ot_qwen_slab_port_group.sv) per slab + 8 block-word meso FIFOs '
            '(meso_d4_v7) + scale ROM', status='RTL_OPEN', owner='CLAUDE QWEN-PHYS',
        closure='456 variant r6d_456_lead2 SS +6.64 / FF +8.21 but 120 slew pins, FAIL_ROUTED_COMPONENT '
                '(results/rtl/qwen_slab_share_20261005/takeover_r6/physical/terminal.json); r10a-f routing (EPYC1)',
        note='parameterised band-slab family: 6 primaries + 10 fragments (_f1/_f2/_f3); the die netlist has one master per '
             'slab, not 96 port-group instances'),
    'qfd_io_collective': dict(rtl='ot_rom_oneshot_die (rtl/rom/ot_rom_oneshot_allreduce.sv) + rtl/rom/collectives/',
                              status='RTL_OPEN', owner='CODEX',
                              closure='screen only: -1,208 ps reg-to-reg (~490 MHz) (results/rtl/risk_clock_loops_20261003/'
                              'screens/qwen/oneshot_die_d32_833.json)', note='serial 0.9 GHz; die PLL / clock root'),
    'qfd_io_embedding_rom': dict(rtl='ot_qwen_rt_embed_rom (rtl/hdc/ot_qwen_rt_embed_rom.sv)', status='RTL_OPEN',
                                 owner='CODEX', closure='never routed', note='no address input net on the die'),
    'qfd_io_ucie': dict(rtl='none', status='NO_RTL_TOP', owner='CODEX', closure='n/a',
                        note='UCIe PHY reservation (10 mm2): hard IP abstract needed (the S81 die uses ot_pdie_ucie)'),
    'qfd_io_serdes': dict(rtl='none', status='NO_RTL_TOP', owner='CODEX', closure='n/a',
                          note='SerDes PHY reservation (4 mm2): hard IP abstract needed (the S81 die uses ot_pdie_serdes)'),
}


def family_of(die, mst):
    if die.startswith('s81'):
        if mst.startswith('ot_pdie_'):
            return 'ot_pdie_*'
        if re.match(r'dsfd_stn_[hlv]$', mst) or re.match(r'dsfd_stn[hv]_', mst):
            return 'dsfd_stn_*'
        for pat, fam in ((r'dsfd_hstn[hv]_', 'dsfd_hstn_*'), (r'dsfd_(m2l|r2l|l2r)_', 'dsfd_hend_*'),
                         (r'dsfd_rly_', 'dsfd_rly_*'), (r'dsfd_node_', 'dsfd_node'), (r'dsfd_sstn_', 'dsfd_sstn_*'),
                         (r'dsfd_qbank_', 'dsfd_qbank_*'), (r'dsfd_lkck_', 'dsfd_lkck_*')):
            if re.match(pat, mst):
                return fam
        if re.match(r'dsfd_sp_su_[ns]$', mst):
            return 'dsfd_sp_su_*'
        return mst
    if mst.startswith('qfd_lst_'):
        return 'qfd_lst_*'
    if mst.startswith('qfd_port_tiles_'):
        return 'qfd_port_tiles_*'
    return mst


VIEWS = 'physical/s81_die_views/views'


def landed_views(masters):
    """die views landed by the closure loop (physical/s81_die_views/views/<master>/corner_sta.json): closed at SS and FF
    >= +15 ps at the 833.333 ps sign-off"""
    out = {}
    for mst in masters:
        f = ROOT / VIEWS / mst / 'corner_sta.json'
        if not f.exists():
            continue
        c = json.loads(f.read_text())
        ss, ff = c['setup_ss'].get('worst_slack_ps'), c['hold_ff'].get('worst_slack_ps')
        if ss is None or ff is None:
            continue
        out[mst] = dict(ss=ss, ff=ff, closed=ss >= 15.0 and ff >= 15.0, path=f'{VIEWS}/{mst}/ ({mst}.lef + SS/FF LIB)')
    return out


def rom_abstracts(die):
    """block-family inventory of one ROM die: what each family needs to become a real hardened abstract.
    With --s81-opts the S81 dies are the r8 / r9 die variant of those options (the recorded die case)."""
    dd = 's81r8_' + die.split('_')[1] if S81_OPTS and die in ('s81_layer', 's81_head') else die
    m, pw, M, tool = build(dd)
    table = QWEN_FAMILIES if die == 'qwen_rom' else dict(S81_FAMILIES, **(S81R8_FAMILIES if dd != die else {}))
    real = real_blocks(dd)
    cnt = Counter(it.master for it in m['insts'])
    fam = defaultdict(list)
    for mst, n in cnt.items():
        fam[family_of(die, mst)].append((mst, n))
    rows = []
    for f, lst in sorted(fam.items()):
        ms_ = sorted(x for x, _ in lst)
        insts = [i_ for i_ in m['insts'] if i_.master in ms_]
        sizes = sorted({(round(i_.w, 3), round(i_.h, 3)) for i_ in insts})
        ports = {}
        for mst in ms_:
            if mst in M:
                mm = M[mst]
                for p in mm.order:
                    sp = mm.ports[p]
                    face = sp[2] if sp[0] in ('face', 'phy') else sp[0]
                    b = pw.get((mst, p), 0) or 0
                    e = ports.setdefault(p, dict(bits=0, face=set(), masters=0))
                    e['bits'] = max(e['bits'], b)
                    e['face'].add(face)
                    e['masters'] += 1
            else:                                    # real LEF macro: ports = its die bundles (bound pin names)
                for p, names in (real.get(mst, {}).get('binding') or {}).items():
                    b = max((pw.get((mst, p), 0) or 0), 0)
                    ports.setdefault(p, dict(bits=b, face={'LEF'}, masters=1))
        for e in ports.values():
            e['face'] = '/'.join(sorted(e['face']))
            if e['masters'] == len(ms_):
                e.pop('masters')
        meta = table.get(f)
        lv = landed_views(ms_) if dd != die else {}
        if lv and meta is not None:
            ok_ = [x for x, v in lv.items() if v['closed']]
            meta = dict(meta, view=(meta.get('view') or []) + [v['path'] for v in lv.values()],
                        closure=meta['closure'] + '; landed die views: ' + ', '.join(
                            f"{x} SS {v['ss']:+.2f} / FF {v['ff']:+.2f}" for x, v in sorted(lv.items())))
            if len(ok_) == len(ms_):
                meta['status'] = 'REAL_VIEW'
            elif lv:
                meta['status'] = 'REAL_VIEW_NOT_CLOSED' if not ok_ else meta['status']
        if meta is None:
            meta = dict(rtl='UNKNOWN (new master: add it to the family table)', status='NO_RTL_TOP', owner='?',
                        closure='', note='')
        notes = sorted({M[x].note for x in ms_ if x in M})
        rows.append(dict(
            family=f, kind=insts[0].kind, domain=sorted({i_.domain for i_ in insts}), masters=ms_,
            distinct_masters=len(ms_), instances=sum(n for _, n in lst),
            per_master={x: n for x, n in sorted(lst)} if len(lst) > 1 else None,
            placeholder_size_um=sizes[:6], distinct_sizes=len(sizes),
            die_view='real LEF macro' if all(x not in M for x in ms_) else 'generated placeholder abstract'
            + (' (bound to its RTL ports in the lint)' if any(x in real for x in ms_) else ''),
            ports=ports, rtl_top=meta['rtl'], status=meta['status'], hardened_view=meta.get('view'),
            closure=meta['closure'], owner=meta['owner'], note=meta['note'], generator_note=notes[:2]))
    summ = Counter(r['status'] for r in rows)
    inst = Counter()
    for r in rows:
        inst[r['status']] += r['instances']
    return dict(
        schema='opentallas.rom_die_abstract_list.v1', die=die, generator=tool, generator_tag=gen_tag(tool.split()[0], gen_root(die)), s81_opts=S81_OPTS if dd != die else None,
        qwen_source={k: str(v) for k, v in qwen_src().items()} if die == 'qwen_rom' else None,
        qwen_recipe=(QWEN_R18 if QWEN_RECIPE == 'r18' else QWEN_R17B) if die == 'qwen_rom' else None, variant=m.get('variant'),
        die_um=[round(m['die']['w'], 3), round(m['die']['h'], 3)] if isinstance(m.get('die'), dict) else
        [round(max(i_.x + i_.w for i_ in m['insts']), 3), round(max(i_.y + i_.h for i_ in m['insts']), 3)],
        status_codes=STATUS_ORDER,
        summary=dict(kinds=len(rows), copies=sum(r['instances'] for r in rows),
                     families_by_status={s: summ.get(s, 0) for s in STATUS_ORDER},
                     instances_by_status={s: inst.get(s, 0) for s in STATUS_ORDER}),
        families=rows)


DIE_TITLE = dict(s81_layer='DeepSeek-V4.1 ROM S81 layer die', s81_head='DeepSeek-V4.1 ROM S81 head die',
                 qwen_rom='Qwen3-8B ROM die r17b')


def rom_readme(recs, out):
    L = ['# ROM-die block-family (hardened-abstract) inventory', '',
         'Generated by `python3 tools/die_top_lint.py abstracts --die rom --qwen-ref f76c3603b` (CLAUDE DIE-LINT, '
         '2026-10-06). Rerun the same command after a generator change (S81-DIE r8, QWEN-PHYS merge: then drop '
         '`--qwen-ref`). Status of each family is the research table in `tools/die_top_lint.py` '
         '(S81_FAMILIES / QWEN_FAMILIES); a new master shows up as UNKNOWN.', '',
         'Status codes: REAL_VIEW = LEF (+LIB) of a final block; REAL_VIEW_NOT_CLOSED = LEF of a failing route or a '
         'pin-only shell; RTL_CLOSED = closed at SS60/FF25, no view written; RTL_OPEN = RTL routed-but-failing or never '
         'routed; NO_RTL_TOP = logic with no RTL top; RESERVATION_ONLY = area, no logic.', '',
         'The HBM die list is `hbm_die_abstract_list.json` (round 1).', '']
    for die, rec in recs.items():
        s = rec['summary']
        g = rec['generator_tag']
        L += [f'## {DIE_TITLE[die]}', '',
              f'Generator `{rec["generator"]}` sha256 `{g["sha256"][:16]}`, file commit `{(g.get("file_commit") or "?")[:12]}`'
              + (f', from ref `{rec["qwen_source"]["commit"][:12]}` (overlay on main)' if rec.get('qwen_source') and
                 rec['qwen_source'].get('ref') not in (None, 'None') else '')
              + f'; tree `{(g.get("tree_head") or "?")[:12]}`. Die (or instance extent) {rec["die_um"][0]:.0f} x {rec["die_um"][1]:.0f} um.', '',
              '| kinds | copies | real view | real view, not closed / pin-only | RTL closed, no view | RTL open | '
              'no RTL top | reservation only |', '|---|---|---|---|---|---|---|---|',
              f'| {s["kinds"]} | {s["copies"]:,} | ' + ' | '.join(
                  f'{s["families_by_status"][k]} ({s["instances_by_status"][k]:,})' for k in STATUS_ORDER) + ' |', '',
              '(families, with instances in brackets)', '',
              '| family | masters | copies | size um (first) | status | owner |', '|---|---|---|---|---|---|']
        for r in sorted(rec['families'], key=lambda r: (STATUS_ORDER.index(r['status']), -r['instances'])):
            sz = r['placeholder_size_um'][0] if r['placeholder_size_um'] else ['-', '-']
            L.append(f'| `{r["family"]}` | {r["distinct_masters"]} | {r["instances"]:,} | {sz[0]} x {sz[1]}'
                     + (f' (+{r["distinct_sizes"] - 1})' if r['distinct_sizes'] > 1 else '')
                     + f' | {r["status"]} | {r["owner"]} |')
        L.append('')
    qf = out / 'qwen_rom_findings.json'
    if qf.exists():
        q = json.loads(qf.read_text())
        v = q['result']['verilator']
        L += ['## Qwen3-8B ROM die r17b: interface / connectivity lint (first lint of this die)', '',
              f'`qwen_rom_findings.json` (+ `qwen_rom_lint_top_lint.json`, Verilog top / stubs / shells). Census '
              f'{q["census"]["instances"]:,} instances, {q["census"]["buses"]:,} buses, {q["census"]["net_bits"]:,} net bits. '
              f'The top ELABORATES as generated (Verilator shell top rc={v["shell_top"]["rc"]}, full RTL '
              f'rc={v["full_rtl"]["rc"]}); {q["result"]["connectivity"]}.', '',
              '| id | severity | class | block |', '|---|---|---|---|']
        for f in q['findings']:
            L.append(f'| {f["id"]} | {f["severity"]} | {f["cls"]} | {f["block"]} |')
        L.append('')
    (out / 'README.md').write_text('\n'.join(L) + '\n')


# ------------------------------------------------------------------------------------------------ main
def run_lint(die, out, top_fix=False, tag=''):
    m, pw, M, tool = build(die, top_fix)
    R8_ACTIVE[0] = die.startswith('s81r8')
    real = real_blocks(die, m)
    CUR_M['_by'] = {it.name: it for it in m['insts']}
    CUR_M['_real'] = real
    F, unb, conflicting = lint_connectivity(die, m, real, pw)
    ck_rows, ck_ports, rst_rows = clock_reset(die, m, real)
    mp = dict(m, buses=[(b[0], b[1], b[2], [e for e in b[3] if e[0] != 'TOP']) for b in m['buses']])
    missing, away, spread = physical(die, mp, M, pw, real)
    ab = abut(die, mp)
    gp = gap(die, mp, pw) if not R8_ACTIVE[0] else gap_r8(mp)
    xr = region_crossings(die, mp)
    out.mkdir(parents=True, exist_ok=True)
    top = f'{die}{tag}_lint_top' + ('_fix' if top_fix else '')
    em = emit_verilog(die, m, real, pw, out, top)
    extra = (S.GLUE_RTL.replace('/r8/', f'/{S.out_rev()}/'), S.CFG7_RTL) if R8_ACTIVE[0] else ()
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
        schema='opentallas.die_top_lint.v1', die=die, top_fix=top_fix, generator=tool,
        generator_sha256=sha_gen(die, tool.split()[0]), generator_tag=gen_tag(tool.split()[0], gen_root(die)),
        qwen_source={k: str(v) for k, v in qwen_src().items()} if die == 'qwen_rom' else None,
        qwen_recipe=(QWEN_R18 if QWEN_RECIPE == 'r18' else QWEN_R17B) if die == 'qwen_rom' else None, pin_fit_errors=dict(PIN_FIT_ERRORS),
        lint_tool_sha256=sha('tools/die_top_lint.py'), variant=H._jsonable(m.get('variant')) if die == 'hbm' else m.get('variant'),
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
        reset=[dict(master=k[0], net=k[1], instances=n) for k, n in sorted(rst_rows.items())],
        interfaces=interfaces(die, m, pw) if die == 'hbm' else {},
        top_ports=list(LAST_TOP) if R8_ACTIVE[0] else 0,
        physical=dict(missing_pins=[dict(master=k[0], port=k[1], **v) for k, v in sorted(missing.items())],
                      face_away=[dict(master=k[0], port=k[1], orient=k[2], **v) for k, v in sorted(away.items())],
                      pin_spread=sorted(spread, key=lambda r: -r['span_um'])[:60],
                      pin_spread_count=len(spread),
                      abut_without_channel=[dict(compute=k[0], hub_kind=k[1], hub=k[2], **v) for k, v in sorted(ab.items())]),
        meso_forwarded_gap=dict(gp, clock_region_crossings=xr, clock_domain_crossings=domain_crossings(mp)),
        block_shape=block_shape(die, mp, real), counterparts=counterparts(die, m, pw),
        abstract_ports_without_net=ports_without_net(m, M, pw),
        top_fixes=TOP_FIXES if top_fix else {},
        verilog=dict(em, filelist=f'{top}.f', rtl_files=len(files), unresolved_modules=unresolved))
    (out / f'{top}_lint.json').write_text(json.dumps(rec, indent=1, default=str) + '\n')
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['lint', 'abstracts', 'vlsum'])
    ap.add_argument('--top')
    ap.add_argument('--die', choices=['s81_layer', 's81_head', 'hbm', 'qwen_rom', 'rom', 's81r8_layer', 's81r8_layer1', 's81r8_head'])
    ap.add_argument('--qwen-recipe', default='r17b', choices=['r17b', 'r18'])
    ap.add_argument('--qwen-ref', help='git ref of the Qwen die generator when it is not on this tree (e.g. f76c3603b)')
    ap.add_argument('--top-fix', action='store_true')
    ap.add_argument('--s81-opts', default='', help='s81r8 dies: generator die options of the case, e.g. '
                    '"--rev r9 --elem-h 198.72 --cc-reach-um 215 --vch-interleave"')
    ap.add_argument('--tag', default='', help='output name tag (e.g. _r15)')
    ap.add_argument('--variant', default='', help='hbm: tools/hbm_accel_die_fp.py --variant (default: its adopted r16g)')
    ap.add_argument('--out', type=Path, default=ROOT / OUT)
    a = ap.parse_args(argv)
    global VARIANT, S81_OPTS
    S81_OPTS = a.s81_opts
    VARIANT = a.variant
    global QWEN_REF, QWEN_RECIPE
    QWEN_REF = a.qwen_ref
    QWEN_RECIPE = a.qwen_recipe
    if a.mode == 'vlsum':
        s = vlsum(a.out / f'{a.top}.verilator.log', a.top)
        (a.out / f'{a.top}_verilator_summary.json').write_text(json.dumps(s, indent=1) + '\n')
        print(json.dumps(s, indent=1))
        return 0
    if a.mode == 'lint':
        rec = run_lint(a.die, a.out, a.top_fix, a.tag)
        print(json.dumps(rec['census']))
    elif a.die == 'rom' or (a.die and a.die != 'hbm'):
        a.out.mkdir(parents=True, exist_ok=True)
        recs = {}
        for die in (('s81_layer', 's81_head', 'qwen_rom') if a.die == 'rom' else (a.die,)):
            recs[die] = rom_abstracts(die)
            (a.out / f'{die}_abstract_list.json').write_text(json.dumps(recs[die], indent=1, default=str) + '\n')
            print(die, json.dumps(recs[die]['summary']))
        if a.die == 'rom':
            rom_readme(recs, a.out)
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
