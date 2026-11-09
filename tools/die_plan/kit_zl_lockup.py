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
"groups": [["i"], ["iw"]], "types": [module types], "allow_missing": true}, ...]}  (first matching entry wins)

Usage: kit_zl_lockup.py RTL.sv SPEC.json [--out OUT.sv] [--report REPORT.json]
"""
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
        e = _close(txt, lp)
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


def decl_widths(txt):
    w = {}
    txt = re.sub(r"/\*.*?\*/", "", re.sub(r"//[^\n]*", "", txt), flags=re.S)
    for m in re.finditer(r"^\s*(?:input|output|inout)\s+(?:wire|reg|logic)?\s*(\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*([A-Za-z_]\w*)",
                         txt, re.M):
        w.setdefault(m.group(4), abs(int(m.group(2)) - int(m.group(3))) + 1 if m.group(1) else 1)
    for m in re.finditer(r"\b(?:wire|reg|logic)\b\s*(\[\s*(\d+)\s*:\s*(\d+)\s*\])?([^;]*);", txt):
        n = abs(int(m.group(2)) - int(m.group(3))) + 1 if m.group(1) else 1
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
        return sum(expr_width(p, widths) for p in parts)
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


def apply(txt, spec):
    guard = spec.get("guard", "OT_ZL_LOCKUP")
    hops = []
    for h in spec["hops"]:
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
    skipped = dict(reset=0, port=0)
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
                if (re.match(r"[A-Za-z_]\w*", x.lstrip("{ ")) or [None])[0] in ins:
                    skipped["port"] += 1
                    continue
                ports.append(p)
            if not ports:
                continue
            ws = [port_width(mt, params, p, cs[p][0], widths) for p in ports]
            exprs = [cs[p][0] for p in ports]
            tot = sum(ws)
            base = name[2:] if name.startswith("u_") else name
            base = re.sub(r"\W", "_", base) + ("" if len(sel[1]) == 1 else "_" + "_".join(group))
            ln = f"fl_{base}"
            while ln in used:
                ln += "_x"
            used.add(ln)
            src = exprs[0] if len(exprs) == 1 else "{" + ", ".join(reversed(exprs)) + "}"
            latches.append(dict(inst=f"u_{ln}", net=ln, width=tot, src=src, capture=name, ports=ports))
            lo = 0
            for p, w in zip(ports, ws):
                if tot == 1:
                    sl = ln
                elif w == 1:
                    sl = f"{ln}[{lo}]"
                else:
                    sl = f"{ln}[{lo + w - 1}:{lo}]"
                edits.append((cs[p][1], cs[p][2], sl))
                lo += w
    for i, n in hit.items():
        if n == 0:
            raise LkError(f"spec hop {spec['hops'][i]['inst']!r} matched no instance")
    for a, b, sl in sorted(edits, reverse=True):
        txt = txt[:a] + sl + txt[b:]
    decl = [f"    // kit_zl_lockup (DIE-HEAD-86/SPN 11-08): {len(latches)} zero-logic hop lockup latches, "
            f"{sum(l['width'] for l in latches)} bits; on with -D{guard}"]
    for l in latches:
        decl.append(f"    wire [{l['width'] - 1}:0] {l['net']};  // kit_zl_lockup: {l['capture']}.{'+'.join(l['ports'])}")
    body = [f"`ifdef {guard}",
            "    // negative-level lockup latches (ot_dp_lk: transparent while clk is LOW), 0 cycles; clock_taps.tcl hangs",
            "    // each u_fl_* latch on its LAUNCH flop's tap, face_flops.tcl places it at the hop midpoint"]
    body += [f"    ot_dp_lk #(.W({l['width']})) {l['inst']} (.clk(clk), .d({l['src']}), .q({l['net']}));" for l in latches]
    body.append("`else")
    body += [f"    assign {l['net']} = {l['src']};" for l in latches]
    body.append("`endif")
    txt = txt[:hdr_end] + "\n" + "\n".join(decl) + txt[hdr_end:]
    txt = re.sub(r"(\n\s*endmodule\b)", lambda m: "\n" + "\n".join(body) + m.group(1), txt, count=1)
    return txt, latches, skipped


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    rtl, spec = Path(argv[0]), json.loads(Path(argv[1]).read_text())
    out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else rtl
    txt, latches, skipped = apply(rtl.read_text(), spec)
    out.write_text(txt)
    rep = dict(rtl=str(out), guard=spec.get("guard", "OT_ZL_LOCKUP"), latches=len(latches),
               bits=sum(l["width"] for l in latches), skipped=skipped, entries=latches)
    if "--report" in argv:
        Path(argv[argv.index("--report") + 1]).write_text(json.dumps(rep, indent=1))
    print(json.dumps(dict(latches=rep["latches"], bits=rep["bits"], skipped=skipped)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
