#!/usr/bin/env python3
"""Compose the native W128 HC width contract into an HBM plan candidate.

The source is the actual native B2 bit census, including fault and control bits;
the old nine-bundle arithmetic-only estimate is insufficient. This changes only
HC lanes, their endpoint buses and traversed FT widths. Wider FT allocations are
invalidated for the geometry composer to regenerate. No latency is invented.
The output is a re-plan input, never a routed or signed-off plan.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def select_hc(report):
    rows = []
    for r in report["lane_capacity"]:
        ports = r.get("source_ports", [])
        if not ports or not all(p.startswith(("hcb_", "hc_")) for p in ports):
            continue
        if r.get("coarse_instances") or r["status"] == "SPANS_PARTITIONS":
            raise ValueError(f"HC source is not partition-resolved: {r['src']}->{r['dst']}")
        if r["need"] > r["width"]:
            if len(r["lanes"]) != 1:
                raise ValueError("HC bundle needs an explicit split-lane allocation")
            rows.append(copy.deepcopy(r))
    if not rows:
        raise ValueError("no native HC width corrections found")
    return rows


def apply(raw, report):
    out = copy.deepcopy(raw)
    rows = select_hc(report)
    ports = {p["id"]: p for p in out["ports"]}
    lanes = {p["id"]: p for p in out["lanes"]}
    parts = {p["name"]: p for p in out["partitions"]}
    requests, changed = {}, []
    for r in rows:
        ln = lanes[r["lanes"][0]]
        first, last = ports[ln["ports"][0]], ports[ln["ports"][-1]]
        if (first["src"]["part"], last["dst"]["part"]) != (r["src"], r["dst"]):
            raise ValueError(f"native path endpoints changed for {ln['id']}")
        for pid in ln["ports"]:
            p = ports[pid]
            if p["width"] not in (r["width"], r["need"]):
                raise ValueError(f"unexpected prior width on {pid}: {p['width']}")
            p["width"] = r["need"]
            for side in ("src", "dst"):
                e = p[side]
                key = (parts[e["part"]]["type"], e["bus"])
                if key in requests and requests[key] != r["need"]:
                    raise ValueError(f"replicated HC bus has inconsistent widths: {key}")
                requests[key] = r["need"]
    invalidated = []
    for tn, t in out["partition_types"].items():
        for b in t.get("buses", []):
            key = (tn, b["name"])
            if key in requests:
                before = b["width"]
                b["width"] = requests.pop(key)
                changed.append(dict(type=tn, bus=b["name"], before=before, after=b["width"]))
        for s in t.get("ft_slots", []):
            ks = [(tn, s["name"] + suffix) for suffix in ("_i", "_o")]
            ws = {requests[k] for k in ks if k in requests}
            if not ws:
                continue
            if len(ws) != 1:
                raise ValueError(f"in/out width mismatch on {tn}.{s['name']}")
            width = ws.pop()
            before = s["width"]
            s["width"] = width
            for k in ks:
                requests.pop(k, None)
            # Old per-bit locations have the old cardinality. Retaining them
            # would silently turn half the new native bundle into unplaced bits.
            if width != before:
                for key in ("bit_sites_um", "bit_site_cell_um"):
                    s.pop(key, None)
                invalidated.append(dict(type=tn, slot=s["name"], before=before,
                                        after=width, stations=s["stations"]))
    if requests:
        raise ValueError(f"missing plan HC bus/slot declarations: {sorted(requests)}")
    summary = dict(schema="opentallas.hbm.native_hc128_delta.v1", qualification="REPLAN_INPUT",
                   rows=rows, changed_buses=changed, invalidated_ft_allocations=invalidated,
                   added_data_cycles=0, latency_table_unchanged=out.get("latency") == raw.get("latency"),
                   pending=["repack_wider_face_windows", "regenerate_wider_perbit_stations",
                            "install_exact_W128_parent_cut_maps", "G0C_geometry_GRT_clock_token"])
    return out, summary


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    p.add_argument("--native-report", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    raw = json.loads(a.plan.read_text())
    native = json.loads(a.native_report.read_text())
    candidate, summary = apply(raw, native)
    summary["plan_sha256"] = hashlib.sha256(a.plan.read_bytes()).hexdigest()
    summary["native_report_sha256"] = hashlib.sha256(a.native_report.read_bytes()).hexdigest()
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "die_plan.json").write_text(json.dumps(candidate, indent=1) + "\n")
    (a.out / "hc128_delta.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps({k: len(summary[k]) for k in ("rows", "changed_buses", "invalidated_ft_allocations")}))


if __name__ == "__main__":
    main()
