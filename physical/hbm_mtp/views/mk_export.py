#!/usr/bin/env python3
"""mtp-lead 2026-10-09: die-view export scripts for a CLOSED block from its INSTALLED 6_final.{odb,sdc,spef}
(post-ECO when the loop installed a hold ECO).  Writes export_{ss,ff,tt}.tcl into OUT: propagated clocks,
write_timing_model per corner (RVT + LVT/SLVT twins, since ECO/LVT cells may be present), write_abstract_lef in the TT run.

    mk_export.py MASTER OUT
"""
import sys

master, out = sys.argv[1], sys.argv[2]
P = "/OpenROAD-flow-scripts/flow/platforms/asap7"
LIBS = {"SS": ["AO_RVT_SS_nldm_211120.lib.gz", "INVBUF_RVT_SS_nldm_220122.lib.gz", "OA_RVT_SS_nldm_211120.lib.gz",
               "SEQ_RVT_SS_nldm_220123.lib", "SIMPLE_RVT_SS_nldm_211120.lib.gz"],
        "FF": ["AO_RVT_FF_nldm_211120.lib.gz", "INVBUF_RVT_FF_nldm_220122.lib.gz", "OA_RVT_FF_nldm_211120.lib.gz",
               "SEQ_RVT_FF_nldm_220123.lib", "SIMPLE_RVT_FF_nldm_211120.lib.gz"],
        "TT": ["AO_RVT_TT_nldm_211120.lib.gz", "INVBUF_RVT_TT_nldm_220122.lib.gz", "OA_RVT_TT_nldm_211120.lib.gz",
               "SEQ_RVT_TT_nldm_220123.lib", "SIMPLE_RVT_TT_nldm_211120.lib.gz"]}
for c, libs in LIBS.items():
    L = [f"read_lef {P}/lef/asap7_tech_1x_201209.lef", f"read_lef {P}/lef/asap7sc7p5t_28_R_1x_220121a.lef"]
    for lib in libs:
        for v in ("RVT", "LVT", "SLVT"):
            f = f"{P}/lib/NLDM/asap7sc7p5t_{lib.replace('_RVT_', '_' + v + '_')}"
            L.append(f"if {{[file exists {f}]}} {{read_liberty {f}}}")
    L += ["read_db /in/6_final.odb", "read_sdc /in/6_final.sdc", "read_spef /in/6_final.spef",
          "set_propagated_clock [all_clocks]",
          f'puts "OT_{c}_WS setup_ns=[sta::worst_slack_cmd max] hold_ns=[sta::worst_slack_cmd min]"',
          f"write_timing_model -library_name {master}_{c.lower()} /w/{master}_{c.lower()}.lib"]
    if c == "TT":
        L.append(f"write_abstract_lef /w/{master}.lef")
    L += ["puts OT_EXPORT_DONE", "exit"]
    open(f"{out}/export_{c.lower()}.tcl", "w").write("\n".join(L) + "\n")
