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
  * queue slices (spec key "queue_slices"): a 2-bank flop queue (q[{b, rp[2:0]}] -> r0/r1 on issue, out = bank ? r1 : r0)
    is cut into B-bit column slices; each slice owns kept copies of every control it uses (wp/rp/bank copies loaded
    with the same next state, negedge copies of take/issue and of the write data per bank), so no control or data
    net fans out past one slice (bounded fanout by construction, cycle exact).
  * registered write face (spec key "out_slice", DIE-KV-64/RF-E 11-03): a valid/ready write port leaves from
    private port flop banks through a one-entry slice (+1 write latency, 1/cycle); done/tag/count held until the
    descriptor's last sector left the slice; busy covers the slice and pending done (see out_slice()).
  * exact logic rewrites (spec key "rewrite": [{"find", "replace", "add", "why"}]): a next-state expression replaced
    by a Boolean-identical shallower form (each needs its identity argument in "why" and a 0-mismatch co-simulation).
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


def _cut(body, txt, what):
    if body.count(txt) != 1:
        raise SystemExit(f"rf_wrap queue_slices: {what} found {body.count(txt)}x")
    return body.replace(txt, "")


def queue_slices(body, sp, ck="ck"):
    mem, data, take, wp, rp, issue = sp["mem"], sp["data"], sp["en"], sp["wa"], sp["ra"], sp["rd_en"]
    r0, r1, bank, osel, wpn, rpn, rst = sp["r0"], sp["r1"], sp["bank"], sp["out_sel"], sp["wa_next"], sp["ra_next"], sp["rst"]
    B = int(sp.get("slice_bits", 32))
    d = re.search(r"^(?:  \(\*[^\n]*\*\)\n)?  reg \[(\d+):0\] " + re.escape(mem) + r" \[15:0\];\n", body, re.M)
    if not d:
        raise SystemExit("rf_wrap queue_slices: memory declaration not found")
    w = int(d.group(1)) + 1
    blk = re.compile(r"^  always @\(posedge " + ck + r"\) begin\n(?:    if \(\w+\[\d+\]\)\n      " + re.escape(mem) +
                     r"\[\w+\]\[\d+:\d+\] <= \w+\[\d+\];\n)+  end\n", re.M)
    b = blk.search(body, d.end())
    if not b or b.start() != d.end() or b.group(0).count(" <= ") != w:
        raise SystemExit("rf_wrap queue_slices: per-bit write block not found right after the declaration")
    body = body[:d.start()] + body[b.end():]
    rd = {}
    for k in (0, 1):
        m = re.search(r"^  assign (\w+) = " + re.escape(mem) + r"\[\{ 1'h" + str(k) + r", " + re.escape(rp) + r"\[2:0\] \}\];\n", body, re.M)
        if not m:
            raise SystemExit(f"rf_wrap queue_slices: bank {k} read not found")
        rd[k] = m.group(1); body = _cut(body, m.group(0), f"bank {k} read")
    for k, r in ((0, r0), (1, r1)):
        m = re.search(r"^  assign (\w+) = " + re.escape(issue) + r" \? " + rd[k] + " : " + re.escape(r) + r";\n", body, re.M)
        if not m:
            raise SystemExit(f"rf_wrap queue_slices: {r} load mux not found")
        body = _cut(body, m.group(0), f"{r} mux")
        body = _cut(body, f"  always @(posedge {ck})\n    {r} <= {m.group(1)};\n", f"{r} register")
    body = _cut(body, f"  assign {osel}[{w-1}:0] = {bank} ? {r1} : {r0};\n", "output select")
    if re.search(re.escape(mem) + r"\[", body):
        raise SystemExit("rf_wrap queue_slices: stray access to the old memory left")
    base = mem.rstrip(); L = []
    ns = -(-w // B)
    for c in range(ns):
        lo, hi = c * B, min(w, (c + 1) * B) - 1; n = hi - lo + 1; t = f"{base}.rf_s{c}_"
        L += [f"  (* keep = 1 *) reg [3:0] {t}wp ;", f"  (* keep = 1 *) reg [2:0] {t}rp ;", f"  (* keep = 1 *) reg {t}bk ;",
              f"  always @(posedge {ck}, negedge {rst}) if (!{rst}) begin {t}wp  <= 4'h0; {t}rp  <= 3'h0; {t}bk  <= 1'h0; end",
              f"    else begin {t}wp  <= {wpn}; {t}rp  <= {rpn}[2:0]; {t}bk  <= {rp}[3]; end",
              f"  (* keep = 1 *) reg {t}tk ;", f"  (* keep = 1 *) reg {t}is ;",
              f"  (* keep = 1 *) reg [{n-1}:0] {t}wd0 ;", f"  (* keep = 1 *) reg [{n-1}:0] {t}wd1 ;",
              f"  always @(negedge {ck}) begin {t}tk  <= {take}; {t}is  <= {issue}; {t}wd0  <= {data}[{hi}:{lo}]; {t}wd1  <= {data}[{hi}:{lo}]; end",
              f"  reg [{n-1}:0] {t}m0  [7:0];", f"  reg [{n-1}:0] {t}m1  [7:0];",
              f"  always @(posedge {ck}) if ({t}tk  && {rst} && !{t}wp [3]) {t}m0 [{t}wp [2:0]] <= {t}wd0 ;",
              f"  always @(posedge {ck}) if ({t}tk  && {rst} && {t}wp [3]) {t}m1 [{t}wp [2:0]] <= {t}wd1 ;",
              f"  always @(posedge {ck}) if ({t}is  && {rst}) begin {r0}[{hi}:{lo}] <= {t}m0 [{t}rp ]; {r1}[{hi}:{lo}] <= {t}m1 [{t}rp ]; end",
              f"  assign {osel}[{hi}:{lo}] = {t}bk  ? {r1}[{hi}:{lo}] : {r0}[{hi}:{lo}];"]
    body = body.rstrip(); assert body.endswith("endmodule")
    body = body[:-len("endmodule")] + "\n".join(L) + "\nendmodule\n"
    return body, dict(mem=mem, width=w, slices=ns, slice_bits=B, added_flops=ns * (3 + 3 + 1 + 2) + 2 * w,
                      form="column slices with per-slice kept control copies, negedge take/issue/write-data copies")



def skid_slices(body, sp, ck="ck"):
    """column-slice each skid FIFO memory sm[D][W] with per-slice kept copies of its write address/valid and read
    pointer (equivalent: every copy has the source reg's reset and next state; write = swv ? sm[swa] <= swd)"""
    B = int(sp.get("slice_bits", 64)); rep = []
    for i in sp["fifos"]:
        ie = re.escape(i)
        d = re.search(r"^(?:  \(\*[^\n]*\*\)\n)?  reg \[(\d+):0\] \\" + ie + r"\.sm  \[(\d+):0\];\n", body, re.M)
        if not d:
            raise SystemExit(f"rf_wrap skid_slices: {i}.sm decl not found")
        w, dp = int(d.group(1)) + 1, int(d.group(2)) + 1
        blk = re.compile(r"  always @\(posedge " + re.escape(ck) + r"\) begin\n(?:    if \((\w+)\[(\d+)\]\)\n      \\" + ie +
                         r"\.sm \[(\w+)\]\[\2:\2\] <= (\w+)\[\2\];\n)+  end\n")
        b = blk.match(body, d.end())
        if not b or b.group(0).count(" <= ") != w:
            raise SystemExit(f"rf_wrap skid_slices: {i}.sm per-bit write block not found")
        en, ad, dat = b.group(1), b.group(3), b.group(4)
        for sig, src in ((ad, "swa"), (dat, "swd"), (en, None)):
            m = re.search(r"^  assign " + sig + r" = \\" + ie + r"\.swv  \? \(\* full_case = 32'd1 \*\) (\S+(?: )?) : (\S+);\n", body, re.M)
            if not m:
                raise SystemExit(f"rf_wrap skid_slices: {sig} not swv-gated")
            if src and m.group(1).strip() != f"\\{i}.{src}":
                raise SystemExit(f"rf_wrap skid_slices: {sig} = {m.group(1)} not {src}")
            if src is None and (set(m.group(1).split("'h")[1]) - set("3f") or set(m.group(2).split("'h")[1]) != {"0"}):
                raise SystemExit(f"rf_wrap skid_slices: {sig} not ones/zeros")
        rd = re.search(r"^  assign (\S+) = \\" + ie + r"\.sm \[\\" + ie + r"\.srp \[(\d+):0\]\];\n", body, re.M)
        if not rd:
            raise SystemExit(f"rf_wrap skid_slices: {i}.sm read not found")
        x, ra = rd.group(1), int(rd.group(2)) + 1
        def nxt(r):
            m = re.search(r"  always @\(posedge " + re.escape(ck) + r", negedge ([^)]+)\)\n\s*if \(!\1\) \\" + ie + r"\." + r +
                          r"  <= \S+;\n\s*else \\" + ie + r"\." + r + r"  <= (\S+(?: )?);\n", body)
            if not m:
                raise SystemExit(f"rf_wrap skid_slices: {i}.{r} reset/next block not found")
            return m.group(1), m.group(2)
        (rst, wan), (_, wvn), (_, rpn) = nxt("swa"), nxt("swv"), nxt("srp")
        wa = re.search(r"reg \[(\d+):0\] \\" + ie + r"\.swa ;", body); aw = int(wa.group(1)) + 1
        body = body[:d.start()] + body[b.end():]
        body = body.replace(rd.group(0), "", 1)
        L = []; ns = -(-w // B)
        for c in range(ns):
            lo, hi = c * B, min(w, (c + 1) * B) - 1; n = hi - lo + 1; t = f"\\{i}.rf_k{c}_"
            L += [f"  (* keep = 1 *) reg [{aw-1}:0] {t}wa ;", f"  (* keep = 1 *) reg {t}wv ;", f"  (* keep = 1 *) reg [{ra-1}:0] {t}rp ;",
                  f"  always @(posedge {ck}, negedge {rst}) if (!{rst}) begin {t}wa  <= {aw}'h0; {t}wv  <= 1'h0; {t}rp  <= {ra}'h0; end",
                  f"    else begin {t}wa  <= {wan}; {t}wv  <= {wvn}; {t}rp  <= {rpn}[{ra-1}:0]; end",
                  f"  reg [{n-1}:0] {t}m  [{dp-1}:0];",
                  f"  always @(posedge {ck}) if ({t}wv ) {t}m [{t}wa ] <= \\{i}.swd [{hi}:{lo}];",
                  f"  assign {x}[{hi}:{lo}] = {t}m [{t}rp ];"]
        body = body.rstrip(); assert body.endswith("endmodule")
        body = body[:-len("endmodule")] + "\n".join(L) + "\nendmodule\n"
        rep.append(dict(fifo=i, width=w, depth=dp, slices=ns, slice_bits=B, added_flops=ns * (aw + 1 + ra),
                        form="column slices with per-slice kept write-address/valid and read-pointer copies"))
    return body, rep


def out_slice(decl, conn, sp, ck, gates):
    """registered write face (spec key "out_slice": {"v", "rdy", "data": [bus..], "done": {"v", "tag", "cnt"},
    "busy", "rst"}): a one-entry forward-registered slice between the core's valid/ready write port and the port
    (throughput 1/cycle, +1 write latency).  w_v / data come from private port flop banks (od, loaded from the core or
    from the hold bank oh), so each port flop Q loads only its port; the core sees rdy' = !occupied | rdy.
    done (v/tag/cnt) is held in a 2-deep queue until the slice no longer holds that descriptor's last sector
    (released when the slice is empty or transferring), then leaves from registered port flops one edge later:
    every done still follows its last sector at the port (the engine contract); tag and count are the core's values
    captured with the done.  busy = core busy | slice occupied | done pending, so busy stays high until the done left."""
    v, rdy, rst = sp["v"], sp["rdy"], sp["rst"]
    for p, d in ((v, "output"), (rdy, "input"), (rst, "input")):
        if decl.get(p, ("",))[0] != d or width(decl[p][1]) != 1:
            raise SystemExit(f"rf_wrap out_slice: {p} is not a 1-bit {d}")
    rr = conn[rst]; rr1 = rr.strip("{}") if rr != rst else f"{rst}[0]"
    L = [f"  wire rf_cwv; reg rf_ov; reg rf_pv;",
         f"  wire rf_cwrdy = !rf_ov || {rdy}[0];",
         f"  wire rf_ld = rf_cwv && rf_cwrdy;",
         f"  always @(posedge {ck} or negedge {rr1}) if (!{rr1}) begin rf_ov <= 1'b0; rf_pv <= 1'b0; end",
         f"    else begin rf_ov <= rf_ld ? 1'b1 : ({rdy}[0] ? 1'b0 : rf_ov); rf_pv <= rf_ld ? 1'b1 : ({rdy}[0] ? 1'b0 : rf_ov); end",
         f"  assign {v} = {{rf_pv}};"]
    conn[v] = "{rf_cwv}"; conn[rdy] = "{rf_cwrdy}"
    added = 2; buses = []
    for b in sp["data"]:
        if decl.get(b, ("",))[0] != "output":
            raise SystemExit(f"rf_wrap out_slice: {b} is not an output")
        w = width(decl[b][1])
        L += [f"  wire [{w-1}:0] rf_c_{b};", f"  (* keep = 1 *) reg [{w-1}:0] rf_od_{b};",
              f"  (* keep = 1 *) reg [{w-1}:0] rf_oh_{b};",
              f"  always @(posedge {ck}) rf_oh_{b} <= rf_ld ? rf_c_{b} : rf_oh_{b};",
              f"  always @(posedge {ck}) rf_od_{b} <= rf_ld ? rf_c_{b} : rf_oh_{b};   // private port bank",
              f"  assign {b} = rf_od_{b};"]
        conn[b] = f"rf_c_{b}"; added += 2 * w; buses.append(dict(bus=b, width=w))
    dn = sp.get("done")
    if dn:
        dv, tg, cn = dn["v"], dn["tag"], dn["cnt"]
        wt, wc = width(decl[tg][1]), width(decl[cn][1])
        for p in (dv, tg, cn):
            if decl.get(p, ("",))[0] != "output":
                raise SystemExit(f"rf_wrap out_slice: done port {p} is not an output")
        D = int(dn.get("depth", 2)); la = max(1, (D - 1).bit_length())
        if D < 2 or D & (D - 1):
            raise SystemExit("rf_wrap out_slice: done depth must be a power of two >= 2")
        L += [f"  wire rf_cdv; wire [{wt-1}:0] rf_ctg; wire [{wc-1}:0] rf_ccn;",
              f"  reg [{wt-1}:0] rf_qtg [0:{D-1}]; reg [{wc-1}:0] rf_qcn [0:{D-1}]; reg [{la}:0] rf_qn; reg [{la-1}:0] rf_qw, rf_qr;",
              f"  wire rf_rel = (rf_qn != 0) && (!rf_ov || {rdy}[0]);",
              f"  always @(posedge {ck} or negedge {rr1}) if (!{rr1}) begin rf_qn <= 0; rf_qw <= 0; rf_qr <= 0; end",
              f"    else begin rf_qn <= rf_qn + (rf_cdv ? 1'b1 : 1'b0) - (rf_rel ? 1'b1 : 1'b0);",
              f"      if (rf_cdv) rf_qw <= rf_qw + 1'b1; if (rf_rel) rf_qr <= rf_qr + 1'b1; end",
              f"  always @(posedge {ck}) if (rf_cdv) begin rf_qtg[rf_qw] <= rf_ctg; rf_qcn[rf_qw] <= rf_ccn; end",
              f"  reg rf_dv, rf_dvi; (* keep = 1 *) reg [{wt-1}:0] rf_dtg; (* keep = 1 *) reg [{wc-1}:0] rf_dcn;",
              f"  always @(posedge {ck} or negedge {rr1}) if (!{rr1}) begin rf_dv <= 1'b0; rf_dvi <= 1'b0; end",
              f"    else begin rf_dv <= rf_rel; rf_dvi <= rf_rel; end",
              # tag / count ports: the head entry, loaded every edge (the parent samples them with done_v only)
              f"  always @(posedge {ck}) begin rf_dtg <= rf_qtg[rf_qr]; rf_dcn <= rf_qcn[rf_qr]; end",
              f"  assign {dv} = {{rf_dv}}; assign {tg} = rf_dtg; assign {cn} = rf_dcn;"]
        conn[dv] = "{rf_cdv}"; conn[tg] = "rf_ctg"; conn[cn] = "rf_ccn"
        added += (la + 1) + 2 * la + D * (wt + wc) + 2 + wt + wc
        g = dn.get("gate")
        if g:
            # bound the done queue (DIE-KV-64/RF-E): only a fenced descriptor yields a done, so the wrapper counts the
            # fenced descriptors accepted whose done the core has not produced yet (rf_fo; cleared whenever the core
            # is idle, so a fenced descriptor that ends without a done cannot leak) and admits no descriptor while
            # rf_fo + pending dones >= depth: pending dones never exceed the queue depth (by construction).
            gv, gr, fb = g["v"], g["rdy"], g["fence_bit"]
            fbus = re.sub(r"\[\d+\]$", "", fb)
            if decl.get(fbus, ("",))[0] != "input":
                raise SystemExit(f"rf_wrap out_slice: fence bit {fb} is not an input bit")
            L += [f"  wire rf_cbusy_g; reg [{la+1}:0] rf_fo;",
                  f"  wire rf_dacc = {gv}[0] && !rf_hold_{gr} && rf_crdy_{gr};",
                  f"  always @(posedge {ck} or negedge {rr1}) if (!{rr1}) rf_fo <= 0;",
                  f"    else rf_fo <= (rf_cbusy_g ? rf_fo - ((rf_cdv && rf_fo != 0) ? 1'b1 : 1'b0) : 0) + ((rf_dacc && {fb}) ? 1'b1 : 1'b0);",
                  f"  wire rf_dhold = ({{1'b0, rf_fo}} + rf_qn) >= {D};"]
            gates.setdefault((gv, gr), []).append("rf_dhold")
            added += la + 2
    bz = sp.get("busy")
    if bz:
        if decl.get(bz, ("",))[0] != "output" or width(decl[bz][1]) != 1:
            raise SystemExit(f"rf_wrap out_slice: busy {bz} is not a 1-bit output")
        L += [f"  wire rf_cbusy;", f"  assign rf_cbusy_g = rf_cbusy;" if dn and dn.get("gate") else "",
              f"  assign {bz} = {{rf_cbusy || rf_ov{' || (rf_qn != 0) || rf_dvi' if dn else ''}}};"]
        conn[bz] = "{rf_cbusy}"
    return L, dict(v=v, rdy=rdy, data=buses, done=bool(dn), busy=bz, write_added_cycles=1, done_added_cycles="1..2 (held until its last sector left the slice)",
                   throughput="1/cycle", rdy_face="combinational (timed face: slice load enable)", added_flops=added)


def inline_alias(body):
    """replace every whole-vector alias wire `wire [n:0] _N_ = \\reg ;` by the reg itself (pure rename): yosys
    otherwise names the flop after the alias and LEC cannot pair it with the gold register"""
    rep = []
    for m in list(re.finditer(r"^  wire \[(\d+):0\] (_\d+_) = (\\\S+ );\n", body, re.M)):
        a, r = m.group(2), m.group(3)
        if not re.search(r"^  reg \[" + m.group(1) + r":0\] " + re.escape(r) + r";", body, re.M):
            continue
        body = body.replace(m.group(0), "", 1)
        body, n = re.subn(r"(?<![\w\\$])" + re.escape(a) + r"(?!\w)", lambda _m: r, body)
        rep.append(dict(alias=a, reg=r.strip(), uses=n))
    return body, rep

def rewrite(body, items):
    rep = []
    for it in items:
        f = it["find"]
        if body.count(f) != 1:
            raise SystemExit(f"rf_wrap rewrite: {f[:60]!r} found {body.count(f)}x")
        at = body.index(f); a = body.rfind("\n  always", 0, at) + 1
        body = body[:a] + it.get("add", "") + body[a:].replace(f, it["replace"], 1)
        rep.append(dict(find=f, why=it.get("why", "")))
    return body, rep


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
    iar = []
    if spec.get("inline_alias"):
        body, iar = inline_alias(body)
    rc = []
    if spec.get("rcopy_bits"):
        body, rc = rcopy(body, int(spec["rcopy_bits"]))
    nmr, bsr = [], None
    rwr = []
    if spec.get("rewrite"):
        body, rwr = rewrite(body, spec["rewrite"])
    if spec.get("negmid"):
        body, nmr = negmid(body, spec["negmid"])
    if spec.get("queue_slices"):
        body, bsr = queue_slices(body, spec["queue_slices"])
    if spec.get("bank_split"):
        body, bsr = bank_split(body, spec["bank_split"])
    ssr = []
    if spec.get("skid_slices"):
        body, ssr = skid_slices(body, spec["skid_slices"])
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
    rep["out_slice"] = None; gates = {}
    if spec.get("out_slice"):
        osl, rep["out_slice"] = out_slice(decl, conn, spec["out_slice"], ck, gates)
        g = (spec["out_slice"].get("done") or {}).get("gate")
        if g:   # declared before the slice logic that reads them
            lines += [f"  wire rf_crdy_{g['rdy']}; wire rf_hold_{g['rdy']};"]
        lines += osl; rep["added_flops"] += rep["out_slice"]["added_flops"]
    for hp in spec.get("reset_hold", []):
        # an input handshake of a relayed-reset core: the port ready is low (and the core sees no valid) until the
        # core's reset relay released, so nothing is accepted on the edge the parent leaves reset (+1 edge)
        q = conn[hp["rst"]].strip("{}")
        if not q.startswith("rf_rst_q__"):
            raise SystemExit(f"rf_wrap reset_hold: {hp['rst']} is not a relayed reset")
        gates.setdefault((hp["v"], hp["rdy"]), []).append("!" + q)
    for (gv, gr), terms in gates.items():
        for p, d in ((gv, "input"), (gr, "output")):
            if decl.get(p, ("",))[0] != d or width(decl[p][1]) != 1 or conn[p] != p:
                raise SystemExit(f"rf_wrap gate: {p} is not a free 1-bit {d}")
        hold = " || ".join(terms)
        pre = f"  wire rf_crdy_{gr}; wire rf_hold_{gr};" in lines
        lines += ([] if pre else [f"  wire rf_crdy_{gr}; wire rf_hold_{gr};"]) + \
            [f"  assign rf_hold_{gr} = {hold};", f"  assign {gr} = {{rf_crdy_{gr} && !rf_hold_{gr}}};"]
        conn[gv] = f"{{{gv}[0] && !rf_hold_{gr}}}"; conn[gr] = f"{{rf_crdy_{gr}}}"
    rep["input_gates"] = {f"{v}/{r}": t for (v, r), t in gates.items()}
    hdr = [f"// GENERATED hr_rf_wrap.py (RF-KV1 RE-FORM, DIE-KV-64/RF-C 11-03): {mod} = {inner} + registered reset/read faces",
           "(* top = 1 *)", f"module {mod}({', '.join(order)});"]
    hdr += [f"  {decl[p][0]} {decl[p][1]+' ' if decl[p][1] else ''}{p};" for p in order]
    inst = [f"  {inner} u_rf_core (" + ",\n    ".join(f".{p}({conn[p]})" for p in order) + ");", "endmodule", ""]
    rep["inner_port_keeps_dropped"] = nk
    rep["rewrite"] = rwr; rep["negmid"] = nmr; rep["bank_split"] = bsr; rep["skid_slices"] = ssr; rep["inline_alias"] = iar
    rep["added_flops"] += sum(r["added_flops"] for r in ssr)
    rep["added_flops"] += sum(r["added_flops"] for r in nmr) + (bsr["added_flops"] if bsr else 0)
    rep["rcopy"] = rc; rep["added_flops"] += sum(r["added_flops"] for r in rc)
    return new.rstrip() + "\n\n" + "\n".join(hdr + lines + inst), rep


def write_report(kd, rep, spec):
    (kd / "hr_rf_wrap.json").write_text(json.dumps(dict(schema="opentallas.kit_hr_rf_wrap.v1", spec=spec, **rep,
        note="RF-KV1 RE-FORM: reset release +1 edge per relayed reset; FWFT read data +1 cycle; other ports unchanged"),
        indent=1) + "\n")
