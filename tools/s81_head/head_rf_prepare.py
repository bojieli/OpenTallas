#!/usr/bin/env python3
"""DH58-RFPLAN: a PREPARED kit-wave dir for the HEAD l48rf plan (head_rf_plan_delta.py output).

  copy BASE_PREPARED (e.g. l48h1 dh55-cland/prep_v3) -> OUT, then
  - source_plan.json = the l48rf plan (RF_DIR/source_plan.json)
  - source_sidecar.json: a single-partition clock-landing region (tag == partition name) of a grown partition gets
    the grown slot rect as box_um (clock_landings.Landings maps a part to the region holding its centre; the grow
    moved the centre of hd_st_m parts out of their old box).  Multi-part regions must already hold the new rect.
  - published/: every eligible type whose plan record changed is republished with
    head_cland_stage_delta.republish (GEN bootstrap + START alias patch), wave_prepare.json records it (l48rf key).

usage: head_rf_prepare.py BASE_PREPARED RF_DIR OUT --tools TOOLS_ROOT [--types t1,t2] [--core-pin F.json] [--event l48rf]
"""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rect(plan, p):
    w, h = plan["partition_types"][p["type"]]["outline_um"]
    return [p["origin_um"][0], p["origin_um"][1], round(p["origin_um"][0] + w, 3), round(p["origin_um"][1] + h, 3)]


def inside(a, b, tol=1e-3):
    return b[0] <= a[0] + tol and b[1] <= a[1] + tol and b[2] >= a[2] - tol and b[3] >= a[3] - tol


def regrow_regions(side, old, new):
    """returns the changed regions; raises when a grown part cannot be held by its region"""
    op = {p["name"]: p for p in old["partitions"]}
    by_tag = {r["tag"]: r for r in side["regions"]}
    changed = []
    for p in new["partitions"]:
        o, n = rect(old, op[p["name"]]), rect(new, p)
        if o == n:
            continue
        own = [r for r in side["regions"] if inside(o, r["box_um"])]
        if len(own) != 1:
            raise SystemExit(f"{p['name']}: {len(own)} regions hold the old slot")
        r = own[0]
        if inside(n, r["box_um"]):
            continue
        if r["tag"] != p["name"] or r.get("parts", 1) != 1:
            raise SystemExit(f"{p['name']}: grown slot {n} leaves multi-part region {r['tag']} {r['box_um']}")
        for q in side["regions"]:
            b = q["box_um"]
            if q is not r and b[0] < n[2] - 1e-3 and n[0] < b[2] - 1e-3 and b[1] < n[3] - 1e-3 and n[1] < b[3] - 1e-3:
                raise SystemExit(f"{p['name']}: grown region overlaps region {q['tag']}")
        changed.append(dict(tag=r["tag"], old=r["box_um"], new=n))
        r["box_um"] = n
    assert len(by_tag) == len(side["regions"])
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", type=Path)
    ap.add_argument("rf", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--tools", type=Path, required=True, help="tools root whose gen.py republishes (frozen HEAD src)")
    ap.add_argument("--core-pin", type=Path, action="append", default=[],
                    help="regenerated core_pins/<name>.json to install (e.g. lep_pair_pins_777.json from the signed LEF)")
    ap.add_argument("--k-replan", type=Path, help="DH58-PROTO k_replan_delta.json: count-aligned K / sched_lat per port "
                    "(sidecar count_aligned.ports + ports[].added_cycles), checked against K_old / sched_lat_old")
    ap.add_argument("--tap-window", action="append", default=[], help="TYPE=PS: clock.tap_window.per_type_ps entry")
    ap.add_argument("--event", default="l48rf", help="wave_prepare.json event key")
    ap.add_argument("--types", help="republish only these (default: every eligible type whose plan record changed)")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import head_cland_stage_delta as CL
    old = json.loads((a.base / "source_plan.json").read_text())
    new = json.loads((a.rf / "source_plan.json").read_text())
    rec = json.loads((a.base / "wave_prepare.json").read_text())
    if a.out.exists():
        CL.writable(a.out)
        shutil.rmtree(a.out)
    shutil.copytree(a.base, a.out, symlinks=True)
    CL.writable(a.out)
    for f in a.out.glob("republish_*.log"):
        f.unlink()
    (a.out / "source_plan.json").write_text(json.dumps(new, indent=1) + "\n")
    core = []
    for f in a.core_pin:
        dst = a.out / "core_pins" / f.name
        if dst.is_symlink():
            dst.unlink()
        shutil.copy2(f, dst)
        core.append(dict(file=f"core_pins/{f.name}", sha256=digest(dst)))
    side = json.loads((a.base / "source_sidecar.json").read_text())
    regions = regrow_regions(side, old, new)
    kdone, kparts = {}, set()
    if a.k_replan:
        kd = json.loads(a.k_replan.read_text())["ports"]
        ca = side["count_aligned"]["ports"]
        rows = {r["port"]: r for r in side["ports"]}
        for pid, d in sorted(kd.items()):
            if "dK" not in d:
                continue
            c = ca[pid]
            if (c["K"], c["sched_lat"], c.get("tree")) != (d["K_old"], d["sched_lat_old"], False):
                raise SystemExit(f"{pid}: sidecar K/sched_lat {c['K']}/{c['sched_lat']} != k_replan old {d['K_old']}/{d['sched_lat_old']}")
            c["K"], c["sched_lat"] = d["K_new"], d["sched_lat_new"]
            r = rows[pid]
            if r.get("added_cycles") == d["sched_lat_old"]:
                r["added_cycles"] = d["sched_lat_new"]
            kdone[pid] = dict(src=d["src"], dst=d["dst"], dK=d["dK"], K=[d["K_old"], d["K_new"]],
                              sched_lat=[d["sched_lat_old"], d["sched_lat_new"]])
            kparts |= {d["src"], d["dst"]}
    tw = {}
    for kv in a.tap_window:
        tn, ps = kv.split("=")
        new["clock"]["tap_window"].setdefault("per_type_ps", {})[tn] = float(ps)
        tw[tn] = float(ps)
    if tw:
        (a.out / "source_plan.json").write_text(json.dumps(new, indent=1) + "\n")
    if regions or kdone:                               # untouched sidecar stays byte-identical (same sha / kit key)
        (a.out / "source_sidecar.json").write_text(json.dumps(side) + "\n")
    changed = sorted(t for t in new["partition_types"] if new["partition_types"][t] != old["partition_types"].get(t))
    ptype = {p["name"]: p["type"] for p in new["partitions"]}
    ktypes = {ptype[p] for p in kparts if p in ptype}
    types = a.types.split(",") if a.types else sorted(t for t in set(changed) | ktypes if t in rec["eligible_types"])
    rec[a.event] = dict(event=a.event, core_pins=core, base_prepared=str(a.base), base_prepared_plan_sha256=digest(a.base / "source_plan.json"),
                        rf_plan=str(a.rf / "source_plan.json"), changed_types=changed, republished=types,
                        k_replan=dict(file=str(a.k_replan), ports=kdone) if a.k_replan else None, tap_window_per_type_ps=tw,
                        held_changed=[t for t in changed if t in rec.get("held_types", [])], sidecar_regions=regions,
                        tool="tools/s81_head/head_rf_plan_delta.py + head_rf_prepare.py", by="DH58-RFPLAN")
    (a.out / "wave_prepare.json").write_text(json.dumps(rec, indent=1) + "\n")
    CL.republish(a.out, a.tools.resolve(), types, a.out / "source_sidecar.json")
    rec = json.loads((a.out / "wave_prepare.json").read_text())
    print(json.dumps(dict(out=str(a.out), plan=rec["prepared_plan_sha256"][:12], sidecar=rec["sidecar_sha256"][:12],
                          regions=[r["tag"] for r in regions], republished=types)))


if __name__ == "__main__":
    main()
