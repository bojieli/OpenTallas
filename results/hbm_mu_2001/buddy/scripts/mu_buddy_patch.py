#!/usr/bin/env python3
"""HBM-MU-SIZE probe (read-only plan arithmetic, UNCHECKED): R11 planA2 hub evaluation with MU (P=3, 4 users) deltas.
MU model per hub (inferred from hbm_next fork unit READMEs, see lane note):
  coll   : stations touching COLL delivery cores x1.25 bits (L=5 vs 4); COLL q3/q2 core widths x1.25
  vm     : VM records +1 sector bit (x(1+1/257)); vms_bank outline height 313.2 -> 403.92 (7 macros: A0..A3,C,B0,B1 for 2^19)
  fused  : 8 hnx_fused_lane (345.6 x 518.4) per hub, each rd 257 + wr 282 + rq 18 b to the hub VM glue
  idxn   : 2 key buffers (324 x 324) per hub, 2 x 256 b to the idx query core
Usage: mu_probe.py TOOLS PLAN_DIR MODE H1[,H2..] [bound_nw,bound_ne|search]
"""
import json, math, re, sys, copy
sys.path.insert(0, sys.argv[1])
import hbm_r11_delta as R11

MODE = "vm_fused_idxn"
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
                w, hh = h["outline_um"]; add["area_um2"] += w * (403.92 - hh); h["outline_um"] = [w, 403.92]
    # Native MU: 32 physical VM banks total, four macros/bank, one per FUSED lane.
    # Existing station/pin tables remain diagnostic geometry; native bind is not claimed.
    for h in list(hc):
        if h["inst"].startswith("u_vmb_"):
            h["module"]="hnx_vms_bank_q0_faces"
            clone=copy.deepcopy(h);clone["inst"]=h["inst"]+"_mu1"
            clone["pins_file"]=None
            hc.append(clone);add["area_um2"]+=clone["outline_um"][0]*clone["outline_um"][1]
    glue = sorted([h for h in hc if h["inst"].startswith("u_vmb_")], key=lambda h: h["inst"])
    if ("fused" in MODE or "all" in MODE) and glue:
        for i in range(16):
            g = glue[i % len(glue)]
            o = [g["origin_um"][0] + (i // len(glue)) * 345.6, g["origin_um"][1]]
            h = dict(inst=f"u_mu_fused_{i}", module="hnx_fused_lane", origin_um=o, outline_um=[345.6, 518.4],
                     track_offset_um=[0, 0], pins_file=None, note="MU probe")
            hc.append(h); add["area_um2"] += 345.6 * 518.4
            for nm, b, a_, c_ in (("rd", 257, g, h), ("wr", 282, h, g), ("rq", 18, h, g)):
                st.append(dict(conn=f"{a_['inst']}.{nm}|{c_['inst']}", launch=f"{a_['inst']}.{nm}", capture=c_["inst"],
                               bits=b, from_um=onedge(a_, "W" if a_["inst"].startswith("u_mu_fused_") and c_["inst"].startswith("u_vmb_") else "E"), to_um=onedge(c_, "E" if a_["inst"].startswith("u_mu_fused_") and c_["inst"].startswith("u_vmb_") else "W"), regs_um=[]))
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
    # Actual external FUSED tree: two groups of eight lanes per hub, seven
    # 172.8-square nodes/group; all 271-bit up and 173-bit down edges retained.
    # One 345.6-square ot_hnx_fused_hub is reserved in the central root OUTSIDE
    # this per-hub probe. Each quadrant root crosses the hub face to that root.
    add["tree_nodes"] = 0
    add["tree_bits"] = 0
    banknodes = {h["inst"]:h for h in hc}
    def tree_link(child,parent,slot):
        for nm,b,a_,c_ in (("up",271,child,parent),("down",173,parent,child)):
            ap=onedge(a_,"E");cp=onedge(c_,"W")
            # Each kept child down copy is a distinct source port, as native RTL.
            port=("da" if slot==0 else "db") if nm=="down" else "uo"
            st.append(dict(conn=f"mu_tree:{a_['inst']}.{port}|{c_['inst']}",launch=f"{a_['inst']}.{port}",capture=(f"{c_['inst']}."+("ua" if slot==0 else "ub")) if nm=="up" else f"{c_['inst']}.dn",bits=b,from_um=ap,to_um=cp,regs_um=[]))
            add["tree_bits"]+=b
    def node(name,aa,bb):
        na,nb=banknodes[aa],banknodes[bb]
        x=(na["origin_um"][0]+nb["origin_um"][0])/2
        y=(na["origin_um"][1]+nb["origin_um"][1])/2
        h=dict(inst=name,module="ot_hnx_fused_tnode",origin_um=[x,y],outline_um=[172.8,172.8],track_offset_um=[0,0],pins_file=None,note="MU FUSED native binary tree model")
        hc.append(h);banknodes[name]=h;add["area_um2"]+=172.8**2;add["tree_nodes"]+=1
        tree_link(na,h,0);tree_link(nb,h,1)
        return name
    for q in range(2):
        names=[]
        for g in range(4):
            names.append(node(f"u_mu_fused_n1_q{q}_{g}",f"u_mu_fused_{q*8+2*g}",f"u_mu_fused_{q*8+2*g+1}"))
        l=node(f"u_mu_fused_n2L_q{q}",names[0],names[1])
        r=node(f"u_mu_fused_n2R_q{q}",names[2],names[3])
        top=banknodes[node(f"u_mu_fused_n3_q{q}",l,r)]
        # Both hubs' transport must include the real per-quadrant up/down lanes
        # before claiming that the central-root tree fits the die.
        face=[t1["outline_um"][0] if t1.get("_mu_hub_type")=="q_hub_nw" else 0.0,t1["outline_um"][1]/2]
        for nm,b,a_,c_ in (("up",271,onedge(top,"E"),face),("down",173,face,onedge(top,"W"))):
            st.append(dict(conn=f"mu_tree_root:{q}:{nm}",launch=(f"{top['inst']}.uo" if nm=="up" else f"face root.dn{q}"),capture=(f"face root.up{q}" if nm=="up" else f"{top['inst']}.dn"),bits=b,from_um=a_,to_um=c_,regs_um=[]))
            add["tree_bits"]+=b
    add["global_root_reserve_mm2_outside_hub"]=345.6**2/1e6
    return add


_orig = R11.prepare
ADD = {}


def prepare(P, part, tn, cap, spread):
    t, W, H0, t1, lrep = _orig(P, part, tn, cap, spread)
    t1 = copy.deepcopy(t1)
    t1["_mu_hub_type"] = tn
    ADD[tn] = patch(t1)
    core = sum(h["outline_um"][0] * h["outline_um"][1] for h in t1["hard_cores"])
    ADD[tn]["core_area_mm2_after"] = round(core / 1e6, 3)
    return t, W, H0, t1, lrep


R11.prepare = prepare
P = json.load(open(sys.argv[2] + "/die_plan.json"))
hubs = [("NW_hub", "q_hub_nw"), ("NE_hub", "q_hub_ne")]
out = []
for H in HS:
    row = dict(mode=MODE, fused_lanes_per_hub=16, fused_topology="bank-local, 32 FUSED and 32 physical VM banks, 4 macros/bank, native bind UNQUALIFIED; full14local tnodes/hub plus root-face888bits; rootbodyoutsidehub; buddy W/E repin/rekit REQUIRED", H=H, hubs={})
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
