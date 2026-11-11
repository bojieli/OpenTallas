#!/usr/bin/env python3
"""HEAD-92/H2 11-10 (COORD ruling: hd_host_e form H2): type-local plan event for hd_host_e + the new hard core
ot_s81hd_he_epc (u_rr + u_ep of the lane-1 collector, tools/s81_head/head_he_epc_kit.py).

  * hard_cores: the 36 u_ep ot_sram_1r1w2c_256x64_m1 entries -> ONE entry u_core.u_lane1.u_ln.u.u_epc
    (ot_s81hd_he_epc, 224.64 x 492.48 at (336.96, 60.48), pins core_pins/ot_s81hd_he_epc_pins.json, views from --views);
  * the 19 ot_sram_1r1w2c_32x64_m1 leave the core rectangle: u_gb.u_sf column -> x 233.28 (W of the tap, next to the
    gbx / l1 W windows), u_ski.u_head column -> x 604.8 (E strip, next to the coll_i1 S window);
  * clock / reset points that fell inside the core rectangle move just outside it (chain order kept): reset tap
    (531.36, 172.8) -> (574.56, 172.8); coll_i1 reader start stage 2 and status anchor u_cland_agg_2 -> S strip
    y 47.52; landing local reset k4 -> (524.65, 51.84); density sink sites inside the core dropped, the two on its N
    edge lifted to y 559.872.  The type clock tap and count straps (x 319.68-324) do not move;
  * verilog_defines += OT_HE_EPC; sources += rtl/dsrom_sys/s81_head/ot_s81hd_he_epc.sv.

    python3 -I physical/die_plan/s81_head/plan_of_record/l48hp1_h2/apply_delta.py IN_PLAN.json OUT_PLAN.json [--views DIR] [--type hd_host_e]
"""
import argparse
import hashlib
import json
from pathlib import Path

INST = "u_core.u_lane1.u_ln.u.u_epc"
EP = "u_core.u_lane1.u_ln.u.u_ep."
MOD = "ot_s81hd_he_epc"
ORIGIN, OUTLINE = [336.96, 60.48], [224.64, 492.48]
SRC = "rtl/dsrom_sys/s81_head/ot_s81hd_he_epc.sv"
DEF = "OT_HE_EPC"
VIEWS = "results/head_he_epc_h2_1110"


def inside(x, y, m=0.0):
    return ORIGIN[0] - m <= x <= ORIGIN[0] + OUTLINE[0] + m and ORIGIN[1] - m <= y <= ORIGIN[1] + OUTLINE[1] + m


def apply(raw, tn="hd_host_e", views=VIEWS):
    t = raw["partition_types"][tn]
    log = []
    hc = t["hard_cores"]
    ep = [h for h in hc if h["inst"].startswith(EP)]
    if len(ep) != 36 or any(h["module"] != "ot_sram_1r1w2c_256x64_m1" for h in ep):
        raise SystemExit(f"expected 36 u_ep 256x64 SRAM entries, found {len(ep)}")
    if any(h["inst"] == INST for h in hc):
        raise SystemExit("already applied")
    keep = [h for h in hc if not h["inst"].startswith(EP)]
    for h in keep:
        x, y = h["origin_um"]
        if ".u_gb.u_sf." in h["inst"]:
            k = int(h["inst"].split("g_bank[")[1].split("]")[0])
            h["origin_um"] = [233.28, 259.2 if k == 9 else y]
        elif ".u_ski.u_head." in h["inst"]:
            h["origin_um"] = [604.8, y]
        log.append(f"{h['inst']}: {[x, y]} -> {h['origin_um']}") if [x, y] != h["origin_um"] else None
    keep.append(dict(inst=INST, module=MOD, origin_um=ORIGIN, outline_um=OUTLINE, orient="R0", track_offset_um=[0.0, 0.0],
                     pins_file=f"core_pins/{MOD}_pins.json", lef=f"{views}/{MOD}.lef", lib=f"{views}/{MOD}_tt.lib",
                     note="HEAD-92/H2 11-10 (COORD hd_host_e form H2): u_rr + u_ep of the lane-1 collector as one hard core, "
                          "face shell off (0 pin cycles, cut ports timed_face), 36 ep SRAMs inside; kit "
                          "tools/s81_head/head_he_epc_kit.py"))
    t["hard_cores"] = keep
    for h in keep:   # no other hard core may overlap the new one
        if h["inst"] == INST:
            continue
        x, y = h["origin_um"]; w, hh = h["outline_um"]
        if x < ORIGIN[0] + OUTLINE[0] and x + w > ORIGIN[0] and y < ORIGIN[1] + OUTLINE[1] and y + hh > ORIGIN[1]:
            raise SystemExit(f"{h['inst']} overlaps the core")
    c = t["clock"]
    ss = []
    for s in c["sink_sites_um"]:
        if inside(s[0], s[1]) and s[1] > ORIGIN[1] + OUTLINE[1] - 2.0:
            ss.append([s[0], 559.872] + s[2:]); log.append(f"sink site {s} -> {ss[-1]}")
        elif inside(s[0], s[1]):
            log.append(f"sink site {s} dropped")
        else:
            ss.append(s)
    c["sink_sites_um"] = ss
    st = c["landing_reader_start"]["branches"]["coll_i1"]["stages"][2]
    log.append(f"reader start coll_i1 stage 2 {st['xy_um']} -> [445.17, 47.52]"); st["xy_um"] = [445.17, 47.52]
    an = c["landing_status_anchors"]
    log.append(f"u_cland_agg_2 {an['u_cland_agg_2']} -> [351.81, 47.52]"); an["u_cland_agg_2"] = [351.81, 47.52]
    for r in c["landing_local_resets"]:
        if r["name"] == "k4":
            log.append(f"local reset k4 {r['xy_um']} -> [524.65, 51.84]"); r["xy_um"] = [524.65, 51.84]
    lt = t["reset"]["local_taps_um"]
    for i, p in enumerate(lt):
        if inside(*p):
            log.append(f"reset tap {p} -> [574.56, {p[1]}]"); lt[i] = [574.56, p[1]]
    if DEF not in t["verilog_defines"]:
        t["verilog_defines"].append(DEF)
    if SRC not in t["sources"]:
        i = t["sources"].index("rtl/dsrom_sys/s81_head/ot_s81hd_mesh_ep_core.sv")
        t["sources"].insert(i, SRC)
    bad = []

    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, p + "." + k)
        elif isinstance(o, list):
            if len(o) >= 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in o[:2]):
                if inside(o[0], o[1]):
                    bad.append(f"{p} {o}")
            else:
                for i, v in enumerate(o):
                    walk(v, f"{p}[{i}]")
    tt = {k: v for k, v in t.items() if k != "hard_cores"}
    walk(tt, tn)
    if bad:
        raise SystemExit("points left inside the core: " + "; ".join(bad))
    return log


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp")
    ap.add_argument("out")
    ap.add_argument("--type", default="hd_host_e")
    ap.add_argument("--views", default=VIEWS)
    a = ap.parse_args()
    raw = json.loads(Path(a.inp).read_text())
    for line in apply(raw, a.type, a.views):
        print(line)
    d = json.dumps(raw, indent=1) + "\n"
    Path(a.out).write_text(d)
    print("plan sha", hashlib.sha256(d.encode()).hexdigest()[:12])


if __name__ == "__main__":
    main()
