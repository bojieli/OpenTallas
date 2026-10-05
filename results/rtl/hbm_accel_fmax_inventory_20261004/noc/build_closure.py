#!/usr/bin/env python3
"""Build closure.json of the noc family (HBM accelerator 1.2 GHz closure, 2026-10-04) from the committed small copies
of each route's physical.json / corner_sta.json (routes/<label>/), the screens (screens/<label>.json) and the bench
records in this directory.  Row schema: the program brief's closure.json row.

    python3 build_closure.py            # writes closure.json beside this file
"""
import json
from pathlib import Path

H = Path(__file__).resolve().parent
REL = "results/rtl/hbm_accel_fmax_inventory_20261004/noc"


def cs(label):
    p = H / "routes" / label / "corner_sta.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    ph = json.loads((H / "routes" / label / "physical.json").read_text()) if (H / "routes" / label / "physical.json").exists() else {}
    area = None
    s = json.dumps(ph)
    import re
    m = re.search(r'"cell_area_um2": ([0-9.]+)', s)
    if m:
        area = float(m.group(1))
    f = lambda k, x: d[k].get(x)  # noqa: E731
    return dict(route_record=f"{REL}/routes/{label}/", period_ns=0.833,
                ss_r2r_ps=f("setup_ss", "worst_reg_to_reg_slack_ps"), ss_worst_ps=f("setup_ss", "worst_slack_ps"),
                ss_output_port_ps=f("setup_ss", "worst_output_port_slack_ps"),
                ss_input_to_reg_ps=f("setup_ss", "worst_input_to_reg_slack_ps"),
                ff_hold_ps=f("hold_ff", "worst_slack_ps"), closes_signoff=d.get("closes_signoff"),
                cell_area_um2=area)


def main():
    spec = json.loads((H / "closure_spec.json").read_text())
    rows = []
    for r in spec["rows"]:
        r = dict(r)
        if "revisions" in r:
            r["revisions"] = [{**v, **(cs(v["route_label"]) or {})} for v in r["revisions"]]
        for k in ("before", "after"):
            if isinstance(r.get(k), dict) and r[k].get("route_label"):
                got = cs(r[k]["route_label"])
                if got:
                    r[k] = {**r[k], **got}
        rows.append(r)
    out = dict(schema="opentallas.hbm_fmax.closure.v1", family="noc", date="2026-10-04",
               signoff="0.833 ns, SS setup 60 ps, FF hold 25 ps (tools/w18/corner_sta.py)",
               collective_term=spec.get("collective_term"), rows=rows)
    (H / "closure.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(rows)} rows")


if __name__ == "__main__":
    main()
