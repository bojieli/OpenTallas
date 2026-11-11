#!/usr/bin/env python3
"""HBM-CHANNELS 11-11 (DO_NOT_COUNT): stage-equivalence proof for every register stage the channel event adds.

For each changed link (ft slot chain or internal-station chain) of plan EVENT vs base BASE:
  OLD  = the link exactly as the strict base bind emitted it (instance lines extracted verbatim from the bound RTL
         BOUND_RTL/<module>.sv: u_ft_<slot>_o_<i> chain, or u_ist_<bus>_<i> chain + u_bout_<bus>).
  NEW  = the same generator pattern with the event's station count (pattern checked: emitting the OLD count with it
         reproduces the extracted OLD lines byte-identically after whitespace normalisation).
  GOLD = OLD followed by k = n_new - n_old cycles of delay (data: plain flops; epoch/valid bit: flop with async reset
         to 0, the ot_dp_st eq semantics).
  PASS : yosys miter -equiv + sat -tempinduct -prove-asserts -set-init-zero, GOLD == NEW (all outputs, every cycle).
  NEG1 : GOLD with k-1 delay cycles vs NEW -> must FAIL (the extra stage is really +k, not fewer).
  NEG2 : NEW mutant, data bit 0 of the added stage bypasses it -> must FAIL (every bit takes the stage).
Also checks k against the plan: lane latency delta == sum of the station deltas on the lane's crossings.

  eq_stations.py BASE_PLAN EVENT_PLAN BOUND_RTL OUT_DIR YOSYS_CMD
"""
import json, re, subprocess, sys
from pathlib import Path

BASE, EV, RTL, OUT, YOSYS = sys.argv[1], sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]
a, b = json.load(open(BASE)), json.load(open(EV))
TA, TB = a["partition_types"], b["partition_types"]
OUT.mkdir(parents=True, exist_ok=True)
CELL = """module ot_dp_st #(parameter integer W = 1) (input wire clk, input wire rst_n, input wire [W-1:0] d, input wire ea,
    output reg [W-1:0] q, output reg eq);
    always @(posedge clk) q <= d;
    always @(posedge clk or negedge rst_n) if (!rst_n) eq <= 1'b0; else eq <= ea;
endmodule
"""


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def rtl_of(tn):
    m = TA[tn]["module"]
    for f in (f"{m}__{tn}.sv", f"{m}.sv"):
        if (RTL / f).exists():
            return (RTL / f).read_text()
    raise FileNotFoundError(tn)


def ft_lines(sn, n, W):
    out = []
    for i in range(n):
        d = f"{sn}_i[{W-1}:0]" if i == 0 else f"{sn}_o_s{i-1}[{W-1}:0]"
        ea = f"{sn}_i[{W}]" if i == 0 else f"{sn}_o_s{i-1}[{W}]"
        q = f"{sn}_o[{W-1}:0]" if i == n - 1 else f"{sn}_o_s{i}[{W-1}:0]"
        e = f"{sn}_o[{W}]" if i == n - 1 else f"{sn}_o_s{i}[{W}]"
        out.append(f"ot_dp_st #(.W({W})) u_ft_{sn}_o_{i} (.clk(clk), .rst_n(rst_n), .d({d}), .ea({ea}), .q({q}), .eq({e}));")
    return out


def ist_lines(bus, n, W, src):
    out = []
    for i in range(n):
        d = src if i == 0 else f"{bus}_is{i-1}_q"
        ea = "rst_n" if i == 0 else f"{bus}_is{i-1}_eq"
        out.append(f"ot_dp_st #(.W({W})) u_ist_{bus}_{i} (.clk(clk), .rst_n(rst_n), .d({d}), .ea({ea}), .q({bus}_is{i}_q), .eq({bus}_is{i}_eq));")
    out.append(f"ot_dp_st #(.W({W})) u_bout_{bus} (.clk(clk), .rst_n(rst_n), .d({bus}_is{n-1}_q), .ea({bus}_is{n-1}_eq), .q({bus}[{W-1}:0]), .eq({bus}[{W}]));")
    return out


def extract(txt, pat):
    return [norm(l.split("//")[0]) for l in txt.splitlines() if re.search(pat, l) and "ot_dp_st" in l]


def module(name, kind, sn, n, W, lines, mutate=False):
    body = []
    if kind == "ft":
        ports = f"input wire clk, input wire rst_n, input wire [{W}:0] {sn}_i, output wire [{W}:0] {sn}_o"
        for i in range(n - 1):
            body.append(f"wire [{W}:0] {sn}_o_s{i};")
    else:
        ports = f"input wire clk, input wire rst_n, input wire [{W-1}:0] src, output wire [{W}:0] {sn}"
        for i in range(n):
            body += [f"wire [{W-1}:0] {sn}_is{i}_q;", f"wire {sn}_is{i}_eq;"]
    ls = list(lines)
    if mutate:   # NEG2: data bit 0 of the last added stage bypasses it
        last = [l for l in ls if " u_ft_" in l or " u_ist_" in l][-1]
        D = re.search(r"\.d\(([^)]*)\)", last).group(1); Q = re.search(r"\.q\(([^)]*)\)", last).group(1)
        D0 = D.replace(f"[{W-1}:0]", "[0]") if D.endswith(f"[{W-1}:0]") else D + "[0]"
        body.append(f"wire [{W-1}:0] __byp;")
        ls[ls.index(last)] = last.replace(f".q({Q})", ".q(__byp)")
        ls.append(f"assign {Q} = {{__byp[{W-1}:1], {D0}}};")
    return f"module {name} ({ports});\n" + "\n".join("    " + x for x in body + ls) + "\nendmodule\n"


def gold(name, inner, kind, sn, W, k):
    if kind == "ft":
        ports = f"input wire clk, input wire rst_n, input wire [{W}:0] {sn}_i, output wire [{W}:0] {sn}_o"
        inst = f"{inner} u (.clk(clk), .rst_n(rst_n), .{sn}_i({sn}_i), .{sn}_o(w0));"
        o = f"{sn}_o"
    else:
        ports = f"input wire clk, input wire rst_n, input wire [{W-1}:0] src, output wire [{W}:0] {sn}"
        inst = f"{inner} u (.clk(clk), .rst_n(rst_n), .src(src), .{sn}(w0));"
        o = sn
    lines = [f"wire [{W}:0] w0;", inst]
    for i in range(k):
        lines += [f"reg [{W-1}:0] dq{i}; reg de{i};",
                  f"always @(posedge clk) dq{i} <= w{i}[{W-1}:0];",
                  f"always @(posedge clk or negedge rst_n) if (!rst_n) de{i} <= 1'b0; else de{i} <= w{i}[{W}];",
                  f"wire [{W}:0] w{i+1} = {{de{i}, dq{i}}};"]
    lines.append(f"assign {o} = w{k};")
    return f"module {name} ({ports});\n" + "\n".join("    " + x for x in lines) + "\nendmodule\n"


def prove(d, gold_sv, gate_sv):
    d.mkdir(parents=True, exist_ok=True)
    (d / "cells.sv").write_text(CELL); (d / "gold.sv").write_text(gold_sv); (d / "gate.sv").write_text(gate_sv)
    ys = (f"read_verilog -sv {d}/cells.sv {d}/gold.sv {d}/gate.sv\nhierarchy -check\nproc\nflatten gold_top\nflatten gate_top\n"
          "async2sync\nmiter -equiv -flatten -make_assert -ignore_gold_x gold_top gate_top miter\nhierarchy -top miter\n"
          "opt -full\n"   # sound simplification (structural hashing / register merge) before the SAT proof
          "sat -verify -tempinduct -prove-asserts -set-init-zero -seq 1 -maxsteps 24 miter\n")
    (d / "proof.ys").write_text(ys)
    r = subprocess.run(YOSYS.split() + ["-q", "-l", str(d / "yosys.log"), "-s", str(d / "proof.ys")], capture_output=True, text=True)
    log = (d / "yosys.log").read_text(errors="replace") if (d / "yosys.log").exists() else ""
    return dict(rc=r.returncode, proved=r.returncode == 0, induction="Induction step proven" in log,
                log=str(d / "yosys.log"), tail=(r.stderr or "")[-300:])


links = []
for tn, t in TB.items():
    if tn not in TA:
        continue
    for sl in t.get("ft_slots", []):
        so = next((x for x in TA[tn].get("ft_slots", []) if x["name"] == sl["name"]), None)
        if so and int(sl.get("stations", 1)) != int(so.get("stations", 1)):
            links.append(("ft", tn, sl["name"], int(so["stations"]), int(sl["stations"])))
    ib, ia = t.get("internal_stations", []), TA[tn].get("internal_stations", [])
    assert len(ib) == len(ia), tn
    for e, eo in zip(ib, ia):            # rows are per core/bus (several per conn): compare row by row
        assert e.get("conn") == eo.get("conn"), (tn, e.get("conn"))
        if len(e["regs_um"]) != len(eo["regs_um"]):
            links.append(("ist", tn, e["conn"][4:], len(eo["regs_um"]), len(e["regs_um"])))
res = {}
for kind, tn, sn, n0, n1 in links:
    txt = rtl_of(tn); k = n1 - n0
    if kind == "ft":
        m = re.search(r"input\s+wire\s+\[(\d+):0\]\s+" + re.escape(sn) + r"_i\b", txt); W = int(m.group(1))
        ext = extract(txt, r"\bu_ft_" + re.escape(sn) + r"_o_\d+\b")
        old = ft_lines(sn, n0, W); new = ft_lines(sn, n1, W)
    else:
        m = re.search(r"output\s+wire\s+\[(\d+):0\]\s+" + re.escape(sn) + r"\b", txt); W = int(m.group(1))
        ext = extract(txt, r"\bu_(ist_" + re.escape(sn) + r"_\d+|bout_" + re.escape(sn) + r")\b")
        src = re.search(r"u_ist_" + re.escape(sn) + r"_0 \(.*?\.d\((.*?)\), \.ea", txt).group(1)
        old = ist_lines(sn, n0, W, "src"); new = ist_lines(sn, n1, W, "src")
    pat = [norm(x) for x in (ft_lines(sn, n0, W) if kind == "ft" else ist_lines(sn, n0, W, src))]
    pattern_ok = sorted(pat) == sorted(ext)
    d = OUT / f"{tn}__{sn}"
    g_old = module("old_link", kind, sn, n0, W, old)
    gate = module("gate_top", kind, sn, n1, W, new)
    gate_mut = module("gate_top", kind, sn, n1, W, new, mutate=True)
    r = dict(kind=kind, type=tn, link=sn, width=W, stations_base=n0, stations_new=n1, k=k,
             pattern_matches_bound_rtl=pattern_ok, bound_rtl_lines=len(ext))
    r["PASS"] = prove(d / "pass", g_old + gold("gold_top", "old_link", kind, sn, W, k), gate)
    r["NEG1_short_delay"] = prove(d / "neg1", g_old + gold("gold_top", "old_link", kind, sn, W, k - 1), gate)
    r["NEG2_bit_bypass"] = prove(d / "neg2", g_old + gold("gold_top", "old_link", kind, sn, W, k), gate_mut)
    r["verdict"] = ("EQ_CYCLE_SHIFTED_+%d" % k if pattern_ok and r["PASS"]["rc"] == 0 and r["NEG1_short_delay"]["rc"] != 0
                    and r["NEG2_bit_bypass"]["rc"] != 0 else "NOT_PROVEN")
    res[f"{tn}.{sn}"] = r
    print(tn, sn, n0, "->", n1, "W", W, "pattern", pattern_ok, "PASS rc", r["PASS"]["rc"], "NEG1 rc", r["NEG1_short_delay"]["rc"],
          "NEG2 rc", r["NEG2_bit_bypass"]["rc"], r["verdict"], flush=True)

# lane cycle cross-check: latency delta == sum of station deltas on the lane's crossings
sys.path.insert(0, "tools/die_plan")
import schema as S
PB, PE = S.Plan(json.load(open(BASE))), S.Plan(json.load(open(EV)))
dl = {}
for lid in PE.lanes:
    cb = b["latency"]["lanes"].get(lid, {}).get("cycles"); ca = a["latency"]["lanes"].get(lid, {}).get("cycles")
    if cb != ca:
        st = 0
        for part, slot, x, y in PE.lane_crossings(lid):
            tn = PE.parts[part]["type"]; st += res.get(f"{tn}.{slot}", {}).get("k", 0)
        fx = int(next(l for l in b["lanes"] if l["id"] == lid).get("fixed_cycles", 0)) - int(next(l for l in a["lanes"] if l["id"] == lid).get("fixed_cycles", 0))
        dl[lid] = dict(latency_base=ca, latency_new=cb, delta=cb - ca, ft_station_delta=st, fixed_cycles_delta=fx,
                       consistent=(cb - ca) == st + fx)
json.dump(dict(base=BASE, event=EV, bound_rtl=str(RTL), links=res, lanes=dl,
               verdict="ALL_EQ_CYCLE_SHIFTED" if all(v["verdict"].startswith("EQ") for v in res.values()) and all(v["consistent"] for v in dl.values()) else "INCOMPLETE"),
          open(OUT / "eq_stations.json", "w"), indent=1)
print(json.dumps(dl, indent=0))
