#!/usr/bin/env python3
"""CLOCK-KV-R25 (KV-CORES-PV blocker): die-owned 12.2a1 feed-through ports for the in-core clock islands of hm_r24.

    kv_island_ports.py PLAN_IN PLAN_OUT --groups groups.json [--suffix _r25] [--report R.json]

hm_r24 clock.mesh.core_islands[module] (core frame = the pins_file frame of every instance, identical on all, canon_pushdown.py)
holds the bodies of the die clock cells pushed down into the core: a mesh driver group (2 x BUFx24 in parallel, die
tree leaf -> continuous mesh ck_mesh) or a tree node (1 x BUFx24, parent leg -> child legs).  Each GROUP (abutting
rects on one row) is ONE ft arc of the core:

    ft_ck_i_<k>  (in, from the die M9->M5 stack)  ->  island cell(s)  ->  ft_ck_o_<k>  (out, M5->M9 stack to the die net)

k = group index in the core frame ordered by (y, x).  Names: scalar identifiers accepted by ft_ports.declaration
(IDENT), classified "clock" by ft_ports._kind (`_ck_`), interior by pin_audit.INTERIOR (`ft_(ck|rst)_[io]_N`).
Pins (12.2a1 / 12.1a, KV core M5 ceiling): layer M5 (top core layer of these cores; the die stack drops M9->M5 onto the
pin, VIA89/78/67/56 as the 12.8a centre entry), interior, x on the M5 track lattice (0.024 + k 0.048) and clear of the
kit M5 PG stripe pair (offset 2.064, 2 x 0.12 + 0.072 gap, pitch 4.32) by >= 0.25 um, y = island row centre;
in-port = first legal track >= 1.08 um left of the group, out-port = first legal track >= 1.08 um right of it (the two
stacks >= 2.16 um + group width apart).  Identical for every instance of the module by construction (one pin view per
pins_file, the islands identical in that frame).  Every pins_file used by the module gets the SAME ports at the same
coordinates (the islands are identical in the pins_file frame, not in a mirrored GDS frame).  Original pin files are not
touched: the new views are written as <stem><suffix>.json next to them and PLAN_OUT points at them.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path

M5_PITCH, M5_OFF = 0.048, 0.024
PG_OFF, PG_W, PG_GAP, PG_PITCH = 2.064, 0.12, 0.072, 4.32
PG_CLEAR = 0.25
STACK_SEP = 1.08
ROW = 0.27


def sha(b):
    return hashlib.sha256(b).hexdigest()


def pg_ok(x):
    """x clear of the M5 PG stripe pair [2.064, 2.064 + 0.312] (mod 4.32) by PG_CLEAR (pin half width 0.024 included)."""
    lo, hi = PG_OFF - PG_CLEAR - 0.024, PG_OFF + 2 * PG_W + PG_GAP + PG_CLEAR + 0.024
    m = x % PG_PITCH
    return not (lo <= m <= hi or lo <= m + PG_PITCH <= hi or lo <= m - PG_PITCH <= hi)


def track(x, direction):
    k = math.ceil((x - M5_OFF) / M5_PITCH - 1e-9) if direction > 0 else math.floor((x - M5_OFF) / M5_PITCH + 1e-9)
    while True:
        t = round(M5_OFF + k * M5_PITCH, 4)
        if pg_ok(t):
            return t
        k += direction


def groups_of(rects):
    rs = sorted((tuple(r) for r in rects), key=lambda r: (r[1], r[0]))
    out = []
    for r in rs:
        if out and abs(out[-1][1] - r[1]) < 1e-6 and abs(out[-1][2] - r[0]) < 1e-6:
            out[-1] = (out[-1][0], out[-1][1], r[2], max(out[-1][3], r[3]))
            out[-1 + 0] = out[-1]
            continue
        out.append(r)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("--groups", required=True)
    ap.add_argument("--suffix", default="_r25")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    pin = Path(a.plan_in)
    raw = json.loads(pin.read_text())
    G = json.loads(Path(a.groups).read_text())
    ci = raw["clock"]["mesh"]["core_islands"]
    rep = dict(tool="tools/die_plan/kv_r25/kv_island_ports.py", plan_in=str(pin), plan_in_sha256=sha(pin.read_bytes()),
               modules={}, files={})
    newname = {}
    for mod, isl in sorted(ci.items()):
        grs = groups_of(isl["rects_um"])
        roles = sorted(G[mod]["groups"], key=lambda g: (g["bbox"][1], g["bbox"][0]))
        if len(roles) != len(grs) or any(max(abs(p - q) for p, q in zip(g["bbox"], r)) > 1e-3 for g, r in zip(roles, grs)):
            raise SystemExit(f"{mod}: core_islands groups {grs} != mesh groups {[g['bbox'] for g in roles]}")
        ports = []
        for k, (r, g) in enumerate(zip(grs, roles)):
            y = round(r[1] + ROW / 2, 4)
            xi, xo = track(r[0] - STACK_SEP, -1), track(r[2] + STACK_SEP, +1)
            ports.append(dict(k=k, role=g["role"], cells=g["cells"], masters=g["masters"], rect_um=list(r),
                              arc=[f"ft_ck_i_{k}", f"ft_ck_o_{k}"],
                              pins=[dict(name=f"ft_ck_i_{k}", layer="M5", x=xi, y=y),
                                    dict(name=f"ft_ck_o_{k}", layer="M5", x=xo, y=y)]))
        files = sorted({hc["pins_file"] for t in raw["partition_types"].values() for hc in t.get("hard_cores", []) or []
                        if hc["module"] == mod})
        rep["modules"][mod] = dict(instances=isl["instances"], groups=len(grs), ports=ports, pins_files=files)
        for f in files:
            src = pin.parent / f
            d = json.loads(src.read_text())
            w, h = (float(v) for v in d["frame"].split("outline ")[1].split(" x "))
            names = {p["name"] for p in d["pins"]}
            m5 = [(p["x"], p["y"]) for p in d["pins"] if p["layer"] == "M5"]
            new = copy.deepcopy(d)
            for P_ in ports:
                for q in P_["pins"]:
                    if q["name"] in names:
                        raise SystemExit(f"{f}: {q['name']} already present")
                    if not (0.5 < q["x"] < w - 0.5 and 0.5 < q["y"] < h - 0.5):
                        raise SystemExit(f"{f}: {q['name']} not interior")
                    near = [p for p in m5 if abs(p[0] - q["x"]) < 2 * M5_PITCH - 1e-6 and abs(p[1] - q["y"]) < 1.0]
                    if near:
                        raise SystemExit(f"{f}: {q['name']} within 2 M5 tracks of plan pins {near[:3]}")
                    new["pins"].append(dict(q))
            new["source"] = d["source"] + (" | CLOCK-KV-R25 10-27: 12.2a1 in-core clock island ft ports ft_ck_i_<k>/ft_ck_o_<k> "
                                           "(M5 interior, die M9->M5 stacks) for hm_r24 clock.mesh.core_islands")
            new["island_ft"] = dict(rule="METHODOLOGY 12.2a1 pushdown: die-owned feed-through, no core logic on these ports; "
                                         "fixed dont_touch cells in the core netlist at rect_um (core frame = this file's frame)",
                                    plan_core_islands_of="hm_r24 53cc76e3 clock.mesh.core_islands." + mod,
                                    arcs=[dict(source=P_["arc"][0], sink=P_["arc"][1], kind="clock", role=P_["role"],
                                               cells=P_["cells"], master=P_["masters"][0], rect_um=P_["rect_um"],
                                               via_stack=["VIA89", "VIA78", "VIA67", "VIA56"],
                                               net=("die tree leaf -> continuous mesh ck_mesh" if P_["role"] == "mesh_driver"
                                                    else "die H-tree parent leg -> child legs"))
                                          for P_ in ports])
            dst = src.with_name(src.stem + a.suffix + ".json")
            body = (json.dumps(new, indent=1) + "\n").encode()
            dst.write_bytes(body)
            newname[f] = str(Path(f).with_name(dst.name))
            rep["files"][f] = dict(out=newname[f], in_sha256=sha(src.read_bytes()), out_sha256=sha(body),
                                   pins_in=len(d["pins"]), pins_out=len(new["pins"]))
    n = 0
    for t in raw["partition_types"].values():
        for hc in t.get("hard_cores", []) or []:
            if hc.get("pins_file") in newname:
                hc["pins_file"] = newname[hc["pins_file"]]
                n += 1
    raw["clock"]["mesh"]["delta"] = raw["clock"]["mesh"].get("delta", "") + "+D-KV-ISL-FT-R25"
    out = Path(a.plan_out)
    out.write_text(json.dumps(raw, indent=1) + "\n")
    rep.update(hard_core_entries_repointed=n, plan_out=str(out), plan_out_sha256=sha(out.read_bytes()))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "modules"}, indent=1))
    for m, v in rep["modules"].items():
        print(m, v["instances"], [(p["role"], p["rect_um"], [(q["name"], q["x"], q["y"]) for q in p["pins"]]) for p in v["ports"]])


if __name__ == "__main__":
    main()
