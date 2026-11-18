"""FABLE-FIX-QC-N N4.1 11-18 (BIN-COPY): prove that an as-built leaf module is PURE WIRING and return its bit map.

A leaf such as qfd_dv_s8_frs (QC st_a: `assign rs_s_c = {rs_s[1027:1026], rs_s[513:512]};` ...) holds no logic: every
output bit is one input bit.  The binder keeps it as a leaf (its outputs are lane sources and core inputs), so a
partition in-boundary flop that feeds it drives, through the leaf's wires, every consumer of that output bit.  The
bin-copy form of the landing-pad tail split (bind_pad_tail_split.py, asbuilt.land_pad_tail_split.wire_leaves) gives each
far consumer core its own kept copy of that flop; bind.py and bind_verify.py both need the leaf's bit map, each from the
RTL source, so the proof never trusts the binder's own record.

    wire_map(text, module) -> {(out port, bit): (in port, bit)}

Fail closed (ValueError) unless the module body is ONLY `assign <output or output slice> = <input bits>;` statements over
ANSI-declared, constant-range ports: a parameter, a generate, an instance, an always block, a function, an operator or a
constant on the right-hand side, a bit driven twice or a width mismatch all raise.  Output bits left undriven are simply
absent from the map.
"""
import re

_ID = r"[A-Za-z_][A-Za-z0-9_$]*"
_RANGE = r"\[\s*(\d+)\s*:\s*(\d+)\s*\]"


def _strip(text):
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def module_text(text, module):
    """the header and body of `module`, comments stripped: (ports text, body text)"""
    t = _strip(text)
    m = re.search(rf"\bmodule\s+{re.escape(module)}\s*(#\s*\()?", t)
    if not m:
        raise ValueError(f"wire leaf {module}: module not found in the source")
    if m.group(1):
        raise ValueError(f"wire leaf {module}: parameterised module (not provably pure wiring)")
    rest = t[m.end():]
    if not rest.lstrip().startswith("("):
        raise ValueError(f"wire leaf {module}: no ANSI port list")
    a = rest.index("(")
    b = rest.find(")", a)
    semi = rest.find(";", b)
    end = re.search(r"\bendmodule\b", rest)
    if b < 0 or semi < 0 or not end or rest[b + 1:semi].strip():
        raise ValueError(f"wire leaf {module}: cannot read the port list")
    return rest[a + 1:b], rest[semi + 1:end.start()]


def ports(header, module):
    """{port: (direction, msb, lsb)} of an ANSI port list with constant ranges (a scalar is (dir, 0, 0))"""
    out, cur = {}, None
    for item in header.split(","):
        item = item.strip()
        if not item:
            raise ValueError(f"wire leaf {module}: empty port")
        m = re.fullmatch(rf"(input|output)\s+(?:wire\s+)?(?:{_RANGE}\s*)?({_ID})", item)
        if m:
            cur = (m.group(1), int(m.group(2) or 0), int(m.group(3) or 0))
            name = m.group(4)
        elif cur is not None and re.fullmatch(_ID, item):
            name = item
        else:
            raise ValueError(f"wire leaf {module}: port '{item[:60]}' is not a plain input / output wire")
        if cur[1] < cur[2] or name in out:
            raise ValueError(f"wire leaf {module}: port {name}: descending range expected, declared once")
        out[name] = cur
    return out


def _bits(expr, pt, want, module):
    """MSB-first [(port, bit)] of a `port`, `port[i]`, `port[h:l]` or `{..}` expression over `want` ports"""
    expr = expr.strip()
    if expr.startswith("{"):
        if not expr.endswith("}") or "{" in expr[1:]:
            raise ValueError(f"wire leaf {module}: nested / unbalanced concatenation '{expr[:60]}'")
        return [b for part in expr[1:-1].split(",") for b in _bits(part, pt, want, module)]
    m = re.fullmatch(rf"({_ID})\s*(?:\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\])?", expr)
    if not m or m.group(1) not in pt or pt[m.group(1)][0] != want:
        raise ValueError(f"wire leaf {module}: '{expr[:60]}' is not a plain {want} port reference")
    _d, hi, lo = pt[m.group(1)]
    if m.group(2) is not None:
        h = int(m.group(2))
        l = int(m.group(3)) if m.group(3) is not None else h
        if not lo <= l <= h <= hi:
            raise ValueError(f"wire leaf {module}: '{expr[:60]}' outside the port range [{hi}:{lo}]")
        hi, lo = h, l
    return [(m.group(1), i) for i in range(hi, lo - 1, -1)]


def wire_map(text, module):
    """{(out port, bit): (in port, bit)} of the pure-wiring module `module` in the RTL `text`; ValueError otherwise.
    Bit numbers are 0-based positions in the port (port[lsb] = 0), as the binder / bind_sinks.json count them."""
    header, body = module_text(text, module)
    pt = ports(header, module)
    out = {}
    for st in body.split(";"):
        st = st.strip()
        if not st:
            continue
        m = re.fullmatch(r"assign\s+(.+?)\s*=\s*(.+)", st, flags=re.S)
        if not m:
            raise ValueError(f"wire leaf {module}: statement '{st[:60]}' is not a plain assign (not pure wiring)")
        lhs = _bits(m.group(1), pt, "output", module)
        rhs = _bits(m.group(2), pt, "input", module)
        if len(lhs) != len(rhs):
            raise ValueError(f"wire leaf {module}: assign width {len(lhs)} != {len(rhs)}: '{st[:60]}'")
        for (op, ob), (ip, ib) in zip(lhs, rhs):
            k = (op, ob - pt[op][2])
            if k in out:
                raise ValueError(f"wire leaf {module}: {op}[{ob}] is driven twice")
            out[k] = (ip, ib - pt[ip][2])
    return out


def from_files(files, module):
    """wire_map of `module` from every one of `files` that defines it; ValueError when none does or two definitions
    give different maps (the elaborated one is then not known from the name alone)"""
    maps = []
    for f in files or []:
        try:
            text = open(f, errors="replace").read()
        except OSError:
            continue
        if re.search(rf"\bmodule\s+{re.escape(module)}\b", _strip(text)):
            maps.append(wire_map(text, module))
    if not maps:
        raise ValueError(f"wire leaf {module}: no RTL source defines it")
    if any(m != maps[0] for m in maps[1:]):
        raise ValueError(f"wire leaf {module}: {len(maps)} RTL definitions with different wiring")
    return maps[0]


def leaf_map(ab, base, module, index=None):
    """wire_map of as-built leaf module `module` from the as-built RTL closure (asbuilt rtl_roots / files / prefer under
    `base`); `index` = a bind_elab.module_index already built for the same manifest"""
    from pathlib import Path
    if index is None:
        import bind_elab as E
        index = E.module_index(ab.get("rtl_roots", ["rtl"]), ab.get("files", []), base)
    files = [str(f) for f in index.get(module, [])]
    for f in ab.get("prefer", []):
        f = f if Path(f).is_absolute() else str(Path(base) / f)
        if f not in files:
            files.append(f)
    return from_files(files, module)
