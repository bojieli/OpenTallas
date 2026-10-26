#!/usr/bin/env python3
"""KV-PLAN2 10-25 (plan v3.9d geometry, COORD KV RULINGS 05:07 (b)(c)): the three channel-lattice blockers that
chan_windows.py reports NO_FIT on v3.9 get a structural fix before the pins are re-windowed.

(1) pv column (pv|pv N/S boundaries: up to 8,154 pins per boundary through ~340 um of N/S channel mouth = 24 pins/um):
    the pv column (13 kv3_pv* types, kv3_hub_C, kv3_sys_c) widens 1900.8 -> 2160.0 um (+259.2 = 30 lattice steps,
    ruling (b)); the four pv_pair columns re-space from 103.68-um to 190.08-um N/S channels (edges stay 34.56), each
    column's join core moves with it.  Every partition east of the column shifts +259.2 um; the die is 11076.48 um
    wide; the clock spine root stays at the column centre (x + 129.6).  Port windows on N/S faces east of the column
    shift with their partitions; the column's own N/S windows are re-packed by chan_windows.py.
(2) kv3_hub_Wi (hub_Wi|hub_Wo: 5,239 pins, NO_FIT): the 22 host cores (none hardened yet: 0 kits) re-place from five
    full-width rows into a bottom block (pad + 2x4 adapters + qm + cdc_ci + cdc_hi; guard/queue/prompt right-aligned)
    and a top block (cdc_pc/peer/tx/rx, ingest/order/cdc_ch), leaving an E-W channel y 622..855 um that lines up with
    the free band of kv3_hub_C (y 561.6..1045.44) and the free kv3_hub_Wo face; every block keeps >= 110 um from the
    N and S faces; W-face mouth ~710 um (was ~360), N/S faces free.
(3) kv3_hg* (hg|hg N/S: 9,804 pins, NO_FIT): the 881.28 x 216 qkd_ectlk strip spans two of the three N/S channels
    between the head_eighth columns.  Ruling (c): split it (KV-CORES owns the RTL split; request in KVG3-CORES.md) into
    four column-aligned planned cores qkd_ectlk_q0..q3 (inner 216 x 293.76, outer 216 x 172.8 at the top: 201.5k um2 vs
    190.4k), one above each head_eighth column, so all three N/S channels run through the tile and the E/W face mouth
    above the head rows stays open.  PLANNED: the quarter pins files are a
    placeholder split of qkd_ectlk_pins.json (S pins by x range, W pins -> q0, E pins -> q3, clock/reset N pins on every
    quarter) on the plan tracks, to be replaced by the KV-CORES top-down re-pin.
usage: geom_v39d.py IN_PLAN OUT_PLAN [--cores-out DIR]   (writes the quarter pins files into DIR, default <plan dir>/cores)
"""
import argparse
import copy
import json
import math
from pathlib import Path

GRID = 8.64
DW = 259.2                      # pv column widening (30 lattice steps)
PV_X0 = 4458.24                 # pv column origin (die frame)
PV_W0 = 1900.8
PV_COLS = [34.56, 604.8, 1175.04, 1745.28]     # new pv_pair column x (was 34.56, 518.4, 1002.24, 1486.08)
PV_OLD = [34.56, 518.4, 1002.24, 1486.08]
WIDEN = lambda tn: tn.startswith("kv3_pv") or tn in ("kv3_hub_C", "kv3_sys_c")

HUB_WI = {   # inst -> (x, y)   (outlines and orients unchanged); every block >= 110 um from the N and S faces
    "host__qkd_hr_phy_pad": (25.92, 120.96),
    "host__qkd_hr_phy_adp_0": (181.44, 120.96), "host__qkd_hr_phy_adp_1": (302.4, 120.96),
    "host__qkd_hr_phy_adp_2": (423.36, 120.96), "host__qkd_hr_phy_adp_3": (544.32, 120.96),
    "host__qkd_hr_phy_adp_4": (181.44, 233.28), "host__qkd_hr_phy_adp_5": (302.4, 233.28),
    "host__qkd_hr_phy_adp_6": (423.36, 233.28), "host__qkd_hr_phy_adp_7": (544.32, 233.28),
    "host__qkd_hr_host_qm": (665.28, 120.96), "host__qkd_hr_cdc_ci": (760.32, 120.96),
    "host__qkd_hr_cdc_hi": (1002.24, 120.96),
    "host__qkd_hr_core_guard": (483.84, 362.88), "host__qkd_hr_core_queue": (760.32, 362.88),
    "host__qkd_hr_core_prompt": (1019.52, 362.88),
    "host__qkd_hr_cdc_pc": (25.92, 855.36), "host__qkd_hr_core_peer": (362.88, 855.36),
    "host__qkd_hr_core_tx": (691.2, 855.36), "host__qkd_hr_core_rx": (984.96, 855.36),
    "host__qkd_hr_ingest_eng": (25.92, 1192.32), "host__qkd_hr_core_order": (406.08, 1192.32),
    "host__qkd_hr_cdc_ch": (751.68, 1192.32),
}
HG_COLS = [17.28, 336.96, 656.64, 976.32]
# quarters (v3.9d): inner two were 216 x 293.76, outer two 216 x 172.8 at the top so the E/W face mouth above the head rows
# so the E/W face mouth above the head rows (y 1192..1330) stays open for hg|hgi / hg|pc pins (201.5k um2 vs 190.4k)
Q_W = 216.0
# KV-PLAN3 10-25: synthesized quarters (ectlk_live.json: 2-3 SRAM 128x256 + ~2.7k um2 cells, 23-28 % of the outlines)
# fit 216 x 172.8 -> all four quarters one outline at the top (one kit frame, wider channel above the head rows)
Q_GEOM = [(17.28, 1330.56, 172.8), (336.96, 1330.56, 172.8), (656.64, 1330.56, 172.8), (976.32, 1330.56, 172.8)]


def snap(c, off, pitch):
    return round(off + round((c - off) / pitch) * pitch, 6)


def quarter_pins(src, cores_dir):
    d = json.loads(Path(src).read_text())
    W0 = 881.28
    span = W0 / 4
    q = [[] for _ in range(4)]
    QH = [g[2] for g in Q_GEOM]
    for p in d["pins"]:
        x, y, ln = p["x"], p["y"], p["layer"]
        if y <= 1e-6 + 0.2 and ln in ("M5", "M7"):                 # S face (y ~ 0)
            k = min(3, int(x // span))
            nx = snap((x - k * span) * Q_W / span, 0.024, 0.048)
            q[k].append(dict(p, x=min(max(nx, 0.072), Q_W - 0.072)))
        elif y >= 216.0 - 0.2:                                       # N face: clock / reset entry -> every quarter
            for k in range(4):
                nx = snap(Q_W / 2 + (x - W0 / 2), 0.024, 0.048)
                q[k].append(dict(p, x=nx, y=round(QH[k] - (216.0 - y), 6)))
        elif x <= 0.2:                                               # W face -> q0
            q[0].append(dict(p, y=snap(min(max(y * QH[0] / 216.0, 0.072), QH[0] - 0.072), 0.024, 0.048)))
        else:                                                        # E face -> q3
            q[3].append(dict(p, x=round(Q_W - (W0 - x), 6),
                             y=snap(min(max(y * QH[3] / 216.0, 0.072), QH[3] - 0.072), 0.024, 0.048)))
    out = []
    for k in range(4):
        # de-duplicate snapped S-face pins on one track: move to the next free track
        seen = set()
        pins = []
        for p in sorted(q[k], key=lambda p: (p["layer"], p["y"], p["x"])):
            key = (p["layer"], round(p["x"], 4), round(p["y"], 4))
            while key in seen:
                if p["y"] <= 0.2 or p["y"] >= QH[k] - 0.2:
                    p = dict(p, x=round(p["x"] + 0.048, 6))
                else:
                    p = dict(p, y=round(p["y"] + 0.048, 6))
                key = (p["layer"], round(p["x"], 4), round(p["y"], 4))
            seen.add(key)
            pins.append(p)
        nm = f"qkd_ectlk_q{k}"
        fn = Path(cores_dir) / f"{nm}_pins.json"
        fn.write_text(json.dumps(dict(
            schema=d["schema"], core=nm, frame=f"core R0, origin (0,0), outline {Q_W} x {QH[k]}",
            source="KV-PLAN2 10-25 PLACEHOLDER: column-aligned quarter of qkd_ectlk (geom_v39d.py) from "
                   "qkd_ectlk_pins.json -- KV-CORES re-pins after the RTL split", pins=pins), indent=0) + "\n")
        out.append((nm, len(pins)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--cores-out")
    ap.add_argument("--die-io-out", help="shifted die_io.json (default: next to OUT_PLAN)")
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    T = raw["partition_types"]
    log = []
    # (1) pv column
    shifted = set()
    for p in raw["partitions"]:
        if p["origin_um"][0] > PV_X0 + 1:
            p["origin_um"][0] = round(p["origin_um"][0] + DW, 4)
            shifted.add(p["name"])
    for tn, t in T.items():
        if not WIDEN(tn):
            continue
        t["outline_um"][0] = round(t["outline_um"][0] + DW, 4)
        for k in ("clock", "reset"):
            if t.get(k, {}).get("tap_um"):
                t[k]["tap_um"][0] = round(t[k]["tap_um"][0] + DW / 2, 4)
        for c in t.get("hard_cores", []):
            if tn.startswith("kv3_pv"):
                x = c["origin_um"][0]
                col = min(range(4), key=lambda i: abs(x - PV_OLD[i]) if x - PV_OLD[i] > -1 else 1e9)
                c["origin_um"][0] = round(x + PV_COLS[col] - PV_OLD[col], 4)
        if "note" in t:
            t["note"] += " | v3.9d: column widened +259.2 um (N/S channels 190.08 um between pv_pair columns)"
        log.append(f"widen {tn}")
    raw["die"]["outline_um"][0] = round(raw["die"]["outline_um"][0] + DW, 4)
    raw["clock"]["spine"]["root_um"][0] = round(raw["clock"]["spine"]["root_um"][0] + DW / 2, 4)
    parts = {p["name"]: p for p in raw["partitions"]}
    col_parts = {n for n, p in parts.items() if WIDEN(p["type"])}
    for pr in raw["ports"]:
        if pr["face"] not in "NS":
            continue
        s, d = pr["src"]["part"], pr["dst"]["part"]
        if s in shifted or d in shifted:
            pr["window_um"] = [round(x + DW, 4) for x in pr["window_um"]]
        elif s in col_parts or d in col_parts:
            # column N/S windows: scale into the wider face (re-packed by chan_windows.py afterwards)
            f = (PV_W0 + DW) / PV_W0
            pr["window_um"] = [round(PV_X0 + (x - PV_X0) * f, 4) for x in pr["window_um"]]
    # (2) hub_Wi
    for c in T["kv3_hub_Wi"]["hard_cores"]:
        c["origin_um"] = list(HUB_WI[c["inst"]])
        if c["inst"][-2:] in ("_4", "_5", "_6", "_7") and "phy_adp" in c["inst"]:
            c["orient"] = "R0"    # every adapter now sits E of the pad: no MY copy (its W pins would face away)
    T["kv3_hub_Wi"]["note"] = T["kv3_hub_Wi"].get("note", "") + (" | v3.9d: host cores re-placed into a bottom and a "
                                                                    "top block -> E-W channel y 527..950 um")
    # (3) kv3_hg*: ectlk -> four column-aligned quarters
    cores_dir = Path(a.cores_out or Path(a.plan).resolve().parent / "cores")
    qp = quarter_pins(Path(a.plan).resolve().parent / "cores/qkd_ectlk_pins.json", cores_dir)
    for tn, t in T.items():
        hcs = t.get("hard_cores", [])
        e = [c for c in hcs if c.get("module") == "qkd_ectlk"]
        if not e:
            continue
        e = e[0]
        hcs.remove(e)
        for k, (x, y, hq) in enumerate(Q_GEOM):
            c = copy.deepcopy(e)
            c.update(inst=f"ectl_q{k}", module=f"qkd_ectlk_q{k}", origin_um=[x, y], outline_um=[Q_W, hq],
                     pins_file=f"cores/qkd_ectlk_q{k}_pins.json",
                     note="PLANNED v3.9d: column-aligned quarter of qkd_ectlk (COORD ruling 10-25 (c), RTL split by "
                          "KV-CORES); placeholder pins from the qkd_ectlk table")
            hcs.append(c)
        log.append(f"ectlk split {tn}")
    Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
    # die IO sites move with their host partitions (pv column: sys_c widens)
    io = json.loads((Path(a.plan).resolve().parent / "die_io.json").read_text())
    for e in io:
        r = e["rect_um"]
        if e["part"] in shifted:
            e["rect_um"] = [round(r[0] + DW, 4), r[1], round(r[2] + DW, 4), r[3]]
        elif e["part"] in col_parts:
            e["rect_um"] = [r[0], r[1], round(r[2] + DW, 4), r[3]]
    Path(a.die_io_out or Path(a.out).parent / "die_io.json").write_text(json.dumps(io, indent=1) + "\n")
    print(f"geom_v39d: {len(shifted)} partitions shifted +{DW}; {sum(1 for x in log if x.startswith('widen'))} types "
          f"widened; hub_Wi re-placed; ectlk quarters {qp}; die {raw['die']['outline_um']}")


if __name__ == "__main__":
    main()
