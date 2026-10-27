#!/usr/bin/env python3
"""Give a CLOSED ref_tile view a unique master name (no re-route, no geometry or timing change).

One generic RTL module hardened at two parameter sets yields two views both called <top>; a parent or die cannot bind
both.  This copies views/<old> to views/<new> renaming only the master: LEF MACRO/FOREIGN/END, Liberty library and cell
names, and the name fields of the json records.  Every other byte is unchanged; renamed_from.json records the source
sha256 of each file.  The RTL must provide module <new> with the identical port list (a fixed-parameter wrapper).

  rename_view.py physical/ref_tile/<kit>/views/<old> <new>
"""
import hashlib, json, re, shutil, sys
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    src, new = Path(sys.argv[1].rstrip("/")), sys.argv[2]
    old = src.name
    dst = src.parent / new
    if not (src / f"{old}.lef").exists():
        print(f"rename_view: {src}/{old}.lef missing", file=sys.stderr)
        return 2
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir()
    rec = {"schema": "opentallas.ref_tile.view_rename.v1", "from_view": str(src), "from_master": old, "master": new,
           "rule": "master name only; geometry, pins and timing arcs byte-identical", "files": {}}
    for f in sorted(src.iterdir()):
        if not f.is_file():
            continue
        out = dst / f.name.replace(old, new)
        t = f.read_text(errors="replace")
        if f.suffix == ".lef":
            n0 = len(re.findall(rf"^(MACRO|\s*FOREIGN|END) {old}\b", t, flags=re.M))
            t = re.sub(rf"^(MACRO|\s*FOREIGN|END) {old}\b", lambda m: f"{m.group(1)} {new}", t, flags=re.M)
            assert n0 == 3, f"{f}: expected MACRO/FOREIGN/END, found {n0}"
        elif f.suffix == ".lib":
            t, a = re.subn(rf"^library \({old}_(tt|ff|ss)\)", lambda m: f"library ({new}_{m.group(1)})", t, flags=re.M)
            t, b = re.subn(rf'^(\s*)cell \("{old}"\)', lambda m: f'{m.group(1)}cell ("{new}")', t, flags=re.M)
            assert a == 1 and b == 1, f"{f}: library {a} cell {b}"
        elif f.suffix == ".json":
            d = json.loads(t)
            if isinstance(d, dict):
                if d.get("name") == old:
                    d["name"] = new
                for v in d.values():
                    if isinstance(v, dict) and v.get("cell") == old:
                        v["cell"] = new
                if d.get("cell") == old:
                    d["cell"] = new
            t = json.dumps(d, indent=1) + "\n"
        out.write_text(t)
        rec["files"][out.name] = {"from": f.name, "from_sha256": sha(f), "sha256": sha(out)}
    (dst / "renamed_from.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"rename_view: {src} -> {dst} ({len(rec['files'])} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
