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
                r = os.path.join(rel, os.path.relpath(sp, src))
                dp2 = os.path.join(stage, r)
                os.makedirs(os.path.dirname(dp2), exist_ok=True)
                if f.endswith(TEXT):
                    b = open(sp, "rb").read()
                    for s_, d_ in rules:
                        b = b.replace(s_.encode(), d_.encode())
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
