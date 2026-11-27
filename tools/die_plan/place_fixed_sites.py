"""Lower fixed placement-region seats to the kit's native placement hooks."""

import math
from pathlib import Path
import re
import shutil


SITE_DATA = "place_fixed_sites_data.tcl"
SITE_HOOK = "place_fixed_sites.tcl"
SAFE_NAME = re.compile(r"[A-Za-z0-9_.$/\[\]:+~-]+")


def _coordinates(values, length):
    if len(values) != length or not all(math.isfinite(value) for value in values):
        raise ValueError("fixed sites require finite rectangular coordinates")
    return values


def install(kit, regions):
    """Emit exact member, expected master and reserved footprint before placement."""
    if not any(region.get("kind") == "fixed" for region in regions):
        return
    region_names, instance_names = set(), set()
    rows = []
    for region in regions:
        name = region["name"]
        if region.get("kind") != "fixed":
            raise ValueError("fixed sites and optimizer regions cannot share a kit")
        if name in region_names or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            raise ValueError(f"bad or duplicate fixed region {name!r}")
        region_names.add(name)
        x0, y0, x1, y1 = _coordinates(region["box_um"], 4)
        sites = region["fixed_sites"]
        if not sites:
            raise ValueError(f"fixed region {name} has no members")
        for site in sites:
            instance, master = site["instance"], site["master"]
            if not SAFE_NAME.fullmatch(instance) or not SAFE_NAME.fullmatch(master):
                raise ValueError(f"invalid fixed-site instance or master in {name}")
            if instance in instance_names:
                raise ValueError(f"duplicate fixed-site instance {instance}")
            instance_names.add(instance)
            x, y, right, top = _coordinates(site["reserve_rect_um"], 4)
            if not (x0 <= x < right <= x1 and y0 <= y < top <= y1):
                raise ValueError(f"fixed-site reservation for {instance} exceeds region {name}")
            rect = " ".join(str(coordinate) for coordinate in (x, y, right, top))
            rows.append(f"  {{{{{instance}}} {{{master}}} {rect}}}")

    kit = Path(kit)
    (kit / SITE_DATA).write_text("set ::ot_fixed_sites {\n" + "\n".join(rows) + "\n}\n")
    shutil.copyfile(Path(__file__).with_name(SITE_HOOK), kit / SITE_HOOK)
    for filename, action in (("face_flops.tcl", "seed"), ("face_flops_release.tcl", "check")):
        with (kit / filename).open("a") as hook:
            hook.write(f"\nsource /work/{SITE_HOOK}\not_fixed_sites::{action}\n")
