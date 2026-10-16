#!/usr/bin/env python3
"""Generate four source-specific VM bank probes from the die lead's actual grant.

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

GRANT = "results/arch/hbm_die_v15/vm_identity_grants_1417.json"

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
        if not slot["cell"].endswith("_b0"):
            continue
        q = int(re.search(r"_q(\d)_", slot["cell"])[1])
        for rel, digest in slot["source_dependencies_sha256"].items():
            assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == digest, rel
        name = f"vm_identity_q{q}_b0_ref"
        kd = ROOT / "physical/ref_tile" / name
        hd_rel = f"physical/hbm_vm_identity_1015/q{q}_b0"
        hd = ROOT / hd_rel
        hd.mkdir(parents=True, exist_ok=True)
        s = json.loads((ROOT / "physical/ref_tile/vms_bank_vsh1_rg4wg1_1015/spec.json").read_text())
        s.update(name=name, top=slot["cell"],
                 sources=[slot["source"], "rtl/hbm_accel/generic/vm/static/ot_vms_bank_static_identity.sv",
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
        io = ["# Source-exact die bit grant (explicit per-bit actual-track, PG-clear centres); PG BTerms are preserved.",
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
        purpose = ("Source-specialized bank from actual literal quadrant/slice identity; identity ports and FFs removed, "
                   "no static-input timing waiver. CE status gains one registered carry edge; data calendars unchanged. "
                   "Die grant r2: every bit on an actual M4/M5 track, M5 centres clear of PG stripe projections (q1 identity1 gate: "
                   "3068 off-track centres + 95 PG projections), placed by the shared exact-pin helper; actual ODB coordinate/track/PG readback. Diagnostic child only; "
                   "no parent/die binding or physical qualification claimed.")
        s["job"] = {"owner": "Claude H-SM", "branch": "claude/hbm-sm-attention-1015", "tag": "identity2",
                    "purpose": purpose, "structural_change": purpose,
                    "extra_paths": ["rtl/hbm_accel/generic/vm/static", hd_rel, GRANT,
                                    "physical/common_flow/assigned_pin_exact.tcl"],
                    "record_to": f"results/rtl/ref_tile/{name}", "views_to": f"physical/ref_tile/{name}/views",
                    "benches": [{"name": "literal_banks_and_wrong_compiled_identity",
                                 "cmd": f"bash rtl/hbm_accel/generic/vm/static/identity/run_identity_wrappers.sh {{RUN}}/bench/literal {q} && bash rtl/hbm_accel/generic/vm/static/identity/run_identity.sh {{RUN}}/bench/identity {q}",
                                 "expect": "pass", "threads": 1, "peak_ram_gb": 2,
                                 "min_count_regex": r"eachgroup_reads=(\d+)"}]}
        kd.mkdir(parents=True, exist_ok=True)
        (kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print(json.dumps(RT.gen(str(kd / "spec.json"))))


if __name__ == "__main__":
    make()
