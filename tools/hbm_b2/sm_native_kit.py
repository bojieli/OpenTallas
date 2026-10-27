#!/usr/bin/env python3
"""Stage exact native SM child bodies with zero external face-register cycles.

Use --inventory-only [--module NAME] to inspect the measured native interfaces
without creating a kit (all eight measured masters remain inspectable). Actual
generation permits only XS3/BDC/TCL/TCT; beat/land/row transport stays soft. It accepts the shared generator's
--views/--view/--out/--master-slice arguments. Pin-window census and geometry
review must precede new kits; this driver never launches P&R.
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SOURCE_COMMIT = "4d6f5439dcee43b97baffaa731aae826fdcb6a66"
HEADER_COMMIT = "4673cf757e"
HEADER_PATH = "physical/die_plan/hbm_arch_cores/rtl/hnx_rp4lp4_leaf_selfcontained.sv"
LEAF_PATH = "rtl/hbm_next/sm/hnx_rp4lp4_leaf.sv"
SPEC_PATH = "physical/hbm_next/sm4/hnx_rp3lp3h_n_spec.json"
CAPACITY_PATH = "results/hbm_native_children_1027/capacity.json"
RELEASE_MASTERS = frozenset({"hnx_xs3", "ot_hbm_accel_smh_bdc",
                            "ot_hbm_accel_smh_tcl", "ot_hbm_accel_smh_tct"})
NATIVE_SOURCES = {
    "hnx_xs3": "rtl/hbm_next/sm/hnx_xs3.sv",
    "ot_hbm_accel_smh_bdc": "rtl/hbm_accel/sm/ot_hbm_accel_smh.sv",
    "ot_hbm_accel_smh_tcl": "rtl/hbm_accel/sm/ot_hbm_accel_smh.sv",
    "ot_hbm_accel_smh_tct": "rtl/hbm_accel/sm/ot_hbm_accel_smh.sv",
    "ot_smh_tr_group_beat_e": "rtl/hbm_accel/sm/ot_hbm_smh_transport_group_masters.sv",
    "ot_smh_tr_group_land": "rtl/hbm_accel/sm/ot_hbm_smh_transport_split_masters.sv",
    "ot_smh_tr_group_row_w": "rtl/hbm_accel/sm/ot_hbm_smh_transport_group_masters.sv",
    "ot_smh_tr_group_row_e": "rtl/hbm_accel/sm/ot_hbm_smh_transport_group_masters.sv",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_bytes(repo, commit, path):
    return subprocess.check_output(["git", "-C", str(repo), "show", commit + ":" + path])


def source_bundle(repo):
    """Use the exact native source closure, never old generic physical wrappers."""
    spec = json.loads(git_bytes(repo, SOURCE_COMMIT, SPEC_PATH))
    sources = {p: git_bytes(repo, SOURCE_COMMIT, p) for p in spec["sources"]}
    old = sources[LEAF_PATH]
    fixed = git_bytes(repo, HEADER_COMMIT, HEADER_PATH)
    if not fixed.endswith(old):
        raise ValueError("macro profile changed the pinned native leaf body")
    sources[LEAF_PATH] = fixed
    return spec, sources


def profile_for(module, capacity, spec, sources):
    if module not in NATIVE_SOURCES:
        raise ValueError("not one of the eight native SM child masters: " + module)
    measured = capacity["profiles"][module]
    if not measured["native"] or measured["external_face_shell"] or measured["unknown"]:
        raise ValueError("capacity inventory is not an exact native interface")
    source = NATIVE_SOURCES[module]
    ports = [(p["name"], p["direction"], p["width"]) for p in measured["port_buses"]]
    if ("clk", "input", 1) not in ports or ("rst_a", "input", 1) not in ports:
        raise ValueError("native clock/reset inventory changed")
    macros = ["ot_sram_1r1w_128x256_m1_r2c2"] if module == "hnx_xs3" else []
    expected = {macros[0]: 12} if macros else {}
    if measured["macros"] != expected:
        raise ValueError("native SRAM inventory changed")
    recipe = dict(
        top=module, files=list(sources), params={}, defines=list(spec["defines"]),
        source_commit=SOURCE_COMMIT, macros=macros,
        source="Exact native SM child, original hard hierarchy; no generic input/output face shell",
    )
    profile = dict(
        source_commit=SOURCE_COMMIT, family="SM_NATIVE_CHILD",
        release_eligible=module in RELEASE_MASTERS,
        transport_policy="beat/land/row transport stays soft inside the native parent",
        endpoint_contract=dict(kind="INTERNAL_CORE",
                               partition_rule="R2_INTERNAL_TIMED_IN_PARTITION",
                               parent_partition="q_sm*", source="tools/die_plan/README.md R2"),
        added_face_cycles=0, qualification="CAPACITY_MEASURED_UNROUTED",
        clock_ports=["clk"], reset_ports=["rst_a"],
        source_manifest={p: digest(data) for p, data in sources.items()},
        preprocessor_profile=dict(commit=HEADER_COMMIT, file=HEADER_PATH,
                                  original_body_byte_identical=True),
        native_capacity=dict(std_cells=measured["std_cells"], macros=expected,
                             evidence=CAPACITY_PATH, external_face_shell=False),
        port_inventory=dict(top=module, source_file=source,
                            source_sha256=digest(sources[source]), ports=ports),
    )
    return recipe, profile


def option_values(args, option):
    values = []
    for i, arg in enumerate(args):
        if arg == option:
            if i + 1 == len(args):
                raise ValueError(option + " needs a value")
            values.append(args[i + 1])
        elif arg.startswith(option + "="):
            values.append(arg.split("=", 1)[1])
    return values


def one_option(args, option, required=False):
    values = option_values(args, option)
    if not values:
        if required:
            raise ValueError(option + " required")
        return None
    if len(set(values)) != 1:
        raise ValueError("conflicting " + option)
    return values[0]


def force_option(args, option, value):
    values = option_values(args, option)
    if values and any(v != value for v in values):
        raise ValueError(option + " must be " + value + " for native SM child bodies")
    if not values:
        args.extend([option, value])


def stage_sources(cache, sources):
    cache.mkdir(parents=True, exist_ok=True)
    overrides = {}
    for path, data in sources.items():
        target = cache / Path(path).name
        if target.exists() and target.read_bytes() != data:
            raise ValueError("source cache content/name collision: " + str(target))
        if not target.exists():
            target.write_bytes(data)
        overrides[path] = str(target.resolve())
    return overrides


def generate(repo, forwarded, module, recipe, profile, overrides, backend=None):
    if module not in RELEASE_MASTERS:
        raise ValueError("native transport remains soft in parent; inventory-only master: " + module)
    if one_option(forwarded, "--wrapper"):
        raise ValueError("native SM child profiles do not accept external wrappers")
    force_option(forwarded, "--face-shell", "off")
    force_option(forwarded, "--sigmax", "M5")
    force_option(forwarded, "--recipe-key", module)
    if not option_values(forwarded, "--core-insertion"):
        forwarded.extend(["--core-insertion", "none"])
    if not option_values(forwarded, "--clock-taps"):
        forwarded.extend(["--clock-taps", "density"])
    if backend is None:
        path = repo / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py"
        desc = importlib.util.spec_from_file_location("sm_native_shared_kit", path)
        backend = importlib.util.module_from_spec(desc)
        desc.loader.exec_module(backend)
    saved = sys.argv
    try:
        sys.argv = ["gen_core_kit_hbm.py", *forwarded]
        return backend.main(recipe_overrides={module: recipe}, source_overrides=overrides,
                            source_profile=profile)
    finally:
        sys.argv = saved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--source-cache", type=Path)
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument("--inventory-out", type=Path)
    parser.add_argument("--module", choices=sorted(NATIVE_SOURCES))
    parser.add_argument("--diagnostic-plan", action="store_true")
    args, forwarded = parser.parse_known_args(argv)
    repo = args.repo.resolve()
    capacity = json.loads((repo / CAPACITY_PATH).read_text())
    spec, sources = source_bundle(repo)
    if args.inventory_only:
        modules = [args.module] if args.module else sorted(NATIVE_SOURCES)
        inventory = {m: profile_for(m, capacity, spec, sources)[1] for m in modules}
        text = json.dumps(inventory, indent=2) + "\n"
        if args.inventory_out:
            args.inventory_out.write_text(text)
        else:
            print(text, end="")
        return 0
    views_path = Path(one_option(forwarded, "--views", required=True))
    view_id = one_option(forwarded, "--view", required=True)
    out = Path(one_option(forwarded, "--out", required=True))
    selected = next((v for v in json.loads(views_path.read_text())["view_list"]
                     if v["view"] == view_id), None)
    if selected is None or selected["module"] not in NATIVE_SOURCES:
        raise ValueError("view is not one of the eight native SM child masters")
    module = selected["module"]
    if module not in RELEASE_MASTERS:
        raise ValueError("transport is inventory-only and remains soft in parent: " + module)
    if args.module and args.module != module:
        raise ValueError("--module differs from selected view")
    if selected.get("canonical_type"):
        raise ValueError("native view must not use a legacy canonical wrapper")
    recipe, profile = profile_for(module, capacity, spec, sources)
    if args.diagnostic_plan:
        profile["diagnostic_inputs"] = True
    cache = args.source_cache or out / ".sm_native_sources"
    overrides = stage_sources(cache, sources)
    return generate(repo, forwarded, module, recipe, profile, overrides)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
