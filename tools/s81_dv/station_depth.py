#!/usr/bin/env python3
"""station_depth.py -- S81-FRAME-FIX-1 (11-11): register depth of the S81 frame pass-through stations, read from the
bound RTL (single source of truth for every compiler / schedule tracer that walks a station).

Why: dc23a738f3 (S81-KITS-RTLC 10-24) made dsfd_qbank_N/_S, dsfd_rstg, ot_s81_sstn_payload536 and ot_s81_sstn_base566
2 flops deep, but the frame return topology (frame_return_plan.topology), the frame emission calendar
(frame_return_plan.emission) and the LP schedule extractor (frame_schedule.py) all counted a station as a hard-coded
+1 edge, so the field compiler emitted the pre-RTLC calendar and the frame bench faults on main (TOK-VERIFY-1 11-11).

What: STEP names, per station master, which input pin feeds each output pin (the wiring contract, no timing).  depth()
elaborates the station's RTL (default defines, i.e. no bench mutants; `ifdef blocks resolved) into a signal graph
(assign / @(*) = 0 edges, posedge / negedge register = 1 edge, child instances = their own depth) and returns the
number of register edges from the input pin to the output pin; every bit-path must agree, else it raises.

OT_S81_STATION_DEPTH_OVERRIDE='{"dsfd_rstg": 1, ...}' forces a depth (negative controls only: the frame gate's
wrong-depth control must FAULT)."""
import functools
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def rtl_root():
    '''the tree whose RTL the frame is bound to: the selected frame source root when a compile runs on one
    (OT_S81_FRAME_SOURCE_ROOT / OT_S81_SELECTED_SOURCE_ROOT, as frame_return_plan.plan_phase hashes), else this tree'''
    return Path(os.environ.get('OT_S81_FRAME_SOURCE_ROOT') or os.environ.get('OT_S81_SELECTED_SOURCE_ROOT') or ROOT)

# the bound RTL the frame bench / frame wrapper elaborates (tools/s81_dv/frame_wrap.RTL_FILES + the relay primitive)
RTL_FILES = [
    'rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv',
    'rtl/dsrom_sys/s81_glue/ot_s81_rly.sv',
    'rtl/dsrom_sys/s81_glue/dsfd_rly_masters.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_536.sv',
    'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_266ew.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv',
    'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_c26l.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_gen18.sv',
    'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_v16.sv',
    'rtl/dsrom_sys/s81_static_net/ot_s81_sstn_base566.sv', 'rtl/dsrom_sys/s81_static_net/ot_s81_sstn_payload536.sv',
    'rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv',
    'rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_N.sv', 'rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_S.sv',
]


def step(master, out_pin):
    """(input pin feeding out_pin, register edges in between) for a pass-through station master, else None"""
    if master.startswith(('dsfd_rly', 'dsfd_dvrly')) or master in ('ot_s81_rly', 'dsfd_rstg', 'ot_s81_sstn_payload536'):
        if out_pin != 'o':
            return None
        src = 'i'
    elif master.startswith('dsfd_qbank') and out_pin.startswith('d_'):
        src = 'e_' + out_pin[2:]
    elif master.startswith('dsfd_qbank') and out_pin.startswith('o_'):
        src = 'i_' + out_pin[2:]
    elif master == 'ot_s81_sstn_base566':
        src = {'xa': 'xai', 'xb': 'xbi', 'cc': 'cci'}.get(out_pin)
        if src is None:
            return None
    else:
        return None
    return src, depth(master, out_pin, src)


# ------------------------------------------------------------------------------------------------ RTL elaboration
_LIT = re.compile(r"\d*\s*'[sS]?[bBhHdDoO][0-9a-fA-FxXzZ_?]+")
_KW = {'if', 'else', 'begin', 'end', 'posedge', 'negedge', 'or', 'and', 'not', 'reg', 'wire', 'logic', 'int',
       'genvar', 'for', 'generate', 'endgenerate', 'assign', 'always', 'localparam', 'parameter', 'input', 'output'}


def preprocess(text, defines=()):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//[^\n]*', '', text)
    out, stack = [], []          # stack of [active, taken]
    for line in text.split('\n'):
        s = line.strip()
        m = re.match(r'`(ifdef|ifndef|elsif)\s+(\w+)', s)
        if m:
            d, live = m.group(2) in defines, all(a for a, _ in stack)
            if m.group(1) == 'ifdef':
                stack.append([d, d])
            elif m.group(1) == 'ifndef':
                stack.append([not d, not d])
            else:
                top = stack[-1]
                top[0] = (not top[1]) and d
                top[1] = top[1] or d
            continue
        if s.startswith('`else'):
            top = stack[-1]
            top[0] = not top[1]
            top[1] = True
            continue
        if s.startswith('`endif'):
            stack.pop()
            continue
        if s.startswith('`'):
            continue
        if all(a for a, _ in stack):
            out.append(line)
    return '\n'.join(out)


def _modules():
    return _modules_at(str(rtl_root()))


@functools.lru_cache(maxsize=None)
def _modules_at(root):
    mods = {}
    for f in RTL_FILES:
        t = preprocess((Path(root) / f).read_text())
        for m in re.finditer(r'\bmodule\s+(\w+)(.*?)\bendmodule\b', t, re.S):
            mods.setdefault(m.group(1), (f, m.group(2)))
    return mods


def _ids(expr):
    return {x for x in re.findall(r'\b[A-Za-z_]\w*\b', _LIT.sub(' ', expr)) if x not in _KW}


def _split_top(s):
    out, dep, cur = [], 0, ''
    for ch in s:
        dep += ch in '({['
        dep -= ch in ')}]'
        if ch == ',' and dep == 0:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [x.strip() for x in out]


def _graph(module):
    return _graph_at(str(rtl_root()), module)


@functools.lru_cache(maxsize=None)
def _graph_at(root, module):
    """signal -> [(driver signal, edges)]"""
    mods = _modules()
    if module not in mods:
        raise KeyError(f'station master {module} not in the bound RTL ({len(RTL_FILES)} files)')
    body = mods[module][1]
    hdr_end = body.index(');')
    body = body[hdr_end + 2:]
    g = {}

    def edge(lhs, rhs, w):
        for a in _ids(lhs):
            for b in _ids(rhs):
                g.setdefault(a, []).append((b, w))
    for m in re.finditer(r'\bassign\s+([^=;]+?)\s*=\s*([^;]+);', body):
        edge(m.group(1), m.group(2), 0)
    # always blocks: text up to the next always / assign / instance-free terminator
    starts = [m for m in re.finditer(r'\balways\s*@\s*\(([^)]*)\)', body)]
    for k, m in enumerate(starts):
        end = starts[k + 1].start() if k + 1 < len(starts) else len(body)
        blk = body[m.end():end]
        blk = re.split(r'\bassign\b|\bend\s+endgenerate\b', blk)[0]
        seq = 'posedge' in m.group(1) or 'negedge' in m.group(1)
        if seq:
            for a in re.finditer(r'(\w+)\s*(?:\[[^\]]*\])?\s*<=\s*([^;]+);', blk):
                edge(a.group(1), a.group(2), 1)
        else:
            for a in re.finditer(r'(\w+)\s*(?:\[[^\]]*\])?\s*(?<![<>=!])=(?!=)\s*([^;]+);', blk):
                edge(a.group(1), a.group(2), 0)
    # child instances of other bound modules
    for m in re.finditer(r'\b(\w+)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s+(\w+)\s*\(((?:[^;])*?)\)\s*;', body):
        child = m.group(1)
        if child not in mods or child == module:
            continue
        conns = {}
        for c in _split_top(m.group(3)):
            pm = re.match(r'^\.(\w+)\s*\((.*)\)$', c, re.S)
            if pm:
                conns[pm.group(1)] = pm.group(2)
        for op, oe in conns.items():
            for ip, ie in conns.items():
                if op == ip:
                    continue
                ds = _depths(child, op, ip)
                if ds:
                    assert len(ds) == 1, (child, op, ip, ds)
                    edge(oe, ie, next(iter(ds)))
    return g


def _depths(module, out_pin, in_pin):
    return _depths_at(str(rtl_root()), module, out_pin, in_pin)


@functools.lru_cache(maxsize=None)
def _depths_at(root, module, out_pin, in_pin):
    g = _graph(module)
    res = set()

    def walk(s, acc, seen):
        if s == in_pin:
            res.add(acc)
            return
        for b, w in g.get(s, []):
            if b not in seen:
                walk(b, acc + w, seen | {b})
    walk(out_pin, 0, {out_pin})
    return frozenset(res)


def _override():
    v = os.environ.get('OT_S81_STATION_DEPTH_OVERRIDE')
    return json.loads(v) if v else {}


def depth(master, out_pin, in_pin):
    ov = _override()
    if master in ov:
        return int(ov[master])
    ds = _depths(master, out_pin, in_pin)
    if len(ds) != 1:
        raise ValueError(f'station {master}.{out_pin} <- {in_pin}: register depth not unique in RTL: {sorted(ds)}')
    return next(iter(ds))


STATION_PINS = {'dsfd_qbank_N': ['d_r0', 'd_r1', 'd_st'], 'dsfd_qbank_S': ['o_cfg', 'o_go', 'o_x0', 'o_x1'],
                'dsfd_rstg': ['o'], 'ot_s81_sstn_payload536': ['o'], 'ot_s81_sstn_base566': ['xa', 'xb', 'cc'],
                'ot_s81_rly': ['o']}


def fingerprint():
    """{master: {out pin: register edges}} of the pass-through stations: stored in every schedule record that counts
    them, compared on load (a stale record is refused, never re-used)"""
    return {m: {p: step(m, p)[1] for p in ps} for m, ps in sorted(STATION_PINS.items())}


if __name__ == '__main__':
    print(json.dumps(fingerprint(), indent=1))
