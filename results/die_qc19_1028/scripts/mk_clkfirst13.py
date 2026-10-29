# DIE-QC-19 copy of die-qc11-1028/mk_clkfirst.py + node M rows (source-fall arrival at each clock cell output, polarity-resolved) for tap_fall_merge --tree
#!/usr/bin/env python3
"""DIE-QC-4 (10-28): CLOCK-FIRST die global route (standard flow / OWNER infra-first rule, COORD ruling DIE-QC-3 (c)).
Stage 1 (this script, mode=clk): the die clock tree ALONE is globally routed on M8-M9 with the macros (core abstracts) and
die PG stripes as blockages and, with ndr=2w2s, the clock NDR CK2W2S (width 0.08 = 2W, spacing 0.32 -> 5 tracks per
wire incl. a shield track each side; same rule as results/die_trial_1024/hbm_b2/clock).  No signal net exists, so GRT
cannot detour the clock around signal congestion: the routed clock is the frozen clock.  Writes the clock guides and
per-tap/per-cell arrivals (estimate_parasitics -global_routing, same format as mk_combo_qc.py).
Stage 2 (mode=sig): the kit's signal GRT (route.v, M4-M9, 50 it, critical 0) with the FROZEN clock as obstructions: every
stage-1 clock guide run on M8/M9 becomes a 5-track-wide (0.40 um; 1 track = 0.08 um at 1x) obstruction along its
centre line, in place of the kit's planned clock reservation rects.  Overflow 0 there = die GRT0 incl clock (12.4a).
Derived from /srv/opentallas-scratch2/claude/die-qc-1027-r250/mk_combo_qc.py (same floorplan / placement / RC / arrival
code).   usage: CORNER=TT mk_clkfirst_qc.py KIT_DIR CLK_DIR OUT_DIR clk {2w2s|1x}
                CORNER=TT mk_clkfirst_qc.py KIT_DIR CLK_DIR OUT_DIR sig STAGE1_GUIDE [ntracks]"""
import json
import os
import re
import sys

K, C, O, MODE = sys.argv[1:5]
os.makedirs(O, exist_ok=True)
kit = json.load(open(K + "/kit.json"))
g = kit["grt"]
npg = g["pg_stripes"]
obs = open(K + "/grt/obs.tcl").read().splitlines()
t = open(K + "/grt/grt.tcl").read()
adj = re.findall(r"set_global_routing_layer_adjustment (M\d) ([\d.]+)", t)
assert adj, "kit grt.tcl has no layer adjustments"
pre = t.split("source /work/grt/obs.tcl")[0]
rv = open(K + "/grt/route.v").read()

if MODE == "clk":
    NDR = sys.argv[5]
    open(O + "/obs_pg.tcl", "w").write("\n".join(obs[:npg]) + "\n")
    cv = open(C + "/ctree.v").read()
    mh = re.match(r"\s*module\s+(\w+)\s*\(([^)]*)\);", rv)
    rports = [p.strip() for p in mh.group(2).split(",") if p.strip()]
    body = []
    for line in rv[mh.end():rv.rindex("endmodule")].split("\n"):
        s = line.strip()
        if not s or s.startswith("wire"):
            continue
        if s.startswith(("input", "output")):
            body.append(line); continue
        m = re.match(r"(\w+)\s+(\w+)\s*\(", s)
        assert m and s.endswith(");"), s[:200]
        body.append(f"  {m.group(1)} {m.group(2)} ();")        # macro kept as a blockage, no signal net
    mc = re.search(r"module\s+ctree\s*\(([^)]*)\);", cv, re.S)
    cports = [p.strip() for p in mc.group(1).split(",") if p.strip()]
    Pset = set(cports)
    f = lambda n: n if n in Pset else "ck_" + n
    out = []
    for line in cv[mc.end():cv.rindex("endmodule")].split("\n"):
        s = line.strip()
        if not s or s.startswith(("input", "output")):
            continue
        m = re.match(r"wire\s+(\w+)\s*;", s)
        if m:
            out.append(f"  wire {f(m.group(1))};"); continue
        m = re.match(r"(\w+)\s+(\w+)\s*\((.*)\);", s)
        if m:
            conns = re.sub(r"\.(\w+)\((\w+)\)", lambda q: f".{q.group(1)}({f(q.group(2))})", m.group(3))
            out.append(f"  {m.group(1)} ck_{m.group(2)} ({conns});"); continue
        m = re.match(r"assign\s+(\w+)\s*=\s*(\w+)\s*;", s)
        if m:
            out.append(f"  assign {f(m.group(1))} = {f(m.group(2))};"); continue
        raise SystemExit("unparsed: " + s)
    decl = [l for l in cv[mc.end():].split("\n") if l.strip().startswith(("input", "output"))]
    open(O + "/clkonly.v", "w").write(f"module die_combo ({', '.join(rports + cports)});\n" + "\n".join(body) + "\n"
                                      + "\n".join(decl) + "\n" + "\n".join(out) + "\nendmodule\n")
    ct = open(C + "/ctree.tcl").read()
    pins = [l for l in ct.split("\n") if l.startswith("place_pin")]
    insts = [re.sub(r"-name (\S+)", r"-name ck_\1", l) for l in ct.split("\n") if l.startswith("place_inst")]
    p = pre.replace("read_verilog /work/grt/route.v",
                    "foreach f [glob $::env(LIBDIR)/*RVT_$::env(CORNER)_nldm*.lib*] { read_liberty $f }\nread_verilog /out/clkonly.v")
    p = p.replace(re.search(r"link_design \S+", p).group(0), "link_design die_combo")
    ndr = ("create_ndr -name CK2W2S -width {M8 0.08 M9 0.08} -spacing {M8 0.32 M9 0.32}\n"
           "assign_ndr -ndr CK2W2S -all_clocks\nputs \"OT_NDR CK2W2S [llength [get_nets -hierarchical ck_*]]\"\n") if NDR == "2w2s" else ""
    tail = f"""source /out/obs_pg.tcl
puts "OT_T obs [expr {{[clock seconds]-$t0}}]"
{chr(10).join(pins)}
{chr(10).join(insts)}
puts "OT_T clockplaced [expr {{[clock seconds]-$t0}}]"
create_clock -name dck -period 833.0 [get_ports root]
set_routing_layers -signal M4-M9 -clock M8-M9
{chr(10).join(f"set_global_routing_layer_adjustment {L} {a}" for L, a in adj)}
{ndr}if {{[catch {{global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose -congestion_report_file /out/congestion_$::env(CORNER).rpt}} e]}} {{ puts "OT_GRT_ERROR $e" }}
puts "OT_T grt [expr {{[clock seconds]-$t0}}]"
if {{[catch {{grt::report_layer_wire_lengths}} e]}} {{ puts "OT_NO_LAYER_WL $e" }}
write_guides /out/route_$::env(CORNER).guide
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
delete_clock [get_clocks dck]
estimate_parasitics -global_routing
create_clock -name vclk -period 833.0
set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]
set_input_delay 0 -clock vclk [get_ports root]
set_load 3.0 [get_ports t_*]
set_output_delay 0 -clock vclk [get_ports t_*]
set fh [open /out/arr_$::env(CORNER).txt w]
foreach p [get_ports t_*] {{ puts $fh "T [get_full_name $p] [expr {{833.0 - [get_property $p slack_max_rise]}}] [get_property $p slack_min_rise] [get_property $p slew_max_rise]" }}
foreach i [get_cells ck_*] {{ set q [get_pins [get_full_name $i]/Y]; set a [get_pins [get_full_name $i]/A]; puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise] [get_property $a slew_max_rise] [get_property $q slew_max_rise]" }}
close $fh
report_check_types -max_slew -max_capacitance -violators
report_check_types -min_pulse_width -violators
puts OT_DONE
"""
    # DIE-QC-11: inverter tree (--clock-cell inv) -> per instance output polarity from ctree.v; N readout takes the
    # edge that carries the source RISING edge (fall at an odd-parity output); F lines = tap fall/rise (duty readout)
    drv = {}
    for mm in re.finditer(r"^\s+(\S+) (\S+) \(\.A\((\S+)\), \.Y\((\S+)\)\);", cv, re.M):
        drv[mm.group(4)] = (mm.group(1), mm.group(2), mm.group(3))
    par = {}

    def parity(net):
        st = []
        while net != "root" and net not in par:
            st.append(net)
            net = drv[net][2]
        v = par.get(net, 0)
        for n_ in reversed(st):
            v = (v + ("INV" in drv[n_][0])) % 2
            par[n_] = v
        return v
    odd = sorted("ck_" + drv[n_][1] for n_ in drv if parity(n_))
    oddtcl = "set ot_odd [dict create " + " ".join(f"{x} 1" for x in odd) + "]\n"
    tail = tail.replace("set fh [open", oddtcl + "set fh [open", 1)
    tail = tail.replace('puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise]',
                        'set e [expr {[dict exists $ot_odd [get_full_name $i]] ? "fall" : "rise"}]; set g [expr {$e eq "fall" ? "rise" : "fall"}]; puts $fh "M [string range [get_full_name $i] 3 end] [get_property $q arrival_max_$g] [get_property $q arrival_min_$g]"; puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_$e] [get_property $q arrival_min_$e]', 1)
    tail = tail.replace('foreach p [get_ports t_*] { puts $fh "T ',
                        'foreach p [get_ports t_*] { puts $fh "F [get_full_name $p] [expr {833.0 - [get_property $p slack_max_fall]}] [expr {833.0 - [get_property $p slack_max_rise]}] [get_property $p slew_max_fall]" }\nforeach p [get_ports t_*] { puts $fh "T ', 1)
    assert "ot_odd" in tail and '"F ' in tail and '"M ' in tail, "readout patch did not apply"
    print("odd-parity clock instances", len(odd))
    open(O + "/clk.tcl", "w").write(p + tail)
    print("clock-only ports", len(rports), len(cports), "macros", sum(1 for b in body if b.endswith("();")), "ck insts", len(insts), "ndr", NDR)
else:   # sig: kit signal GRT with the frozen stage-1 clock as obstructions
    guide, ntr = sys.argv[5], float(sys.argv[6]) if len(sys.argv) > 6 else 5.0
    hw = ntr * 0.08 / 2
    rects, cur = [], None
    for line in open(guide):
        s = line.split()
        if len(s) == 1 and s[0] not in ("(", ")"):
            cur = s[0]; continue
        if len(s) == 5 and s[4] in ("M8", "M9"):
            x0, y0, x1, y1 = (float(v) / 1000.0 for v in s[:4])      # guide DBU (1000 / um)
            if s[4] == "M8" and x1 - x0 > (y1 - y0) * 1.5:
                yc = (y0 + y1) / 2; rects.append(("M8", x0, yc - hw, x1, yc + hw))
            elif s[4] == "M9" and y1 - y0 > (x1 - x0) * 1.5:
                xc = (x0 + x1) / 2; rects.append(("M9", xc - hw, y0, xc + hw, y1))
    with open(O + "/obs_sig.tcl", "w") as fo:
        fo.write("\n".join(obs[:npg]) + "\n")
        for L, a, b, c, d in rects:
            fo.write(f"create_obstruction -region {{{a:.3f} {b:.3f} {c:.3f} {d:.3f}}} -layer {L}\n")
    s = t.replace("source /work/grt/obs.tcl", "source /out/obs_sig.tcl").replace("/work/grt/congestion.rpt", "/out/congestion_sig.rpt").replace("write_guides /work/grt/route.guide", "write_guides /out/route_sig.guide")
    open(O + "/sig.tcl", "w").write(s)
    print("frozen clock obstructions", len(rects), "pg", npg, "track width", ntr)
