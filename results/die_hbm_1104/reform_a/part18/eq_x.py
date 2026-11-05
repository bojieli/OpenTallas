#!/usr/bin/env python3
"""HBM-REFORM-A part 18 bench generator: uncut lane core in its kit shell vs lane_x + sfu_s, each in its own face shell.
The compiler moves exp/sigmoid/SiLU S-out and later control +XS.  So the bench runs epochs of one op kind with a drain between them:
  pre-S inputs            same on both sides, every edge
  post-S control + side_y DUT sees them XS edges later in a deep epoch (EXP, SIGM, SILU), same edge otherwise
  write / reduce outputs  dut[t] == ref[t - XS] in a deep epoch, dut[t] == ref[t] otherwise
  pre-S outputs           dut[t] == ref[t] always
  fault                   one pulse stream: S and later faults move XS, earlier ones do not.  Every ref pulse at t needs a DUT pulse at t or t + XS, and the reverse.
  f_sfu                   S-chain fault net inside each lane, cycle exact: dut[t] == ref[t - XS] in a deep epoch, 0 in a shallow one, and pulses must occur.  Random
                          operands fire the other 8 fault sources at the same edges, so the pin stream alone masks a dead seam fault (mutant 5 survived it).
                          Random stimulus alone never fires the S chain (0 pulses), so the second half of the epochs forces the lane's R to a signalling NaN on both sides.
    eq_x.py PORTS.json WRAP.sv REF DUT KINDS OUT_tb.sv [EPOCHS]     KINDS: comma list of ci_sfu values, deep ones are 1,4,5"""
import json, re, sys
P = json.load(open(sys.argv[1])); REF, DUT = sys.argv[3:5]
KINDS = [int(k) for k in sys.argv[5].split(",")]; out = sys.argv[6]; EP = int(sys.argv[7]) if len(sys.argv) > 7 else 40
XS = 4; DRAIN = 400; LEN = 600
ports = P["ports"]; clks = P["clk"]; rsts = P["rst"]
def pin(core):
    f = core.removeprefix("lane_")
    c = [n for n in ports if n == core or n.endswith("u_lane_" + f) or n.endswith("_lane_" + f)]
    if len(c) != 1: raise SystemExit(f"pin of {core}: {c}")
    return c[0]
def has(core):
    f = core.removeprefix("lane_")
    return any(n == core or n.endswith("u_lane_" + f) or n.endswith("_lane_" + f) for n in ports)
POST_CORE = "cs_sfu cs_e1 cs_imm2 ce_e2 ce_imm1 co_rnd co_dst side_y".split()
post_in = {pin("lane_" + c) for c in POST_CORE if has("lane_" + c)}
post_out = {pin("lane_" + c) for c in "vm_we vm_waddr vm_wdata kv_we kv_waddr kv_wdata ro_v ro_x".split()}
QUAL = {pin("lane_" + a): pin("lane_" + v) for a, v in (("vm_waddr", "vm_we"), ("vm_wdata", "vm_we"), ("kv_waddr", "kv_we"), ("kv_wdata", "kv_we"), ("ro_x", "ro_v"))}
FAULT = pin("lane_fault"); CI, CS, EMIT = pin("lane_ci_sfu"), pin("lane_cs_sfu"), pin("lane_emit")
hold = {n: f"{ports[n][1]}'d5" for n in ports if "lane_id" in n}
ins = [n for n, (d, w) in ports.items() if d == "input" and n not in clks and n not in rsts]
outs = [n for n, (d, w) in ports.items() if d == "output"]
missing = (post_out | {FAULT}) - set(outs)
if missing: raise SystemExit(f"post outs not plan pins {missing}")
W = lambda n: ports[n][1]
L = ["`timescale 1ns/1ps", "`default_nettype none", "module tb;"]
for c in clks: L.append(f"  logic [{W(c)-1}:0] {c} = '0;")
for r in rsts: L.append(f"  logic [{W(r)-1}:0] {r} = '0;")
for n in ins:
    L.append(f"  logic [{W(n)-1}:0] {n}_r = '0;")
    if n in post_in:
        L.append(f"  logic [{W(n)-1}:0] {n}_d[0:{XS-1}];")
for n in outs:
    L += [f"  wire [{W(n)-1}:0] {n}_ref, {n}_dut;"]
    if n in post_out: L.append(f"  logic [{W(n)-1}:0] {n}_h[0:{XS-1}];")
L += ["  logic deep = 0; logic [2:0] kind = 0; logic drain = 1;",
      f"  logic [{2*XS}:0] fr = '0, fd = '0;", f"  logic [{XS-1}:0] sr = '0;", "  longint sp = 0;"]
def inst(mod, name, suffix):
    a = [f".{c}({c})" for c in clks] + [f".{r}({r})" for r in rsts]
    for n in ins:
        e = f"{n}_r"
        if suffix == "dut" and n in post_in: e = f"(deep ? {n}_d[{XS-1}] : {n}_r)"
        a.append(f".{n}({e})")
    a += [f".{n}({n}_{suffix})" for n in outs]
    return f"  {mod} {name} (" + ", ".join(a) + ");"
L += [inst(REF, "u_ref", "ref"), inst(DUT, "u_dut", "dut")]
def rnd(w):
    k = (w + 31) // 32
    return "{" + ",".join(["$urandom"] * k) + "}" if k > 1 else "$urandom"
L += ["  longint checks = 0, errs = 0, ferrs = 0, deep_w = 0, sh_w = 0, fp = 0; int ep = 0, cyc = 0;",
      "  task automatic bad(input string n); errs++; if (errs < 12) $display(\"MISMATCH %s cyc=%0d ep=%0d kind=%0d deep=%0d\", n, cyc, ep, kind, deep); endtask",
      "  always #0.5 begin"]
for c in clks: L.append(f"    {c} = ~{c};")
L += ["  end", "  always @(posedge " + clks[0] + ") begin", "    cyc <= cyc + 1;"]
for n in ins:
    if n in hold: L.append(f"    {n}_r <= {hold[n]};"); continue
    if n == CI or n == CS:
        L.append(f"    {n}_r <= kind;")
        if n in post_in: L.append(f"    {n}_d[0] <= {n}_r; for (int i = 1; i < {XS}; i++) {n}_d[i] <= {n}_d[i-1];")
        continue
    if n == EMIT: L.append(f"    {n}_r <= drain ? 1'b0 : $urandom;"); continue
    L.append(f"    {n}_r <= {rnd(W(n))};")
    if n in post_in:
        L.append(f"    {n}_d[0] <= {n}_r; for (int i = 1; i < {XS}; i++) {n}_d[i] <= {n}_d[i-1];")
for n in outs:
    if n in post_out: L.append(f"    {n}_h[0] <= {n}_ref; for (int i = 1; i < {XS}; i++) {n}_h[i] <= {n}_h[i-1];")
L += [f"    fr <= {{fr[{2*XS-1}:0], |{FAULT}_ref}}; fd <= {{fd[{2*XS-1}:0], |{FAULT}_dut}};"]
SR = "u_ref.u_fcore.u_core.u_lane.u_lane.f_sfu"; SD = "u_dut.u_fcore.u_core.u_l.u_fcore.u_lane.u_lane.f_sfu"
L += [f"    sr <= {{sr[{XS-2}:0], {SR}}};"]
L += ["    if (cmp) begin", f"      if ({SR}) sp++;", f"      if ({SD} !== (deep ? sr[{XS-1}] : {SR})) bad(\"f_sfu\");"]
for n in outs:
    if n == FAULT: continue
    if n in post_out:
        q = QUAL.get(n)    # data under its valid: the insertion line's idle output is stale and depends on depth (no consumer reads it)
        rv = (f"(deep ? {q}_h[{XS-1}] : {q}_ref)" if q else "1'b1")
        L.append(f"      checks++; if ({rv} && {n}_dut !== (deep ? {n}_h[{XS-1}] : {n}_ref)) bad(\"{n}\");")
    else:
        L.append(f"      checks++; if ({n}_dut !== {n}_ref) bad(\"{n}\");")
vm = pin("lane_vm_we")
L += [f"      if (|{vm}_ref) begin if (deep) deep_w++; else sh_w++; end",
      f"      if (fr[{XS}]) begin fp++; if (!(fd[{XS}] || fd[0])) begin ferrs++; bad(\"fault ref\"); end end",
      f"      if (fd[{XS}] && !(fr[{XS}] || fr[{2*XS}])) begin ferrs++; bad(\"fault dut\"); end",
      "    end", "  end",
      "  logic cmp = 0;",
      "  initial begin"]
for r in rsts: L.append(f"    {r} = '0;")
L += ["    repeat (20) @(posedge " + clks[0] + ");"]
for r in rsts: L.append(f"    {r} = '1;")
L.append(f"    repeat ({DRAIN}) @(posedge {clks[0]});")
L += [f"    for (ep = 0; ep < {EP}; ep++) begin",
      f"      kind = kinds[ep % {len(KINDS)}]; deep = (kind == 1 || kind == 4 || kind == 5);",
      f"      repeat ({DRAIN}) @(posedge {clks[0]});",
      f"      if (ep >= {EP//2}) begin force {SR[:-5]}R = 32'h7f800001; force {SD[:-5]}R = 32'h7f800001; end",
      "      cmp = 1; drain = 0;",
      f"      repeat ({LEN}) @(posedge {clks[0]});",
      "      drain = 1;",
      f"      repeat ({DRAIN}) @(posedge {clks[0]});",
      "      cmp = 0;",
      f"      release {SR[:-5]}R; release {SD[:-5]}R;",
      "    end",
      "    $display(\"XEQ %s checks=%0d errs=%0d deep_writes=%0d shallow_writes=%0d fault_pulses=%0d sfu_fault_pulses=%0d\", (errs == 0 && deep_w > 0 && sh_w > 0 && sp > 0) ? \"PASS\" : \"FAIL\", checks, errs, deep_w, sh_w, fp, sp);",
      "    $finish;", "  end",
      f"  int kinds[0:{len(KINDS)-1}] = '{{" + ",".join(map(str, KINDS)) + "};",
      "endmodule", "`default_nettype wire"]
open(out, "w").write("\n".join(L) + "\n")
print("post_in", sorted(post_in)[:12], "post_out", len(post_out), "ins", len(ins), "outs", len(outs))
