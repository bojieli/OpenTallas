#!/usr/bin/env python3
"""xtier_land.py -- S81-FRAME-FIX-1 / x-tier (11-11): the slice x-tier (u_xr) leaf-interface landing edges, read from the
bound RTL (single source of truth for every compiler constant that crosses the xr lo / p / e leaf faces).

Why: dc23a738f3 (S81-KITS-RTLC 10-24) made ot_s81sl_xrt FACE_LAND = 1 the default (lo / p / e land in one pin register
before anything else: "+1 cycle on lo -> send, p -> xfin partials and e -> ENG collection", ot_s81sl_xrt.sv header of the
face landing).  The die binds ot_s81sl_xrt1 / xrt3 (ot_s81sl_slice.sv `ifdef OT_S81SL_KV_TRANSPORT; every
physical/die_plan/s81/bind/asbuilt_*.json selects it), but lower_vpx.LO_AFTER_CTL 15, leaf_transport.LO_LOCAL 7 and
dv_layer_compile.XFIN collector 5 were measured / written for ot_s81sl_xr (no face landing), so the compiler issued the
lo / p paths one edge late on the bound die.

What: form() resolves, for the selected defines, which u_xr master the slice instantiates (ot_s81sl_slice.sv, generate /
`ifdef resolved), the FACE_LAND / RING_LAND the master elaborates with (instance override, else the wrapper's default,
i.e. the active `define OT_S81SL_XRT_FLAND_DEF / _RLAND_DEF), and then elaborates ot_s81sl_xrt's body with those
parameters (generate-if resolved, mutant `ifdefs off) into a signal graph (assign / @(*) = 0, posedge register = 1 edge,
negedge register = 0 edges: a negedge pin flop in front of a posedge flop is the same cycle at every posedge consumer,
RF-J) and counts the register edges from each leaf-face port (lo_v / lo_d, p_v / p_d, e_v / e_c / e_d) to the internal
signal the FACE_LAND = 0 module reads (lo_v_i ...), and from each ring / band port (dl_ev ...) to dl_ev_i ... .  Every
bit-path must agree, else it raises (fail-closed, no default).  ot_s81sl_xr (no landing stage) = 0 edges by
construction; the walk asserts it has no FACE_LAND parameter.

Selected defines: OT_S81_SELECTED_DEFINES (comma list, the die bind's +define set; slice_source.bind_defines) when the
variable is SET (an empty value = no defines = the ot_s81sl_xr form); unset = DIE_DEFINES, the define the as-built die
manifests select (gate: test_xtier_land.py checks every asbuilt_*.json resolves to the same form).
RTL root: OT_S81_SELECTED_SOURCE_ROOT, else this tree."""
import functools
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SLICE = 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv'
XRT = 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv'
XR = 'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xr.sv'
DIE_DEFINES = ('OT_S81SL_KV_TRANSPORT',)       # the as-built die manifests' xr form selector (gate-checked)
FACES = dict(lo=('lo_v', 'lo_d'), p=('p_v', 'p_d'), e=('e_v', 'e_c', 'e_d'))
RING = ('dl_ev', 'dl_wv', 'dl_vv', 'dl_e', 'dl_w', 'dl_vb')


def selected_defines():
    v = os.environ.get('OT_S81_SELECTED_DEFINES')
    if v is None:
        return frozenset(DIE_DEFINES)
    return frozenset(d for d in v.split(',') if d)


def rtl_root():
    return Path(os.environ.get('OT_S81_SELECTED_SOURCE_ROOT') or ROOT)


# ------------------------------------------------------------------------------------------------ preprocess
def preprocess(text, defines):
    """strip comments, resolve `ifdef / `ifndef / `elsif / `else / `endif, collect active `define NAME VALUE, expand
    `NAME of those macros; returns (text, macros)"""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'//[^\n]*', '', text)
    out, stack, macros = [], [], {}
    for line in text.split('\n'):
        s = line.strip()
        m = re.match(r'`(ifdef|ifndef|elsif)\s+(\w+)', s)
        if m:
            d = m.group(2) in defines or m.group(2) in macros
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
        if not all(a for a, _ in stack):
            continue
        m = re.match(r'`define\s+(\w+)\s*(.*)$', s)
        if m:
            macros[m.group(1)] = m.group(2).strip()
            continue
        if s.startswith('`'):
            continue
        out.append(line)
    body = '\n'.join(out)
    body = re.sub(r'`(\w+)', lambda m: macros.get(m.group(1), m.group(0)), body)
    return body, macros


@functools.lru_cache(maxsize=None)
def _file(root, rel, defines):
    raw = (Path(root) / rel).read_bytes()
    text, macros = preprocess(raw.decode(), defines)
    mods = {m.group(1): m.group(2) for m in re.finditer(r'\bmodule\s+(\w+)(.*?)\bendmodule\b', text, re.S)}
    return text, macros, mods, hashlib.sha256(raw).hexdigest()


def _int(v):
    v = v.strip()
    m = re.fullmatch(r"(?:\d+)?'[sS]?([dDhHoObB])([0-9a-fA-F_]+)", v)
    if m:
        return int(m.group(2).replace('_', ''), dict(d=10, h=16, o=8, b=2)[m.group(1).lower()])
    return int(v)


def _params(header):
    """parameter defaults of a module header"""
    hdr = header.split(');', 1)[0]
    return {m.group(1): m.group(2) for m in re.finditer(r'parameter\s+(?:integer\s+|\[[^\]]*\]\s*)?(\w+)\s*=\s*([^,)]+)', hdr)}


# ------------------------------------------------------------------------------------------------ generate resolution
def _match_end(text, i):
    """text[i:] starts right after a `begin`; index just past the matching `end`"""
    depth = 1
    for m in re.compile(r'\b(begin|end)\b').finditer(text, i):
        depth += 1 if m.group(1) == 'begin' else -1
        if depth == 0:
            return m.end()
    raise ValueError('unbalanced begin / end in generate')


def _eval(cond, env):
    ids = set(re.findall(r'\b[A-Za-z_]\w*\b', cond))
    if not ids <= set(env):
        return None
    expr = re.sub(r"\d*'[sS]?[dDhHoObB][0-9a-fA-F_]+", lambda m: str(_int(m.group(0))), cond)
    expr = re.sub(r'!(?!=)', ' not ', expr.replace('&&', ' and ').replace('||', ' or '))
    return bool(eval(expr, {'__builtins__': {}}, dict(env)))


def _if_chain(text, i, env):
    """text[i:] starts at `if (`; returns (end index, kept text)"""
    m = re.compile(r'if\s*\(').match(text, i)
    j, depth = m.end(), 1
    while depth:
        depth += {'(': 1, ')': -1}.get(text[j], 0)
        j += 1
    cond = text[m.end():j - 1]
    bm = re.compile(r'\s*begin\b(\s*:\s*\w+)?').match(text, j)
    if not bm:
        raise ValueError('generate if without begin: ' + cond)
    e = _match_end(text, bm.end())
    then = text[bm.end():e - 3]
    rest, k = '', e
    em = re.compile(r'\s*else\b').match(text, e)
    if em:
        k = em.end()
        im = re.compile(r'\s*(?=if\s*\()').match(text, k)
        if im:
            k, rest = _if_chain(text, im.end(), env)
        else:
            bm2 = re.compile(r'\s*begin\b(\s*:\s*\w+)?').match(text, k)
            e2 = _match_end(text, bm2.end())
            rest, k = text[bm2.end():e2 - 3], e2
    v = _eval(cond, env)
    kept = then if v is True else rest if v is False else then + '\n' + rest
    return k, kept


def resolve_generate(body, env):
    out, pos = [], 0
    pat = re.compile(r'\bgenerate\s+(?=if\s*\()')
    while True:
        m = pat.search(body, pos)
        if not m:
            out.append(body[pos:])
            return ''.join(out)
        out.append(body[pos:m.start()])
        k, kept = _if_chain(body, m.end(), env)
        em = re.compile(r'\s*endgenerate\b').match(body, k)
        if not em:
            raise ValueError('generate if not closed by endgenerate')
        out.append(resolve_generate(kept, env))
        pos = em.end()


# ------------------------------------------------------------------------------------------------ register-edge graph
_LIT = re.compile(r"\d*\s*'[sS]?[bBhHdDoO][0-9a-fA-FxXzZ_?]+")
_KW = {'if', 'else', 'begin', 'end', 'posedge', 'negedge', 'or', 'and', 'not', 'reg', 'wire', 'logic', 'integer',
       'for', 'assign', 'always'}


def _ids(expr):
    return {x for x in re.findall(r'\b[A-Za-z_]\w*\b', _LIT.sub(' ', expr)) if x not in _KW}


def _graph(body):
    g = {}

    def edge(lhs, rhs, w):
        for a in _ids(re.sub(r'\[[^\]]*\]', '', lhs)):
            for b in _ids(rhs):
                g.setdefault(a, set()).add((b, w))
    for m in re.finditer(r'\bassign\s+([^=;]+?)\s*=\s*([^;]+);', body):
        edge(m.group(1), m.group(2), 0)
    starts = list(re.finditer(r'\balways\s*@\s*\(([^)]*)\)', body))
    for k, m in enumerate(starts):
        end = starts[k + 1].start() if k + 1 < len(starts) else len(body)
        blk = re.split(r'\bassign\b|\bgenerate\b|\bendgenerate\b', body[m.end():end])[0]
        if 'posedge' in m.group(1) or 'negedge' in m.group(1):
            w = 1 if 'posedge' in m.group(1) else 0
            for a in re.finditer(r'(\w+)\s*(?:\[[^\]]*\])?\s*<=\s*([^;]+);', blk):
                edge(a.group(1), a.group(2), w)
        else:
            for a in re.finditer(r'(\w+)\s*(?:\[[^\]]*\])?\s*(?<![<>=!])=(?!=)\s*([^;]+);', blk):
                edge(a.group(1), a.group(2), 0)
    return g


def _depths(g, sig, port):
    res = set()

    def walk(s, acc, seen):
        if s == port:
            res.add(acc)
            return
        for b, w in g.get(s, ()):
            if b not in seen:
                walk(b, acc + w, seen | {b})
    walk(sig, 0, {sig})
    return res


def _edges(g, pairs, what):
    out = set()
    for sig, port in pairs:
        ds = _depths(g, sig, port)
        if len(ds) != 1:
            raise ValueError(f'{what}: {sig} <- {port} register depth not unique in RTL: {sorted(ds)}')
        out |= ds
    if len(out) != 1:
        raise ValueError(f'{what}: bit-paths disagree: {sorted(out)}')
    return out.pop()


# ------------------------------------------------------------------------------------------------ the bound form
def _xr_choice(slice_text):
    """{(master, override text)} the slice's u_xr generate branches instantiate"""
    return {(m.group(1), m.group(2) or '') for m in
            re.finditer(r'\b(ot_s81sl_xrt?[13])\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*u_xr\s*\(', slice_text)}


@functools.lru_cache(maxsize=None)
def _form(root, defines):
    st, _, smods, ssha = _file(root, SLICE, defines)
    choice = _xr_choice(smods['ot_s81sl_slice'])
    fams = {m.rstrip('13') for m, _ in choice}
    if len(fams) != 1 or len(choice) != 2:
        raise ValueError(f'slice u_xr selection not one family with C1 / C3 branches: {sorted(choice)}')
    fam = fams.pop()
    dl = {_int(v) for k, v in _params(smods['ot_s81sl_slice']).items() if k == 'DL'}
    if len(dl) != 1:
        raise ValueError('ot_s81sl_slice DL default unresolved')
    rec = dict(schema='opentallas.s81.xtier_land.v1', defines=sorted(defines), rtl_root=str(root), family=fam,
               masters=sorted(m for m, _ in choice), slice_dl=dl.pop(), sources={SLICE: ssha})
    if fam == 'ot_s81sl_xr':
        _, _, xmods, xsha = _file(root, XR, defines)
        rec['sources'][XR] = xsha
        for m, _ in choice:
            if m not in xmods:
                raise ValueError(f'{m} not defined in {XR}')
        if any('FACE_LAND' in b or 'RING_LAND' in b for b in xmods.values()):
            raise ValueError(f'{XR} grew a landing parameter: extend xtier_land')
        rec.update(face_land=0, ring_land=0, face_edges=dict(lo=0, p=0, e=0), ring_edges=0)
        return rec
    _, macros, xmods, xsha = _file(root, XRT, defines)
    rec['sources'][XRT] = xsha
    per = {}
    for m, ov in sorted(choice):
        hdr = _params(xmods[m])
        prm = {}
        for p in ('FACE_LAND', 'RING_LAND'):
            o = re.search(r'\.' + p + r'\s*\(\s*([^)]+?)\s*\)', ov)
            prm[p] = _int(o.group(1) if o else hdr[p])
            if not re.search(r'\bot_s81sl_xrt\s*#\s*\([^;]*\.' + p + r'\s*\(\s*' + p + r'\s*\)', xmods[m]):
                raise ValueError(f'{m} does not pass {p} through to ot_s81sl_xrt')
        for f in [x for fs in FACES.values() for x in fs] + list(RING):
            if not re.search(r'\.' + f + r'\s*\(\s*' + f + r'\b', xmods[m]):
                raise ValueError(f'{m}.{f} is not wired straight to ot_s81sl_xrt.{f}')
        hb = re.search(r'\bot_s81sl_xrt\s*#\s*\([^;]*\.HB\s*\(\s*(\d+)\s*\)', xmods[m])
        core = _params(xmods['ot_s81sl_xrt'])
        env = {k: _int(v) for k, v in core.items() if re.fullmatch(r"[\d'sSdDhHoObB_a-fA-F]+", v.strip())}
        env.update(prm, HB=int(hb.group(1)) if hb else env.get('HB', 0))
        body = resolve_generate(xmods['ot_s81sl_xrt'].split(');', 1)[1], env)
        g = _graph(body)
        fe = {k: _edges(g, [(s + '_i', s) for s in sigs], f'{m} face {k}') for k, sigs in FACES.items()}
        re_ = _edges(g, [(s + '_i', s) for s in RING], f'{m} ring')
        per[m] = dict(face_land=prm['FACE_LAND'], ring_land=prm['RING_LAND'], face_edges=fe, ring_edges=re_)
    vals = {json.dumps(v, sort_keys=True) for v in per.values()}
    if len(vals) != 1:
        raise ValueError(f'xrt1 / xrt3 landing forms differ: {per}')
    rec.update(json.loads(vals.pop()))
    rec['macros'] = {k: macros[k] for k in ('OT_S81SL_XRT_FLAND_DEF', 'OT_S81SL_XRT_RLAND_DEF') if k in macros}
    return rec


def _override():
    v = os.environ.get('OT_S81_XTIER_FACE_OVERRIDE')
    return json.loads(v) if v else {}


def form(defines=None, root=None):
    """the bound x-tier landing form (see module doc); defines=None = selected_defines().
    OT_S81_XTIER_FACE_OVERRIDE='{"lo": 0}' forces face edges (negative controls only: the xrt vpx gate's stale-constant
    control must FAIL on the xrt bench); a forced form carries face_edges_override."""
    d = selected_defines() if defines is None else frozenset(defines)
    f = dict(_form(str(root or rtl_root()), d))
    ov = _override()
    if ov:
        f['face_edges'] = {**f['face_edges'], **{k: int(v) for k, v in ov.items()}}
        f['face_edges_override'] = ov
    return f


def face_edges(face, defines=None, root=None):
    """register edges the bound u_xr adds on leaf face `face` (lo / p / e) over the unlanded ot_s81sl_xr input"""
    f = form(defines, root)
    if f['ring_edges'] != 0:
        raise ValueError(f'ring landing adds {f["ring_edges"]} edge(s) on every CTL / RD consequence: CFG_AT / '
                         'RX_WR_AFTER_PIN were measured with none; re-measure before compiling this form')
    return f['face_edges'][face]


if __name__ == '__main__':
    print(json.dumps(form(), indent=1))
