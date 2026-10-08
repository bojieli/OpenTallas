#!/usr/bin/env python3
"""MULTI-VT: one row per block from dispatch_resta collect JSON(s): setup WS RVT/LVT/LVT+SLVT (fresh-session verify),
FF hold, cell mix, TT leakage/total power ratio, and the owner policy verdict (2026-10-07: RVT default; LVT allowed when
<= LVT_CAP % of cells closes setup >= ACCEPT ps; SLVT only as a named exception).

    summarize.py all.json [more.json ...] [--cap 2.0] [--accept 0] [--json out.json]
"""
import argparse
import json


def rows(d, cap, accept):
    out = []
    for n, r in d.items():
        x = r.get("result")
        if not x:
            out.append(dict(job=n, status="pending"))
            continue
        s, v, f, p = x["ss_setup"], x.get("ss_verify", {}), x.get("ff_hold", {}), x.get("tt_power") or {}
        tot = sum(s["RVT"]["vt"].values()) or 1
        lv, sl = s["LVT"]["vt"], s["LVT_SLVT"]["vt"]
        ws = lambda k: (v.get(k) or s.get(k) or {}).get("ws_ps")  # noqa: E731
        lr = lambda k: (p[k]["leakage_w"] / p["RVT"]["leakage_w"]) if p.get(k) and p["RVT"]["leakage_w"] else None  # noqa: E731
        tr = lambda k: (100 * (p[k]["total_w"] / p["RVT"]["total_w"] - 1)) if p.get(k) and p["RVT"]["total_w"] else None  # noqa: E731
        lpct = 100 * lv["L"] / tot
        row = dict(job=n, corner=x.get("setup_corner", "ss"), link_budget=bool(x.get("extra_setup_sdc")),
                   cells=tot, setup_rvt=s["RVT"]["ws_ps"], setup_lvt=ws("LVT"), setup_lvt_slvt=ws("LVT_SLVT"),
                   ff_rvt=(f.get("RVT") or {}).get("ws_ps"), ff_lvt=(f.get("LVT") or {}).get("ws_ps"),
                   ff_lvt_slvt=(f.get("LVT_SLVT") or {}).get("ws_ps"),
                   lvt_cells=lv["L"], lvt_pct=round(lpct, 3), lvt_slvt_cells=sl["L"] + sl["SL"],
                   lvt_slvt_pct=round(100 * (sl["L"] + sl["SL"]) / tot, 3),
                   leak_w_rvt=(p.get("RVT") or {}).get("leakage_w"), leak_x_lvt=lr("LVT"), leak_x_lvt_slvt=lr("LVT_SLVT"),
                   total_pct_lvt=tr("LVT"), total_pct_lvt_slvt=tr("LVT_SLVT"))
        if row["setup_rvt"] is not None and row["setup_rvt"] >= accept:
            row["policy"] = "RVT already closes setup"
        elif row["setup_lvt"] is not None and row["setup_lvt"] >= accept and lpct <= cap:
            row["policy"] = f"LVT <= {cap}% closes -> queue -tt-lvt"
        elif row["setup_lvt"] is not None and row["setup_lvt"] >= accept:
            row["policy"] = f"LVT closes but needs {lpct:.1f}% > cap -> structural"
        elif row["setup_lvt_slvt"] is not None and row["setup_lvt_slvt"] >= accept:
            row["policy"] = "only LVT+SLVT closes -> named-exception candidate / structural"
        else:
            row["policy"] = "Vt does not close -> structural"
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--cap", type=float, default=2.0)
    ap.add_argument("--accept", type=float, default=0.0)
    ap.add_argument("--json")
    a = ap.parse_args()
    allr = []
    for f in a.inputs:
        allr += rows(json.load(open(f)), a.cap, a.accept)
    fmt = lambda v, w=8, d=1: (f"{v:{w}.{d}f}" if isinstance(v, (int, float)) else f"{'-':>{w}}")  # noqa: E731
    for r in allr:
        if r.get("status") == "pending":
            print(f"{r['job'][:44]:44s} pending")
            continue
        print(f"{r['job'][:44]:44s} {r['corner']}{'+lb' if r['link_budget'] else '   '} setup {fmt(r['setup_rvt'])} {fmt(r['setup_lvt'])} "
              f"{fmt(r['setup_lvt_slvt'])} | FF {fmt(r['ff_rvt'],7)} {fmt(r['ff_lvt'],7)} | L% {fmt(r['lvt_pct'],6,2)} "
              f"L+SL% {fmt(r['lvt_slvt_pct'],6,2)} | leak x{fmt(r['leak_x_lvt'],5,2)} x{fmt(r['leak_x_lvt_slvt'],5,2)} "
              f"tot% {fmt(r['total_pct_lvt'],5,2)} | {r['policy']}")
    if a.json:
        json.dump(dict(cap_pct=a.cap, accept_ps=a.accept, rows=allr), open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
