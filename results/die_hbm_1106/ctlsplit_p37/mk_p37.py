#!/usr/bin/env python3
"""HBM-FORM-TIMING-11 d44v part 38 (COORD 11-06 10:2x + 11:21 (2)): split3__ctl -> rest + pipe hard cores.

u_sfucore_Q_ctl (ot_hgi_sfu_core_split3__ctl, 427.68 x 453.6, MY) becomes
  u_sfucore_Q_ctl__rest  ot_hgi_sfu_split3_ctl_rest_1c  SAME slot, origin, orient, track offset, pins (all 11,813 plan pins
                         at their sites) + 560 seam pins (seam_d[279:0] out, seam_q[279:0] in) on its local E face, which
                         is the die-W face under MY;
  u_sfucore_Q_ctl__pipe  ot_hgi_sfu_split3_ctl_pipe_1c  NEW slot 172.8 x 151.2 (R0) in the free parent space W of the rest
                         slot (die x 328.32..501.12, y 1019.52..1170.72; 8.544 street to the rest box), seam pins on its E
                         face at the SAME die y as the rest seam pins (straight 8.6-um hops, FF->FF, zero logic),
                         rst_n / rst_lg_n[3:0] on the same face above them, clk at the centre entry (4.32 PG lattice).
Same related clock (one plan tap per core, same insertion target as the ctl tap); the pipe keeps its own copy of the ctl
reset synchroniser (rst_n -> 2-flop sync -> relay), so no reset crosses the seam.  core_conns: rest = old ctl rows +
seam -> pipe; pipe = clk tap, rst_n / rst_lg_n = the ctl rows, seam -> rest; every core:u_sfucore_Q_ctl -> __rest;
stations repointed to __rest.  Both plan types that hold the ctl (q_b113, q_b113__physical_v1).
    mk_p37.py PLAN_DIR   (unpacked d44v: die_plan.json, core_conns.json, clock_entries.json, core_macros.json, cores/)"""
import json, re, sys
from pathlib import Path
d = Path(sys.argv[1])
SRC = {n: (d / n).read_text() for n in ("die_plan.json", "core_conns.json", "clock_entries.json", "core_macros.json")}
P = json.loads(SRC["die_plan.json"]); CC = json.loads((d / "core_conns.json").read_text())
CE = json.loads((d / "clock_entries.json").read_text()); CM = json.loads((d / "core_macros.json").read_text())
I, OLDM = "u_sfucore_Q_ctl", "ot_hgi_sfu_core_split3__ctl"
RI, PI = I + "__rest", I + "__pipe"
RM, PM = "ot_hgi_sfu_split3_ctl_rest_1c", "ot_hgi_sfu_split3_ctl_pipe_1c"
PO, PWH = [328.32, 1019.52], [172.8, 151.2]
PG, PITCH, OFF, EDGE = 4.32, 0.048, 0.024, 0.096
r3 = lambda v: round(v + 0.0, 3)
NOTE = "HBM-FORM-TIMING-11 d44v part 38 (COORD 11-06 10:2x/11:21): split3__ctl rest+pipe (I205 delay-line cut, 0 cycles; glue results/die_hbm_1106/ctlsplit_p37/ot_hgi_sfu_core_split3__ctl__p37glue.sv)"
# ---------------------------------------------------------------- pins
old = next(h for t in P["partition_types"].values() for h in t.get("hard_cores") or [] if h["inst"] == I)
assert old["module"] == OLDM and old.get("orient") == "MY", old
W, H = old["outline_um"]
OP = json.loads((d / old["pins_file"]).read_text())
assert len(OP) == 11813, len(OP)
# rest local E face (x = W - EDGE, M4): seam sites over the pipe's die-y span, interleaved d/q by bit, on free M4 tracks
ylo, yhi = PO[1] - old["origin_um"][1] + PG + 1.0, PO[1] - old["origin_um"][1] + PWH[1] - PG - 6.0   # top 6 um: pipe resets
used = sorted(p["y"] for p in OP if p["layer"] == "M4" and abs(p["x"] - (W - EDGE)) < 0.01)
trk = lambda v: round(OFF + round((v - OFF) / PITCH) * PITCH, 3)
import bisect
def free(y, k=2):
    i = bisect.bisect_left(used, y - k * PITCH + 1e-6)
    return not (i < len(used) and used[i] <= y + k * PITCH - 1e-6)
cands = [y for y in (trk(ylo + j * PITCH) for j in range(int((yhi - ylo) / PITCH))) if free(y)]
names = [n for i in range(280) for n in (f"seam_d[{i}]", f"seam_q[{i}]")]
step = len(cands) / len(names); assert step >= 2, (len(cands), "free M4 tracks for 560 seam pins")
sel = [cands[int(i * step)] for i in range(len(names))]
assert all(b - a >= 2 * PITCH - 1e-6 for a, b in zip(sel, sel[1:])), "seam pins closer than 2 tracks (p34 rule)"
rest_pins = OP + [dict(name=n, layer="M4", x=r3(W - EDGE), y=y) for n, y in zip(names, sel)]
# pipe: R0, local E face at die x = PO.x + 172.8 faces the rest; die y of a rest pin = origin_y + y (MY keeps y)
dy = old["origin_um"][1] + old.get("track_offset_um", [0, 0])[1] - PO[1]
pw, ph = PWH
pipe_pins = [dict(name=n, layer="M4", x=r3(pw - EDGE), y=r3(y + dy)) for n, y in zip(names, sel)]
rtop = [trk(ph - PG - 5.0 + j * 0.96) for j in range(5)]
pipe_pins += [dict(name=n, layer="M4", x=r3(pw - EDGE), y=y) for n, y in zip(["rst_n"] + [f"rst_lg_n[{i}]" for i in range(4)], rtop)]
ex, ey = round(round(pw / 2 / PG) * PG, 3), round(round(ph / 2 / PG) * PG, 3)
pipe_pins.append(dict(name="clk", layer="M5", x=r3(ex + OFF), y=ey, w=0.048, h=0.48))
assert all(PG <= p["y"] <= ph - PG for p in pipe_pins), "pipe pin outside the inset"
assert len({p["y"] for p in pipe_pins if p["name"] != "clk"}) == 565
RPF = f"cores/{RM}__{W}x{H}__d44v_split.json"; PPF = f"cores/{PM}__{pw}x{ph}__d44v_split.json"
(d / RPF).write_text(json.dumps(rest_pins, indent=1) + "\n"); (d / PPF).write_text(json.dumps(pipe_pins, indent=1) + "\n")
# ---------------------------------------------------------------- plan swap
ev = dict(schema="opentallas.hbm_plan_event.v1", event="part38", lane="HBM-FORM-TIMING-11", note=NOTE, types=[],
          designs_removed=[OLDM], designs_added=[RM, PM], added_cycles="0 (seam = FF->FF registers of the uncut core; pipe keeps a local copy of the 2-flop reset sync + relay)",
          rest=dict(inst=RI, module=RM, pins_file=RPF, pins=len(rest_pins), seam_y_um=[sel[0], sel[-1]]),
          pipe=dict(inst=PI, module=PM, origin_um=PO, outline_um=PWH, pins_file=PPF, pins=len(pipe_pins), clock_entry_um=[ex, ey]))
box = (PO[0], PO[1], PO[0] + pw, PO[1] + ph)
def ovl(a, b): return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
rx = lambda s: re.sub(r"\b" + I + r"\b(?!__)", RI, s)
for tn, T in P["partition_types"].items():
    hc = T.get("hard_cores") or []
    k = next((i for i, h in enumerate(hc) if h["inst"] == I), None)
    if k is None:
        continue
    o = hc.pop(k)
    TW, TH = T["outline_um"]
    assert box[0] >= 0 and box[1] >= 0 and box[2] <= TW and box[3] <= TH
    for h in hc + T.get("contents", [])[1:]:
        hb = (h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1])
        assert not ovl(box, (hb[0] - 8.64, hb[1] - 8.64, hb[2] + 8.64, hb[3] + 8.64)), (tn, h.get("inst"), "pipe slot overlaps / no street")
    rb = (o["origin_um"][0] + o["track_offset_um"][0], o["origin_um"][1], o["origin_um"][0] + W, o["origin_um"][1] + H)
    assert rb[0] - box[2] >= 8.5, (rb, box)
    r = dict(o, inst=RI, module=RM, pins_file=RPF, physical_inst=f"{I}.u_fcore.u_core.u_rest", physical_master=RM,
             note=NOTE + " | rest sub-core (was " + o["note"][:300] + ")")
    p = dict(inst=PI, module=PM, origin_um=list(PO), outline_um=list(PWH), track_offset_um=[0.0, 0.0], pins_file=PPF,
             physical_inst=f"{I}.u_fcore.u_core.u_pipe", physical_master=PM, note=NOTE + " | pipe sub-core (21,816 delay-line flops + local reset sync)", obs_max=o.get("obs_max", "M5"))
    hc[k:k] = [r, p]
    nst = 0
    for s in T.get("internal_stations") or []:
        for f in ("launch", "capture", "conn"):
            if isinstance(s.get(f), str):
                v = rx(s[f]); nst += v != s[f]; s[f] = v
        for rg in s.get("regs_um") or []:
            assert not (box[0] - 1 < rg[0] < box[2] + 1 and box[1] - 1 < rg[1] < box[3] + 1), (tn, s.get("conn"), rg, "station register in the pipe slot")
    taps = T["clock"]["taps"]
    ot = next(tp for tp in taps if tp["name"] == I)
    ot.update(name=RI, budget_owner=RM, note=NOTE + " | rest tap (was " + I + ") | " + ot.get("note", "")[:200])
    taps.append(dict({k_: v_ for k_, v_ in ot.items() if k_ not in ("merged_clock_ports",)}, name=PI, xy=[r3(PO[0] + ex), r3(PO[1] + ey)],
                     budget_owner=PM, note=NOTE + " | pipe tap: centre entry, same insertion target as the ctl tap"))
    ce = CE[tn]; oe = ce.pop(I)
    ce[RI] = dict(oe, tap=RI, module=RM, native_module=RM, source=oe.get("source", "") + " | " + NOTE)
    ce[PI] = {k_: v_ for k_, v_ in oe.items() if k_ not in ("xy_um", "island_um", "port", "merged_clock_ports", "tap", "module", "native_module", "clock_bind_contract")}
    ce[PI].update(xy_um=[ex, ey], island_um=[r3(ex - PG), r3(ey - PG), r3(ex + PG), r3(ey + PG)], port="clk", merged_clock_ports=[],
                  tap=PI, module=PM, native_module=PM, source=NOTE + " | pipe centre entry (4.32 PG lattice)")
    cc = CC[tn]; oc = cc.pop(I)
    rc = {k_: [("tap:" + RI if x == "tap:" + I else x) for x in v_] for k_, v_ in oc.items()}
    rc["seam_d"] = ["core:" + PI]; rc["seam_q"] = ["core:" + PI]
    cc[RI] = rc
    cc[PI] = dict(clk=["tap:" + PI], seam_d=["core:" + RI], seam_q=["core:" + RI])
    cc[PI].update({k_: list(oc[k_]) for k_ in ("rst_n", "rst_lg_n") if k_ in oc})   # the ctl has no rst rows (partition reset tree), so neither does the pipe
    nref = 0
    for ci, ports in cc.items():
        for lp, lst in ports.items():
            if "core:" + I in lst:
                ports[lp] = sorted((set(lst) - {"core:" + I}) | {"core:" + RI}); nref += 1
    ev["types"].append(dict(type=tn, stations_repointed=nst, core_conn_refs_repointed=nref, rest_box_um=[r3(v) for v in rb], pipe_box_um=[r3(v) for v in box],
                            rst_rows={k_: oc.get(k_) for k_ in ("rst_n", "rst_lg_n")}))
assert len(ev["types"]) == 2, ev["types"]
mc = CM["cores"][OLDM]
CM["cores"][RM] = dict(mc, note=(mc.get("note") or "") + " | " + NOTE)
CM["cores"][PM] = dict(status="NONE", outline_um=list(PWH), basis="no macros (flops only)", macros=[], note=NOTE)
for f, o in (("die_plan.json", P), ("core_conns.json", CC), ("clock_entries.json", CE), ("core_macros.json", CM)):
    t = SRC[f]   # keep the layout of each file (die_plan / clock_entries compact, the others indent 1): the git diff is the event only
    (d / f).write_text(json.dumps(o, indent=1 if t.startswith("{\n") else None) + ("\n" if t.endswith("\n") else ""))
(d / "part38_event.json").write_text(json.dumps(ev, indent=1) + "\n")
print("part38", [(t["type"], t["stations_repointed"], t["core_conn_refs_repointed"]) for t in ev["types"]], "seam y", sel[0], sel[-1], "rest pins", len(rest_pins), "pipe pins", len(pipe_pins))
