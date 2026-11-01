#!/usr/bin/env python3
"""Prepare only the current C11E three-SRAM VMS bank; no added face cycles."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MODULE = "hnx_vms_bank_q0_faces__vecd4ae"
READSET = "results/hbm_vms_native_source_1400/readset.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(repo, view, views):
    """Bind the exact C source bytes and current E interface, not the 4-SRAM proposal."""
    readset = json.loads((repo / READSET).read_text())
    inventory = json.loads(views.read_text())
    if inventory["plan_sha256"] != readset["plan_sha256"]:
        raise ValueError("current VMS profile requires its exact E plan")
    candidates = {row["view"] for row in inventory["view_list"]
                  if row["module"] == MODULE}
    if view not in candidates or view not in readset["views"]:
        raise ValueError("current C has only the three-SRAM bank; no vec6293/r2048 alias")
    for row in readset["files"]:
        if digest(repo / row["file"]) != row["sha256"]:
            raise ValueError("selected current C source changed: " + row["file"])
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"],
                                     text=True).strip()
    recipes = json.loads((repo / "physical/die_plan/hbm_arch_cores/recipes_b2.json").read_text())
    recipe = dict(recipes[MODULE])
    recipe.update(top=readset["top"], params={}, files=[r["file"] for r in readset["files"]],
                  read_at_commit=False, source_commit=commit,
                  source="Exact C11E preferred three-SRAM native bank; no generic face shell")
    recipe.pop("files_at_commit", None)
    profile = dict(
        source_commit=commit, family="VMS_CURRENT_NATIVE_3SRAM", release_eligible=False,
        qualification="SOURCE_PREP_UNROUTED", added_face_cycles=0,
        endpoint_contract=dict(kind="INTERNAL_CORE", parent_partition="q_hub*",
                               partition_rule="R2_INTERNAL_TIMED_IN_PARTITION"),
        clock_ports=readset["clock_ports"], reset_ports=["rst_n"],
        source_manifest={r["file"]: r["sha256"] for r in readset["files"]},
        source_caller=readset["caller"], source_readset=READSET,
        native_capacity=dict(macros={"ot_sram_1r1w_1024x256_m2_r2c2": 3},
                             external_face_shell=False),
        rejected_alias="vec6293/r2048 is not instantiated by current C; needs source event",
    )
    return recipe, profile


def values(args, key):
    result = []
    for i, arg in enumerate(args):
        if arg == key:
            if i + 1 == len(args):
                raise ValueError(key + " requires a value")
            result.append(args[i + 1])
        elif arg.startswith(key + "="):
            result.append(arg.split("=", 1)[1])
    return result


def force(args, key, value):
    supplied = values(args, key)
    if any(v != value for v in supplied):
        raise ValueError(key + " must be " + value + " for the current native VMS profile")
    if not supplied:
        args.extend([key, value])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--profile-out", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    args, forwarded = parser.parse_known_args(argv)
    for key in ["--views", "--view"]:
        if len(set(values(forwarded, key))) != 1:
            raise ValueError("one " + key + " required")
    if values(forwarded, "--wrapper"):
        raise ValueError("external hand wrappers cannot replace the current native bank")
    for key in ["--io-tt-ps", "--io-ff-ps"]:
        if values(forwarded, key):
            raise ValueError("preserve the E plan's existing clock arrival contract")
    force(forwarded, "--face-shell", "off")
    force(forwarded, "--recipe-key", MODULE)
    force(forwarded, "--clock-pin-entry", "on")
    force(forwarded, "--core-macros", "auto")
    force(forwarded, "--core-insertion", "none")
    recipe, profile = prepare(args.repo, values(forwarded, "--view")[0],
                              Path(values(forwarded, "--views")[0]))
    if args.profile_out:
        args.profile_out.parent.mkdir(parents=True, exist_ok=True)
        args.profile_out.write_text(json.dumps(dict(recipe=recipe, profile=profile), indent=1) + "\n")
    if args.prepare_only:
        return
    path = args.repo / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py"
    spec = importlib.util.spec_from_file_location("vms_current_native_backend", path)
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    sys.argv = [str(path), *forwarded]
    backend.main(recipe_overrides={MODULE: recipe}, source_profile=profile)


if __name__ == "__main__":
    main()
