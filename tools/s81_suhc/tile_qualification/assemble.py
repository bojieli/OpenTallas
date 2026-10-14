#!/usr/bin/env python3
"""S81 HC per-tile qualification record, second batch (every other closed HC tile + the hard-pad gate).
  assemble2.py <fetched run dir> <bench commit> [<out json>]
Run dir layout (tools/s81_suhc/hc_tile_bench.sh): exact/ exacthard/ mut_<tile>/ hmut_<tile>/ each with run_*.json.
Per route (closed loop job) of a tile:
  effective tuple   = module defaults AT THE ROUTE COMMIT overridden by the kit.env PARAMS at the route commit
  production        = that tuple equals a tuple the probe saw in the bench, modulo parameters the module body cannot
                      depend on (hc_gate.tile_inert at the bench commit)
  body_identical    = module text after the parameter header, comments removed, route == bench (sha256)
  hierarchy_changed = modules under the tile (by name, over the kit's Verilog sources) whose text differs route..bench
A tile is qualified when the probe run is bit-exact with the tile only at routed tuples, its in-module mutant fails
with compared rows, and at least one route is production + body identical + hierarchy unchanged."""
import json, re, subprocess, sys, hashlib, datetime, importlib.util
from pathlib import Path
WT = Path("/home/ubuntu/wt/s81hc-1013"); R = Path(sys.argv[1]); BENCH = sys.argv[2]
OUT = WT / (sys.argv[3] if len(sys.argv) > 3 else "results/rtl/s81_suhc_20261013/hc_tile_qualification2_1013.json")
sp = importlib.util.spec_from_file_location("g", WT / "tools/s81_suhc/hc_gate.py"); g = importlib.util.module_from_spec(sp); sp.loader.exec_module(g)
JOBS = {
    "ot_s81_hc_cpin": ["s81hc_cpin_ref-v2-be8de3bc6"],
    "ot_s81_hc_caq": ["s81hc_caq_ref-v1-d02b035e3"],
    "ot_s81_hc_crx": ["s81hc_crxh2_ref-v1-70eafa55c", "s81hc_crx_ref-v1-d02b035e3"],
    "ot_s81_hc_ccr": ["s81hc_ccrh2_ref-v1-70eafa55c", "s81hc_ccr_ref-v1-ee56cc32d"],
    "ot_s81_hc_cseq": ["s81hc_cseqh2_ref-v1-70eafa55c", "s81hc_cseq_ref-v1-ee56cc32d"],
    "ot_s81_hc_cntree": ["s81hc_cntreeh2_ref-v1-70eafa55c", "s81hc_cntree_ref-v1-ee56cc32d"],
    "ot_s81_hc_ctfn": ["s81hc_ctfn_ref-v1-4c6ea9b8c"], "ot_s81_hc_ctfx": ["s81hc_ctfx_ref-v1-a9cfb97b9"],
    "ot_s81_hc_ctfs": ["s81hc_ctfs_ref-v1-a9cfb97b9"],
    "ot_s81_hc_ctpl": ["s81hc_ctpl_ref-v3-cx-pinstage-958724442"],
    "ot_s81_hc_ctrn": ["s81hc_ctrn_ref-v4-aligned-pins-65b479514"],
    "ot_s81_hc_crootr_t": ["s81hc_crrte_ref-v1-d71bc15c1", "s81hc_crrtw_ref-v1-d71bc15c1"],
    "ot_s81_hc_crootr_f": ["s81hc_crrfe_ref-v2-pinplan-f41de6496", "s81hc_crrfw_ref-v2-pinplan-f41de6496"],
    "ot_s81_hc_crootr_r": ["s81hc_crrre_ref-v2-pinplan-f41de6496", "s81hc_crrrw_ref-v2-pinplan-f41de6496"],
    "ot_s81_hc_crootr_w": ["s81hc_crrww_ref-v2-pinplan-f41de6496"],
}
JOBS1 = {"ot_s81_hc_pad_f8": ["s81hc_pad_f8_ref-v1-cx-relay-678198f73"], "ot_s81_hc_pad_meta2": ["s81hc_pad_meta2_ref-v1-cx-relay-21e8aac25"],
         "ot_s81_hc_pad_f5r1": ["s81hc_pad_f5r1_ref-v2-cx-lattice-21e8aac25"], "ot_s81_hc_pad_r5": ["s81hc_pad_r5_ref-v2-cx-lattice-21e8aac25"],
         "ot_s81_hc_pad_r6": ["s81hc_pad_r6_ref-v2-cx-lattice-21e8aac25"],
         "ot_s81_hc_ctnl_l0": ["s81hc_ctnl_l0_ref-fixed-lane-2f4ed494d"], "ot_s81_hc_ctnl_l1": ["s81hc_ctnl_l1_ref-fixed-lane-2f4ed494d"],
         "ot_s81_hc_ctnl_l2": ["s81hc_ctnl_l2_ref-fixed-lane-2f4ed494d"], "ot_s81_hc_ctnl_l3": ["s81hc_ctnl_l3_ref-fixed-lane-2f4ed494d"],
         "ot_s81_hc_crooty_w": ["s81hc_crywe_ref-v4-outhold-splice-a7343353d", "s81hc_cryww_ref-v3-outhold-276e553ee"]}
if not sorted(R.glob("mut_ot_s81_hc_cpin/run_*.json")):   # first batch (the ten tiles of tq_0c0a3fe61)
    JOBS = JOBS1
EXTRA = [x for x in sys.argv[4:]]                      # extra "tile=job" bindings
for x in EXTRA:
    t_, j_ = x.split("="); JOBS.setdefault(t_, []).append(j_)
ST = Path.home() / ".local/state/closure_loop/jobs"
git = lambda *a: subprocess.run(["git", "-C", str(WT), *a], capture_output=True, text=True)
show = lambda c, p: git("show", f"{c}:{p}").stdout
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()


def one(pat):
    f = sorted(R.glob(pat)); return json.loads(f[0].read_text()) if f else None


def summ(r):
    return None if r is None else dict(status=r["status"], pad_hard=r.get("pad_hard", 0), runs=[
        dict(run=x["run"], ok=x["ok"], err_rows=x.get("err_rows"), rows=x.get("rows"), cycles=x.get("cycles"), fault=x.get("fault")) for x in r["runs"]])


def modules(commit, srcs):
    """{module: text} over the Verilog sources at a commit"""
    out = {}
    for s in srcs:
        if not s.endswith((".sv", ".v")):
            continue
        t = show(commit, s)
        for m in re.finditer(r"(?ms)^module\s+(\w+).*?^endmodule", t):
            out[m.group(1)] = m.group(0)
    return out


def closure(mods, top):
    seen, todo = set(), [top]
    while todo:
        m = todo.pop()
        if m in seen or m not in mods:
            continue
        seen.add(m)
        todo += [x for x in set(re.findall(r"[A-Za-z_]\w*", re.sub(r"//[^\n]*", "", mods[m]))) if x in mods and x not in seen]
    return seen


exact, hard = one("exact/run_*.json"), one("exacthard/run_*.json")
gate_ok = bool(exact and exact["status"] == "pass")
out = dict(schema="opentallas.s81_hc.tile_qualification.v2", generated=datetime.date.today().isoformat(), bench_source=BENCH,
           method=__doc__.split("\n", 3)[3].strip() + " Bench: tools/s81_suhc/hc_tile_bench.sh (NG 256, HIER 3, CNL_PIN 1, CHAIN_STEP 6, LANE_SPECIALIZE 1; CPU golden of the 1M token + two stress runs).",
           shape=dict(ng=256, hier=3, cnl_pin=1, chain_step=6, lane_specialize=1),
           exact_probe=summ(exact),
           composition_gate_on_main=dict(exact=summ(one("main_m0/run_*.json")), mutant1=summ(one("main_m1/run_*.json")), note="NG256 production shape without the tile flags, at the bench source") if one("main_m0/run_*.json") else None,
           hard_pad_gate=dict(what="the same gate with OT_S81_HC_PAD_HARD: pad leaves and the ccr core instantiated with NO parameters (their hard views); ot_s81_hc_ccr defaults = HALF 1 / RLY 2 / RF 4 / DW 6",
                              exact=summ(hard), tiles={k: dict(ok=v["ok"], instances=v["instances"], params_seen=v["params_seen"], foreign=v["foreign"]) for k, v in ((hard or {}).get("tiles") or {}).items()
                                                      if k.startswith("ot_s81_hc_pad") or k == "ot_s81_hc_ccr"},
                              mutants={p.parent.name[5:]: summ(json.loads(p.read_text())) for p in sorted(R.glob("hmut_*/run_*.json"))}),
           scope="Standalone hard leaves. The HC parent assembly and the family throughput are not qualified by this record. ETM .lib views were re-exported on main after the export-SDC fix; the verdicts are the routes'.",
           tiles={})
h = out["hard_pad_gate"]
h["pass"] = bool(hard and hard["status"] == "pass" and h["mutants"] and all(m["status"] == "fail" and all(x.get("rows") for x in m["runs"]) for m in h["mutants"].values()))
for mod, jobs in JOBS.items():
    t = g.TILES[mod]; mut = one(f"mut_{mod}/run_*.json"); probe = (exact or {}).get("tiles", {}).get(mod)
    btext = show(BENCH, t["src"]); inert = g.tile_inert(btext, mod)
    cut = lambda q: {k: v for k, v in q.items() if k not in inert}
    bbody = sha(g._tile_head(btext, mod)[1])
    rows = []
    for jn in jobs:
        j = json.loads((ST / (jn + ".json")).read_text()); c = j["commit_full"]
        kit = jn.split("-")[0]
        env = show(c, f"physical/ref_tile/{kit}/kit.env")
        srcs = re.search(r"^SRCS='([^']*)'", env, re.M)[1].split()
        prm = re.search(r"^PARAMS=\((.*)\)", env, re.M)
        kp = {k: int(v) for k, v in re.findall(r"--param (\w+)=(-?\d+)", prm[1])} if prm else {}
        rtext = show(c, t["src"])
        eff = dict(g.tile_params(rtext, mod), **kp)
        added = sorted(k for k in g.tile_params(btext, mod) if k not in eff)      # parameters the module gained after the route
        cutr = lambda q: {k: v for k, v in q.items() if k not in inert and k not in added}
        prod = bool(probe and any(cutr(eff) == cutr(p) for p in probe["params_seen"]))
        ma, mb = modules(c, srcs), modules(BENCH, srcs)
        cl = closure(mb, mod) | closure(ma, mod)
        changed = sorted(m for m in cl if m != mod and ma.get(m) != mb.get(m))
        rb_, bb_ = g._tile_head(rtext, mod)[1], g._tile_head(btext, mod)[1]
        rbody = sha(rb_)
        import difflib
        dl = [x for x in difflib.unified_diff(rb_.splitlines(), bb_.splitlines(), lineterm="", n=0) if x[:1] in "+-" and x[:3] not in ("+++", "---")]
        lp = one(f"lpproof_{mod}.json")
        # a body that differs ONLY in localparam definitions is the same hardware when every differing localparam has the
        # same value in both elaborations (measured: lpproof_<tile>.json); this also covers parameters added since the route
        names = sorted({m for x in dl for m in re.findall(r"localparam\s+integer\s+(\w+)", x)})
        equiv = bool(dl and all(re.match(r"[+-]\s*localparam\b", x) for x in dl) and lp and lp.get("route_job") == jn
                     and all(n in lp["route"] and lp["route"][n] == lp["bench"].get(n) for n in names))
        rows.append(dict(physical_job=jn, route_source=c[:9], record=(j.get("publish") or {}).get("branch_commit", "")[:9], kit=f"physical/ref_tile/{kit}",
                         kit_params=kp, effective_params=eff, production=prod, reason=j.get("reason", "").split(" | ")[0],
                         module_text_identical=g.tile_sha(rtext, mod) == g.tile_sha(btext, mod), body_sha256=dict(route=rbody, bench=bbody), body_identical=rbody == bbody,
                         params_added_since_route=added, body_diff=dl, body_equivalent=dict(localparams=names, proof=lp) if equiv else None,
                         hierarchy_modules=len(cl), hierarchy_changed=changed,
                         ok=prod and not changed and (equiv or (rbody == bbody and not added))))
    mut_ok = bool(mut and mut["status"] == "fail" and any(not x["ok"] for x in mut["runs"]) and all(x.get("rows") for x in mut["runs"]))
    ok = bool(gate_ok and probe and probe["ok"] and mut_ok and any(r["ok"] for r in rows))
    out["tiles"][mod] = dict(qualified=ok, qualified_routes=[r["physical_job"] for r in rows if r["ok"]] if ok else [],
                             not_production_routes=[r["physical_job"] for r in rows if not r["production"]],
                             module_file=t["src"], inert_params=inert, routes=rows, probe=probe, mutant=dict(edit=list(t["mut"]), killed=mut_ok, result=summ(mut)))
out["all_qualified"] = all(t["qualified"] for t in out["tiles"].values())
OUT.write_text(json.dumps(out, indent=1) + "\n")
for mod, t in out["tiles"].items():
    mu = t["mutant"]["result"]
    print(mod.ljust(20), "QUALIFIED" if t["qualified"] else "NOT      ", "inst", (t["probe"] or {}).get("instances"), "probe_ok", (t["probe"] or {}).get("ok"),
          "mut", mu and [(x["err_rows"], x["rows"]) for x in mu["runs"]],
          "| routes", [(r["physical_job"].split("_ref")[0][6:], "prod" if r["production"] else "NOTPROD", "body" if r["body_identical"] else "EQUIV" if r["body_equivalent"] else "BODYDIFF", r["hierarchy_changed"]) for r in t["routes"]],
          "foreign", (t["probe"] or {}).get("foreign"), "inertdiff", (t["probe"] or {}).get("inert_differing"))
print("exact", summ(exact)); print("hard", h["pass"], summ(hard), h["tiles"]); print("hard mutants", h["mutants"])
