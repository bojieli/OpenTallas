#!/usr/bin/env python3
"""RTL-vs-RTL equivalence of the qxpq_w10 clock-gate change (S81-CORE-LAT/QX 2026-10-26): CGR = 8 vs the single-gate RTL.

    python3 tools/dsrom_qelem_cl/qxpq_cgr_lec.py GATE_ROOT GOLD_ROOT OUT [--yosys Y] [--top T] [--gold-top T]
        [--gate-param K=V ... | --gate-param none]   (S81-QX-GB 2026-10-26: other masters, e.g. the _gb top at CGR default)
        GATE_ROOT: tree with the new rtl/ (elaborated with CGR = 8);  GOLD_ROOT: tree with the reference rtl/ (CGR absent/0)
        exit 0 EQUIVALENT, 1 transform refused, 2 UNPROVEN (equiv_* left compare points), 3 tool error;  OUT/lec_cgr.json = verdict

Why a separate flow: tools/die_plan/lec.py stops UNPROVEN on any ICG (clock gates are not modelled) and this change
moves ONLY clock nets: every flop keeps its next-state function, its clock moves from gclk (= ICG(clk, u_z)) to
gclk_r[k] (= ICG(clk, u_ze_r<k>)).  Method = the standard clock-gate abstraction of commercial LEC:
  1. both designs: read_verilog -sv -DSYNTHESIS (die parameters of the kit spec, gate also CGR = 8), ot_hdc_cg and the
     ROM macros as black boxes, keep_hierarchy removed, proc, flatten, memory_map, opt_clean (no merging passes);
  2. clock-gate -> enable (this script, identical on both sides): every flop clocked by an ot_hdc_cg output becomes a
     flop on the gate's clk with enable = the gate's en (AND-ed with its own enable if it had one) -- exact for the
     latch-based ICG (an edge on gclk at a clk edge iff en held during the preceding low phase = the enable register's
     value); every ROM macro clocked by a gate gets clk = the gate's clk and ce_in AND en (read iff edge and ce);
     anything else on a gate output (logic, ports) is refused (exit 1);
  3. Yosys equiv_make gold gate; async2sync; equiv_struct; equiv_simple -seq 2; equiv_induct -seq 2; equiv_status
     -assert.  The 8 kept enable copies u_ze_r<k> have no gold counterpart: they are proved through their (matched)
     next state qz_zd and reset by the sequential steps.  Compare points: every primary output, every matched flop,
     every ROM black-box input pin.
  --merge-enables (gate side, before step 2): the 8 copies u_ze_r<k> are proved STRUCTURALLY identical to u_z (same
     cell type, clock, async reset, reset value, D bits) and merged into it. Every FF bit is then retained as a
     named state point and true primary/ROM ports are preserved; dead/combinational wire aliases are not proof cuts.
     Forward RTL-cell structural merging plus induction proves the normalized design. Clock edge/reset parameters,
     corresponding clock connections and defined initial values are checked before normalization.
"""
import argparse, json, os, subprocess, sys, time
PARAMS = dict(MTP=1, EARLY=1, NB=2, FAST=1, PP=1, QTIMING_FIX=1, QPIPE=1, QP_XS=1, QP_CAP=0, QP_P1=1, QP_CSAM=10, QZ=1,
              QZ_NS=8, QZ_NE=4, QY=1, QX=10, PQ=1, QW=0, QM=5, QS=5, RSTP=1)
TOP = "ot_v41_rom_elem_q_qxpq_w10"
SRC = """rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv rtl/v41rom/ot_v41_elem_pq_tags.sv
rtl/v41rom/ot_v41_kreg.sv rtl/v41rom/ot_v41_chain3.sv rtl/v41rom/ot_v41_chain4.sv rtl/v41rom/ot_v41_fadd2.sv
rtl/v41rom/ot_v41_rom_elem_w10.sv rtl/v41rom/ot_v41_bterm.sv rtl/v41rom/ot_v41_chain.sv rtl/v41rom/ot_v41_segtree.sv
rtl/v41rom/ot_v41_bf16_lanes.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_delay.sv
rtl/proto/ot_fp32_add_rne_pipe.sv rtl/v41rom/ot_v41_fadd.sv rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_bterm2_w10.sv
rtl/v41rom/ot_v41_chain2.sv rtl/v41rom/ot_v41_segtree2.sv rtl/v41rom/ot_v41_bf16_lanes2.sv rtl/v41rom/ot_v41_bterm3_w10.sv
rtl/v41rom/ot_v41_bterm4_w10.sv rtl/v41rom/ot_v41_bterm5_w10.sv rtl/v41rom/ot_v41_segtree3.sv rtl/v41rom/ot_v41_segtree4.sv
rtl/v41rom/ot_v41_segtree5.sv rtl/v41rom/ot_v41_segtree6.sv""".split()
BB = """(* blackbox *) module ot_hdc_cg (input wire clk, input wire en, output wire gclk); endmodule
(* blackbox *) module ot_rom_4096x274_m8 #(parameter VIAMAP = "", parameter INSTANCE = "") (input wire clk, input wire ce_in,
  input wire [11:0] addr_in, output wire [273:0] rd_out); endmodule
(* blackbox *) module ot_rom_8192x274_m8 #(parameter VIAMAP = "", parameter INSTANCE = "") (input wire clk, input wire ce_in,
  input wire [12:0] addr_in, output wire [273:0] rd_out); endmodule
"""


def srcs(top):
    """SRC with the top file swapped for rtl/v41rom/<top>.sv (S81-QX-GB 2026-10-26: --top / --gold-top, e.g. the _gb master)"""
    return [f"rtl/v41rom/{top}.sv"] + SRC[1:]


def elab(y, root, out, name, extra, top=TOP):
    files = " ".join(os.path.join(root, f) for f in srcs(top))
    ch = " ".join(f"-chparam {k} {v}" for k, v in {**PARAMS, **extra}.items())
    js = os.path.join(out, name + ".elab.json")
    scr = (f"read_verilog -sv -DSYNTHESIS {files} {out}/lec_bb.v; hierarchy -top {top} {ch}; "
           f"setattr -mod -unset keep_hierarchy; proc; flatten; memory_map; opt_clean; stat; write_json {js}")
    r = subprocess.run([y, "-q", "-l", os.path.join(out, name + ".elab.log"), "-p", scr])
    if r.returncode:
        sys.exit(f"tool error: elaboration {name} rc {r.returncode}")
    return js


def cg_to_enable(js, name, out, merge_enables=False):
    d = json.load(open(js))
    tops = [k for k, v in d["modules"].items() if v.get("attributes", {}).get("top")]
    m = d["modules"][tops[0]]
    nxt = [1 + max(b for n in m["netnames"].values() for b in n["bits"] if isinstance(b, int))]

    def newbit(nm):
        b = nxt[0]; nxt[0] += 1
        m["netnames"][nm] = {"hide_name": 0, "bits": [b], "attributes": {}}
        return b

    def and2(nm, a, b):
        y = newbit(nm + ".lec_en")
        m["cells"][nm + ".lec_and"] = {"hide_name": 0, "type": "$and", "attributes": {},
            "parameters": {"A_SIGNED": "0", "B_SIGNED": "0", "A_WIDTH": "1", "B_WIDTH": "1", "Y_WIDTH": "1"},
            "port_directions": {"A": "input", "B": "input", "Y": "output"}, "connections": {"A": [a], "B": [b], "Y": [y]}}
        return y
    if merge_enables:
        st0 = merge_enable_copies(m)
    gates = {}
    for cn, c in list(m["cells"].items()):
        if c["type"] == "ot_hdc_cg":
            gates[c["connections"]["gclk"][0]] = (cn, c["connections"]["clk"][0], c["connections"]["en"][0])
    st = {"gates": sorted(v[0] for v in gates.values()), "flops": 0, "roms": 0}
    if merge_enables:
        st["merged_enable_copies"] = st0
    used = {g: 0 for g in gates}
    for cn, c in list(m["cells"].items()):
        t, pc = c["type"], c["connections"]
        if t == "ot_hdc_cg":
            continue
        for p, bits in list(pc.items()):
            for i, b in enumerate(bits):
                if b not in gates or c["port_directions"].get(p) != "input":
                    continue
                gname, ck, en = gates[b]
                used[b] += 1
                if t in ("$dff", "$adff", "$dffe", "$adffe") and p == "CLK":
                    pc["CLK"] = [ck]
                    if "EN" in pc:
                        pc["EN"] = [and2(cn, en, pc["EN"][0])] if c["parameters"].get("EN_POLARITY", "1").endswith("1") \
                            else [and2(cn, en, newnot(m, cn, pc["EN"][0], newbit))]
                        c["parameters"]["EN_POLARITY"] = "1"
                    else:
                        c["type"] = "$dffe" if t == "$dff" else "$adffe"
                        c["parameters"]["EN_POLARITY"] = "1"; c["port_directions"]["EN"] = "input"; pc["EN"] = [en]
                    st["flops"] += 1
                elif t.startswith("ot_rom_") and p == "clk":
                    pc["clk"] = [ck]; pc["ce_in"] = [and2(cn, en, pc["ce_in"][0])]; st["roms"] += 1
                else:
                    sys.stderr.write(f"REFUSED {name}: gate {gname} output reaches {t} {cn}.{p}[{i}]\n"); sys.exit(1)
    # ROM black boxes -> the same stub on both sides (equiv_induct has no model for a black box): every input pin bit
    # becomes a primary output lec_bbi_<inst>_<pin> (compare point), every output pin bit a primary input
    # lec_bbo_<inst>_<pin> (shared free input, matched by name)
    for cn, c in list(m["cells"].items()):
        if not c["type"].startswith("ot_rom_"):
            continue
        tag = "".join(ch if ch.isalnum() else "_" for ch in cn)
        for p, bits in c["connections"].items():
            if c["port_directions"][p] == "input":
                m["ports"][f"lec_bbi_{tag}_{p}"] = {"direction": "output", "bits": list(bits)}
            else:
                m["ports"][f"lec_bbo_{tag}_{p}"] = {"direction": "input", "bits": list(bits)}
        del m["cells"][cn]
        st["rom_stubs"] = st.get("rom_stubs", 0) + 1
    for o, (cn, ck, en) in gates.items():
        for pn, p in m["ports"].items():
            if o in p["bits"]:
                sys.stderr.write(f"REFUSED {name}: gate {cn} output is port {pn}\n"); sys.exit(1)
        del m["cells"][cn]
    del d["modules"][tops[0]]
    d["modules"][name] = m
    for k in list(d["modules"]):          # black-box definitions: once (gold file); ot_hdc_cg no longer used
        if k != name and (k == "ot_hdc_cg" or name == "gate"):
            del d["modules"][k]
    o = os.path.join(out, name + ".cge.json")
    json.dump(d, open(o, "w"))
    st["gated_flop_cells_per_gate"] = {gates[g][0]: n for g, n in used.items()}
    return o, st


def merge_enable_copies(m):
    """--merge-enables (gate only): prove STRUCTURALLY that every kept enable copy u_ze_r<k> is the same register as
    u_z (same cell type, clock, asynchronous reset, reset value, polarities and the same D bits = qz_zd), hence equal
    in every cycle from reset; then replace each copy's output by u_z's output.  Sound: two registers with identical
    clock, reset and next-state inputs hold identical values in every reachable state (both reset to RV)."""
    def q_of(net):
        bits = m["netnames"][net]["bits"]
        for cn, c in m["cells"].items():
            if c["type"] in ("$adff", "$dff") and c["connections"].get("Q") == bits:
                return cn, c
        sys.exit(f"merge-enables: no flop drives {net}")
    alias = "u_e.g_qz_cg.u_z.q"
    if alias in m["netnames"] and not any(n.startswith("u_e.g_cgr.") for n in m["netnames"]):
        # S81-QX-GB 2026-10-26: gate at CGR 0 (single gate, no copies): nothing to merge; --state-points stays usable
        return {"into": None, "copies": [], "check": "CGR 0: no enable copies in the gate"}
    if alias in m["netnames"]:
        zn, z = q_of(alias); rep = "u_e.g_qz_cg.u_z"; ks = range(8)
    else:                               # CGR: u_z has no load (only simulation checks read it) and is gone after
        zn, z = q_of("u_e.g_cgr.u_ze_r0.q")   # opt_clean; u_ze_r0 represents it, under u_z's name (matched to gold u_z)
        m["netnames"][alias] = {"hide_name": 0, "bits": list(z["connections"]["Q"]), "attributes": {}}
        rep = "u_e.g_cgr.u_ze_r0 (named u_e.g_qz_cg.u_z.q)"; ks = range(1, 8)
    key = lambda c: (c["type"], c["connections"]["CLK"], c["connections"].get("ARST"), c["connections"]["D"],
                     tuple(sorted(c["parameters"].items())))
    sub, done = {}, []
    for k in ks:
        cn, c = q_of(f"u_e.g_cgr.u_ze_r{k}.q")
        if key(c) != key(z):
            sys.exit(f"merge-enables REFUSED: u_ze_r{k} differs from u_z: {key(c)} vs {key(z)}")
        sub[c["connections"]["Q"][0]] = z["connections"]["Q"][0]
        del m["cells"][cn]; done.append(f"u_e.g_cgr.u_ze_r{k}")
    for c in m["cells"].values():
        for p, bits in c["connections"].items():
            if c["port_directions"].get(p) == "input":
                c["connections"][p] = [sub.get(b, b) for b in bits]
    for pn, pp in m["ports"].items():
        if pp["direction"] == "output":
            pp["bits"] = [sub.get(b, b) for b in pp["bits"]]
    return {"into": rep, "copies": done, "check": "type/CLK/ARST/D/params identical"}


def normalize_state_points(gold_json, gate_json, out):
    """Retain all state bits/true ports while removing combinational alias cuts.

    Only netnames change: cells, clocks, edge/enable/reset parameters and port
    connections remain intact. Require a complete one-to-one FF alias map and
    matching defined initial values; the subsequent proof checks every FF bit.
    """
    data = [json.load(open(p)) for p in (gold_json,gate_json)]
    models = [d["modules"][n] for d,n in zip(data,("gold","gate"))]
    interface = lambda m: {n:(p["direction"],len(p["bits"])) for n,p in m["ports"].items()}
    if interface(models[0]) != interface(models[1]):
        raise ValueError("state points: primary/ROM interface differs")
    sequential = {"$dff","$adff","$dffe","$adffe"}
    states, initial, records = [], [], []
    for m in models:
        q, init, cells = set(), {}, {}
        for cell in m["cells"].values():
            typ = cell["type"]
            if typ not in sequential and typ.startswith(("$dff","$adff","$sdff","$aldff","$dlatch","$ff","$sr","$mem","$fsm")):
                raise ValueError("state points: unsupported state cell "+typ)
            if typ in sequential:
                bits = cell["connections"]["Q"]
                if any(not isinstance(b,int) or b in q for b in bits):
                    raise ValueError("state points: multiply driven/nonvariable FF output")
                q.update(bits)
                cells.update({b:(cell,i) for i,b in enumerate(bits)})
        for name,net in m["netnames"].items():
            value = net.get("attributes",{}).get("init")
            if value is None:
                continue
            if not isinstance(value,str) or len(value) != len(net["bits"]):
                raise ValueError("state points: malformed initial value "+name)
            for i,bit in enumerate(net["bits"]):
                v = value[-1-i]
                if v in "01":
                    if bit not in q or (bit in init and init[bit] != v):
                        raise ValueError("state points: unsupported/conflicting initial value "+name)
                    init[bit] = v
        states.append(q);initial.append(init);records.append(cells)
    links, reverse = {}, {}
    for name in sorted(set(models[0]["netnames"]) & set(models[1]["netnames"])):
        if "$" in name:
            continue
        a,b = [m["netnames"][name]["bits"] for m in models]
        if len(a) != len(b):
            continue
        for g,t in zip(a,b):
            if g in states[0] and t in states[1]:
                links.setdefault(g,set()).add(t);reverse.setdefault(t,set()).add(g)
    if any(len(v) != 1 for d in (links,reverse) for v in d.values()):
        raise ValueError("state points: ambiguous FF aliases")
    pairs = [(g,next(iter(ts))) for g,ts in links.items()]
    if set(links) != states[0] or set(reverse) != states[1] or len(pairs) != len(states[1]):
        raise ValueError("state points: unmatched FF bits")
    for g,t in pairs:
        if initial[0].get(g,"x") != initial[1].get(t,"x"):
            raise ValueError("state points: defined initial values differ")
    clock_pairs = dict(pairs)
    for name,port in models[0]["ports"].items():
        if port["direction"] == "input":
            for g,t in zip(port["bits"],models[1]["ports"][name]["bits"]):
                if g in clock_pairs and clock_pairs[g] != t:
                    raise ValueError("state points: conflicting input/state mapping")
                clock_pairs[g] = t
    for g,t in pairs:
        gc,gi = records[0][g];tc,ti = records[1][t]
        param = lambda c,i: (c["type"],tuple(c["parameters"].get(k) for k in
            ("CLK_POLARITY","EN_POLARITY","ARST_POLARITY")),
            c["parameters"]["ARST_VALUE"][-1-i] if "ARST_VALUE" in c["parameters"] else None)
        if param(gc,gi) != param(tc,ti):
            raise ValueError("state points: clock/enable/reset cell semantics differ")
        gclk,tclk = gc["connections"]["CLK"][0],tc["connections"]["CLK"][0]
        if clock_pairs.get(gclk,gclk if isinstance(gclk,str) else None) != tclk:
            raise ValueError("state points: unmatched or unproved derived clock")
    outputs = []
    for side,(d,m,name) in enumerate(zip(data,models,("gold","gate"))):
        names = {n:{"hide_name":0,"bits":list(p["bits"]),"attributes":{}} for n,p in m["ports"].items()}
        for i,pair in enumerate(pairs):
            key = f"lec_state_{i}"
            if key in names:
                raise ValueError("state points: reserved port name "+key)
            bit = pair[side];attrs = {"keep":"00000000000000000000000000000001"}
            if bit in initial[side]:
                attrs["init"] = initial[side][bit]
            names[key] = {"hide_name":0,"bits":[bit],"attributes":attrs}
        m["netnames"] = names
        path = os.path.join(out,name+".state.json")
        json.dump(d,open(path,"w"));outputs.append(path)
    return *outputs, dict(state_bits=len(pairs),primary_and_rom_ports=len(interface(models[0])),
                          interface_bits=sum(n for _,n in interface(models[0]).values()),
                          cells_and_ports_changed=False,defined_initial_values_checked=True,
                          clock_edges_and_reset_parameters_checked=True)


def newnot(m, cn, a, newbit):
    y = newbit(cn + ".lec_nen")
    m["cells"][cn + ".lec_not"] = {"hide_name": 0, "type": "$not", "attributes": {},
        "parameters": {"A_SIGNED": "0", "A_WIDTH": "1", "Y_WIDTH": "1"},
        "port_directions": {"A": "input", "Y": "output"}, "connections": {"A": [a], "Y": [y]}}
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gate_root"); ap.add_argument("gold_root"); ap.add_argument("out")
    ap.add_argument("--yosys", default=os.path.expanduser("~/.local/opentallas-tools/yosys-0.68/bin/yosys"))
    ap.add_argument("--merge-enables", action="store_true",
                    help="prove the 8 kept enable copies equal to u_z structurally and merge them (no induction needed)")
    ap.add_argument("--state-points",action="store_true",
                    help="with --merge-enables: retain every state bit and true port, remove combinational alias cuts")
    ap.add_argument("--top", default=TOP, help="gate top module (file rtl/v41rom/<top>.sv)")
    ap.add_argument("--gold-top", default=None, help="gold top module (default = --top)")
    ap.add_argument("--gate-param", action="append", default=None, metavar="K=V",
                    help="gate-only parameter override (repeatable); default CGR=8. 'none' = no override")
    a = ap.parse_args()
    a.gold_top = a.gold_top or a.top
    gate_extra = {"CGR": 8} if a.gate_param is None else {
        k: int(v) for k, v in (x.split("=", 1) for x in a.gate_param if x != "none")}
    if a.state_points and not a.merge_enables:
        ap.error("--state-points requires structural --merge-enables")
    a.state_points = a.state_points or a.merge_enables
    os.makedirs(a.out, exist_ok=True)
    json.dump(dict(schema="opentallas.lec_cgr.v1",verdict="RUNNING"),open(os.path.join(a.out,"lec_cgr.json"),"w"))
    open(os.path.join(a.out, "lec_bb.v"), "w").write(BB)
    t0 = time.time()
    gj, gst = cg_to_enable(elab(a.yosys, a.gold_root, a.out, "gold", {}, a.gold_top), "gold", a.out)
    tj, tst = cg_to_enable(elab(a.yosys, a.gate_root, a.out, "gate", gate_extra, a.top), "gate", a.out, a.merge_enables)
    scope = None
    if a.state_points:
        try:
            gj,tj,scope = normalize_state_points(gj,tj,a.out)
        except ValueError as ex:
            json.dump(dict(schema="opentallas.lec_cgr.v1",verdict="REFUSED",reason=str(ex)),
                      open(os.path.join(a.out,"lec_cgr.json"),"w"),indent=1)
            ap.exit(1,str(ex)+"\n")
    steps = "equiv_struct -icells -fwd; equiv_induct -seq 2; " if a.state_points else (
        "equiv_struct; equiv_simple -seq 2; "+("" if a.merge_enables else "equiv_induct -seq 2; "))
    scr = (f"read_json {gj}; read_json {tj}; async2sync; equiv_make gold gate equiv; hierarchy -top equiv; "+
           steps+"equiv_status; equiv_status -assert")
    log = os.path.join(a.out, "equiv.log")
    r = subprocess.run([a.yosys, "-l", log, "-p", scr], stdout=subprocess.DEVNULL)
    txt = open(log).read()
    summ = [l.strip() for l in txt.splitlines() if "Found" in l and "$equiv" in l or "unproven" in l.lower()][-6:]
    errs = [l for l in txt.splitlines() if l.startswith("ERROR:")]
    if r.returncode == 0:
        verdict = "EQUIVALENT"
    elif errs and "equiv_status" in errs[-1] or errs and "unproven $equiv" in errs[-1]:
        verdict = "UNPROVEN"            # equiv_* could not prove some compare points (listed in equiv.log)
    else:
        verdict = "TOOL ERROR"
    summ += errs[-1:]
    res = {"schema": "opentallas.lec_cgr.v1", "verdict": verdict, "gold": a.gold_root, "gate": a.gate_root,
           "params": PARAMS, "gate_extra": gate_extra,
           "gold_top": a.gold_top, "gate_top": a.top, "merge_enables": a.merge_enables, "gold_cg": gst, "gate_cg": tst, "equiv_summary": summ,
           "state_point_scope":scope,"clock_abstraction":"unchanged registered-enable ICG-to-enable transform",
           "seconds": round(time.time() - t0)}
    json.dump(res, open(os.path.join(a.out, "lec_cgr.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))
    sys.exit({"EQUIVALENT": 0, "UNPROVEN": 2}.get(verdict, 3))


if __name__ == "__main__":
    main()
