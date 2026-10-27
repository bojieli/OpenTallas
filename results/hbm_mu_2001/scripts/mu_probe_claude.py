#!/usr/bin/env python3
"""HBM-MU-SIZE probe (read-only plan arithmetic, UNCHECKED): R11 planA2 hub evaluation with MU (P=3, 4 users) deltas.
MU model per hub (inferred from hbm_next fork unit READMEs, see lane note):
  coll   : stations touching COLL delivery cores x1.25 bits (L=5 vs 4); COLL q3/q2 core widths x1.25
  vm     : VM records +1 sector bit (x(1+1/257)); vms_bank outline height 313.2 -> 561.6 (7 macros: A0..A3,C,B0,B1 for 2^19)
  fused  : 8 hnx_fused_lane (345.6 x 518.4) per hub, each rd 257 + wr 282 + rq 18 b to the hub VM glue
  idxn   : 2 key buffers (324 x 324) per hub, 2 x 256 b to the idx query core
Usage: mu_probe.py TOOLS PLAN_DIR MODE H1[,H2..] [bound_nw,bound_ne|search]
"""
import json, math, re, sys, copy
sys.path.insert(0, sys.argv[1])
import hbm_r11_delta as R11

MODE = sys.argv[3]
HS = [float(h) for h in sys.argv[4].split(",")]
BOUNDS = None if len(sys.argv) < 6 or sys.argv[5] == "search" else [float(x) for x in sys.argv[5].split(",")]
COLL = re.compile(r"u_hb_coll_|u_hcollg")
VM = re.compile(r"u_vmb_|u_vmks_|u_hb_vms_|u_vmdel_|u_smw_|u_calendar_")


def onedge(h, side):
    x, y = h["origin_um"]; w, hh = h["outline_um"]
    return {"N": [x + w / 2, y + hh], "S": [x + w / 2, y], "W": [x, y + hh / 2], "E": [x + w, y + hh / 2]}[side]


def patch(t1):
    hc = t1["hard_cores"]; st = t1["internal_stations"]
    byn = {h["inst"]: h for h in hc}
    add = dict(coll_bits=0, vm_bits=0, fused_bits=0, idxn_bits=0, area_um2=0.0)
    if "coll" in MODE or "all" in MODE:
        for s in st:
            if COLL.search(str(s.get("launch", ""))) or COLL.search(str(s.get("capture", ""))):
                nb = int(math.ceil(s["bits"] * 1.25)); add["coll_bits"] += nb - s["bits"]; s["bits"] = nb
        for h in hc:
            if re.search(r"u_hb_coll_", h["inst"]):
                w, hh = h["outline_um"]; nw = round(math.ceil(w * 1.25 / 4.32) * 4.32, 3)
                add["area_um2"] += (nw - w) * hh; h["outline_um"] = [nw, hh]
    if "vm" in MODE or "all" in MODE:
        for s in st:
            if VM.search(str(s.get("launch", ""))) or VM.search(str(s.get("capture", ""))):
                nb = int(math.ceil(s["bits"] * (1 + 1 / 257))); add["vm_bits"] += nb - s["bits"]; s["bits"] = nb
        for h in hc:
            if h["inst"].startswith("u_vmb_"):
                w, hh = h["outline_um"]; add["area_um2"] += w * (561.6 - hh); h["outline_um"] = [w, 561.6]
    glue = sorted([h for h in hc if h["inst"].startswith("u_hb_vms_")], key=lambda h: h["inst"])
    if ("fused" in MODE or "all" in MODE) and glue:
        for i in range(8):
            g = glue[i % len(glue)]
            o = [g["origin_um"][0] + (i // len(glue)) * 345.6, g["origin_um"][1]]
            h = dict(inst=f"u_mu_fused_{i}", module="hnx_fused_lane", origin_um=o, outline_um=[345.6, 518.4],
                     track_offset_um=[0, 0], pins_file=None, note="MU probe")
            hc.append(h); add["area_um2"] += 345.6 * 518.4
            for nm, b, a_, c_ in (("rd", 257, g, h), ("wr", 282, h, g), ("rq", 18, h, g)):
                st.append(dict(conn=f"{a_['inst']}.{nm}|{c_['inst']}", launch=f"{a_['inst']}.{nm}", capture=c_["inst"],
                               bits=b, from_um=onedge(a_, "E"), to_um=onedge(c_, "W"), regs_um=[]))
                add["fused_bits"] += b
    iq = sorted([h for h in hc if h["inst"].startswith("u_hb_idx__q_Q")], key=lambda h: h["inst"])
    if ("idxn" in MODE or "all" in MODE) and iq:
        for i, q in enumerate(iq):
            h = dict(inst=f"u_mu_keybuf_{i}", module="hnx_idxn_keybuf", origin_um=[q["origin_um"][0], q["origin_um"][1]],
                     outline_um=[324.0, 324.0], track_offset_um=[0, 0], pins_file=None, note="MU probe")
            hc.append(h); add["area_um2"] += 324.0 * 324.0
            for nm, a_, c_ in (("kin", q, h), ("kout", h, q)):
                st.append(dict(conn=f"{a_['inst']}.{nm}|{c_['inst']}", launch=f"{a_['inst']}.{nm}", capture=c_["inst"],
                               bits=256, from_um=onedge(a_, "E"), to_um=onedge(c_, "W"), regs_um=[]))
                add["idxn_bits"] += 256
    return add


_orig = R11.prepare
ADD = {}


def prepare(P, part, tn, cap, spread):
    t, W, H0, t1, lrep = _orig(P, part, tn, cap, spread)
    t1 = copy.deepcopy(t1)
    ADD[tn] = patch(t1)
    core = sum(h["outline_um"][0] * h["outline_um"][1] for h in t1["hard_cores"])
    ADD[tn]["core_area_mm2_after"] = round(core / 1e6, 3)
    return t, W, H0, t1, lrep


R11.prepare = prepare
P = json.load(open(sys.argv[2] + "/die_plan.json"))
hubs = [("NW_hub", "q_hub_nw"), ("NE_hub", "q_hub_ne")]
out = []
for H in HS:
    row = dict(mode=MODE, H=H, hubs={})
    for i, (part, tn) in enumerate(hubs):
        try:
            cores, st, res = R11.run_hub(P, part, tn, H, None if BOUNDS is None else BOUNDS[i], 6.0, 3.0, 2, 1000.0, 8,
                                         route=False, jobs=48, log=lambda *a: None)
            c = res["cut_per_sink_blocked"]
            row["hubs"][tn] = dict(bound=res["bound_um"], k=res["k"], x=c["x"]["max_use"], y=c["y"]["max_use"],
                                   seg=[(s["cut_x"], s["cut_y"]) for s in res["segments"]], fill=res["segment_fill"],
                                   cc=res["cc_serialised"], add=ADD.get(tn),
                                   ok=max(c["x"]["max_use"], c["y"]["max_use"], *[s["cut_y"] or 0 for s in res["segments"]]) <= 0.6 + 1e-9)
        except Exception as e:  # packing failure etc.
            row["hubs"][tn] = dict(error=repr(e)[:300], add=ADD.get(tn))
    print(json.dumps(row), flush=True)
