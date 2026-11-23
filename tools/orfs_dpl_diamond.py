#!/usr/bin/env python3
"""CTS-DPL-DIAMOND-1123 b (COORD 11:0x, QC btab_s4r DPL-0033 after CTS): the diamond-legalizer fallback of
physical/common_flow/grt183_make.sh (CTS-DPL-DIAMOND-1123 in cts.tcl, GRT-DPL-DIAMOND-1122 in global_route.tcl) for
flows that do not run through that wrapper: the ref_tile / closure_loop hard-core runner (tools/run_abi3_physical.py)
patches its DISPOSABLE container copy of the ORFS scripts with this tool, beside tools/orfs_hold_mm.py.  Same Tcl
lines, byte for byte (tools/test_orfs_dpl_diamond.py checks it): a bare detailed_placement takes the kit
DETAIL_PLACEMENT_ARGS when they select -use_diamond_legalizer, and any non-diamond pass that leaves check_placement
failing gets ONE diamond pass.  A legal result is untouched.  Opt out: OT_CTS_DPL_ARGS=0 / OT_GRT_DPL_ARGS=0 in the
environment or 'export OT_CTS_DPL_ARGS = 0' / 'export OT_GRT_DPL_ARGS = 0' in the given config.mk.
   orfs_dpl_diamond.py <ORFS scripts dir> [<config.mk>]"""
import os
import re
import sys
from pathlib import Path

CTS_LINE = ('set ::ot_kit_dpl_args [expr {[info exists ::env(DETAIL_PLACEMENT_ARGS)] ? [string trim $::env(DETAIL_PLACEMENT_ARGS)] : ""}]; '
        'if {[info commands ::ot_cts_dpl_orig] eq "" && [info commands ::detailed_placement] ne ""} { '
        'rename ::detailed_placement ::ot_cts_dpl_orig; '
        'proc ::detailed_placement {args} { '
        'set kd [expr {[string first -use_diamond_legalizer $::ot_kit_dpl_args] >= 0}]; '
        'if {![llength $args] && $kd} { set args $::ot_kit_dpl_args }; '
        'set rc [catch {uplevel 1 [list ::ot_cts_dpl_orig {*}$args]} res opts]; '
        'if {[lsearch -exact $args -use_diamond_legalizer] < 0 && [catch {check_placement}]} { '
        'set da [expr {$kd ? $::ot_kit_dpl_args : "-use_diamond_legalizer"}]; '
        'puts "OT_CTS_DPL_ARGS residual: CTS detailed_placement left an illegal placement (rc $rc), one diamond pass: $da"; '
        'return [uplevel 1 [list ::ot_cts_dpl_orig {*}$da]] }; '
        'return -options $opts $res }; '
        'puts "OT_CTS_DPL_ARGS: CTS detailed_placement kit args [expr {[string first -use_diamond_legalizer $::ot_kit_dpl_args] >= 0 ? $::ot_kit_dpl_args : {(negotiation; diamond pass on an illegal result)}}]" } ;# OT_CTS_DPL_ARGS')
GRT_LINE = ('set ::ot_grt_dpl_args [expr {[info exists ::env(DETAIL_PLACEMENT_ARGS)] ? [string trim $::env(DETAIL_PLACEMENT_ARGS)] : ""}]; '
        'if {[info commands ::ot_grt_dpl_orig] eq "" && [info commands ::detailed_placement] ne ""} { '
        'rename ::detailed_placement ::ot_grt_dpl_orig; '
        'proc ::detailed_placement {args} { '
        'set kd [expr {[string first -use_diamond_legalizer $::ot_grt_dpl_args] >= 0}]; '
        'if {![llength $args] && $kd} { set args $::ot_grt_dpl_args }; '
        'set rc [catch {uplevel 1 [list ::ot_grt_dpl_orig {*}$args]} res opts]; '
        'if {[lsearch -exact $args -use_diamond_legalizer] < 0 && [catch {check_placement}]} { '
        'set da [expr {$kd ? $::ot_grt_dpl_args : "-use_diamond_legalizer"}]; '
        'puts "OT_GRT_DPL_ARGS residual: GRT detailed_placement left an illegal placement (rc $rc), one diamond pass: $da"; '
        'return [uplevel 1 [list ::ot_grt_dpl_orig {*}$da]] }; '
        'return -options $opts $res }; '
        'puts "OT_GRT_DPL_ARGS: GRT detailed_placement kit args [expr {[string first -use_diamond_legalizer $::ot_grt_dpl_args] >= 0 ? $::ot_grt_dpl_args : {(negotiation; diamond pass on an illegal result)}}]" } ;# OT_GRT_DPL_ARGS')

STAGES = (("cts.tcl", "cts", "OT_CTS_DPL_ARGS", CTS_LINE), ("global_route.tcl", "grt", "OT_GRT_DPL_ARGS", GRT_LINE))


def opted_out(key, config=None):
    if os.environ.get(key, "").strip() == "0":
        return True
    if config and Path(config).is_file():
        return bool(re.search(r"(?m)^export " + key + r"[ \t]*=[ \t]*0[ \t]*$", Path(config).read_text(errors="replace")))
    return False


def patch(scripts, config=None):
    out = {}
    for name, stage, key, line in STAGES:
        p = Path(scripts) / name
        if not p.is_file():
            out[name] = "missing"
            continue
        s = p.read_text()
        if key in s:
            out[name] = "already patched"
            continue
        if opted_out(key, config):
            out[name] = "opted out"
            continue
        s2, n = re.subn(r"(?m)^( *)(erase_non_stage_variables " + stage + r")",
                        lambda m: m.group(1) + line + "\n" + m.group(1) + m.group(2), s, count=1)
        if n != 1:
            out[name] = "inactive (no erase_non_stage_variables " + stage + ")"
            continue
        p.write_text(s2)
        out[name] = "patched"
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    r = patch(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print("orfs_dpl_diamond: " + ", ".join(f"{k} {v}" for k, v in r.items()))
