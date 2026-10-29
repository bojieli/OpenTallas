"""TOK-QC-2 10-28: PAIRED-DIRECTION rule for count-aligned (12.16a) relay chains whose two directions one RTL parameter
must describe (generator rule, COORD 20:49 item 2: no hand pad).

The QC collective face calendar takes ONE relay depth per port (coll_regen.py RS_j: u_collective sx_j -> face tx_* depth
== face rx_* -> u_collective sr_j depth).  Under count alignment every hop's schedule latency is
sched_lat = K + 1 + n_dst - n_src (count_align_bind identity), so the two directions of a relay chain differ whenever
the clock origins along the chain are not symmetric (QC g14: core->face 2+2+2+2 = 8, face->core 3+3+3+3 = 12).
Rule (applied to the gate's bind_clock BEFORE annotate_table, i.e. both directions derived from the plan with the same
count):
  * PAIRS = (lane coll_core__crec_tx_s<j>, the reverse lane ending at coll_core with bus rec_rx_s<j>_i), j = 0..2 -
    exactly the chains coll_regen RS_j reads.
  * target = max(sum sched_lat) over the two chains; the shorter chain receives the shortfall as +1 count steps
    (K += 1, sched_lat += 1 together, so the identity and every fundamental loop stay exact), one per hop, hops ordered
    by the largest high-guard room ((DEPTH - 0.5) T - L_hi_ps), each step only if the hop keeps >= NEED_PS to the high
    guard after the step; never on a start-tree hop.  A shortfall that cannot be placed is an error (no partial fix).
  * The caller re-runs count_align_bind.verify() on the result (identity, loops, simulated ring-guard margins).
"""
import re

NEED_PS = 100.0


def chains(b, table):
    """lane -> ordered port ids (hop index __N) for the ports of the region table that the bind lists"""
    lanes = {}
    for r in table["ports"]:
        if r["port"] in b["ports"]:
            lanes.setdefault(r["lane"], []).append(r["port"])
    return {k: sorted(v, key=lambda p: int(p.rsplit("__", 1)[1])) for k, v in lanes.items()}


def pairs(b, table):
    ch = chains(b, table)
    out = []
    for lane, ps in sorted(ch.items()):
        m = re.fullmatch(r"coll_core__crec_tx_s(\d)", lane)
        if not m:
            continue
        j = m.group(1)
        far = b["ports"][ps[-1]]["dst_part"]
        rev = [k for k, v in ch.items() if re.fullmatch(rf"\w+__crec_rx_s{j}", k)
               and b["ports"][v[0]]["src_part"] == far and b["ports"][v[-1]]["dst_part"] == "coll_core"]
        if len(rev) != 1:
            raise ValueError(f"{lane}: reverse chain to coll_core not unique: {rev}")
        out.append((f"RS{j}", lane, rev[0]))
    return out, ch


def apply(b, table, need_ps=NEED_PS):
    """mutates b; returns the record of every step"""
    T = b["period_ps"]
    rec = []
    ps, ch = pairs(b, table)
    for name, a, r in ps:
        s = {x: sum(b["ports"][p]["sched_lat"] for p in ch[x]) for x in (a, r)}
        tgt = max(s.values())
        short = min(s, key=s.get)
        need = tgt - s[short]
        row = dict(pair=name, chains={a: s[a], r: s[r]}, target=tgt, steps=[])
        if need:
            hops = [p for p in ch[short] if not b["ports"][p]["tree"]]
            room = lambda p: (b["ports"][p]["depth"] - 0.5) * T - b["ports"][p]["L_hi_ps"]
            while need:
                hops.sort(key=lambda p: -room(p))
                ok = [p for p in hops if room(p) - T >= need_ps]
                if not ok:
                    raise ValueError(f"{name}: {need} count(s) of {short} cannot be placed inside the ring guards")
                # one step per hop per round (spread), largest room first
                for p in ok[:need]:
                    c = b["ports"][p]
                    c["K"] += 1
                    c["sched_lat"] += 1
                    for k in ("L_lo_ps", "L_hi_ps"):
                        if k in c:
                            c[k] = round(c[k] + T, 1)
                    for k, sg in (("margin_lo_ps", 1), ("margin_hi_ps", -1)):
                        if k in c:
                            c[k] = round(c[k] + sg * T, 1)
                    row["steps"].append(dict(port=p, K=c["K"], sched_lat=c["sched_lat"],
                                             hi_room_ps=round(room(p), 1)))
                    need -= 1
        rec.append(row)
    return rec
