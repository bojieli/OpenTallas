#!/usr/bin/env python3
"""PATH-HBM 10-26 (COORD 01:21 APPROVED, folded into D-HBM-B1): HBM hard-core route ceiling M5.

Every planned HBM hard core gets the owner-default tile ceiling (10-12: M5): OBS M1-M5 (hard_cores[].obs_max = M5)
and pins on M4/M5 only.  The core pins_file pins that sit on M6 (H) / M7 (V) move to the same-direction layer
M4 / M5 (direction, face and order kept), snapped to the nearest FREE target track of that face (track phase taken
from the plan layer table + the core's track_offset_um; checked against the file's existing target-layer pins).
Pins never leave their face and never leave the face span; if a face has more pins than free target tracks the tool
FAILS (no silent overlap).  Partition FT then owns M6/M7 over every core (die_trial core OBS = M5).

    python3 path_hbm_m5_ceiling.py PLAN_DIR OUT_DIR       (copies PLAN_DIR, edits die_plan.json + cores/*.json)

Writes OUT_DIR/m5_ceiling_report.json (per pins_file: moved pins, max/mean displacement, per-face fill).
Pure geometry: no lanes, ports, outlines, stations or cycles change.
"""
import collections
import json
import math
import shutil
import sys
from pathlib import Path

MAP = {"M6": "M4", "M7": "M5"}
DIRS = {"M4": "H", "M5": "V"}          # H layer: pin coordinate along the face is y (E/W faces); V: x (N/S faces)


def face_of(x, y, w, h):
    return min((("S", y), ("N", h - y), ("W", x), ("E", w - x)), key=lambda t: t[1])[0]


def snap_file(pins, w, h, layers, toff, tol=1e-4):
    """Remap M6/M7 pins in place; return stats."""
    used = collections.defaultdict(set)          # (face, layer) -> set(track index)
    phase = {}
    for L in ("M4", "M5"):
        pitch, off = layers[L]["pitch_um"], layers[L]["offset_um"]
        t = toff[1] if DIRS[L] == "H" else toff[0]
        ph = (off + t) % pitch
        # trust the file's own target-layer pins when they agree on one phase
        own = collections.Counter(round(((p["y"] if DIRS[L] == "H" else p["x"]) - 0) % pitch, 4)
                                  for p in pins if p["layer"] == L)
        if own:
            top, n = own.most_common(1)[0]
            if n >= 0.9 * sum(own.values()):
                ph = top
        phase[L] = ph
    def idx(L, v):
        pitch = layers[L]["pitch_um"]
        return int(round((v - phase[L]) / pitch))
    for p in pins:
        if p["layer"] in ("M4", "M5"):
            f = face_of(p["x"], p["y"], w, h)
            used[(f, p["layer"])].add(idx(p["layer"], p["y"] if DIRS[p["layer"]] == "H" else p["x"]))
    moved = []
    todo = [p for p in pins if p["layer"] in MAP]
    # deterministic: by face then coordinate along the face
    def along(p):
        return p["y"] if MAP[p["layer"]] == "M4" else p["x"]
    todo.sort(key=lambda p: (face_of(p["x"], p["y"], w, h), MAP[p["layer"]], along(p)))
    for p in todo:
        L = MAP[p["layer"]]
        pitch = layers[L]["pitch_um"]
        f = face_of(p["x"], p["y"], w, h)
        span = h if DIRS[L] == "H" else w
        v = along(p)
        k0 = idx(L, v)
        kmin = int(math.ceil((0.0 + pitch / 2 - phase[L]) / pitch - tol))
        kmax = int(math.floor((span - pitch / 2 - phase[L]) / pitch + tol))
        best = None
        for d in range(0, kmax - kmin + 2):
            for k in ((k0 + d, k0 - d) if d else (k0,)):
                if kmin <= k <= kmax and k not in used[(f, L)]:
                    best = k
                    break
            if best is not None:
                break
        if best is None:
            raise SystemExit(f"FAIL face {f} layer {L}: no free track for {p['name']}")
        used[(f, L)].add(best)
        nv = round(phase[L] + best * pitch, 4)
        moved.append(abs(nv - v))
        if DIRS[L] == "H":
            p["y"] = nv
        else:
            p["x"] = nv
        p["layer"] = L
    fill = {}
    for (f, L), s in used.items():
        span = h if DIRS[L] == "H" else w
        fill[f"{f}.{L}"] = round(len(s) / (span / layers[L]["pitch_um"]), 3)
    return dict(moved=len(moved), max_disp_um=round(max(moved), 4) if moved else 0.0,
                mean_disp_um=round(sum(moved) / len(moved), 4) if moved else 0.0, fill=fill)


def main():
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    if out.exists():
        raise SystemExit(f"{out} exists")
    shutil.copytree(src, out, symlinks=True)
    plan = json.loads((out / "die_plan.json").read_text())
    layers = {}
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
    import schema as S
    layers = S.Plan(plan).layers
    files = collections.defaultdict(list)
    n_obs = collections.Counter()
    for tn, t in plan["partition_types"].items():
        for hc in t.get("hard_cores", []):
            old = hc.get("obs_max")
            if old != "M5":
                n_obs[f"{old}->M5"] += 1
                hc["obs_max"] = "M5"
            files[hc["pins_file"]].append(hc)
    rep = dict(tool="path_hbm_m5_ceiling", src=str(src), obs_changes=dict(n_obs), files={})
    for f, hcs in sorted(files.items()):
        w, h = hcs[0]["outline_um"]
        toffs = {tuple(hc.get("track_offset_um", [0, 0])) for hc in hcs}
        if len({tuple(hc["outline_um"]) for hc in hcs}) != 1 or len(toffs) != 1:
            raise SystemExit(f"FAIL {f}: shared pins_file with different outline/track offset {toffs}")
        fp = out / f
        pins = json.loads(fp.read_text())
        if not any(p["layer"] in MAP for p in pins):
            continue
        before = collections.Counter(p["layer"] for p in pins)
        st = snap_file(pins, w, h, layers, list(next(iter(toffs))))
        st["before"] = dict(before)
        st["after"] = dict(collections.Counter(p["layer"] for p in pins))
        assert not (set(st["after"]) - {"M2", "M3", "M4", "M5"}), st["after"]
        fp.write_text(json.dumps(pins) + "\n")
        rep["files"][f] = st
    plan.setdefault("note", "")
    plan["note"] = (plan["note"] + " | D-HBM-B1 M5 ceiling (COORD 10-26 01:21): every hard core OBS M1-M5, pins M4/M5").strip(" |")
    (out / "die_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    rep["n_files_remapped"] = len(rep["files"])
    rep["pins_moved"] = sum(v["moved"] for v in rep["files"].values())
    rep["max_disp_um"] = max((v["max_disp_um"] for v in rep["files"].values()), default=0)
    rep["max_fill"] = max((x for v in rep["files"].values() for x in v["fill"].values()), default=0)
    (out / "m5_ceiling_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "files"}))


if __name__ == "__main__":
    main()
