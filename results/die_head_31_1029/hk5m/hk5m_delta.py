#!/usr/bin/env python3
"""DIE-HEAD-31 fix-only plan delta hk5m on hk5l (COORD 14:5x approved class B default (A) + class A estimate).
1. hd_tile cland_tstart_in (landing_contract pin + clock.start_capture_um) (362.4,354.208) -> (518.4,862.944) (E strip x 501-708, clear of eB 216-501 x 734-1020): the
   START capture pin joins the landing scalars in the hk5 band (strap_pad 0: s1 drives fstart_o directly, so s1 must be
   within 405 um of both the tstart pin reg and the E fstart pin; 857 > 810 from the tile centre).
2. o/i status bits to the band BOTTOM: every window of the 565-bit hd_tile i/o abutment group (hd_tile i/o, 4 spine
   shim link slots, hd_turn_a / hd_turn_b t slots, hd_spn / hd_spn_end be_i/bw_i/xe_o/xw_o) lsb_low -> lsb_high, the
   same permutation on every member, so every abutting pair stays bit-aligned.  Bits 512..564 land at the band bottom
   (next to the core status launchers at y~717); data bits 0..511 mirror (est. worst data r2r 278.5 -> 308.8).
0 cycles, 0 flops, no RTL edit.  usage: hk5m_delta.py IN_PLAN OUT_PLAN"""
import json, sys
p = json.load(open(sys.argv[1])); T = p["partition_types"]; log = []
OLD, NEW = [362.4, 354.208], [518.4, 862.944]
c = T["hd_tile"]["clock"]
assert c["start_capture_um"] == OLD, c["start_capture_um"]
pin = [q for q in c["landing_contract"]["pins"] if q["name"] == "cland_tstart_in"]
assert len(pin) == 1 and pin[0]["xy_um"] == OLD, pin
pin[0]["xy_um"] = list(NEW); c["start_capture_um"] = list(NEW); log.append(f"hd_tile.cland_tstart_in {OLD} -> {NEW}")
BUSES = {"hd_tile": ("i", "o"), "hd_spn": ("be_i", "bw_i", "xe_o", "xw_o"), "hd_spn_end": ("be_i", "bw_i", "xe_o", "xw_o")}
SLOTS = {"hd_spn_eshim_rx": "link", "hd_spn_eshim_tx": "link", "hd_spn_wshim_rx": "link", "hd_spn_wshim_tx": "link",
         "hd_turn_a": "t", "hd_turn_b": "t"}
for tn, names in BUSES.items():
    for b in T[tn]["buses"]:
        if b["name"] in names:
            assert b.get("order", "lsb_low") == "lsb_low", (tn, b["name"], b.get("order"))
            b["order"] = "lsb_high"; log.append(f"{tn}.bus.{b['name']} order lsb_low -> lsb_high")
    assert sum(b["name"] in names for b in T[tn]["buses"]) == len(names), tn
for tn, sn in SLOTS.items():
    s = [s for s in T[tn]["ft_slots"] if s["name"] == sn]; assert len(s) == 1, (tn, sn); s = s[0]
    for k in ("order", "in_order", "out_order"):
        assert s.get(k, "lsb_low") == "lsb_low", (tn, k, s.get(k))
    s["order"] = "lsb_high"; s.pop("in_order", None); s.pop("out_order", None)
    log.append(f"{tn}.ft_slot.{sn} order lsb_low -> lsb_high")
# die-frame port records that carry their own resolved geometry: the type flip mirrors each die-frame order
GROUP = set(BUSES) | set(SLOTS)
PT = {x["name"]: x["type"] for x in p["partitions"]}
nflip = 0
MEMB = {(t, b) for t, bs in BUSES.items() for b in bs} | {(t, SLOTS[t] + x) for t in SLOTS for x in ("_i", "_o")}
for q in p["ports"]:
    ends = [(PT.get(q[k]["part"]), q[k]["bus"]) for k in ("src", "dst")]
    inn = [e in MEMB for e in ends]
    assert all(inn) or not any(inn), (q["id"], ends)       # the group is closed under abutment
    if all(inn) and "order" in q:
        q["order"] = {"lsb_low": "lsb_high", "lsb_high": "lsb_low"}[q["order"]]; nflip += 1
log.append(f"ports: {nflip} explicit die-frame 565-bit port orders mirrored")
p["note"] = p.get("note", "") + " | DIE-HEAD-31 hk5m: tstart pin in the band + 565-bit tile group lsb_high (status bits at band bottom)"
json.dump(p, open(sys.argv[2], "w"), indent=1)
print("\n".join(log))
