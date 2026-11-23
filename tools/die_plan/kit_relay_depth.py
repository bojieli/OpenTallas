"""KIT-RD-1 (FABLE-FIX-S81-LEPE 11-20, COORD): plan relay_depth rows in bind.py kit-rtl.

kit-rtl wraps the bound module that an EARLIER bind run wrote (BIND_OUT/rtl/<module>.sv); the plan it is given may carry
relay_depth rows that bind run never saw.  Until now those rows were dropped without a word: S81 proof6 (lepe_mu_LP__t2,
4 rows {u_lnl<N>, k_li_r, side sink, D 1}) got a kit with 0 of the 4 stages and nothing in the log.

apply(btxt, tn, rows, leaf_id) -> (btxt, receipt):
  * a row whose stages are already in the bound text (bind emitted them: u_y_xd_<sink>_<port>_* for a sink row, a
    u_y_xd_* stage fed by w_<source>_<port> for a source row) is left alone and counted "bound";
  * a SINK row (side "sink") is applied here: D single-stage ot_dp_dly instances u_y_xd_<sink>_<port>_k<row>_<s> (the
    bind's relay-named form, so relay_mid / relay_sites treat them as relay stages) in front of bits [lo, hi] of the
    sink instance's input port, on the bound module's clk; the cycles are DECLARED in the receipt (kit_relay_depth.json);
  * anything else raises ValueError naming the row: a source row the bound text does not carry, a sink instance or port
    that is not in the bound text, a port connection that is not a plain wire / bit / slice, bits outside the port, or a
    bound module without a clk input.  A row is never dropped silently.
Rows absent = byte-identical text, receipt None."""
import re


def _row_name(r):
    return f"{r.get('inst')}.{r.get('port', 'i' if r.get('side') == 'sink' else 'o')}"


def _inst_span(btxt, iname):
    """(start, end) of the port list of instance iname: the text between its '(' and the matching ')'."""
    m = re.search(rf"(?<![\w$])({re.escape(iname)})\s*\(", btxt)
    if not m:
        return None
    i = m.end() - 1
    depth = 0
    for j in range(i, len(btxt)):
        if btxt[j] == "(":
            depth += 1
        elif btxt[j] == ")":
            depth -= 1
            if depth == 0:
                return i + 1, j
    return None


def _width(btxt, expr):
    """bit width of a plain connection expression, None when it is not a wire / bit / slice of a declared wire."""
    e = expr.strip()
    if e.startswith("{") and e.endswith("}") and "{" not in e[1:-1]:
        # RESET-RELAY-GEN-1530 11-21: {a, b[3:0], c[2]} of plain items (an S81 lane pad .d({eb, b}))
        ws = [_width(btxt, x) for x in e[1:-1].split(",")]
        return sum(ws) if ws and None not in ws else None
    m = re.fullmatch(r"([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]", e)
    if m:
        return 1
    m = re.fullmatch(r"([A-Za-z_]\w*)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]", e)
    if m:
        return abs(int(m.group(2)) - int(m.group(3))) + 1
    m = re.fullmatch(r"[A-Za-z_]\w*", e)
    if m:
        d = re.search(rf"^\s*(?:wire|input\s+wire|output\s+wire|reg)\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s+{re.escape(e)}\s*[;,]",
                      btxt, re.M)
        if d:
            return abs(int(d.group(1)) - int(d.group(2))) + 1 if d.group(1) else 1
    return None


def apply(btxt, tn, rows, leaf_id, sv_id):
    rows = list(rows or [])
    if not rows:
        return btxt, None
    rec = dict(schema="opentallas.kit_relay_depth.v1", type=tn, rows=[])
    decl, body = [], []
    for k, r in enumerate(rows):
        name = _row_name(r)
        sid, port, D = sv_id(r["inst"]), r.get("port", "i" if r.get("side") == "sink" else "o"), int(r["D"])
        if r.get("side") != "sink":
            fed = re.search(rf"u_y_xd_\w*\s*\(\s*\.clk\(clk\),\s*\.d\(\{{?[^)]*\bw_{re.escape(sid)}_{re.escape(port)}\b", btxt)
            if not fed:
                raise ValueError(f"relay_depth {tn}: row {name} (source side, D {D}) is not in the bound module and kit-rtl "
                                 "cannot add a source-side stage: re-run bind.py on this plan")
            rec["rows"].append(dict(row=name, D=D, how="bound"))
            continue
        if re.search(rf"\bu_y_xd_{re.escape(sid)}_{re.escape(port)}_\w+\s*\(", btxt):
            rec["rows"].append(dict(row=name, D=D, how="bound"))
            continue
        if D < 1:
            raise ValueError(f"relay_depth {tn}: row {name}: D {D} < 1")
        if not re.search(r"^\s*input\s+wire\s+clk\s*[,)]", btxt, re.M):
            raise ValueError(f"relay_depth {tn}: row {name}: the bound module has no clk input")
        iname = next((n for n in (leaf_id(r["inst"]), sid, r["inst"]) if _inst_span(btxt, n)), None)
        if iname is None:
            raise ValueError(f"relay_depth {tn}: row {name}: sink instance {leaf_id(r['inst'])} is not in the bound module")
        a, b = _inst_span(btxt, iname)
        seg = btxt[a:b]
        pm = re.search(rf"\.{re.escape(port)}\s*\(", seg)
        if not pm:
            raise ValueError(f"relay_depth {tn}: row {name}: {iname} has no connection .{port}(...)")
        i0 = pm.end()
        depth, j = 1, i0
        while depth:
            depth += {"(": 1, ")": -1}.get(seg[j], 0)
            j += 1
        expr = seg[i0:j - 1]
        W = _width(btxt, expr)
        if W is None:
            raise ValueError(f"relay_depth {tn}: row {name}: connection .{port}({expr.strip()}) is not a plain wire, bit or "
                             "slice; kit-rtl cannot stage it")
        lo, hi = (r.get("bits") or [0, None])
        lo, hi = int(lo), (W - 1 if hi is None else int(hi))
        if not (0 <= lo <= hi < W):
            raise ValueError(f"relay_depth {tn}: row {name}: bits [{lo}, {hi}] outside the {W}-bit connection {expr.strip()}")
        base = f"u_y_xd_{sid}_{port}_k{k}"
        win, wout = f"rdk_{sid}_{port}_k{k}_in", f"rdk_{sid}_{port}_k{k}_out"
        n = hi - lo + 1
        decl.append(f"    wire [{W - 1}:0] {win};  // KIT-RD-1 relay_depth row {name}: D {D} on bits {lo}..{hi}")
        decl.append(f"    wire [{W - 1}:0] {wout};")
        body.append(f"    assign {win} = {expr.strip()};")
        prev = f"{win}[{hi}:{lo}]"
        lk = bool(r.get("lockup"))
        for s in range(D):
            q = f"{base}_s{s}_q"
            decl.append(f"    wire [{n - 1}:0] {q};")
            qf = f"{base}_s{s}_f" if lk else q
            if lk:
                decl.append(f"    wire [{n - 1}:0] {qf};")
            body.append(f"    ot_dp_dly #(.W({n}), .D(1)) {base}_{s} (.clk(clk), .d({prev}), .q({qf}));  "
                        f"// relay_depth (kit-rtl): stage {s + 1}/{D} DECLARED on bits {lo}..{hi}")
            if lk:                  # FABLE-CLOSURE-1930: lockup latch after the stage (0 cycles, T/2 hold margin across taps)
                body.append(f"    ot_dp_lk #(.W({n})) u_lk_xd_{sid}_{port}_k{k}_{s} (.clk(clk), .d({qf}), .q({q}));  "
                            f"// relay_depth lockup latch")
                rec["needs_cells"] = ["ot_dp_lk"]
            prev = q
        body.append(f"    assign {wout}[{hi}:{lo}] = {prev};")
        if hi < W - 1:
            body.append(f"    assign {wout}[{W - 1}:{hi + 1}] = {win}[{W - 1}:{hi + 1}];")
        if lo > 0:
            body.append(f"    assign {wout}[{lo - 1}:0] = {win}[{lo - 1}:0];")
        new = wout if W > 1 else f"{wout}[0]"
        seg = seg[:i0] + new + seg[j - 1:]
        btxt = btxt[:a] + seg + btxt[b:]
        lkc = int(r.get("lockup_cycles") or 0)          # LOCKUP-NEGEDGE: the latch in front of a falling-edge capture is +1 cycle
        if lkc and not lk:
            raise ValueError(f"relay_depth {tn}: row {name}: lockup_cycles needs lockup true")
        rec["rows"].append(dict(row=name, D=D, bits=[lo, hi], how="kit-rtl", stages=[f"{base}_{s}" for s in range(D)],
                                cycles_added=D + lkc, **({"lockup_cycles": lkc} if lkc else {})))
    if decl:
        # declarations right after the port list (the sink instance uses the new wires), stages before endmodule
        h = re.search(r"^\s*\);[ \t]*$", btxt, re.M)
        m = list(re.finditer(r"^\s*endmodule\b", btxt, re.M))
        if not h or not m or h.end() > m[0].start():
            raise ValueError(f"relay_depth {tn}: cannot find the bound module port list / endmodule")
        at = m[0].start()
        btxt = btxt[:at] + "\n".join(body) + "\n" + btxt[at:]
        btxt = btxt[:h.end()] + "\n" + "\n".join(decl) + btxt[h.end():]
    rec["applied"] = sum(1 for x in rec["rows"] if x["how"] == "kit-rtl")
    rec["bound"] = sum(1 for x in rec["rows"] if x["how"] == "bound")
    return btxt, rec


def check_branch(btxt, tn, rows, leaf_id):
    """plan relay_branch rows against the bound text: kit-rtl cannot make a relay copy, so every planned copy leaf must already be
    a bound instance (bind.py relay_branch.apply); a missing copy raises ValueError naming the row and the copy.  Returns the
    number of copies checked."""
    n = 0
    for r in rows or []:
        for cp in r.get("copies") or []:
            if not re.search(rf"(?<![\w$]){re.escape(leaf_id(cp['name']))}\s*\(", btxt):
                raise ValueError(f"relay_branch {tn}: row {r.get('inst')} copy {cp['name']} is not in the bound module and kit-rtl "
                                 "cannot add a relay copy: re-run bind.py on this plan")
            n += 1
    return n
