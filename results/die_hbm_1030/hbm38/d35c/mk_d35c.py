#!/usr/bin/env python3
"""DIE-HBM-38: pin-only plan event d35c = d35b + (1) SU lane_exp0_id load-side control pins + (2) RING signed-view pins
(COORD 13:0x: HBM-CORES-KITS-28 ASK 12:50 (A) APPROVED; RING option (b) per KITS-28 FINDING 13:03).
(1) ot_hbm_su_static_pgslice_lg__lane_exp0_id (414.72x207.36, outline unchanged; 4 hard_cores entries q_su00/q_su10 +
    physical_v1): g_lane_0_g_plain_u_lane_emit / _lane_ld / _lane_ld_bank move along the S face (M5, y 0.096) from the
    SW corner (x 11.112/12.12/13.128) into the free M5 tracks nearest x~320 (the 4-bit s_q register's p2 load field
    x 340-405 / y 40-200; r2r 576 um > 405 in kit _k27a). Every other pin byte-identical; new file ..__d35c.json.
(2) ot_hfd_coll_q2_hard_v8g__ring_ag (q_hub_nw/ne): pins_file ..__c25c_centerclk__codex_g21.json (clk at the N face,
    contradicting clock_entries centre 116.64 + the entry note) -> the sibling ..__c25c_centerclk.json (sha bb7960a3d6b9,
    clk centre 116.664,116.64 = signed ring_wl120 view, pincmp 2228/2228 + 12 only-view FT ports); the 12 island FT
    ports go to a die-owned FT sidecar (core_die_owned_ft.v1, as the collar d35b).
usage: mk_d35c.py BASE OUT RING_DEF RING_FT_PORTS_JSON"""
import hashlib, json, re, subprocess, sys
from pathlib import Path
base, out, dv, ftj = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
if out.exists(): sys.exit(f"{out} exists")
SU = "ot_hbm_su_static_pgslice_lg__lane_exp0_id"
SU_OLD = "cores/ot_hbm_su_static_pgslice_lg__lane_exp0_id__414.72x207.36__d35a.json"
SU_NEW = "cores/ot_hbm_su_static_pgslice_lg__lane_exp0_id__414.72x207.36__d35c.json"
RING = "ot_hfd_coll_q2_hard_v8g__ring_ag"
R_OLD = "cores/ot_hfd_coll_q2_hard_v8g__ring_ag__233.28x233.28__q_hub_u_hb_coll_Q_ring_ag__oneclk__c25c_centerclk__codex_g21.json"
R_NEW = "cores/ot_hfd_coll_q2_hard_v8g__ring_ag__233.28x233.28__q_hub_u_hb_coll_Q_ring_ag__oneclk__c25c_centerclk.json"
R_SIDE = "cores/ot_hfd_coll_q2_hard_v8g__ring_ag__233.28x233.28__d35c_die_owned_ft.json"
subprocess.check_call(["cp", "-al", str(base), str(out)])
def wnew(rel, obj):
    p = out / rel
    if p.exists() or p.is_symlink(): p.unlink()
    p.write_text(json.dumps(obj, indent=1) + "\n")
sha = lambda p: hashlib.sha256((out / p).read_bytes()).hexdigest()
# (1) SU pins
pins = json.load(open(base / SU_OLD))
MOVE = ["g_lane_0_g_plain_u_lane_emit", "g_lane_0_g_plain_u_lane_ld", "g_lane_0_g_plain_u_lane_ld_bank"]
S = sorted(p["x"] for p in pins if p["layer"] == "M5" and abs(p["y"] - 0.096) < 1e-6 and p["name"] not in MOVE)
TR0, TP, MIN = 0.024, 0.048, 0.48            # M5 track grid; keep >= 10 tracks from any other S pin
cands = []
for k in range(int(250 / TP), int(400 / TP)):
    x = round(TR0 + k * TP, 3)
    if min(abs(x - s) for s in S) >= MIN - 1e-9: cands.append(x)
cands.sort(key=lambda x: abs(x - 320.0))
pick = []
for x in cands:
    if all(abs(x - q) >= MIN for q in pick): pick.append(x)
    if len(pick) == 3: break
pick.sort()
assert len(pick) == 3, cands[:10]
moved = {}
newp = []
for q in pins:
    q = dict(q)
    if q["name"] in MOVE:
        x = pick[MOVE.index(q["name"])]
        moved[q["name"]] = [[q["x"], q["y"]], [x, q["y"]]]
        q["x"] = x
        q["note"] = "d35c: moved from the SW corner to the S-face load side (KITS-28 ASK 12:50 (A), r2r 576 um)"
    newp.append(q)
wnew(SU_NEW, newp)
# (2) RING sidecar from the signed view DEF
t = dv.read_text()
u = float(re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)", t).group(1))
sec = re.search(r"^\s*PINS\s+\d+\s*;(.*?)^\s*END\s+PINS", t, re.S | re.M).group(1)
view = {}
for st in sec.split(";"):
    st = st.strip()
    if not st.startswith("-"): continue
    n = st[1:].split()[0].replace("\\", "")
    d = re.search(r"DIRECTION\s+(\S+)", st)
    ly = re.search(r"LAYER\s+(\S+)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)", st)
    pl = re.search(r"(?:PLACED|FIXED)\s*\(\s*(-?\d+)\s+(-?\d+)\s*\)", st)
    if ly and pl:
        x, y = int(pl.group(1)) / u, int(pl.group(2)) / u
        r = [int(ly.group(i)) / u for i in (2, 3, 4, 5)]
        view[n] = dict(layer=ly.group(1), dir=d.group(1) if d else None,
                       rect=[round(x + r[0], 4), round(y + r[1], 4), round(x + r[2], 4), round(y + r[3], 4)])
ft = json.load(open(ftj))
# (plan edits)
plan = json.load(open(base / "die_plan.json"))
ns = nr = 0
for tn, ty in plan["partition_types"].items():
    for h in ty.get("hard_cores", []):
        if h.get("module") == SU:
            assert h["pins_file"] == SU_OLD; h["pins_file"] = SU_NEW; ns += 1
            h["note"] = h.get("note", "") + " | DIE-HBM-38 d35c: lane_emit/lane_ld/lane_ld_bank S pins at the load side"
        if h.get("module") == RING:
            assert h["pins_file"] == R_OLD; h["pins_file"] = R_NEW; nr += 1
            h["note"] = h.get("note", "") + " | DIE-HBM-38 d35c: pins = c25c_centerclk (clk centre = clock entry = signed ring_wl120 view); 12 island FT ports in die-owned sidecar"
assert ns == 4 and nr == 2, (ns, nr)
wnew("die_plan.json", plan)
side = {"schema": "opentallas.core_die_owned_ft.v1", "module": RING, "plan": "die_plan.json (HBM d35c)",
        "plan_sha256": sha("die_plan.json"), "plan_core_pins": R_NEW, "plan_core_pins_sha256": sha(R_NEW),
        "outline_um": [233.28, 233.28], "core_signal_pins": len(json.load(open(out / R_NEW))),
        "die_owned_ft_pins": [dict(name=p["name"], direction=view[p["name"]]["dir"], layer=view[p["name"]]["layer"],
                                   rect_um=view[p["name"]]["rect"]) for p in ft["ports"]],
        "ft_declaration": {"source": f"hbm-cores-kits-27/ring_wl120 ft_ports.json (opentallas.ft_ports.v1, sha {hashlib.sha256(ftj.read_bytes()).hexdigest()[:8]})",
                           "arcs": ft["arcs"], "note": "in-core clock/reset island feedthroughs (3 islands); die-owned, not core signal pins"},
        "signed_view": {"def": str(dv)}}
wnew(R_SIDE, side)
print(json.dumps({"su_moved": moved, "su_pins_sha256": sha(SU_NEW), "ring_pins": R_NEW, "ring_pins_sha256": sha(R_NEW),
                  "ring_sidecar_sha256": sha(R_SIDE), "die_plan_sha256": sha("die_plan.json")}, indent=1))
