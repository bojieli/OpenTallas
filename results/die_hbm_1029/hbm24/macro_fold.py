#!/usr/bin/env python3
"""DIE-HBM-24 (COORD 19:09 HBM-CORES-KITS-22-PARK (3)): fold the 10.8-um-channel-compliant `_b` macro placements of
HBM-CORES-KITS-22 (intel1 hbm-cores-kits-22/k2/mp) into the plan macro sidecar core_macros.json.
Cores: hfd_ep_static (plan listed no macros, kit has 4 SRAMs), ot_hbm_host_cp_rxs (column gaps 8.664 -> 10.8),
ot_hbm_su_static_sfustore_hw (6.48 -> 10.8).  die_plan.json is unchanged (no outline / pin / cycle change): the
script fails closed unless every _b macro rect lies inside the plan hard-core outline of that module, and every pair
of macros whose projections overlap is either abutted (gap 0) or >= 10.8 um apart.  Names = 'u_fcore.' + kit key
(plan convention, see ep_b4r_mp.tcl).  usage: macro_fold.py PLAN_DIR MP_DIR OUT_DIR"""
import hashlib, json, os, shutil, sys
from pathlib import Path

CORES = {"hfd_ep_static": "hfd_ep_static_b", "ot_hbm_host_cp_rxs": "ot_hbm_host_cp_rxs_b",
         "ot_hbm_su_static_sfustore_hw": "ot_hbm_su_static_sfustore_hw_b"}
CH = 10.8


def gaps(rects):
    bad, mn = [], None
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            ra, rb = a["rect_um"], b["rect_um"]
            if min(ra[3], rb[3]) - max(ra[1], rb[1]) > 1e-6:      # y-overlap -> horizontal gap
                g = max(rb[0] - ra[2], ra[0] - rb[2])
            elif min(ra[2], rb[2]) - max(ra[0], rb[0]) > 1e-6:    # x-overlap -> vertical gap
                g = max(rb[1] - ra[3], ra[1] - rb[3])
            else:
                continue
            g = round(g, 4)
            if g < -1e-6:
                bad.append((a["name"], b["name"], g, "overlap"))
            elif 1e-6 < g < CH - 1e-6:
                bad.append((a["name"], b["name"], g, "channel<10.8"))
            if g > 1e-6:
                mn = g if mn is None else min(mn, g)
    return bad, mn


def main(plan_dir, mp_dir, out_dir):
    plan_dir, mp_dir, out_dir = Path(plan_dir), Path(mp_dir), Path(out_dir)
    P = json.loads((plan_dir / "die_plan.json").read_text())
    outl = {}
    for t in P["partition_types"].values():
        for h in t.get("hard_cores", []):
            if h["module"] in CORES:
                outl.setdefault(h["module"], set()).add(tuple(h["outline_um"]))
    raw = (plan_dir / "core_macros.json").read_bytes()
    CM = json.loads(raw)
    rep = dict(schema="opentallas.hbm.macro_fold.v1", source_core_macros_sha256=hashlib.sha256(raw).hexdigest(), cores={})
    for mod, fb in CORES.items():
        assert len(outl[mod]) == 1, (mod, outl[mod])
        W, H = next(iter(outl[mod]))
        B = json.loads((mp_dir / f"{fb}.json").read_text())
        est = json.loads((mp_dir / f"{fb}.est.json").read_text())["masters"]
        new = []
        for m in B["macro_placement"]:
            w, h = est[m["macro"]]["w"], est[m["macro"]]["h"]
            x, y = m["origin_um"]
            r = [round(x, 4), round(y, 4), round(x + w, 4), round(y + h, 4)]
            if not (r[0] >= -1e-6 and r[1] >= -1e-6 and r[2] <= W + 1e-6 and r[3] <= H + 1e-6):
                raise SystemExit(f"{mod}: {m['k']} rect {r} outside plan outline {W}x{H}")
            new.append(dict(name="u_fcore." + m["k"], master=m["macro"], rect_um=r, orient=m["orient"]))
        bad, mn = gaps(new)
        if bad:
            raise SystemExit(f"{mod}: {bad[:4]}")
        old = CM["cores"][mod]
        old_bad, old_mn = gaps(old.get("macros", []))
        if old.get("macros"):
            assert sorted(x["name"] for x in old["macros"]) == sorted(x["name"] for x in new), mod
        rep["cores"][mod] = dict(plan_outline_um=[W, H], kit_outline_um=B["outline_um"], macros=len(new),
                                 old_macros=len(old.get("macros", [])), old_min_channel_um=old_mn,
                                 old_violations=len(old_bad), new_min_channel_um=mn, source=str(mp_dir / f"{fb}.json"))
        old["macros"] = new
        old["channel_rule_um"] = CH
        old["note"] = (old.get("note", "") + f" | DIE-HBM-24 macro_fold: HBM-CORES-KITS-22 {fb} placement "
                       f"(min channel {mn} um >= 10.8; was {old_mn})").strip(" |")
    CM["note"] = CM.get("note", "") + " | DIE-HBM-24 macro_fold (10.8-um macro channel rule: ep/cp_rxs/sfustore)"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for f in os.listdir(plan_dir):
        if f in ("core_macros.json", "macro_fold_report.json") or f.startswith("g0"):
            continue
        s = plan_dir / f
        (shutil.copytree(s, out_dir / f, copy_function=os.link) if s.is_dir() else os.link(s, out_dir / f))
    txt = json.dumps(CM, indent=1)
    (out_dir / "core_macros.json").write_text(txt)
    rep["core_macros_sha256"] = hashlib.sha256(txt.encode()).hexdigest()
    rep["die_plan_sha256"] = hashlib.sha256((out_dir / "die_plan.json").read_bytes()).hexdigest()
    (out_dir / "macro_fold_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: {x: v[x] for x in ("macros", "old_macros", "old_min_channel_um", "old_violations",
                                              "new_min_channel_um")} for k, v in rep["cores"].items()}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
