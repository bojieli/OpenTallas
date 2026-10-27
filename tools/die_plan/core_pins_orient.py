#!/usr/bin/env python3
"""CLOCK-KV-R12 10-26: top-down re-pin of hard cores whose plan orientation changed (KV headmirror MX/MY flips).

A mirror flip of a placed core moves its N/S (MX) or E/W (MY) pin groups to the opposite face, so a group that faced
its partners now faces away (check.py core_faces).  The structural fix is top-down pin assignment (M:top-down pins):
each core instance gets the pin variant D in {R0, MX, MY, R180} of its module's pins_file (data pins mirrored in the
core frame) that minimises its away-facing groups/pins under the SAME check.py core_faces model, so in the type frame
the data pins sit where the partners are while the core body (and its in-core clock island, 12.2a1) keeps the plan
orientation.  Clock / reset / island pins are NOT mirrored (the clock entry stays at the plan-fixed island).
One pins_file per (module, D): every instance of a module that needs the same variant shares one file (= one core
view per (module, D)); D = R0 keeps the original file.  Ties keep R0.  Faces only: the core outline, origin and orient
are unchanged; on-track: N/S pins keep x (y -> ch - y), E/W pins keep y (x -> cw - x) on symmetric tracks.

    core_pins_orient.py PLAN_IN PLAN_DIR PLAN_OUT REPORT [--types a,b]   (PLAN_OUT is written into PLAN_DIR's tree)
"""
import argparse, copy, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check as C   # noqa: E402
import schema as S  # noqa: E402

FLIP = {"R0": (0, 0), "MY": (1, 0), "MX": (0, 1), "R180": (1, 1)}
INV = {v: k for k, v in FLIP.items()}
CLKRST = re.compile(r'^(clk|ck|ck_\w+|clk_\w+|rst_n|arst_n|\w*_rst_n|\w*isl\w*|\w*island\w*)(\[\d+\])?$')


def compose(o, d):
    a, b = FLIP[o], FLIP[d]
    return INV[(a[0] ^ b[0], a[1] ^ b[1])]


def score(raw, plan_dir, d, types=None):
    r = copy.deepcopy(raw)
    for tn, t in r["partition_types"].items():
        if types and tn not in types:
            continue
        for hc in t.get("hard_cores", []):
            if hc.get("orient", "R0") in FLIP:
                hc["orient"] = compose(hc.get("orient", "R0"), d)
    P = S.Plan(r, Path(plan_dir) / "die_plan.json")
    per = {}
    C.check_core_faces(P, C.Report(True), plan_dir, None, per_core=per)
    return per


def mirror_pins(src, dst, d, cw, ch, layers=None, hc=None):
    """mirror the data pins by d; with `layers` (plan layers) + `hc` (one placed instance), a mirrored pin whose
    track coordinate lands off the plan track in the type frame (core width not a track multiple) snaps to the
    nearest on-track coordinate (< pitch/2)."""
    js = json.loads(Path(src).read_text())
    pins = js["pins"] if isinstance(js, dict) else js
    fx, fy = FLIP[d]
    kept = snapped = 0
    o = (hc or {}).get("orient", "R0")
    ox = (hc or {}).get("origin_um", [0, 0])[0] + ((hc or {}).get("track_offset_um") or [0, 0])[0]
    oy = (hc or {}).get("origin_um", [0, 0])[1] + ((hc or {}).get("track_offset_um") or [0, 0])[1]
    ofx, ofy = FLIP.get(o, (0, 0))
    for p in pins:
        nm = p.get("name") or p.get("bus", "")
        if CLKRST.match(nm):
            kept += 1
            continue
        if fx:
            p["x"] = round(cw - p["x"], 6)
        if fy:
            p["y"] = round(ch - p["y"], 6)
        L = (layers or {}).get(p["layer"])
        if L and hc is not None and ((fx and L["dir"] == "V") or (fy and L["dir"] == "H")):
            ax, org, flip, ext = ("x", ox, ofx, cw) if L["dir"] == "V" else ("y", oy, ofy, ch)
            tf = org + (ext - p[ax] if flip else p[ax])
            k = round((tf - L["offset_um"]) / L["pitch_um"])
            tn = L["offset_um"] + k * L["pitch_um"]
            if abs(tn - tf) > 1e-6:
                p[ax] = round((ext - (tn - org)) if flip else (tn - org), 6)
                snapped += 1
    # a mirrored data pin landing on a kept clock/reset pin slides along its face to the nearest free track
    pitch = dict(M4=0.048, M5=0.048, M6=0.064, M7=0.064)
    seen = {(p["layer"], round(p["x"], 4), round(p["y"], 4)) for p in pins if CLKRST.match(p.get("name") or "")}
    slid = 0
    for p in pins:
        if CLKRST.match(p.get("name") or ""):
            continue
        k = (p["layer"], round(p["x"], 4), round(p["y"], 4))
        if k in seen:
            ns = p["y"] < 1e-3 + 0.2 or p["y"] > ch - 0.2      # N/S face pin: slide in x, else in y
            ax = "x" if ns else "y"
            lim = cw if ns else ch
            for j in range(1, 2000):
                for sgn in (1, -1):
                    v = round(p[ax] + sgn * j * pitch[p["layer"]], 6)
                    q = (p["layer"], round(v, 4) if ax == "x" else k[1], k[2] if ax == "x" else round(v, 4))
                    if 2.16 <= v <= lim - 2.16 and q not in seen:
                        p[ax] = v; k = q; slid += 1
                        break
                else:
                    continue
                break
            else:
                raise ValueError(f"{dst}: no free track for {p.get('name')}")
        seen.add(k)
    if isinstance(js, dict):
        if isinstance(js.get("faces"), dict) and (fx or fy):
            sw = {"N": "S", "S": "N"} if fy else {}
            sw.update({"E": "W", "W": "E"} if fx else {})
            js["faces"] = {sw.get(f, f): v for f, v in js["faces"].items()}
        js["source"] = f"{js.get('source', '')} | CLOCK-KV-R12 core_pins_orient: data pins mirrored {d} " \
                       f"(clock/reset/island pins kept: {kept}, data pins slid off them: {slid}, track snaps: {snapped})"
    Path(dst).write_text(json.dumps(js, indent=0) + "\n")
    return kept


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("plan_dir"); ap.add_argument("out"); ap.add_argument("report")
    ap.add_argument("--types")
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    types = set(a.types.split(",")) if a.types else None
    sc = {d: score(raw, a.plan_dir, d, types) for d in FLIP}
    layers = S.Plan(copy.deepcopy(raw), Path(a.plan_dir) / "die_plan.json").layers
    choice, files, before, after = {}, {}, [0, 0], [0, 0]
    for tn, t in raw["partition_types"].items():
        if types and tn not in types:
            continue
        for hc in t.get("hard_cores", []):
            k = (tn, hc["inst"])
            if k not in sc["R0"] or not hc.get("pins_file") or hc.get("orient", "R0") not in FLIP:
                continue
            base = sc["R0"][k]
            best = min(FLIP, key=lambda d: (sc[d].get(k, base)[1], sc[d].get(k, base)[0], d != "R0"))
            v = sc[best].get(k, base)
            before[0] += base[1]; before[1] += base[0]; after[0] += v[1]; after[1] += v[0]
            if best == "R0" or v[1] >= base[1] and v[0] >= base[0]:
                continue
            src = hc["pins_file"]
            stem = re.sub(r"(_f(MX|MY|R180))?\.json$", "", src)
            dst = f"{stem}_f{best}.json"
            if dst not in files:
                kept = mirror_pins(Path(a.plan_dir) / src, Path(a.plan_dir) / dst, best, *hc["outline_um"],
                                   layers=layers, hc=hc)
                files[dst] = dict(src=src, flip=best, module=hc["module"], clock_pins_kept=kept)
            hc["pins_file"] = dst
            choice[f"{tn}/{hc['inst']}"] = dict(flip=best, module=hc["module"], orient=hc.get("orient", "R0"),
                                                groups_away=[base[1], v[1]], pins_away=[base[0], v[0]])
    raw["note"] = "CLOCK-KV-R12 core_pins_orient (top-down re-pin after mirror flips) <- " + raw.get("note", "")[:200]
    Path(a.out).write_text(json.dumps(raw) + "\n")
    rep = dict(cores_repinned=len(choice), pin_files=files, groups_away=[before[0], after[0]],
               pins_away=[before[1], after[1]], cores=choice)
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"re-pinned {len(choice)} cores, {len(files)} pin variants; away groups {before[0]} -> {after[0]}, "
          f"away pins {before[1]} -> {after[1]}")


if __name__ == "__main__":
    main()
