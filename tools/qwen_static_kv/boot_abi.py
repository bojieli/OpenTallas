#!/usr/bin/env python3
"""KV-TOK 10-26 (COORD RULING KV-TOK boot 12:32): the KV HOST boot image ABI, ONE source, and its build-time check.

The image length per boot target is defined ONCE, by the image builder (program_target_frames.encode_image: TARGET_WORDS,
TARGET_WORDS_MU for MU 1, target 10 = 96 for the die-cfg image with the 19 boot ages).  Two RTL tables must agree with it
on every bound die, for the die's actual parameters:

  * the die dispatcher   qkd_static_kv_boot_dispatch*  word_count(t)  (+ the MU wrapper's GAP block: target 1 seal at
                         word 470 -> 471 words when MU != 0)
  * the HOST loader      qkd_host_program_loader_target target_words(t)  (MU / AGES / NRST / DIECAP parameters, set at the
                         HOST instance by the native mission preparation from the dispatcher's own parameters)

B33 BOOT_FAULT@655 was exactly this mismatch (loader 327/77 vs dispatcher+image 471/96).  check() evaluates both RTL
functions from the bound source text (no hand-copied constant) and fails on any difference, for targets 1..13.

Host pacing (static host schedule, the host is the off-die elastic boundary; no die feedback):
  BEGIN(n+1) >= AUTH(n) + replay(n) + HOST_LINK_LAT_MAX,  replay(n) = pw(n) + dw(n) + REPLAY_FIXED
(spec: docs/QWEN_KV_HOST_BOOT_ABI.md).
"""
from __future__ import annotations
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location('ptf_boot_abi', HERE / 'program_target_frames.py')
ptf = importlib.util.module_from_spec(_s)
_s.loader.exec_module(ptf)

TARGETS = range(1, 14)
REPLAY_FIXED = 16            # loader fixed replay overhead after AUTH (program + descriptor words + 16 ck)
HOST_LINK_LAT_MAX = 160      # declared host -> loader one-way bound, core cycles (measured 122, B33 vehicle, CHECKED)


def image_words(mu: bool, ages: bool) -> dict[int, int]:
    """The ONE table: what the image builder emits (program word count per target)."""
    w = dict(ptf.TARGET_WORDS_MU if mu else ptf.TARGET_WORDS)
    if ages:
        w[10] = 96
    return {t: w.get(t, 0) for t in TARGETS}


def next_begin_min(auth_cycle: int, pw: int, dw: int, link_lat: int = HOST_LINK_LAT_MAX) -> int:
    """Earliest host send cycle for the next BEGIN after the image AUTHed at auth_cycle (static host schedule)."""
    return auth_cycle + pw + dw + REPLAY_FIXED + link_lat


# ---------------------------------------------------------------- tiny SV constant-expression evaluator
_TOK = re.compile(r"\s*(?:(\d+'[dD]\d+)|(\d+)'\(|(\d+)|([A-Za-z_]\w*)|(!=|==|\?|:|\+|-|\(|\)))")


def _tokens(s):
    out, i = [], 0
    s = s.strip()
    while i < len(s):
        m = _TOK.match(s, i)
        if not m or m.end() == i:
            raise ValueError(f'boot_abi: cannot parse SV expression at {s[i:i + 30]!r}')
        sized, cast, num, ident, op = m.groups()
        out.append(('n', int(sized.split("'")[1][1:])) if sized else ('cast', None) if cast else
                   ('n', int(num)) if num else ('id', ident) if ident else ('op', op))
        i = m.end()
    return out


def sv_eval(expr: str, params: dict) -> int:
    toks = _tokens(expr)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else ('end', None)

    def take(v=None):
        t = peek()
        if v is not None and t[1] != v:
            raise ValueError(f'boot_abi: expected {v!r}, got {t} in {expr!r}')
        pos[0] += 1
        return t

    def primary():
        k, v = take()
        if k == 'n':
            return v
        if k == 'id':
            if v not in params:
                raise ValueError(f'boot_abi: parameter {v} not bound in {expr!r}')
            return int(params[v])
        if k in ('cast',) or v == '(':       # N'( e )  or  ( e )
            r = ternary()
            take(')')
            return r
        raise ValueError(f'boot_abi: unexpected {v!r} in {expr!r}')

    def add():
        r = primary()
        while peek()[1] in ('+', '-'):
            op = take()[1]
            r = r + primary() if op == '+' else r - primary()
        return r

    def cmp():
        r = add()
        while peek()[1] in ('!=', '=='):
            op = take()[1]
            b = add()
            r = int(r != b) if op == '!=' else int(r == b)
        return r

    def ternary():
        c = cmp()
        if peek()[1] == '?':
            take('?')
            a = ternary()
            take(':')
            b = ternary()
            return a if c else b
        return c

    r = ternary()
    if pos[0] != len(toks):
        raise ValueError(f'boot_abi: trailing tokens in {expr!r}')
    return r


def module_text(text: str, name: str) -> str:
    hits = [m.start() for m in re.finditer(rf'\bmodule\s+{re.escape(name)}\b', text)]
    if len(hits) != 1:
        raise ValueError(f'boot_abi: expected one module {name}, found {len(hits)}')
    i = hits[0]
    return text[i:text.index('endmodule', i)]


def module_defaults(mod: str) -> dict:
    head = mod[:mod.index(')(')] if ')(' in mod else mod[:mod.index(';')]
    return {k: int(v) for k, v in re.findall(r'(?:parameter\s+(?:integer\s+)?|,\s*)(\w+)\s*=\s*(\d+)\b', head)}


def case_table(mod: str, func: str, params: dict) -> dict[int, int]:
    """Evaluate `function automatic [..] func(input [3:0] t); case(t) ... endcase` for targets 1..13."""
    m = re.search(rf'function\s+automatic\s*\[[^\]]*\]\s*{func}\s*\(.*?\);\s*case\s*\(\s*t\s*\)(.*?)endcase', mod, re.S)
    if not m:
        raise ValueError(f'boot_abi: no case function {func}')
    body = re.sub(r'//[^\n]*', '', m.group(1))
    table, default = {}, None
    for item in re.finditer(rf'([\d,\s]+|default)\s*:\s*{func}\s*=\s*(.*?);', body, re.S):
        v = sv_eval(item.group(2), params)
        if item.group(1).strip() == 'default':
            default = v
        else:
            for t in item.group(1).split(','):
                table[int(t)] = v
    return {t: table.get(t, default if default is not None else 0) for t in TARGETS}


def inst_params(text: str, module_rx: str, inst: str) -> tuple[str, dict]:
    hits = list(re.finditer(rf'\b({module_rx})\s*#\s*\((.*?)\)\s*{re.escape(inst)}\s*\(', text, re.S))
    if len(hits) != 1:
        raise ValueError(f'boot_abi: expected one {module_rx} {inst}, found {len(hits)}')
    return hits[0].group(1), {k: int(v) for k, v in re.findall(r'\.(\w+)\s*\(\s*(\d+)\s*\)', hits[0].group(2))}


def dispatcher_table(ctl_text: str, face_text: str) -> tuple[dict, dict[int, int]]:
    """The native dispatcher instance u_boot in the KV control (actual parameters) -> its effective word count table."""
    mod, p = inst_params(ctl_text, r'qkd_static_kv_boot_dispatch_mu_\w+', 'u_boot')
    wrap = module_text(face_text, mod)
    eff = {**module_defaults(wrap), **p}
    inner = sorted({n for n in re.findall(r'\b(qkd_static_kv_boot_dispatch\w*)\s*#\s*\(', wrap) if n != mod})
    if len(inner) != 1:
        raise ValueError(f'boot_abi: {mod} must wrap one dispatcher, found {inner}')
    inner = inner[0]
    tbl = case_table(module_text(face_text, inner), 'word_count', {**module_defaults(module_text(face_text, inner)), **eff})
    if eff.get('MU', 0):
        seal = re.findall(r"seal_w\s*=\s*w1\s*&&\s*addr\s*==\s*10'd(\d+)", wrap)
        if len(seal) != 1:
            raise ValueError('boot_abi: MU dispatcher seal address not found')
        tbl[1] = int(seal[0]) + 1
    return eff, tbl


def loader_table(loader_text: str, params: dict) -> dict[int, int]:
    mod = module_text(loader_text, 'qkd_host_program_loader_target')
    return case_table(mod, 'target_words', {**module_defaults(mod), **params})


def check(dispatcher: dict[int, int], loader: dict[int, int], image: dict[int, int]) -> list[str]:
    """Every target the die dispatcher accepts must have the same length in the loader and the image builder."""
    errs = []
    for t in TARGETS:
        if dispatcher[t] == 0:
            continue                                           # target not built on this die
        if not (dispatcher[t] == loader[t] == image[t]):
            errs.append(f'target {t}: dispatcher {dispatcher[t]} loader {loader[t]} image {image[t]}')
    return errs
