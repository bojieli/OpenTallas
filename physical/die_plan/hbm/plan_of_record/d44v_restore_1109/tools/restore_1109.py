#!/usr/bin/env python3
"""DIE-HBM-97/RESTORE 11-09: plan event restore_1109 on the HBM final d44v_corepins_1109 (sha256 3742832d6eb33412).

The final was built on plan_final3 and lost five signed hard-core forms that the d44v lineage carries.  This replays the
five original d44v events, in their original order, each with its own script or its own logic, on a plain plan dir
(die_plan.json, clock_entries.json, core_macros.json, core_conns.json, cores/ as the final's materialized dir):

  1 part60        (7de1e0f41b, mk_p60.py logic)      ot_hgi_coll_inj_idx_join_rg table drops 31 read-nothing pins
  2 part61        (bbda1ab30f, mk_p61.py logic)      ot_svgr_bk back to 259.2 x 207.36 (pre-part-53 rows/taps)
  3 expx328_1107  (ccbad2a1c5, mk_expx328.py as is + replay.sh post steps ft_nudge / ft_reach_fix / ft_s0_resite --medoid-fix)
  4 qcore267_1107 (0cf1ab2aa7)                        ot_hbm_su_static_qcore_r13 table drops slice_t[267]
  5 opsarest_c2_1107 (834d940a5e, mk_opsarest_c2.py as is, on a gz shim of the plan dir)

    restore_1109.py PLANDIR REPO HIST OUT_EVENT_JSON
  REPO = repo root (tools/, results/, physical/die_plan/hbm/plan_of_record/d44v/)
  HIST = pre53_die_plan.json.gz (d44v at 01a61d4b8ca^1), pre53_core_macros.json, p61_core_macros.json
Every new table is checked byte-equal (decompressed) to the d44v/cores copy.
Kept as in the final: q_su00/q_su10(+__physical_v1) u_su_Q{0,1}_lane_exp0__l (module exp_x 319.68, EXP0-KIND1-1108):
it is held out of the expx328 row solver as a fixed item, so it is neither grown nor moved."""
import gzip, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

pd, repo, hist, out_ev = Path(sys.argv[1]), Path(sys.argv[2]).resolve(), Path(sys.argv[3]), Path(sys.argv[4])
D44V = repo / "physical/die_plan/hbm/plan_of_record/d44v"
EV = dict(schema="opentallas.hbm_plan_event.v1", event="restore_1109", plan="d44v_restore_1109", base="d44v_corepins_1109 (3742832d6eb33412)",
          lane="DIE-HBM-97/RESTORE", date="2026-11-09", steps=[])


def rd(p):
    p = Path(p)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes())


def d44v_bytes(rel):
    p = D44V / rel
    return p.read_bytes() if p.exists() else gzip.decompress((D44V / (rel + ".gz")).read_bytes())


def load(): return json.loads((pd / "die_plan.json").read_text())
def save(P): (pd / "die_plan.json").write_text(json.dumps(P, indent=1) + "\n")   # the final's own form (indent 1)
def sha(b): return hashlib.sha256(b).hexdigest()


def snap(P, mods):
    return {(tn, h["inst"]): json.dumps(h, sort_keys=True) for tn, t in P["partition_types"].items() for h in t.get("hard_cores") or [] if h["module"] in mods}


# ---------------- 1 part60
P = load()
OLD = "cores/ot_hgi_coll_inj_idx_join_rg__211.68x207.36__content_trial__d16f__codex_g21__centry.json"
NEW = OLD[:-5] + "__r1drop.json"
DROP = ["inj_rd_r1[1]"] + [f"idx_tx_h_r1[{b}]" for b in range(102, 132)]
READ = ["inj_rd_r1[0]"] + [f"idx_tx_h_r1[{a*33+k}]" for a in range(4) for k in range(3)]
t = rd(pd / OLD); assert len(t) == 4761 and set(DROP) <= {p["name"] for p in t}
keep = [p for p in t if p["name"] not in set(DROP)]
assert len(keep) == 4730 and set(READ) <= {p["name"] for p in keep}
raw = (json.dumps(keep) + "\n").encode(); assert raw == d44v_bytes(NEW), "p60 table != d44v"
(pd / NEW).write_bytes(raw)
inst = []
for q in ("q_hub_nw", "q_hub_ne"):
    for c in P["partition_types"][q]["hard_cores"]:
        if c.get("pins_file") == OLD:
            c["pins_file"] = NEW; inst.append(f"{q}.{c['inst']}")
assert len(inst) == 4, inst
save(P)
EV["steps"].append(dict(event="part60", commit="7de1e0f41b", module="ot_hgi_coll_inj_idx_join_rg", instances=inst, changes=dict(pins_file=4),
                        table=NEW, table_sha256=sha(raw), pins=[4761, 4730], pins_removed=len(DROP)))

# ---------------- 2 part61
P = load(); pre = rd(hist / "pre53_die_plan.json.gz")
OLD = "cores/ot_svgr_bk__259.2x207.36__d44v_split.json"; P53 = "cores/ot_svgr_bk__302.4x207.36__d44v_p53.json"; NEW = "cores/ot_svgr_bk__259.2x207.36__d44v_p61.json"
SITE = [21.72, 103.68]
n = tapn = 0; inst = []
for q in ("q_hub_nw", "q_hub_ne"):
    t, p0 = P["partition_types"][q], pre["partition_types"][q]
    a = {c["inst"]: c for c in p0["hard_cores"]}; insts = set()
    for c in t["hard_cores"]:
        if c.get("module") == "ot_svgr_bk":
            o = a[c["inst"]]; assert o["pins_file"] == OLD and c["pins_file"] == P53 and c["outline_um"] == [302.4, 207.36]
            for k in ("origin_um", "outline_um", "note"): c[k] = o[k]
            c["pins_file"] = NEW; n += 1; insts.add(c["inst"]); inst.append(f"{q}.{c['inst']}")
    ta = {k["name"]: k for k in p0["clock"]["taps"]}
    for k in t["clock"]["taps"]:
        if k["name"] in insts:
            k["xy"] = ta[k["name"]]["xy"]; k["note"] = ta[k["name"]].get("note"); tapn += 1
assert n == 16 and tapn == 16, (n, tapn)
raw = d44v_bytes(NEW); tt = json.loads(raw)
assert sha(raw).startswith("8ba152814ecb") and len(tt) == 2255 and [p for p in tt if p["name"] == "stream_clk"][0]["x"] == SITE[0]
(pd / NEW).write_bytes(raw)
save(P)
ce = json.loads((pd / "clock_entries.json").read_text()); m = 0
for q, v in ce.items():
    if isinstance(v, dict):
        for e in v.values():
            if isinstance(e, dict) and e.get("module") == "ot_svgr_bk":
                assert e["clock_pin_sites_um"]["stream_clk"] == [22.008, 103.68]; e["clock_pin_sites_um"]["stream_clk"] = SITE; m += 1
assert m == 16
(pd / "clock_entries.json").write_text(json.dumps(ce) + "\n")
# core_macros: mk_p61 put back the pre-part-53 bytes after asserting only svgr_bk differed; on the final only the ot_svgr_bk entry goes back
cm = json.loads((pd / "core_macros.json").read_text()); cpre = rd(hist / "pre53_core_macros.json"); cp61 = rd(hist / "p61_core_macros.json")
assert cm["cores"]["ot_svgr_bk"]["outline_um"] == [302.4, 207.36] and cpre["cores"]["ot_svgr_bk"] == cp61["cores"]["ot_svgr_bk"]
assert {k: v for k, v in cm["cores"]["ot_svgr_bk"].items() if k not in ("outline_um", "basis")} == {k: v for k, v in cpre["cores"]["ot_svgr_bk"].items() if k not in ("outline_um", "basis")}
cm["cores"]["ot_svgr_bk"] = cpre["cores"]["ot_svgr_bk"]
(pd / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
L = d44v_bytes("corelat/cycles_svgr_bk_vB_1107.tsv"); (pd / "corelat").mkdir(exist_ok=True); (pd / "corelat/cycles_svgr_bk_vB_1107.tsv").write_bytes(L)
EV["steps"].append(dict(event="part61", commit="bbda1ab30f", module="ot_svgr_bk", instances=inst,
                        changes=dict(origin_um=16, outline_um=16, pins_file=16, note=16, clock_taps=16, clock_entries_stream_clk=16, core_macros_entry=1),
                        table=NEW, table_sha256=sha(raw), corelat="corelat/cycles_svgr_bk_vB_1107.tsv", kept="part 53 internal_stations regs_um"))

# ---------------- 3 expx328_1107 (mk_expx328.py unchanged; exp0__l held out as a fixed row item)
HOLD = "__restore_1109_hold__"; EXP = "ot_hbm_su_pg_lane_exp_x_core"
P = load(); held = []
for tn in ("q_su00", "q_su00__physical_v1", "q_su10", "q_su10__physical_v1"):
    for h in P["partition_types"][tn]["hard_cores"]:
        if h["inst"] in ("u_su_Q0_lane_exp0__l", "u_su_Q1_lane_exp0__l"):
            assert h["module"] == EXP; h["module"] = HOLD; held.append(f"{tn}.{h['inst']}")
assert len(held) == 4, held
before = snap(P, {EXP, "ot_hbm_su_pg_sfu_s_core", HOLD}); save(P)
before_all = {(tn, h["inst"]): (h["origin_um"], h["outline_um"]) for tn, t in P["partition_types"].items() for h in t.get("hard_cores") or []}
env = dict(os.environ, PYTHONPATH="tools/die_plan:tools", PYTHONDONTWRITEBYTECODE="1")
def run(cmd):
    r = subprocess.run(cmd, cwd=repo, env=env, capture_output=True, text=True); print(r.stdout[-3000:], r.stderr[-3000:]); return r
r = run([sys.executable, "results/die_hbm_1107/expx328/mk_expx328.py", str(pd)]); assert r.returncode == 0
mk = json.loads(r.stdout.strip().splitlines()[-1])
r = run([sys.executable, "tools/die_plan/ft_nudge.py", str(pd / "die_plan.json"), str(pd / "die_plan.nudged.json"), str(pd / "expx328_1107_ft_nudge_ledger.json")]); assert r.returncode == 0
os.replace(pd / "die_plan.nudged.json", pd / "die_plan.json")
r = run([sys.executable, "tools/die_plan/ft_reach_fix.py", str(pd / "die_plan.json"), str(pd / "die_plan.reach.json"), str(pd / "expx328_1107_ft_reach_ledger.json")])
reach_applied = (pd / "die_plan.reach.json").exists()
if reach_applied: os.replace(pd / "die_plan.reach.json", pd / "die_plan.json")
led = json.loads((pd / "expx328_1107_ft_nudge_ledger.json").read_text())
SL = ",".join(sorted({x["type"] + "/" + x["slot"] for x in led if x.get("mode") == "bit_sites" and x.get("bits_moved")}))
print("medoid-fix:", SL)
if SL:
    r = run([sys.executable, "tools/die_plan/ft_s0_resite.py", "--medoid-fix", str(pd / "die_plan.json"), str(pd / "die_plan.medoid.json"), SL]); assert r.returncode == 0
    os.replace(pd / "die_plan.medoid.json", pd / "die_plan.json")
P = load()
for tn in ("q_su00", "q_su00__physical_v1", "q_su10", "q_su10__physical_v1"):
    for h in P["partition_types"][tn]["hard_cores"]:
        if h["module"] == HOLD: h["module"] = EXP
after = snap(P, {EXP, "ot_hbm_su_pg_sfu_s_core"})
for k in held:
    tn, i = k.split(".", 1); assert json.loads(before[(tn, i)]) == dict(json.loads(after[(tn, i)]), module=HOLD), ("exp0__l changed", k)
mv = [k for k in after if k in before and after[k] != before[k]]
moved_other = [k for tn, t in P["partition_types"].items() for h in t.get("hard_cores") or [] for k in [(tn, h["inst"])]
               if before_all.get(k) != (h["origin_um"], h["outline_um"]) and h["module"] not in (EXP, "ot_hbm_su_pg_sfu_s_core")]
save(P)
raw = (pd / "cores/ot_hbm_su_pg_lane_exp_x_core__328.32x207.36__d44v_expx328.json").read_bytes()
assert raw == d44v_bytes("cores/ot_hbm_su_pg_lane_exp_x_core__328.32x207.36__d44v_expx328.json"), "expx table != d44v"
ex = json.loads((pd / "expx328_1107_event.json").read_text())
EV["steps"].append(dict(event="expx328_1107", commit="ccbad2a1c5", module=EXP, script="results/die_hbm_1107/expx328/mk_expx328.py (unchanged) + replay.sh post steps",
                        held_fixed=held, grown=mk["modules"][EXP]["instances"], moved_cores=len(ex["moved"]), moved_by_module={
                            m: sum(1 for r_ in ex["moved"] if (r_["type"], r_["inst"]) in {(tn, h["inst"]) for tn, t in P["partition_types"].items() for h in t.get("hard_cores") or [] if h["module"] == m})
                            for m in (EXP, "ot_hbm_su_pg_sfu_s_core", "ot_hbm_su_pg_lane_full_x_core")},
                        taps=len(ex["taps"]), istation_chains=len(ex["istations"]), istation_regs_moved=sum(x["moved"] for x in ex["istations"]),
                        ft_nudge_rows=len(led), ft_nudge_bit_sites_slots=SL.split(",") if SL else [], ft_reach_fix_applied=reach_applied,
                        rows_changed=len(mv), other_modules_moved=[".".join(k) for k in moved_other],
                        table="cores/ot_hbm_su_pg_lane_exp_x_core__328.32x207.36__d44v_expx328.json", table_sha256=sha(raw),
                        sidecars="clock_entries (exp_x entries -> (164.16, 103.68)), core_macros ot_hbm_su_pg_lane_exp_x_core (328.32, edge columns)",
                        event_file="expx328_1107_event.json"))

# ---------------- 4 qcore267_1107
P = load()
OLD = "cores/ot_hbm_su_static_qcore_r13__224.64x207.36__canon__codex_g21__codex_v1__dh17v2__centry.json"; NEW = OLD[:-5] + "__s267drop.json"
t = rd(pd / OLD); raw = d44v_bytes(NEW); nt = json.loads(raw)
assert len(t) == 1473 and len(nt) == 1472 and nt == [p for p in t if p["name"] != "slice_t[267]"] and sha(raw).startswith("330ffe42")
(pd / NEW).write_bytes(raw); inst = []
for q in ("q_hub_ne", "q_hub_nw"):
    for c in P["partition_types"][q]["hard_cores"]:
        if c.get("pins_file") == OLD:
            assert c["inst"] == "u_sucore_Q__q0"; c["pins_file"] = NEW; inst.append(f"{q}.{c['inst']}")
assert len(inst) == 2, inst
save(P)
EV["steps"].append(dict(event="qcore267_1107", commit="0cf1ab2aa7", module="ot_hbm_su_static_qcore_r13", instances=inst, changes=dict(pins_file=2),
                        table=NEW, table_sha256=sha(raw), pins=[1473, 1472], pins_removed=["slice_t[267]"]))

# ---------------- 5 opsarest_c2_1107 (mk_opsarest_c2.py unchanged, on a gz shim)
def gzw(src, dst):
    with open(dst, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g: g.write(Path(src).read_bytes())
sh = Path(tempfile.mkdtemp(prefix="opsa_shim_", dir=str(pd.parent)))
for n_ in ("die_plan.json", "core_conns.json", "clock_entries.json"): gzw(pd / n_, sh / (n_ + ".gz"))
(sh / "cores").mkdir()
for f in (pd / "cores").iterdir():
    if f.name.endswith(".json"): os.symlink(f, sh / "cores" / f.name)
OT = "cores/ot_hgi_sfu_opsa_rest__760.32x86.4__d44v_split.json"; os.unlink(sh / OT); gzw(pd / OT, sh / (OT + ".gz"))
(sh / "README.md").write_text("shim\n"); (sh / "SHA256SUMS").write_text("0  die_plan.json\n")
OD = "results/die_hbm_1107/opsarest_c2"
r = subprocess.run([sys.executable, "-I", f"{OD}/mk_opsarest_c2.py", str(sh), f"{OD}/opsa_rest_vC2_pins.json", "results/die_hbm_1105/form_split/p27/opstore_a.conn.json", str(pd / "opsarest_c2_1107_report.json")],
                   cwd=repo, capture_output=True, text=True); print(r.stdout[-3000:], r.stderr[-3000:])
if r.returncode != 0:
    # fail closed: the script's own reach assert (every moved reg-to-reg link <= 452.5 um measured one-cycle reach) does not hold
    # on the final (restjC_1108 compacted u_sfucore_Q_ctl__rest to 267.84x267.84 at (587.52, 1105.92)); sweep the script's own
    # placement space (opsarest_sweep2.py) to show no slot origin/orient meets it. The plan is left unchanged by this step.
    assert "assert all(v <= L.MEASURED_REACH for _, v in over)" in r.stderr, r.stderr[-2000:]
    shutil.rmtree(sh)
    sw = subprocess.run([sys.executable, "-I", f"{OD}/opsarest_sweep2.py", OD, str(pd), "results/die_hbm_1105/form_split/p27/opstore_a.conn.json", f"{OD}/opsa_rest_vC2_pins.json"],
                        cwd=repo, capture_output=True, text=True)
    assert sw.returncode == 0, sw.stderr[-2000:]
    top = sw.stdout.strip().splitlines()[:3]
    EV["steps"].append(dict(event="opsarest_c2_1107", commit="834d940a5e", module="ot_hgi_sfu_opsa_rest", replayed=False,
                            script=f"{OD}/mk_opsarest_c2.py (unchanged) stops at its reach assert: links over 452.5 um at the d44v origin (1131.84, 959.04)",
                            cause="the final carries restjC_1108 (u_sfucore_Q_ctl__rest = ot_hgi_sfu_split3_ctl_rest_1c 267.84x267.84 at (587.52, 1105.92) MY; d44v has 427.68x453.6 at (509.76, 1010.88)): ctl_rest <-> rest links grow to 502-546 um",
                            sweep=f"{OD}/opsarest_sweep2.py on this plan, best minimax (um, orient, x0, y0, worst links): " + " || ".join(top),
                            plan_change="none (q_b113 / q_b113__physical_v1 opsa_rest rows, taps, clock entries and stations stay as in the final)"))
else:
    (pd / "die_plan.json").write_bytes(gzip.decompress((sh / "die_plan.json.gz").read_bytes()))
    (pd / "clock_entries.json").write_bytes(gzip.decompress((sh / "clock_entries.json.gz").read_bytes()))
    NEW = "cores/ot_hgi_sfu_opsa_rest__250.56x64.8__d44v_opsarest_c2.json"
    raw = gzip.decompress((sh / (NEW + ".gz")).read_bytes()); assert raw == d44v_bytes(NEW), "opsa table != d44v"
    (pd / NEW).write_bytes(raw)
    for n_ in ("corelat/cycles_opsarest_c2_1107.tsv", "opsarest_c2_1107_event.json"): shutil.copyfile(sh / n_, pd / n_)
    assert (pd / "corelat/cycles_opsarest_c2_1107.tsv").read_bytes() == d44v_bytes("corelat/cycles_opsarest_c2_1107.tsv")
    shutil.rmtree(sh)
    oe = json.loads((pd / "opsarest_c2_1107_event.json").read_text()); rep = json.loads((pd / "opsarest_c2_1107_report.json").read_text())
    EV["steps"].append(dict(event="opsarest_c2_1107", commit="834d940a5e", module="ot_hgi_sfu_opsa_rest", script=f"{OD}/mk_opsarest_c2.py (unchanged)",
                            instances=["q_b113.u_sfucore_Q_opstore_a__r", "q_b113__physical_v1.u_sfucore_Q_opstore_a__r"],
                            changes=dict(origin_um=2, outline_um=2, pins_file=2, clock_taps=2, clock_entries=2,
                                         istations_touched={tn: len(v["stations"]) for tn, v in rep["types"].items()},
                                         istations_resited={tn: sum(1 for x in v["stations"] if x["changed"]) for tn, v in rep["types"].items()}),
                            table=NEW, table_sha256=sha(raw), corelat="corelat/cycles_opsarest_c2_1107.tsv", event_file="opsarest_c2_1107_event.json",
                            timing_833ps=oe["timing_833ps"]))
save(load())
out_ev.write_text(json.dumps(EV, indent=1) + "\n")
print("RESTORE OK", sha((pd / "die_plan.json").read_bytes())[:16])
