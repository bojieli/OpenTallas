#!/usr/bin/env python3
"""Fail before synthesis on implicit nets, unresolved hierarchy or undriven RTL, and on source forms the flow's
yosys frontend mis-elaborates silently (YC1 / YC2 below; YOSYS-CONCAT 10-26).
Runs inside the kit container, using one blackbox liberty view per macro.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path


def config(kit):
    values = {}
    text = (kit / 'config.mk').read_text().replace('\\\n', ' ')
    for key, value in re.findall(r'^[ \t]*(?:override[ \t]+)?export[ \t]+(\w+)[ \t]*[:?]?=[ \t]*(.*?)[ \t]*$', text, re.M):
        values[key] = value.split()
    return values


def script(kit, mount='/work'):
    cfg = config(kit)
    top = cfg.get('DESIGN_NAME', [])
    sources = cfg.get('VERILOG_FILES', [])
    if len(top) != 1 or not sources:
        raise ValueError('config needs one DESIGN_NAME and nonempty VERILOG_FILES')
    params = cfg.get('VERILOG_TOP_PARAMS', [])
    if len(params) % 2:
        raise ValueError('VERILOG_TOP_PARAMS needs name/value pairs')
    if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', name) for name in params[::2]):
        raise ValueError('VERILOG_TOP_PARAMS contains an invalid parameter name')
    parameter_args = ''.join(f' -set {name} {value}' for name, value in zip(params[::2], params[1::2]))
    # Standalone chparam derives/replaces the top once. hierarchy -chparam can
    # re-add a deferred module under its existing name (Yosys rtlil.cc assertion).
    parameter_commands = [f'chparam{parameter_args} {top[0]}'] if params else []
    libs, seen = [], set()
    for p in sorted((kit / 'macros').glob('*.lib*'), key=lambda p: ('_tt.lib' not in p.name, p.name)):
        key = re.sub(r'_(tt|ff|ss)\.lib(?:\.gz)?$|\.lib(?:\.gz)?$', '', p.name)
        if key not in seen:
            seen.add(key)
            libs.append(f'read_liberty -lib -ignore_miss_func {mount}/macros/{p.name}')
    # S81-CORE-LAT/QB 10-26: RTL that instantiates a platform cell by name (ot_hdc_cg -> ICGx1_ASAP7_75t_R) failed
    # hierarchy -check (missing module): read the platform SEQ liberty as interface-only cells (-lib), like the macros.
    import glob as _glob
    for _p in sorted(_glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_*.lib*'))[:1]:
        libs.append(f'read_liberty -lib -ignore_miss_func {_p}')
    # KV-CORES-PV2 10-27: 12.2a1 island ft cells are RTL instances of the platform BUF (BUFx24_ASAP7_75t_R) -> INVBUF too
    for _p in sorted(_glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_*.lib*'))[:1]:
        libs.append(f'read_liberty -lib -ignore_miss_func {_p}')
    # QC-A0-KITS 10-27: a mapped-netlist source (a split child carried as its yosys netlist, e.g. rawleaf TIEHIx1)
    # instantiates any platform cell: read EVERY ASAP7 RVT TT liberty as interface-only cells, and fail closed when a
    # mapped source names a cell no such liberty defines (hierarchy -check also rejects it).
    if mapped_cells(_kit_sources(kit)):
        for _p in platform_libs():
            line = f'read_liberty -lib -ignore_miss_func {_p}'
            if line not in libs:
                libs.append(line)
    defines = ['-DSYNTHESIS'] + [v if v.startswith('-D') else '-D'+v for v in cfg.get('VERILOG_DEFINES', [])]
    includes = ['-I'+v for v in cfg.get('VERILOG_INCLUDE_DIRS', []) + cfg.get('SYNTH_INCLUDE_DIRS', [])]
    return '\n'.join(libs + ['verilog_defines ' + ' '.join(dict.fromkeys(defines))] +
                     # -defer as ORFS synth: modules elaborate once, with the parameters they are instantiated
                     # with (FLOW-CANARY 10-25: without it 'initial if(P<1) $fatal' guards fired on the default
                     # parameters -- qkd_static_k_issuer RESPONSE_LAT=0 -- and failed every KV head kit's lint);
                     # -noautowire still rejects implicit nets under -defer (checked on the orfs:asap7lock yosys).
                     # Native headers preserve content-only ROM parameters omitted by Liberty.
                     [('read_verilog -lib -overwrite -sv -noautowire '
                       if re.search(r'_bb\.(?:v|sv)$', s) else
                       'read_verilog -defer -sv -noautowire ') +
                      ' '.join(includes + [s]) for s in sources] +
                     # Optional actual-top liveness for macro-composed parents: hierarchy-local dead outputs can
                     # retain undriven cones whose consumers disappear only across module boundaries. Flatten
                     # before pruning preserves every LIVE undriven top connection for check -assert.
                     parameter_commands + [f'hierarchy -check -top {top[0]}', 'proc'] +
                     (['flatten', 'opt_expr -keepdc'] if cfg.get('OT_RTL_LINT_FLATTEN') == ['1'] else []) + [
                                           # Check the elaborated live design. Dead parameter-disabled cones can
                                           # retain unassigned legacy wires after proc (safe4 PIPE=2); live
                                           # undriven nets still survive opt_clean and fail check -assert.
                                           'opt_clean', 'check -assert']) + '\n'


# ---- YOSYS-CONCAT 10-26: reject source forms that the flow's yosys read_verilog -sv (0.68+post, orfs:asap7lock)
# mis-elaborates SILENTLY (characterised against read_slang in the same binary, 520 probes, 0 silent misses):
#  YC1  a concatenation / replication member that is an operator expression (binary op, ?:) containing a
#       non-constant size or type cast N'(e) with |e| > N is sized at the UNCAST width: every more significant
#       member shifts up by |e|-N bits (usually off the top).  {3'b010,5'd0,({1'(s/2),..}^3'(..))} -> {8'h00,..}
#       (QC-LEC-4 N59 bout_x3.q[521]).  A bare cast member {K,2'(x)}, a bare nested concat {K,{1'(a),1'(b)}} and a
#       cast of a constant (literal / parameter / genvar expression) elaborate correctly.
#  YC2  a unary prefix operator directly before a size cast: |2'(x) parses as (|2)'(x) = 1'(x); ^ likewise
#       (silent); ~ - & ! give a negative / zero size (loud).  Parenthesise: |(2'(x)).
# Both are rejected without width inference (a widening cast in YC1 position is rejected too): fix = give the cast
# its own named sized wire (or parenthesise it for YC2), then concatenate.
_YC_KEEP_SIGN = {'signed', 'unsigned', 'const', 'type'}
_YC_KEYWORDS = {'assign', 'return', 'else', 'begin', 'if', 'case', 'default', 'or', 'and', 'not'}
_YC_CAST = re.compile(r"(\d+|[A-Za-z_][A-Za-z0-9_$]*|\)|\])\s*'\s*\(")
_YC_SIZED = re.compile(r"\d*\s*'\s*[sS]?[bBoOdDhH]\s*[0-9a-fA-FxXzZ_?]+|'[01xXzZ]\b|\b\d+(?:\.\d+)?\b")
_YC_NOISE = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\\n])*"', re.S)


def _yc_strip(text):
    """comments and strings -> blanks, newlines kept (offsets and line numbers survive)"""
    return _YC_NOISE.sub(lambda m: re.sub(r'[^\n]', ' ', m.group(0)), text)


def _yc_match(t):
    """{open index: close index} of balanced ( [ { brackets"""
    pairs, stack, match = {')': '(', ']': '[', '}': '{'}, [], {}
    for m in re.finditer(r'[()\[\]{}]', t):
        c, i = m.group(0), m.start()
        if c in '([{':
            stack.append((c, i))
        elif stack and stack[-1][0] == pairs[c]:
            match[stack.pop()[1]] = i
        else:
            stack = []          # unbalanced: forget the open groups
    return match


def _yc_casts(t, match):
    """sorted [(cast start, '(' index, ')' index)] of size / type casts"""
    out = []
    for m in _YC_CAST.finditer(t):
        if m.group(1) in _YC_KEEP_SIGN:
            continue
        p = m.end() - 1
        if p not in match:
            continue
        start = m.start(1)
        if m.group(1) in ')]':       # (W+1)'(x) / logic [3:0]'(x): the size is the bracket group before
            opener = next((o for o in (start - 1 - k for k in range(0, 4096)) if o >= 0 and match.get(o) == start), None)
            start = start if opener is None else opener
        out.append((start, p, match[p]))
    return out


def _yc_constant(t, p, q, consts):
    names = re.findall(r'[A-Za-z_$][A-Za-z0-9_$]*', _YC_SIZED.sub(' ', t[p + 1:q]))
    return all(n in consts or n in ('$clog2', '$bits') for n in names)


def _yc_bare(t, match, a, b):
    """member t[a:b] without surrounding whitespace / parentheses"""
    while True:
        while a < b and t[a].isspace():
            a += 1
        while b > a and t[b - 1].isspace():
            b -= 1
        if a < b and t[a] == '(' and match.get(a) == b - 1:
            a, b = a + 1, b - 1
            continue
        return a, b


def _yc_split(t, match, a, b):
    """top-level comma split of t[a:b] -> [(start, end)]"""
    parts, s, j = [], a, a
    while j < b:
        if t[j] in '([{' and j in match:
            j = match[j] + 1
            continue
        if t[j] == ',':
            parts.append((s, j)); s = j + 1
        j += 1
    parts.append((s, b))
    return parts


_YC_REL = re.compile(r'&&|\|\||===|!==|==|!=|<=|>=|(?<![<>])[<>](?![<>=])')


def _yc_top(t, match, a, b):
    """t[a:b] with every bracket group blanked (top level only)"""
    out, j = [], a
    while j < b:
        if t[j] in '([{' and j in match and match[j] < b:
            out.append(t[j] + ' ' * (match[j] - j - 1) + t[match[j]]); j = match[j] + 1
        else:
            out.append(t[j]); j += 1
    return ''.join(out)


def _yc_risky(t, match, casts, starts, consts, a, b, bare_ok=True):
    """True when member t[a:b] may be mis-sized by YC1: an operator expression holding a variable cast whose width
    reaches the member width.  Exempt (proven correct by probe): a bare cast, a bare nested concat, a cast of a
    constant, a cast inside an index [..] or a call argument f(..), the condition of ?:, and any member whose top
    level is a relational / equality / logical operator (1-bit self-determined result)."""
    import bisect
    a, b = _yc_bare(t, match, a, b)
    if a >= b or (bare_ok and t[a] == '{' and match.get(a) == b - 1):
        return False
    top = _yc_top(t, match, a, b)
    q = top.find('?')
    if q >= 0:                                  # cond ? x : y -> only the branches size the member
        depth, k = 0, q + 1
        while k < len(top):
            if top[k] == '?':
                depth += 1
            elif top[k] == ':':
                if depth == 0:
                    break
                depth -= 1
            k += 1
        return (_yc_risky(t, match, casts, starts, consts, a + q + 1, a + k, False) or     # a ?: branch is
                _yc_risky(t, match, casts, starts, consts, a + k + 1, b, False))           # context-sized
    if _YC_REL.search(top):
        return False
    masked = []
    for j in range(a, b):                       # index groups and call arguments
        if t[j] in '[(' and j in match:
            if t[j] == '[' or re.search(r"[A-Za-z_$][\w$]*\s*$", t[max(a, j - 64):j]) and \
                    not re.search(r"\b(?:signed|unsigned)\s*$", t[max(a, j - 16):j]):
                masked.append((j, match[j]))
    inner = [c for c in casts[bisect.bisect_left(starts, a):bisect.bisect_left(starts, b)]
             if not _yc_constant(t, c[1], c[2], consts) and not any(x < c[0] and c[2] <= y for x, y in masked)]
    if not inner or bare_ok and any(c[0] == a and c[2] == b - 1 for c in casts[bisect.bisect_left(starts, a):
                                                                              bisect.bisect_left(starts, a + 1)]):
        return False                            # no variable cast / the member is one bare cast (self-sized)
    if not bare_ok:
        return True
    r = re.match(r'[^{]*\{', t[a:b])            # replication count{inner}: inner scanned on its own
    if r and match.get(a + r.end() - 1) == b - 1 and not any(c[0] < a + r.end() - 1 for c in inner):
        return False
    return True


def yosys_cast_hits(text):
    """sorted [(line, rule, snippet)] of YC1 / YC2 forms in SystemVerilog source text"""
    if not re.search(r"'\s*\(", text):
        return []
    import bisect
    t = _yc_strip(text)
    match = _yc_match(t)
    casts = _yc_casts(t, match)
    if not casts:
        return []
    starts = [c[0] for c in casts]
    consts = set()
    for decl in re.finditer(r'\b(?:parameter|localparam)\b([^;]*)', t):     # parameter [W:0] A=1, B=2
        consts.update(re.findall(r'([A-Za-z_]\w*)\s*(?:\[[^\]]*\]\s*)*=(?!=)', decl.group(1)))
    consts.update(re.findall(r'\bgenvar\s+([A-Za-z_]\w*)', t))
    nl = [m.start() for m in re.finditer('\n', t)]
    line = lambda i: bisect.bisect_left(nl, i) + 1
    snip = lambda a, b: ' '.join(text[a:b].split())[:160]
    hits = set()
    for (s, p, q) in casts:                                  # YC2: unary prefix operator before a cast
        k = s - 1
        while k >= 0 and (t[k].isspace() or t[k] in '|&^~-!'):
            k -= 1
        toks = re.findall(r'\|\||&&|~\^|\^~|~&|~\||[|&^~!-]', t[k + 1:s])
        if not toks:
            continue
        w = re.search(r'([A-Za-z_][A-Za-z0-9_$]*)\s*$', t[max(0, k - 40):k + 1])
        operand = k >= 0 and (t[k].isalnum() or t[k] in "_)]}$'") and not (w and w.group(1) in _YC_KEYWORDS)
        if operand and toks[0] in ('||', '&&', '~^', '^~', '|', '&', '^', '-'):
            toks = toks[1:]                                  # binary: a | 2'(x), a - 2'(x) parse correctly
        if toks:
            hits.add((line(s), 'YC2', snip(k + 1, q + 1)))
    for i, j in match.items():                               # YC1: concat / replication members
        if t[i] != '{':
            continue
        k = i - 1
        while k >= 0 and t[k].isspace():
            k -= 1
        if k >= 0 and t[k] == "'":
            continue                                         # assignment pattern '{..}
        lo, hi = bisect.bisect_left(starts, i), bisect.bisect_left(starts, j)
        if lo == hi or ';' in t[i + 1:j]:
            continue                                         # no cast inside / block-like braces (struct body)
        for a, b in _yc_split(t, match, i + 1, j):
            a, b = _yc_bare(t, match, a, b)
            if a >= b or (t[a] == '{' and match.get(a) == b - 1):
                continue                                     # empty / bare nested concat (scanned on its own)
            if not _yc_risky(t, match, casts, starts, consts, a, b):
                continue
            hits.add((line(a), 'YC1', snip(a, b)))
    return sorted(hits)


def yosys_cast_scan(paths):
    """{path: [(line, rule, snippet)]} over the existing SystemVerilog / Verilog sources"""
    out = {}
    for s in paths:
        p = Path(s)
        if p.suffix in ('.sv', '.v', '.svh', '.vh') and p.is_file():
            h = yosys_cast_hits(p.read_text(errors='replace'))
            if h:
                out[str(p)] = h
    return out


def _kit_sources(kit):
    """VERILOG_FILES as readable paths (container /work/... resolved against the kit when run outside it)"""
    out = []
    for s in config(kit).get('VERILOG_FILES', []):
        p = Path(s)
        if not p.is_file() and s.startswith('/work/'):
            p = kit / s[len('/work/'):]
        out.append(p)
    return out


PLATFORM_LIB_GLOB = '/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*'
_CELL_INST = re.compile(r'^[ \t]*([A-Za-z_][A-Za-z0-9_]*_ASAP7_75t_[A-Za-z0-9_]+)[ \t]+[\\A-Za-z_]', re.M)


def platform_libs(pattern=None):
    import glob as _glob
    return sorted(_glob.glob(pattern or PLATFORM_LIB_GLOB))


def mapped_cells(paths):
    """{cell type: count} of ASAP7 platform cells instantiated in the readable sources (empty -> RTL only)"""
    out = {}
    for p in paths:
        p = Path(p)
        if p.suffix in ('.v', '.sv') and p.is_file():
            for c in _CELL_INST.findall(p.read_text(errors='replace')):
                out[c] = out.get(c, 0) + 1
    return out


def liberty_cells(paths):
    import gzip
    cells = set()
    for p in paths:
        p = str(p)
        text = (gzip.open(p, 'rt', errors='replace') if p.endswith('.gz') else open(p, errors='replace')).read()
        cells.update(re.findall(r'\bcell\s*\(\s*"?([A-Za-z_][A-Za-z0-9_]*)"?\s*\)', text))
    return cells


def mapped_cell_errors(kit, pattern=None):
    """fail-closed check: every platform cell a mapped source instantiates is defined by an RVT TT liberty"""
    used = mapped_cells(_kit_sources(kit))
    if not used:
        return []
    libs = platform_libs(pattern)
    if not libs:
        return [f'ERROR: mapped-netlist source but no ASAP7 RVT TT liberty matches {pattern or PLATFORM_LIB_GLOB}']
    known = liberty_cells(libs)
    return [f'ERROR: mapped-netlist cell {c} ({n} instances) is not defined by any ASAP7 RVT TT liberty'
            for c, n in sorted(used.items()) if c not in known]


def run(kit, yosys='yosys'):
    out = kit / 'rtl_lint.json'
    try:
        ys = kit / 'rtl_lint.ys'
        ys.write_text(script(kit))
        result = subprocess.run([yosys, '-q', '-s', str(ys)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        log = result.stdout
        (kit / 'rtl_lint.log').write_text(log)
        cast = yosys_cast_scan(_kit_sources(kit))
        cast_errors = [f'{p}:{ln}: ERROR: {rule} yosys read_verilog -sv mis-elaborates this cast form '
                       f'(put the cast in its own named sized wire): {sn}' for p, hs in sorted(cast.items()) for ln, rule, sn in hs]
        cell_errors = mapped_cell_errors(kit)
        cast_errors = cell_errors + cast_errors
        record = dict(verdict='PASS' if result.returncode == 0 and not cast_errors else 'FAIL', rc=result.returncode,
                      mapped_cell_types=len(mapped_cells(_kit_sources(kit))),
                      top_params=config(kit).get('VERILOG_TOP_PARAMS', []),
                      errors=re.findall(r'^.*\bERROR:.*$', log, re.M) + cast_errors, yosys_cast=len(cast_errors),
                      command=[yosys, '-q', '-s', str(ys)])
    except (OSError, ValueError) as error:
        record = dict(verdict='NOT RUN', rc=2, errors=[str(error)])
    out.write_text(json.dumps(record, indent=1) + '\n')
    print('RTL_LINT', record['verdict'], 'errors', len(record['errors']))
    return 0 if record['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kit', type=Path, nargs='?')
    parser.add_argument('--yosys', default='yosys')
    parser.add_argument('--scan', nargs='+', metavar='SRC', help='only report YC1/YC2 cast forms in these sources')
    args = parser.parse_args()
    if args.scan:
        hits = yosys_cast_scan(args.scan)
        for p, hs in sorted(hits.items()):
            for ln, rule, sn in hs:
                print(f'{p}:{ln}\t{rule}\t{sn}')
        raise SystemExit(1 if hits else 0)
    raise SystemExit(run(args.kit.resolve(), args.yosys))
