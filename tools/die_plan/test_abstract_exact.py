"""abstract_exact: blanket M4/M5 OBS -> exact metal grown / merged / clipped, M1-M3 + pins untouched; PRECHECK
ABSTRACT-BLANKET-OBS report-only; merged_gds_drc verdict rules."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abstract_exact as AE  # noqa: E402
import merged_gds_drc as MG  # noqa: E402

HEAD = """VERSION 5.8 ;
MACRO core
  CLASS BLOCK ;
  SIZE 100 BY 50 ;
  PIN a
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT  0 20 0.5 20.024 ;
    END
  END a
  PIN VDD
    DIRECTION INOUT ;
    USE POWER ;
    PORT
      LAYER M5 ;
        RECT  12 1 12.12 49 ;
    END
  END VDD
  PIN VSS
    DIRECTION INOUT ;
    USE GROUND ;
    PORT
      LAYER M5 ;
        RECT  14 1 14.12 49 ;
    END
  END VSS
"""


def blanket():
    return HEAD + "  OBS\n" + "".join(f"    LAYER M{i} ;\n     RECT  0 0 100 50 ;\n" for i in range(1, 6)) + "  END\nEND core\n"


def exact(m4=("1 10 30 10.024", "99.99 30 100 30.024"), m5=("20 1 20.024 49",)):
    body = "".join(f"    LAYER M{i} ;\n     RECT  0 0 100 50 ;\n" for i in range(1, 4))
    body += "    LAYER M4 ;\n" + "".join(f"     RECT  {r} ;\n" for r in m4)
    body += "    LAYER M5 ;\n" + "".join(f"     RECT  {r} ;\n" for r in m5)
    return HEAD + "  OBS\n" + body + "  END\nEND core\n"


def _obs(path):
    W, H, obs, _ = AE.layer_rects(path)
    return obs


def test_form_replaces_blanket_routing_layers_only(tmp_path):
    b, d, o, r = tmp_path / "b.lef", tmp_path / "d.lef", tmp_path / "o.lef", tmp_path / "r.json"
    b.write_text(blanket())
    d.write_text(exact())
    assert AE.form(b, d, o, r) == 0
    rec = json.loads(r.read_text())
    assert rec["layers"] == ["M4", "M5"] and rec["check_ok"] and rec["verdict"] == "OK"
    obs = _obs(o)
    for L in ("M1", "M2", "M3"):                                 # M1-M3 stay blanket
        assert obs[L] == [(0, 0, 100000, 50000)]
    # M4 grown by the pitch (0.048) and clipped to the outline; nothing outside 0..100 x 0..50
    assert all(0 <= r[0] and r[2] <= 100000 and 0 <= r[1] and r[3] <= 50000 for L in ("M4", "M5") for r in obs[L])
    assert any(r[0] == 952 and r[2] == 30048 for r in obs["M4"])
    assert rec["obs_after"]["M4"][0] < 5 and rec["obs_after"]["M5"][0] < 5
    assert o.read_text().split("  OBS")[0] == b.read_text().split("  OBS")[0]       # pins / SIZE byte-identical
    assert rec["pins_without_access"] == []


def test_pin_own_shape_cut_only_foreign_metal_stays(tmp_path):
    """v3 (Fable 11-25): only the signal pin's own shape is cut; foreign metal 30 nm away stays OBS; no sliver < min width"""
    b, d, o, r = tmp_path / "b.lef", tmp_path / "d.lef", tmp_path / "o.lef", tmp_path / "r.json"
    b.write_text(blanket())
    d.write_text(exact(m4=("0.53 19.99 3 20.03",)))              # foreign metal 30 nm right of pin a
    assert AE.form(b, d, o, r) == 0
    pin = (0, 20000, 500, 20024)
    obs = _obs(o)["M4"]
    assert not any(q[0] < pin[2] and q[2] > pin[0] and q[1] < pin[3] and q[3] > pin[1] for q in obs)
    covered = AE.K.union_minus([(530, 19990, 3000, 20030)], obs)
    assert covered == []                                         # the foreign metal is fully OBS
    assert all(min(q[2] - q[0], q[3] - q[1]) >= 24 for q in obs)


def test_dense_layer_is_not_replaced(tmp_path):
    b, d, o, r = tmp_path / "b.lef", tmp_path / "d.lef", tmp_path / "o.lef", tmp_path / "r.json"
    b.write_text(blanket())
    d.write_text(exact(m4=("0 0 100 30",), m5=("20 1 20.024 49",)))   # M4 60 % real metal: stays blanket
    assert AE.form(b, d, o, r) == 0
    assert json.loads(r.read_text())["layers"] == ["M5"]
    assert _obs(o)["M4"] == [(0, 0, 100000, 50000)]


def test_nothing_to_do(tmp_path):
    b, d, o = tmp_path / "b.lef", tmp_path / "d.lef", tmp_path / "o.lef"
    d.write_text(exact())
    b.write_text(exact())
    assert AE.form(b, d, o) == 1 and not o.exists()


def test_precheck_report_only(tmp_path):
    (tmp_path / "v").mkdir()
    (tmp_path / "v" / "core.lef").write_text(blanket())
    (tmp_path / "v" / "ok.lef").write_text(exact())
    raw = {"die": "kv", "partition_types": {
        "t1": {"hard_cores": [{"inst": "u0", "lef": "v/core.lef"}, {"inst": "u1", "lef": "v/ok.lef"}]},
        "t2": {"hard_cores": [{"inst": "u0", "lef": "physical/asap7_memory_macros/x/x.lef"}]}}}
    f = AE.findings(raw, str(tmp_path))
    warn = [x for x in f if x.startswith("WARN ABSTRACT-BLANKET-OBS")]
    assert len(warn) == 1 and "kv/core" in warn[0] and "M4 100%/1 rect" in warn[0]
    assert not any(x.startswith("FAIL") for x in f)
    assert f[-1] == "LIST ABSTRACT-BLANKET-OBS die kv hard-core views 2 blanket 1"


def test_merged_gds_verdict():
    cells = {"filled": {"m": "/out/core_m.gds"}, "missing": [], "empty_allowed": []}
    assert MG.judge({"new_hardcore": 0, "new_parent": 3}, cells)["verdict"] == "PASS"
    assert MG.judge({"new_hardcore": 2}, cells)["verdict"] == "FAIL"
    assert MG.judge({"new_hardcore": 0}, dict(cells, missing=["x"]))["verdict"] == "FAIL"


def test_merged_gds_gate_required_only_for_exact_views(tmp_path):
    b, d = tmp_path / "b.lef", tmp_path / "d.lef"
    b.write_text(blanket())
    d.write_text(exact(m4=tuple("%d 10 %d 10.024" % (i, i + 1) for i in range(1, 20, 2))))
    kit = tmp_path / "kit"
    (kit / "macros").mkdir(parents=True)
    assert MG.gate_check(kit) is None                                # no views at all
    (kit / "macros" / "core.lef").write_text(blanket())
    assert not MG.needs_gate(kit / "macros" / "core.lef") and MG.gate_check(kit) is None
    assert AE.form(b, d, kit / "macros" / "core.lef") == 0          # the exact form: the parent may route over the core
    assert MG.needs_gate(kit / "macros" / "core.lef")
    g = MG.gate_check(kit)
    assert g["verdict"] == "NOT RUN"                                 # blocks until the merged-GDS DRC ran
    (kit / "merged_gds_drc").mkdir()
    (kit / "merged_gds_drc" / "verdict.json").write_text(json.dumps({"verdict": "PASS", "new_hardcore": 0}))
    assert MG.gate_check(kit)["verdict"] == "PASS"
    (kit / "merged_gds_drc" / "verdict.json").write_text(json.dumps({"verdict": "ERROR"}))
    assert MG.gate_check(kit)["verdict"] == "NOT RUN"
    kp = MG.kit_plan(kit)
    assert kp["required"] and kp["allow_empty"] == "core"             # no core.gds beside the view yet


def test_signoff_merged_gds_guard_blocks_under_every_profile():
    import signoff
    rec = {"verdict": "SIGNED", "reasons": [], "local_verdict": "SIGNED",
           "checks": {"merged_gds_drc": {"verdict": "NOT RUN"}}}
    signoff.merged_gds_guard(rec)
    assert rec["verdict"] == "NOT SIGNED" and rec["local_verdict"] == "NOT SIGNED"
    assert rec["reasons"][-1].startswith("merged_gds_drc: NOT RUN")
    ok = {"verdict": "SIGNED", "reasons": [], "checks": {"merged_gds_drc": {"verdict": "PASS"}}}
    assert signoff.merged_gds_guard(ok)["verdict"] == "SIGNED"
    none = {"verdict": "SIGNED", "reasons": [], "checks": {}}
    assert signoff.merged_gds_guard(none)["verdict"] == "SIGNED"


def test_macro_name_skips_propertydefinitions(tmp_path):
    p = tmp_path / "m.lef"
    p.write_text("VERSION 5.8 ;\nPROPERTYDEFINITIONS\n  MACRO width INTEGER ;\nEND PROPERTYDEFINITIONS\nMACRO real_core\n  CLASS BLOCK ;\nEND real_core\n")
    assert MG.macro_name(p) == "real_core"


def test_stale_non_blanket_layer_is_replaced(tmp_path):
    """STALE-OBS 11-25 (hd_host_e): a non-blanket M6 OBS from another build that misses real metal of the signed DB is
    replaced by the exact one; a non-blanket layer that covers all real metal is left alone"""
    b, d, o, r = tmp_path / "b.lef", tmp_path / "d.lef", tmp_path / "o.lef", tmp_path / "r.json"
    stale6 = "    LAYER M6 ;\n     RECT  50 40 60 40.032 ;\n    LAYER M7 ;\n     RECT  0 0 100 50 ;\n  END\nEND core\n"
    b.write_text(blanket().replace("  END\nEND core\n", stale6))
    real6 = "    LAYER M6 ;\n     RECT  30 2.128 80 2.16 ;\n    LAYER M7 ;\n     RECT  5 5 5.032 20 ;\n  END\nEND core\n"
    d.write_text(exact().replace("  END\nEND core\n", real6))
    assert AE.stale_layers(b, d) == {"M6": dict(uncovered=1, metal_rects=1, uncovered_pct=100.0,
                                                example_nm=[30000, 2128, 80000, 2160])}
    assert AE.form(b, d, o, r) == 0
    rec = json.loads(r.read_text())
    assert rec["layers"] == ["M4", "M5", "M6"] and rec["schema"].endswith("v4")
    m6 = _obs(o)["M6"]
    assert AE.uncovered(m6, [(30000, 2128, 80000, 2160)]) == []          # the real wire is OBS now
    assert not AE.uncovered([(50000, 40000, 60000, 40032)], m6) == []    # the stale rect is gone
    assert _obs(o)["M7"] == [(0, 0, 100000, 50000)]                      # M7 covered all real metal: untouched


def test_pin_eol_own_wire_merged_and_keepout_clear(tmp_path):
    """PIN-EOL 11-25 (col_h9_r2 Lef58EolKeepOut): exact export puts the pin's own wire beyond the 0.084 pin sliver in OBS;
    v4 merges it into the pin, keeps grown OBS out of the 0.048 line-end band, keeps real foreign metal 50 nm past the end"""
    b, d, o, r = tmp_path / "b.lef", tmp_path / "d.lef", tmp_path / "o.lef", tmp_path / "r.json"
    b.write_text(blanket())
    hd = HEAD.replace("RECT  0 20 0.5 20.024", "RECT  0 20 0.084 20.024")
    body = "".join(f"    LAYER M{i} ;\n     RECT  0 0 100 50 ;\n" for i in range(1, 4))
    body += "    LAYER M4 ;\n     RECT  0.016 20 0.131 20.024 ;\n     RECT  0.181 20 3 20.024 ;\n"
    body += "    LAYER M5 ;\n     RECT  20 1 20.024 49 ;\n"
    d.write_text(hd + "  OBS\n" + body + "  END\nEND core\n")
    b.write_text(hd + blanket()[len(HEAD):])
    assert AE.pin_eol_findings(d)["M4"]["pins"] == 1               # the raw export has the defect
    assert AE.form(b, d, o, r) == 0
    rec = json.loads(r.read_text())
    assert rec["pin_wire_merge"]["merged_rects"] == 1 and rec["pin_rects_added"] == 1
    assert rec["pin_eol"] == {} and AE.pin_eol_findings(o) == {}
    assert rec["real_metal_exposed_um2"] == {}
    _, _, _, pins = AE.layer_rects(o)
    assert (16, 20000, 131, 20024) in pins["M4"]


def test_pin_eol_fix_moves_only_the_short_stub(tmp_path):
    """pin-eol-fix on a foreign view: the 0.016-0.131 stub on pin a's track and width moves into pin a; the separate wire at
    0.181 and everything else stays"""
    src, out = tmp_path / "v.lef", tmp_path / "o.lef"
    hd = HEAD.replace("RECT  0 20 0.5 20.024", "RECT  0 20 0.084 20.024")
    body = "    LAYER M4 ;\n     RECT  0.016 20 0.131 20.024 ;\n     RECT  0.181 20 3 20.024 ;\n"
    src.write_text(hd + "  OBS\n" + body + "  END\nEND core\n")
    rep = AE.pin_eol_fix(src, out)
    assert rep["moved"] == 1 and rep["before"]["M4"]["pins"] == 1 and rep["after"] == {}
    _, _, obs, pins = AE.layer_rects(out)
    assert obs["M4"] == [(181, 20000, 3000, 20024)] and (16, 20000, 131, 20024) in pins["M4"]
