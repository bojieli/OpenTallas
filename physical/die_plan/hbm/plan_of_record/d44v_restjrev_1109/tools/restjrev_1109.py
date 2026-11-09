#!/usr/bin/env python3
"""DIE-HBM-97/RESTORE 11-09: plan event restjrev_1109 on d44v_restore_1109 (sha256 27e46e2d84777acf), DIE-HBM-97 decision (a).

  1 restjC_1108 inverted on q_b113 and q_b113__physical_v1: u_sfucore_Q_ctl__rest (ot_hgi_sfu_split3_ctl_rest_1c) goes back
    from 267.84x267.84 (restjC vC) to the d44v form 427.68x453.6.  Every value RESTJ-C-1108 changed (its own event file
    restjC_1108_event.json: die_plan_rows + clock_entry + core_macros) is set back to the event's recorded 'old' value and
    the event's appended note suffix is removed from each note it touched (row note, tap note, clock_entries source,
    core_macros note).  Asserted: the plan holds the event's 'new' values, and the result equals d44v_gqi's row, tap,
    clock entry and core_macros entry.  The 427.68 table is checked against the signed record's kit pins.json
    (epyc4 die-hbm-88/r1c/eco_one_b/i1, sha256 8606b728), face pins inset 0.096 as core_pin_event.py.
  2 opsarest_c2_1107: results/die_hbm_1107/opsarest_c2/mk_opsarest_c2.py unchanged, on a gz shim of the plan dir.  Fail closed.

    restjrev_1109.py PLANDIR REPO RESTJC_EVENT.json KIT_PINS.json CORE_PIN_EVENT_DIR OUT_EVENT_JSON"""
import gzip, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

pd, repo, evf, kitf, cpe, out_ev = Path(sys.argv[1]), Path(sys.argv[2]).resolve(), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5], Path(sys.argv[6])
POR = repo / "physical/die_plan/hbm/plan_of_record"
sys.path.insert(0, cpe); import core_pin_event as CPE  # noqa: E402
INST, MOD = "u_sfucore_Q_ctl__rest", "ot_hgi_sfu_split3_ctl_rest_1c"
OLD_PF = "cores/ot_hgi_sfu_split3_ctl_rest_1c__427.68x453.6__d44v_split.json"
ev = json.loads(evf.read_text()); assert ev["event"] == "RESTJ-C-1108" and ev["module"] == MOD and ev["old_pins_file"] == OLD_PF
SUF = " | " + ev["tag"]
def sha(b): return hashlib.sha256(b).hexdigest()
def unsuf(s):
    assert s.endswith(SUF), s[-200:]; return s[: -len(SUF)]
def rdgz(p): return json.loads(gzip.decompress(Path(p).read_bytes()))
EV = dict(schema="opentallas.hbm_plan_event.v1", event="restjrev_1109", plan="d44v_restjrev_1109", base="d44v_restore_1109 (27e46e2d84777acf)",
          lane="DIE-HBM-97/RESTORE", date="2026-11-09", decision="DIE-HBM-97 (a): revert restjC_1108, then replay opsarest_c2_1107", steps=[])

# ---------------- pins: d44v 427.68 table vs signed kit
tab = json.loads((pd / OLD_PF).read_text())
assert tab == rdgz(POR / "d44v/cores" / (Path(OLD_PF).name + ".gz")), "plan dir 427.68 table != d44v"
kit = json.loads(kitf.read_text()); kp = {CPE.kname(k): CPE.to_plan(k) for k in kit}; tp = {p["name"]: p for p in tab}
assert set(kp) == set(tp) and len(tp) == 12373
lay = [n for n in tp if kp[n]["layer"] != tp[n]["layer"]]; assert not lay, lay[:5]
dev = {n: round(max(abs(kp[n]["x"] - tp[n]["x"]), abs(kp[n]["y"] - tp[n]["y"])), 4) for n in tp}
off = {n: v for n, v in dev.items() if v > 1e-3}
assert all(v <= 0.1 for v in off.values()), off   # mk_p60 / mk_p61 kit-vs-table tolerance (kit edge point vs table pin centre)
pins_chk = dict(kit=str(kitf), kit_sha256=sha(kitf.read_bytes()), record="epyc4 /srv/opentallas-scratch3/claude/die-hbm-88/r1c/eco_one_b/i1 (signed_records hbc_ot_hgi_sfu_split3_ctl_rest_1c, LOCAL_PASS_NEEDS_PARENT / local SIGNED)",
                names_equal=True, pins=len(tp), layer_changes=0, inset_um=0.096, off_after_inset=off,
                note="clk is the entry pin: kit 216.024 = entry 216.0 + 0.024, d44v table 215.976 = entry - 0.024; both 0.048-wide rects end on the entry x 216.0")

# ---------------- 1 restjC_1108 inverse
P = json.loads((pd / "die_plan.json").read_text()); G = rdgz(POR / "d44v_gqi/die_plan.json.gz")["partition_types"]
rows = []
for tn, pl in ev["placements"].items():
    t = P["partition_types"][tn]
    h = [x for x in t["hard_cores"] if x["inst"] == INST]; assert len(h) == 1; h = h[0]
    assert h["module"] == MOD and h["orient"] == pl["orient"]
    for k in ("origin_um", "track_offset_um", "outline_um"):
        assert h[k] == pl["new"][k], (tn, k, h[k]); h[k] = pl["old"][k]; rows.append(f"{tn}.{k}")
    assert h["pins_file"] == ev["new_pins_file"]; h["pins_file"] = pl["old"]["pins_file"]; rows.append(f"{tn}.pins_file")
    h["note"] = unsuf(h["note"]); rows.append(f"{tn}.note")
    tp_ = [x for x in t["clock"]["taps"] if x["name"] == INST]; assert len(tp_) == 1; tp_ = tp_[0]
    assert tp_["xy"] == pl["new"]["tap"]; tp_["xy"] = pl["old"]["tap"]; tp_["note"] = unsuf(tp_["note"]); rows += [f"{tn}.tap.xy", f"{tn}.tap.note"]
    g = [x for x in G[tn]["hard_cores"] if x["inst"] == INST][0]; gt = [x for x in G[tn]["clock"]["taps"] if x["name"] == INST][0]
    assert h == g, (tn, {k: (h.get(k), g.get(k)) for k in set(h) | set(g) if h.get(k) != g.get(k)})
    assert tp_ == gt, tn
P["note"] = "DIE-HBM-97/RESTORE restjrev_1109 (revert RESTJ-C-1108: ctl_rest_1c back to 427.68x453.6; opsarest_c2_1107 replay) <- " + P.get("note", "")
(pd / "die_plan.json").write_text(json.dumps(P, indent=1) + "\n")
ce = json.loads((pd / "clock_entries.json").read_text()); dce = rdgz(POR / "d44v/clock_entries.json.gz")
for tn in ev["placements"]:
    e = ce[tn][INST]; assert e["xy_um"] == ev["clock_entry"]["new"] and e["module"] == MOD
    e["xy_um"] = ev["clock_entry"]["old"]; x, y = e["xy_um"]; e["island_um"] = [round(x - 4.32, 3), round(y - 4.32, 3), round(x + 4.32, 3), round(y + 4.32, 3)]
    e["source"] = unsuf(e["source"]); assert e == dce[tn][INST], tn
(pd / "clock_entries.json").write_text(json.dumps(ce) + "\n")
cm = json.loads((pd / "core_macros.json").read_text()); dcm = json.loads((POR / "d44v/core_macros.json").read_text())
c = cm["cores"][MOD]; assert c["outline_um"] == [267.84, 267.84]
c["outline_um"] = [427.68, 453.6]; c["note"] = unsuf(c["note"]); assert c == dcm["cores"][MOD]
(pd / "core_macros.json").write_text(json.dumps(cm, indent=1) + "\n")
EV["steps"].append(dict(event="restjC_1108 inverse", source_event="restjC_1108_event.json (DIE-HBM-92-RESTJ RESTJ-C-1108)", module=MOD,
                        instances=[f"{tn}.{INST}" for tn in ev["placements"]],
                        changes=dict(origin_um=2, track_offset_um=2, outline_um=2, pins_file=2, note=2, clock_taps=2, clock_tap_notes=2, clock_entries=2, core_macros_entry=1),
                        values={tn: dict(origin_um=pl["old"]["origin_um"], track_offset_um=pl["old"]["track_offset_um"], outline_um=pl["old"]["outline_um"], tap=pl["old"]["tap"]) for tn, pl in ev["placements"].items()},
                        clock_entry=ev["clock_entry"]["old"], pins_file=OLD_PF, equals_d44v_gqi="row, tap, clock_entries entry, core_macros entry", pins_check=pins_chk,
                        internal_stations="unchanged (RESTJ-C-1108 changed none)"))

# ---------------- 2 opsarest_c2_1107 (mk_opsarest_c2.py unchanged)
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
    shutil.rmtree(sh); sys.exit("FAIL CLOSED: mk_opsarest_c2.py rc %d" % r.returncode)
P = json.loads(gzip.decompress((sh / "die_plan.json.gz").read_bytes()))
(pd / "die_plan.json").write_text(json.dumps(P, indent=1) + "\n")
(pd / "clock_entries.json").write_bytes(gzip.decompress((sh / "clock_entries.json.gz").read_bytes()))
NEW = "cores/ot_hgi_sfu_opsa_rest__250.56x64.8__d44v_opsarest_c2.json"
raw = gzip.decompress((sh / (NEW + ".gz")).read_bytes()); assert raw == gzip.decompress((POR / "d44v" / (NEW + ".gz")).read_bytes()), "opsa table != d44v"
(pd / NEW).write_bytes(raw)
(pd / "corelat").mkdir(exist_ok=True)
for n_ in ("corelat/cycles_opsarest_c2_1107.tsv", "opsarest_c2_1107_event.json"): shutil.copyfile(sh / n_, pd / n_)
assert (pd / "corelat/cycles_opsarest_c2_1107.tsv").read_bytes() == (POR / "d44v/corelat/cycles_opsarest_c2_1107.tsv").read_bytes()
shutil.rmtree(sh)
oe = json.loads((pd / "opsarest_c2_1107_event.json").read_text()); rep = json.loads((pd / "opsarest_c2_1107_report.json").read_text())
for tn in ("q_b113", "q_b113__physical_v1"):
    h = [x for x in P["partition_types"][tn]["hard_cores"] if x["inst"] == "u_sfucore_Q_opstore_a__r"][0]
    g = [x for x in G[tn]["hard_cores"] if x["inst"] == "u_sfucore_Q_opstore_a__r"][0]
    assert all(h[k] == g[k] for k in ("origin_um", "outline_um", "pins_file", "orient")), tn
EV["steps"].append(dict(event="opsarest_c2_1107", commit="834d940a5e", module="ot_hgi_sfu_opsa_rest", script=f"{OD}/mk_opsarest_c2.py (unchanged)",
                        instances=["q_b113.u_sfucore_Q_opstore_a__r", "q_b113__physical_v1.u_sfucore_Q_opstore_a__r"],
                        changes=dict(origin_um=2, outline_um=2, pins_file=2, note=2, clock_taps=2, clock_entries=2,
                                     istations={tn: dict(touched=len(v["stations"]), resited=sum(1 for x in v["stations"] if x["changed"]),
                                                         launch=sum(1 for x in v["stations"] if x["kind"] == "launch"), capture=sum(1 for x in v["stations"] if x["kind"] == "capture"))
                                                for tn, v in rep["types"].items()}),
                        table=NEW, table_sha256=sha(raw), equals_d44v_gqi="origin, outline, pins_file, orient",
                        corelat="corelat/cycles_opsarest_c2_1107.tsv", event_file="opsarest_c2_1107_event.json", report="opsarest_c2_1107_report.json",
                        timing_833ps=oe["timing_833ps"]))
out_ev.write_text(json.dumps(EV, indent=1) + "\n")
print("RESTJREV OK", sha((pd / "die_plan.json").read_bytes())[:16])
