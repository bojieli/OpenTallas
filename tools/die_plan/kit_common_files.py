"""KIT-COMMON-1117 (COORD, S81-CORES-R3): the generator-independent run helpers every core kit carries.

ONE list, read by EVERY kit writer, so no generator can miss a helper the shared kit tools source:
  - tools/die_plan/gen_phys.py write_type_kit (type kits)
  - tools/die_plan/core_flow.py apply (gen_core_kit_legacy.py, gen_core_kit_qc.py, gen_core_kit_kv.py)
  - physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py, physical/die_plan/hbm/cores/harden/gen_core_kit.py,
    physical/die_plan/s81/cores/eng/gen_core_kit.py, physical/die_plan/s81/cores/svc/gen_core_kit_s81.py
  - tools/ref_tile/ref_tile.py gen
test_kit_common_files.py classifies every gen_*kit*.py in the repo (writer / delegate / exempt): a new generator
fails the test until it reads this list or names the writer it delegates to.
Why: 11-17 a legacy-profile kit (dsdv_bksel_c_rfdq) and the QC core kits (6 KV ring masters) carried
core_final_repair.tcl, which sources hold_sdc_guard.tcl, but not the guard (only gen_phys copied it, HOLD-SDC-1116):
5_1_grt died after a clean hold repair.

Listed: helpers the SHARED kit tools reference (core_final_repair.tcl / pregrt_ff_hold -> hold_sdc_guard.tcl,
lec.py -> native_bb.py, lec_async.sh -> lec_completed_*.py, port binding -> port_bind_gate.py) and the hold
helpers several writers already copied.  Not listed on purpose: names a writer ships its own version of
(hold_gate.tcl: hbm_arch_cores has its own; signoff.py stages tools' copy by dependency), generator-specific hooks,
and helpers whose mere presence switches a kit step on (adder_map_dontuse.py, stage_odb_cap.py, partition_ir.py)."""
import importlib.util
import shutil
from pathlib import Path

TOOL = Path(__file__).resolve().parent
REPO = TOOL.parents[1]

# kit file name -> source path relative to the repo
FILES = {
    "hold_sdc_guard.tcl": "tools/die_plan/hold_sdc_guard.tcl",
    "hold_pad_hb4.tcl": "physical/common_flow/hold_pad_hb4.tcl",
    "orfs_hold_mm.py": "tools/orfs_hold_mm.py",
    "port_bind_gate.py": "tools/die_plan/port_bind_gate.py",
    "native_bb.py": "tools/die_plan/native_bb.py",
    "lec_completed_transfer.py": "tools/die_plan/lec_completed_transfer.py",
    "lec_completed_reference.py": "tools/die_plan/lec_completed_reference.py",
}


def _common_flow_file(name, repo):
    """physical/common_flow/<name> (from git HEAD in a sparse checkout without it; common_flow_src.py), loaded by
    path so this module never puts tools/die_plan on sys.path of the writer that imports it"""
    cfs = TOOL / "common_flow_src.py"
    if cfs.is_file():
        spec = importlib.util.spec_from_file_location("_kcf_common_flow_src", cfs)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return Path(mod.common_flow_file(name, repo))
    return Path(repo) / "physical/common_flow" / name


def source(name, repo=REPO):
    """the source file for kit helper `name`"""
    rel = FILES[name]
    if rel.startswith("physical/common_flow/"):
        return _common_flow_file(Path(rel).name, repo)
    return Path(repo) / rel


def stage(kd, repo=REPO):
    """copy every shared helper into kit dir kd; returns the kit file names"""
    kd = Path(kd)
    for name in FILES:
        shutil.copyfile(source(name, repo), kd / name)
    return sorted(FILES)


def load(repo=REPO):
    """this module, loaded by path (for writers outside tools/die_plan: tools/ref_tile/ref_tile.py)"""
    spec = importlib.util.spec_from_file_location("kit_common_files", Path(repo) / "tools/die_plan/kit_common_files.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
