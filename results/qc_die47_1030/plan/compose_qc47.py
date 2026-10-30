"""DIE-QC-47 plan_qc47 = plan_qc46 + PHY clock entry at the native clock pin + PHY body clock keep-outs.

Why: the reach-safe die clock GEN on plan_qc45 (Codex 06:32, tree 8f728d09) put 89 clock cells inside 5 native PHY
bodies, because (1) the PHY types' clock tap is the slot centre (inside the bare macro) and (2) bare PHY slots carry no
hard_cores, so SiteMap saw them as free area. Fix (plan data only; no pin, outline, port or cycle change):
  * clock.keepouts_um = the native body rectangle (type frame) of every PHY type; die_trial --clock-type-keepouts
    (DIE-QC-47 opt-in) forbids those rectangles + 2.16 um halo for die clock cells.
  * PHY clock tap = the native M5 clk pin centre (native LEF, Codex phy_native_impact.json views/instances).
  * phy_serdes native body sits at y +4.104 in its 2324.16 slot (Codex body_packing_review_option): io_serdes_2 /
    io_serdes_1 body gap 4.104 -> 8.208 um, 3.888 um free after both 2.16 halos = a clock row next to the io_serdes_2
    clk pin. io_serdes (MX) then has its body flush with the slot S edge and its clk pin facing the channel below.
  * coll_ucie: u_io_ucie.ck core tap -> native clk pin; glue_00 tap (inside the UCIe body) -> just above the body.
"""
import hashlib, json, sys
src, dst = sys.argv[1], sys.argv[2]
P = json.load(open(src))
T = P["partition_types"]
SER_W, SER_H = 1563.57, 2320.056          # ot_qfd_serdes_112g_x12_phy_s597.lef SIZE (sha 4c62ffde)
SER_CLK = (753.018, 2319.96)              # native M5 clk centre, body frame
UC = 777.6
log = []
def setk(t, rect, tap):
    ck = T[t].setdefault("clock", {})
    old = (list(ck.get("tap_um", [])), list(ck.get("keepouts_um", [])))
    ck["keepouts_um"] = [rect]
    if tap is not None:
        ck["tap_um"] = [round(tap[0], 4), round(tap[1], 4)]
    log.append(dict(type=t, old_tap=old[0], new_tap=ck.get("tap_um"), keepout=rect))
dy = 4.104
setk("phy_serdes", [0.0, dy, SER_W, round(dy + SER_H, 4)], (SER_CLK[0], SER_CLK[1] + dy))

setk("phy_serdes_b", [0.0, 0.0, SER_W, SER_H], SER_CLK)

setk("phy_ucie_kv", [0.0, 0.0, UC, UC], (276.396, 777.504))      # ot_qkvd_ucie_x64_phy clk, N face
cu = T["coll_ucie"]["clock"]
setk("coll_ucie", [0.0, 0.0, UC, UC], None)
tx, ty = cu["tap_um"]
for tp in cu.get("taps", []):
    if tp["name"] == "u_io_ucie.ck":
        tp["xy"] = [188.844, 777.504]                               # ot_qfd_ucie_x64_phy clk, N face
    elif tp["name"] == "glue_00":
        tp["xy"] = [388.8, 803.52]                                  # was (388.8, 406.08) inside the PHY body
    else:
        continue
    tp["from_root_um"] = round(abs(tp["xy"][0] - tx) + abs(tp["xy"][1] - ty), 3)
    log.append(dict(type="coll_ucie", tap=tp["name"], xy=tp["xy"], from_root_um=tp["from_root_um"]))
P.setdefault("note", "")
P["note"] = (P["note"] + " | " if P["note"] else "") + "plan_qc47 (DIE-QC-47): plan_qc46 + PHY native clock entry + PHY body clock keep-outs"
txt = json.dumps(P, indent=1)
open(dst, "w").write(txt + "\n")
print(json.dumps(dict(src_sha256=hashlib.sha256(open(src, "rb").read()).hexdigest(),
                      dst_sha256=hashlib.sha256(open(dst, "rb").read()).hexdigest(), changes=log), indent=1))
