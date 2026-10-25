#!/usr/bin/env python3
"""KV-PLAN3 10-25: real pin tables of the four column-aligned ECTLK cores qkd_ectlk_q0..q3 (replaces the v3.9d
PLACEHOLDER split of geom_v39d.py.quarter_pins).

Source of truth = the quarter modules of the four-column RTL (codex/kv-ectlk-1025 ectlk_columns.py ->
qkd_ectlk_columns.sv; lockstep miter vs the legacy qkd_ectlk PASS, 0 mismatches over 8580 edges), approved pin drop
applied by that generator (so 413->271, req_v gone, req_t 14->13, si 633->537; KV-CORES RULING 10-25 05:28 (1)):
  * port list per quarter = the module header (compact names);
  * new bit -> legacy bit from the generator's `assign X[i] = old_X[j]` / `assign old_X[j] = X[i]` lines, so every
    pin inherits the face and layer of its legacy pin (qkd_ectlk_pins.json);
  * inputs: only the bits live after synthesis of that quarter (ectlk_live.json); without it every input is kept
    (and the report says so).
Placement (quarter frame, outline from geom_v39d.Q_GEOM): pins of one face keep the legacy order along the face and
are spread evenly over it (2 um corner keep-out), die symmetric tracks (offset pitch/2).  One ck pin and rst_n at the
N-face centre (each quarter has its own clock entry: KV-PLAN2 05:35 request).
"""
import json
import re
from collections import defaultdict
from pathlib import Path

import post_v39e as PV

Q_W = 216.0
Q_H = [172.8, 293.76, 293.76, 172.8]
KEEP = 2.0
HDR = re.compile(r"^\s*(input|output)\s+wire\s+\[(\d+):0\]\s+(\w+)")
AO = re.compile(r"^\s*assign\s+(\w+)\[(\d+)\]\s*=\s*old_(\w+)\[(\d+)\];")
AI = re.compile(r"^\s*assign\s+old_(\w+)\[(\d+)\]\s*=\s*(\w+)\[(\d+)\];")


def parse_sv(sv):
    mods, cur, in_hdr = {}, None, False
    for ln in Path(sv).read_text().splitlines():
        m = re.match(r"^module\s+(qkd_ectlk_q[0-3])\s*\(", ln)
        if m:
            cur, in_hdr = m.group(1), True
            mods[cur] = dict(ports={}, omap={}, imap={})
            continue
        if re.match(r"^module\s", ln):
            cur = None
            continue
        if cur is None:
            continue
        if in_hdr:
            m = HDR.match(ln)
            if m:
                mods[cur]["ports"][m.group(3)] = (m.group(1), int(m.group(2)) + 1)
            if ln.strip().startswith(");"):
                in_hdr = False
            continue
        m = AO.match(ln)
        if m and m.group(1) in mods[cur]["ports"]:
            mods[cur]["omap"][(m.group(1), int(m.group(2)))] = (m.group(3), int(m.group(4)))
            continue
        m = AI.match(ln)
        if m and m.group(3) in mods[cur]["ports"]:
            mods[cur]["imap"][(m.group(3), int(m.group(4)))] = (m.group(1), int(m.group(2)))
    return mods


def build(raw, cores, sv, live_json=None):
    cores = Path(cores)
    leg = json.loads((cores / "qkd_ectlk_pins.json").read_text())
    W0, H0 = PV.outline_of(leg)
    lpin = {p["name"]: p for p in leg["pins"]}
    mods = parse_sv(sv)
    live = json.loads(Path(live_json).read_text())["quarters"] if live_json else None
    rep = dict(source=str(sv), liveness="synthesized" if live else "NOT_SYNTHESIZED (all inputs kept)", quarters={})
    for k in range(4):
        nm = f"qkd_ectlk_q{k}"
        M = mods[nm]
        W, H = Q_W, Q_H[k]
        faces = defaultdict(list)
        dropped_dead, missing_leg = 0, 0
        for pn, (dr, wd) in M["ports"].items():
            if pn in ("ck", "rst_n"):
                continue
            for i in range(wd):
                if dr == "input" and live is not None:
                    lv = live[nm]["live_inputs"].get(pn, [])
                    if i not in lv:
                        dropped_dead += 1
                        continue
                old = (M["omap"] if dr == "output" else M["imap"]).get((pn, i), (pn, i))
                lp = lpin.get(f"{old[0]}[{old[1]}]")
                if lp is None:
                    missing_leg += 1
                    f, ly, c = ("S", "M5", W0 / 2)
                else:
                    f = PV.face_of(lp, leg)
                    ly = lp["layer"]
                    c = lp["x"] if f in "SN" else lp["y"]
                faces[f].append((c, ly, f"{pn}[{i}]"))
        pins = []
        for f, lst in faces.items():
            lst.sort()
            L = W if f in "SN" else H
            n = len(lst)
            for j, (c, ly, name) in enumerate(lst):
                v = KEEP + (L - 2 * KEEP) * (j + 0.5) / n
                if f in "SN":
                    pins.append(dict(name=name, layer=ly, x=v, y=0.096 if f == "S" else H - 0.096))
                else:
                    pins.append(dict(name=name, layer=ly, x=0.096 if f == "W" else W - 0.096, y=v))
        pins.append(dict(name="ck[0]", layer="M5", x=W / 2, y=H - 0.096))
        pins.append(dict(name="rst_n[0]", layer="M5", x=W / 2 + 0.576, y=H - 0.096))
        pins.sort(key=lambda p: (p["layer"], p["x"], p["y"]))
        pins, _ = PV.die_tracks(pins, W, H)
        fc = defaultdict(lambda: dict(pins=0, layers=set()))
        for p in pins:
            f = PV.face_of(p, dict(frame=f"outline {W} x {H}"))
            fc[f]["pins"] += 1
            fc[f]["layers"].add(p["layer"])
        d = dict(schema=leg["schema"], core=nm, frame=f"core R0, origin (0,0), outline {W} x {H}",
                 source=("KV-PLAN3 v3.9e: quarter pins from the four-column RTL ports (ectlk_columns.py, lockstep "
                         "miter PASS) with the approved pin drop; legacy face/layer/order per bit; inputs "
                         + rep["liveness"]),
                 faces={f: dict(pins=v["pins"], layers=sorted(v["layers"])) for f, v in sorted(fc.items())},
                 pins=pins)
        (cores / f"{nm}_pins.json").write_text(json.dumps(d, indent=0) + "\n")
        per_um = {f: round(v["pins"] / (W if f in "SN" else H), 2) for f, v in fc.items()}
        rep["quarters"][nm] = dict(pins=len(pins), dead_inputs_dropped=dropped_dead, no_legacy_pin=missing_leg,
                                   faces={f: v["pins"] for f, v in sorted(fc.items())}, pins_per_um=per_um)
    # the plan's hard-core notes lose the PLACEHOLDER wording
    for t in raw["partition_types"].values():
        for c in t.get("hard_cores", []) or []:
            if str(c.get("module", "")).startswith("qkd_ectlk_q"):
                c["note"] = ("v3.9e: column-aligned quarter of qkd_ectlk (COORD ruling 10-25 (c)); pins from the "
                             "four-column RTL (ectlk_columns.py, miter PASS), approved pin drop applied")
    return rep
