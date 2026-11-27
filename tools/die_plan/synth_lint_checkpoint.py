#!/usr/bin/env python3
"""Optional strict-lint RTLIL handoff for the qualified XS4 core kit."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rtl_lint

FLOW = Path("/OpenROAD-flow-scripts/flow")
CANON = FLOW / "scripts/synth_canonicalize.tcl"
MOUNT = Path("/work")
RECEIPT = "rtl_lint_checkpoint.json"
COMPILER_INPUT_DIGEST = "4d90976e4243cd5fe4f4536938c250983fbf69006308ce74df5139dbb846757a"
COMPILER_CONFIG_DIGEST = "a92f5607fc715b0fc8be17d700d0445b7c901074c89d85145a731fdad91a3095"
MACROS = ("ot_sram_1r1w_128x256_m1_r2c2", "ot_sram_1r1w2c_128x64_m1", "ot_rom_4096x72_m8")
WRAPPER_DIGEST = "7a69a9c5d6afb3e90436738ac548711319fd8afbd300cb788afef4910c2058b3"
RUNTIME_DIGEST = "72a5a397087d30be6ad5aaaa379e7a1c8d04cf4cf003317e10f1467ebfd77144"
RUNTIME_FILES = ["Makefile", *("scripts/" + n for n in (
    "synth_canonicalize.tcl", "synth_preamble.tcl", "synth_stdcells.tcl", "util.tcl", "synth.sh")),
    "platforms/asap7/yoSys/cells_clkgate_R.v"]
PLATFORM_LIB = "platforms/asap7/lib/NLDM"
LIB_GROUPS = ("AO", "INVBUF", "OA", "SEQ", "SIMPLE")
HEADER = "read_design_sources\n\nhierarchy -check -top $::env(DESIGN_NAME)"
UNSUPPORTED = ("OT_NATIVE_SRAM_PATHS", "OT_PRIVATE_HHP_CLOCK_MESH", "OT_RTL_LINT_FLATTEN",
               "OT_RTL_LINT_DEAD_OUTPUT_MODULES", "SYNTH_HDL_FRONTEND", "VERILOG_TOP_PARAMS",
               "SYNTH_INCLUDE_DIRS", "SYNTH_BLACKBOXES", "SYNTH_NETLIST_FILES")


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def file_stamp(path):
    st = path.stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def seal_file(path):
    stamp = file_stamp(path)
    sha = digest(path)
    if file_stamp(path) != stamp:
        raise ValueError(f"{path} changed during compiler input capture")
    return {"sha256": sha, "identity": stamp}


def inventory(root, names):
    return {name: seal_file(root / name) for name in names}


def inventory_digest(files):
    records = (f"{record['sha256']}  {name}\n" for name, record in files.items())
    return hashlib.sha256("".join(records).encode()).hexdigest()


def require_same_files(root, files, omit=()):
    for name, record in files.items():
        if name not in omit and file_stamp(root / name) != record["identity"]:
            raise ValueError(f"{name} changed since strict RTL lint")


def require_isolated_container():
    if not Path("/.dockerenv").is_file() or CANON.is_symlink():
        raise ValueError("checkpoint overlay requires the isolated ORFS Docker container")


def compiler_config(text):
    # Nickname chooses the results directory. Comments and nickname never feed
    # the qualified stock Verilog frontend; every other Make line stays exact.
    if any(line.rstrip().endswith(chr(92)) for line in text.splitlines()):
        raise ValueError("unqualified multiline Make configuration")
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")
             and not re.fullmatch(r"export DESIGN_NICKNAME = [A-Za-z0-9_]+", line)]
    return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()


def runtime():
    files = list(RUNTIME_FILES)
    libs = []
    for group in LIB_GROUPS:
        matches = sorted((FLOW / PLATFORM_LIB).glob(f"asap7sc7p5t_{group}_RVT_TT_nldm_*.lib*"))
        if len(matches) != 1:
            raise ValueError(f"unknown native liberty group {group}")
        libs += matches
    files += [str(path.relative_to(FLOW)) for path in libs]
    yosys = shutil.which("yosys")
    if not yosys:
        raise ValueError("Yosys unavailable")
    return inventory(FLOW, [*files, yosys]), [str(path) for path in libs]


def source_identity(kit):
    config_file = kit / "config.mk"
    config = seal_file(config_file)
    cfg = rtl_lint.config(kit)
    if any(cfg.get(key) or os.environ.get(key) for key in UNSUPPORTED):
        raise ValueError("unsupported RTL or SRAM authority profile")
    if any((kit / name).exists() for name in ("kit_assembly.json", "resume.json")):
        raise ValueError("unsupported assembly or resume profile")
    wrapper = kit / "grt183_make.sh"
    wrapper_record = seal_file(wrapper) if wrapper.exists() else None
    if wrapper_record and wrapper_record["sha256"] != WRAPPER_DIGEST:
        raise ValueError("unknown Make wrapper")
    if (kit / "run/results").exists():
        raise ValueError("stock synthesis results already present")
    recipe = compiler_config(config_file.read_text())
    if file_stamp(config_file) != config["identity"] or recipe != COMPILER_CONFIG_DIGEST:
        raise ValueError("unqualified compiler Make configuration")
    rtl = sorted((kit / "rtl").iterdir())
    macro_paths = [kit / "macros" / f"{name}_tt.lib" for name in sorted(MACROS)]
    macro_dir = kit / "macros"
    if {p.name for p in macro_dir.glob("*.lib*")} != {
        f"{name}_{corner}.lib" for name in MACROS for corner in ("tt", "ff")
    }:
        raise ValueError("unknown strict-lint macro liberty")
    paths = rtl + macro_paths
    if any(p.is_symlink() or not p.is_file() for p in paths):
        raise ValueError("unqualified source or macro file")
    selected = inventory(kit, [str(path.relative_to(kit)) for path in paths])
    require_isolated_container()
    rt, libs = runtime()
    if inventory_digest(selected) != COMPILER_INPUT_DIGEST or inventory_digest(rt) != RUNTIME_DIGEST:
        raise ValueError("unqualified RTL, TT macro views, or ORFS runtime")
    # The raw lint checkpoint precedes these ordinary ORFS hooks. Their actual
    # bytes are recorded for this attempt and reused by the stock continuation.
    selected.update(inventory(kit, ["ot_keep_regs.tcl", "rtl_lint.py"]))
    selected["config.mk"] = config
    if wrapper_record:
        selected["grt183_make.sh"] = wrapper_record
    directories = {name: file_stamp(kit / name) for name in ("rtl", "macros")}
    return dict(recipe=recipe, kit_files=selected, dirs=directories, runtime_files=rt,
                top=cfg["DESIGN_NAME"][0], sources=cfg["VERILOG_FILES"],
                libraries=libs + [str(MOUNT / "macros" / f"{name}_tt.lib") for name in MACROS])


def check_receipt(kit, identity, overlay=False):
    require_same_files(kit, identity["kit_files"])
    for name, stamp in identity["dirs"].items():
        if file_stamp(kit / name) != stamp:
            raise ValueError(f"{name} inventory changed since strict RTL lint")
    omit = (str(CANON.relative_to(FLOW)),) if overlay else ()
    require_same_files(FLOW, identity["runtime_files"], omit)



def interfaces(path):
    modules = {}
    ports = None
    for line in path.read_text().splitlines():
        if line.startswith("module "):
            ports = modules.setdefault(line.split()[1], {})
        elif line == "end":
            ports = None
        elif ports is not None and line.startswith("  wire "):
            pin = re.search(r"\b(input|output|inout) \d+ (\\\S+)$", line)
            if pin:
                ports[pin[2]] = (pin[1], line[7:pin.start()].strip())
    return modules


def hard_interfaces(active, lint, stock):
    lint, stock = interfaces(lint), interfaces(stock)
    modules = set()
    references = {}
    ports = None
    with active.open() as source:
        for line in source:
            if line.startswith("module "):
                modules.add(line.split()[1])
            elif line.startswith("  cell "):
                cell_type = line.split()[1]
                ports = references.setdefault(cell_type, set()) if cell_type.startswith("\\") else None
            elif line.startswith("  end"):
                ports = None
            elif ports is not None and line.startswith(("    parameter ", "    connect ")):
                operation, pin = line.split()[:2]
                ports.add((operation, pin))
    if modules & stock.keys():
        raise ValueError("live design module collides with native hard view")
    hard = set(references) - modules
    for master in hard:
        if not lint.get(master) or lint[master] != stock.get(master):
            raise ValueError(f"hard port signature mismatch for {master}")
        if any(op != "connect" or pin not in lint[master] for op, pin in references[master]):
            raise ValueError(f"hard master {master} has positional port, parameter, or unknown pin")
    return sorted(hard)


def write_receipt(kit, **stages):
    (kit / RECEIPT).write_text(json.dumps(stages, indent=2, sort_keys=True) + "\n")


def run_lint(kit, trial):
    try:
        identity = source_identity(kit)
        if any(trial.iterdir()):
            raise ValueError("checkpoint scratch is not empty")
    except (OSError, ValueError, KeyError) as error:
        write_receipt(kit, status="STOCK", reason=str(error))
        return rtl_lint.run(kit)
    code = rtl_lint.run(kit, checkpoint=trial)
    record = json.loads((kit / "rtl_lint.json").read_text())
    if code == 1 and not (trial / "active.rtlil").is_file():
        # The extra pre-lowering capture can fail before the original check
        # executes. Let the original standalone command classify the failure.
        write_receipt(kit, status="STOCK", reason="optional capture did not complete", identity=identity)
        return rtl_lint.run(kit)
    if code or record.get("flat_recheck_dead_undriven"):
        write_receipt(kit, status="STOCK", reason="ordinary lint failure or flattened retry", identity=identity)
        return code
    try:
        check_receipt(kit, identity)
        write_receipt(kit, status="READY", trial=trial.name, identity=identity,
                      checkpoint_files=inventory(trial, ["active.rtlil", "lint_boxes.rtlil"]))
    except (OSError, ValueError) as error:
        write_receipt(kit, status="STOCK", reason=str(error), identity=identity)
        return rtl_lint.run(kit)
    return code


# The ordinary canonical hook and writer below this insertion run unchanged.
# Tcl reports a rejected handoff only before the checkpoint is read.
INSERT = """
set ot_trial $::env(OT_LINT_CHECKPOINT_DIR)
proc ot_reject_checkpoint {path reason} {
  set f [open [file join $path ineligible] w]
  puts $f $reason
  close $f
  error "RTL checkpoint ineligible: $reason"
}
foreach name {SYNTH_HDL_FRONTEND SYNTH_BLACKBOXES SYNTH_NETLIST_FILES VERILOG_TOP_PARAMS SYNTH_INCLUDE_DIRS} {
  if {[env_var_exists_and_non_empty $name]} {
    ot_reject_checkpoint $ot_trial "unsupported effective $name"
  }
}
if {[env_var_equals AUTO_MEMORIES 1] ||
    $::env(VERILOG_DEFINES) ne "-DSYNTHESIS" ||
    $::env(VERILOG_INCLUDE_DIRS) ne "/work/rtl" ||
    $::env(CLKGATE_MAP_FILE) ne "$::env(FLOW_HOME)/platforms/asap7/yoSys/cells_clkgate_R.v"} {
  ot_reject_checkpoint $ot_trial "different effective canonical frontend"
}
set ot_sources $::env(VERILOG_FILES)
if {[catch {exec python3 -I /work/synth_lint_checkpoint.py check /work $ot_trial \
    $::env(DESIGN_NAME) {*}$ot_sources -- {*}$::env(LIB_FILES)} ot_reason]} {
  ot_reject_checkpoint $ot_trial $ot_reason
}
set ::env(VERILOG_FILES) {}
read_design_sources
set ::env(VERILOG_FILES) $ot_sources
select =A:blackbox =A:whitebox
write_rtlil -selected $ot_trial/stock_boxes.rtlil
select -clear
if {[catch {exec python3 -I /work/synth_lint_checkpoint.py consume /work $ot_trial} ot_reason]} {
  ot_reject_checkpoint $ot_trial $ot_reason
}
puts $ot_reason
read_rtlil $ot_trial/active.rtlil
hierarchy -check -top $::env(DESIGN_NAME)
"""


def check_effective(kit, args):
    split = args.index("--")
    top, *sources = args[:split]
    libs = args[split + 1:]
    receipt = json.loads((kit / RECEIPT).read_text())
    identity = receipt["identity"]
    if (top, sources, libs) != (identity["top"], identity["sources"], identity["libraries"]):
        raise ValueError("effective Make source or Liberty file list differs")


def consume(kit, trial):
    receipt = json.loads((kit / RECEIPT).read_text())
    if receipt.get("status") != "READY" or receipt.get("trial") != trial.name:
        raise ValueError("checkpoint receipt does not identify this attempt")
    try:
        check_receipt(kit, receipt["identity"], overlay=True)
    except (OSError, ValueError) as error:
        (trial / "inputs_changed").write_text(str(error) + "\n")
        raise
    require_same_files(trial, receipt["checkpoint_files"])
    hard = hard_interfaces(trial / "active.rtlil", trial / "lint_boxes.rtlil", trial / "stock_boxes.rtlil")
    (trial / "selected").write_text(json.dumps(hard) + "\n")
    print("RTL checkpoint eligible:", " ".join(hard))


def inputs_changed(kit, receipt, error):
    reason = f"FAIL_PREFLOOR lint compiler inputs changed after check: {error}"
    with (kit / "FAIL_PREFLOOR").open("a") as log:
        print(reason, file=log)
    print(reason)
    write_receipt(kit, **{**receipt, "status": "INPUT CHANGED", "reason": str(error)})
    return 8


def run_synth(kit, trial, command):
    try:
        receipt = json.loads((kit / RECEIPT).read_text())
        if receipt.get("status") != "READY" or receipt.get("trial") != trial.name:
            return subprocess.call(command)
        try:
            check_receipt(kit, receipt["identity"])
        except (OSError, ValueError) as error:
            return inputs_changed(kit, receipt, error)
        require_isolated_container()
        original = CANON.read_text()
        if original.count(HEADER) != 1:
            raise ValueError("unrecognized ORFS canonical reader")
        canonical_stat = CANON.stat()
        with tempfile.NamedTemporaryFile(mode="w", dir=CANON.parent, delete=False) as pending:
            pending.write(original.replace(HEADER, INSERT, 1))
        patched = Path(pending.name)
        try:
            patched.chmod(canonical_stat.st_mode & 0o777)
            patched.replace(CANON)
        finally:
            patched.unlink(missing_ok=True)
    except (OSError, ValueError, KeyError) as error:
        write_receipt(kit, status="STOCK", reason=str(error))
        return subprocess.call(command)
    try:
        code = subprocess.call(command, env={**os.environ, "OT_LINT_CHECKPOINT_DIR": str(trial)})
    finally:
        CANON.write_text(original)
        os.utime(CANON, ns=(canonical_stat.st_atime_ns, canonical_stat.st_mtime_ns))
    changed = trial / "inputs_changed"
    if changed.is_file():
        return inputs_changed(kit, receipt, changed.read_text().strip())
    rejected, selected = trial / "ineligible", trial / "selected"
    if code and rejected.is_file() and not selected.exists():
        write_receipt(kit, **{**receipt, "status": "STOCK", "reason": rejected.read_text().strip()})
        return subprocess.call(command)
    write_receipt(kit, **{**receipt, "status": "USED" if selected.is_file() else "NOT USED", "synth_rc": code})
    return code


if __name__ == "__main__":
    command, kit, trial, *args = sys.argv[1:]
    kit, trial = Path(kit), Path(trial)
    if command == "lint":
        raise SystemExit(run_lint(kit, trial))
    if command == "synth":
        raise SystemExit(run_synth(kit, trial, args))
    if command in ("check", "consume"):
        try:
            if command == "check":
                check_effective(kit, args)
            else:
                consume(kit, trial)
        except (OSError, ValueError, KeyError) as error:
            print(str(error), file=sys.stderr)
            raise SystemExit(3) from None
    else:
        raise SystemExit(f"unknown synth checkpoint stage: {command}")
