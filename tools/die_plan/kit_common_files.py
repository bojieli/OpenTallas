"""KIT-COMMON-1117 (COORD, S81-CORES-R3): the generator-independent run helpers every core kit carries.

ONE list, read by both kit paths, so they cannot drift:
  - tools/die_plan/gen_phys.py write_type_kit (type kits)
  - tools/die_plan/core_flow.py apply (gen_core_kit_legacy.py legacy-profile kits and the other core generators)
Why: dsdv_bksel_c_rfdq 11-17 (a legacy-profile kit) carried core_final_repair.tcl, which sources hold_sdc_guard.tcl,
but not the guard itself (only gen_phys copied it, HOLD-SDC-1116), so 5_1_grt died after a clean hold repair.

Listed: helpers that the SHARED kit tools reference (core_final_repair.tcl / hold_pad_hb4.tcl / pregrt_ff_hold ->
hold_sdc_guard.tcl, signoff.py -> hold_gate.tcl, lec.py -> native_bb.py, lec_async.sh -> lec_completed_*.py,
port binding -> port_bind_gate.py) plus the hold helpers both paths already copied.
Not listed on purpose: generator-specific hooks, and helpers whose mere presence switches a kit step on
(adder_map_dontuse.py, stage_odb_cap.py, partition_ir.py): adding those to every kit would change other flows, so
they stay with the generator that opts in."""
import shutil
from pathlib import Path

TOOL = Path(__file__).resolve().parent
REPO = TOOL.parents[1]

# kit file name -> source path relative to the repo
FILES = {
    "hold_sdc_guard.tcl": "tools/die_plan/hold_sdc_guard.tcl",
    "hold_pad_hb4.tcl": "physical/common_flow/hold_pad_hb4.tcl",
    "orfs_hold_mm.py": "tools/orfs_hold_mm.py",
    "hold_gate.tcl": "tools/die_plan/hold_gate.tcl",
    "port_bind_gate.py": "tools/die_plan/port_bind_gate.py",
    "native_bb.py": "tools/die_plan/native_bb.py",
    "lec_completed_transfer.py": "tools/die_plan/lec_completed_transfer.py",
    "lec_completed_reference.py": "tools/die_plan/lec_completed_reference.py",
}


def source(name, repo=REPO):
    """the source file for kit helper `name` (physical/common_flow from git HEAD in a sparse checkout without it)"""
    rel = FILES[name]
    if rel.startswith("physical/common_flow/"):
        try:
            import sys
            sys.path.insert(0, str(TOOL))
            from common_flow_src import common_flow_file
        except ImportError:
            return Path(repo) / rel
        return Path(common_flow_file(Path(rel).name, repo))
    return Path(repo) / rel


def stage(kd, repo=REPO):
    """copy every shared helper into kit dir kd; returns the kit file names"""
    kd = Path(kd)
    for name in FILES:
        shutil.copyfile(source(name, repo), kd / name)
    return sorted(FILES)
