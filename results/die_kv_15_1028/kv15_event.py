# DIE-KV-15: KV source event on the FISHBONE clock (DIE-KV-14 c, proofF measured fall, rebuilt on the core_tx 164.16 plan hm_r26q15c);
# = DIE-KV-13 kv13_event.py with paths changed only.  DIE-KV-13 header:
# DIE-KV-13: KV source event on the INVERTER clock (DIE-KV-12 inv r150 phase bind) + ECTL K round-trip equalisation
# (Codex ectl_ca_candidate.py / compose_ectl.py recipe, re-run on the new table; no tool fork: main/worktree tools imported).
#  1. reproduce the DIE-KV-12 phase bind in-process (same argv as ca.sh), capturing the count_align plan doc;
#  2. ECTL RT per frame by the landed-stage model (bind_s2 bus_groups mapping, landed = sum sched_lat + lane constant, CHECKED
#     on bind_s2: RT20 32/32); target = max RT; extra cycles on one non-tree request crossing into the ectl sink partition
#     (Codex eligibility: L_hi + d*T <= 7.5T - ap, depth re-derived 4/8, lo >= T/2 + ap);
#  3. re-bind (parts = ocv rows), verify, annotate l128_table strap form, compose (q9d + die_io, reset monitor, observer
#     hub_C, band_reserve live), latency, straps.
import json, sys, copy, os, collections
from pathlib import Path
W = Path("/srv/opentallas-scratch2/claude/wt/die-kv-15"); sys.path.insert(0, str(W / "tools/die_plan"))
import count_align_bind as CB
R12 = Path("/srv/opentallas-scratch2/claude/die-kv-15-1028"); O = Path(sys.argv[1]); O.mkdir(parents=True, exist_ok=True)
P = R12 / "proofF_fb"; PL = str(R12 / "hm_r26q15c.json")
argv = [str(R12 / "ca_fb_inv_r150/fb_inv_r150_spice_xing_lpo.json"), "--from-ocv", "--parts", "ocv", "--sta-proof", str(P),
        "--sta-plan", PL, "--sta-clock-cal", "spice", "--sta-cppr-lca", "--sta-clock-ocv", "table", "--sta-clock-droop", "shared", "--sta-clock-cell", "inv",
        "--sta-droop-regions", str(P / "droop_regions.json"), "--sta-core-latency-ff", "202.5", "--start-tree", "clock",
        "--start-clean", "phase", "--samples", "500", "--out", str(O / "repro_bind.json")]
cap = {}
_bind = CB.bind
def bind(plan, *a, **k):
    cap.setdefault("plan", copy.deepcopy(plan)); cap.setdefault("parts", k.get("parts"))
    return _bind(plan, *a, **k)
CB.bind = bind
rc = CB.main(argv)
CB.bind = _bind
p = cap["plan"]; parts = cap["parts"]
(O / "plan_doc.json").write_text(json.dumps(p, indent=0) + "\n")
ref = json.load(open(R12 / "ca_fb_inv_r150/st_fall_bind_parts.json"))["ports"]
rep = json.load(open(O / "repro_bind.json"))["ports"]
ndiff = sum(1 for k in ref if (ref[k]["K"], ref[k]["depth"], ref[k]["sched_lat"]) != (rep[k]["K"], rep[k]["depth"], rep[k]["sched_lat"]))
print("REPRO rc", rc, "ports", len(rep), "diff vs DIE-KV-12 st_phase_bind_parts", ndiff, flush=True)
assert ndiff == 0
# 2. ECTL equalisation
bg = json.load(open("/srv/opentallas-scratch2/claude/die-kv-8-1028/bind_s2/bus_groups.json"))
side0 = json.load(open(W / "results/die_kv_7_1028/event_ectl/sidecar.json")); ca0 = side0["count_aligned"]["ports"]
bylane = collections.defaultdict(list)
for r in side0["ports"]:
    bylane[r["lane"]].append(r)
def dl(m): return sum(rep[x["port"]]["sched_lat"] - ca0[x["port"]]["sched_lat"] for x in bylane[m["lane"]])
req = collections.defaultdict(list); rsp = collections.defaultdict(list)
for g in bg["landing"]:
    for m in g["members"]:
        sp, _, pn = m["source"].rpartition(".")
        if pn.startswith("req_") and m["sink_port"] == "kreq": req[sp].append((g, m))
        if m["sink_port"].startswith("rsp_") and "ectl" in g["sink"]: rsp[g["sink"]].append((g, m))
RT = {s: 8 + next(iter({m["landed_stages"] + dl(m) for _, m in v})) + next(iter({m["landed_stages"] + dl(m) for _, m in rsp[s]}))
      for s, v in req.items()}
target = max(RT.values()); T = float(p["summary"]["period_ps"]); ap = float(p["summary"]["aperture_ps"])
rows = {r["port"]: r for r in p["crossings"]}; extra = {}; bad = []
for s in sorted(req):
    d = target - RT[s]
    if not d: continue
    for g, m in req[s]:
        ports = [x for x in bylane[m["lane"]] if x["dst"] == g["sink_part"]]
        el = [x for x in ports if rows[x["port"]]["kind"] == "nontree" and rows[x["port"]]["L_hi_ps"] + d * T <= 7.5 * T - ap + 1e-6]
        if not el: bad.append(dict(frame=s, lane=m["lane"], ports=[x["port"] for x in ports])); continue
        q = el[-1]["port"]; assert q not in extra or extra[q]["frame"] == s, (q, s); extra[q] = dict(cycles=d, frame=s, oldRT=RT[s], target=target)
print("ECTL RT", dict(collections.Counter(RT.values())), "target", target, "extra rows", len(extra), "cycles",
      sum(e["cycles"] for e in extra.values()), "bad", len(bad), flush=True)
assert not bad, bad
before = copy.deepcopy(p)
for port, e in extra.items():
    r = rows[port]; d = e["cycles"]; lo = r["L_lo_ps"] + d * T; hi = r["L_hi_ps"] + d * T
    depth = 4 if hi <= 3.5 * T - ap + 1e-6 else 8 if hi <= 7.5 * T - ap + 1e-6 else None
    assert depth is not None and lo >= .5 * T + ap - 1e-6, (port, lo, hi)
    for k in ("K_eff", "K", "lat_cycles", "rx_lat_counts"): r[k] += d
    r.update(L_lo_ps=round(lo, 1), L_hi_ps=round(hi, 1), depth=depth, margin_lo_ps=round(lo - .5 * T, 1),
             margin_hi_ps=round((depth - .5) * T - hi, 1))
    r["rtl"].update(K=r["K"], DEPTH=depth, GUARD_HI=depth)
assert p["regions"] == before["regions"]
p["summary"]["extra_data_latency"] = dict(scope="DIE-KV-15 KV ECTL equalisation on the fishbone proofF phase bind (DIE-KV-13 / Codex RT20 recipe)",
                                         edges=extra, aggregate_crossing_cycles=sum(x["cycles"] for x in extra.values()))
b = CB.bind(p, parts=parts); v = CB.verify(b, samples=500); rp = CB.report(b, v); rp["relay"] = CB.relay_summary(b)
rp["plan_source"] = "DIE-KV-15 fishbone proofF phase (repro of st2 fall) + ECTL extra"; b["report"] = rp
(O / "bind.json").write_text(json.dumps(b, indent=0) + "\n")
print("VERIFY", json.dumps(v)[:600], flush=True)
assert not v["identity_and_loop_errors"] and v["sim_window_violations"] == 0
# 3. compose (Codex compose_ectl.py recipe)
import clock_landing_plan as LP, gen
I = W / "results/die_kv_7_1028/input"; E = O / "event"; E.mkdir(exist_ok=True)
raw = json.load(open(I / "hm_r26q15d.json")); raw["die"]["io"] = json.load(open(I / "die_io.json"))
table = CB.annotate_table(json.load(open(I / "l128_table.json")), b, strap_form=True)
(E / "regions_ca.json").write_text(json.dumps(table, indent=1) + "\n")
observer = dict(module="qkd_seq_core_static_s", instance_suffix="u_seq_u_core", fault_port="hf", ready_port="lp_run")
plan, side = LP.compose(raw, table, plan_path=I / "hm_r26q15d.json", observer_part="hub_C", observer=observer, monitor="reset",
                        band_reserve="live", forward_source="clk")
for typ in plan["partition_types"].values():
    for h in typ.get("hard_cores", []):
        if h.get("pins_file") and not Path(h["pins_file"]).is_absolute():
            h["pins_file"] = os.path.relpath((I / h["pins_file"]).resolve(), E)
plan["note"] = plan.get("note", "") + " | DIE-KV-15: fishbone (DIE-KV-14 c) measured-fall proofF phase K + core_tx 164.16 slot (DIE-KV-14a) + ECTL RT equalisation"
(E / "plan.json").write_text(json.dumps(plan, indent=1) + "\n"); (E / "sidecar.json").write_text(json.dumps(side, indent=1) + "\n")
gen.write_latency(plan, E / "latency", E / "plan.json")
st = CB.strap_ties(side["count_aligned"], plan); (E / "straps.json").write_text(json.dumps(st, indent=1) + "\n")
print("COMPOSE", json.dumps(dict(types=len(plan["partition_types"]), parts=len(plan["partitions"]), straps=st["summary"],
      placement_failures=len(side.get("collector", {}).get("placement_failures", side.get("placement_failures", []))))), flush=True)
