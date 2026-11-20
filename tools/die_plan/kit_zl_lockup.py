#!/usr/bin/env python3
"""kit_zl_lockup.py -- DIE-HEAD-86/SPN 11-08: zero-logic hop LOCKUP LATCHES as a kit RTL post-pass (opt-in).

Why (measured, hd_spn vF_U + hd_spn_end vE2_hooks GRT FF sign-off): a zero-logic register hop (Q -> D through
buffers only) whose launch and capture flops hang on DIFFERENT kit clock tap ports loses the per-port die tap-window
early source latency one for one (no CRPR across ports): hd_spn 2815 non-port hold endpoints to -53.5 ps, hd_spn_end
1195 to -66.8 ps, all station / ingress / spine-node / ft stage hops.  Tap sharing cannot hold these chains (they span
mm; vF_zlA -325.6 ps post-CTS).  The safe form is the TYPE-SAFE-1 hop lockup (gen_rtl.ft_hop_lockup): an ot_dp_lk
negative-level latch (transparent while clk is LOW, ASAP7 DLLx) between launch and capture, clocked from the LAUNCH
flop's tap (clock_taps.tcl hop-latch follow-D pass, instances u_fl_*) and placed at the hop midpoint (face_flops.tcl).
The launch -> latch check is intra-tap; the latch -> capture check gains ~T/2 of hold; 0 cycles added (the latch is
transparent in the low phase of the same cycle; LEC: lec.py latch_to_wire).

What: for every capture instance whose name full-matches a spec regex, the named input port connections are routed
through ONE ot_dp_lk instance u_fl_<base> (ports concatenated, first port in the LSBs).  An input whose connection is a
reset net (rst_n, rst_n_t<k>, rst_boot_t<k>) is left alone.  Every capture (port group) gets its own latch (kept module: never merged).  An input fed by a module input port
is never latched (the port loads its face flop directly).
With "guard" (default "OT_ZL_LOCKUP") the latches sit under `ifdef <guard>` and the else branch is a plain wire, so
the patched file without the define is the original circuit; the kit turns the latches on with -D<guard>.
Never run = no change.  Spec (JSON): {"guard": "OT_ZL_LOCKUP", "hops": [{"inst": "<regex>", "ports": ["d", "ea"]} | {"inst": "<regex>",
"groups": [["i"], ["iw"]], "types": [module types], "allow_missing": true}, ...],
"regs": [{"reg": "<regex>", "allow_missing": true}, ...]}  (first matching entry wins)
LOCKUP-STATION-1130 11-20 (station_rule.py): "regs" entries latch FLATTENED registers of a bound netlist-style RTL
(`reg [W-1:0] R; always @(posedge clk ..) .. R <= X;`): a register whose every non-constant assignment is the same wire
expression X (identifier / slice / concatenation: zero logic) gets ot_dp_lk u_fl_<R> on X, clocked by the always
block's posedge clock; a register with logic, two data sources, a port source or no posedge block is skipped and
counted.  "guard": null emits the latches unguarded (gen_phys clock.zl_lockup: the kit takes no define).
apply_kit(RTL_DIR, SPEC) runs the pass on every staged *.sv that has a match and adds the ot_dp_lk module when no
staged file defines it.

Usage: kit_zl_lockup.py RTL.sv SPEC.json [--out OUT.sv] [--report REPORT.json]
"""
import collections
import json
import re
import sys
from pathlib import Path

RESET_NET = re.compile(r"(rst_n|rst_n_t\d+|rst_boot_t\d+)")
INST_RE = re.compile(r"^[ \t]*(?:\(\*[^*]*\*\)[ \t]*)?([A-Za-z_]\w*)[ \t]*(#\((?:[^()]|\([^()]*\))*\))?[ \t]+([A-Za-z_]\w*)[ \t]*\(",
                     re.M)
KEYWORDS = {"module", "wire", "reg", "logic", "input", "output", "inout", "assign", "always", "if", "else", "begin",
            "end", "generate", "endgenerate", "for", "case", "function", "task", "localparam", "parameter", "genvar"}


class LkError(Exception):
    pass


def _close(txt, i):
    """index just after the ')' matching the '(' at txt[i]."""
    depth = 0
    for k in range(i, len(txt)):
        c = txt[k]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return k + 1
    raise LkError(f"unbalanced parenthesis at offset {i}")


def instances(txt):
    """[(module_type, params, name, start, end_of_conn_list, conn_text_start)] of the module body."""
    out = []
    for m in INST_RE.finditer(txt):
        mt, params, name = m.group(1), m.group(2) or "", m.group(3)
        if mt in KEYWORDS or name in KEYWORDS:
            continue
        lp = m.end() - 1
        try:
            e = _close(txt, lp)
        except LkError:
            continue                                  # e.g. an `ifdef inside the header: not an editable instance
        out.append((mt, params, name, m.start(), e, lp))
    return out


def conns(txt, lp, e):
    """{port: (expr, abs_start, abs_end)} for the named connections in txt[lp:e]."""
    res = {}
    k = lp + 1
    while True:
        m = re.compile(r"\.\s*([A-Za-z_]\w*)\s*\(").search(txt, k, e)
        if not m:
            break
        pe = _close(txt, m.end() - 1)
        res[m.group(1)] = (txt[m.end():pe - 1].strip(), m.end(), pe - 1)
        k = pe
    return res


def _rw(hi, lo):
    """width of [hi:lo]: an int, or a parameter expression string such as '((W-1)-(0)+1)' (LOCKUP-STATION-1130)"""
    try:
        return abs(int(hi) - int(lo)) + 1
    except ValueError:
        return f"(({hi.strip()})-({lo.strip()})+1)"


def _wsum(ws):
    if all(isinstance(w, int) for w in ws):
        return sum(ws)
    return "(" + "+".join(str(w) for w in ws) + ")"


def _bits(ws):
    return sum(w for w in ws if isinstance(w, int))


def decl_widths(txt):
    w = {}
    txt = re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", txt), flags=re.S)
    for m in re.finditer(r"(?:^|[(,])\s*(?:input|output|inout)\s+(?:wire|reg|logic)?\s*(\[\s*([^\]:]+?)\s*:\s*([^\]:]+?)\s*\])?\s*([A-Za-z_]\w*)",
                         txt, re.M):
        w.setdefault(m.group(4), _rw(m.group(2), m.group(3)) if m.group(1) else 1)
    for m in re.finditer(r"\b(?:wire|reg|logic)\b\s*(\[\s*([^\]:]+?)\s*:\s*([^\]:]+?)\s*\])?([^;]*);", txt):
        n = _rw(m.group(2), m.group(3)) if m.group(1) else 1
        for part in m.group(4).split(","):
            nm = re.match(r"\s*([A-Za-z_]\w*)", part.split("=")[0])
            if nm and nm.group(1) not in KEYWORDS:
                w.setdefault(nm.group(1), n)
    return w


def expr_width(expr, widths):
    expr = expr.strip()
    if expr.startswith("{") and expr.endswith("}"):
        inner = expr[1:-1]
        if re.match(r"^\s*\d+\s*\{", inner):
            raise LkError(f"replication not supported: {expr}")
        parts, depth, cur = [], 0, ""
        for c in inner:
            if c in "{[(":
                depth += 1
            elif c in "}])":
                depth -= 1
            if c == "," and depth == 0:
                parts.append(cur)
                cur = ""
            else:
                cur += c
        parts.append(cur)
        return _wsum([expr_width(p, widths) for p in parts])
    m = re.fullmatch(r"([A-Za-z_]\w*)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]", expr)
    if m:
        return abs(int(m.group(2)) - int(m.group(3))) + 1
    m = re.fullmatch(r"([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]", expr)
    if m:
        return 1
    if re.fullmatch(r"[A-Za-z_]\w*", expr):
        if expr not in widths:
            raise LkError(f"no declaration for {expr}")
        return widths[expr]
    raise LkError(f"unsupported connection expression {expr!r}")


def port_width(mt, params, port, expr, widths):
    if mt in ("ot_dp_st", "ot_dp_ste"):
        if port == "ea":
            return 1
        if port == "d":
            m = re.search(r"\.W\((\d+)\)", params)
            return int(m.group(1)) if m else 1
    return expr_width(expr, widths)


def input_ports(txt, hdr):
    """names of the module's input ports (a port feeds its face flop directly: never latched)."""
    return set(re.findall(r"^\s*input\s+(?:wire|reg|logic)?\s*(?:\[[^\]]*\])?\s*([A-Za-z_]\w*)", hdr, re.M))


CONST_RE = re.compile(r"^\s*(?:\d*'[sS]?[bBhHdDoO][0-9a-fA-FxXzZ_?]+|\d+|\{\s*\d+\s*\{[^{}]*\}\s*\})\s*$")
LK_MODULE = """
// ot_dp_lk: negative-level lockup latch (transparent while clk is LOW), kit_zl_lockup (LOCKUP-STATION-1130); same text as
// gen_rtl.py.  LEC: tools/die_plan/lec.py latch_to_wire.
(* keep_hierarchy, keep *)
module ot_dp_lk #(parameter integer W = 1) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output reg  [W-1:0] q
);
    always @(*) if (!clk) q = d;  // Verilog-2001 latch (read_verilog without -sv; yosys infers $dlatch)
endmodule
"""


def _reg_edits(txt, hdr_end, regs, ins, widths, used, latches, edits, skipped):
    """flattened register captures (spec "regs"): edits + latches; returns the per-entry hit counts."""
    hit = [0] * len(regs)
    body = txt[hdr_end:]
    names = sorted(set(re.findall(r"\breg\b\s*(?:\[[^\]]*\])?\s*([A-Za-z_]\w*)\s*;", body)) |
                   set(re.findall(r"\boutput\s+reg\b\s*(?:\[[^\]]*\])?\s*([A-Za-z_]\w*)\s*[,;)]", txt[:hdr_end])))
    alw = [(m.start(), m.group(1), m.group(2)) for m in
           re.finditer(r"\balways\s*@\s*\(\s*(posedge|negedge)\s+([A-Za-z_]\w*)", body)]
    for nm in names:
        sel = next((i for i, (rx, *_r) in enumerate(regs) if rx.fullmatch(nm)), None)
        if sel is None:
            continue
        dm = re.search(r"\breg\b\s*(?:\[[^\]]*\])?\s*" + re.escape(nm) + r"\s*;", body)
        pre_txt = body[:dm.start()] if dm else ""            # an output reg is declared in the header: top level
        depth = (len(re.findall(r"\bbegin\b", pre_txt)) - len(re.findall(r"\bend\b", pre_txt))
                 + len(re.findall(r"\bgenerate\b", pre_txt)) - len(re.findall(r"\bendgenerate\b", pre_txt)))
        if depth:
            skipped["scope"] += 1                     # declared in a generate / named block: not visible at module end
            continue
        hit[sel] += 1
        asg = [m for m in re.finditer(r"\b" + re.escape(nm) + r"\s*<=\s*([^;]+);", body)]
        data = [m for m in asg if not CONST_RE.match(m.group(1))]
        if not data:
            skipped["const"] += 1
            continue
        exprs = {re.sub(r"\s+", "", m.group(1)) for m in data}
        if len(exprs) != 1:
            skipped["logic"] += 1
            continue
        x = data[0].group(1).strip()
        try:
            w = expr_width(x, widths)
        except LkError:
            skipped["logic"] += 1
            continue
        if w != widths.get(nm, w):
            skipped["logic"] += 1
            continue
        if (re.match(r"[A-Za-z_]\w*", x.lstrip("{ ")) or [None])[0] in ins and not regs[sel][2]:
            skipped["port"] += 1                      # the kit top: a pin loads its face flop directly
            continue
        pre = [a for a in alw if a[0] < data[0].start()]
        if not pre or pre[-1][1] != "posedge":
            skipped["clock"] += 1
            continue
        ln = f"fl_{nm}"
        while ln in used:
            ln += "_x"
        used.add(ln)
        latches.append(dict(inst=f"u_{ln}", net=ln, width=w, src=x, capture=nm, ports=["<="], clk=pre[-1][2]))
        for m in data:
            edits.append((hdr_end + m.start(1), hdr_end + m.end(1), ln))
    return hit


def apply(txt, spec):
    guard = spec.get("guard", "OT_ZL_LOCKUP")
    hops = []
    for h in spec.get("hops") or []:
        groups = h.get("groups") or [h["ports"]]
        types = set(h.get("types") or [])
        hops.append((re.compile(h["inst"]), [list(g) for g in groups], types, bool(h.get("allow_missing"))))
    mod = re.search(r"\bmodule\s+\w+\s*(#\((?:[^()]|\([^()]*\))*\))?\s*\(", txt)
    if not mod:
        raise LkError("no module header")
    hdr_end = txt.index(";", _close(txt, mod.end() - 1)) + 1
    ins = input_ports(txt, txt[:hdr_end])
    widths = decl_widths(txt)
    insts = instances(txt[hdr_end:])
    edits, latches, used = [], [], set()
    hit = {i: 0 for i in range(len(hops))}
    skipped = dict(reset=0, port=0, logic=0, const=0, clock=0, scope=0)
    for mt, params, name, s, e, lp in insts:
        if mt == "ot_dp_lk" or name.startswith("u_fl_"):
            continue
        sel = None
        for i, (rx, groups, types, am) in enumerate(hops):
            if rx.fullmatch(name) and (not types or mt in types):
                sel = (i, groups, am)
                break
        if sel is None:
            continue
        hit[sel[0]] += 1
        cs = conns(txt, hdr_end + lp, hdr_end + e)
        for gi, group in enumerate(sel[1]):
            missing = [p for p in group if p not in cs]
            if missing and not sel[2]:
                raise LkError(f"{name}: no connection for port(s) {missing}")
            ports = []
            for p in group:
                if p not in cs:
                    continue
                x = cs[p][0]
                if RESET_NET.fullmatch(x):
                    skipped["reset"] += 1
                    continue
                if CONST_RE.match(x):
                    skipped["const"] += 1
                    continue
                if (re.match(r"[A-Za-z_]\w*", x.lstrip("{ ")) or [None])[0] in ins:
                    skipped["port"] += 1
                    continue
                ports.append(p)
            if not ports:
                continue
            ws = [port_width(mt, params, p, cs[p][0], widths) for p in ports]
            exprs = [cs[p][0] for p in ports]
            tot = _wsum(ws)
            if not isinstance(tot, int) and len(ports) > 1:
                skipped["logic"] += 1                 # a parameter-width group of several ports: not split here
                continue
            base = name[2:] if name.startswith("u_") else name
            base = re.sub(r"\W", "_", base) + ("" if len(sel[1]) == 1 else "_" + "_".join(group))
            ln = f"fl_{base}"
            while ln in used:
                ln += "_x"
            used.add(ln)
            src = exprs[0] if len(exprs) == 1 else "{" + ", ".join(reversed(exprs)) + "}"
            ck = cs["clk"][0] if "clk" in cs and re.fullmatch(r"[A-Za-z_]\w*", cs["clk"][0]) else "clk"
            latches.append(dict(inst=f"u_{ln}", net=ln, width=tot, src=src, capture=name, ports=ports, clk=ck))
            lo = 0
            for p, w in zip(ports, ws):
                if tot == 1 or not isinstance(tot, int):
                    sl = ln
                elif w == 1:
                    sl = f"{ln}[{lo}]"
                else:
                    sl = f"{ln}[{lo + w - 1}:{lo}]"
                edits.append((cs[p][1], cs[p][2], sl))
                lo += w
    for i, n in hit.items():
        if n == 0 and not hops[i][3]:
            raise LkError(f"spec hop {spec['hops'][i]['inst']!r} matched no instance")
    mname = re.search(r"\bmodule\s+(\w+)", txt).group(1)
    # a module-scoped entry applies in its module only, and there a port-fed register is an internal hop (latched)
    regs = [(re.compile(r["reg"]), bool(r.get("allow_missing")), bool(r.get("module")))
            if r.get("module") in (None, mname) else (re.compile(r"(?!x)x"), True, True) for r in spec.get("regs") or []]
    if regs:
        rh = _reg_edits(txt, hdr_end, regs, ins, widths, used, latches, edits, skipped)
        for i, n in enumerate(rh):
            if n == 0 and not regs[i][1]:
                raise LkError(f"spec reg {spec['regs'][i]['reg']!r} matched no register")
    if not latches:
        return txt, latches, skipped
    for a, b, sl in sorted(edits, reverse=True):
        txt = txt[:a] + sl + txt[b:]
    decl = [f"    // kit_zl_lockup (DIE-HEAD-86/SPN 11-08): {len(latches)} zero-logic hop lockup latches, "
            f"{_bits([l['width'] for l in latches])} bits; " + (f"on with -D{guard}" if guard else "unguarded")]
    for l in latches:
        decl.append(f"    wire [{l['width'] - 1 if isinstance(l['width'], int) else str(l['width']) + '-1'}:0] {l['net']};  // kit_zl_lockup: {l['capture']}.{'+'.join(l['ports'])}")
    lk = ["    // negative-level lockup latches (ot_dp_lk: transparent while clk is LOW), 0 cycles; clock_taps.tcl hangs",
          "    // each u_fl_* latch on its LAUNCH flop's tap, face_flops.tcl places it at the hop midpoint"]
    lk += [f"    ot_dp_lk #(.W({l['width']})) {l['inst']} (.clk({l.get('clk', 'clk')}), .d({l['src']}), .q({l['net']}));"
           for l in latches]
    if guard:
        body = [f"`ifdef {guard}"] + lk + ["`else"] + [f"    assign {l['net']} = {l['src']};" for l in latches] + ["`endif"]
    else:
        body = lk
    txt = txt[:hdr_end] + "\n" + "\n".join(decl) + txt[hdr_end:]
    txt = re.sub(r"(\n\s*endmodule\b)", lambda m: "\n" + "\n".join(body) + m.group(1), txt, count=1)
    return txt, latches, skipped


def apply_kit(rtl_dir, spec):
    """gen_phys entry (plan clock.zl_lockup, LOCKUP-STATION-1130): the pass on every staged *.sv / *.v of the kit that
    has a match (an entry may match in one file only; an entry that matches in NO file fails closed unless
    allow_missing).  Adds ot_dp_lk to the first patched file when no staged file defines it.  -> {file: stats}"""
    files = sorted(Path(rtl_dir).glob("*.sv")) + sorted(Path(rtl_dir).glob("*.v"))
    out, any_hit, patched, errors = {}, set(), [], []
    hop_rx = [re.compile(h["inst"]) for h in spec.get("hops") or []]
    reg_rx = [re.compile(r["reg"]) for r in spec.get("regs") or []]
    for f in files:
        src = f.read_text(errors="replace")
        if not re.search(r"\bmodule\b", src) or re.search(r"\bmodule\s+ot_dp_lk\b", src):
            continue
        sub = dict(spec, hops=[dict(h, allow_missing=True) for h in spec.get("hops") or []],
                   regs=[dict(r, allow_missing=True) for r in spec.get("regs") or []])
        words = set(re.findall(r"[A-Za-z_]\w*", src))
        if not any(rx.fullmatch(w) for w in words for rx in hop_rx + reg_rx):
            continue                                  # no name of this file can match: never parsed, never touched
        # one pass per module of the file (a staged leaf file may hold several modules)
        pieces, lat, sk, k = [], [], collections.Counter(), 0
        for m in re.finditer(r"(?s)\bmodule\s+[A-Za-z_]\w*.*?\bendmodule\b", src):
            pieces.append(src[k:m.start()])
            chunk = m.group(0)
            try:
                ctxt, clat, csk = apply(chunk + "\n", sub)
            except LkError as ex:                      # a module the pass cannot read stays as it is, recorded;
                errors.append(f"{f.name}:{m.group(0)[:60].split('(')[0].strip()}: {ex}")   # a strict entry that
                ctxt, clat, csk = chunk + "\n", [], {}                                     # then matches nothing fails below
            pieces.append(ctxt[:-1] if ctxt.endswith("\n") and not chunk.endswith("\n") else ctxt)
            lat += clat
            sk.update(csk)
            k = m.end()
        pieces.append(src[k:])
        txt, sk = "".join(pieces), dict(sk)
        if not lat:
            continue
        for l in lat:
            for i, rx in enumerate(hop_rx):
                if rx.fullmatch(l["capture"]):
                    any_hit.add(("h", i))
            for i, rx in enumerate(reg_rx):
                if rx.fullmatch(l["capture"]):
                    any_hit.add(("r", i))
        tmp = f.with_name(f.name + ".zlk_tmp")
        tmp.write_text(txt)
        tmp.replace(f)
        patched.append(f)
        out[f.name] = dict(latches=len(lat), bits=_bits([l["width"] for l in lat]), skipped=sk)
    if errors:
        out["_unparsed_modules"] = errors[:50]
    for i, h in enumerate(spec.get("hops") or []):
        if ("h", i) not in any_hit and not h.get("allow_missing"):
            raise LkError(f"spec hop {h['inst']!r} matched no instance in {rtl_dir}")
    for i, r in enumerate(spec.get("regs") or []):
        if ("r", i) not in any_hit and not r.get("allow_missing"):
            raise LkError(f"spec reg {r['reg']!r} matched no register in {rtl_dir}")
    if patched and not any(re.search(r"\bmodule\s+ot_dp_lk\b", f.read_text(errors="replace")) for f in files):
        with open(patched[0], "a") as fh:
            fh.write(LK_MODULE)
        out[patched[0].name]["ot_dp_lk_module"] = True
    return out


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    rtl, spec = Path(argv[0]), json.loads(Path(argv[1]).read_text())
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else rtl
    txt, latches, skipped = apply(rtl.read_text(), spec)
    out.write_text(txt)
    rep = dict(rtl=str(out), guard=spec.get("guard", "OT_ZL_LOCKUP"), latches=len(latches),
               bits=_bits([l["width"] for l in latches]), skipped=skipped, entries=latches)
    if "--report" in argv:
        Path(argv[argv.index("--report") + 1]).write_text(json.dumps(rep, indent=1))
    print(json.dumps(dict(latches=rep["latches"], bits=rep["bits"], skipped=skipped)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
