#!/usr/bin/env python3
"""Replay real placed hybrid-leaf CTS and inspect actual post-CTS OpenDB.

Run this through ot-run. FIXTURE is a retained pre_route_gate remote run;
the helper is mounted over its original clock_entries.tcl, with every other
source and all timing/ownership checks retained. Negative cases alter actual
OpenDB connectivity, not RTL text or mocked timing records.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


DUMP = r'''
 set b [ord::get_db_block]
 foreach name {clk_macro0 clk_macro1 clk_macro2 clk_macro3 clk_macro4 clk_macro5} {
  set bt [$b findBTerm $name];set net [$bt getNet]
  set ni {};foreach it [$net getITerms] {lappend ni "[[$it getInst] getName]/[[$it getMTerm] getName]"}
  set nb {};foreach t [$net getBTerms] {lappend nb [$t getName]}
  puts "TOPOLOGY_SOURCE $name net=[$net getName] bterms=$nb iterms=$ni"
 }
 write_db /work/probe_post_cts.odb
 if {$probe_rc} {return -options $probe_options $probe_error}
'''

MUTANTS = {
    "positive": "",
    "shared_macro_source": r'''
 set b [ord::get_db_block];set net [[$b findBTerm clk_macro0] getNet]
 set cell [lindex [get_cells -hierarchical *g_read?1?.u_m] 0]
 set inst [sta::sta_to_db_inst $cell];set pin [$inst findITerm clk]
 $pin disconnect;$pin connect $net
''',
    "standard_cell_on_raw_source": r'''
 set b [ord::get_db_block];set net [[$b findBTerm clk_macro0] getNet]
 set pin [lindex [all_registers -clock ot_entry_0 -clock_pins] 0]
 set cell [lindex [get_cells -of_objects $pin] 0]
 set inst [sta::sta_to_db_inst $cell]
 set term [$inst findITerm [get_property $pin lib_pin_name]]
 $term disconnect;$term connect $net
''',
    "raw_source_declared_cts": "lappend ::ot_ce_cts_roots clk_macro0\n",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(fixture, helper, out, image):
    source = fixture / "src"
    original = fixture / "routes/gate/work/orfs"
    receipt = dict(qualified=False, scope="actual CTS topology regression; no routed timing/DRC claim",
                   fixture=str(fixture), helper_sha256=sha(helper), cases=[])
    receipt["source_placed_odb_sha256"] = sha(next((original / "results/asap7").glob("*/base/3_place.odb")))
    receipt["source_netlist_sha256"] = sha(next((original / "results/asap7").glob("*/base/1_2_yosys.v")))
    for mode, mutation in MUTANTS.items():
        case = out / mode
        work = case / "orfs"
        shutil.copytree(original, work, symlinks=True)
        hook = work / "hooks/pre_cts_ot_cts_fix.tcl"
        hook.write_text(hook.read_text() + "\nrename clock_tree_synthesis probe_cts_original\n"
                        + "proc clock_tree_synthesis {args} {\n" + mutation
                        + "set probe_rc [catch {probe_cts_original {*}$args} probe_error probe_options]\n"
                        + DUMP + "\n}\n")
        args = ["docker", "run", "--rm", "-v", f"{source}:/src:ro", "-v", f"{work}:/work",
                "-v", f"{helper}:/src/physical/common_flow/clock_entries.tcl:ro",
                "-w", "/OpenROAD-flow-scripts/flow", image, "bash", "-lc",
                "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
                "python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && "
                "make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base cts"]
        with (case / "flow.log").open("w") as log:
            proc = subprocess.run(args, stdout=log, stderr=subprocess.STDOUT)
        text = (case / "flow.log").read_text()
        topology = [line for line in text.splitlines() if line.startswith("TOPOLOGY_SOURCE ")]
        row = dict(name=mode, returncode=proc.returncode, topology=topology,
                   log_sha256=sha(case / "flow.log"))
        odb = work / "probe_post_cts.odb"
        row["post_cts_odb_sha256"] = sha(odb) if odb.exists() else None
        if mode == "positive":
            expected = []
            for index, line in enumerate(topology):
                expected.append(bool(re.fullmatch(
                    rf"TOPOLOGY_SOURCE clk_macro{index} net=clk_macro{index} bterms=clk_macro{index} "
                    + rf"iterms=\{{?u_bank\.u_data\.g_read.*{index}.*\.u_m/clk\}}?", line)))
            row["passed"] = (proc.returncode == 0 and len(topology) == 6 and all(expected)
                             and "OT_HYBRID excluded hard entries:" in text
                             and "OT_MULTI_ROOT OWNERSHIP PASS" in text)
        else:
            row["passed"] = (proc.returncode != 0 and bool(re.search(
                r"OT_ENTRIES: .*clock entries|OT_HYBRID: CTS source .*?(?:standard-cell clock pins|has no registers)", text)))
        receipt["cases"].append(row)
        (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(mode, "PASS" if row["passed"] else "FAIL", "rc", proc.returncode, flush=True)
    receipt["regression_passed"] = all(row["passed"] for row in receipt["cases"])
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return 0 if receipt["regression_passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--image", default="openroad/orfs:latest")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    raise SystemExit(run(args.fixture.resolve(), args.helper.resolve(), args.out.resolve(), args.image))
