"""FLOW-PROC-A 11-21 (FABLE-FLOW-0800 e): the kit flow refresh is all or nothing; a partial refresh defers the stage (exit 75, autopilot
infra-flow-refresh) instead of launching on mixed flow files; a read-only runner bind gets a refreshed override copy; the route fail key
carries the first error line, and the attempt cap names its causes instead of "(mixed errors)"."""
import errno
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_flow_refresh as K       # noqa: E402


def setup(tmp):
    rt = Path(tmp) / "rt" / "aaaaaaaaaaaa"
    (rt / "tools/die_plan").mkdir(parents=True)
    (rt / "physical/common_flow").mkdir(parents=True)
    old, new = b"puts old\n", b"puts fixed\n"
    (rt / "tools/die_plan/vclk_measured_hold.tcl").write_bytes(new)
    (rt / "tools/die_plan/cts_fix.tcl").write_bytes(b"cts fixed\n")
    (rt / "tools/die_plan/stage_odb_cap.py").write_bytes(b"cap new\n")
    idx = {"blobs": {"tools/die_plan/vclk_measured_hold.tcl": sorted({K.blob_id(old), K.blob_id(new)}),
                     "tools/die_plan/cts_fix.tcl": sorted({K.blob_id(b"cts old\n"), K.blob_id(b"cts fixed\n")})}}
    (rt / "tools/.flow_blobs.json").write_text(json.dumps(idx))
    Path(str(rt) + ".manifest.json").write_text(json.dumps({"sha": "a" * 40}))
    gen = Path(tmp) / "gen"
    kit = gen / "kit"
    kit.mkdir(parents=True)
    (kit / "vclk_measured_hold.tcl").write_bytes(old)
    (kit / "cts_fix.tcl").write_bytes(b"cts old\n")
    (kit / "stage_odb_cap.py").write_bytes(b"cap old\n")
    (gen / "run_kit.sh").write_bytes(b"#!/bin/bash\necho old runner\n")
    return rt, kit


def busy_on(monkeypatch, names, inplace_err=None):
    """os.replace onto a target whose basename is in names fails EBUSY (a bwrap file bind); inplace_err makes the in-place rewrite fail too"""
    real_replace, real_open = os.replace, open

    def rep(a, b, *k, **kw):
        if os.path.basename(str(b)) in names or str(b) in names:
            raise OSError(errno.EBUSY, "Device or resource busy", str(b))
        return real_replace(a, b, *k, **kw)

    def opn(p, mode="r", *k, **kw):
        if inplace_err and mode == "r+b" and (os.path.basename(str(p)) in names or str(p) in names):
            raise OSError(inplace_err, os.strerror(inplace_err), str(p))
        return real_open(p, mode, *k, **kw)
    monkeypatch.setattr(K.os, "replace", rep)
    monkeypatch.setattr(K, "open", opn, raising=False)
    monkeypatch.setattr(K.time, "sleep", lambda s: None)


def test_partial_refresh_changes_nothing_and_exits_75(monkeypatch, capsys):
    rt, kit = setup(tempfile.mkdtemp())
    busy_on(monkeypatch, {"vclk_measured_hold.tcl"}, inplace_err=errno.EROFS)
    rc = K.main(["--kit", str(kit), "--stage", "route", "--rt", str(rt)])
    out = capsys.readouterr().out
    assert rc == K.PARTIAL_RC == 75
    assert "KIT_FLOW_REFRESH FAIL FLOW-REFRESH-PARTIAL" in out
    # all or nothing: the files that sort before AND after the busy one keep their old bytes
    assert (kit / "cts_fix.tcl").read_bytes() == b"cts old\n"
    assert (kit / "stage_odb_cap.py").read_bytes() == b"cap old\n"
    assert (kit / "vclk_measured_hold.tcl").read_bytes() == b"puts old\n"
    assert (kit.parent / "run_kit.sh").read_bytes() == b"#!/bin/bash\necho old runner\n"
    rec = json.loads((kit / "flow_refresh.jsonl").read_text().splitlines()[-1])
    assert rec["partial"] is True and "rolled back" in rec["error"]
    assert not [n for n in os.listdir(kit) if ".kfr." in n]          # no temp file left behind


def test_bind_mounted_kit_file_is_rewritten_in_place(monkeypatch):
    rt, kit = setup(tempfile.mkdtemp())
    busy_on(monkeypatch, {"cts_fix.tcl"})
    assert K.main(["--kit", str(kit), "--stage", "route", "--rt", str(rt)]) == 0
    assert (kit / "cts_fix.tcl").read_bytes() == b"cts fixed\n"
    assert (kit / "vclk_measured_hold.tcl").read_bytes() == b"puts fixed\n"
    rec = json.loads((kit / "flow_refresh.jsonl").read_text().splitlines()[-1])
    assert any("in-place" in n for n in rec.get("commit_notes", []))


def test_readonly_runner_gets_override_and_rest_is_refreshed(monkeypatch):
    """kv3_hub_Wo a9: the sealed job's runner is a read-only input bind (rename EBUSY); the refresh used to throw there and leave the rest stale"""
    rt, kit = setup(tempfile.mkdtemp())
    monkeypatch.setattr(K, "_rt_run_kit_text", lambda rtr, roots=None: "#!/bin/bash\necho new runner\n")
    busy_on(monkeypatch, {str(kit.parent / "run_kit.sh")}, inplace_err=errno.EROFS)
    assert K.main(["--kit", str(kit), "--stage", "route", "--rt", str(rt)]) == 0
    assert (kit / "cts_fix.tcl").read_bytes() == b"cts fixed\n"
    assert (kit / "stage_odb_cap.py").read_bytes() == b"cap new\n"
    assert (kit.parent / "run_kit.sh").read_bytes() == b"#!/bin/bash\necho old runner\n"
    alt = kit / K.RUNNER_OVERRIDE_DIR / "run_kit.sh"
    assert alt.read_bytes() == b"#!/bin/bash\necho new runner\n"
    assert K.runner_override(str(kit)) == str(alt)
    import signoff_chain as SC
    assert SC.runner_override(kit) == str(alt)


def test_signoff_chain_defers_on_partial_and_runs_override(tmp_path):
    import signoff_chain as SC
    kit = tmp_path / "kit"
    kit.mkdir()
    ran = []

    def run(argv, **kw):
        ran.append(argv)
        return 1
    rc = SC.continue_kit(kit, str(tmp_path / "run_kit.sh"), "route", 8, 2, run=run, preflight=str(tmp_path / "none.py"),
                         refresh=lambda k, g: 75, so_tool=None, eco_loop=None)
    assert rc == 3 or rc == 75                  # preflight missing -> 3 (staged tool check) comes first
    (tmp_path / "pf.py").write_text("import sys; sys.exit(0)\n")
    ran.clear()
    rc = SC.continue_kit(kit, str(tmp_path / "run_kit.sh"), "route", 8, 2, run=lambda a, **k: (ran.append(a), 0)[1],
                         preflight=str(tmp_path / "pf.py"), refresh=lambda k, g: 75, so_tool=None, eco_loop=None)
    assert rc == 75 and not any("bash" == a[0] for a in ran)
    alt = kit / ".flow_runner" / "run_kit.sh"
    alt.parent.mkdir()
    alt.write_text("#!/bin/bash\n")

    def ref(k, g):
        (kit / "flow_refresh.jsonl").write_text(json.dumps({"runner_override": str(alt)}) + "\n")
        return 0
    ran.clear()
    SC.continue_kit(kit, str(tmp_path / "run_kit.sh"), "cts", 8, 2, run=lambda a, **k: (ran.append(a), 0)[1],
                    preflight=str(tmp_path / "pf.py"), refresh=ref, so_tool=None, eco_loop=None)
    assert ["bash", str(alt), str(kit), "cts", "8", "2"] in ran


def test_autopilot_classifies_partial_as_infra_and_names_route_cause():
    import autopilot as AP
    o = AP.parse_client_log("x\nKIT_FLOW_REFRESH FAIL FLOW-REFRESH-PARTIAL: stage route on epyc9: OSError: busy\nAP_RC=75\n")
    assert o.get("flow_refresh_partial", "").startswith("KIT_FLOW_REFRESH FAIL")
    cls, kind, _ = AP.classify({}, o)
    assert (cls, kind) == ("CRASH", "infra-flow-refresh") and kind in AP.INFRA_KINDS
    c = {"FAIL_route": "FAIL_route make exit 2 (see run_route.log)",
         "first_error": "4_1_cts.log: Error: cts.tcl, 89 can't read \"tb_cdirect\": no such variable"}
    cls, kind, why = AP.classify(c, {"exit": 2})
    assert kind == "route-make-fail" and "cts.tcl, 89 can't read" in why and "see run_route" not in why


def test_probe_reads_first_error_line(tmp_path):
    import autopilot as AP
    import subprocess
    K_ = tmp_path / "kit"
    lg = K_ / "run/logs/asap7/d/base"
    lg.mkdir(parents=True)
    (lg / "3_place.log").write_text("ok\n")
    (lg / "4_1_cts.log").write_text("a\nError: cts.tcl, 89 can't read \"tb_cdirect\": no such variable\nb\nError: cts.tcl, 89 again\n")
    (K_ / "FAIL_route").write_text("FAIL_route make exit 2 (see run_route.log)\n")
    (K_ / "run_route.log").write_text("make: *** Error 2\n")
    out = subprocess.run([sys.executable, "-c", AP.PROBE_CLASSIFY, json.dumps({"kit": str(K_), "since": 0, "goal": "route"})],
                         capture_output=True, text=True).stdout
    d = json.loads([ln for ln in out.splitlines() if ln.startswith("AP_JSON ")][-1][8:])
    assert d["first_error"] == "4_1_cts.log: Error: cts.tcl, 89 can't read \"tb_cdirect\": no such variable"


def test_cap_names_causes_and_cause_key_sees_tcl_errors():
    import repeat_stop as RS
    import kit_wave as KW
    st = {}
    tcl = "route-make-fail: FAIL_route make exit 2: 4_1_cts.log: Error: cts.tcl, 89 can't read \"tb_cdirect\": no such variable"
    evs = [RS.record(st, "qwen_kvsys", "kv3_hub_Wo", n, "route", "FLOW", tcl if n != 3 else "KeyError: x (gen_phys.py)", t=n, event="E")
           for n in range(1, 7)]
    cap = [e for e in evs if e and e["event"] == RS.CAP_STATE]
    blk = [e for e in evs if e and e["event"] == "BLOCKED-REPEAT"]
    assert blk and "tcl cts.tcl can't read \"tb_cdirect\"" in blk[0]["fp"]
    st2 = {}
    whys = [tcl, "KeyError: x (gen_phys.py)", tcl.replace("tb_cdirect", "tb_other")]
    evs = [RS.record(st2, "d", "i", n, "route", "FLOW", whys[n % 3], t=n * 30000, event="E") for n in range(1, 7)]
    cap = [e for e in evs if e and e["event"] == RS.CAP_STATE]
    assert cap and "mixed errors" not in cap[0]["why"] and "3 causes:" in cap[0]["why"] and "x2" in cap[0]["why"]
    k1 = KW.cause_key({"q_class": "FLOW", "stage": "route", "q_reason": tcl})
    k2 = KW.cause_key({"q_class": "FLOW", "stage": "route", "q_reason": "route-make-fail: FAIL_route make exit 2: 5_2_route.log: Error: drt.tcl, 12 invalid command name \"foo\""})
    assert "cts.tcl" in k1 and k1 != k2
    assert KW.is_infra_fail({"reason": "infra-flow-refresh: KIT_FLOW_REFRESH FAIL FLOW-REFRESH-PARTIAL: x"})
