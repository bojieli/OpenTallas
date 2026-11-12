import sys, json, copy
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/head-95-rfsr/tools/die_plan")
import schema as S, reset_tree as RT
p = sys.argv[1]; raw = json.load(open(p)); flat = copy.deepcopy(raw)
for h in flat["partition_types"]["hd_lep0N"]["hard_cores"]:
    dx, dy = h.get("track_offset_um", [0, 0])
    if "g_pp" not in h["inst"]:
        h["origin_um"] = [round(h["origin_um"][0] + dx, 3), round(h["origin_um"][1] + dy, 3)]; h["track_offset_um"] = [0.0, 0.0]
def rel(r):
    T = RT.for_type(S.Plan(r, p), "hd_lep0N")
    return sorted((x["name"], tuple(x["xy"]), x.get("role")) for x in (RT.start_relays(T) if T.get("start") else T["relays"]))
a, b = rel(raw), rel(flat)
print("obstacle_model", raw["partition_types"]["hd_lep0N"]["reset"].get("obstacle_model"), "same tree:", a == b, len(a), len(b))
sa, sb = set(a), set(b); print("only enc", sorted(sa - sb)[:6]); print("only flat", sorted(sb - sa)[:6])
