#!/usr/bin/env python3
"""DIE-KV-64/RF-C 11-03 (RE-FORM batch RF-KV1): HR core face wrapper, applied by gen_core_kit_kv.py from the recipe
key rf_wrap = {"resets": [port, ...], "fwft_reads": [{"rd": P, "rdata": P, "rempty": P, "rst": P}, ...]}.

The kit top file (face-recut <mod>.v) is kept bit for bit except that its module is renamed <mod>__rf_core; a new
module <mod> with the identical port list wraps it:
  * reset relay (registered reset face): each listed active-low reset port drives exactly one relay flop
    (async assert, synchronous release one ck edge later); the relay Q is the core's reset.  Reset release +1 edge.
  * registered FWFT read face: rdata / rempty come straight from flops (rdata = a private port bank whose hold
    input is the internal hold bank, so the port flop Q loads only the port) (one-entry prefetch stage: the inner FIFO is
    popped when the stage is empty or the face pops it; FWFT semantics kept, throughput 1/cycle, +1 read latency).
  * read-address copies (spec key "rcopy_bits": B): each inner FIFO head read  assign X = \\I.mem [\\I.rbin [..]]
    selects each B-bit slice of the row with its own kept copy of the read address, loaded with the rbin next state
    on the same edge (same form as ot_link_afifo RCOPY): bounded select fanout, no select-tree slew class.
  * negedge mid stage (spec key "negmid": [{"reg": R, "src": S}]): a zero-logic same-clock copy R <= f(S) becomes
    S -> kept negedge flop -> R; R still holds f(S) of the previous rising edge (cycle exact), but each half has a
    half-period hold window by construction (closes the zero-logic hold class without pad buffers).
  * bank split (spec key "bank_split": {"mem", "data", "en", "wa"}): a 2-bank flop memory (reads q[{b, a}]) is
    written from one kept negedge copy of the write-data face register per bank (cycle exact): each copy drives
    one bank's rows, so the face register Q drives 2 loads instead of every row (bounded fanout, no slew class).
All other ports pass through unchanged.
"""
import json
import re


def ports(text, mod):
    m = re.search(r"^module\s+" + re.escape(mod) + r"\s*\((.*?)\);", text, re.S | re.M)
    if not m:
        raise SystemExit(f"rf_wrap: module {mod} not found")
    order = [p.strip() for p in m.group(1).split(",")]
    body = text[m.end():text.index("endmodule", m.end())]
    decl = {}
    for d, rng, n in re.findall(r"^\s*(input|output)\s+(?:wire\s+|reg\s+)?(\[[^\]]+\])?\s*([A-Za-z_][\w$]*)\s*;", body, re.M):
        decl[n] = (d, rng or "")
    miss = [p for p in order if p not in decl]
    if miss:
        raise SystemExit(f"rf_wrap: no declaration for ports {miss[:5]}")
    return order, decl, m.start()


def width(rng):
    if not rng:
        return 1
    a, b = [int(x) for x in rng.strip("[]").split(":")]
    return abs(a - b) + 1


def rcopy(body, bits):
    """replicate the FIFO head read address per bits-wide slice (equivalent: every copy = rbin[AW-1:0])"""
    rep = []
    pat = r"^  assign (\S+) = \\(\S+)\.mem \[\\\2\.rbin \[(\d+):0\]\];\n"
    for fifo in [mm.group(2) for mm in re.finditer(pat, body, re.M)]:
        m = [mm for mm in re.finditer(pat, body, re.M) if mm.group(2) == fifo][0]   # offsets move per rewrite
        x, i, hi = m.group(1), m.group(2), int(m.group(3)); aw = hi + 1; ie = re.escape(i)
        mw = re.search(r"reg \[(\d+):0\] \\" + ie + r"\.mem  \[", body)
        blk = re.search(r"  always @\(posedge ([^,]+), negedge ([^)]+)\)\n\s*if \(!\2\) \\" + ie +
                        r"\.rbin  <= \S+;\n\s*else \\" + ie + r"\.rbin  <= (\S+);\n", body)
        if not (mw and blk):
            raise SystemExit(f"rf_wrap rcopy: {i} mem/rbin form not found")
        w = int(mw.group(1)) + 1; k = -(-w // bits); ck, rst, nx = blk.groups()
        add, rd = [], []
        for c in range(k):
            r = f"\\{i}.rf_rbc{c} "; row = f"\\{i}.rf_row{c} "; lo = c * bits; h = min(w, lo + bits) - 1
            add += [f"  (* keep = 1 *) reg [{aw-1}:0] {r};",
                    f"  always @(posedge {ck}, negedge {rst}) if (!{rst}) {r} <= {aw}'h0; else {r} <= {nx}[{aw-1}:0];"]
            rd += [f"  wire [{w-1}:0] {row} = \\{i}.mem [{r}];", f"  assign {x}[{h}:{lo}] = {row}[{h}:{lo}];"]
        body = body[:m.start()] + "\n".join(rd) + "\n" + body[m.end():]
        b2 = body.index(blk.group(0)) + len(blk.group(0))
        body = body[:b2] + "\n".join(add) + "\n" + body[b2:]
        rep.append(dict(fifo=i, rdata=x, width=w, aw=aw, copies=k, slice_bits=bits, added_flops=k * aw))
    return body, rep


def negmid(body, items, ck="ck"):
    rep = []
    for it in items:
        r, src = it["reg"], it["src"]
        m = re.search(r"^(\s*else " + re.escape(r) + r" <= )(.*);\n", body, re.M)
        w = re.search(r"reg \[(\d+):0\] " + re.escape(src) + r";", body)
        if not (m and w) or src not in m.group(2):
            raise SystemExit(f"rf_wrap negmid: {r} <= ..{src}.. form not found")
        nm = (r if r.startswith("\\") else "\\" + r + " ").rstrip() + ".rf_nm "
        n = int(w.group(1)) + 1
        rst = it.get("rst")
        # source async reset asserted between the negedge sample and the next rising edge: gate the mid stage with
        # the source reset level so R takes the reset value on exactly the same edge as the original copy
        use = nm if not rst else nm.rstrip() + "g "
        body = body[:m.start()] + m.group(1) + m.group(2).replace(src, use) + ";\n" + body[m.end():]
        gate = f"  wire [{n-1}:0] {use} = {nm} & {{{n}{{{rst}}}}};\n" if rst else ""
        w = re.search(r"reg \[(\d+):0\] " + re.escape(src) + r";\n", body)   # declare before every use
        body = body[:w.end()] + (f"  (* keep = 1 *) reg [{n-1}:0] {nm};\n"
                                 f"  always @(negedge {ck}) {nm} <= {src};\n" + gate) + body[w.end():]
        rep.append(dict(reg=r, src=src, src_reset=rst, width=n, added_flops=n, form="negedge mid stage, cycle exact"))
    return body, rep


def bank_split(body, sp, ck="ck"):
    mem, data, en, wa = sp["mem"], sp["data"], sp["en"], sp["wa"]
    d = re.search(r"^  reg \[(\d+):0\] " + re.escape(mem) + r" \[15:0\];\n", body, re.M)
    if not d:
        raise SystemExit("rf_wrap bank_split: memory declaration not found")
    w = int(d.group(1)) + 1
    blk = re.compile(r"^  always @\(posedge " + ck + r"\) begin\n(?:    if \(\w+\[\d+\]\)\n      " + re.escape(mem) +
                     r"\[\w+\]\[\d+:\d+\] <= \w+\[\d+\];\n)+  end\n", re.M)
    b = blk.search(body, d.end())
    if not b or b.start() != d.end():
        raise SystemExit("rf_wrap bank_split: per-bit write block not found right after the declaration")
    nb = b.group(0).count(" <= ")
    if nb != w:
        raise SystemExit(f"rf_wrap bank_split: write block covers {nb} of {w} bits")
    rd = {}
    for k in (0, 1):
        m = re.search(r"^  assign (\w+) = " + re.escape(mem) + r"\[\{ 1'h" + str(k) + r", (\\\S+ )\[2:0\] \}\];\n", body, re.M)
        if not m:
            raise SystemExit(f"rf_wrap bank_split: bank {k} read not found")
        rd[k] = m
    base = mem.rstrip()
    new = []
    for k in (0, 1):
        new += [f"  (* keep = 1 *) reg [{w-1}:0] {base}.rf_wd{k} ;",
                f"  always @(negedge {ck}) {base}.rf_wd{k}  <= {data};",
                f"  reg [{w-1}:0] {base}.rf_b{k}  [7:0];",
                f"  always @(posedge {ck}) if ({en} && {'!' if k == 0 else ''}{wa}[3]) {base}.rf_b{k} [{wa}[2:0]] <= {base}.rf_wd{k} ;"]
    body = body[:d.start()] + "\n".join(new) + "\n" + body[b.end():]
    for k in (0, 1):
        m = re.search(re.escape(rd[k].group(0)), body)
        body = body[:m.start()] + f"  assign {rd[k].group(1)} = {base}.rf_b{k} [{rd[k].group(2)}[2:0]];\n" + body[m.end():]
    if re.search(re.escape(mem) + r"\[", body):
        raise SystemExit("rf_wrap bank_split: stray access to the old memory left")
    return body, dict(mem=mem, width=w, banks=2, rows_per_bank=8, added_flops=2 * w,
                      form="per-bank negedge write-data copy, cycle exact")


def transform(text, mod, spec):
    order, decl, at = ports(text, mod)
    clk = "ck" if "ck" in decl else None
    if not clk:
        raise SystemExit("rf_wrap: core clock port ck not found")
    ck = "ck[0]" if decl["ck"][1] else "ck"
    inner = mod + "__rf_core"
    head = text[:at]
    head = re.sub(r"\(\*\s*top\s*=\s*1\s*\*\)\s*\n", "", head)
    head = head.replace(f'hdlname = "{mod}"', f'hdlname = "{inner}"')
    body = re.sub(r"^module\s+" + re.escape(mod) + r"\b", "module " + inner, text[at:], count=1, flags=re.M)
    # a kept inner PORT wire survives flatten as its own net behind a buffer = an extra load on the face net
    # (face_guard 'shared'); the port flops keep their own (* keep *) on the reg cells
    body, nk = re.subn(r"^[ \t]*\(\*\s*keep\s*=\s*32'd1\s*\*\)[ \t]*\n(?=[ \t]*(?:input|output)\b)", "", body,
                       flags=re.M)
    rc = []
    if spec.get("rcopy_bits"):
        body, rc = rcopy(body, int(spec["rcopy_bits"]))
    nmr, bsr = [], None
    if spec.get("negmid"):
        body, nmr = negmid(body, spec["negmid"])
    if spec.get("bank_split"):
        body, bsr = bank_split(body, spec["bank_split"])
    new = head + body
    conn = {p: p for p in order}
    lines, rep = [], dict(resets=[], fwft_reads=[], added_flops=0)
    for r in spec.get("resets", []):
        if r not in decl or decl[r][0] != "input" or width(decl[r][1]) != 1:
            raise SystemExit(f"rf_wrap: reset {r} is not a 1-bit input")
        q = f"rf_rst_q__{r}"
        lines += [f"  (* keep = 1 *) reg {q};",
                  f"  always @(posedge {ck} or negedge {r}[0]) if (!{r}[0]) {q} <= 1'b0; else {q} <= 1'b1;"]
        conn[r] = "{" + q + "}"
        rep["resets"].append(dict(port=r, relay=q, release_added_edges=1)); rep["added_flops"] += 1
    for g in spec.get("fwft_reads", []):
        rd, rdat, remp, rst = g["rd"], g["rdata"], g["rempty"], g["rst"]
        for p, d in ((rd, "input"), (rdat, "output"), (remp, "output"), (rst, "input")):
            if decl.get(p, ("",))[0] != d:
                raise SystemExit(f"rf_wrap: {p} is not an {d}")
        w = width(decl[rdat][1]); rr = conn[rst]
        rr1 = rr.strip("{}") if rr != rst else f"{rst}[0]"
        b = rdat
        lines += [f"  wire [{w-1}:0] rf_i_{b};", f"  wire rf_ie_{b};", f"  wire rf_ird_{b};",
                  f"  reg rf_ov_{b};", f"  (* keep = 1 *) reg [{w-1}:0] rf_od_{b};", f"  (* keep = 1 *) reg [{w-1}:0] rf_oh_{b};",
                  f"  wire rf_ld_{b} = !rf_ie_{b} && (!rf_ov_{b} || {rd}[0]);",
                  f"  assign rf_ird_{b} = rf_ld_{b};",
                  f"  always @(posedge {ck} or negedge {rr1}) if (!{rr1}) rf_ov_{b} <= 1'b0;",
                  f"    else if (rf_ld_{b}) rf_ov_{b} <= 1'b1; else if ({rd}[0]) rf_ov_{b} <= 1'b0;",
                  f"  always @(posedge {ck}) rf_oh_{b} <= rf_ld_{b} ? rf_i_{b} : rf_oh_{b};",
                  f"  always @(posedge {ck}) rf_od_{b} <= rf_ld_{b} ? rf_i_{b} : rf_oh_{b};   // private port bank",
                  # private rempty port flop (= !rf_ov), next state from rf_ov, so its Q loads only the port
                  f"  reg rf_pe_{b};",
                  f"  always @(posedge {ck} or negedge {rr1}) if (!{rr1}) rf_pe_{b} <= 1'b1;",
                  f"    else rf_pe_{b} <= rf_ld_{b} ? 1'b0 : ({rd}[0] ? 1'b1 : !rf_ov_{b});",
                  f"  assign {rdat} = rf_od_{b};", f"  assign {remp} = {{rf_pe_{b}}};"]
        conn[rd] = "{rf_ird_" + b + "}"; conn[rdat] = "rf_i_" + b; conn[remp] = "rf_ie_" + b
        rep["fwft_reads"].append(dict(rd=rd, rdata=rdat, rempty=remp, rst=rst, width=w, read_added_cycles=1,
                                      throughput="1/cycle", rd_face="combinational (stage load enable)"))
        rep["added_flops"] += 2 * w + 2
    hdr = [f"// GENERATED hr_rf_wrap.py (RF-KV1 RE-FORM, DIE-KV-64/RF-C 11-03): {mod} = {inner} + registered reset/read faces",
           "(* top = 1 *)", f"module {mod}({', '.join(order)});"]
    hdr += [f"  {decl[p][0]} {decl[p][1]+' ' if decl[p][1] else ''}{p};" for p in order]
    inst = [f"  {inner} u_rf_core (" + ",\n    ".join(f".{p}({conn[p]})" for p in order) + ");", "endmodule", ""]
    rep["inner_port_keeps_dropped"] = nk
    rep["negmid"] = nmr; rep["bank_split"] = bsr
    rep["added_flops"] += sum(r["added_flops"] for r in nmr) + (bsr["added_flops"] if bsr else 0)
    rep["rcopy"] = rc; rep["added_flops"] += sum(r["added_flops"] for r in rc)
    return new.rstrip() + "\n\n" + "\n".join(hdr + lines + inst), rep


def write_report(kd, rep, spec):
    (kd / "hr_rf_wrap.json").write_text(json.dumps(dict(schema="opentallas.kit_hr_rf_wrap.v1", spec=spec, **rep,
        note="RF-KV1 RE-FORM: reset release +1 edge per relayed reset; FWFT read data +1 cycle; other ports unchanged"),
        indent=1) + "\n")
