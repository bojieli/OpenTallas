# FABLE-FIX-KV-HUB-R3: plan_p3 (D27d + hroot B + 9 hard rings per hub type, reset re-derived) -> plan_p4:
#  + the hub_C row fields on every new ring core (track_offset_um, pins_file, lef, lib, reset_net, cells_basis)
#  + kv3_hub_Wo raw branch fs_o_host_host_rst_n stage 0 x 986.461 -> 979.461 (kit preflight cland_band_legal_site, R2 row)
# usage (cwd = launch tree): compose.py PLAN_IN PLAN_OUT VIEWS_REL REPORT
import json, sys, re
sys.path.insert(0, "tools/die_plan")
import clock_landings as CL
src, dst, vrel, rep = sys.argv[1:5]
p = json.load(open(src)); out = {}
ident = getattr(CL, "ident", lambda s: re.sub(r"\W", "_", s))
for tn in ("kv3_hub_Wo", "kv3_hub_Eo"):
    t = p["partition_types"][tn]; cfg = t["clock"]["landing_reader_start"]
    owners = CL.reader_start_owners(cfg) if cfg.get("share_trunk") else {}
    rows = []
    for h in t["hard_cores"]:
        if not h["inst"].startswith("cl_"): continue
        bus = h["physical_inst"][len("u_bound.u_cland_"):]; m = h["module"]
        st = cfg["branches"][bus]["stages"]; i = len(st) - 1
        ob = owners[bus][i] if owners.get(bus) else bus
        h["track_offset_um"] = [0.012, 0.012]
        h["pins_file"] = f"cores/kv_ring/{m}_pins.json"
        h["cells_basis"] = "CLAND-MACRO-1 master native cell count (KV-HUBWO-SPLIT row)"
        h["reset_net"] = f"cland_reader_start_{ident(ob)}_{i}"
        h["lef"] = f"{vrel}/{m}/{m}.lef"; h["lib"] = f"{vrel}/{m}/{m}_tt.lib"
        rows.append(h)
    out[tn] = rows
rb = p["partition_types"]["kv3_hub_Wo"]["clock"]["landing_raw_branches"]
b = [x for x in rb if x["name"] == "fs_o_host_host_rst_n"]; assert len(b) == 1
assert b[0]["stages"][0]["xy_um"] == [986.461, 829.3], b[0]["stages"][0]
b[0]["stages"][0]["xy_um"] = [979.461, 829.3]
p["note"] = p.get("note", "") + " | KV-D28-HUBRING R3: ring rows carry views/pins/reset_net (re-frozen masters); hub_Wo fs_o_host_host_rst_n stage 0 x -7 um"
json.dump(p, open(dst, "w"), indent=1)
json.dump(dict(schema="kv_hubc_split_rows.v1", base="D27d plan 07a462a13e91 + reset re-derivation (landing_remap resel, collector_reattach, hard_ring_wreg)",
               rows=out, extra_rows=[dict(type="kv3_hub_Wo", path="clock.landing_raw_branches[fs_o_host_host_rst_n].stages[0].xy_um", old=[986.461, 829.3], new=[979.461, 829.3])]),
          open(rep, "w"), indent=1)
for tn, rows in out.items():
    for h in rows: print(tn, h["inst"], h["module"], h["origin_um"], h["orient"], h["reset_net"])
