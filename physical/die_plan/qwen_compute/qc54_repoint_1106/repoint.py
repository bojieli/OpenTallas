"""DIE-QC-85 11-06: fix-only plan event v3 -> v4. Re-pick START raw resets that the tap class / resite edits moved.
Stage xy, depths and stage counts stay. Only references whose relay changed (name absent, or other site/depth/kind
between the v2 and v3 live trees) are re-picked, by the START4 rule: nearest non-exported, non-port live relay; local
reset copies keep depth(raw)+1 == depth(old consumer reset), so no release edge moves."""
import copy, json, re, sys
from pathlib import Path
S = Path(sys.argv[1]); PRE = Path(sys.argv[2]); OUT = Path(sys.argv[3])
sys.path[:0] = [str(S / "tools/die_plan"), str(S / "tools/s81_head")]
import schema, reset_tree as RT, clock_landings as CL, head_cland_stage_delta as H
pa = "/srv/opentallas-scratch3/claude/dq85/qc53root/qc53v2.json"
pb = S / "physical/die_plan/qwen_compute/plan_of_record/plan_qc53_candidate_v3.json"
side = json.loads((S / "physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar.json").read_text())
A = schema.Plan(schema.load(pa), Path(pb).resolve()); B = schema.Plan(schema.load(str(pb)), Path(pb).resolve())
base = json.loads(Path(pb).read_text()); new = copy.deepcopy(base)
def site(T): return {x["q"]: (tuple(x["xy"]), x.get("depth"), x.get("kind")) for x in T["relays"]}
def live(tn):
    txt = (PRE / f"{tn}.sv").read_text()
    outs = set(re.findall(r"\boutput\s+(?:wire\s+|reg\s+)?(?:\[[^\]]*\]\s*)?(\w+)", txt))
    bad = lambda n: n in outs or any(o in outs for o in re.findall(r"\bassign\s+(\w+)\s*=\s*" + re.escape(n) + r"\s*;", txt))
    rr = [r for r in H.rrl_from_rtl(PRE / f"{tn}.sv") if not bad(r[0])]
    return txt, rr
def graph_depth(text):
    out = {}
    for m in re.finditer(r"\bot_dp_r(?:relay|gate)(?:_nl)?\s+(\w+)\s*\(([^;]*?)\);([^\n]*)", text, re.S):
        ps = dict(re.findall(r"\.(clk|d|q)\(\s*(\w+)\s*\)", m[2])); d = re.search(r"\bdepth (\d+)\b", m[3])
        if "q" in ps: out[ps["q"]] = dict(ps, depth=int(d[1]) if d else None)
    def depth(net, seen=()):
        if net in seen: raise ValueError(("loop", net))
        if net in out:
            z = out[net]
            if z["depth"] is None: z["depth"] = depth(z["d"], seen + (net,)) + 1
            return z["depth"]
        a = re.search(r"\bassign\s+" + re.escape(net) + r"\s*=\s*(\w+)\s*;", text)
        if a: return depth(a[1], seen + (net,))
        if net in ("rst_n", "rst_root_n", "arst_n"): return 0
        raise ValueError(("no depth", net))
    return depth
report = {}
for tn, t in new["partition_types"].items():
    c = t.get("clock", {})
    refs = []
    for key in ("landing_writer_start", "landing_reader_start"):
        for bus, br in (c.get(key) or {}).get("branches", {}).items():
            refs += [(key, bus, i, st) for i, st in enumerate(br.get("stages", []))]
    loc = c.get("landing_local_resets") or []
    if not refs and not loc: continue
    Ta, Tb = RT._wf_type_tree(A, tn), RT._wf_type_tree(B, tn)
    ma, mb = site(Ta), site(Tb)
    moved = lambda n: ma.get(n) != mb.get(n)
    txt, rr = live(tn); names = {r[0]: r for r in rr}
    rows = []
    for key, bus, i, st in refs:
        old = st["raw_reset"]
        if not moved(old) and old in names: continue
        r = H.nearest(rr, st["xy_um"], allow_exported=False)
        st["raw_reset"] = r[0]
        rows.append(dict(kind=key, bus=bus, stage=i, old=old, new=r[0], xy=st["xy_um"], hop_um=round(H.md(r[2:4], st["xy_um"]), 1),
                         old_v2_hop_um=round(H.md(ma[old][0], st["xy_um"]), 1) if old in ma else None))
    if any(moved(l["raw"]) or l["raw"] not in names for l in loc):
        tmp = copy.deepcopy(new); tmp["partition_types"][tn]["clock"].pop("landing_local_resets")
        L0 = CL.Landings(tmp, side); text0 = L0.type_rtl(tn, txt, base=tn); depth = graph_depth(text0)
        bands = c["landing_contract"]["bands"]; rects = [v["rect_um"] for v in bands.values()]
        pins = H.pins_of(t)
        for l in loc:
            cons = l["consumers"][0]
            m = re.search(r"\b" + re.escape(cons) + r"\s*\(([^;]*?)\);", text0, re.S)
            oldrst = re.search(r"\.(?:rst_raw_n|rst_n)\(\s*(\w+)\s*\)", m[1])[1]; want_d = depth(oldrst) - 1
            xy = l["xy_um"]                        # the planned copy site stays when both hops stay legal
            if cons.startswith("u_cland_fstart_"): cxy = pins["cland_fstart_out_" + cons[len("u_cland_fstart_"):]]
            else: cxy = c["landing_reader_start"]["origin_rect_um"]; cxy = [(cxy[0] + cxy[2]) / 2, (cxy[1] + cxy[3]) / 2]
            cand = sorted((z for z in rr if z[1] == want_d and not z[4]), key=lambda z: H.md(z[2:4], cxy))
            for z in cand:
                d = H.md(z[2:4], cxy)
                if d > 740: continue
                wnt = cxy if d <= 296 else ((cxy[0] + z[2]) / 2, (cxy[1] + z[3]) / 2)
                cp = H.snap_point(wnt, rects, t["outline_um"])
                if H.md(cp, z[2:4]) <= 370 and H.md(cp, cxy) <= 370: break
            else: raise ValueError((tn, cons, "no legal same-depth copy", want_d))
            rows.append(dict(kind="local", consumer=cons, old=l["raw"], new=z[0], depth=want_d, raw_hop_um=round(H.md(cp, z[2:4]), 1),
                             consumer_hop_um=round(H.md(cp, cxy), 1), old_xy=l["xy_um"], xy=H.rnd(cp)))
            l["raw"] = z[0]; l["xy_um"] = H.rnd(cp)
    if rows: report[tn] = rows
new["reset"]["relay_resite_crossing"] = True      # QC opts in; the tool default goes OFF
for tn in new["partition_types"]:
    if tn not in report and tn in base["partition_types"]: assert new["partition_types"][tn] == base["partition_types"][tn]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "plan_qc53_candidate_v4.json").write_text(json.dumps(new, separators=(", ", ": ")) + "\n")
(OUT / "repoint_report.json").write_text(json.dumps(report, indent=1) + "\n")
# in-process check of the START emission on every dumped type, before the 15-min bind
L = CL.Landings(new, side); errs = {}; done = 0
for tn, ps in sorted(new["partition_types"].items()):
    f = PRE / f"{tn}.sv"
    if not f.exists(): continue
    try: L.type_rtl(tn, f.read_text(), base=new["partition_types"][tn].get("split_of", tn)); done += 1
    except Exception as e: errs[tn] = str(e)[:300]
print("types repicked", len(report), "refs", sum(len(v) for v in report.values()), "emit ok", done, "errs", len(errs))
for k, v in errs.items(): print(" ERR", k, v)
h = [r for v in report.values() for r in v]
print("max stage hop", max([r.get("hop_um", 0) for r in h] or [0]), "max raw hop", max([r.get("raw_hop_um", 0) for r in h] or [0]))
for k, v in report.items(): print(k, len(v), max([r.get("hop_um", r.get("raw_hop_um", 0)) for r in v]))
