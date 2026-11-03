#!/usr/bin/env python3
"""S81-FBAY-1: FIXED-BAY station form, kit overlay (form A = negative-level lockup latch behind each relay station flop).

    fixed_bay_kit.py SRC_KIT OUT_GEN      # SRC_KIT = <wave item>/gen/<T>; writes OUT_GEN/<T> + OUT_GEN/run_kit.sh

1. bays: every ft slot without plan sites gets k plan bays at L*j/k on its in->out line (ft_stations.txt regs), so
   face_flops places station i of a landed slot at bay i+1 (FIRM) instead of re-placing it on the ring->out line
   (the collapsed-hop class of t30__cl1653104c); plain slots keep their plan regs.
2. lockup: the u_ft_* stations become ot_dp_st_lk = ot_dp_st + a negative-level latch on q/eq (transparent while clk
   is low).  The value launched at posedge j is captured at posedge j+1 exactly as before: lane cycle counts unchanged.
3. face_flops: the lockup latch is a pass-through link for the station tracing, and is placed FIRM next to its flop.
Gates, SDC, IO budgets, repeater rule (OT_MAXWIRE_UM) and clocking (tap grid) are unchanged."""
import sys, os, re, shutil, json
src, outg = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
T = os.path.basename(src); dst = os.path.join(outg, T)
SKIP = re.compile(r"^(run|lec|lec_async\..*|FAIL_.*|.*\.previous\..*|postcts_gate_.*\.(log|json)|run_.*\.log|orfs_metrics\.log|"
                  r"physical_completion|1_synth_odb\.v|autopilot_chain_.*|resume\.json|kwrs_make\.sh|preflight_history|"
                  r"kit_preflight_.*\.json|preflight_autopilot_.*|__pycache__)$")
if os.path.exists(dst): raise SystemExit(f"exists: {dst}")
os.makedirs(outg, exist_ok=True)
shutil.copytree(src, dst, ignore=lambda d, names: [n for n in names if d == src and SKIP.match(n)], symlinks=True)
shutil.copy2(os.path.join(os.path.dirname(src), "run_kit.sh"), os.path.join(outg, "run_kit.sh"))
# ---- 1. bays
pins = {}
for ln in open(f"{dst}/io.tcl"):
    m = re.search(r"-pin_name \{?(\w+)\[\d+\]\}? .*-location \{([\d.]+) ([\d.]+)\}", ln)
    if m: pins.setdefault(m.group(1), []).append((float(m.group(2)), float(m.group(3))))
cen = {b: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v)) for b, v in pins.items()}
out = []; bays = {}
for ln in open(f"{dst}/ft_stations.txt"):
    f = ln.split()
    if ln.startswith("#") or not f: out.append(ln.rstrip("\n")); continue
    s, k = f[0], int(f[1])
    if len(f) < 4 + 2 * k:
        a, b = cen[s + "_i"], cen[s + "_o"]
        pts = [(a[0] + (b[0] - a[0]) * j / k, a[1] + (b[1] - a[1]) * j / k) for j in range(k)]
        f = f[:4] + [f"{v:.4f}" for p in pts for v in p]
    bays[s] = [[float(f[i]), float(f[i + 1])] for i in range(4, 4 + 2 * k, 2)]
    hops = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(bays[s], bays[s][1:])]
    assert max(hops) <= 405.0, (s, hops)
    out.append(" ".join(f))
open(f"{dst}/ft_stations.txt", "w").write("\n".join(out) + "\n")
# ---- 2. lockup RTL
bc = f"{dst}/rtl/bind_cells.sv"
open(bc, "a").write("""
// S81-FBAY-1 FIXED-BAY form A: relay station + negative-level lockup latch (transparent while clk is low).  The flop
// launches at posedge; the latch passes it at the following negedge and holds it through the high phase, so the next
// station still captures it at the next posedge (cycle count unchanged) while its hold edge is half a period away.
module ot_dp_st_lk #(parameter integer W = 1) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    input  wire         ea,
    output reg  [W-1:0] q,
    output reg          eq
);
    wire [W-1:0] st_q; wire st_eq;
    ot_dp_st #(.W(W)) u_st (.clk(clk), .rst_n(rst_n), .d(d), .ea(ea), .q(st_q), .eq(st_eq));
    always @* if (!clk) q = st_q;
    always @* if (!clk) eq = st_eq;
endmodule
""")
bf = f"{dst}/rtl/{T}_bound.sv"; t = open(bf).read()
t2, n = re.subn(r"\bot_dp_st (#\(\.W\(\d+\)\) u_ft_)", r"ot_dp_st_lk \1", t)
assert n > 0; open(bf, "w").write(t2)
# ---- 3. face_flops
ff = f"{dst}/face_flops.tcl"; t = open(ff).read()
old = """proc ff_is_buf {inst} {
  set m [[$inst getMaster] getName]
  return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]}]
}"""
new = """proc ff_is_buf {inst} {
  set m [[$inst getMaster] getName]
  if {[ff_is_lockup $inst]} { return 1 }
  return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "HB*" $m]}]
}
# S81-FBAY-1 FIXED-BAY form A: the station lockup latch (ot_dp_st_lk q/eq latch) is a pass-through link of its station
proc ff_is_lockup {inst} {
  return [expr {[string match "DLL*" [[$inst getMaster] getName]] && [regexp {u_ft_[^./]+_o_[0-9]+[./]} [$inst getName]]}]
}"""
assert old in t; t = t.replace(old, new)
anchor = 'if {$ff_lst} { puts "OT_FACE_FLOPS landed ft slots:'
place = r'''# S81-FBAY-1: every station lockup latch FIRM next to the station flop that drives it (same bay, same clock leaf)
set ff_lk 0; set ff_lk_miss 0
foreach i [$ff_blk getInsts] {
  if {![ff_is_lockup $i]} continue
  set src [ff_d_driver $i]
  if {$src eq "" || [$src getPlacementStatus] ne "FIRM"} { incr ff_lk_miss; continue }
  lassign [$src getLocation] sx sy
  set got [ff_put_near $i $sx $sy]
  if {$got eq ""} { incr ff_lk_miss; continue }
  incr ff_lk
}
puts "OT_FBAY lockup latches FIRM next to their station flops: $ff_lk ($ff_lk_miss without a FIRM station driver)"
'''
assert anchor in t; t = t.replace(anchor, place + anchor, 1)
open(ff, "w").write(t)
json.dump(dict(schema="opentallas.fixed_bay_overlay.v1", src=src, form="A_lockup", bays=bays, stations_lk=n),
          open(f"{dst}/fixed_bay.json", "w"), indent=1)
print("OK", dst, "lockup stations", n, {s: len(b) for s, b in bays.items()})
