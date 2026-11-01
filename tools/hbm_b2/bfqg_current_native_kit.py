#!/usr/bin/env python3
"""Current C native BFQG source profile; preserve all twenty physical clock inputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from vms_current_native_kit import digest, force, values, load_backend

ROOT = Path(__file__).resolve().parents[2]
MODULE = "ot_hgi_sm_xload_cl2_bfqg"
READSET = "results/hbm_bfqg_native_source_1520/readset.json"


def prepare(repo, view, views):
    readset = json.loads((repo / READSET).read_text())
    inventory = json.loads(views.read_text())
    if inventory["plan_sha256"] != readset["plan_sha256"]:
        raise ValueError("native BFQG requires its exact E plan")
    allowed = {r["view"] for r in inventory["view_list"] if r["module"] == MODULE}
    if view not in allowed or view not in readset["views"]:
        raise ValueError("view is not the current native BFQG interface")
    for row in readset["files"]:
        if digest(repo / row["file"]) != row["sha256"]:
            raise ValueError("selected current C source changed: " + row["file"])
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    recipe = dict(json.loads((repo / "physical/die_plan/hbm_arch_cores/recipes_b2.json").read_text())[MODULE])
    recipe.update(top=MODULE, params={}, files=[r["file"] for r in readset["files"]],
                  source_commit=commit, read_at_commit=False,
                  source="Exact preferred current C BFQG body and reset relay; no generic face shell")
    recipe.pop("files_at_commit", None)
    profile = dict(source_commit=commit, family="BFQG_CURRENT_NATIVE", release_eligible=False,
                   qualification="SOURCE_PREP_UNROUTED", added_face_cycles=0,
                   endpoint_contract=dict(kind="INTERNAL_CORE", parent_partition="q_hub*",
                                          partition_rule="R2_INTERNAL_TIMED_IN_PARTITION"),
                   clock_ports=readset["clock_ports"], reset_ports=["rst_n"],
                   source_manifest={r["file"]: r["sha256"] for r in readset["files"]},
                   source_caller=readset["caller"], source_readset=READSET,
                   pin_placement_policy="DECLARED_CLOCK_RESET_POINTS",
                   native_capacity=dict(macros=readset["macros"], external_face_shell=False))
    return recipe, profile


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=ROOT)
    p.add_argument("--profile-out", type=Path)
    p.add_argument("--prepare-only", action="store_true")
    args, forwarded = p.parse_known_args(argv)
    for key in ["--views", "--view"]:
        if len(set(values(forwarded, key))) != 1:
            raise ValueError("one " + key + " required")
    if values(forwarded, "--wrapper"):
        raise ValueError("external wrappers cannot replace the current BFQG source")
    for key in ["--io-tt-ps", "--io-ff-ps"]:
        if values(forwarded, key):
            raise ValueError("preserve the E plan's clock arrival contract")
    for key, value in [("--face-shell", "off"), ("--recipe-key", MODULE),
                       ("--clock-pin-entry", "on"), ("--core-macros", "auto"),
                       ("--core-insertion", "none")]:
        force(forwarded, key, value)
    recipe, profile = prepare(args.repo, values(forwarded, "--view")[0],
                              Path(values(forwarded, "--views")[0]))
    if args.profile_out:
        args.profile_out.parent.mkdir(parents=True, exist_ok=True)
        args.profile_out.write_text(json.dumps(dict(recipe=recipe, profile=profile), indent=1) + "\n")
    if not args.prepare_only:
        backend = load_backend(args.repo)
        sys.argv = ["gen_core_kit_hbm.py", *forwarded]
        backend.main(recipe_overrides={MODULE: recipe}, source_profile=profile)


if __name__ == "__main__":
    main()
