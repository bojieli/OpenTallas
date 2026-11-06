"""QC over-cap tap class (DIE-QC-84, 2026-11-06): apply measured density taps to every studied type.

For each type in clock_patches.json the base type must hash-match (sha256 of canonical JSON) or nothing is written.
Only partition_types[<type>].clock is replaced: sink_bins_file (measured register inventory of the type's retained
3_place), tap_mode density, tap_max_sinks min(plan, 1200), tap_target_sinks, tap_radius_um 200, tap_chain_affinity
(bounded per-bit grouping, default-off support on main).  No RTL, data cycles, source windows, uncertainty or hard
macro change.  New tap ports need the native re-bind + parent clock composition before adoption.
"""
import argparse, json, hashlib
from pathlib import Path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("plan", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--types", default="", help="comma list (default: all patched types)")
    a = ap.parse_args()
    p = json.loads(a.plan.read_text())
    patch = json.loads(Path(__file__).with_name("clock_patches.json").read_text())
    sel = [t for t in a.types.split(",") if t] or sorted(patch)
    bad = [tn for tn in sel if tn not in patch or tn not in p["partition_types"]
           or digest(p["partition_types"][tn]) != patch[tn]["base_type_sha256"]]
    if bad:
        raise SystemExit("base type changed or unknown (re-measure / re-compose): " + ", ".join(bad))
    for tn in sel:
        p["partition_types"][tn]["clock"] = patch[tn]["clock"]
    a.out.write_text(json.dumps(p, separators=(", ", ": ")) + "\n")
    print(json.dumps({"changed_types": sel, "data_cycles": 0, "source_windows_changed": False,
                      "qualification": "planning estimate; native re-bind/parent clock composition and CTS/sign-off pending"}))


if __name__ == "__main__":
    main()
