"""HEAD-99 (COORD STALE-CORE-VIEW gate / TYPE-HDEPC): hd_host_e u_epc lib -> the SIGNED view (tt f663e343abd8, ff 1016d15ff88c), absolute path, same on every HEAD host.
usage: epc_repoint.py PLAN_IN PLAN_OUT"""
import json, sys
V = "/srv/opentallas-scratch2/claude/head-97/hepc_south/eco99_south_g2/i1/views/ot_s81hd_he_epc_tt.lib"
d = json.load(open(sys.argv[1])); n = 0
for tn, t in d["partition_types"].items():
    for h in t.get("hard_cores", []):
        if h.get("module") == "ot_s81hd_he_epc":
            print(tn, h["inst"][-20:], h["lib"], "->", V); h["lib"] = V; n += 1
            t["note"] = t.get("note", "") + " | HEAD-99 11-14: u_epc lib repointed to the signed view (tt f663e343abd8, ff 1016d15ff88c; TYPE-HDEPC: stale 8aad8716ff84 bundled since kits20b)."
json.dump(d, open(sys.argv[2], "w"), indent=1, ensure_ascii=False); print("repointed", n)
