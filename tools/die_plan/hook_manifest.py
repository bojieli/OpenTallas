#!/usr/bin/env python3
"""GENBUG-4 hook manifest: which kit hook files differ from the tool tree that generated the kit, and from main.

  write:  hook_manifest.write(kit_dir, tool_dir)   -> KIT/hooks.manifest (json, schema ot_hook_manifest/1)
  check:  hook_manifest.py check KIT --main DIR     -> prints MANIFEST rows; exit 3 when a hook is not on main (opt: --strict)

For every file in the kit root that has a same-name file in tools/die_plan of the generating tree, the manifest records
sha256 of the kit copy, of the tree copy, and (check time) of the main copy.  Class: `main` kit==main, `stale` kit==tree!=main
(main fixed it and the tree did not follow), `local` kit!=main and kit differs from nothing known (die-local line, not on main).
"""
import hashlib, json, os, sys
from pathlib import Path
SCHEMA = "ot_hook_manifest/1"
EXT = (".tcl", ".py", ".sh")

def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]

def write(kit, tool_dir, main_sha=None):
    kit, tool_dir = Path(kit), Path(tool_dir)
    rows = {}
    for f in sorted(kit.iterdir()):
        if not f.is_file() or f.suffix not in EXT:
            continue
        t = tool_dir / f.name
        if t.is_file():
            rows[f.name] = dict(kit=_sha(f), tree=_sha(t))
    doc = dict(schema=SCHEMA, tool_dir=str(tool_dir), main_sha=main_sha or os.environ.get("OT_MAIN_SHA", ""), hooks=rows)
    (kit / "hooks.manifest").write_text(json.dumps(doc, indent=1) + "\n")
    return doc

def check(kit, main_dir):
    doc = json.loads((Path(kit) / "hooks.manifest").read_text())
    main_dir = Path(main_dir)
    out = []
    for name, r in doc["hooks"].items():
        m = main_dir / name
        if not m.is_file():
            continue                                # not a main hook (generated or die-only file)
        ms = _sha(m)
        if r["kit"] == ms:
            continue
        cls = "stale" if r["kit"] == r["tree"] else "local"
        out.append(dict(hook=name, cls=cls, kit=r["kit"], main=ms))
    return out

if __name__ == "__main__":
    if len(sys.argv) >= 5 and sys.argv[1] == "check" and sys.argv[3] == "--main":
        rows = check(sys.argv[2], sys.argv[4])
        for r in rows:
            print("MANIFEST %s %s kit=%s main=%s" % (r["cls"], r["hook"], r["kit"], r["main"]))
        print("MANIFEST_SUM kit=%s differing=%d" % (sys.argv[2], len(rows)))
        sys.exit(3 if rows and "--strict" in sys.argv else 0)
    sys.exit("usage: hook_manifest.py check KIT --main DIR [--strict]")
