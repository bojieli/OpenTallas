#!/usr/bin/env python3
"""DH54-PAD formal coupon checker (runs inside openroad/orfs:asap7lock, flow yosys 0.68+post).

Proves, for a design under test (DUT) against the source recurrence of the 14 HEAD u_wtx pad bits
(ref_model.sv: q_next = (start|owe) ? 0 : q ; o_next = start ? b0 : q ; no reset, no init):

  BIJECTION: the DUT has exactly 28 state bits, one per gold bit (14 hold + 14 output), no init value on any
             of them, all plain posedge-ck flops (no reset); the state map is bitwise (identity or complement),
             hence a bijection between the 2^28 gold and DUT initial states (every gold initial state, incl. all
             2^14 padding states, has exactly one DUT partner and vice versa).
  STEP:      for every gold state s and every input: outputs equal under the map, and next states correspond
             (combinational SAT proof of the transition relation = unbounded 1-step inductive bisimulation).
  IDLE_FOLD: diagnostic: "for every initial state, after one idle cycle (start=0) o==0".  PROVEN means the
             padding state is folded; the gold has a free-state counterexample (state visible).

The checker never edits the DUT. Netlists are read with functional ASAP7 RVT TT Liberty models (the same 5 Libs
the kit synthesis used); RTL is read with proc only (no opt). Each design is flattened, techmapped to yosys gate
primitives, dumped to JSON and re-emitted here as a pure transition function (state in -> next state, outputs).
"""
import argparse, itertools, json, os, re, subprocess

YOSYS = "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys"
LIBDIR = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"
LIBS = ["asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz",
        "asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib",
        "asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz"]
W = 14


def yosys(script, log):
    with open(log + ".ys", "w") as f:
        f.write(script)
    r = subprocess.run([YOSYS, "-q", "-l", log, "-s", log + ".ys"], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def dump_json(kind, files, top, params, out):
    s = []
    if kind == "netlist":
        s += [f"read_liberty -ignore_miss_func {LIBDIR}/{l}" for l in LIBS]
        # yosys' Liberty frontend models ff(IQN,IQNN) as two $_DFF_P_ (IQN and IQNN); no pin reads IQNN, so its flop
        # is a dangling modelling artefact. Clean ONLY the cell models (before the netlist is read) so that one
        # physical DFFHQNx1 = one state bit; the DUT netlist itself is never optimised.
        s += ["opt_clean -purge *"]
        s += [f"read_verilog {f}" for f in files]
    else:
        s += [f"read_verilog -sv {f}" for f in files]
    for k, v in params.items():
        s.append(f"chparam -set {k} {v} {top}")
    s += [f"hierarchy -check -top {top}", "proc", "setattr -mod -unset keep_hierarchy *", "setattr -unset keep_hierarchy *",
          "flatten -noscopeinfo",
          "techmap", f"write_json {out}.json"]
    rc, msg = yosys("\n".join(s) + "\n", out + ".log")
    if rc:
        raise RuntimeError(f"yosys dump failed for {files}: {msg[-2000:]}")
    return json.load(open(out + ".json"))["modules"][top]


COMB = {"$_NOT_": "A", "$_BUF_": "A", "$_AND_": "AB", "$_OR_": "AB", "$_XOR_": "AB", "$_NAND_": "AB",
        "$_NOR_": "AB", "$_XNOR_": "AB", "$_ANDNOT_": "AB", "$_ORNOT_": "AB", "$_MUX_": "ABS", "$_NMUX_": "ABS",
        "$_AOI3_": "ABC", "$_OAI3_": "ABC", "$_AOI4_": "ABCD", "$_OAI4_": "ABCD"}
EXPR = {"$_NOT_": "~{A}", "$_BUF_": "{A}", "$_AND_": "{A}&{B}", "$_OR_": "{A}|{B}", "$_XOR_": "{A}^{B}",
        "$_NAND_": "~({A}&{B})", "$_NOR_": "~({A}|{B})", "$_XNOR_": "~({A}^{B})", "$_ANDNOT_": "{A}&~{B}",
        "$_ORNOT_": "{A}|~{B}", "$_MUX_": "{S}?{B}:{A}", "$_NMUX_": "~({S}?{B}:{A})",
        "$_AOI3_": "~(({A}&{B})|{C})", "$_OAI3_": "~(({A}|{B})&{C})", "$_AOI4_": "~(({A}&{B})|({C}&{D}))",
        "$_OAI4_": "~(({A}|{B})&({C}|{D}))"}

RX_OUT = re.compile(r"(?:^|\.|\\)o\[(\d+)\]")
RX_HOLD = [re.compile(r"state[^\[]*\[(\d+)\]"), re.compile(r"g_pad\[(\d+)\]"), re.compile(r"(?:^|\.|\\)q\[(\d+)\]")]


def analyse(mod, name):
    """Transition-function Verilog text + per-FF info."""
    ports, nn = mod["ports"], mod["netnames"]
    bitnames = {}
    for n, v in nn.items():
        bits = v["bits"]
        init = v.get("attributes", {}).get("init")
        for i, b in enumerate(bits):
            if not isinstance(b, int):
                continue
            label = n if len(bits) == 1 else f"{n}[{i + v.get('offset', 0)}]"
            ib = None
            if init is not None:
                init_s = str(init)
                ib = init_s[len(bits) - 1 - i] if (set(init_s) <= set("01xz") and len(init_s) == len(bits)) else "?"
            bitnames.setdefault(b, []).append((label, ib))
    pin = {p: ports[p]["bits"] for p in ports}
    for p, w in (("ck", 1), ("start", 1), ("owe", 1), ("b0", W), ("o", W)):
        if p not in pin or len(pin[p]) != w:
            raise RuntimeError(f"{name}: port {p} missing/width")
    ffs, comb, issues = [], [], []
    for cn, c in mod["cells"].items():
        t = c["type"]
        if t == "$scopeinfo":
            continue
        if t in COMB:
            comb.append((cn, c))
        elif re.match(r"^\$_(S?DFF|DFFE|DFFSR|ALDFF|DLATCH)", t):
            ffs.append((cn, c))
        else:
            issues.append(f"unsupported cell {cn} {t}")
    if issues:
        raise RuntimeError(f"{name}: " + "; ".join(issues[:5]))

    def sig(b):
        if isinstance(b, int):
            return f"n{b}"
        return {"0": "1'b0", "1": "1'b1"}.get(b, "1'b0")

    ffinfo, lines = [], []
    ck = pin["ck"][0]
    for k, (cn, c) in enumerate(ffs):
        t, con = c["type"], c["connections"]
        if t != "$_DFF_P_":
            raise RuntimeError(f"{name}: state cell {cn} is {t}, not a plain posedge DFF (reset/enable/latch)")
        q, d, clk = con["Q"][0], con["D"][0], con["C"][0]
        labels = [l for l, _ in bitnames.get(q, [])] + [cn]
        inits = [ib for _, ib in bitnames.get(q, []) if ib not in (None, "x", "z")]
        cls = set()
        for l in labels:
            m = RX_OUT.search(l)
            if m:
                cls.add(("out", int(m.group(1))))
                continue
            for rx in RX_HOLD:
                m = rx.search(l)
                if m:
                    cls.add(("hold", int(m.group(1))))
                    break
        ffinfo.append({"cell": cn, "labels": labels[:4], "class": sorted(cls), "init": inits, "clk_ok": clk == ck})
        lines.append(f"  assign n{q} = s[{k}];")
        lines.append(f"  assign sn[{k}] = {sig(d)};")
    for cn, c in comb:
        t, con = c["type"], c["connections"]
        lines.append(f"  assign n{con['Y'][0]} = " + EXPR[t].format(**{p: sig(con[p][0]) for p in COMB[t]}) + ";")
    for p in ("start", "owe"):
        lines.append(f"  assign n{pin[p][0]} = {p};")
    for i, b in enumerate(pin["b0"]):
        lines.append(f"  assign n{b} = b0[{i}];")
    if isinstance(ck, int):
        lines.append(f"  assign n{ck} = 1'b0;  // clock only feeds flop C pins (checked)")
    for i, b in enumerate(pin["o"]):
        lines.append(f"  assign o[{i}] = {sig(b)};")
    used = set()
    for _, c in mod["cells"].items():
        for p, v in c["connections"].items():
            used |= {b for b in v if isinstance(b, int)}
    allbits = sorted(used | {b for v in nn.values() for b in v["bits"] if isinstance(b, int)})
    driven = set(pin["ck"] + pin["start"] + pin["owe"] + pin["b0"]) | {c["connections"]["Y"][0] for _, c in comb} \
        | {c["connections"]["Q"][0] for _, c in ffs}
    undriven = [b for b in used if b not in driven]
    if undriven:
        raise RuntimeError(f"{name}: undriven nets used {undriven[:5]}")
    clk_in_logic = any(ck in c["connections"][p] for _, c in comb for p in COMB[c["type"]])
    if clk_in_logic:
        raise RuntimeError(f"{name}: clock feeds logic")
    n = max(len(ffs), 1)
    v = (f"module {name}(input [{n-1}:0] s, input start, input owe, input [{W-1}:0] b0,\n"
         f"  output [{n-1}:0] sn, output [{W-1}:0] o);\n" + "\n".join(f"  wire n{b};" for b in allbits) + "\n"
         + "\n".join(lines) + "\nendmodule\n")
    return v, ffinfo


def classify(ffinfo):
    m, bad = {}, []
    for k, f in enumerate(ffinfo):
        if len(f["class"]) != 1:
            bad.append(f"ff {f['cell']} class {f['class']}")
            continue
        key = tuple(f["class"][0])
        if key in m:
            bad.append(f"duplicate {key}")
        m[key] = k
    return m, bad


def sat(trv, fn, top, log):
    rc, _ = yosys(f"read_verilog {trv}\nread_verilog {fn}\nhierarchy -top {top}\nflatten\n"
                  f"sat -prove ok 1 -verify -show-inputs {top}\n", log)
    return rc == 0


def check(kind, files, top, params, outdir, tag, ref):
    os.makedirs(outdir, exist_ok=True)
    res = {"tag": tag, "dut_kind": kind, "dut_files": files, "dut_top": top, "dut_params": params}
    gv, gff = analyse(dump_json("rtl", [ref], "pad_ref", {}, f"{outdir}/{tag}.gold"), "gold_tr")
    dv, dff = analyse(dump_json(kind, files, top, params, f"{outdir}/{tag}.dut"), "dut_tr")
    gmap, gbad = classify(gff)
    assert not gbad and len(gmap) == 2 * W, (gbad, len(gmap))
    dmap, dbad = classify(dff)
    res.update(dut_ff_total=len(dff), dut_hold_ff=sum(k[0] == "hold" for k in dmap),
               dut_out_ff=sum(k[0] == "out" for k in dmap), dut_ff_inits=sum(bool(f["init"]) for f in dff),
               dut_ff_clk_bad=sum(not f["clk_ok"] for f in dff), classify_issues=dbad)
    complete = not dbad and len(dff) == 2 * W and set(dmap) == set(gmap)
    res["bijection_structural"] = bool(complete and res["dut_ff_inits"] == 0 and res["dut_ff_clk_bad"] == 0)
    trv = f"{outdir}/{tag}.tr.v"
    open(trv, "w").write(gv + "\n" + dv)
    idle = {}
    for which, mod, n in (("dut", "dut_tr", max(len(dff), 1)), ("gold", "gold_tr", 2 * W)):
        v = (f"module idle_{which}(input [{n-1}:0] s, input owe1, input start2, input owe2, input [{W-1}:0] b1,"
             f" input [{W-1}:0] b2, output ok);\n  wire [{n-1}:0] s1, s2; wire [{W-1}:0] o0, o1;\n"
             f"  {mod} a(.s(s), .start(1'b0), .owe(owe1), .b0(b1), .sn(s1), .o(o0));\n"
             f"  {mod} b(.s(s1), .start(start2), .owe(owe2), .b0(b2), .sn(s2), .o(o1));\n"
             f"  assign ok = (o1 == {W}'b0);\nendmodule\n")
        fn = f"{outdir}/{tag}.idle_{which}.v"
        open(fn, "w").write(v)
        idle[which] = "PROVEN_FOLDED" if sat(trv, fn, f"idle_{which}", fn[:-2] + ".log") else "CEX_STATE_VISIBLE"
    res["idle_fold"] = idle
    res["step"], passed = {}, []
    if complete:
        gs = [None] * (2 * W)
        for (cls, i), k in gmap.items():
            gs[k] = f"gq[{i}]" if cls == "hold" else f"go[{i}]"
        for ph, po in itertools.product((0, 1), (0, 1)):
            asg = []
            for (cls, i), k in sorted(dmap.items(), key=lambda x: x[1]):
                pol = "~" if (ph if cls == "hold" else po) else ""
                asg.append(f"  assign ds[{k}] = {pol}{'gq' if cls == 'hold' else 'go'}[{i}];")
                asg.append(f"  assign ex[{k}] = {pol}gsn[{gmap[(cls, i)]}];")
            v = (f"module step(input [{W-1}:0] gq, input [{W-1}:0] go, input start, input owe, input [{W-1}:0] b0,"
                 f" output ok);\n  wire [{2*W-1}:0] gst = {{{', '.join(reversed(gs))}}};\n"
                 f"  wire [{2*W-1}:0] gsn, ds, dsn, ex; wire [{W-1}:0] og, od;\n"
                 f"  gold_tr g(.s(gst), .start(start), .owe(owe), .b0(b0), .sn(gsn), .o(og));\n"
                 f"  dut_tr d(.s(ds), .start(start), .owe(owe), .b0(b0), .sn(dsn), .o(od));\n" + "\n".join(asg) +
                 "\n  assign ok = (og == od) && (dsn == ex);\nendmodule\n")
            key = f"hold_pol{ph}_out_pol{po}"
            fn = f"{outdir}/{tag}.step_{key}.v"
            open(fn, "w").write(v)
            ok = sat(trv, fn, "step", fn[:-2] + ".log")
            res["step"][key] = "PROVEN" if ok else "FAIL"
            if ok:
                passed.append(key)
    res["step_passing_maps"] = passed
    res["verdict"] = "PRESERVED_BIT_EXACT" if (res["bijection_structural"] and passed) else "REJECTED"
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["netlist", "rtl"], required=True)
    ap.add_argument("--top", required=True)
    ap.add_argument("--param", action="append", default=[])
    ap.add_argument("--ref", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    try:
        r = check(a.kind, a.files, a.top, dict(p.split("=", 1) for p in a.param), a.outdir, a.tag, a.ref)
    except RuntimeError as e:  # structural rejection (e.g. reset/enable flop, unsupported cell) is a REJECT
        r = {"tag": a.tag, "verdict": "REJECTED", "structural_error": str(e)}
    json.dump(r, open(f"{a.outdir}/{a.tag}.formal.json", "w"), indent=1)
    print(json.dumps({k: r.get(k) for k in ("tag", "dut_ff_total", "dut_hold_ff", "dut_out_ff", "dut_ff_inits",
                                             "bijection_structural", "idle_fold", "step", "verdict",
                                             "structural_error")}))
