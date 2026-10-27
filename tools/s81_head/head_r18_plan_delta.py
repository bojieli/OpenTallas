#!/usr/bin/env python3
"""HEAD-R18 plan delta (COORD 2026-10-27 07:47 HEAD-CORE-R17 rulings item 4, both APPROVED):
  (a) copy-B burst FIFO depth BQ = 2 on hd_mesh u_core (ot_s81hd_mesh_ep_core) -- one type, so all 3 hd_mesh instances.
      Evidence claude/head-r17-rtl-1027@04f28d2bd9 (results/s81_head_r17/copyb): worst replay burst N = 2 records
      (8 x ATOB 1481 = 11848 cycles vs >= 8357 spacing); bench BQ 2 PASS, depth-1 mutant FAILS.  The RTL default 7 stays;
      the plan sets the parameter on the instance (gen_rtl emits #(.BQ(2))), as for CH_B on hd_lep*.
  (b) clock_entry tap rename: hd_tile core taps u_core.u_b.g_cv*.u_e*.clk -> .ft_mstrap_i, the real clock pin of the
      BUILT R14/R16 views, carried with its real position: the plan pin files cores/elem{A,B}_pins.json are regenerated
      from the built LEFs first (head_pins_from_lef.py), and for every hd_tile hard core this delta sets
      outline_um = the pin file outline (built SIZE) and the core tap xy = origin + track_offset + orient(native ft_mstrap_i pin) (R19: + track_offset).
      Insertion / budget fields unchanged (insertion stays PENDING until the signed views publish theirs).
  (c) HEAD-R19: the mirrored-axis track_offset_um of each hd_tile hard core is recomputed for the NEW outline (the old
      0.028 was derived from the 317.672 closed outline: 317.672 mod 0.048 = 0.008); for every axis the offset is the
      sub-pitch shift that puts the core's pins on the plan track (offset p/2, pitch p) in the type frame, from the
      pins' common core-frame residue (fails closed if the pins of one axis do not share one residue).
Nothing else in the plan changes (checked: dict-equal after undoing the edits).
  head_r18_plan_delta.py PLAN [--report OUT.json]   (rewrites PLAN in place; pin files are read via each core's pins_file)"""
import argparse, copy, hashlib, json
from pathlib import Path

PIN = "ft_mstrap_i"


def place(o, w, h, x, y):
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]


TRK = (0.048, 0.024)          # plan M4/M5 pitch, offset (schema.ASAP7_LAYERS, symmetric)
VERT = {"M3", "M5", "M7", "M9"}


def track_offset(pf, orient, origin):
    """per-axis sub-pitch shift that lands the M4/M5 pins on the plan tracks in the type frame."""
    w, h = pf["outline_um"]
    pt, off = TRK
    out = []
    for ax, size, mir in ((0, w, orient in ("MY", "R180")), (1, h, orient in ("MX", "R180"))):
        vals = {round((p["x"] if ax == 0 else p["y"]) % pt, 4) % pt for p in pf["pins"]
                if p["layer"] in ("M4", "M5") and ((p["layer"] in VERT) == (ax == 0))}
        if len(vals) != 1:
            raise SystemExit(f"{pf.get('macro')}: axis {ax} pins share no single track residue {sorted(vals)}")
        r = next(iter(vals))
        c = (origin[ax] + (size - r if mir else r)) % pt
        out.append(round((off - c) % pt, 4))
    return out


def apply(P, base):
    rep = dict(bq=[], taps=[])
    m = P["partition_types"]["hd_mesh"]
    cs = [c for c in m["contents"] if c["module"] == "ot_s81hd_mesh_ep_core"]
    if len(cs) != 1:
        raise SystemExit("hd_mesh: expected exactly one ot_s81hd_mesh_ep_core content")
    old = dict(cs[0].get("params") or {})
    cs[0]["params"] = {**old, "BQ": "2"}
    rep["bq"].append(dict(type="hd_mesh", inst=cs[0]["inst"], old=old.get("BQ", "default 7"), new="2",
                          instances=sorted(p["name"] for p in P["partitions"] if p["type"] == "hd_mesh")))
    T = P["partition_types"]["hd_tile"]
    taps = T["clock"]["taps"]
    for hc in T["hard_cores"]:
        pf = json.loads((base / hc["pins_file"]).read_text())
        pin = [q for q in pf["pins"] if q["name"] == PIN]
        if len(pin) != 1 or any(q["name"] in ("clk", "ck") for q in pf["pins"]):
            raise SystemExit(f"{hc['pins_file']}: need exactly one {PIN} and no clk/ck pin (regenerate from the built LEF)")
        w, h = pf["outline_um"]
        x, y = place(hc["orient"], w, h, pin[0]["x"], pin[0]["y"])
        to = track_offset(pf, hc["orient"], hc["origin_um"])
        xy = [round(hc["origin_um"][0] + to[0] + x, 4), round(hc["origin_um"][1] + to[1] + y, 4)]   # placed box = origin + track_offset
        tp = [t for t in taps if t.get("kind") == "core" and t["name"] == hc["inst"] + ".clk"]
        if len(tp) != 1:
            raise SystemExit(f"{hc['inst']}: expected one core tap {hc['inst']}.clk")
        tp = tp[0]
        rep["taps"].append(dict(inst=hc["inst"], old=tp["name"], new=hc["inst"] + "." + PIN, old_xy=tp["xy"], new_xy=xy,
                               layer=pin[0]["layer"], outline_old=hc["outline_um"], outline_new=[w, h],
                               pins_file=hc["pins_file"], pins_canon_sha256=pf.get("pins_canon_sha256"), source=pf.get("source")))
        tp["name"], tp["xy"] = hc["inst"] + "." + PIN, xy
        hc["outline_um"] = [w, h]
        rep["taps"][-1].update(track_offset_old=hc.get("track_offset_um"), track_offset_new=to)
        hc["track_offset_um"] = to
    return rep


def undo(P, rep):
    Q = copy.deepcopy(P)
    c = [c for c in Q["partition_types"]["hd_mesh"]["contents"] if c["module"] == "ot_s81hd_mesh_ep_core"][0]
    c["params"].pop("BQ", None)
    if not c["params"]:
        c.pop("params")
    T = Q["partition_types"]["hd_tile"]
    for r in rep["taps"]:
        tp = [t for t in T["clock"]["taps"] if t["name"] == r["new"]][0]
        tp["name"], tp["xy"] = r["old"], r["old_xy"]
        hc = [hc for hc in T["hard_cores"] if hc["inst"] == r["inst"]][0]
        hc["outline_um"] = r["outline_old"]
        hc["track_offset_um"] = r["track_offset_old"]
    return Q


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("--report")
    a = ap.parse_args()
    p = Path(a.plan); raw = p.read_bytes(); P = json.loads(raw); P0 = copy.deepcopy(P)
    if any("BQ" in (c.get("params") or {}) for c in P["partition_types"]["hd_mesh"]["contents"]):
        raise SystemExit("plan already carries BQ (delta applied?)")
    rep = apply(P, p.parent)
    if len(rep["taps"]) != 5:
        raise SystemExit(f"expected 5 hd_tile core taps, got {len(rep['taps'])}")
    if undo(P, rep) != P0:
        raise SystemExit("delta changed more than BQ + tap names/xy + core outline/track_offset")
    out = json.dumps(P, indent=2) + "\n"
    p.write_text(out)
    rep.update(plan=str(p), sha256_before=hashlib.sha256(raw).hexdigest(), sha256_after=hashlib.sha256(out.encode()).hexdigest(),
               other_content_changed=False)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(bq=rep["bq"], taps=len(rep["taps"]), before=rep["sha256_before"][:12], after=rep["sha256_after"][:12])))


if __name__ == "__main__":
    main()
