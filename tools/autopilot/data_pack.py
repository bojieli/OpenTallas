#!/usr/bin/env python3
"""data_pack: move lane-folder inputs INTO a published die tree as data (FLOW-0713 / FLOW-REVIEW-0513, TOOLS-CONVERGE-1116).

A prepared plan names inputs in lane folders (head-97/pd/native_domains, head-99/prep.../assets): a host without the folder fails kit_rtl.
`make` copies each SRC dir to <tree>/<RELDIR>, rewrites the absolute SRC paths in its text files (and in the copied plan files) to the
in-tree location, and writes a pack for `src_manifest.py delta-apply` (new tree = cp -a of the old tree + the pack, overlay_add recorded).
  data_pack.py make --old-tree T --new-tree T2 --out PACK --map SRC=RELDIR [--map ...] [--files SRC=RELDIR/rel ...]
  --digest RELPLAN:RELWAVE   after the rewrite, set wave_prepare.json prepared_plan_sha256 / sidecar_sha256 to the new bytes (HEAD)
The content of every copied file is unchanged except the rewritten path strings; sha256 of every rewritten file is in the pack.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import src_manifest as SM  # noqa: E402

TEXT = (".json", ".f", ".txt", ".tcl", ".tsv", ".sh", ".mk", ".sdc")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()



def rebase_asbuilt_map(data, src_file, old_tree, new_tree, rules):
    """Keep bind.py map_file manifest-relative semantics when packing an as-built file.

    Historical S81 manifests use a tree-relative map_file even after moving the
    manifest below plan_inputs/run. Resolve an existing manifest-relative path
    first, then its base and old-tree roots; never invent an input or waive a gate.
    """
    if not isinstance(data, dict) or not data.get("top") or not data.get("map_file"):
        return data
    value = data["map_file"]
    if not isinstance(value, str):
        return data
    parent = os.path.dirname(src_file)
    base = data.get("base") or old_tree
    if not os.path.isabs(base):
        base = os.path.join(parent, base)
    candidates = [value] if os.path.isabs(value) else [os.path.join(parent, value)]
    if not os.path.isabs(value):
        # The payload may contain only the manifest; an unchanged sibling map
        # remains in the baseline tree. Resolve its manifest-relative location
        # at the mapped destination, then look for that exact baseline input.
        for source, target in rules:
            if src_file == source or src_file.startswith(source + "/"):
                packed_file = target + src_file[len(source):]
                packed_map = os.path.normpath(os.path.join(os.path.dirname(packed_file), value))
                if os.path.commonpath([packed_map, new_tree]) == os.path.normpath(new_tree):
                    candidates.append(os.path.join(old_tree, os.path.relpath(packed_map, new_tree)))
                break
        candidates.extend([os.path.join(base, value), os.path.join(old_tree, value)])
    resolved = next((os.path.normpath(q) for q in candidates if os.path.isfile(q)), None)
    if resolved is None:
        raise ValueError(f"asbuilt map_file does not exist: {src_file}: {value}")
    for source, target in rules + [(old_tree.rstrip("/"), new_tree.rstrip("/"))]:
        if resolved == source or resolved.startswith(source + "/"):
            resolved = target + resolved[len(source):]
            break
    data["map_file"] = resolved
    return data


def make(old_tree, new_tree, out, maps, digest=None):
    m = json.load(open(os.path.join(old_tree, ".src-manifest.json")))
    stage = os.path.join(out, "files")
    os.makedirs(stage)
    rules = []                                           # (abs src, in-tree abs dst)
    for src, rel in maps:
        rules.append((src.rstrip("/"), os.path.join(new_tree, rel).rstrip("/")))
    rules.sort(key=lambda r: -len(r[0]))
    add = {}
    for (src, dst), (_s, rel) in zip(sorted(rules, key=lambda r: [x[0] for x in maps].index(r[0])), maps):
        for dp, dn, fn in os.walk(src):
            for f in fn:
                sp = os.path.join(dp, f)
                if os.path.islink(sp) or not os.path.isfile(sp) or SM.skipped(os.path.join(rel, f)):
                    continue   # symlinks and cache/backup names (*.bak*, *.orig, __pycache__) are not tree content
                r = os.path.normpath(os.path.join(rel, os.path.relpath(sp, src)))   # RELDIR '.' must not leave './' in the manifest key
                dp2 = os.path.join(stage, r)
                os.makedirs(os.path.dirname(dp2), exist_ok=True)
                if f.endswith(TEXT):
                    b = open(sp, "rb").read()
                    for s_, d_ in rules:
                        b = b.replace(s_.encode(), d_.encode())
                    if f.endswith(".json"):
                        try:
                            original = json.loads(open(sp, "rb").read())
                        except (ValueError, UnicodeError):
                            original = None
                        if isinstance(original, dict) and original.get("top") and original.get("map_file"):
                            fixed = rebase_asbuilt_map(original, sp, old_tree, new_tree, rules)
                            packed = json.loads(b)
                            packed["map_file"] = fixed["map_file"]
                            b = (json.dumps(packed, indent=1) + "\n").encode()
                    open(dp2, "wb").write(b)
                else:
                    shutil.copyfile(sp, dp2)
                add[r] = {"sha256": sha(dp2), "exec": os.access(sp, os.X_OK), "link": False}
    if digest:
        plan_rel, wave_rel = digest.split(":")
        side_rel = os.path.join(os.path.dirname(plan_rel), "source_sidecar.json")
        wp = os.path.join(stage, wave_rel)
        w = json.load(open(wp))
        w["prepared_plan_sha256"] = sha(os.path.join(stage, plan_rel))
        w["sidecar_sha256"] = sha(os.path.join(stage, side_rel))
        for k, v in (w.get("native_sink_censuses") or {}).items():
            p = v["path"]
            if p.startswith(new_tree):
                v["sha256"] = sha(os.path.join(stage, os.path.relpath(p, new_tree)))
        json.dump(w, open(wp, "w"), indent=1, sort_keys=True)
        add[wave_rel]["sha256"] = sha(wp)
    json.dump({"old_manifest_hash": m["manifest_hash"], "old_main": m["main_sha"], "new_main": m["main_sha"], "scope": m["scope"],
               "add": add, "delete": [], "overlay_add": {k: v["sha256"] for k, v in add.items()}},
              open(os.path.join(out, "delta.json"), "w"), indent=0, sort_keys=True)
    return len(add)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    mk = sp.add_parser("make")
    mk.add_argument("--old-tree", required=True)
    mk.add_argument("--new-tree", required=True)
    mk.add_argument("--out", required=True)
    mk.add_argument("--map", action="append", required=True, help="SRCDIR=RELDIR (relative to the tree)")
    mk.add_argument("--digest", help="RELPLAN:RELWAVE_PREPARE (HEAD: re-issue the two digests the exporter checks)")
    a = ap.parse_args(argv)
    n = make(a.old_tree, a.new_tree, a.out, [tuple(x.split("=", 1)) for x in a.map], a.digest)
    print(f"DATA_PACK {a.out}: {n} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
