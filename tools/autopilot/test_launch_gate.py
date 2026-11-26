"""KNOWN-PROBLEM + POST-PLACEMENT launch gates (COMPOSE-FAST 11-25; OWNER 04:4x / 05:0x / 05:1x)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import launch_gate as G  # noqa: E402

VIS = ("# c\ndie\ttype\tkit\tcause\tfailed (measured)\tvisual\tvisible\tpre-build plan check\tbasis\n"
       "qwen_compute\tsle_st_a_v1\tk1\tC1-STA-MACROFACE\t-\t-\tPLAN\t-\tMEASURED\n"
       "qwen_kvsys\tkv3_hgi_v4\tk2\tC6-KVHGI-LEG\t-\t-\tPLAN\t-\tSTOPPED\n"
       "qwen_kvsys\tkv3_pc\tk3\tC4\t-\t-\tPLAN\t-\tMEASURED FIXED 11-25\n")
SMELL = "die\ttype\tsmell\nKV\tkv3_sys_c\tPILE\n"
FP = ("type\tclass\tstatus\tproven\tts\n"
      "kv3_pv_v2\tVISUAL\tPASS\t\t\n"
      "kv3_pv_v3\tRSTREACH\tFAIL\t\t\n"
      "kv3_pv_v4\tSINKBINS\tFAIL\tyes\t\n"
      "kv3_pv_v5\tNEWRULE\tFAIL\t\t\n"
      "kv3_pv_v6\tNEWRULE2\tFAIL\t\t\n")
RULES = "rule\tstatus\nFP:NEWRULE2\tPROVEN\n"


def T(rules=RULES):
    G.reset_cache()
    files = {G.VIS_REL: VIS, G.SMELL_REL: SMELL, "lanes/FP-KV.tsv": FP, G.RULES_REL: rules}
    return G.tables("qwen_kvsys", reader=lambda rel: files.get(rel)), G.tables("qwen_compute", reader=lambda rel: files.get(rel))


def proven(fl):
    return sorted(f["rule"] for f in fl if f["proven"])


def test_flags_proven_only_from_proven_classes():
    kv, qc = T()
    assert proven(G.flags("qwen_compute", "sle_st_a_v1__cl67389ecd", qc)) == ["VIS:C1-STA-MACROFACE"]
    assert proven(G.flags("qwen_kvsys", "kv3_hgi_v4", kv)) == []                  # STOPPED basis: advisory
    assert proven(G.flags("qwen_kvsys", "kv3_pc", kv)) == []                       # FIXED row cleared
    assert proven(G.flags("qwen_kvsys", "kv3_sys_c", kv)) == ["SMELL:PILE"]
    assert proven(G.flags("qwen_kvsys", "kv3_pv_v3", kv)) == ["PRE:RSTREACH"]      # established PRE class
    assert proven(G.flags("qwen_kvsys", "kv3_pv_v4", kv)) == ["FP:SINKBINS"]       # FP class marked proven
    assert proven(G.flags("qwen_kvsys", "kv3_pv_v5", kv)) == []                    # new rule: advisory
    assert proven(G.flags("qwen_kvsys", "kv3_pv_v6", kv)) == ["FP:NEWRULE2"]       # promoted in the rule table
    assert [f["rule"] for f in G.flags("qwen_kvsys", "kv3_pv_v2", kv)] == []       # FLOORPLAN-CLEAN, no flag
    assert "FP:NOT-CLEAN" in [f["rule"] for f in G.flags("qwen_kvsys", "kv3_pv_v5", kv)]


def _st(states):
    return lambda it: states.get(it, "")


def test_decide_known_problem_pilot_then_probe():
    fl = [dict(rule="VIS:C1", proven=True)]
    pilots = {}
    m, why, key = G.decide("qc", "a", fl, "fa", {"a"}, pilots, _st({}))
    assert m == "PILOT" and key                                                   # guardrail 3: one full pilot per known problem
    pilots[key] = dict(item="a")
    assert G.decide("qc", "a", fl, "fa", {"a"}, pilots, _st({"a": "LIVE"}))[0] == "PILOT"
    assert G.decide("qc", "a", fl, "fa", {"a"}, pilots, _st({"a": "FAILED"}))[0] == "PROBE"
    assert G.decide("qc", "b", [], "fb", {"b"}, pilots, _st({}))[0] == "FULL"
    assert G.decide("qc", "b", [dict(rule="X", proven=False)], "fb", {"b"}, pilots, _st({}))[0] == "FULL"


def test_decide_family_pilot_and_release():
    pilots = {}
    m, _, key = G.decide("s81", "col_r0", [], "fam", {"col_r0", "col_r1", "col_r2"}, pilots, _st({}))
    assert m == "PILOT"
    pilots[key] = dict(item="col_r0")
    assert G.decide("s81", "col_r1", [], "fam", {"col_r0", "col_r1"}, pilots, _st({"col_r0": "LIVE"}))[0] == "PROBE"
    assert G.decide("s81", "col_r1", [], "fam", {"col_r0", "col_r1"}, pilots, _st({"col_r0": "SIGNED"}))[0] == "FULL"
    fl = [dict(rule="SMELL:X", proven=True)]
    assert G.decide("s81", "col_r1", fl, "fam", {"col_r0", "col_r1"}, pilots, _st({"col_r0": "SIGNED"}))[0] == "PILOT"
    assert G.decide("s81", "c2", [], "f2", {"c1", "c2"}, {}, _st({"c1": "SIGNED"}))[0] == "FULL"       # an already signed member releases
    assert G.decide("s81", "c2", [], "f2", {"c1", "c2"}, {}, _st({"c1": "LIVE"}))[0] == "PROBE"        # a routing member is the pilot


def test_idle_fill():
    assert G.idle_slots({"a": dict(cores=128, load=200)}) == 0
    assert G.idle_slots({"a": dict(cores=128, load=10), "b": dict(cores=64, load=60)}) == 2
    assert G.idle_slots({"epyc2": dict(cores=128, load=57), "epyc12": dict(cores=96, load=178)}) == 1   # one idle host counts
    assert G.idle_pick([("x", 0, 3), ("y", 0, 1), ("z", 1, 0)], 1) == ["y"]


def test_rule_promotion():
    types = {("d", f"t{i}"): ("FAIL", ["R"]) for i in range(4)}
    types.update({("d", f"u{i}"): ("PASS" if i else "FAIL", []) for i in range(6)})
    st = G.rule_stats(types)
    assert st["R"] == [4, 4, 6, 1] and G.promote(st["R"]) == "PROVEN"
    assert G.promote([194, 157, 0, 0]) == "ADVISORY"                    # flags every type: no contrast (FP:NOT-CLEAN 11-25 04:35)
    assert G.promote([3, 3, 6, 0]) == "ADVISORY" and G.promote([10, 3, 10, 2]) == "ADVISORY"
    txt = G.rules_tsv({"R": [4, 4, 6, 1], "Q": [9, 9, 1, 0]}, keep={"Q": "ADVISORY-HAND"})
    rows = {r["rule"]: r["status"] for r in G.parse_tsv(txt)}
    assert rows == {"R": "PROVEN", "Q": "ADVISORY-HAND"}


RPT = """Startpoint: a (rising edge-triggered flip-flop)
Endpoint: b (rising edge-triggered flip-flop)
  -210.00   slack (VIOLATED)
"""


def test_pp_decide_and_release(monkeypatch):
    import auto_visual_review as AVR
    monkeypatch.setattr(AVR, "parse_report", lambda t: dict(wns=-210.0, path_slack=-210.0, worst_slew=None))
    fl = G.pp_decide(dict(rpt=RPT, geom_fail=[["route_demand_v", 1.4], ["grt", 12]], grt="12"))
    assert fl[0].startswith("setup -210") and any("density" in f for f in fl) and any("congestion" in f for f in fl)
    monkeypatch.setattr(AVR, "parse_report", lambda t: dict(wns=-90.0, path_slack=-90.0, worst_slew=None))
    assert G.pp_decide(dict(rpt=RPT, geom_fail=[], grt="0")) == [] and G.pp_decide(None) == []
    t0 = time.time() - 100
    kv = {"fp": G.parse_tsv(f"type\tclass\tstatus\tts\nkv3_pv_v2\tPOSTPLACE\tPASS\t{int(time.time())}\n")}
    assert G.pp_released("qwen_kvsys", "kv3_pv_v2", kv, t0) and not G.pp_released("qwen_kvsys", "kv3_pv_v3", kv, t0)


def test_modes_and_private_goal(monkeypatch):
    assert G.mode({}, "kpg") == "enforce"
    assert G.mode({}, "pp", now=G.PP_ENFORCE_AFTER - 1) == "report" and G.mode({}, "pp", now=G.PP_ENFORCE_AFTER) == "enforce"
    assert G.mode({"launch_gate": {"pp": "off"}}, "pp") == "off"
    kv, qc = T()
    files = {G.VIS_REL: VIS, G.SMELL_REL: SMELL, "lanes/FP-KV.tsv": FP, G.RULES_REL: RULES}
    G.reset_cache()
    rd = lambda rel: files.get(rel)                                                # noqa: E731
    assert G.private_goal("qwen_kvsys", "kv3_sys_c", "route", reader=rd, log=lambda m: None) == "place"
    assert G.private_goal("qwen_kvsys", "kv3_pv_v5", "route", reader=rd, log=lambda m: None) == "route"
    assert G.private_goal("qwen_kvsys", "kv3_sys_c", "grt", reader=rd, log=lambda m: None) == "grt"
    monkeypatch.setenv("OT_KPG_FULL", "1")
    assert G.private_goal("qwen_kvsys", "kv3_sys_c", "route", reader=rd, log=lambda m: None) == "route"


def test_kit_wave_route_hold(monkeypatch):
    import kit_wave as KW
    files = {G.VIS_REL: VIS, G.SMELL_REL: SMELL, "lanes/FP-KV.tsv": FP, G.RULES_REL: RULES}
    G.reset_cache()

    class AP:
        logs = []
        read_coord = staticmethod(lambda rel: files.get(rel))
        log = staticmethod(lambda m: AP.logs.append(m))
    monkeypatch.setattr(KW, "family_of", lambda die, item: item)
    monkeypatch.setattr(KW, "kpg_pp_hold", lambda *a: None)
    st = {"items": {"1": dict(die="qwen_kvsys", item="kv3_sys_c", attempt=1, status="FAIL", q_status="FAIL", updated=1)}}
    cfg = {"dies": {"qwen_kvsys": {"event": "e1"}}, "_otrun_status": {"h": dict(cores=128, load=500)}}
    rec = dict(die="qwen_kvsys", item="kv3_sys_c", attempt=2)
    assert KW.kpg_route_hold(AP, cfg, st, rec) is None                             # first: the known-problem pilot routes
    assert list(st["kpg_pilots"]) == ["qwen_kvsys|kv3_sys_c|e1|SMELL:PILE"]
    st["items"]["2"] = dict(die="qwen_kvsys", item="kv3_sys_c", attempt=2, status="FAIL", q_status="FAIL", updated=2)
    assert KW.kpg_route_hold(AP, cfg, st, rec).startswith("KPG-PROBE: known problems SMELL:PILE")
    cfg["launch_gate"] = {"kpg": "report"}
    assert KW.kpg_route_hold(AP, cfg, st, rec) is None and any("KPG-REPORT" in m for m in AP.logs)
    assert KW.kpg_route_hold(AP, {"dies": {}}, st, dict(die="qwen_kvsys", item="kv3_pv_v5", attempt=1)) is None


def test_real_table_layouts():
    """11-25 tables: SMELL.tsv render checkpoints are not smells; FP-<DIE>.tsv wide (one column per class) layouts"""
    smell = ("t\tkit\tdie\ttype\tstage\ttrigger\tvalue\trender\towner\n"
             "1\t/x/items/kv3_pc_v1__cl4ea58a5c/gen/kv3_pc_v1__cl4ea58a5c\tKV\tfin\tPLACE-GP\tCHECKPOINT\tPLACE-GP render rendering\th:/r\tCOORD\n"
             "1\t/x/gen/kv3_pv_v8\tKV\tkv3-pv-v8-grt\tGRT\tDENSITY-PILE\tov 1449\th:/r\tFP-CONVERGE-KV\n")
    fp = ("type\tSTREET\tTAPNAME\tR8\tVISUAL\tCLEAN\n"
          "kv3_hg\tFAIL:1\tFAIL:2\tpass\tFAIL-A5t7-render\tNO\n"
          "kv3_hg_v2\tpass\tpass\tpass\tPASS\tYES\n"
          "kv3_hg_v3\tFAIL:1 FIXED in A5t8\tpass\tpass\t\tNO\n")
    files = {G.SMELL_REL: smell, "lanes/FP-KV.tsv": fp}
    G.reset_cache()
    kv = G.tables("qwen_kvsys", reader=lambda rel: files.get(rel))
    assert proven(G.flags("qwen_kvsys", "kv3_pc_v1__cl4ea58a5c", kv)) == []
    assert proven(G.flags("qwen_kvsys", "kv3_pv_v8", kv)) == ["SMELL:DENSITY-PILE"]
    fl = G.flags("qwen_kvsys", "kv3_hg__r889141819", kv)
    assert proven(fl) == ["PRE:TAPNAME"] and {"FP:STREET", "FP:VISUAL", "FP:NOT-CLEAN"} <= {f["rule"] for f in fl}
    assert G.flags("qwen_kvsys", "kv3_hg_v2", kv) == []
    assert [f["rule"] for f in G.flags("qwen_kvsys", "kv3_hg_v3", kv)] == ["FP:NOT-CLEAN"]
    s81 = {"fp": G.parse_tsv("type\tfamily\tREACH\tfails\tvisual\titer\ncol_h10_r0_p1__t1__cl574cc59d__pv3d0d4d97\tcol_h10_r0_p1\tFAIL 11\tREACH\tFAIL die:x\tc9s-1\n")}
    assert {f["rule"] for f in G.flags("s81", "col_h10_r0_p1__t1__cl574cc59d", s81)} == {"FP:REACH", "FP:VISUAL", "FP:NOT-CLEAN"}
    assert G.flags("s81", "col_h10_r0_p1__t2", s81) == [dict(rule="FP:NOT-CLEAN", source="FP", proven=False, detail="no VISUAL PASS / CLEAN row")]


def test_hand_proven_rules_place_only():
    """FLOW-0730 F9: five measured rules block a full kit by hand, whatever the rule table says; everything else stays advisory"""
    fp = "type\tclass\tstatus\tproven\tts\n" + "".join(f"t_{c}\t{c}\tFAIL\t\t\n" for c in ("CORE-TAP-OWNER", "MISAIM", "STREET", "REACH", "TAP", "BOUNDARY"))
    smell = "die\ttype\tsmell\nKV\tt_grt\tGRT\nKV\tt_drt\tDRT\n"
    rules = "rule\tstatus\nFP:STREET\tADVISORY\nFP:REACH\tADVISORY\nFP:TAP\tADVISORY\n"
    files = {"lanes/FP-KV.tsv": fp, G.SMELL_REL: smell, G.RULES_REL: rules}
    G.reset_cache()
    kv = G.tables("qwen_kvsys", reader=lambda rel: files.get(rel))
    for c in ("STREET",):                                                       # FLOW-1920 F6: demoted (lift 1.13, p 0.34): mutant of the old hand list
        assert proven(G.flags("qwen_kvsys", "t_" + c, kv)) == [] and not any(f.get("hand") for f in G.flags("qwen_kvsys", "t_" + c, kv))
    for c in ("CORE-TAP-OWNER", "MISAIM", "REACH"):
        fl = G.flags("qwen_kvsys", "t_" + c, kv)
        assert proven(fl) == ["FP:" + c]                                        # PROVEN even though the table says ADVISORY
        m, why, key = G.decide("qwen_kvsys", "t_" + c, fl, "f", {"t_" + c}, {}, _st({}))
        assert m == "PROBE" and "FLOW-0730" in why and key == ""                # no pilot
    fl = G.flags("qwen_kvsys", "t_grt", kv)
    assert proven(fl) == ["SMELL:GRT"] and G.decide("qwen_kvsys", "t_grt", fl, "f", {"t_grt"}, {}, _st({}))[0] == "PROBE"
    for t_ in ("t_TAP", "t_BOUNDARY", "t_drt"):                                  # mutants: advisory classes keep the old behaviour
        assert not any(f.get("hand") for f in G.flags("qwen_kvsys", t_, kv))
    assert proven(G.flags("qwen_kvsys", "t_TAP", kv)) == [] and proven(G.flags("qwen_kvsys", "t_BOUNDARY", kv)) == []
    assert G.decide("qwen_kvsys", "t_TAP", G.flags("qwen_kvsys", "t_TAP", kv), "f", {"t_TAP"}, {}, _st({}))[0] == "FULL"
    txt = G.rules_tsv({"FP:REACH": [102, 95, 95, 63], "FP:TAP": [22, 20, 175, 138], "FP:STREET": [13, 11, 184, 138]})
    rows = {r["rule"]: r["status"] for r in G.parse_tsv(txt)}
    assert rows == {"FP:REACH": "PROVEN-HAND", "FP:TAP": "ADVISORY", "FP:STREET": "ADVISORY"}


def test_site_in_macro_is_advisory_after_f6_demotion():
    """FLOW-1920 F6: SITE-IN-MACRO measured 4/9 flagged fail vs 145/188 unflagged (lift 0.58): advisory now, a firm site no longer forces place-only"""
    fp = "type\tSITE-IN-MACRO\nt_firm\tFAIL:176 on core\nt_halo\tWARN:216 halo only\nt_ok\tPASS\n"
    files = {"lanes/FP-KV.tsv": fp, G.RULES_REL: "rule\tstatus\n"}
    G.reset_cache()
    kv = G.tables("qwen_kvsys", reader=lambda rel: files.get(rel))
    for t_ in ("t_firm", "t_halo", "t_ok"):
        assert proven(G.flags("qwen_kvsys", t_, kv)) == []
    assert "FP:SITE-IN-MACRO" not in G.HAND_PLACE_ONLY and "FP:STREET" not in G.HAND_PLACE_ONLY
    assert {"FP:CORE-TAP-OWNER", "FP:MISAIM", "SMELL:GRT", "FP:REACH"} == set(G.HAND_PLACE_ONLY)
