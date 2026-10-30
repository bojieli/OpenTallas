"""DIE-QC-48 QC COLLFT acceptance test for core_forest (FLOW-9 8bc5475ee9f). Usage: collft_accept.py <tools/die_plan dir> <fixture dir> <work>"""
import copy, gzip, hashlib, json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import core_infra as CI, master_slice as MS
fx, work = Path(sys.argv[2]), Path(sys.argv[3]); work.mkdir(parents=True, exist_ok=True)
CI.REPO = work
fix = json.load(open(fx / "forest_fixture.json"))
trees = json.load(gzip.open(fx / "tree_packed_actual_pins.json.gz"))
models = json.load(gzip.open(fx / "packed_full_models.json.gz"))
outline = fix["outline_um"]
LAT = dict(TT=250, FF=202.5)

def prefixed(tree, pre, port):
    t = copy.deepcopy(tree)
    mc = models[port]["corners"]
    lm = {c: {l["node"]: l for l in mc[c]["leaf_means"]} for c in ("TT", "FF")}
    for l in t["leaves"]:
        l["pin_latency_ps"] = {c: dict(min=lm[c][l["node"]]["min_ps"], max=lm[c][l["node"]]["max_ps"]) for c in ("TT", "FF")}
    ren = {n["name"]: pre + n["name"] for n in t["nodes"]}
    for n in t["nodes"]:
        n["name"] = ren[n["name"]]
        n["parent"] = ren.get(n["parent"], n["parent"])
    for l in t["leaves"]:
        l["node"] = ren[l["node"]]
        l["sinks"] = [s + "/CLK" for s in l["sinks"]]   # QC graph must spell inst/pin (fixture = instance names)
    for g in t.get("gates", []):
        g["parent"] = ren.get(g["parent"], g["parent"])
    t.pop("coordinate_basis", None)
    # HARNESS ONLY: the fixture carries no model_qualification block; the real QC graph must supply it
    t["model_qualification"] = dict(measured_timing_used=False, electrical_latency_qualified=True, source="HARNESS codex 515014cc720 packed_full_models", model="joint_nldm (fixture)", band_policy="info", window_policy="info", corners={c: dict(slew_max=mc[c]["slew_max_ps"], leaf_min=min(l["pin_latency_ps"][c]["min"] for l in t["leaves"]), leaf_max=max(l["pin_latency_ps"][c]["max"] for l in t["leaves"])) for c in ("TT", "FF")})
    for c in ("TT", "FF"):
        q = t["model_qualification"]["corners"][c]; q["leaf_window"] = q["leaf_max"] - q["leaf_min"]
    return t

def build(ports):
    forest, ents = [], []
    for k, p in enumerate(ports):
        e = next(x for x in fix["clock_entries"] if x["port"] == p)
        pre = f"f{k}_"
        t = prefixed(trees[p]["core_tree"], pre, p)
        sinks = sorted(s for l in t["leaves"] for s in l["sinks"])
        f = work / f"sinks_{k}.txt.gz"
        f.write_bytes(gzip.compress(("".join(s + "\n" for s in sinks)).encode(), mtime=0))
        forest.append(dict(clock_port=p, name_prefix=pre, sinks_file=f.name,
                           sinks_sha256=hashlib.sha256(f.read_bytes()).hexdigest(), latency=dict(LAT), tree=t))
        ents.append(dict(port=p, island=f"isl{k}", clock_pin=dict(layer="M5", xy_um=e["xy_um"]),
                         latency=dict(common_clock_latency_ps=dict(LAT))))
    return dict(schema=MS.SCHEMA, die="qwen_compute", type="coll_ft", master_plan_sha256="0"*64, frozen=False, module=fix["module"], kind="core", outline_um=outline, pushdown={"islands": []},
                islands=[dict(name=f"isl{k}", rect_um=[0, 0, *outline]) for k in range(len(ports))], bays=[],
                clock_entries=ents, core_forest=forest, pg_obstructions_um={})

res = {}
def case(name, fn, expect_ok, needle=None):
    try:
        out = fn(); ok = True; msg = out
    except (CI.InfraError, SystemExit, ValueError, KeyError) as exc:
        ok = False; msg = str(exc)
    good = (ok == expect_ok) and (expect_ok or needle is None or needle in msg)
    res[name] = dict(result="PASS" if good else "FAIL", ok=ok, msg=str(msg)[:300])
    print(f"{'PASS' if good else 'FAIL'} {name}: {res[name]['msg']}")

def validate(sl):
    errs = MS.validate(sl)
    if errs: raise ValueError("; ".join(errs[:3]))
    return "validate 0 errors"

def full(sl):
    validate(sl)
    plan = CI.compile_slice(sl)
    tcl = CI.emit_tcl(sl)
    cts = CI.emit_cts_tcl(plan)
    n = sum(f["sinks"] for f in plan["core_forest"])
    begins = tcl.count("\not_ci_tree_begin "); fin = tcl.count("\not_ci_tree_finish")
    return f"roots {len(plan['core_forest'])} cells {len(plan['cells'])} sinks {n} begin/finish {begins}/{fin} tcl_sha {hashlib.sha256(tcl.encode()).hexdigest()[:12]} cts_open {cts.splitlines()[1]}"

RCLK = [e["port"] for e in fix["clock_entries"] if e["kind"] == "RCLK"]
ALL = [e["port"] for e in fix["clock_entries"]]
case("RCLK8 validate+compile+emit", lambda: full(build(RCLK)), True)
case("ALL15 validate+compile+emit", lambda: full(build(ALL)), True)
# negative mutants (must fail closed)
def m_shared():
    sl = build(RCLK); a, b = sl["core_forest"][0], sl["core_forest"][1]
    s = a["tree"]["leaves"][0]["sinks"][0]; b["tree"]["leaves"][0]["sinks"].append(s)
    f = work / b["sinks_file"]; pins = gzip.decompress(f.read_bytes()).decode().split(); pins.append(s)
    f2 = work / "mut_shared.txt"; f2.write_text("".join(p + "\n" for p in pins))
    b["sinks_file"] = f2.name; b["sinks_sha256"] = hashlib.sha256(f2.read_bytes()).hexdigest()
    return full(sl)
case("mutant shared sink across roots", m_shared, False, "shared")
def m_missing():
    sl = build(RCLK); a = sl["core_forest"][2]; a["tree"]["leaves"][0]["sinks"].pop()
    return full(sl)
case("mutant tree drops a listed sink", m_missing, False, "sinks_file")
def m_sha():
    sl = build(RCLK); sl["core_forest"][1]["sinks_sha256"] = "0" * 64; return full(sl)
case("mutant sinks sha mismatch", m_sha, False, "sha256")
def m_port():
    sl = build(RCLK); sl["core_forest"].pop(); return full(sl)
case("mutant forest misses a clock_entries root", m_port, False, "exactly")
def m_prefix():
    sl = build(RCLK); t = sl["core_forest"][3]["tree"]; old = t["nodes"][-1]["name"]; new = "f0_" + old[3:]
    t["nodes"][-1]["name"] = new
    for n in t["nodes"]:
        if n["parent"] == old: n["parent"] = new
    for l in t["leaves"]:
        if l["node"] == old: l["node"] = new
    return full(sl)
case("mutant node outside its root prefix", m_prefix, False, "name_prefix")
def m_lat():
    sl = build(RCLK); sl["core_forest"][0]["latency"]["TT"] = 260; return full(sl)
case("mutant latency != 12.3 entry budget", m_lat, False, "latency")
def m_mixed():
    sl = build(RCLK); sl["core_tree"] = sl["core_forest"][0]["tree"]; return full(sl)
case("mutant core_tree beside core_forest", m_mixed, False, None)
def m_scope():
    sl = build(RCLK); sl["core_forest"][0]["tree"]["root_scope"] = {"x": 1}; return full(sl)
case("mutant root_scope inside forest", m_scope, False, "fail-closed")
def m_dup():
    sl = build(RCLK); sl["core_forest"][1]["clock_port"] = sl["core_forest"][0]["clock_port"]; return full(sl)
case("mutant root listed twice", m_dup, False, None)
json.dump(res, open(work / "collft_accept.json", "w"), indent=1)
print("OVERALL", "PASS" if all(r["result"] == "PASS" for r in res.values()) else "FAIL", f"{sum(r['result']=='PASS' for r in res.values())}/{len(res)}")
