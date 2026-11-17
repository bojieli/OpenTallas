#!/usr/bin/env python3
"""KV-HUBC-SPLIT: hub ring row writer.  Rebinds every ot_dp_clk_landing_cas ring of kv3_hub_C-style hub types whose
width is >= --min-w (default 250 bits) to a hard ring child core (OVERSIZE-1 form, KV-RING-CORES-MERGED.tsv masters).

Hub types carry no clock.landing_contract (kv3_hg* do), so hgsplit.py cannot do them.  Rings are found in the bound RTL
(`ot_dp_clk_landing_cas #(.W(n)...) u_cland_<bus> (`); the face of each ring comes from the bus pin site (--pins
JSON {bus: [x, y]} in the type frame, from pin_sites.type_pins / gen_phys io.tcl), the master from the exact parameter
set.  A ring with no master is reported NO_MASTER (never guessed).  0 added cycles: exact parent parameters.

usage: kv_hubc_ring_rows.py PLAN RTL OUT_PLAN --type kv3_hub_C --masters RKDIR [--pins pins.json] [--min-w 250]
"""
import argparse, glob, json, math, os, re, sys

RING = re.compile(r"ot_dp_clk_landing_cas\s*#\((?P<p>.*?)\)\s*(?P<inst>u_cland_\w+)\s*\(", re.S)
ORI = {("ew", "W"): "R0", ("ew", "E"): "MY", ("ns", "S"): "R0", ("ns", "N"): "MX"}


def parse_rings(text):
    """[(inst, bus, params)] for every ot_dp_clk_landing_cas instance in an RTL text."""
    out = []
    for m in RING.finditer(text):
        pr = {k: int(v) for k, v in re.findall(r"\.(\w+)\((\d+)\)", m.group("p"))}
        inst = m.group("inst")
        out.append((inst, inst[len("u_cland_"):], pr))
    return out


def norm(pr):
    d = dict(pr); d["W"] = int(d["W"]); return json.dumps(d, sort_keys=True)


def load_masters(rk):
    byk = {}
    for d in sorted(glob.glob(os.path.join(rk, "kv_cland_*"))):
        try:
            c = json.load(open(d + "/config.json")); p = json.load(open(d + "/pins.json"))
        except OSError:
            continue
        cells = None
        for f in glob.glob(d + "/kits/*/native_cell_count.json"):
            try: cells = json.load(open(f))["stdcells"]
            except Exception: pass
        byk[(norm(c["params"]), c["orient"])] = dict(name=os.path.basename(d), pins=p, cells=cells)
    return byk


def face_of(xy, size):
    x, y = xy; d = {"W": x, "E": size[0] - x, "S": y, "N": size[1] - y}
    return min(d, key=d.get)


def hit(r, o):
    return r[0] < o[2] and r[2] > o[0] and r[1] < o[3] and r[3] > o[1]


def rows(plan, rings, tn, masters, pins, min_w=250, grid=8.64, margin=8.64):
    t = plan["partition_types"][tn]; W, H = t["outline_um"]
    obs = []
    for h in t["hard_cores"]:
        x, y = h["origin_um"]; w, hh = h["outline_um"]; hl = h.get("halo_um") or 4.32
        obs.append((x - hl, y - hl, x + w + hl, y + hh + hl))
    out = []
    for inst, bus, pr in sorted(rings, key=lambda r: -r[2]["W"]):
        if pr["W"] < min_w:
            continue
        pxy = pins.get(bus)
        if pxy is None:
            out.append(dict(inst=inst, bus=bus, W=pr["W"], status="NO_PIN")); continue
        face = face_of(pxy, (W, H)); axes = ("ew", "ns") if face in "WE" else ("ns", "ew")
        best = None
        for ax in axes:
            M = masters.get((norm(pr), ax))
            if M is None:
                continue
            cw, ch = M["pins"]["outline_um"]
            ori = ORI[(ax, face)] if (ax, face) in ORI else None
            if ori is None:
                continue
            for i in range(int(W / grid) + 1):
                for j in range(int(H / grid) + 1):
                    ox, oy = i * grid, j * grid
                    r = (ox, oy, ox + cw, oy + ch)
                    if r[0] < margin or r[1] < margin or r[2] > W - margin or r[3] > H - margin:
                        continue
                    d = abs(ox + cw / 2 - pxy[0]) + abs(oy + ch / 2 - pxy[1])
                    if best and d >= best[0]:
                        continue
                    if any(hit(r, o) for o in obs):
                        continue
                    best = (d, ox, oy, M, ori, ax)
        if best is None:
            out.append(dict(inst=inst, bus=bus, W=pr["W"], status="NO_MASTER" if not any((norm(pr), a) in masters for a in axes) else "NO_SITE"))
            continue
        d, ox, oy, M, ori, ax = best; cw, ch = M["pins"]["outline_um"]
        obs.append((ox - 2.16, oy - 2.16, ox + cw + 2.16, oy + ch + 2.16))
        out.append(dict(inst=inst, bus=bus, W=pr["W"], status="OK", master=M["name"], orient=ori, face=face, axis=ax,
                        origin_um=[round(ox, 3), round(oy, 3)], outline_um=[cw, ch], cells=M["cells"] or int(24.9 * (pr["W"] + 1)),
                        params=pr))
    return out


def apply(plan, tn, res):
    t = plan["partition_types"][tn]
    for r in res:
        if r["status"] != "OK":
            continue
        t["hard_cores"].append(dict(
            inst="cl_" + r["bus"], module=r["master"], origin_um=r["origin_um"], outline_um=r["outline_um"], orient=r["orient"],
            physical_inst="u_bound." + r["inst"], physical_master=r["master"],
            param_wrap=dict(base="ot_dp_clk_landing_cas", params=r["params"]), cells=r["cells"],
            note="KV-HUBC-SPLIT: hub ring %s as hard ring child core (master %s, exact parent params, 0 added cycles); UNSIGNED until its master signs off" % (r["inst"], r["master"])))
    return plan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("rtl"); ap.add_argument("out")
    ap.add_argument("--type", default="kv3_hub_C"); ap.add_argument("--masters", required=True)
    ap.add_argument("--pins", required=True); ap.add_argument("--min-w", type=int, default=250)
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    res = rows(plan, parse_rings(open(a.rtl).read()), a.type, load_masters(a.masters), json.load(open(a.pins)), a.min_w)
    apply(plan, a.type, res)
    json.dump(plan, open(a.out, "w"), indent=1)
    for r in res:
        print(r["status"], r["inst"], r["W"], r.get("master", ""))
    bad = [r for r in res if r["status"] != "OK"]
    print("rings", len(res), "ok", len(res) - len(bad), "not ok", len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
