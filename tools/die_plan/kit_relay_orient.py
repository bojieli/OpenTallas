"""kit_relay_orient.py -- relay_orient.py in the kit preflight (S81-STAGE-SEAT 11-25, COORD scope add; default on, OT_RELAY_ORIENT=0 off).

Seats exist only at kit level (relay_seats / exit_relay_seats / hard_seats in a kit seats JSON, `ot_seat {inst} x y` lines in the kit
macro_place.tcl); the plan carries none.  Before macro placement every kit that has both gets each relay / exit-relay macro oriented
by its outgoing hop (tools/die_plan/relay_orient.py): macro_place.tcl is rewritten to `ot_seat_o {inst} x y ORIENT` (original kept
once as macro_place.pre_orient.tcl) and <kit>/relay_orient.json records the counts.  Idempotent; a kit without seats is SKIP.

    apply(kit, env=None) -> (status, line)      status in ON / OFF / SKIP / FAIL (FAIL never raises; the kit is left unchanged)
"""
import json
import os
import shutil
from pathlib import Path

SEATS_NAMES = ("relay_seats.json", "seats.json", "kit_seats.json", "seats/seats.json")


def find_seats(kit):
    for n in SEATS_NAMES:
        p = Path(kit) / n
        if p.is_file():
            return p
    return None


def apply(kit, env=None):
    env = os.environ if env is None else env
    if env.get("OT_RELAY_ORIENT", "1") == "0":
        return "OFF", "RELAY-ORIENT OFF (OT_RELAY_ORIENT=0)"
    kit = Path(kit)
    mp, sj = kit / "macro_place.tcl", find_seats(kit)
    if sj is None or not mp.is_file():
        return "SKIP", "RELAY-ORIENT SKIP no seats json / macro_place.tcl"
    try:
        import relay_orient as RO
        seats = json.loads(sj.read_text())
        text = mp.read_text()
        pos = RO.tcl_positions(text)
        faces = tuple(env.get("OT_RELAY_ORIENT_OUT_FACES", "E,S").split(","))
        orients = RO.orient_seats(seats, pos, faces, float(env.get("OT_RELAY_ORIENT_TOL", "5")))
        if not orients:
            return "SKIP", "RELAY-ORIENT SKIP no relay seats in " + sj.name
        new = RO.rewrite_tcl(text, orients)
        flipped = sum(1 for o in orients.values() if o != "R0")
        if new != text:
            bak = kit / "macro_place.pre_orient.tcl"
            if not bak.exists():
                shutil.copyfile(mp, bak)
            tmp = kit / ".macro_place.tcl.orient"
            tmp.write_text(new)
            os.replace(tmp, mp)
        import collections
        rec = {"seats": sj.name, "relays": len(orients), "flipped": flipped, "orient": dict(collections.Counter(orients.values())),
               "out_faces": list(faces)}
        (kit / "relay_orient.json").write_text(json.dumps(rec, indent=1) + "\n")
        return "ON", f"RELAY-ORIENT ON relays={len(orients)} flipped={flipped} {rec['orient']}"
    except Exception as e:  # noqa: BLE001 the preflight never dies on this step; the kit keeps its seats as they were
        return "FAIL", f"RELAY-ORIENT FAIL {type(e).__name__}: {str(e)[:200]} (kit unchanged)"
