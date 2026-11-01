import sys, json, copy, math
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/dh52-wave/tools/die_plan")
import schema as S, reset_tree as RT, taps as TP
src = sys.argv[1]; edits = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
raw = json.load(open(src + "/source_plan.json"))
P0 = S.Plan(copy.deepcopy(raw))
for tn, ops in edits.items():
    ck = raw["partition_types"][tn]["clock"]
    for op in ops:
        if op[0] == "add": ck["taps"].append(dict(name=op[1], xy=op[2]))
        if op[0] == "sink": ck["sink_sites_um"].append(op[1])
        if op[0] == "move":
            for t in ck["taps"]:
                if t["name"] == op[1]: t["xy"] = op[2]
P = S.Plan(raw)
for tn in ("hd_spn_end", "hd_spn"):
    r0 = [(r["q"], tuple(r["xy"]), r["d"]) for r in RT.for_type(P0, tn)["relays"]]
    r1 = [(r["q"], tuple(r["xy"]), r["d"]) for r in RT.for_type(P, tn)["relays"]]
    print(tn, "relays", len(r0), len(r1), "identical", r0 == r1, "changed", sum(1 for a, b in zip(r0, r1) if a != b), flush=True)
    try: ex = TP.explicit_taps(P, tn)
    except Exception as e: print(" ", e); continue
    sinks = TP.sink_sites(P, tn)
    taps = [(n, x, y) for n, x, y, *_ in ex]
    def nm(s): return min(abs(s[0]-x)+abs(s[1]-y) for _, x, y in taps)
    far = max(sinks, key=nm)
    print(tn, "relays", len(r0), len(r1), "identical", r0 == r1, "changed", sum(1 for a, b in zip(r0, r1) if a != b),
          "taps", len(ex), "maxload", max(l for *_, l, _ in ex), "maxR(euclid)", round(max(r for *_, r in ex), 1),
          "manhattan far", round(nm(far), 1), far[:2])
