"""Correct the l48z mesh receiver band's vertical setback without changing its interface or RTL.

The E-face pins span y=8.856..34.104.  The old band starts at y=17.28, so
pinslot clamps its lower keys onto the same rows and spills their four captures
westward (measured input reach 114.819 um, input-group p90 98.852 um).
Move the unchanged band down one 8.64 um PG period / 32 native rows.  Its
8.64..34.64 range then contains the complete pin column.  Physical placement
and geometry checks must qualify this candidate before routing or adoption.
"""
import argparse
import copy
import json
import shutil
from pathlib import Path

OLD = [727.92, 17.28, 820.8, 43.28]
NEW = [727.92, 8.64, 820.8, 34.64]


def apply(plan):
    result = copy.deepcopy(plan)
    tile = result["partition_types"]["hd_mesh_e"]
    if tile["outline_um"] != [838.08, 86.4]:
        raise ValueError("mesh receiver correction requires the measured l48z outline")
    changed = 0

    def walk(value):
        nonlocal changed
        if isinstance(value, dict):
            if value.get("instance") == "u_cland_m_tx_ft_i" and "rect_um" in value:
                if value["rect_um"] != OLD:
                    raise ValueError("mesh receiver band differs from the measured l48z source")
                value["rect_um"] = NEW[:]
                changed += 1
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(tile["clock"])
    if not changed:
        raise ValueError("measured mesh receiver band is absent")
    return result, changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    plan, count = apply(json.loads((args.source / "source_plan.json").read_text()))
    shutil.copytree(args.source, args.out)
    (args.out / "source_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    report = dict(base="l48z", type="hd_mesh_e", old_band_um=OLD, new_band_um=NEW,
                  changed_records=count, added_data_cycles=0, added_boot_cycles=0,
                  interface_changed=False, physical_qualified=False)
    (args.out / "mesh_pin_delta.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
