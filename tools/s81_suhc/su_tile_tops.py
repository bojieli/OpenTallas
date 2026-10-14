#!/usr/bin/env python3
"""The S81 SU slab with the ROUTED tile tops (gate s81su_tiles).

dsfd_sp_su_h instantiates the engine cores ot_s81_su_<x> #(slab parameters); what is routed is the wrapper
dsfd_su_t_<x> (fixed parameters).  This tool rewrites the slab text so that every core instance that has a routed
wrapper becomes that wrapper, and nothing else changes:

  * the wrapper is chosen at ELABORATION by a generate-if on parameter equality (slab expression == wrapper value;
    a parameter only the slab passes, e.g. MUT / STALEDEN, must equal the core default); an instance with no
    matching wrapper prints SU_TILE_TOPS_NOMATCH with its parameter values and stops the simulation;
  * every connected port is checked for width ($bits(slab expression) == wrapper port width): the gate compiles with
    -Wno-WIDTH, so a silent truncation would otherwise go unseen;
  * one mutant per wrapper class: +tmut=K inverts significant bits of the widest output of every instance of class K
    (the table is printed by `--list` and stored in the manifest), so a tile whose output the cases do not observe
    is found by a mutant that still passes.

    python3 tools/s81_suhc/su_tile_tops.py --out DIR      # DIR/dsfd_sp_su_h_tt.sv + DIR/tile_tops.json
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HD = "rtl/dsrom_sys/s81_suhc/hier/"
SLAB = HD + "dsfd_sp_su_h.sv"
WRAP = [HD + f for f in ("dsfd_su_t_qn.sv", "dsfd_su_t_kv.sv", "dsfd_su_t_qb.sv", "dsfd_su_t_sw.sv", "dsfd_su_t_sm.sv",
                         "dsfd_su_tiles.sv")]
CORES = [HD + f for f in ("ot_s81_su_qn.sv", "ot_s81_su_kv.sv", "ot_s81_su_qb.sv", "ot_s81_su_sw.sv", "ot_s81_su_sm.sv",
                          "ot_s81_su_ctl.sv", "ot_s81_su_hctl.sv", "ot_s81_su_tile.sv", "ot_s81_su_norm_lg.sv")]


def strip_comments(s):
    s = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), s, flags=re.S)
    return re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), s)


def close_paren(s, i):
    """index just past the parenthesis that closes s[i] == '('"""
    assert s[i] == "(", s[i:i + 20]
    d = 0
    for k in range(i, len(s)):
        if s[k] == "(":
            d += 1
        elif s[k] == ")":
            d -= 1
            if d == 0:
                return k + 1
    raise ValueError("unbalanced")


def named_list(s):
    """'.a(x), .b(y[1]), .c()' -> {a: 'x', b: 'y[1]', c: ''}"""
    out, i = {}, 0
    while True:
        m = re.compile(r"\.(\w+)\s*\(").search(s, i)
        if not m:
            return out
        e = close_paren(s, m.end() - 1)
        out[m.group(1)] = " ".join(s[m.end():e - 1].split())
        i = e


INST = re.compile(r"\b(ot_s81_su_\w+)\s*(#\s*\()?")


def instances(text):
    """(start, end, core, params, inst name, ports) of every ot_s81_su_* instance in comment-stripped text"""
    i = 0
    while True:
        m = INST.search(text, i)
        if not m:
            return
        j, par = m.end(), {}
        if m.group(2):
            e = close_paren(text, m.end() - 1)
            par = named_list(text[m.end():e - 1])
            j = e
        n = re.compile(r"\s*(\w+)\s*\(").match(text, j)
        if not n:                       # the module's own declaration, a comment remnant, ...
            i = m.end()
            continue
        e = close_paren(text, n.end() - 1)
        semi = re.compile(r"\s*;").match(text, e)
        if not semi:
            i = m.end()
            continue
        yield m.start(), semi.end(), m.group(1), par, n.group(1), named_list(text[n.end():e - 1])
        i = semi.end()


def header_params(hdr):
    """'parameter integer N = 256, S_RD = 16, parameter [3:0] K = f(1, 2)' -> {N: '256', S_RD: '16', K: 'f(1, 2)'}"""
    out, d, cur, items = {}, 0, "", []
    for ch in hdr:
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
        if ch == "," and d == 0:
            items.append(cur)
            cur = ""
        else:
            cur += ch
    items.append(cur)
    for it in items:
        if "=" not in it:
            continue
        lhs, rhs = it.split("=", 1)
        lhs = re.sub(r"\[[^\]]*\]", " ", lhs).split()
        out[lhs[-1]] = " ".join(rhs.split())
    return out


def modules(path):
    """name -> (param defaults, port text, body) of each module in a file"""
    s = strip_comments((ROOT / path).read_text())
    out = {}
    for m in re.finditer(r"\bmodule\s+(\w+)\s*", s):
        j, par = m.end(), {}
        if s[j] == "#":
            k = s.index("(", j)
            e = close_paren(s, k)
            par = header_params(s[k + 1:e - 1])
            j = e + len(re.match(r"\s*", s[e:]).group(0))
        e = close_paren(s, j)
        out[m.group(1)] = (par, s[j + 1:e - 1], s[e:s.index("endmodule", e)])
    return out


def port_widths(ptxt):
    """wrapper port name -> (direction, msb expression or None)"""
    out, d, w = {}, None, None
    for item in ptxt.split(","):
        t = item.split()
        if not t:
            continue
        if t[0] in ("input", "output", "inout"):
            d, w = t[0], None
            t = t[1:]
            while t and t[0] in ("wire", "logic", "reg"):
                t = t[1:]
            rest = " ".join(t)
            m = re.match(r"\[(.+):\s*0\s*\]\s*(\w+)$", rest)
            if m:
                w, name = m.group(1).strip(), m.group(2)
            else:
                name = rest
        else:
            name = " ".join(t)
        assert re.fullmatch(r"\w+", name), (item, name)
        out[name] = (d, w)
    return out


def wrappers():
    """core -> [wrapper dicts]"""
    by = {}
    for f in WRAP:
        for name, (wpar, ptxt, body) in modules(f).items():
            if not name.startswith("dsfd_su_t_"):
                continue
            ins = list(instances(body))
            assert len(ins) == 1, (name, [x[2] for x in ins])
            _, _, core, par, _, ports = ins[0]
            par = {k: wpar.get(v, v) for k, v in par.items()}          # a wrapper parameter passed through: its default
            pw = port_widths(ptxt)
            cat, tied = {}, {}
            for cp, wp in ports.items():
                if wp in pw:
                    continue
                m = re.fullmatch(r"\{\s*(\w+(?:\s*,\s*\w+)*)\s*\}", wp)
                if m and all(x.strip() in pw for x in m.group(1).split(",")):
                    cat[cp] = [x.strip() for x in m.group(1).split(",")]      # a core port split over wrapper pins (msb first)
                else:
                    assert re.fullmatch(r"\d*'[bdh][0-9a-fA-F_]+", wp), f"{name}: core port {cp} tied to {wp!r}"
                    tied[cp] = wp                                             # a core input the wrapper ties to a constant
            by.setdefault(core, []).append(dict(name=name, file=f, core=core, params=par, tied=tied, cat=cat, pins=pw,
                                                core2pin={cp: wp for cp, wp in ports.items() if cp not in tied and cp not in cat}))
    return by


def core_defaults():
    d = {}
    for f in CORES:
        for name, (par, _, _) in modules(f).items():
            d[name] = par
    return d


def mask(msb):
    """bits to invert in a [msb:0] output: exponent-range bits of the low lanes, or bit 0 of a narrow one"""
    return (f"(({msb}) >= 30 ? (({msb}) + 1)'(64'h4000_4000) : ({msb}) >= 14 ? (({msb}) + 1)'(64'h4000) : (({msb}) + 1)'(1))")


def build():
    wr, cdef = wrappers(), core_defaults()
    classes = sorted({w["name"] for ws in wr.values() for w in ws})
    tm = {n: i + 1 for i, n in enumerate(classes)}
    raw = (ROOT / SLAB).read_text()
    txt = strip_comments(raw)
    out, pos, n, man = [], 0, 0, dict(tmut=tm, instances=[], unwrapped=[])
    for s, e, core, par, iname, ports in instances(txt):
        if core not in wr:      # no routed top wraps this core: say so if the shape elaborates it
            man["unwrapped"].append(dict(core=core, inst=iname, line=txt.count("\n", 0, s) + 1))
            out.append(raw[pos:s])
            out.append(f'initial $display("SU_TILE_TOPS_UNWRAPPED {core} {iname} %m");\n')
            pos = s
            continue
        n += 1
        line = txt.count("\n", 0, s) + 1
        g = [f"/* SU_TILE_TOPS: {core} {iname} (slab line {line}) */"]
        dflt = cdef.get(core, {})
        for k, w in enumerate(wr[core]):
            cond = []
            for p, sv in par.items():
                if p in w["params"]:
                    cond.append(f"(({sv}) == ({w['params'][p]}))")
                else:
                    assert p in dflt, f"{core}.{p}: no default found"
                    cond.append(f"(({sv}) == ({dflt[p]}))")
            for p, wv in w["params"].items():              # set by the wrapper only: the slab runs the core default
                if p not in par:
                    assert p in dflt, f"{core}.{p}: no default found"
                    cond.append(f"(({dflt[p]}) == ({wv}))")
            missing = [cp for cp in ports if cp not in w["core2pin"] and cp not in w["tied"] and cp not in w["cat"]]
            assert not missing, f"{w['name']}: slab connects core ports the wrapper lacks: {missing}"
            outs = [(cp, w["pins"][w["core2pin"][cp]][1]) for cp, x in ports.items()
                    if x and cp in w["core2pin"] and w["pins"][w["core2pin"][cp]][0] == "output" and w["pins"][w["core2pin"][cp]][1]]
            # the widest output (numeric msb where known); ties: the first
            def width(o):
                try:
                    return int(eval(o[1], {"__builtins__": {}}))
                except Exception:
                    return 0
            mp = max(outs, key=width)[0] if outs else None
            conn, chk, pre, post = [], [], [], []
            for cp, x in ports.items():
                if cp in w["tied"]:        # the routed top ties this input: the slab must drive the same constant
                    if x:
                        post.append(f'always @({x}) if ($time > 0 && ({x}) != ({w["tied"][cp]})) begin $display('
                                    f'"SU_TILE_TOPS_TIE {w["name"]} core port {cp} %m: the slab drives a value the routed '
                                    f'top ties to {w["tied"][cp]}"); $fatal(1, "SU_TILE_TOPS tie"); end')
                    continue
                if cp in w["cat"]:         # one core port over several wrapper pins: slice the slab bus, msb pin first
                    ws = [int(eval(w["pins"][q][1] or "0", {"__builtins__": {}})) + 1 for q in w["cat"][cp]]
                    tot, hi = sum(ws), sum(ws)
                    pre.append(f"wire [{tot - 1}:0] tt_c_{cp};")
                    post.append(f"assign {x} = tt_c_{cp};" if w["pins"][w["cat"][cp][0]][0] == "output" else f"assign tt_c_{cp} = {x};")
                    for q, wq in zip(w["cat"][cp], ws):
                        conn.append(f".{q}(tt_c_{cp}[{hi - 1}:{hi - wq}])")
                        hi -= wq
                    chk.append(f'if ($bits({x}) != {tot}) begin $display("SU_TILE_TOPS_WIDTH {w["name"]} core port {cp} '
                               f'%m slab %0d pins %0d", $bits({x}), {tot}); tt_bad = 1; end')
                    continue
                pin = w["core2pin"][cp]
                msb = w["pins"][pin][1] or "0"
                if cp == mp:
                    pre.append(f"wire [{msb}:0] tt_mut;")
                    post.append(f"assign {x} = tt_mut ^ ((tmut == 8'd{tm[w['name']]}) ? {mask(msb)} : '0);")
                    conn.append(f".{pin}(tt_mut)")
                else:
                    conn.append(f".{pin}({x})")
                if x:
                    chk.append(f'if ($bits({x}) != ({msb}) + 1) begin $display("SU_TILE_TOPS_WIDTH {w["name"]}.{pin} '
                               f'%m slab %0d pin %0d", $bits({x}), ({msb}) + 1); tt_bad = 1; end')
            used = [w["core2pin"][cp] for cp in ports if cp in w["core2pin"]] + [q for cp in ports for q in w["cat"].get(cp, [])]
            unconn = [p for p in w["pins"] if p not in used]
            g.append(("if (" if k == 0 else "else if (") + (" && ".join(cond) or "1") + f") begin : g_tt{k}_{iname}")
            g += pre
            g.append(f"{w['name']} {iname} ({', '.join(conn)});")
            g += post
            g.append("bit tt_bad = 0; initial begin " + " ".join(chk) + " if (tt_bad) begin #1 $fatal(1, \"SU_TILE_TOPS width\"); end end")
            g.append("end")
            if k == 0:
                man["instances"].append(dict(core=core, inst=iname, line=line, wrappers=[x["name"] for x in wr[core]],
                                             slab_params=par, mutated_port=mp, unconnected_pins=unconn))
        pv = " ".join(f'$display("  {p} = %0d", ({sv}));' for p, sv in par.items())
        g.append(f'else begin : g_ttx_{iname} initial begin $display("SU_TILE_TOPS_NOMATCH {core} {iname} line {line} %m"); {pv} '
                 f'#1 $fatal(1, "SU_TILE_TOPS: no routed top with these parameters"); end end')
        out.append(raw[pos:s])
        out.append("\n".join(g))
        pos = e
    out.append(raw[pos:])
    text = "".join(out)
    m = re.search(r"\bmodule\s+dsfd_sp_su_h\b", text)
    k = text.index("(", m.end())
    if text[m.end():k].strip().startswith("#"):
        k = text.index("(", close_paren(text, k))
    he = text.index(";", close_paren(text, k)) + 1
    decl = ('\n    // SU_TILE_TOPS: per-tile-class output mutant, +tmut=K (0 = none)\n    logic [7:0] tmut;\n'
            '    initial begin tmut = 8\'d0; void\'($value$plusargs("tmut=%d", tmut)); '
            '$display("SU_TILE_TOPS tmut=%0d", tmut); end\n')
    text = text[:he] + decl + text[he:]
    man["n_instances"] = n
    return text, man


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    text, man = build()
    if a.list or not a.out:
        print(json.dumps(man, indent=1))
    if a.out:
        o = Path(a.out)
        o.mkdir(parents=True, exist_ok=True)
        (o / "dsfd_sp_su_h_tt.sv").write_text(text)
        (o / "tile_tops.json").write_text(json.dumps(man, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
