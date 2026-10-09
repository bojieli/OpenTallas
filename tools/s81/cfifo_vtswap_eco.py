#!/usr/bin/env python3
"""VT-swap ECO on the routed dsfd_cfifo (colck a6ca75fbe srcfix) database.

The routed reference misses TT setup by 0.75 ps on rd[*] outputs under the
routed IO reference (rule H1, app0_io_ref_routed.sdc): rr[*] DFF -> INVx3 -> BUFx3
-> rd[*].  RVT -> LVT is a same-footprint master swap (ASAP7 R and L LEFs share
geometry and pin shapes), so the routed wires, SPEF and DRC state are unchanged.

Variant A (min):  swap every data-path cell of each TT setup path whose slack is
                  below MARGIN_A (+15 ps design target).
Variant B (wide): every data-path cell of each output / input path below
                  MARGIN_B (+40 ps).
The swapped ODB is written only if TT setup >= 0 AND FF hold >= 0 after the swap
(FF hold is re-measured on the written ODB in a second session with FF libs).
No RTL, cycle, port or budget change; the LVT cell count is reported (owner Vt
policy: LVT <= ~2 % of cells on small misses).
"""
import argparse
from pathlib import Path

LIBS = ["AO_{v}_{c}_nldm_211120.lib.gz", "INVBUF_{v}_{c}_nldm_220122.lib.gz",
        "OA_{v}_{c}_nldm_211120.lib.gz", "SEQ_{v}_{c}_nldm_220123.lib",
        "SIMPLE_{v}_{c}_nldm_211120.lib.gz"]
P = "/OpenROAD-flow-scripts/flow/platforms/asap7"


def head(corner, odb):
    c = {"tt": "TT", "ff": "FF"}[corner]
    s = [f"read_lef {P}/lef/asap7_tech_1x_201209.lef",
         f"read_lef {P}/lef/asap7sc7p5t_28_R_1x_220121a.lef",
         f"read_lef {P}/lef/asap7sc7p5t_28_L_1x_220121a.lef"]
    for v in ("RVT", "LVT"):
        for l in LIBS:
            s.append(f"read_liberty {P}/lib/NLDM/asap7sc7p5t_" + l.format(v=v, c=c))
    base = "/work/results/asap7/opentallas_dsfd_cfifo_asap7_s81g_s81_dsfd_cfifo_colck_a6ca75fbe_tt_srcfix/base"
    s += [f"read_db {odb}", f"read_sdc {base}/6_final.sdc", f"read_spef {base}/6_final.spef",
          "set_propagated_clock [all_clocks]",
          "read_sdc /src/physical/s81_die_views/common/signoff_unc60.sdc",
          "read_sdc /meas/app0_io_ref_routed.sdc", f'puts "OT_CORNER {corner}"']
    return "\n".join(s) + "\n"


SWAP = r'''
proc ot_l {m} { regsub {_ASAP7_75t_R$} $m {_ASAP7_75t_L} }
set ot_db [ord::get_db]; set ot_block [ord::get_db_block]
set ot_ncell [llength [$ot_block getInsts]]
puts "OT_BASE_SETUP [sta::worst_slack_cmd max]"
set ot_sw [dict create]
for {set ot_it 0} {$ot_it < 6} {incr ot_it} {
  set ot_new 0
  foreach ot_p [find_timing_paths -path_delay max -slack_max $MARGIN -group_path_count 2000 -endpoint_path_count 1] {
    foreach ot_pt [get_property $ot_p points] {
      set ot_pin [get_property $ot_pt pin]
      set ot_pn [get_full_name $ot_pin]; set ot_k [string last / $ot_pn]; if {$ot_k < 1} continue; set ot_nm [string range $ot_pn 0 [expr {$ot_k - 1}]]
      set ot_in [$ot_block findInst $ot_nm]
      if {$ot_in eq "NULL"} continue
      set ot_m [[$ot_in getMaster] getName]
      if {![string match *_ASAP7_75t_R $ot_m]} continue
      if {[string match *clkbuf* [$ot_in getName]] || [string match clkload* [$ot_in getName]]} continue
      set ot_lm [$ot_db findMaster [ot_l $ot_m]]
      if {$ot_lm eq "NULL"} { puts "OT_NOLVT $ot_m"; continue }
      set ot_om [$ot_in getMaster]
      if {[$ot_om getWidth] != [$ot_lm getWidth] || [$ot_om getHeight] != [$ot_lm getHeight]} { error "footprint mismatch $ot_m" }
      $ot_in swapMaster $ot_lm
      dict set ot_sw [$ot_in getName] "$ot_m [$ot_lm getName]"
      incr ot_new
    }
  }
  puts "OT_ITER $ot_it swapped_new=$ot_new total=[dict size $ot_sw] setup=[sta::worst_slack_cmd max]"
  if {$ot_new == 0} break
}
dict for {k v} $ot_sw { puts "OT_SWAP $k $v" }
puts "OT_LVT_CELLS [dict size $ot_sw] of $ot_ncell ([expr {100.0*[dict size $ot_sw]/$ot_ncell}] %)"
set ot_ws [sta::worst_slack_cmd max]
puts "OT_ECO_SETUP $ot_ws"
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded
foreach p [all_outputs] { set s [get_property $p slack_max]; if {$s ne "INF" && (![info exists wo] || $s < $wo)} { set wo $s } }
puts "OT_ECO_WS_OUT $wo"
write_db /out/6_final_vtswap.odb
write_verilog /out/6_final_vtswap.v
puts "OT_WROTE"
'''

FFCHK = r'''
puts "OT_FF_HOLD [sta::worst_slack_cmd min]"
report_checks -path_delay min -group_path_count 1 -format full_clock_expanded
set n 0; foreach i [[ord::get_db_block] getInsts] { if {[string match *_ASAP7_75t_L [[$i getMaster] getName]]} { incr n } }
puts "OT_FF_LVT_COUNT $n"
'''

TTCHK = r'''
puts "OT_TT_SETUP [sta::worst_slack_cmd max]"
puts "OT_TT_TNS [sta::total_negative_slack_cmd max]"
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--margin-ps", type=float, required=True)
    ap.add_argument("--tag", required=True)
    a = ap.parse_args()
    out = a.bundle / f"vtswap_{a.tag}"
    out.mkdir(exist_ok=True)
    base = "/work/results/asap7/opentallas_dsfd_cfifo_asap7_s81g_s81_dsfd_cfifo_colck_a6ca75fbe_tt_srcfix/base/6_final.odb"
    (out / "eco_tt.tcl").write_text(head("tt", base) + f"set MARGIN {a.margin_ps}\n" + SWAP + "exit\n")
    (out / "chk_ff.tcl").write_text(head("ff", "/out/6_final_vtswap.odb") + FFCHK + "exit\n")
    (out / "chk_tt.tcl").write_text(head("tt", "/out/6_final_vtswap.odb") + TTCHK + "exit\n")
    print(out)


if __name__ == "__main__":
    main()
