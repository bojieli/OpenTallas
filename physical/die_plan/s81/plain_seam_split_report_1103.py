#!/usr/bin/env python3
"""Report of the S81 plain-lane input budget event (gen_phys.plain_seam_split on plan clock.plain_seam_split).

    plain_seam_split_report_1103.py PLAN OUT_DIR

Per lane (plan lanes[]) and per die port: receiver ft_i written / raw input max old -> new, registered sender ft_o
output max old -> new, and the ESTIMATED sender margin = (T - output max) - sender path, where the sender path is the
relay-bay hop probe (tools/die_plan/relay_bay_hop_rows.json: TT reg-to-reg, worst of M5/M7 at the best BUFx4 pitch
with slew <= 320 ps, T - wire_max_slack; linear beyond the probed 300 um) at the sender's last segment: its last station site (ft_slots[].regs_um) to
the out-pin window centre, else L/k.  Writes plain_seam_split_lanes.tsv + plain_seam_split_summary.json."""
import collections, json, math, os, sys
from pathlib import Path
TD = Path(__file__).resolve().parents[3] / "tools/die_plan"
sys.path.insert(0, str(TD))
import schema as S, gen_phys as G

plan, od = sys.argv[1], sys.argv[2]
os.makedirs(od, exist_ok=True)
P = S.Plan(json.load(open(plan)), plan)
T, sh = float(P.die["period_ps"]), G.ft_hop_in_share(P)
full = (1 - sh) * T
spl = G.plain_seam_split(P)
rows = json.load(open(TD / "relay_bay_hop_rows.json"))
probe = collections.defaultdict(dict)
for r in rows:
    c = r["case"].split("_")          # L<len>_<layer>_BUFx4_<pitch>_ff
    if r["corner"] == "TT" and r["max_slew_max"] <= 320:
        probe[int(c[0][1:])].setdefault(c[1], []).append(T - r["wire_max_slack"])
Ls = sorted(L for L in probe if len(probe[L]) == 2)


def _p(L):
    return max(min(v) for v in probe[L].values())     # best pitch per layer, worst layer


EXTRA = []


def path_ps(seg):
    L = next((x for x in Ls if x >= seg - 1e-6), None)
    if L is not None:
        return _p(L)
    # beyond the probed relay-bay hop range (pre-relay-bay plan sites): linear in length from the top 50 um of the probe
    a = next(x for x in Ls if x >= Ls[-1] - 50)
    EXTRA.append(seg)
    return _p(Ls[-1]) + (seg - Ls[-1]) * (_p(Ls[-1]) - _p(a)) / max(1e-6, Ls[-1] - a)


def pin(t, face, win):
    w, h = t["outline_um"]; m = 0.5 * (win[0] + win[1])
    return {"E": (w, m), "W": (0.0, m), "N": (m, h), "S": (m, 0.0)}[face]


def last_seg(tn, slot):
    t = P.types[tn]
    s = next(x for x in t["ft_slots"] if x["name"] == slot)
    b = pin(t, s["out_face"], s["out_window_um"])
    if s.get("regs_um"):
        r = s["regs_um"][-1]
        return abs(r[0] - b[0]) + abs(r[1] - b[1])
    a = pin(t, s["in_face"], s["in_window_um"])
    return (abs(a[0] - b[0]) + abs(a[1] - b[1])) / max(1, s.get("stations", 1))


def cls(tn):
    b = tn.split("__")[0]
    return "slice_station" if b.startswith("slice_station") else b


lane_of = {p: l["id"] for l in P.raw["lanes"] for p in l["ports"]}
out, summ = [], collections.defaultdict(lambda: collections.Counter())
worst = {}
for pid, pr in P.ports.items():
    s, d = pr["src"], pr["dst"]
    if S.DIE_PART in (s["part"], d["part"]):
        continue
    rt, st = P.parts[d["part"]]["type"], P.parts[s["part"]]["type"]
    db, sb = d["bus"], s["bus"]
    if db not in spl["in"].get(rt, {}):
        continue
    sh_in = -G.tap_window_io_shift(P, rt)[0]
    i_new = spl["in"][rt][db]
    sft = sb.endswith("_o") and sb[:-2] in {x["name"] for x in P.types[st].get("ft_slots", [])}
    o_old = sh * T if sft else G.IO_BUDGET * T
    o_new = spl["out"].get(st, {}).get(sb, o_old)
    seg = last_seg(st, sb[:-2]) if sft else None
    pth = path_ps(seg) if seg is not None else None
    m_old = None if pth is None else round(T - o_old - pth, 1)
    m_new = None if pth is None else round(T - o_new - pth, 1)
    c = cls(rt)
    summ[c]["ports"] += 1
    summ[c]["sender_cut" if o_new > o_old + 1e-6 else ("sender_kept_ft_o" if sft else "sender_bus_unchanged")] += 1
    if m_new is not None and (c not in worst or m_new < worst[c][0]):
        worst[c] = (m_new, st, sb, round(seg, 1), m_old)
    out.append([lane_of.get(pid, ""), pid, rt, db, round(full - sh_in, 1), round(i_new - sh_in, 1), round(full, 1), i_new,
                round(full - i_new, 1), st, sb, "ft_o" if sft else "bus", round(o_old, 1), round(o_new, 1),
                "" if seg is None else round(seg, 1), "" if pth is None else round(pth, 1),
                "" if m_old is None else m_old, "" if m_new is None else m_new])
hdr = ["lane", "port", "rx_type", "rx_bus", "rx_written_old", "rx_written_new", "rx_raw_old", "rx_raw_new",
       "rx_face_gain_ps", "tx_type", "tx_bus", "tx_kind", "tx_out_old", "tx_out_new", "tx_last_seg_um",
       "tx_path_est_ps", "tx_margin_old_ps", "tx_margin_new_ps"]
with open(f"{od}/plain_seam_split_lanes.tsv", "w") as f:
    f.write("\t".join(hdr) + "\n" + "".join("\t".join(map(str, r)) + "\n" for r in out))
lanes = collections.defaultdict(set)
for r in out:
    lanes[cls(r[2])].add(r[0])
res = {"period_ps": T, "ft_hop_in_share": sh, "cfg": P.clock["plain_seam_split"],
       "rx_type_ports": sum(len(v) for v in spl["in"].values()), "tx_type_ports": sum(len(v) for v in spl["out"].values()),
       "die_ports": len(out), "lanes": len({r[0] for r in out}),
       "tx_extrapolated_ports": len(EXTRA), "probe_max_um": Ls[-1], "tx_last_seg_max_um": round(max(EXTRA, default=0), 1),
       "max_rx_written_new": max(r[5] for r in out), "min_rx_face_gain_ps": min(r[8] for r in out),
       "per_class": {c: dict(lanes=len(lanes[c]), **summ[c],
                             worst_tx_margin_new_ps=worst.get(c, (None,))[0],
                             worst_tx=(dict(zip(("type", "bus", "last_seg_um", "margin_old_ps"), worst[c][1:]))
                                       if c in worst else None)) for c in sorted(summ)}}
json.dump(res, open(f"{od}/plain_seam_split_summary.json", "w"), indent=1)
print(json.dumps(res, indent=1))
