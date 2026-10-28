"""DIE-KV-5: METHODOLOGY 1.8 + 12.15a count-strap kit list for KV, in the PARTITION frame (resolves DIE-KV-4's UNCHECKED
region-frame K: K comes from count_align_bind v2 --parts ocv, i.e. the ca-origin start relay of the 32 multi-partition regions
is applied: relay partition N = origin N + relay_stages, non-tree K shifted accordingly).
Per receiving partition TYPE: one kit.  Type parameters (not straps): ring DEPTH per bus = max over the type's instances,
TW (strap width) per bus.  Per-instance strap_* pins (tied TIEHI/TIELO at the parent):
  strap_ck_<bus>[TW-1:0]  ring K mod 2^TW (modular count; K span must be < 2^TW) for every CA receiving bus of the type
  strap_cland_role[1:0]   origin-root / origin-child / relay   (only if the type has >1 role among its instances)
  strap_cland_tsel[..]    which receiving bus carries the parent's forwarded start (child origins; only if it varies)
  strap_cland_pad[..], strap_cland_efall  origin PAD / EDGE_FALL (only if they vary)
LEC variant = the tuple of all strap values of one instance; one LEC per (master, used variant).
    strap_list_v2.py PLAN BIND OUT_JSON [--tw 6]"""
import argparse, json
from collections import defaultdict

ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("bind"); ap.add_argument("out")
ap.add_argument("--tw", type=int, default=6)
a = ap.parse_args()
plan = json.load(open(a.plan)); B = json.load(open(a.bind))
ports = {p["id"]: p for p in plan["ports"]}
ptype = {p["name"]: p["type"] for p in plan["partitions"]}
inst_bus = defaultdict(dict)                          # part -> bus -> (K, depth, port, tree)
for pid, c in B["ports"].items():
    p = ports[pid]
    q, bus = p["dst"]["part"], p["dst"]["bus"]
    if q != c["dst_part"]:
        raise SystemExit(f"{pid}: plan dst {q} != bind dst_part {c['dst_part']}")
    if bus in inst_bus[q]:
        raise SystemExit(f"{pid}: two CA crossings land on {q}.{bus}")
    inst_bus[q][bus] = (c["K"], c["depth"], pid, c["tree"])
ks = [c["K"] for c in B["ports"].values()]
if max(ks) - min(ks) >= (1 << a.tw):      # strap carries K mod 2^TW (ring count is modular); the span must fit
    raise SystemExit(f"K span {min(ks)}..{max(ks)} does not fit {a.tw} bits mod 2^TW")
role = {}
for q, pi in B["parts"].items():
    if pi["role"] == "relay":
        role[q] = ("relay", None, None, None)
    else:
        r = B["regions"][pi["region"]]
        if r["parent"] is None:
            role[q] = ("root", None, None, None)
        else:
            tp = ports[r["tree_port"]]
            if tp["dst"]["part"] != q:
                raise SystemExit(f"region {pi['region']}: tree port {r['tree_port']} lands on {tp['dst']['part']} not origin {q}")
            role[q] = ("child", tp["dst"]["bus"], r["pad"], bool(r["edge_fall"]))
types = defaultdict(list)
for q in set(inst_bus) | set(role):
    types[ptype[q]].append(q)
out, tot = {}, defaultdict(int)
for tn, qs in sorted(types.items()):
    qs.sort()
    buses = sorted({b for q in qs for b in inst_bus.get(q, {})})
    depth = {b: max(inst_bus[q][b][1] for q in qs if b in inst_bus.get(q, {})) for b in buses}
    sigs = {q: (tuple(inst_bus.get(q, {}).get(b, (None,))[0] for b in buses), role.get(q)) for q in qs}
    roles = {s[1][0] if s[1] else None for s in sigs.values()}
    tsel = {s[1][1] for s in sigs.values() if s[1] and s[1][0] == "child"}
    pads = {s[1][2] for s in sigs.values() if s[1] and s[1][0] == "child"}
    efs = {s[1][3] for s in sigs.values() if s[1] and s[1][0] == "child"}
    missing = sum(1 for q in qs for b in buses if b not in inst_bus.get(q, {}))
    var = defaultdict(list)
    for q in qs:
        var[json.dumps(sigs[q])].append(q)
    straps = {f"strap_ck_{b}": a.tw for b in buses}
    if len(roles) > 1: straps["strap_cland_role"] = 2
    if len(tsel) > 1: straps["strap_cland_tsel"] = max(1, (len(tsel) - 1).bit_length())
    if len(pads) > 1: straps["strap_cland_pad"] = max(1, max(pads).bit_length())
    if len(efs) > 1: straps["strap_cland_efall"] = 1
    out[tn] = dict(instances=len(qs), ca_buses=len(buses), depth={b: depth[b] for b in buses},
                   depth_hist={str(k): sum(1 for v in depth.values() if v == k) for k in (4, 8)},
                   roles=sorted(r for r in roles if r) + (["none"] if None in roles else []),
                   tree_buses=sorted(t for t in tsel if t), pads=sorted(pads), edge_fall=sorted(efs),
                   buses_unused_on_some_instance=missing,
                   strap_pins=straps, strap_bits=sum(straps.values()), lec_variants=len(var),
                   variants=[dict(instances=v, K={b: k for b, k in zip(buses, json.loads(s)[0]) if k is not None},
                                  role=json.loads(s)[1]) for s, v in var.items()])
    tot["lec"] += len(var); tot["d8"] += out[tn]["depth_hist"]["8"]; tot["buses"] += len(buses)
    tot["bits"] += out[tn]["strap_bits"] * len(qs); tot["insts"] += len(qs); tot["unused"] += missing
summ = dict(frame="partition (count_align_bind v2 --parts ocv, ca-origin relay applied)", bind=a.bind, plan=a.plan,
            types=len(out), strap_kits=len(out), instances=tot["insts"], ca_buses_per_type_sum=tot["buses"],
            d8_type_buses=tot["d8"], lec_variants=tot["lec"], tied_strap_bits=tot["bits"], tw=a.tw,
            K_range=[min(c["K"] for c in B["ports"].values()), max(c["K"] for c in B["ports"].values())],
            roles={r: sum(1 for v in role.values() if v[0] == r) for r in ("root", "child", "relay")},
            buses_unused_on_some_instance=tot["unused"],
            types_with_role_strap=sum(1 for t in out.values() if "strap_cland_role" in t["strap_pins"]),
            types_with_tsel_strap=sum(1 for t in out.values() if "strap_cland_tsel" in t["strap_pins"]))
json.dump(dict(summary=summ, types=out), open(a.out, "w"), indent=1)
print(json.dumps(summ, indent=1))
for tn, t in sorted(out.items(), key=lambda kv: -kv[1]["lec_variants"])[:12]:
    print(tn, {k: t[k] for k in ("instances", "ca_buses", "depth_hist", "roles", "lec_variants", "strap_bits",
                                  "buses_unused_on_some_instance")})
