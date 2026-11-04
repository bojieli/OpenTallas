#!/usr/bin/env python3
"""DIE-KV-64/RF-B 11-03 CONSERVATIVE split plan delta (see rf_kv3_split.py): every qkd_kvs_pc / qkd_kvs_pc_h_head_p hard
core of the RF-KV1 derived plan becomes two hard cores inside the old 397.44 x 362.88 footprint:
  <inst>    PCC (qkd_kvs_pcc / qkd_kvs_pcc_h_head_p), the RF-KV1 slot 293.76 x 267.84, same origin / orient
  <inst>_f  PCF (qkd_kvs_pcf), 90.72 x 267.84 on the core-frame E side (PC tables have no E pins), 8.64 um channel
Pins: PCC = RF-KV1 table minus i_grp[104:71] and the front/return o_grp bits (kept bits renamed i_grp_c / o_grp_c, same
place), + pcf_x[297:0] on its E face (M4).  PCF = pcf_x[297:0] on its W face at the same y (faces each other in every
orient), i_grp_f / o_grp_f / hrst_n on the face (S or N) that carries the grp pins in the source table, in the source
order; ck / rst_n interior at the PCF centre.

    rf_kv3_plan.py PLAN_RF1 OUT_PLAN DELTA_JSON
"""
import copy
import json
import math
import sys
from pathlib import Path

W, H = 293.76, 267.84
FW, GAP = 90.72, 8.64
PITCH, OFFS, KEEP, EDGE = 0.048, 0.024, 2.16, 0.096
OG_PCC = [289, 290, 291, 292, 293, 294, 299, 300]
OG_PCF = list(range(0, 289)) + [295, 296, 297, 298, 301, 302, 303, 304]
IG_PCF = list(range(71, 105))
IG_PCC = list(range(0, 71)) + list(range(105, 128))
PCC = {"qkd_kvs_pc": "qkd_kvs_pcc", "qkd_kvs_pc_h_head_p": "qkd_kvs_pcc_h_head_p"}
PCF = "qkd_kvs_pcf"


def snap(c):
    return round(OFFS + round((c - OFFS) / PITCH) * PITCH, 3)


def face_of(p, w, h):
    x, y = p["x"], p["y"]
    if abs(y - (h - EDGE)) < 1e-6:
        return "N"
    if abs(y - EDGE) < 1e-6:
        return "S"
    if abs(x - (w - EDGE)) < 1e-6:
        return "E"
    if abs(x - EDGE) < 1e-6:
        return "W"
    return "I"


def bit(name):
    b, i = name[:-1].split("[")
    return b, int(i)


def cross_y():
    n, sp = 298, 16  # 16 tracks = 0.768 um
    y0 = snap((H - (n - 1) * sp * PITCH) / 2)
    return [round(y0 + k * sp * PITCH, 3) for k in range(n)]


def split_pins(src, dst_c, dst_f, pcc_mod):
    d = json.load(open(src))
    assert f"outline {W:g} x {H:g}" in d["frame"], d["frame"]
    cp, grp = [], []
    for p in d["pins"]:
        nm = p["name"]
        if nm.startswith("i_grp[") or nm.startswith("o_grp["):
            b, i = bit(nm)
            grp.append((p, b, i))
            if b == "i_grp" and i in IG_PCC:
                cp.append(dict(p, name=f"i_grp_c[{IG_PCC.index(i)}]"))
            elif b == "o_grp" and i in OG_PCC:
                cp.append(dict(p, name=f"o_grp_c[{OG_PCC.index(i)}]"))
            continue
        assert face_of(p, W, H) != "E", nm
        cp.append(dict(p))
    ys = cross_y()
    for k, y in enumerate(ys):
        cp.append(dict(name=f"pcf_x[{k}]", layer="M4", x=round(W - EDGE, 3), y=y))
    gf = {face_of(p, W, H) for p, _, _ in grp}
    assert len(gf) == 1 and gf <= {"N", "S"}, gf
    gface = gf.pop()
    lay = grp[0][0]["layer"]
    # PCF face pins in the source x order (moved bits only), hrst_n last
    mv = sorted([(p["x"], b, i) for p, b, i in grp if (b == "i_grp" and i in IG_PCF) or (b == "o_grp" and i in OG_PCF)])
    names = [f"i_grp_f[{IG_PCF.index(i)}]" if b == "i_grp" else f"o_grp_f[{OG_PCF.index(i)}]" for _, b, i in mv] + ["hrst_n[0]"]
    sp = 5  # tracks (0.24 um)
    span = (len(names) - 1) * sp * PITCH
    assert span <= FW - 2 * KEEP, span
    x0 = snap((FW - span) / 2)
    fp = [dict(name=n, layer=lay, x=round(x0 + k * sp * PITCH, 3), y=round(EDGE if gface == "S" else H - EDGE, 3))
          for k, n in enumerate(names)]
    fp += [dict(name=f"pcf_x[{k}]", layer="M4", x=EDGE, y=y) for k, y in enumerate(ys)]
    ck = next(p for p in d["pins"] if p["name"] == "ck[0]")
    rs = next(p for p in d["pins"] if p["name"] == "rst_n[0]")
    cx = snap(FW / 2)
    fp += [dict(name="ck[0]", layer=ck["layer"], x=cx, y=ck["y"]),
           dict(name="rst_n[0]", layer=rs["layer"], x=round(cx + (rs["x"] - ck["x"]), 3), y=rs["y"])]
    src_note = d["source"] + " | RF-KV3 DIE-KV-64/RF-B 11-03 CONSERVATIVE split (rf_kv3_plan.py)"
    oc = dict(d, core=pcc_mod, source=src_note + ": PCC", pins=cp)
    of = dict(schema=d["schema"], core=PCF, frame=f"core R0, origin (0,0), outline {FW:g} x {H:g}",
              source=src_note + f": PCF, face {gface}", pins=fp)
    for o, fn in ((oc, dst_c), (of, dst_f)):
        Path(fn).write_text(json.dumps(o, indent=0))
    return oc, of, gface, len(cp), len(fp)


def main(plan_path, out_plan, delta_path):
    plan = json.load(open(plan_path))
    pdir = Path(plan_path).resolve().parent
    done = {}
    delta = dict(schema="opentallas.kv.rf_kv3_split_delta.v1", lane="DIE-KV-64/RF-B",
                 form="CONSERVATIVE split PC -> PCC + PCF (OWNER 18:57; DIE-KV-64 GO 11-03)",
                 face=dict(bits=298, dir="PCC->PCF", content="{corrected_epoch[15:0], controller_co[281:0]}",
                           edges="+1 PCC launch flop, +1 PCF capture flop"),
                 latency="PCF = PC front+return shifted uniformly +2 edges (blk_go / expected_* +2 inside PCF): the KV read "
                         "return o_grp_f (actual_*, front/return status) leaves 2 edges later than the PC's o_grp; "
                         "compiler: consumer schedule of actual_* +2 edges (TOK-VERIFY-1)",
                 i_grp_map=dict(pcc=IG_PCC, pcf=IG_PCF), o_grp_map=dict(pcc=OG_PCC, pcf=OG_PCF),
                 pins_files={}, hard_cores=[], clock_taps=[])
    for t, v in plan["partition_types"].items():
        hcs = v.get("hard_cores") or []
        new = []
        for c in hcs:
            if c.get("module") not in PCC:
                new.append(c)
                continue
            assert c["outline_um"] == [W, H], (t, c["inst"])
            pf = c["pins_file"]
            fc_, ff_ = pf[:-5] + "_rf3c.json", pf[:-5] + "_rf3f.json"
            if pf not in done:
                oc, of, gface, nc, nf = split_pins(pdir / pf, pdir / fc_, pdir / ff_, PCC[c["module"]])
                done[pf] = (gface, nc, nf)
                delta["pins_files"][pf] = dict(pcc=fc_, pcf=ff_, grp_face=gface, pcc_pins=nc, pcf_pins=nf)
            ox, oy = c["origin_um"]
            o = c["orient"]
            fx = ox + W + GAP if o in ("R0", "MX") else ox - GAP - FW
            cc = dict(c, module=PCC[c["module"]], pins_file=fc_,
                      note=(c.get("note") or "") + " | RF-KV3 split PCC (DIE-KV-64/RF-B 11-03, derived plan)")
            cf = dict(inst=c["inst"] + "_f", module=PCF, origin_um=[round(fx, 3), oy], outline_um=[FW, H], orient=o,
                      note=f"RF-KV3 split PCF of {c['inst']} (u_front + u_return; DIE-KV-64/RF-B 11-03, derived plan)",
                      track_offset_um=c.get("track_offset_um") or [0.0, 0.0], pins_file=ff_)
            new += [cc, cf]
            delta["hard_cores"].append(dict(type=t, inst=c["inst"], pcc=dict(module=cc["module"], origin=c["origin_um"],
                                            outline=[W, H], pins_file=fc_),
                                            pcf=dict(inst=cf["inst"], module=PCF, origin=cf["origin_um"], outline=[FW, H],
                                                     orient=o, pins_file=ff_)))
            tro = cf["track_offset_um"]
            ckp = next(p for p in json.load(open(pdir / ff_))["pins"] if p["name"] == "ck[0]")
            X = ckp["x"] if o in ("R0", "MX") else FW - ckp["x"]
            Y = ckp["y"] if o in ("R0", "MY") else H - ckp["y"]
            taps = (v.get("clock") or {}).get("taps")
            if taps is not None:
                base = next((x for x in taps if x.get("name") == f"{c['inst']}.ck[0]"), None)
                if base is not None:
                    nt = dict(base, name=f"{cf['inst']}.ck[0]", xy=[round(fx + X + tro[0], 3), round(oy + Y + tro[1], 3)],
                              budget_owner=PCF, note="RF-KV3 split PCF ck (same leaf contract as the PC ck tap)")
                    taps.append(nt)
                    delta["clock_taps"].append(dict(type=t, name=nt["name"], xy=nt["xy"]))
        v["hard_cores"] = new if hcs else hcs
    Path(out_plan).write_text(json.dumps(plan, indent=1))
    Path(delta_path).write_text(json.dumps(delta, indent=1))
    print(f"RF_KV3_PLAN pins {done} hard_cores {len(delta['hard_cores'])} taps {len(delta['clock_taps'])}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
