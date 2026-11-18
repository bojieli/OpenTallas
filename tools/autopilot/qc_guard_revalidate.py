#!/usr/bin/env python3
"""Revalidate a QC clock-merge guard across a proved manifest relocation.

The old guard, original manifest, guarded CM/KP composition, isolated runtime
receipt, selected elaboration sources and relocated inputs must agree.  The
normal cm_inject inject/check commands still decide acceptance.  No binding or
elaboration is run here.  A JSON spec names the existing artifacts and outputs.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def require(ok, why):
    if not ok:
        raise ValueError(why)


def runtime_refs(m):
    extra = m.get("land_r8_extra") or []
    require(isinstance(extra, list), "land_r8_extra must be a list")
    return [m["clock_landing_table"], m["land_r8"], *extra]


def root_of(m, location):
    p = Path(m.get("base", "."))
    return (p if p.is_absolute() else Path(location).parent / p).resolve()


def resolve(m, location, value, key=""):
    p = Path(value)
    if not p.is_absolute():
        p = (Path(location).parent if key == "map_file" else root_of(m, location)) / p
    return p.resolve()


def validate(spec):
    old = read(spec["old_guard"])
    kp = read(spec["old_kp_guard"])
    original = read(spec["original_manifest"])
    before = read(spec["source_manifest"])
    qualified = read(spec["qualified_manifest"])
    isolated = read(spec["isolation_receipt"])
    new = read(spec["new_manifest"])
    old_root, new_root = Path(spec["old_root"]).resolve(), Path(spec["new_root"]).resolve()
    old_location = isolated["isolated_manifest"]
    new_location = spec["new_manifest"]
    original_sha = sha(spec["original_manifest"])
    require(old.get("manifest_sha256") == original_sha, "old CM guard does not match original manifest")
    require(kp.get("manifest_sha256") == original_sha, "old KP guard does not match original manifest")
    cm = old.get("clock_merge")
    require(isinstance(cm, dict) and cm, "old CM guard has no domain map")
    require(all(isinstance(v, dict) and v and all(isinstance(a, str) and isinstance(b, str) and a != b
                                                for a, b in v.items()) for v in cm.values()), "invalid original clock-domain map")
    expected_before = dict(original, clock_merge=cm, kit_source_station_pricing=kp["kit_source_station_pricing"])
    require(before == expected_before, "guarded source manifest changed beyond CM/KP injection")
    require(sha(spec["source_manifest"]) == isolated["source_sha256"], "isolated receipt source hash mismatch")
    require(sha(spec["qualified_manifest"]) == isolated["isolated_sha256"], "qualified manifest hash mismatch")
    expected_qualified = dict(before, clock_landing_table=isolated["sidecar"], land_r8=isolated["r8"])
    if isolated.get("extra_override_spec"):
        expected_qualified["land_r8_extra"] = [x["copy"] for x in isolated.get("extra_tables") or []]
    require(qualified == expected_qualified, "qualified manifest changed beyond recorded runtime isolation")
    require(root_of(qualified, old_location) == old_root, "qualified manifest base is not original source root")
    require(root_of(new, new_location) == new_root, "relocated manifest base is not new source root")
    require(new.get("clock_merge") == cm and
            new.get("kit_source_station_pricing") == kp["kit_source_station_pricing"],
            "relocated CM/KP semantics differ")

    selected = read(spec["selected_source_map"])
    source_inventory = read(spec["source_inventory"])
    required_sources = [str(Path(p).resolve()) for k in ("full", "lib") for p in source_inventory[k]]
    by_old, by_new = {}, {}
    for item in selected:
        p, q = Path(item["original"]).resolve(), Path(item["packaged"]).resolve()
        require(q.is_relative_to(new_root), "selected source escaped new root")
        h = sha(p)
        require(h == sha(q) == item["sha256"], "selected source payload changed: " + str(p))
        require(str(p) not in by_old or by_old[str(p)] == h, "conflicting selected source mapping")
        by_old[str(p)] = by_new[str(q)] = h
    require(required_sources and all(p in by_old for p in required_sources), "selected elaboration source omitted")

    old_map = resolve(qualified, old_location, qualified["map_file"], "map_file")
    new_map = resolve(new, new_location, new["map_file"], "map_file")
    require(sha(old_map) == sha(new_map), "library/partition map bytes changed")
    assets = read(spec["runtime_assets"])
    items = assets["assets"]
    old_refs, new_refs = runtime_refs(qualified), runtime_refs(new)
    require(assets["asset_count"] == len(items) == len(old_refs) == len(new_refs), "runtime asset count mismatch")
    runtime_hashes = {}
    for i, item in enumerate(items):
        require(old_refs[i] == item["source"], "qualified runtime asset order/path changed")
        p = resolve(qualified, old_location, old_refs[i])
        q = resolve(new, new_location, new_refs[i])
        require(q.is_relative_to(new_root), "runtime asset escaped new root")
        require(sha(p) == sha(item["copy"]) == sha(q) == item["sha256"], "runtime asset payload changed")
        runtime_hashes[str(p)] = runtime_hashes[str(q)] = item["sha256"]
    require(items[0]["sha256"] == isolated["sidecar_sha256"] and
            items[1]["sha256"] == isolated["r8_sha256"], "isolated sidecar/R8 receipt changed")
    for item, receipt in zip(items[2:], isolated.get("extra_tables") or []):
        require(item["sha256"] == receipt["sha256"], "isolated extra table receipt changed")

    def canonical(obj, m, location, root, sources, key=""):
        if isinstance(obj, dict):
            return {k: canonical(v, m, location, root, sources, k) for k, v in obj.items()}
        if isinstance(obj, list):
            return [canonical(v, m, location, root, sources, key) for v in obj]
        if not isinstance(obj, str):
            return obj
        if key == "base":
            return "<ROOT>"
        if key == "map_file":
            return "<MAP:" + sha(resolve(m, location, obj, key)) + ">"
        path_key = key in ("files", "prefer", "netlist", "rtl_roots", "portbind_prefer",
                           "clock_landing_table", "land_r8", "land_r8_extra", "file")
        if obj and not any(c.isspace() for c in obj) and (path_key or "/" in obj):
            p = resolve(m, location, obj, key)
            if str(p) in sources:
                return "<SOURCE:" + sources[str(p)] + ">"
            if str(p) in runtime_hashes:
                return "<RUNTIME:" + runtime_hashes[str(p)] + ">"
            if p.is_relative_to(root):
                return "<ROOT>/" + p.relative_to(root).as_posix()
        return obj.replace(str(root), "<ROOT>")

    require(canonical(qualified, qualified, old_location, old_root, by_old) ==
            canonical(new, new, new_location, new_root, by_new),
            "relocation changed manifest semantics")
    mp_path = Path(spec.get("manifest_paths_module") or
                   Path(__file__).resolve().parents[1] / "die_plan/manifest_paths.py")
    ms = importlib.util.spec_from_file_location("_qc_guard_manifest_paths", mp_path)
    mp = importlib.util.module_from_spec(ms)
    ms.loader.exec_module(mp)
    errors = mp.check(new, Path(new_location).parent, repo=new_root)
    require(not errors, "relocated manifest path policy: " + "; ".join(errors))
    return dict(original_manifest_sha256=original_sha,
                old_guard_sha256=sha(spec["old_guard"]),
                qualified_manifest_sha256=sha(spec["qualified_manifest"]),
                isolation_receipt_sha256=sha(spec["isolation_receipt"]),
                relocated_manifest_sha256=sha(new_location),
                selected_source_count=len(required_sources),
                runtime_asset_count=len(items), map_sha256=sha(new_map))


def revalidate(spec):
    proof = validate(spec)
    out = Path(spec["out"])
    require(not out.exists(), "refuse to overwrite an existing guard")
    out.parent.mkdir(parents=True, exist_ok=True)
    old = read(spec["old_guard"])
    guard = {k: copy.deepcopy(old[k]) for k in ("schema", "family", "default_domain", "die_clock_domain", "instances")
             if k in old}
    guard.update(clock_merge=copy.deepcopy(old["clock_merge"]),
                 manifest=str(spec.get("manifest_reference") or spec["new_manifest"]),
                 manifest_sha256=proof["relocated_manifest_sha256"], revalidated_from=proof)
    stamp = str(time.time_ns())
    candidate = out.with_name(out.name + ".candidate." + stamp)
    candidate.write_text(json.dumps(guard, indent=1) + "\n")
    source_helper = Path(spec["cm_helper"])
    pinned = out.parent / ("cm_inject-" + sha(source_helper) + ".py")
    if not pinned.exists():
        pinned.write_bytes(source_helper.read_bytes())
    env = dict(os.environ, CM_FILE=str(candidate))
    injected = Path(spec["new_manifest"]).with_name("cm_revalidated_" + stamp + ".json")
    commands = [[sys.executable, "-I", str(pinned), "inject", spec["plan"], spec["new_manifest"],
                 str(injected), spec["reference_bind"]],
                [sys.executable, "-I", str(pinned), "check", spec["plan"], spec["bound_bind"],
                 spec["reference_bind"]]]
    transcript = []
    for command in commands:
        r = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        transcript.append(r.stdout)
        require(r.returncode == 0, "normal CM guard refused: " + r.stdout[-1200:])
    require(read(injected) == read(spec["new_manifest"]), "normal CM injection was not idempotent")
    proof.update(normal_cm_inject_rc=0, normal_cm_check_rc=0, cm_helper_sha256=sha(pinned))
    guard["revalidated_from"] = proof
    out.write_text(json.dumps(guard, indent=1) + "\n")
    Path(spec["proof_out"]).write_text(json.dumps(dict(proof=proof, commands=commands, output=transcript), indent=1) + "\n")
    return guard


def main():
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", required=True)
    a = p.parse_args()
    try:
        result = revalidate(read(a.spec))
    except (OSError, KeyError, ValueError) as e:
        p.exit(2, "QC_CM_REVALIDATE FAIL " + str(e) + "\n")
    print("QC_CM_REVALIDATE PASS " + result["manifest_sha256"])


if __name__ == "__main__":
    main()

