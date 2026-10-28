# DIE-KV-13 ESTIMATE: VPORT RT / W / DQ / RL on a new count-align bind by the landed-stage delta model on bind_s2
# (regen_constants.kv_vport formulas; bound_stages/landed = old + sum over the lane's crossings of (new - old) sched_lat).
import json, sys, re, collections
bl = json.load(open(sys.argv[1]))["buses"]; bg = json.load(open(sys.argv[2])); side = json.load(open(sys.argv[3]))
ca0 = side["count_aligned"]["ports"]; bylane = collections.defaultdict(list)
for r in side["ports"]: bylane[r["lane"]].append(r["port"])
new = {n: json.load(open(f))["ports"] for n, f in (a.split("=") for a in sys.argv[4:])}
def d(lane, nb): return 0 if nb is None else sum(nb[p]["sched_lat"] - ca0[p]["sched_lat"] for p in bylane[lane])
for name, nb in [("rt20(bind_s2)", None)] + list(new.items()):
    rows = collections.defaultdict(list)
    for a in bl:
        m = re.search(r"(vport_\w+?)\.vq", " ".join(a["leaves"]))
        if not m: continue
        for c in bl:
            if c["src"] == a["dst"] and c["dst"] == a["src"] and re.search(r"slg_\w+\.rsp", " ".join(c["leaves"])) and c["dst"].startswith("pv"):
                rows[m.group(1)].append(9 + a["bound_stages"] + d(a["lane"], nb) + c["bound_stages"] + d(c["lane"], nb))
    W = {}
    for g in bg["landing"]:
        for mm in g["members"]:
            if re.match(r"pvw_\d__u_ctl\.req_t$", mm["source"].split(".", 1)[-1] if False else mm["source"]) is None and not re.search(r"pvw_\d__u_ctl\.req_t$", mm["source"]): continue
            if g["sink"].startswith("vport_") and mm["sink_port"] == "pr_t":
                W[g["sink"]] = mm["landed_stages"] + d(mm["lane"], nb)
    out = {vp: (max(r), W.get(vp)) for vp, r in sorted(rows.items())}
    rl = max(rt + w for rt, w in out.values()); dq = {k: rl - (rt + w) for k, (rt, w) in out.items()}
    pads = {k: max(v - 15, 0) for k, v in dq.items()}
    print(name, "RT", min(v[0] for v in out.values()), "-", max(v[0] for v in out.values()), "W", min(v[1] for v in out.values()), "-",
          max(v[1] for v in out.values()), "RL(max W+RT)", rl, "FIA", 4 + rl + 1, "DQ max", max(dq.values()), ">15 on", sum(1 for v in dq.values() if v > 15),
          "pad stages sum", sum(pads.values()), "max", max(pads.values()))
    # per-type spread of the W pads (strap-pad sites: fixed base + 4-bit span <= 15, DIE-KV-8)
    if len(sys.argv) > 4 and name == list(new)[-1] or name.startswith("rt20"):
        plan = json.load(open("/srv/opentallas-scratch2/claude/wt/die-kv-6/results/die_kv_7_1028/event_ectl/plan.json"))
        ptype = {p["name"]: p["type"] for p in plan["partitions"]}
        sp = {}
        for g in bg["landing"]:
            if g["sink"].startswith("vport_") and any(m["sink_port"] == "pr_t" for m in g["members"]): sp[g["sink"]] = g["sink_part"]
        bt = collections.defaultdict(list)
        for k, v in pads.items(): bt[ptype[sp[k]]].append((k, sp[k], v))
        for t, xs in sorted(bt.items()):
            print("   type", t, "pads", [(a, b, c) for a, b, c in sorted(xs)], "span", max(c for *_, c in xs) - min(c for *_, c in xs))
