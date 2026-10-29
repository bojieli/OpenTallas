#!/usr/bin/env python3
"""DIE-HEAD-20: HEAD one-entry plan for the hd_tile sign-off regeneration (main tools only).
in : the composed HEAD regional plan (count sites, full pins) -> head_regional_one_entry.apply(tt, ff)
then hd_tile opt-ins already on main: reg_spine (DH17 spec), landing_export_form=fwd_buffer, tap_passthrough, and the
ring band 'i' from the main compose(band_reserve=ring_ff, band_spread=2.0, band_ring=ff) landed plan (DIE-HEAD-14
patch_band.py keys, now at plan level so gen_phys emits landing_placement/reserved_banks itself).
usage: mk_plan20.py REPO SRC_PLAN REG_SPINE.json OUT TT FF RINGFF_LANDED_PLAN"""
import json, sys
from pathlib import Path
W = Path(sys.argv[1]); src = Path(sys.argv[2]); spine = Path(sys.argv[3]); out = Path(sys.argv[4])
tt, ff = float(sys.argv[5]), float(sys.argv[6]); landed = Path(sys.argv[7])
sys.path.insert(0, str(W / "tools/s81_head")); sys.path.insert(0, str(W / "tools/die_plan"))
import head_regional_one_entry as OE, schema as S
raw, rep = OE.apply(json.loads(src.read_text()), tt, ff)
c = raw["partition_types"]["hd_tile"]
c["reg_spine"] = json.loads(spine.read_text())
c["clock"]["landing_export_form"] = "fwd_buffer"
c["clock"]["tap_passthrough"] = True
lr = json.loads(landed.read_text())
nb = next(t for tn, t in lr["partition_types"].items() if tn.startswith("hd_tile"))["clock"]["landing_contract"]["bands"]["i"]
b = c["clock"]["landing_contract"]["bands"]["i"]
for k in ("rect_um", "spread", "ring_place", "area_reserve_um2", "max_pin_to_band_hop_um", "placement"):
    if k in nb: b[k] = nb[k]
rs = [q for q in c["clock"]["reserved_sites_um"] if q.get("kind") == "landing_ring_bank" and q.get("ref") == "u_cland_i"]
assert len(rs) == 1; rs[0]["rect_um"] = list(b["rect_um"])
c["note"] += " | DIE-HEAD-20 hd_tile sign-off form: reg_spine (DH17) + fwd_buffer export + tap_passthrough + ring_ff band i"
err = S.validate(raw); assert not err, err[:5]
out.write_text(json.dumps(raw, indent=1) + "\n")
print(json.dumps(rep["hd_tile"]))
