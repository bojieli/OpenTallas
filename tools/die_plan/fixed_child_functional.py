"""Opt-in functional providers for already assembled, fixed-port signed children.

This selects captured child RTL, not physical BBs and not a new native binder.
It does not assert equivalence to the untransformed native profile.
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re

import kit_assembly as KA


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def asset(root, record):
    root = Path(root).resolve()
    path = (root / record["path"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("functional profile asset escapes its bundle")
    data = path.read_bytes()
    if record.get("compression") == "gzip":
        data = gzip.decompress(data)
    if sha(data) != record["sha256"]:
        raise ValueError("functional profile asset changed: " + record["path"])
    return data


def port_interface(text, master):
    # Same fixed-port parser used by the canonical HR face-wrapper producer.
    path = Path(__file__).resolve().parents[2] / "physical/die_plan/qwen_kvsys/cores/harden/hr_rf_wrap.py"
    spec = importlib.util.spec_from_file_location("functional_hr_rf_wrap", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _, ports, _ = module.ports(text, master)
    return {name: [direction, module.width(rng)] for name, (direction, rng) in ports.items()}


def instance_ports(text, master, instance):
    leaf = instance.rsplit(".", 1)[-1]
    hits = KA._instance_type_spans(text, master, leaf)
    if len(hits) != 1:
        raise ValueError("functional child must have one exact source instance")
    _, type_end, start = hits[0]
    if KA._named_overrides(text[type_end:start]):
        raise ValueError("functional fixed child must not have parameter overrides")
    code = KA._masked_rtl(text)
    opening = code.index("(", start)
    end, depth = opening + 1, 1
    while end < len(code) and depth:
        depth += (code[end] == "(") - (code[end] == ")")
        end += 1
    if depth:
        raise ValueError("unbalanced functional child port map")
    return KA._named_overrides("#" + text[opening:end])


def core_record(receipt, master, instance):
    rows = [r for r in receipt["cores"] if r.get("module") == master and r.get("inst") == instance]
    if len(rows) != 1:
        raise ValueError("functional profile native core is missing or ambiguous")
    row = rows[0]
    return {key: row[key] for key in ("module", "inst", "members", "native_parameters", "uncovered_boundary")
            if key in row}


def validate(profile_path, native_receipt, inverse, parent_source, outer_portmap):
    path = Path(profile_path)
    profile = json.loads(path.read_text())
    if profile.get("schema") != "opentallas.fixed_child_functional.v1" or profile.get("claim") != "EXPLICIT_TRANSFORMED_PROFILE_NOT_BARE_NATIVE_EQ":
        raise ValueError("functional profile must explicitly declare its transformed scope")
    root = path.parent
    captured = {name: asset(root, record) for name, record in profile["assets"].items()}
    master, instance = profile["master"], profile["instance"]
    provider = captured["provider"]
    core = json.loads(captured["core"])
    kit = json.loads(captured["kit_provenance"])
    qualified = json.loads(captured["qualification"])
    routed_lec = json.loads(captured["routed_lec"])
    rf = json.loads(captured["rf_wrap"])
    if qualified.get("verdict") != "SIGNED" or qualified.get("lec_verdict") != "EQUIVALENT" or routed_lec.get("verdict") != "EQUIVALENT":
        raise ValueError("functional provider lacks signed/routed-equivalence qualification")
    if not qualified.get("flow_tag") or not qualified.get("routed_db_sha256"):
        raise ValueError("functional provider qualification is not versioned")
    if kit["files"].get("rtl/" + master + ".v") != sha(provider) or kit["files"].get("core.json") != sha(captured["core"]):
        raise ValueError("functional provider differs from its captured kit provenance")
    if core.get("module") != master or core.get("variant") != profile["core_variant"]:
        raise ValueError("functional core transform identity changed")
    if canonical(core.get("sameclk")) != canonical(profile["sameclk"]):
        raise ValueError("functional SAMECLK transform changed")
    if rf.get("spec") != profile["rf_spec"] or rf.get("fwft_reads"):
        raise ValueError("functional RF profile differs from the qualified capture")
    if not all(r.get("release_added_edges") == 1 for r in rf["resets"]):
        raise ValueError("unaccounted reset relay phase")
    if profile["latency_contract"]["reset_release_added_edges"] != 1:
        raise ValueError("functional reset phase is not declared")
    native = json.loads(Path(native_receipt).read_text())
    if canonical(core_record(native, master, instance)) != canonical(profile["native_record"]):
        raise ValueError("native source/member parameters differ from the selected profile")
    parameters = {row["path"]: row for row in profile["native_record"]["native_parameters"]}
    for change in profile["sameclk_changes"]:
        row = parameters[change["native_path"]]
        old = row["parameters"]["SAMECLK"]
        old = int(old, 2) if isinstance(old, str) and re.fullmatch(r"[01]+", old) else old
        matches = [m for m in core["sameclk"] if m["member"] == change["member"] and m["module"] == change["module"]]
        if old != 0 or change["old"] != 0 or change["new"] != 1 or len(matches) != 1:
            raise ValueError("functional profile does not match the explicit SAMECLK 0-to-1 transform")
        if not row["type"].endswith("\\" + change["module"]):
            raise ValueError("native SAMECLK member type changed")
    if len(profile["sameclk_changes"]) != len(core["sameclk"]):
        raise ValueError("functional profile leaves a SAMECLK transform undeclared")
    face = json.loads(captured["face_delta"])
    spare = json.loads(captured["spare_tie"])
    if face.get("added_cycles") != 0 or spare.get("ties") != profile["spare_ties"]:
        raise ValueError("functional face/spare refinements differ from the captured profile")
    inv = json.loads(Path(inverse).read_text())
    selected = [r for r in inv["cores"] if r.get("module") == master and r.get("inst") == instance]
    if len(selected) != 1 or selected[0].get("missing_plan_anchors") or selected[0].get("native_not_in_plan") or selected[0].get("uncovered_boundary_nets"):
        raise ValueError("native functional boundary is not complete")
    clock_anchors = selected[0]["ports"]["ck[0]"]
    if canonical(sorted(clock_anchors, key=canonical)) != canonical(sorted(profile["clock_anchors"], key=canonical)):
        raise ValueError("native member clock ownership changed")
    parent = Path(parent_source).read_bytes()
    if sha(parent) != profile["parent_source_sha256"]:
        raise ValueError("native parent source differs from its sealed profile")
    ports = instance_ports(parent.decode(), master, instance)
    clocks = profile["clock_contract"]
    if ports.get("ck") != clocks["parent_expression"]:
        raise ValueError("functional child no longer uses its verified parent clock")
    outer = json.loads(Path(outer_portmap).read_text())
    if outer.get("master") != native["top"] or outer["ports"].get(clocks["outer_port"]) != clocks["outer_expression"]:
        raise ValueError("functional native clock is not the captured common root")
    reset_ports = profile["rf_spec"]["resets"]
    if any(ports.get(port) != profile["reset_expression"] for port in reset_ports):
        raise ValueError("functional child reset identities differ")
    expected = {name: [row[0], abs(row[1] - row[2]) + 1] for name, row in core["port_decl"].items()}
    if port_interface(provider.decode(), master) != expected or set(ports) != set(expected):
        raise ValueError("functional provider or parent fixed-port ABI differs")
    return profile, provider, expected


def materialize(profile_path, filelist, native_receipt, inverse, parent_source, outer_portmap, out):
    profile, provider, interface = validate(profile_path, native_receipt, inverse, parent_source, outer_portmap)
    lines = Path(filelist).read_text().splitlines()
    matches = []
    for index, line in enumerate(lines):
        candidate = Path(line)
        if candidate.is_file() and profile["master"] in KA.module_names(candidate.read_text()):
            matches.append((index, candidate))
    if len(matches) != 1:
        raise ValueError("functional selection requires one physical BB provider")
    index, header = matches[0]
    if not header.name.endswith("_bb.v") or port_interface(header.read_text(), profile["master"]) != interface:
        raise ValueError("functional provider cannot replace an unrelated/nonmatching header")
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("functional output must be a fresh directory")
    out.mkdir(parents=True, exist_ok=True)
    target = out / (profile["master"] + ".functional.v")
    target.write_bytes(provider)
    lines[index] = str(target.resolve())
    (out / "functional.f").write_text("\n".join(lines) + "\n")
    receipt = dict(schema="opentallas.fixed_child_functional_selection.v1", master=profile["master"],
                   instance=profile["instance"], replaced_bb=str(header), provider_sha256=sha(provider),
                   other_source_entries_unchanged=True, physical_filelist_unchanged=True,
                   native_equivalence="NOT_CLAIMED", complete_parent_functional_closure="NOT_CLAIMED",
                   latency_contract=profile["latency_contract"])
    (out / "functional_selection.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("profile", "filelist", "native-receipt", "inverse", "parent-source", "outer-portmap", "out"):
        parser.add_argument("--" + key, required=True)
    args = parser.parse_args()
    materialize(args.profile, args.filelist, args.native_receipt, args.inverse, args.parent_source, args.outer_portmap, args.out)

if __name__ == "__main__":
    main()
