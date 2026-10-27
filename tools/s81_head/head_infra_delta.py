#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-2 plan delta for D-INFRA-FIRST-HEAD (COORD RULING INFRA-FIRST-HEAD-1, 2026-10-27 02:05).

--eb-move (the ruled step, kept as an opt-in for the record): elemB origin x 216.00 -> 211.68.  MEASURED: G0C FAIL
  (check.py hard_cores: 'origin [211.68, 734.4] not on the 8.64-um lattice'; track_offset_um may only carry < 2.16).
  An odd-multiple outline (rebuilt elemB 285.12 = 33 x 8.64) cannot be centred on the on-lattice tile axis 354.24 with
  an on-lattice origin.
Default = the lattice-legal equivalent: NO origin move.  The elemB clock entry is pinned at the tile MY axis
  (tile frame x 354.24 = origin 216.00 + 138.24, core-local 4.32 um west of the rebuilt 285.12 core's geometric centre,
  on the core's own 8.64 lattice), so the in-core island set is MY-invariant exactly as in the R1 census.
Clock entries (12.8a), tile frame:
  - elemA eA0..3: core centres of the rebuilt 319.68 outline (core-local 159.84, 159.84; orient-invariant)
    -> x 177.12 | 531.36, y 168.48 | 540.00;
  - elemB eB: (354.24, 734.40 + 142.56 = 876.96);
  - insertion = die common latency (target) with insertion_status PENDING (no centre-entry real view exists: the
    hold2 kits carry edge clk pins, elemA N face (293.58, 317.576), elemB W face (0.042, 257.58));
  - hd_serdes partition tap -> (1442.88, 77.76): the 150-um CORE-VDD digital strip under the PHY zone
    (VDDPHY rect starts at type-frame y 213.64), on the 8.64 lattice, x unchanged.
Pure plan edit of hd_tile / hd_serdes; prints a JSON report; writes OUT."""
import argparse, hashlib, json
from pathlib import Path

ENTRY = {"elemA": (159.84, 159.84), "elemB": (138.24, 142.56)}   # core-local R0
OUTLINE = {"elemA": 319.68, "elemB": 285.12}                       # rebuilt hold2 DIE_AREA (frame of ENTRY)
EB_X_OLD, EB_X_NEW = 216.0, 211.68
SERDES_TAP = (1442.88, 77.76)


def kind(mod):
    return "elemB" if "elemB" in mod else "elemA"


def to_frame(c, k, x, y):
    s = OUTLINE[k]
    ox, oy = c["origin_um"]
    lx, ly = {"R0": (x, y), "MY": (s - x, y), "MX": (x, s - y), "R180": (s - x, s - y)}[c["orient"]]
    return [round(ox + lx, 4), round(oy + ly, 4)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--eb-move", action="store_true", help="the ruled elemB origin x -4.32 (G0C FAIL, record only)")
    ap.add_argument("--no-entries", action="store_true")
    a = ap.parse_args()
    raw = Path(a.plan).read_bytes()
    P = json.loads(raw)
    rep = dict(base=a.plan, base_sha256=hashlib.sha256(raw).hexdigest())
    T = P["partition_types"]["hd_tile"]
    common = float(P["clock"]["common_latency_ps"])
    if a.eb_move:
        for c in T["hard_cores"]:
            if kind(c["module"]) == "elemB":
                assert abs(c["origin_um"][0] - EB_X_OLD) < 1e-6
                c["origin_um"] = [EB_X_NEW, c["origin_um"][1]]
                rep["eb_move"] = [EB_X_OLD, EB_X_NEW]
    if not a.no_entries:
        taps, moved = T["clock"]["taps"], []
        for c in T["hard_cores"]:
            k = kind(c["module"])
            tp = [t for t in taps if t["name"].startswith(c["inst"] + ".")]
            assert len(tp) == 1, (c["inst"], len(tp))
            tp = tp[0]
            new = to_frame(c, k, *ENTRY[k]) if not (a.eb_move and k == "elemB") else [round(EB_X_NEW + 142.56, 4), round(c["origin_um"][1] + 142.56, 4)]
            moved.append(dict(tap=tp["name"], old_xy=tp["xy"], old_insertion_ps=tp.get("insertion_ps"), new_xy=new))
            tp.update(xy=new, insertion_ps=common,
                      note="INSERTION PENDING (no centre-entry real view; hold2 kits have edge clk pins). "
                           "D-INFRA-FIRST-HEAD: 12.8a centre clock entry (M9->M5 in-core island), core-local "
                           f"{ENTRY[k]} on the rebuilt {OUTLINE[k]} outline; die common latency target until the "
                           "core's centre-entry signed view publishes its real insertion (12.3 v5.0)")
        T["clock"].pop("core_taps", None)
        S = P["partition_types"]["hd_serdes"]["clock"]
        rep["serdes"] = dict(old=list(S["tap_um"]), new=list(SERDES_TAP))
        S["tap_um"] = list(SERDES_TAP)
        rep["core_taps"] = moved
    out = json.dumps(P, indent=1) + "\n"
    Path(a.out).write_text(out)
    rep["out_sha256"] = hashlib.sha256(out.encode()).hexdigest()
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
