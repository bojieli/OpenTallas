#!/usr/bin/env python3
"""DIE-HBM-82-SPB: apply the q_spb2 U-turn ft event to a generated q_spb2 kit, kit-locally and only for the re-sited
slots: their ft_stations.txt rows and their ft_bit_sites.tcl entries are rewritten with gen_phys's own formats
(_um + ft_bit_sites.table) from the event plan; every other row/byte is kept.  usage: kit_patch.py PLAN.json KIT SLOT,SLOT"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / "tools/die_plan"))
from gen_phys import _um  # noqa: E402
import ft_bit_sites  # noqa: E402
plan, kit, names = json.loads(Path(sys.argv[1]).read_text()), Path(sys.argv[2]), sys.argv[3].split(",")
slots = {s["name"]: s for s in plan["partition_types"]["q_spb2"]["ft_slots"] if s["name"] in names}
assert set(slots) == set(names), slots.keys()
f = kit / "ft_stations.txt"; out = []
seen = set()
for ln in f.read_text().splitlines():
    nm = ln.split()[0] if ln.strip() and not ln.startswith("#") else None
    if nm in slots:
        s = slots[nm]; seen.add(nm)
        regs = " ".join(f"{_um(x)} {_um(y)}" for x, y in s["regs_um"])
        ln = f"{nm} {int(s['stations'])} {s['in_face']} {s['out_face']} {regs}".rstrip()
    out.append(ln)
assert seen == set(names), seen
f.write_text("\n".join(out) + "\n")
b = kit / "ft_bit_sites.tcl"; t = b.read_text()
assert not any(("{" + n + ",") in t or ("{" + n + "}") in t for n in names), "slot already has bit sites"
add = ft_bit_sites.table(list(slots.values())).splitlines()[3:]   # drop the 3 header lines
b.write_text(t.rstrip("\n") + "\n" + "\n".join(add) + "\n")
print("patched", kit, names, "bit-site lines", len(add))
