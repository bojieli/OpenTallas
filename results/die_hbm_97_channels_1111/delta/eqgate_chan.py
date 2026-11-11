"""HBM-CHANNELS EQ gate (eqgate2.py walk): every changed leaf must be a POSITION key (geometry only, logic and
register structure unchanged).  Register-count keys (ft_slots[].stations, internal_stations[].regs_um length,
latency) are listed separately as CONTRACT changes (need their own bind + cycle proof).  usage: BASE NEW OUT"""
import json, sys, hashlib
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
# DIE-HBM-98 11-11 q_mcb split: type-key rename only.  Check each new type json-equal to the old one except module/note
# and the partition type map, then compare the base with q_mcb renamed per partition (same content) so the walk sees 0 diffs.
import copy
split = {}
if "q_mcb" in a["partition_types"] and "q_mcb" not in b["partition_types"]:
    old_t = a["partition_types"]["q_mcb"]
    def strip(t): t = dict(t); t.pop("module", None); t.pop("note", None); return t
    pm = {x["name"]: x["type"] for x in b["partitions"]}
    for n in ("q_mcb_ne", "q_mcb_nw"):
        split[n] = dict(json_equal_except_module_note=(strip(b["partition_types"][n]) == strip(old_t)),
                        module=b["partition_types"][n]["module"], partitions=sorted(k for k, v in pm.items() if v == n))
    a = copy.deepcopy(a); ot = a["partition_types"].pop("q_mcb")
    for n in ("q_mcb_ne", "q_mcb_nw"):
        a["partition_types"][n] = copy.deepcopy(b["partition_types"][n])   # equal by the check above
    for x in a["partitions"]:
        if x["type"] == "q_mcb": x["type"] = pm[x["name"]]
diffs, lens = [], []
def walk(x, y, p):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in set(x) | set(y):
            if k not in x or k not in y: diffs.append(p + (k,)); continue
            walk(x[k], y[k], p + (k,))
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) == len(y):
            for i, (u, v) in enumerate(zip(x, y)): walk(u, v, p + (i,))
        else:
            lens.append((p, len(x), len(y))); diffs.append(p)
    elif x != y: diffs.append(p)
walk(a, b, ())
POS = ("origin_um", "regs_um", "bit_sites_um", "bit_site_cell_um", "from_um", "to_um", "xy", "tap_um", "in_window_um",
       "out_window_um", "note", "die_ft_bands")
OUTL = ("outline_um", "pins_file")   # DIE-HBM-98 kv_line south grow: geometry, pins checked below
def is_note(d): return len(d) >= 2 and d[-1] == "source" and d[-2] == "reset_from_master"   # (E) citation text
def is_pos(d): return any(k in d for k in POS) or is_note(d)
outl = [list(map(str, d)) for d in diffs if any(k in d for k in OUTL) and not is_pos(d)]
import os
BD, ND = os.path.dirname(os.path.abspath(sys.argv[1])), os.path.dirname(os.path.abspath(sys.argv[2]))
pins_eq = []
def _hc(P, t, i): return [h for h in P["partition_types"][t]["hard_cores"] if h["inst"] == i][0]
for d in outl:
    if "pins_file" not in d: continue
    t, i = d[d.index("partition_types") + 1], None
    hi = int(d[d.index("hard_cores") + 1]); i = a["partition_types"][t]["hard_cores"][hi]["inst"]
    po = json.load(open(os.path.join(BD, _hc(a, t, i)["pins_file"]))); pn = json.load(open(os.path.join(ND, _hc(b, t, i)["pins_file"])))
    H0, H1 = _hc(a, t, i)["outline_um"][1], _hc(b, t, i)["outline_um"][1]
    def face(q, H): return "S" if q["y"] < 1 else "N" if q["y"] > H - 1 else "W" if q["x"] < 1 else "E"
    so = {q["name"]: (q["layer"], q["dir"], face(q, H0)) for q in po}; sn = {q["name"]: (q["layer"], q["dir"], face(q, H1)) for q in pn}
    ew = [q for q in pn if face(q, H1) in "EW"]; ewo = [q for q in po if face(q, H0) in "EW"]
    lo = min(q["y"] for q in ewo) + (H1 - H0); hi_ = max(q["y"] for q in ewo) + (H1 - H0)
    pins_eq.append(dict(type=t, inst=i, pins=len(pn), same_names_layers_dirs_faces=(so == sn),
                        ew_y_inside_old_span=all(lo - 1e-6 <= q["y"] <= hi_ + 1e-6 for q in ew)))
bad_outl = [x for x in pins_eq if not (x["same_names_layers_dirs_faces"] and x["ew_y_inside_old_span"])]
contract = [list(map(str, d)) for d in diffs if "stations" in d or "latency" in d or "fixed_cycles" in d]
reg_len = [dict(path=list(map(str, p)), base=n0, new=n1) for p, n0, n1 in lens if p and p[-1] == "regs_um" and "internal_stations" in p]
ft_up = [dict(path=list(map(str, p)), base=n0, new=n1) for p, n0, n1 in lens if p and p[-1] == "regs_um" and "ft_slots" in p]
bad = [list(map(str, d)) for d in diffs if not is_pos(d) and not ("stations" in d or "latency" in d or "fixed_cycles" in d) and not any(k in d for k in OUTL)] + bad_outl + [k for k, v in split.items() if not v["json_equal_except_module_note"]]
types = sorted({d[d.index("partition_types") + 1] for d in diffs if "partition_types" in d})
out = dict(base_sha=hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest(),
           new_sha=hashlib.sha256(open(sys.argv[2], "rb").read()).hexdigest(),
           changed_paths=len(diffs), non_position_paths=bad, outline_paths=outl, outline_pins_check=pins_eq, type_split=split, note_text_paths=[list(map(str, d)) for d in diffs if is_note(d)], types_changed=types,
           contract_changes=dict(stations_or_latency_paths=contract, internal_station_reg_count=reg_len, ft_reg_count=ft_up),
           verdict=("EQ_BY_CONSTRUCTION" if not bad and not contract and not reg_len else
                    "EQ_BY_CONSTRUCTION_EXCEPT_CONTRACT" if not bad else "NOT_EQ"))
json.dump(out, open(sys.argv[3], "w"), indent=1)
print(out["verdict"], len(diffs), "nonpos", len(bad), bad[:6], "types", types)
print("contract", len(contract), contract[:12]); print("ist reg count", reg_len); print("ft reg count", ft_up)
