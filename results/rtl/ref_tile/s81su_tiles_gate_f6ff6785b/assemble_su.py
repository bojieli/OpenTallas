#!/usr/bin/env python3
"""S81 SU routed-top gate record (s81su_tiles): assemble_su.py <fetched run dir> <gate commit> <fp> <out json>
Per routed-top class: the kept closed job, its commit, kit TOP / PARAMS / SRCS at that commit, and MODULE-level source
identity job commit == gate commit over the tile's hierarchy (every module reachable from the kit top by instantiation,
text with comments and whitespace runs removed).  qualified = exact pass AND this class's mutant fails with error rows AND
the kit top is the routed wrapper AND the hierarchy is identical AND the kit passes no parameter the gate does not."""
import json, re, subprocess, sys, hashlib, datetime, glob
from pathlib import Path
WT = Path("/home/ubuntu/wt/codex-s81su-physical"); R = Path(sys.argv[1]); GATE = sys.argv[2]; FP = sys.argv[3]; OUT = WT / sys.argv[4]
ST = Path.home() / ".local/state/closure_loop/jobs"
JOBS = {"dsfd_su_t_ctl": ["s81su_ctl_ref-v3-136b26407", "s81su_ctl_ref-v2-cbafa4c7a"], "dsfd_su_t_pin": ["dsfd_su_t_pin_rt-rt-77e72f74a"],
        "dsfd_su_t_qnt": ["s81su_qnt_cb32_ref-v6-cb32-c904b01fb"], "dsfd_su_t_qne": ["s81su_qne_ref-v2-8946ebc79"],
        "dsfd_su_t_qnh": ["s81su_qnh_ref-v4m-46d62c427"], "dsfd_su_t_qnr": ["s81su_qnr_ref-v4m-46d62c427"],
        "dsfd_su_t_qnq": ["s81su_qnq_sp8_ref-v5-sp8-2df2353b8"], "dsfd_su_t_kvt": ["s81su_kvt_ref-v2-cceaf47dc"],
        "dsfd_su_t_kve": ["s81su_kve_ref-v1-00167e741"], "dsfd_su_t_kvp": ["s81su_kvp_ref-v1-00167e741"],
        "dsfd_su_t_kvr": ["s81su_kvr_ref-v1-00167e741"], "dsfd_su_t_kvq": ["s81su_kvq_ref-v4-ebdb80f0e"],
        "dsfd_su_t_qbt": ["s81su_qbt_ref-v4-cceaf47dc"], "dsfd_su_t_qbe": ["s81su_qbe_sp8_ref-v5-sp8-2df2353b8"],
        "dsfd_su_t_swt": [], "dsfd_su_t_swe": ["s81su_swe_sp8_ref-v4-sp8-1ec43dde7"],
        "dsfd_su_t_smt": ["s81su_smt_hb2_ref-v2-hb2-ab43f2fe0"], "dsfd_su_t_sml": ["s81su_sml_ref-v1-47c31b637"],
        "dsfd_su_t_smc": ["s81su_smc_ref-v1-47c31b637"], "dsfd_su_t_smr": ["s81su_smr_ref-v1-47c31b637"],
        "dsfd_su_t_smd": ["s81su_smd_ref-v1-47c31b637"]}
git = lambda *a: subprocess.run(["git", "-C", str(WT), *a], capture_output=True, text=True)
show = lambda c, p: git("show", f"{c}:{p}").stdout


def mods(txt):
    t = re.sub(r"//[^\n]*", "", txt); t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    out = {}
    for m in re.finditer(r"\bmodule\s+(\w+)(.*?)\bendmodule\b", t, re.S):
        out[m.group(1)] = re.sub(r"\s+", " ", m.group(2)).strip()
    return out


def closure(top, allm):
    seen, todo = [], [top]
    while todo:
        n = todo.pop()
        if n in seen or n not in allm:
            continue
        seen.append(n)
        todo += [x for x in allm if x != n and re.search(r"\b%s\b\s*(#\s*\(|\w+\s*\()" % re.escape(x), allm[n])]
    return seen


tt = json.loads(next(R.glob("tg_*/tile_tops/tile_tops.json")).read_text()); tm = tt["tmut"]
runs = {}
for f in glob.glob(str(R / "tg*/run_*.json")):
    d = json.loads(Path(f).read_text()); runs[int(re.search(r"_t(\d+)\.json", f)[1])] = d
summ = lambda d: dict(status=d["status"], fp=d["fp"], runs=[dict(run=x["run"], err_rows=x["err_rows"], rows=x["rows"], cycles=x["cycles"], jobs_done=x["done"], fault=x["fault"]) for x in d["runs"]])
exact_ok = runs[0]["status"] == "pass" and all(x["err_rows"] == 0 and x["rows"] > 0 for x in runs[0]["runs"])
tiles = {}
for cls, k in sorted(tm.items(), key=lambda kv: kv[1]):
    mu = runs.get(k); mut_ok = bool(mu and mu["status"] == "fail" and all(x["err_rows"] > 0 for x in mu["runs"]))
    rows = []
    for jn in JOBS.get(cls, []):
        j = json.loads((ST / (jn + ".json")).read_text()); c = j["commit_full"]; kit = jn.split("-")[0]
        env = show(c, f"physical/ref_tile/{kit}/kit.env")
        top = re.search(r"^TOP=(\S+)", env, re.M)[1]; srcs = re.search(r"^SRCS='([^']*)'", env, re.M)[1].split()
        prm = re.search(r"^PARAMS=\((.*)\)", env, re.M); params = re.findall(r"--param (\S+)", prm[1]) if prm else []
        a, b = {}, {}
        for s in srcs:
            if s.endswith((".sv", ".v")):
                a.update(mods(show(c, s))); b.update(mods(show(GATE, s)))
        hier = closure(top, a)
        # a parameter the kit sets explicitly: its DEFAULT in the module headers is not part of the routed design, so the
        # default of exactly those parameters is masked on both sides (the kit value == the gate default is checked below)
        def mask(x):
            for p_ in params:
                x = re.sub(r"\b%s\s*=\s*\w+(?=\s*[,)])" % re.escape(p_.split("=")[0]), p_.split("=")[0] + " = <kit>", x)
            return x
        diff = [m for m in hier if mask(a.get(m, "")) != mask(b.get(m, "<missing>"))]
        raw_diff = [m for m in hier if a.get(m) != b.get(m)]
        # a kit parameter must be what the gate elaborates: the wrapper has none, so a kit --param must equal the wrapper /
        # core default at the gate commit (stated, compared by text of the default)
        pnote = []
        for p in params:
            n, v = p.split("=")
            dm = [re.search(r"parameter\s+(?:integer\s+)?[^;)]*?\b%s\s*=\s*([^,)\s]+)" % n, b.get(m, "")) for m in closure(top, b)]
            dv = next((x.group(1) for x in dm if x), None)
            pnote.append(dict(param=n, kit=v, gate_default=dv, same=(dv == v)))
        ok = top == cls and not diff and all(x["same"] for x in pnote)
        rows.append(dict(physical_job=jn, route_source=c[:9], kit=f"physical/ref_tile/{kit}", top=top, kit_params=pnote, status=j.get("status"),
                         reason=(j.get("reason") or "").split(" | ")[0], hierarchy=hier, modules_differing_route_vs_gate=diff, modules_differing_only_in_the_default_of_a_kit_parameter=[m for m in raw_diff if m not in diff], ok=ok))
    tiles[cls] = dict(tmut=k, mutant=summ(mu) if mu else None, mutant_fails_with_error_rows=mut_ok, routes=rows,
                      qualified=bool(exact_ok and mut_ok and any(r["ok"] and r["status"] == "CLOSED" for r in rows)))
out = dict(schema="opentallas.s81su.tile_top_gate.v2", generated=datetime.date.today().isoformat(), gate="s81su_tiles", gate_source=GATE, fp=FP,
           what="the SU slab dsfd_sp_su_h rebuilt by tools/s81_suhc/su_tile_tops.py so that every engine core instance is its ROUTED top dsfd_su_t_<x> (chosen at elaboration by parameter equality, port widths checked with $bits, wrapper ties asserted); su_gate.py run --shape full --hier --tiles --fp " + FP + "; one output mutant per routed-top class (+tmut=K)",
           instances=tt["n_instances"], classes=len(tm), unwrapped_cores_not_elaborated_in_the_full_shape=[u["core"] for u in tt["unwrapped"]],
           exact=summ(runs[0]), exact_ok=exact_ok, tiles=tiles,
           qualified=[c for c, t in tiles.items() if t["qualified"]], not_qualified={c: ("no closed route" if not t["routes"] else "mutant" if not t["mutant_fails_with_error_rows"] else "source / parameters differ or route not CLOSED") for c, t in tiles.items() if not t["qualified"]},
           scope="Standalone routed tops against the composition. Physical closure is each job's own verdict. Views exported before the export-SDC fix must be re-exported before a parent trusts them. SU throughput is judged per layer (el1013-rom-layer-tput-s81.log), not here.")
OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(out, indent=1) + "\n")
for c, t in tiles.items():
    print(c.ljust(16), "QUALIFIED" if t["qualified"] else "NOT      ", "mut", [x["err_rows"] for x in t["mutant"]["runs"]] if t["mutant"] else None,
          [(r["physical_job"], r["status"], r["top"], r["modules_differing_route_vs_gate"], [(p["param"], p["kit"], p["gate_default"]) for p in r["kit_params"]]) for r in t["routes"]])
print("exact", exact_ok, "qualified", len(out["qualified"]), "of", len(tiles))
