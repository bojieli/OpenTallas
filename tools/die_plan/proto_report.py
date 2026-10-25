#!/usr/bin/env python3
"""PROTO report: render every collected probe (proto_render.py) into OUT/<die>/<type>.png, write OUT/<die>.json (the
proto.json rows) and print one markdown table per die for lanes/PROTO.md.

    proto_report.py RESROOT OUT [--dies hbm_b2m,kv,qc,head,s81] [--plans-root physical/die_plan]
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import proto_render  # noqa: E402

PLANS = {"hbm_b2m": "hbm_arch/B2m", "kv": "qwen_kvsys", "qc": "qwen_compute", "head": "s81_head", "s81": "s81"}
KEEP = ("die", "type", "instance", "outline_um", "pins", "flops", "leaf_blockages", "core_blockages", "route_layers",
        "adjust", "total_overflow", "hot_gcells", "hot_slots", "hot_bbox_um", "layers", "wirelength_um",
        "pin_access_no_ap", "sta", "repair_buffers", "drv", "displacement_um", "peak_gb", "wall", "exit", "classify")


from proto_geometry import hop_stats  # noqa: E402


def fmt(v, nd=1):
    return "-" if v is None else (f"{v:.{nd}f}" if isinstance(v, float) else str(v))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("res")
    ap.add_argument("out")
    ap.add_argument("--dies", default="hbm_b2m,kv,qc,head,s81")
    ap.add_argument("--plans-root", default=str(HERE.parent.parent / "physical" / "die_plan"))
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--src", help="generated probe root (io.tcl + probe.tcl per part) for the ft hop check")
    a = ap.parse_args(argv)
    out = Path(a.out)
    for die in a.dies.split(","):
        rd = Path(a.res) / die
        if not rd.is_dir():
            continue
        plan = json.loads((Path(a.plans_root) / PLANS[die] / "die_plan.json").read_text())
        ninst = Counter(p["type"] for p in plan["partitions"])
        rows = {}
        for d in sorted(rd.glob("part_*")):
            pj = d / "proto.json"
            if not pj.exists():
                continue
            r = json.loads(pj.read_text())
            r = {k: r.get(k) for k in KEEP}
            r["instances"] = ninst.get(r["type"], 0)
            hs = hop_stats(Path(a.src) / die / d.name) if a.src else None
            if hs:
                r["ft_hops"] = hs
                if hs["st_in_core"]:
                    r["classify"] = dict(r["classify"], cls="STRUCTURAL")
                    r["classify"]["why"] = (f"{hs['st_in_core']} planned ft station sites inside a hard core "
                                            f"({', '.join(f'{k}:{v}' for k, v in hs['st_in_core_slots'].items())}; "
                                            "they pile up there -> the local overflow); " + r["classify"]["why"])
                if hs["over_reach"] and r["classify"]["cls"] in ("CLEAN", "HOTSPOT"):
                    r["classify"] = dict(r["classify"], cls="STRUCTURAL")
                if hs["over_reach"]:
                    worst = ", ".join(f"{k} {v:.0f}" for k, v in list(hs["over_reach"].items())[:3])
                    r["classify"]["why"] = (f"{len(hs['over_reach'])} ft slots with a station hop > 405 um "
                                            f"(decision 12; worst {worst} um); " + r["classify"]["why"])
            png = out / die / f"{r['type']}.png"
            if not a.no_render and r["classify"]["cls"] != "NOT RUN":
                png.parent.mkdir(parents=True, exist_ok=True)
                proto_render.render(d, png)
                r["render"] = str(png)
            rows[r["type"]] = r
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{die}.json").write_text(json.dumps(rows, indent=1) + "\n")
        cnt = Counter(r["classify"]["cls"] for r in rows.values())
        print(f"\n### {die} ({PLANS[die]}): " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())))
        print("| type | n | outline um | class | GRT ov (gcells) / hot slots @ bbox | TT setup WNS (viol) | FF hold WNS (viol) "
              "| max ft hop um | peak GB | why |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        order = {"STRUCTURAL": 0, "HOTSPOT": 1, "NOT RUN": 2, "CLEAN": 3}
        for tn, r in sorted(rows.items(), key=lambda kv: (order.get(kv[1]["classify"]["cls"], 9), kv[0])):
            s = r.get("sta") or {}
            w, h = r["outline_um"]
            hs = ""
            if r.get("hot_slots"):
                hs = " " + ",".join(f"{k}:{v}" for k, v in r["hot_slots"][:3]) + f" @{r.get('hot_bbox_um')}"
            print(f"| {tn} | {r['instances']} | {w:.0f}x{h:.0f} | {r['classify']['cls']} | "
                  f"{fmt(r.get('total_overflow'))} ({fmt(r.get('hot_gcells'))}){hs} | "
                  f"{fmt(s.get('tt_setup_wns'))} ({fmt(s.get('tt_setup_viol'))}) | "
                  f"{fmt(s.get('ff_hold_wns'))} ({fmt(s.get('ff_hold_viol'))}) | "
                  f"{fmt((r.get('ft_hops') or {}).get('max_hop_um'), 0)} | {fmt(r.get('peak_gb'))} | "
                  f"{r['classify']['why']} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
