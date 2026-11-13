"""pEv11 delta 1 (DIE-HBM-102, TIMING-CLASS-1 SKEW family q_spb1/vsN1/vsN2): every ft hop lockup latch of these types hangs
on its RECEIVING (capture) station's tap: plan clock.ft_hop_lockup.tap[type][slot][k] = "capture" for every latched hop k -> k+1.
Routed evidence (d44v): q_spb1 u_fl_L720x3_o_2 on clk_t14 (311 ps insertion) vs capture clk_t9 (~40 ps): the launch-tap latch
loses the half cycle to tap skew; vsN2 u_fl_rst_15 -> u_rrl_15 the same.  Capture-tap: latch -> capture is one tap (T/2, CRPR);
launch -> latch keeps a full cycle of setup (time borrow), so any hold there is repairable padding (grt_pre HOPLATCH-HOLD).
latch_frac (0.95 where set) is kept: the long wire stays in the launch -> latch leg.  Physical only: RTL, bind, latency unchanged."""
import json, sys, hashlib
src, dst = sys.argv[1], sys.argv[2]
p = json.load(open(src)); lk = p["clock"]["ft_hop_lockup"]
assert lk.get("all") or True
tap = lk.setdefault("tap", {}); hops = lk.get("hops") or {}
rec = {}
for tn in ("q_spb1", "vsN1", "vsN2"):
    t = p["partition_types"][tn]
    assert tn in lk["types"], tn
    m = tap.setdefault(tn, {}); n = 0; flip = 0
    for s in t.get("ft_slots", []):
        ks = hops.get(tn, {}).get(s["name"]) if tn in hops else list(range(int(s.get("stations", 1)) - 1))
        for k in ks or []:
            old = m.get(s["name"], {}).get(str(k))
            if old == "launch": flip += 1
            m.setdefault(s["name"], {})[str(k)] = "capture"; n += 1
    rec[tn] = {"capture_hops": n, "launch_to_capture": flip}
lk["note"] = lk.get("note", "") + " | pEv11 11-13 DIE-HBM-102 (TIMING-CLASS-1 SKEW q_spb1/vsN1/vsN2): every latched hop of these 3 types on its capture tap " + json.dumps(rec)
s = json.dumps(p, indent=1); open(dst, "w").write(s)
print(json.dumps(rec), "sha", hashlib.sha256(s.encode()).hexdigest()[:12])
