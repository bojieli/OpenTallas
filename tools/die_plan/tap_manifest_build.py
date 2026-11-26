#!/usr/bin/env python3
"""Write the native placed sink-bin manifest that tap_derive.py consumes (C-TAP-LOAD, opt-in --tap-manifest).

  tap_manifest_build.py PLAN OUT_DIR TYPE=ODB_OR_TSV [...] [--kit-plan PLAN2]

Each spec is a placed 3_place.odb (dumped with sink_bins_from_place.dump, docker OpenROAD) or an existing
instance-named sink TSV (net inst master x y).  The bins are native-only (plan-row instances dropped), so tap_derive
adds the current cut's row flops itself.  footprint_sha256 is the digest of the tile in --kit-plan (the plan the kit
was placed from); without it the digest is taken from PLAN, which only asserts that the outline matched (the census
same-type-and-outline check) and is recorded as footprint_basis=current-plan.  The TSV path is kept in the manifest:
tap_derive reads tap_group cohorts from it.  Writes OUT_DIR/manifest.json and OUT_DIR/<type>__native.json.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sink_bins_from_place as sbp
import tap_derive


def build(raw, out_dir, specs, kit_raw=None, dump=sbp.dump):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for tn, src in sorted(specs.items()):
        tile = (kit_raw or raw)["partition_types"][tn]
        src = Path(src)
        if src.suffix == ".odb":
            tsv = out_dir / f"{tn}__sinks.tsv"
            dump(src, tsv)
        else:
            tsv = src.resolve()
        rows = sbp.read_tsv(tsv, native_only=True)
        if not rows:
            raise ValueError(f"{tn}: no native clock sinks in {tsv}")
        doc = dict(bin_um=10.8, n=len(rows), bins=sbp.bins(rows), type=tn, placed_kit=str(src),
                   source=f"tap_manifest_build {src}", native_only=True)
        path = out_dir / f"{tn}__native.json"
        path.write_text(json.dumps(doc) + "\n")
        manifest[tn] = dict(bins=path.name, sinks_tsv=str(tsv), footprint_sha256=tap_derive.footprint_digest(tile),
                            footprint_basis="kit-plan" if kit_raw else "current-plan")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("spec", nargs="+", metavar="TYPE=ODB_OR_TSV")
    ap.add_argument("--kit-plan", type=Path)
    a = ap.parse_args(argv)
    raw = json.loads(a.plan.read_text())
    kit = json.loads(a.kit_plan.read_text()) if a.kit_plan else None
    manifest = build(raw, a.out_dir, dict(s.split("=", 1) for s in a.spec), kit)
    print("MANIFEST", len(manifest), a.out_dir / "manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
