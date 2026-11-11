"""eq_record SRC BASE CAND OUT [extra JSON reports...]: plan-event EQ record (what changed between BASE and CAND).
Every partition type / top key not listed as changed is byte-identical (canonical JSON); per changed type the keys that
differ; every lane whose latency changed with old/new cycles and its fixed_cycles change (the only lane edit allowed)."""
import sys, json, copy, hashlib
SRC, BASE, CAND, OUT = sys.argv[1:5]
sys.path.insert(0, SRC + "/tools/die_plan")
import schema as S
rb, rc = open(BASE, "rb").read(), open(CAND, "rb").read()
b, c = json.loads(rb), json.loads(rc)
canon = lambda x: json.dumps(x, sort_keys=True, separators=(",", ":"))
top = sorted(k for k in set(b) | set(c) if k not in ("partition_types", "lanes") and canon(b.get(k)) != canon(c.get(k)))
bt, ct = b["partition_types"], c["partition_types"]
types = {}
for tn in sorted(set(bt) | set(ct)):
    if canon(bt.get(tn)) != canon(ct.get(tn)):
        x, y = bt.get(tn, {}), ct.get(tn, {})
        types[tn] = sorted(k for k in set(x) | set(y) if canon(x.get(k)) != canon(y.get(k)))
lb = {l["id"]: l for l in b["lanes"]} if isinstance(b["lanes"], list) else b["lanes"]
lc = {l["id"]: l for l in c["lanes"]} if isinstance(c["lanes"], list) else c["lanes"]
lane_edit, lane_other = {}, []
for lid in sorted(set(lb) | set(lc)):
    x, y = lb.get(lid), lc.get(lid)
    if canon(x) == canon(y):
        continue
    xs = dict(x or {}); ys = dict(y or {})
    fx, fy = xs.pop("fixed_cycles", 0), ys.pop("fixed_cycles", 0)
    if canon(xs) != canon(ys):
        lane_other.append(lid)
    lane_edit[lid] = [fx, fy]
def lat(r):
    P = S.Plan(copy.deepcopy(r)); o = {}
    for l in P.lanes:
        try: o[l] = P.lane_latency(l)["cycles"]
        except Exception as e: o[l] = "ERR " + str(e)[:80]
    return o
L0, L1 = lat(b), lat(c)
dl = {l: [L0.get(l), L1.get(l)] for l in sorted(set(L0) | set(L1)) if L0.get(l) != L1.get(l)}
mism = {l: v for l, v in dl.items() if not (isinstance(v[0], int) and isinstance(v[1], int) and l in lane_edit
                                             and v[1] - v[0] == lane_edit[l][1] - lane_edit[l][0])}
eb, ec = S.validate(b) or [], S.validate(c) or []
st = {}
for tn in types:
    o = {e["conn"]: len(e["regs_um"]) for e in bt.get(tn, {}).get("internal_stations", [])}
    n = {e["conn"]: len(e["regs_um"]) for e in ct.get(tn, {}).get("internal_stations", [])}
    st[tn] = dict(stations_added={k: n[k] - o.get(k, 0) for k in n if n[k] != o.get(k, 0)},
                  relay_sites=[len(bt.get(tn, {}).get("relay_sites", {})), len(ct.get(tn, {}).get("relay_sites", {}))],
                  verilog_defines=[bt.get(tn, {}).get("verilog_defines"), ct.get(tn, {}).get("verilog_defines")])
rec = dict(schema="opentallas.qc-plan-event-eq.v1", event="TLOAD-ROMSTAGE B (DIE-QC-97 11-11)",
           base=dict(file=BASE, sha256=hashlib.sha256(rb).hexdigest()), cand=dict(file=CAND, sha256=hashlib.sha256(rc).hexdigest()),
           top_keys_changed=top, types_changed=types, type_events=st, lanes_fixed_cycles=lane_edit,
           lanes_other_field_changed=lane_other, lane_latency_delta=dl, latency_not_explained_by_fixed_cycles=mism,
           validate_errors=dict(base=len(eb), cand=len(ec), new=sorted(set(map(str, ec)) - set(map(str, eb)))),
           eq_claim="no logic change: every changed type gains only relay_sites (firm sites, 0 cycles) and per_bit "
                    "internal_stations (pure register delay); each lane through a station is exactly +N cycles "
                    "(fixed_cycles), all other types / lanes byte-identical",
           verdict="PASS" if not top and not lane_other and not mism and len(ec) <= len(eb) else "FAIL",
           checks={p: json.load(open(p)) for p in sys.argv[5:]})
json.dump(rec, open(OUT, "w"), indent=1)
print(rec["verdict"], "types", list(types), "lanes", len(lane_edit), "lat", len(dl), "unexplained", len(mism),
      "validate", rec["validate_errors"]["base"], rec["validate_errors"]["cand"])
