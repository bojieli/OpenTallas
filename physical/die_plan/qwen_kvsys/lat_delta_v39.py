#!/usr/bin/env python3
"""KV-405 10-24: per-lane cycle change v3.8x -> v3.9 (reach 405 re-plan) for TOK-* pricing.
Every lane: cycles before / after (gen.py latency_table = boundary + ft stations + fixed_cycles + latency-group pad),
the parts of the change (ft stations, fixed = internal stations, pad), src / dst partition + bus, width; summary:
lanes changed, +cycles histogram, max, per (src type -> dst type, bus family) groups, and the KV token-path lane families
(TOKEN_PATH: bus-name patterns of the lanes the Qwen KV token schedule rides; TOK-QK prices them).
With the folded latency JSON (gen.py latency --fold-r8: per lane base + r8_pad) every lane also gets `landed_after` =
base + its largest R8 landing pad (the depth the compiler schedules: valid / payload of one interface land together).
    lat_delta_v39.py BEFORE_PLAN.json AFTER_PLAN.json OUT.json [FOLDED_LATENCY.json]"""
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools/die_plan"))
import gen           # noqa: E402
import schema as S   # noqa: E402

# Qwen KV token path (KV plan v3.x README / KV-FT findings): d2d <-> kvs_attn (q/k/v in, attention out), hub <-> pv
# (vport requests / slg responses / PV rows), pc <-> pv (KV reads, slg/vport), ahub <-> astk (am / ap / cal), seq fan,
# hroot / hslice (KV head fan-out), kvs_emb / kg.  Everything else (fault / health / boot / cfg / obs) is off the token path.
TOKEN_PATH = [
    ("d2d_kvs_attn", r"(d2d|kvs_attn|attn|qkd_d2d|flit|phy_rx|phy_tx)"),
    ("vport_slg", r"(vport|slg|vq|vreq|in0_|rsp)"),
    ("pv_rows", r"(pv|row|pvr|pvw|kv_rd|kvrd)"),
    ("ahub_astk", r"(ahub|astk|_am|_ap|acal|_cal)"),
    ("seq_hroot", r"(seq|hroot|hsl|hslice|fan|xs)"),
    ("emb_kg", r"(emb|kg|kgo|epoch)"),
]
OFF_PATH = r"(fault|flt|health|boot|cfg|obs|dbg|rst|reset|scan|stat)"


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def family(bus):
    b = re.sub(r"_(EN|ES|WN|WS|E|W|N|S|\d+)$", "", re.sub(r"^[io]_", "", bus))
    return re.sub(r"\d+", "#", b)


def main():
    fa, fb, out = sys.argv[1:4]
    fold = {}
    if len(sys.argv) > 4:
        fj = json.loads(Path(sys.argv[4]).read_text())
        fold = {k: v for k, v in fj.get("lanes", {}).items()} if isinstance(fj.get("lanes"), dict) else \
            {e["lane"]: e for e in fj.get("lanes", [])}
    A, B = S.Plan(S.load(fa)), S.Plan(S.load(fb))
    ta, tb = gen.latency_table(A), gen.latency_table(B)
    ports = B.ports
    lanes = {}
    hist = Counter()
    groups = defaultdict(lambda: dict(lanes=0, bits=0, max=0, deltas=Counter()))
    tok = defaultdict(lambda: dict(lanes=0, changed=0, max=0, sum=0, worst=[]))
    for lid, nb in tb.items():
        na = ta[lid]
        ln = B.lanes[lid]
        p0, p1 = ports[ln["ports"][0]], ports[ln["ports"][-1]]
        d = nb["cycles"] - na["cycles"]
        e = dict(param=nb.get("param"), src=p0["src"], dst=p1["dst"], width=p0["width"], kind=p0.get("kind"),
                 before=na["cycles"], after=nb["cycles"], delta=d,
                 d_stations=nb["stations"] - na["stations"], d_fixed=nb["fixed"] - na["fixed"], d_pad=nb["pad"] - na["pad"],
                 natural_before=na["natural"], natural_after=nb["natural"])
        if lid in fold and "r8_pad" in fold[lid]:
            e["r8_pad_after"] = fold[lid]["r8_pad"]
            e["landed_after"] = nb["cycles"] + fold[lid]["r8_pad"]
        lanes[lid] = e
        hist[d] += 1
        bus = p0["src"]["bus"]
        g = groups[f"{B.parts[p0['src']['part']]['type'] if p0['src']['part'] in B.parts else p0['src']['part']} -> "
                   f"{B.parts[p1['dst']['part']]['type'] if p1['dst']['part'] in B.parts else p1['dst']['part']} : {family(bus)}"]
        g["lanes"] += 1
        g["bits"] += p0["width"]
        g["max"] = max(g["max"], d)
        g["deltas"][d] += 1
        name = f"{bus} {p1['dst']['bus']}"
        if re.search(OFF_PATH, name):
            continue
        for fam, rx in TOKEN_PATH:
            if re.search(rx, name):
                t = tok[fam]
                t["lanes"] += 1
                t["changed"] += bool(d)
                t["max"] = max(t["max"], d)
                t["sum"] += d
                t["worst"].append((d, lid, f"{p0['src']['part']}.{bus} -> {p1['dst']['part']}.{p1['dst']['bus']}",
                                   na["cycles"], nb["cycles"], e.get("landed_after")))
                break
    for t in tok.values():
        t["worst"] = [dict(delta=d, lane=l, path=p, before=a, after=b, landed_after=c)
                      for d, l, p, a, b, c in sorted(t["worst"], key=lambda x: x[:2], reverse=True)[:12]]
    ch = [e["delta"] for e in lanes.values() if e["delta"]]
    js = dict(schema="opentallas.die_plan.lane_delta.v1",
              note="KV-405 10-24 v3.9 = v3.8x + run_v39.sh (owner dec. 12/17, rulings 9.3/9.4: signals <= M7, every hop / "
                   "ft station / internal station <= 405 um exactly). Per lane: cycles before/after (gen.py latency_table; "
                   "d_stations = ft slot stations, d_fixed = FIRM internal stations, d_pad = latency-group pad). R8 landing "
                   "pads are separate (r8/qwen_kvsys_r8_landing.json, kv44 groups rebased onto v3.9).",
              plan_digest_before=digest(fa), plan_digest_after=digest(fb),
              summary=dict(lanes=len(lanes), changed=len(ch), unchanged=len(lanes) - len(ch), max_delta=max(ch, default=0),
                           min_delta=min(ch, default=0), sum_delta=sum(ch),
                           mean_delta_changed=round(sum(ch) / len(ch), 3) if ch else 0,
                           histogram={str(k): v for k, v in sorted(hist.items())},
                           token_path=dict(tok)),
              groups={k: dict(v, deltas={str(a): b for a, b in sorted(v["deltas"].items())})
                      for k, v in sorted(groups.items(), key=lambda kv: -kv[1]["max"]) if v["max"]},
              lanes=lanes)
    Path(out).write_text(json.dumps(js, indent=1) + "\n")
    s = js["summary"]
    print(f"lat_delta_v39: {s['changed']}/{s['lanes']} lanes changed, max +{s['max_delta']}, sum +{s['sum_delta']}, "
          f"hist {s['histogram']}")
    for k, v in s["token_path"].items():
        print(f"  token {k}: {v['changed']}/{v['lanes']} lanes changed, max +{v['max']}")


if __name__ == "__main__":
    main()
