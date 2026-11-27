"""Validate the immutable inputs of a named, private station preparation."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bind_tool_stamp
import bound_station_source
import kit_topology
import p2_review_guides


SCHEMA = "opentallas.reviewed_station_prepare.v1"
TYPE = re.compile(r"(?:col_h9_r0_p2|col_h10_r2)__t[0-9]+(?:__[A-Za-z0-9_]+)?\Z")


def checked_file(record):
    path = Path(record["path"])
    if (not path.is_absolute() or not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]):
        raise ValueError(f"reviewed station input changed: {path}")
    return path


def verify(recipe, expected_sha, *, type_name, plan, bind_out, asbuilt, tools):
    """Recheck the original strict bind under its own generator stamp."""
    path = checked_file({"path": recipe, "sha256": expected_sha})
    data = json.loads(path.read_bytes())
    if data["schema"] != SCHEMA or data["type"] != type_name or not TYPE.fullmatch(type_name):
        raise ValueError("expected a named P2 or H10 type")
    artifacts = {field: checked_file(data[field]) for field in (
        "producer_plan", "plan", "asbuilt", "station_receipt", "clock_landing",
    )}
    if any(artifacts[key].resolve() != Path(expected).resolve() for key, expected in
           (("plan", plan), ("asbuilt", asbuilt))):
        raise ValueError("named typed source plan or as-built differs from the worker input")
    bind_out = Path(bind_out)
    if bind_out.resolve() != Path(data["bind_out"]).resolve():
        raise ValueError("named station producer bind changed")
    proof = json.loads(artifacts["station_receipt"].read_bytes())
    if (proof.get("schema") not in {bound_station_source.SCHEMA, bound_station_source.FAMILY_SCHEMA}
            or proof.get("type") != type_name
            or proof["producer_plan_sha256"] != data["producer_plan"]["sha256"]
            or proof["prepared_plan_sha256"] != data["plan"]["sha256"]):
        raise ValueError("named station proof does not cover both plans")
    provenance = json.loads((bind_out / "provenance_bind.json").read_bytes())["provenance"]
    if (provenance["step"] != "bind" or provenance["plan_sha256"] != data["producer_plan"]["sha256"]
            or json.loads((bind_out / "bind_report.json").read_bytes())["n_errors"] != 0):
        raise ValueError("named station producer is not the exact closed native bind")
    native_runtime = Path(data["native_runtime"])
    stamp = json.loads((bind_out / bind_tool_stamp.STAMP).read_bytes())
    if not native_runtime.is_absolute() or not stamp.get("generators"):
        raise ValueError("named station producer has no original generator stamp")
    if stamp["generators"] != bind_tool_stamp.generator_hashes(native_runtime):
        raise ValueError("named station producer runtime differs from its generator stamp")
    producer_plan = artifacts["producer_plan"]
    reference = json.loads(producer_plan.read_bytes())
    if not kit_topology.bind_matches(reference, type_name, bind_out, artifacts["asbuilt"], producer_plan):
        raise ValueError("current verifier could not reproduce the original native binding")
    guides = data.get("p2_guides", {})
    if type_name == p2_review_guides.TYPE:
        if set(guides) != p2_review_guides.FILES or data.get("generation_environment", {}).get(
                "OT_S81_P2_CROP_REVIEW_GUIDES") != "1":
            raise ValueError("the named fE0 P2 source requires its exact physical guides")
        for record in guides.values():
            checked_file(record)
    elif guides:
        raise ValueError("P2 guide files are specific to their reviewed fE0 type")
    tool_files = data["physical_generator_files"]
    if not isinstance(tool_files, dict) or "tools/die_plan/gen_phys.py" not in tool_files:
        raise ValueError("named station recipe must record its exact physical generator")
    for name, digest in tool_files.items():
        relative = Path(name)
        if not relative.is_relative_to("tools/die_plan") or ".." in relative.parts:
            raise ValueError(f"invalid physical generator file {name}")
        checked_file({"path": str(Path(tools) / relative), "sha256": digest})
    return dict(data, instance=proof["instance"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("recipe")
    parser.add_argument("sha256")
    parser.add_argument("--type", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--bind-out", required=True)
    parser.add_argument("--asbuilt", required=True)
    parser.add_argument("--tools", required=True)
    args = parser.parse_args()
    try:
        data = verify(args.recipe, args.sha256, type_name=args.type,
                      plan=args.plan, bind_out=args.bind_out, asbuilt=args.asbuilt, tools=args.tools)
    except (OSError, KeyError, TypeError, ValueError) as error:
        parser.exit(3, f"REVIEWED_STATION_PREPARE refused: {error}\n")
    print("REVIEWED_STATION_PREPARE " + json.dumps(data, sort_keys=True))


if __name__ == "__main__":
    main()
