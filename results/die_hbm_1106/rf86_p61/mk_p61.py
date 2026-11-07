#!/usr/bin/env python3
"""DIE-HBM-86 d44v part 61 (COORD 11-07 09:20 svgr_bk (A)): ot_svgr_bk back to 259.2 x 207.36, the outline of signed DB svgrbk_e2.
mk_p61.py PLANDIR PRE_P53_DIE_PLAN.gz PRE_P53_CORE_MACROS PRE_P35_TABLE KIT_PINS   (in place on PLANDIR, on top of part 60)"""
import gzip, hashlib, json, sys
d, pre_plan, pre_macros, pre35, kit = sys.argv[1:6]
OLD = "cores/ot_svgr_bk__259.2x207.36__d44v_split.json"; P53 = "cores/ot_svgr_bk__302.4x207.36__d44v_p53.json"; NEW = "cores/ot_svgr_bk__259.2x207.36__d44v_p61.json"
SITE = [21.72, 103.68]
def gzw(path, raw):
    with open(path, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g: g.write(raw)
    return hashlib.sha256(raw).hexdigest()
def dump(o): return (json.dumps(o) + "\n").encode()
cur = json.load(gzip.open(f"{d}/die_plan.json.gz")); pre = json.load(gzip.open(pre_plan)); new = cur
# only the core rows and their taps go back. Station chains keep their part 53 sites: they clear the 302.4 outline, so they clear 259.2, and undoing them brings back L40_i hops > 405 um
n = 0; tapn = 0
for q in ("q_hub_nw", "q_hub_ne"):
    t, p0 = new["partition_types"][q], pre["partition_types"][q]
    a = {c["inst"]: c for c in p0["hard_cores"]}; insts = set()
    for c in t["hard_cores"]:
        if c.get("module") == "ot_svgr_bk":
            o = a[c["inst"]]; assert o["pins_file"] == OLD
            for k in ("origin_um", "outline_um", "note"): c[k] = o[k]
            c["pins_file"] = NEW; n += 1; insts.add(c["inst"])
    ta = {k["name"]: k for k in p0["clock"]["taps"]}
    for k in t["clock"]["taps"]:
        if k["name"] in insts:
            k["xy"] = ta[k["name"]]["xy"]; k["note"] = ta[k["name"]].get("note"); tapn += 1
assert n == 16 and tapn == 16, (n, tapn)
raw35 = open(pre35, "rb").read(); t = json.loads(raw35)
k = json.load(open(kit)); kn = {(p["bus"] if p["bit"] is None else f"{p['bus']}[{p['bit']}]"): p for p in k}
assert set(kn) == {p["name"] for p in t} and len(t) == 2255
bad = [p["name"] for p in t if kn[p["name"]]["layer"] != p["layer"] or abs(kn[p["name"]]["x"] - p["x"]) > 0.1 or abs(kn[p["name"]]["y"] - p["y"]) > 0.1]
assert not bad, bad
assert [p for p in t if p["name"] == "stream_clk"][0]["x"] == SITE[0]
ts = gzw(f"{d}/{NEW}.gz", raw35)
ps = gzw(f"{d}/die_plan.json.gz", dump(new))
ce = json.load(gzip.open(f"{d}/clock_entries.json.gz")); m = 0
for q, v in ce.items():
    if isinstance(v, dict):
        for e in v.values():
            if isinstance(e, dict) and e.get("module") == "ot_svgr_bk":
                assert e["clock_pin_sites_um"]["stream_clk"] == [22.008, 103.68]; e["clock_pin_sites_um"]["stream_clk"] = SITE; m += 1
assert m == 16
cs = gzw(f"{d}/clock_entries.json.gz", dump(ce))
mp = json.load(open(pre_macros)); mc = json.load(open(f"{d}/core_macros.json"))
for key in ("cores",):
    diffk = [x for x in set(mp[key]) | set(mc[key]) if mp[key].get(x) != mc[key].get(x)]
    assert all("svgr_bk" in x or "ot_svgr_bk" in json.dumps(mc[key].get(x))[:200] for x in diffk), diffk
raw_m = open(pre_macros, "rb").read(); open(f"{d}/core_macros.json", "wb").write(raw_m); ms = hashlib.sha256(raw_m).hexdigest()
L = "core\tsub_block\tport_or_bus\tdir\tadded_cycles\tnote\not_svgr_bk\t\tcomplete,complete_bank,bfault\tport\t1\tDIE-HBM-86 part 61: signed svgrbk_e2 is VARIANT 1 (vB, ot_svgr_bk_b12.sv): landing write, complete and bank fault +1 stream_clk per packet vs B8, at most one packet per two stream cycles per landing bank; credits cr follow the later pops; bench results/die_hbm_1105/reform_b12/svgr_bk\n"
open(f"{d}/corelat/cycles_svgr_bk_vB_1107.tsv", "w").write(L); ls = hashlib.sha256(L.encode()).hexdigest()
ev = {"schema": "opentallas.hbm_plan_event.v1", "part": 61, "plan": "d44v", "lane": "DIE-HBM-86", "date": "2026-11-07", "approved": "COORD 11-07 09:20 svgr_bk (A)",
      "what": ["ot_svgr_bk 16 instances: outline, origin, clock taps and core_macros outline return to their pre-part-53 values (from die_plan of 01a61d4b8ca^1)", "part 53 station chain sites stay: they clear the larger outline, and undoing them brings back L40_i hops > 405 um (G0C)",
               "table " + NEW + " = pre-p35 table bytes (510f347b9f^): stream_clk M5 21.72, the signed DB's site; clock_pin_sites_um stream_clk follows on 16 rows",
               "corelat/cycles_svgr_bk_vB_1107.tsv records the +1 on complete, complete_bank, bfault that the signed RTL carries"],
      "kept": ["part 53 internal_stations regs_um", "svgr_own RF3 recipe, RTL ifdef and corelat row: not part of the die_plan diff", "302.4 table file stays on disk, unused"],
      "signed_db": {"record": "epyc2 die-hbm-85/eco/svgrbk_e2_resign_dq", "rtl": "ot_svgr_bk_b12.sv VARIANT 1, identical to main except module name __fcore", "build_commit": "acdb25db4ae2"}}
json.dump(ev, open(f"{d}/part61_event.json", "w"), indent=1); open(f"{d}/part61_event.json", "a").write("\n")
es = hashlib.sha256(open(f"{d}/part61_event.json", "rb").read()).hexdigest()
s = []
for l in open(f"{d}/SHA256SUMS").read().splitlines():
    h, name = l.split(None, 1); name = name.strip()
    s.append({"die_plan.json": f"{ps}  {name}", "clock_entries.json": f"{cs}  {name}", "core_macros.json": f"{ms}  {name}"}.get(name, l))
s += [f"{ts}  {NEW}", f"{ls}  corelat/cycles_svgr_bk_vB_1107.tsv", f"{es}  part61_event.json"]
open(f"{d}/SHA256SUMS", "w").write("\n".join(s) + "\n")
print("OK", n, m, ts[:12], ps[:12], cs[:12], ms[:12])
