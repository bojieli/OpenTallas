#!/usr/bin/env python3
"""RTL-vs-RTL equivalence of the qxpq_w10 clock-gate change (S81-CORE-LAT/QX 2026-10-26): CGR = 8 vs the single-gate RTL.

    python3 tools/dsrom_qelem_cl/qxpq_cgr_lec.py GATE_ROOT GOLD_ROOT OUT [--yosys Y]
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


def elab(y, root, out, name, extra):
    files = " ".join(os.path.join(root, f) for f in SRC)
    ch = " ".join(f"-chparam {k} {v}" for k, v in {**PARAMS, **extra}.items())
    js = os.path.join(out, name + ".elab.json")
    scr = (f"read_verilog -sv -DSYNTHESIS {files} {out}/lec_bb.v; hierarchy -top {TOP} {ch}; "
           f"setattr -mod -unset keep_hierarchy; proc; flatten; memory_map; opt_clean; stat; write_json {js}")
    r = subprocess.run([y, "-q", "-l", os.path.join(out, name + ".elab.log"), "-p", scr])
    if r.returncode:
        sys.exit(f"tool error: elaboration {name} rc {r.returncode}")
    return js


def cg_to_enable(js, name, out):
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
    gates = {}
    for cn, c in list(m["cells"].items()):
        if c["type"] == "ot_hdc_cg":
            gates[c["connections"]["gclk"][0]] = (cn, c["connections"]["clk"][0], c["connections"]["en"][0])
    st = {"gates": sorted(v[0] for v in gates.values()), "flops": 0, "roms": 0}
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
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    open(os.path.join(a.out, "lec_bb.v"), "w").write(BB)
    t0 = time.time()
    gj, gst = cg_to_enable(elab(a.yosys, a.gold_root, a.out, "gold", {}), "gold", a.out)
    tj, tst = cg_to_enable(elab(a.yosys, a.gate_root, a.out, "gate", {"CGR": 8}), "gate", a.out)
    scr = (f"read_json {gj}; read_json {tj}; async2sync; equiv_make gold gate equiv; hierarchy -top equiv; "
           "equiv_struct; equiv_simple -seq 2; equiv_induct -seq 2; equiv_status; equiv_status -assert")
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
           "params": PARAMS, "gate_extra": {"CGR": 8}, "gold_cg": gst, "gate_cg": tst, "equiv_summary": summ,
           "seconds": round(time.time() - t0)}
    json.dump(res, open(os.path.join(a.out, "lec_cgr.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))
    sys.exit({"EQUIVALENT": 0, "UNPROVEN": 2}.get(verdict, 3))


if __name__ == "__main__":
    main()
