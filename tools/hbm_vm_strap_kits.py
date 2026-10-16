#!/usr/bin/env python3
"""Generate the four STRAP-identity VM bank masters (one per quadrant, 8 banks each) from the strap grant proposal
(tools/hbm_die_v15/vm_strap_grant_1015.py: the identity2 r2 b0 grant + 5 strap pins).

The grant's bit centres are authoritative. The IO hook checks the resulting ODB,
including actual tracks and PG rectangles, before accepting a pin plan.
"""
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/ref_tile"))
import ref_tile as RT

GRANT = "results/arch/hbm_die_v15/vm_strap_grants_1015.json"

AUDIT = r'''
set vb [ord::get_db_block]
set vu [$vb getDbUnitsPerMicron]
set vt [ord::get_db_tech]
set vm_pg {}
foreach bt [$vb getBTerms] {
 if {[$bt getSigType] ni {POWER GROUND}} continue
 foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {
  lappend vm_pg [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
 }}
}
set vm_bad 0
set vm_rows [open [file join $::env(RESULTS_DIR) identity_actual_pins.tsv] w]
puts $vm_rows "port\tface\tlayer\texpected_um\tactual_um\ttrack_ok\tPG_projection_clear"
foreach item $vm_expected {
 lassign $item name face layer expected
 set bt [$vb findBTerm $name]
 if {$bt eq "NULL" || $bt eq "" || [llength [$bt getBPins]] != 1} {
  puts "VM_ID_PIN_ERROR missing/duplicate pin $name";incr vm_bad;continue
 }
 set boxes [[lindex [$bt getBPins] 0] getBoxes]
 if {[llength $boxes] != 1} {puts "VM_ID_PIN_ERROR rectangle count $name";incr vm_bad;continue}
 set box [lindex $boxes 0]
 set actual [expr {$face in {N S}?([$box xMin]+[$box xMax])/2.0:([$box yMin]+[$box yMax])/2.0}]
 set tl [$vt findLayer $layer]
 set grid [$vb findTrackGrid $tl]
 set tracks [expr {$face in {N S}?[$grid getGridX]:[$grid getGridY]}]
 set track_ok [expr {[lsearch -exact $tracks [expr {int(round($actual))}]] >= 0}]
 set pg_clear 1
 set half [expr {$face in {N S}?([$box xMax]-[$box xMin])/2.0:([$box yMax]-[$box yMin])/2.0}]
 set space [$tl getSpacing]
 foreach rect $vm_pg {
  lassign $rect pl ax ay bx by
  if {$pl ne $layer} continue
  set lo [expr {$face in {N S}?$ax:$ay}]
  set hi [expr {$face in {N S}?$bx:$by}]
  if {$actual+$half+$space>$lo && $actual-$half-$space<$hi} {set pg_clear 0;break}
 }
 set actual_um [expr {$actual/double($vu)}]
 if {abs($actual_um-$expected)>0.0001 || [[$box getTechLayer] getName] ne $layer || !$track_ok || !$pg_clear} {
  puts "VM_ID_PIN_ERROR $name expected=$expected actual=$actual_um track=$track_ok PG_clear=$pg_clear"
  incr vm_bad
 }
 puts $vm_rows "$name\t$face\t$layer\t$expected\t$actual_um\t$track_ok\t$pg_clear"
}
close $vm_rows
set vm_actual_signal 0
foreach bt [$vb getBTerms] {if {[$bt getSigType] ni {POWER GROUND}} {incr vm_actual_signal}}
if {$vm_actual_signal != [llength $vm_expected]} {incr vm_bad;puts "VM_ID_PIN_ERROR signal inventory $vm_actual_signal expected [llength $vm_expected]"}
source /src/tools/fp_margin_lint.tcl
ot_fp_lint_dump [file join $::env(RESULTS_DIR) identity_actual_pin_pg.json]
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
puts "VM_ID_PIN_READBACK checked=[llength $vm_expected] PG_shapes=[llength $vm_pg] violations=$vm_bad"
if {$vm_bad} {error "VM_ID_PIN_READBACK failed: $vm_bad actual coordinate/track/PG errors"}
'''


def make():
    grant = json.loads((ROOT / GRANT).read_text())
    for slot in grant["slots"]:
        q = int(re.search(r"_q(\d)$", slot["cell"])[1])
        rg, wg = {0: (5, 1), 1: (4, 1), 2: (6, 3), 3: (6, 3)}[q]          # run_identity.sh shapes (SID:RG:WG)
        name = f"vm_strap_q{q}_ref"
        kd = ROOT / "physical/ref_tile" / name
        hd_rel = f"physical/hbm_vm_strap_1015/q{q}"
        hd = ROOT / hd_rel
        hd.mkdir(parents=True, exist_ok=True)
        s = json.loads((ROOT / "physical/ref_tile/vms_bank_vsh1_rg4wg1_1015/spec.json").read_text())
        s.update(name=name, top=slot["cell"],
                 sources=[slot["source"], "rtl/hbm_accel/generic/vm/static/ot_vms_bank_static_strap.sv",
                          "rtl/hbm_accel/generic/vm/static/ot_vms_ce_counter_pipe.sv",
                          "physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v"],
                 contract={"file": GRANT, "slot": slot["name"]},
                 outline=dict(slot["outline"], exact=True), pins={f: [] for f in "NSEW"}, pin_ranges={},
                 io_tcl=f"{hd_rel}/io.tcl", orfs_vars={"POST_IO_PLACEMENT_TCL": f"{hd_rel}/post_iop.tcl"})
        w, h = slot["outline"]["w"], slot["outline"]["h"]
        expected = []
        for p in slot["pins"]:
            stem = p["name"].split("[")[0]
            s["pins"][p["face"]].append(stem)
            s["pin_ranges"][stem] = p["span_um"]
            m = re.search(r"\[(\d+):(\d+)\]", p["name"])
            n = int(m[1]) + 1 if m else 1
            assert not m or int(m[2]) == 0
            centres = p["bit_centres_um"]
            assert len(centres) == n, (p["name"], len(centres), n)
            for bit in range(n):
                expected.append((f"{stem}[{bit}]" if m else stem, p["face"], p["layer"], round(centres[bit], 9)))
        io = ["# Strap-master die bit grant proposal (explicit per-bit actual-track, PG-clear centres); PG BTerms are preserved.",
              "# Each pin is constructed at its granted centre by the shared exact helper (no place_pin snapping).",
              "source /src/physical/common_flow/assigned_pin_exact.tcl",
              "set vm_expected {", *[" {%s %s %s %.9f}" % row for row in expected], "}",
              f"set vm_w {w};set vm_h {h}",
              "set vm_block [ord::get_db_block]",
              "foreach bt [$vm_block getBTerms] {if {[$bt getSigType] in {POWER GROUND}} continue;foreach bp [$bt getBPins] {odb::dbBPin_destroy $bp}}",
              "foreach item $vm_expected {",
              " lassign $item name face layer along",
              " ot_assigned_pin_exact $name $layer $face $along", "}"]
        (hd / "io.tcl").write_text("\n".join(io) + "\n")
        (hd / "post_iop.tcl").write_text(f"source /src/{hd_rel}/io.tcl\n" + AUDIT)
        purpose = ("Strap-identity quadrant master (coordinator decision per DEDUPE, 2026-10-15): bank / slice identity is a "
                   "registered strap input (bid[2:0] / sid[1:0] pins, tied to die constants per instance, captured by pin flops), "
                   "so the 8 banks of the quadrant use this ONE view; replaces the 8 literal-identity masters. Same data "
                   "calendars and edges as identity2. Pins: identity2 r2 grant (actual tracks, PG-clear, explicit centres) + 5 "
                   "strap pins on free N-face tracks beside the clock pair (proposal for H-DIE).")
        s["job"] = {"owner": "Claude H-SM", "branch": "claude/hbm-sm-attention-1015", "tag": "strap1",
                    "purpose": purpose, "structural_change": purpose,
                    "extra_paths": ["rtl/hbm_accel/generic/vm/static", hd_rel, GRANT,
                                    "physical/common_flow/assigned_pin_exact.tcl"],
                    "record_to": f"results/rtl/ref_tile/{name}", "views_to": f"physical/ref_tile/{name}/views",
                    "benches": [{"name": "strap_core_and_8_strapped_instances",
                                 "cmd": f"bash rtl/hbm_accel/generic/vm/static/identity/run_strap.sh {{RUN}}/bench/strap {q}",
                                 "expect": "pass", "threads": 1, "peak_ram_gb": 2,
                                 "min_count_regex": r"eachgroup_reads=(\d+)"},
                                {"name": "wrong_bank_strap_mutant",
                                 "cmd": (f"cd rtl/hbm_accel/generic/vm/static/identity && iverilog -g2012 -s tb_hbm_vm_strap_wrappers "
                                         f"-Ptb_hbm_vm_strap_wrappers.SID={q} -Ptb_hbm_vm_strap_wrappers.RG={rg} -Ptb_hbm_vm_strap_wrappers.WG={wg} "
                                         "-Ptb_hbm_vm_strap_wrappers.MUT=3 -o {RUN}/mut3.vvp ../ot_vms_ce_counter_pipe.sv "
                                         f"../ot_vms_bank_static_strap.sv ../physical/hfd_vms_bank_strap_q{q}.sv ../../../../../../physical/asap7_memory_macros_v2/"
                                         "ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v tb_hbm_vm_strap_wrappers.sv && vvp {RUN}/mut3.vvp"),
                                 "expect": "fail", "fail_regex": r"FATAL: .*bank fault", "threads": 1, "peak_ram_gb": 2}]}
        s["pin_regs"] = {"enable": False, "reason": (
            "COORDINATOR DECISION 2026-10-15 (keep the opt-out): this tile already satisfies OWNER RULE 19:50 (every input and "
            "every output registered at its pin) in RTL; a recipe-3 register would be a SECOND stage and add +2 VM edges "
            "(request +1, response +1) with no timing benefit. Evidence, rtl/hbm_accel/generic/vm/static/ot_vms_bank_static_strap.sv "
            "(the wrapper physical/hfd_vms_bank_strap_q*.sv is wiring only): INPUTS -- L118 bid/sid strap registers; L127 payload pin "
            "flops rq_d/wq_d/dq_d/kq_d/xq_d/x2_d/pq_d <= rq/wq/dq/kq/xq/xq2/pq; L128-133 valid pin flops rq_v/wq_v/dq_v/kq_v/xq_v/x2_v/pq_v; "
            "L183-186 slot pin flops rslot_d/wslot_d/rslot_v_d/wslot_v_d; rst_n only into the 3-flop reset relay (L107-112). OUTPUTS -- "
            "L135-141 rr = {rr_v, rr_d}, eg = {eg_v, eg_d}, pr = {pr_v, pr_d} are registers (rr_d L415, pr_d L416, eg_d L282, "
            "rr_v/pr_v/status L400-409); wq_done/dq_done/kq_done/xq_done/xq2_done are output reg (L44-52, set L337-343); status "
            "output reg (L56, L409). Recipe-2 keep_pin_regs + io_flop_at_pins anchor these flops at their pins; synthesized "
            "output-flop census: physical/audit_bank_output_flops.py.")}
        # q2 (identity2: GPL-0305 twice) and q1 (strap1: GRT-0116, 49 overflow at the W mouth of the 20-um channel between
        # arrays 2 and 3, where both arrays' W-edge M4 pin rows meet; rendered 10-15 20:47): abutted centred stack, no
        # inter-array channel.  q3 strap1 failed the same way (verdict 20:57); q0 switched pre-emptively: all four stacked.
        if True:
            s2 = json.loads((ROOT / "physical/ref_tile/vm_identity_q2_b0_ref/spec.json").read_text())
            s["macros"] = s2["macros"]; s["floorplan_note"] = s2.get("floorplan_note", "")
            s["job"]["tag"] = "strap2" if q in (0, 1, 3) else s["job"]["tag"]
        kd.mkdir(parents=True, exist_ok=True)
        (kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print(json.dumps(RT.gen(str(kd / "spec.json"))))


if __name__ == "__main__":
    make()
