#!/usr/bin/env python3
"""Attention half (hfd_attn_half_lo / hfd_attn_half_hi) as ONE hardened wires-only cluster, built once and replicated
32x each in the published die contract (results/arch/hier_contract_1011/r25gq.json: at_*_lo / at_*_hi slots,
1,778.52 x 1,263.6 / 1,778.52 x 689.04, hardened_cluster, ck entry N face M7, pins unassigned).

Source of truth = the native component Codex built and gated (results/arch/hbm_native_1013/attention/{lo,hi}.component.json,
a95a4adfc: 89 / 54 real CLOSED hard children, exact placement, wires-only Yosys netlist {lo,hi}.v, cut <= 0.374 / 0.301).
This tool writes, per half:
  * view wrappers physical/hbm_attn_half_cluster/views/<master>/ (verbatim copies of the closed child LEF + TT/FF/SS libs +
    abstract/insertion; ref_tile needs <view>/<basename>.lef and four of the closed views live in dirs named 'view');
  * a ref_tile cluster spec tools/ref_tile/specs_hbm_attn_half/hattn_half_<h>_ref.json with every child at its component
    xy / orientation (at_exact), the slot outline, and a pin plan DERIVED from the boundary bindings: each parent port goes
    to the face nearest the child pins it binds (majority of bits), its range = the projected span of those child pins,
    widened symmetrically to >= bits x 2 tracks.  The die lead has not published a pin file for these masters; this plan
    follows the children so no boundary bit travels further than its own child's distance to the face.
Nothing here alters a closed child or its source.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "results/arch/hbm_native_1013/attention"
VIEWS = "physical/hbm_attn_half_cluster/views"
SPECS = ROOT / "tools/ref_tile/specs_hbm_attn_half"
PITCH = {"N": 0.096, "S": 0.096, "E": 0.096, "W": 0.096}   # 2 tracks of M4 (W/E) / M5 (N/S), 0.048 each
EDGE_KEEP = 4.32
# the retained two-level lockstep gate (results/rtl/hbm_attn_twolevel_lockh_20261012): split halves vs one-piece tile
LOCKH_G = "-GCG=1 -GLNK=3 -GLNC=1 -GLNR=2 -GLPMID=3 -GLNFR=4 -GLNXP=3 -GXPX=2 -GLLDKR=16"


def lef_pins(text: str) -> dict:
    out = {}
    for name, body in re.findall(r"^\s*PIN (\S+)\n(.*?)^\s*END \1\s*$", text, re.S | re.M):
        m = re.search(r"RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", body)
        if m:
            x0, y0, x1, y1 = map(float, m.groups())
            out[name] = ((x0 + x1) / 2, (y0 + y1) / 2)
    return out


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def wrap_view(child: dict) -> str:
    master = child["logical_module"]
    src = ROOT / Path(child["view_lef"]).parent
    dst = ROOT / VIEWS / master
    dst.mkdir(parents=True, exist_ok=True)
    names = [f"{master}.lef"] + [f"{master}_{c}.lib" for c in ("tt", "ff", "ss")]
    for extra in ("abstract.json", "insertion.json", "child_lint.json"):
        if (src / extra).exists():
            names.append(extra)
    for n in names:
        shutil.copyfile(src / n, dst / n)
    # the LEF (geometry / pins) must be the one the component was gated with; the libs may be the later re-export of the
    # SAME closed run (184cb9f5e: libraries re-exported at the routed verdict's SDC sequence) -- recorded, not refused
    lib_reexport = {}
    for n in names[:4]:
        want = child["sha256"].get(n)
        if want and sha(dst / n) != want:
            if n.endswith(".lef"):
                raise SystemExit(f"{master}: {n} differs from the component's recorded sha256")
            lib_reexport[n] = {"component": want, "now": sha(dst / n)}
    (dst / "WRAPPED_FROM.json").write_text(json.dumps(
        {"source_view": str(src.relative_to(ROOT)), "files": {n: sha(dst / n) for n in names},
         "why": "verbatim copy so <view>/<basename>.lef exists for ref_tile; the closed child is unchanged",
         "lib_reexport_since_component": lib_reexport}, indent=1) + "\n")
    return f"{VIEWS}/{master}"


def place_xy(child: dict, px: float, py: float) -> tuple[float, float]:
    x0, y0 = child["xy_um"]
    w, h = child["w_um"], child["h_um"]
    o = child["orientation"]
    if o == "R0":
        return x0 + px, y0 + py
    if o == "MY":
        return x0 + w - px, y0 + py
    if o == "MX":
        return x0 + px, y0 + h - py
    if o == "R180":
        return x0 + w - px, y0 + h - py
    raise SystemExit(f"orientation {o} not handled")


def build(half: str) -> dict:
    comp = json.loads((COMP / f"{half}.component.json").read_text())
    W, H = comp["outline_um"]
    by_inst = {c["instance"]: c for c in comp["children"]}
    pins_of = {}
    children = []
    for c in comp["children"]:
        view = wrap_view(c)
        m = c["logical_module"]
        if m not in pins_of:
            pins_of[m] = lef_pins((ROOT / view / f"{m}.lef").read_text())
        children.append({"view": view, "inst": c["instance"], "at": list(c["xy_um"]), "orient": c["orientation"],
                         "at_exact": True})
    # per parent port: projected face coordinates of every bound child pin
    proj = collections.defaultdict(list)
    for b in comp["boundary_binding"]:
        c = by_inst[b["child_instance"]]
        lp = pins_of[c["logical_module"]]
        for k in range(b["width"]):
            nm = f"{b['child_port']}[{b['child_lsb'] + k}]"
            if nm not in lp:
                nm = b["child_port"] if b["width"] == 1 and b["child_port"] in lp else None
            if nm is None:
                raise SystemExit(f"{half}: {c['logical_module']} has no pin {b['child_port']}[{b['child_lsb'] + k}]")
            x, y = place_xy(c, *lp[nm])
            d = {"W": x, "E": W - x, "S": y, "N": H - y}
            f = min(d, key=d.get)
            proj[b["parent_port"]].append((f, y if f in "WE" else x, d[f]))
    faces = {"N": [], "S": [], "E": [], "W": []}
    ranges, audit = {}, {}
    for port, info in comp["boundary_ports"].items():
        if info["role"] == "clock":
            continue
        pts = proj[port]
        face = collections.Counter(f for f, _, _ in pts).most_common(1)[0][0]
        span = [p for f, p, _ in pts if f == face] or [p for _, p, _ in pts]
        lo_, hi_ = min(span), max(span)
        need = 1.3 * info["width"] * PITCH[face]   # 30 % slack over 2-track packing
        if hi_ - lo_ < need:
            mid = (lo_ + hi_) / 2
            lo_, hi_ = mid - need / 2, mid + need / 2
        lim = H if face in "WE" else W
        if lo_ < EDGE_KEEP:
            hi_ += EDGE_KEEP - lo_
            lo_ = EDGE_KEEP
        if hi_ > lim - EDGE_KEEP:
            lo_ -= hi_ - (lim - EDGE_KEEP)
            hi_ = lim - EDGE_KEEP
        faces[face].append(port)
        ranges[port] = [round(max(EDGE_KEEP, lo_), 3), round(hi_, 3)]
        audit[port] = {"face": face, "bits": info["width"], "range": ranges[port],
                       "bits_on_other_faces": sum(1 for f, _, _ in pts if f != face),
                       "max_child_pin_to_face_um": round(max(dd for _, _, dd in pts), 2)}
    # the die H-tree leaf enters at the N face (slot clock_entry ck N M7)
    faces["N"].append("ck")
    ranges["ck"] = [round(W / 2 - 0.144, 3), round(W / 2 + 0.144, 3)]
    # overlap / capacity per face
    load = {}
    for f, ports in faces.items():
        lim = H if f in "WE" else W
        bits = sum(comp["boundary_ports"][p]["width"] for p in ports)
        load[f] = {"bits": bits, "face_um": lim, "bits_per_um": round(bits / lim, 2)}
    return {"comp": comp, "children": children, "faces": faces, "ranges": ranges, "audit": audit, "load": load,
            "W": W, "H": H}


def spec_for(half: str, b: dict, commit_note: str) -> dict:
    comp = b["comp"]
    name = f"hattn_half_{half}_ref"
    return {
        "name": name, "top": comp["logical_module"], "kind": "cluster",
        "sources": [f"results/arch/hbm_native_1013/attention/{half}.v"],
        "clock_port": "ck", "reset_ports": [],
        "outline": {"w": b["W"], "h": b["H"]},
        "child_lattice_um": 0.432,
        "children": b["children"],
        "pins": {f: p for f, p in b["faces"].items() if p},
        "pin_ranges": b["ranges"],
        "route": {"pd": 0.3, "threads": 16, "peak_ram_gb": 96, "pin_h": "M4"},
        "recipe": 2,
        "structural_change": (
            "the opaque half masters (hfd_attn_half_lo/hi: parent spine insertion 877-2577 ps, hi soft guard/merge -8.35 ns "
            "pre-route) are replaced by the native wires-only half: the CLOSED leaves (sn544/ew544/sn136/ew136 banks, m6h1q "
            "quads, lo_root / ks_entry / hi_merge glue) at the gated component placement a95a4adfc, no register or logic of "
            "the parent's own; every seam is child flop -> wire -> child flop (component max stage reach 495.0 / 473.2 um, "
            "cut 0.374 / 0.301)."),
        "slot_change_request": (
            "none to outline/faces: r25gq v12 slot at_*_%s %s x %s hardened_cluster, ck entry N M7; pins were empty in the "
            "contract: plan derived from the child boundary bindings (posted to el1011-hbmdie.log)" % (half, b["W"], b["H"])),
        "why_floorplan": "outline = the contract slot = the native component outline; children at_exact from the component",
        "job": {
            "owner": "Claude:hbm-group-B-1014", "branch": "claude/hbm-attn-half-cluster-1014", "tag": "nat1",
            "purpose": (f"native attention half {half}: harden once (64 die instances = 32 lo + 32 hi) from CLOSED children; "
                        "measures the real half seams/clock/route in place of the cancelled/refused hfd_attn_half_* routes"),
            "benches": [
                {"name": "attn_lockh_pos", "cmd": "bash physical/hbm_attn_tile_r/half/run_lockh.sh {RUN}/lockh_pos pos " + LOCKH_G,
                 "expect": "pass", "threads": 8, "peak_ram_gb": 64, "needs": ["verilator"]},
                {"name": "attn_lockh_neg", "cmd": "bash physical/hbm_attn_tile_r/half/run_lockh.sh {RUN}/lockh_neg neg " + LOCKH_G,
                 "expect": "fail", "threads": 8, "peak_ram_gb": 64, "needs": ["verilator"]},
            ],
            "notes": commit_note,
        },
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--half", choices=("lo", "hi", "both"), default="both")
    a = ap.parse_args()
    SPECS.mkdir(parents=True, exist_ok=True)
    rep = {}
    for h in (("lo", "hi") if a.half == "both" else (a.half,)):
        b = build(h)
        s = spec_for(h, b, "generated by tools/hbm_attn_half_cluster_spec.py")
        (SPECS / f"hattn_half_{h}_ref.json").write_text(json.dumps(s, indent=1) + "\n")
        rep[h] = {"faces": b["faces"], "audit": b["audit"], "load": b["load"]}
    out = ROOT / "results/arch/hbm_native_1013/attention/half_cluster_pin_plan.json"
    out.write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({h: {"load": r["load"], "audit": r["audit"]} for h, r in rep.items()}, indent=1))


if __name__ == "__main__":
    main()
