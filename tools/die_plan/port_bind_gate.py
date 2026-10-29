#!/usr/bin/env python3
"""Check exact top-level plan port bits before floorplan; missing/extra ports fail closed."""
import argparse
import json
from pathlib import Path
import re
import sys


def check(text, top, pins, straps=()):
    """straps: the kit's declared ID straps (OWNER 10-25 option B): each must be an INPUT port named strap_* of the
    top; their bits are plan pins like any other (no pin is waived here)."""
    # Yosys emits non-ANSI top declarations. Limit parsing to that module so cell
    # library declarations and child modules cannot mask missing top ports.
    body = re.search(r"(?ms)^\s*module\s+\\?" + re.escape(top) + r"\s*\(.*?;(?P<body>.*?)^\s*endmodule\b", text)
    if not body:
        return dict(verdict="FAIL", reason=f"top {top} missing")
    bits, inputs = set(), set()
    declarations = re.findall(r"^\s*(input|output|inout)\s+(?:(?:wire|reg|signed)\s+)*(\[\s*\d+\s*:\s*\d+\s*\]\s*)?([^;]+);", body['body'], re.M)
    for kind, width, names in declarations:
        for name in names.split(','):
            name = name.strip().lstrip('\\').strip()
            if kind == 'input':
                inputs.add(name)
            if width:
                hi, lo = map(int, re.findall(r'\d+', width))
                bits.update(f'{name}[{i}]' for i in range(min(hi, lo), max(hi, lo)+1))
            else:
                bits.add(name)
    expected = {p['bus'] if p.get('bit') is None else f"{p['bus']}[{p['bit']}]" for p in pins}
    # Scalar declarations and [0:0] declarations are equivalent in Yosys.
    for name in list(bits):
        if name not in expected and name + '[0]' in expected:
            bits.remove(name); bits.add(name + '[0]')
        elif name.endswith('[0]') and name not in expected and name[:-3] in expected:
            bits.remove(name); bits.add(name[:-3])
    missing, extra = sorted(expected-bits), sorted(bits-expected)
    bad_straps = sorted(x for x in (straps or ()) if not re.match(r'^strap_[A-Za-z0-9_]+$', str(x)) or x not in inputs)
    return dict(verdict='PASS' if not missing and not extra and not bad_straps else 'FAIL', top=top,
                straps=sorted(straps or ()), bad_straps=bad_straps,
                plan_bits=len(expected), netlist_bits=len(bits), missing=len(missing), extra=len(extra),
                missing_examples=missing[:16], extra_examples=extra[:16])


_INST = re.compile(r"^    ([A-Za-z_]\w*)\s*(?:#\s*\((?P<par>[^;]*?)\))?\s+([A-Za-z_]\w*)\s*\((?P<body>.*?)\);", re.S | re.M)
_DECL = re.compile(r"^\s*(?:\(\*[^*]*\*\)\s*)*(?:input|output|inout|wire)\s+(?:(?:wire|reg|logic|signed)\s+)*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?"
                   r"([A-Za-z_].*)$")
_KW = {"module", "input", "output", "inout", "wire", "reg", "assign", "always", "if", "else", "case", "endmodule",
       "localparam", "parameter", "genvar", "generate", "begin", "end", "for", "function", "task", "initial"}


def _module_params(text, module):
    """ANSI parameter defaults of `module` (integer / untyped): {name: expr string}."""
    m = re.search(r"\bmodule\s+" + re.escape(module) + r"\b\s*#\s*\(", text)
    if not m:
        return {}
    depth, k = 1, m.end()
    while depth:
        depth += {"(": 1, ")": -1}.get(text[k], 0)
        k += 1
    body = re.sub(r"//[^\n]*|/\*.*?\*/", "", text[m.end():k - 1], flags=re.S)
    out = {}
    for mm in re.finditer(r"(?:parameter|localparam)?\s*(?:integer|int|logic|bit)?\s*(?:\[[^\]]*\]\s*)?(\w+)\s*=\s*([^,]+)", body):
        out[mm.group(1)] = mm.group(2).strip()
    return out


def _clog2(v):
    v = int(v)
    return 0 if v <= 1 else (v - 1).bit_length()


def _eval(expr, env):
    """integer constant expression under env; $clog2 is supported (DIE-HEAD-29: strap_k [$clog2(DEPTH)+3:0] was
    UNRESOLVED on every ot_dp_clk_landing_cas).  Anything else raises (-> UNRESOLVED, closed)."""
    e = expr
    for _ in range(4):
        e2 = re.sub(r"(?<![$\w])([A-Za-z_]\w*)\b", lambda m: f"({env[m.group(1)]})" if m.group(1) in env else m.group(1), e)
        if e2 == e:
            break
        e = e2
    e = re.sub(r"(\d+)'[sS]?[dD](\d+)", r"\2", e)
    e = e.replace("$clog2", "C")
    if not re.fullmatch(r"[\dC\s+\-*/()%<>]*", e) or re.search(r"C(?!\s*\()", e):
        raise ValueError(expr)
    return int(eval(e.replace("/", "//"), {"__builtins__": {}}, {"C": _clog2}))


_DIRECTIVE = re.compile(r"^[ \t]*`(ifdef|ifndef|elsif|else|endif)\b[ \t]*(\w*)")


def preprocess(text, defines=("SYNTHESIS",)):
    """DIE-HEAD-29 (nested leaf-pin FAIL 136/67/452 on HEAD SOURCE7): resolve `ifdef/`ifndef/`elsif/`else/`endif the
    way synthesis reads the source (default: SYNTHESIS defined, nothing else, so the OT_MESO_CA_FV formal-only ports
    are absent).  Dropped lines are blanked (line count kept).  Unbalanced directives raise (closed)."""
    out, stack = [], []   # frames [branch_active, any_branch_taken]
    for ln in text.split("\n"):
        m = _DIRECTIVE.match(ln)
        if not m:
            out.append(ln if all(f[0] for f in stack) else "")
            continue
        k, name = m.group(1), m.group(2)
        if k in ("ifdef", "ifndef"):
            c = (name in defines) == (k == "ifdef")
            stack.append([c, c])
        elif not stack:
            raise ValueError(f"unbalanced `{k}")
        elif k == "elsif":
            f = stack[-1]
            c = not f[1] and name in defines
            f[0], f[1] = c, f[1] or c
        elif k == "else":
            f = stack[-1]
            f[0], f[1] = not f[1], True
        else:
            stack.pop()
        out.append("")
    if stack:
        raise ValueError("unbalanced `ifdef")
    return "\n".join(out)


_CONN = re.compile(r"\.(\w+)\s*\(")


def _conns(body):
    """{port: expr} of named connections .p(expr) with balanced parentheses (DIE-HEAD-29: .start_i(((a) & b)) was
    read as unbound by the old [^()]* form)."""
    out, i = {}, 0
    while True:
        m = _CONN.search(body, i)
        if not m:
            return out
        depth, k = 1, m.end()
        while k < len(body) and depth:
            depth += {"(": 1, ")": -1}.get(body[k], 0)
            k += 1
        if depth:
            raise ValueError(f"unbalanced connection .{m.group(1)}")
        out[m.group(1)] = body[m.end():k - 1].strip()
        i = k


def _balanced(e):
    d = 0
    for c in e:
        d += {"(": 1, "{": 1, "[": 1, ")": -1, "}": -1, "]": -1}.get(c, 0)
        if d < 0:
            return False
    return d == 0


def _split_top(e, seps):
    """split e at top-level (outside () {} []) single-char separators in seps; || and && are never split."""
    parts, depth, cur = [], 0, ""
    for i, c in enumerate(e):
        if c in "({[":
            depth += 1
        elif c in ")}]":
            depth -= 1
        if depth == 0 and c in seps and not (c in "|&" and (e[i + 1:i + 2] == c or e[i - 1:i] == c)):
            parts.append(cur)
            cur = ""
        else:
            cur += c
    parts.append(cur)
    return parts


def _width(rng, env):
    """'[A:B]' -> |A-B|+1 under env; '' -> 1"""
    if not rng:
        return 1
    a, b = rng.strip()[1:-1].split(":", 1)
    return abs(_eval(a, env) - _eval(b, env)) + 1


def _expr_width(expr, decl):
    """width of a connection expression.  DIE-HEAD-29 adds, on top of the atoms below: outer parentheses,
    concatenation {x, y, ...} (sum), unary ~ and bitwise | & ^ (max of the operands, the Verilog context width).
    Any operand it cannot size -> None (UNRESOLVED, closed); replication, arithmetic, logical, shift and ternary
    expressions stay None."""
    e = expr.strip()
    while e.startswith("(") and e.endswith(")") and _balanced(e[1:-1]):
        e = e[1:-1].strip()
    if e.startswith("{") and e.endswith("}") and _balanced(e[1:-1]):
        inner = e[1:-1].strip()
        if re.match(r"[^,{]*\{", inner):   # replication {N{x}}
            return None
        ws = [_expr_width(x, decl) for x in _split_top(inner, ",")]
        return None if any(w is None for w in ws) else sum(ws)
    ops = _split_top(e, "|&^")
    if len(ops) > 1:
        if any(not x.strip() for x in ops):   # reduction / xnor forms
            return None
        ws = [_expr_width(x, decl) for x in ops]
        return None if any(w is None for w in ws) else max(ws)
    if e.startswith("~") and e[1:2] not in "^&|":
        return _expr_width(e[1:], decl)
    return _expr_width_atom(e, decl)


def _expr_width_atom(e, decl):
    m = re.fullmatch(r"(\d+)\s*'\s*[bBdDhH][0-9a-fA-F_xXzZ]+", e)
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"([A-Za-z_]\w*)(?:\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\])?", e)
    if not m or m.group(1) not in decl:
        return None
    if m.group(2) is None:
        return decl[m.group(1)]
    return 1 if m.group(3) is None else abs(int(m.group(2)) - int(m.group(3))) + 1


def nested_check(wrapper_texts, source_texts, max_list=40, defines=("SYNTHESIS",)):
    """HEAD-BIND-4 10-27 (COORD ruling on HEAD-CORE-R13 ASK4 gap d): the die-top port-bind (tools/die_port_bind.py) checks
    the partition instances of the die top only; a generated wrapper whose LEAF instance leaves ports open (hd_serdes
    u_phy: only .rx/.tx bound, clk/rst/st/pma_* open, 514-b coll_o0_d into a 512-b rx) passed it silently.  This walks
    every instance INSIDE every wrapper module and checks it against its master's ANSI header (generated cells and the
    type sources): every master port connected to a non-empty expression, no port the master lacks, and the connected
    expression's width == the port width under the instance parameters.  A width it cannot resolve FAILs (closed).
    wrapper_texts: {name: text} of the generated wrappers; source_texts: [text] of every manifest source.
    -> dict(verdict, instances, unbound, unknown, width_mismatch, unresolved, examples)"""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent))
    import gen_rtl
    source_texts = [preprocess(t, defines) for t in source_texts]
    wrapper_texts = {k: preprocess(t, defines) for k, t in wrapper_texts.items()}
    lib = "\n".join(list(source_texts) + list(wrapper_texts.values()))
    hdr_cache, rec = {}, dict(instances=0, unbound=[], unknown=[], width_mismatch=[], unresolved=[], no_master=[])
    for wn, text in sorted(wrapper_texts.items()):
        for mm in re.finditer(r"(?ms)^module\s+(\w+)\s*\((?P<hdr>.*?)\);(?P<body>.*?)^endmodule\b", text):
            wmod, region = mm.group(1), mm.group("hdr") + "\n" + mm.group("body")
            decl = {}
            for ln in re.sub(r"/\*.*?\*/", "", region, flags=re.S).split("\n"):
                d = _DECL.match(ln.split("//")[0])
                if not d:
                    continue
                w = 1 if d.group(1) is None else abs(int(d.group(1)) - int(d.group(2))) + 1
                for nm in re.split(r"[;=]", d.group(3))[0].split(","):
                    if re.fullmatch(r"\s*[A-Za-z_]\w*\s*", nm):
                        decl[nm.strip()] = w
            for im in _INST.finditer(mm.group("body")):
                mst, inst = im.group(1), im.group(3)
                if mst in _KW:
                    continue
                rec["instances"] += 1
                where = f"{wmod}.{inst} ({mst})"
                if mst not in hdr_cache:
                    hdr_cache[mst] = (gen_rtl.parse_leaf_ports(lib, mst), _module_params(lib, mst))
                ports, pdef = hdr_cache[mst]
                if ports is None:
                    rec["no_master"].append(where)
                    continue
                env = dict(pdef)
                for pm in re.finditer(r"\.(\w+)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)", im.group("par") or ""):
                    env[pm.group(1)] = pm.group(2)
                conns = _conns(im.group("body"))
                for pn in sorted(ports):
                    if not conns.get(pn):
                        rec["unbound"].append(f"{where}.{pn}")
                for pn in sorted(set(conns) - set(ports)):
                    rec["unknown"].append(f"{where}.{pn}")
                for pn, ex in sorted(conns.items()):
                    if pn not in ports or not ex:
                        continue
                    try:
                        pw = _width(ports[pn][1], env)
                    except Exception:
                        pw = None
                    ew = _expr_width(ex, decl)
                    if pw is None or ew is None:
                        rec["unresolved"].append(f"{where}.{pn}({ex})")
                    elif pw != ew:
                        rec["width_mismatch"].append(f"{where}.{pn}: port {pw} b <- {ex} {ew} b")
    bad = {k: v for k, v in rec.items() if k != "instances" and v}
    return dict(verdict="PASS" if not bad and rec["instances"] else "FAIL", instances=rec["instances"],
                **{k: len(v) for k, v in rec.items() if k != "instances"},
                examples={k: v[:max_list] for k, v in bad.items()})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ['nested']:
        # port_bind_gate.py nested GEN_DIR -f FILELIST [--out JSON]: leaf-pin check inside every generated wrapper
        ap = argparse.ArgumentParser(prog='port_bind_gate.py nested')
        ap.add_argument('gen'); ap.add_argument('-f', required=True); ap.add_argument('--out')
        a = ap.parse_args(argv[1:])
        gen = Path(a.gen)
        # the die top (*_top.sv) is die_port_bind's scope (declared wavefront pads); this walks INSIDE the wrappers
        wr = {p.name: p.read_text() for p in sorted(gen.glob('*.sv')) if not p.name.endswith('_top.sv')}
        src = [Path(x).read_text(errors='replace') for x in Path(a.f).read_text().split()
               if x and not Path(x).resolve().parent == gen.resolve()]
        r = nested_check(wr, src)
        if a.out:
            Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
        print('PORT_BIND_NESTED', r['verdict'], json.dumps({k: v for k, v in r.items() if k != 'examples'}))
        for k, v in r.get('examples', {}).items():
            print(' ', k, v[:8])
        return 0 if r['verdict'] == 'PASS' else 1
    ap.add_argument('netlist'); ap.add_argument('kit'); a=ap.parse_args(argv)
    kit=Path(a.kit)
    try:
        budget=json.loads((kit/'budget.json').read_text())
        sj=kit/'straps.json'   # OWNER 10-25 option B: declared ID straps (strap_* inputs)
        sl=(lambda d: d.get('straps',[]) if isinstance(d,dict) else d)(json.loads(sj.read_text())) if sj.is_file() else []
        r=check(Path(a.netlist).read_text(), budget['module'], json.loads((kit/'port_bind_pins.json').read_text()), sl)
    except Exception as e:
        r=dict(verdict='FAIL', reason=f'port-bind checker error: {e}')
    (kit/'port_bind.json').write_text(json.dumps(r,indent=1)+'\n')
    print('PORT_BIND',r['verdict'],json.dumps(r,sort_keys=True))
    return 0 if r['verdict']=='PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main())
