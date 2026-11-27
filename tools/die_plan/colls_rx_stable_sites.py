"""Install exact same-cycle Coll_s receiver locations from its reviewed source packet."""

import json
from pathlib import Path
import re
import shutil

PACKET = "colls_rx_stable_source.json"
HOOK = "colls_rx_stable_sites.tcl"
SCOPE = re.compile(
    r"u_bound\.u_g_face_[34]_u_face\.u_rx\.(?:rd_stage|o_data)\\\[\d+\\\]\$_DFF_P_"
    r"|u_bound\.u_bout_rec_rx_s[12]/q\\\[\d+\\\]\$_DFF_P_"
)

def install(kit_dir, type_plan):
    """Guard all reviewed destinations against their authoritative relay_sites plan values."""
    source = Path(__file__).resolve().parent
    packet = json.loads((source / PACKET).read_text())
    seats = type_plan["relay_sites"]
    exact = {}
    lines = ["set ot_colls_rx_targets {"]
    for key, name, x, y, orient in packet["seats"]:
        if not SCOPE.fullmatch(name) or orient not in ("R0", "MY", "MX", "R180"):
            raise ValueError(f"unexpected Coll_s RX receiver seat {key}")
        if key in exact or seats.get(key) != [x/1000, y/1000]:
            raise ValueError(f"Coll_s RX relay_sites changed at {key}")
        exact[key] = True
        lines.append("    {{%s} %d %d %s}" % (name, x, y, orient))
    if len(exact) != 1773:
        raise ValueError(f"expected all 1773 Coll_s RX receiver seats, got {len(exact)}")
    lines.append("}")
    (kit_dir / "colls_rx_stable_targets.tcl").write_text("\n".join(lines) + "\n")
    shutil.copyfile(source / HOOK, kit_dir / HOOK)
    for filename, operation in (("face_flops.tcl", "seed"), ("face_flops_release.tcl", "retain")):
        with (kit_dir / filename).open("a") as f:
            f.write(f"\nsource /work/colls_rx_stable_targets.tcl\nsource /work/{HOOK}\n"
                    f"::ot_colls_rx_stable::run $ot_colls_rx_targets {operation}\n")
    return dict(type_plan, relay_sites={name: xy for name, xy in seats.items() if name not in exact})
