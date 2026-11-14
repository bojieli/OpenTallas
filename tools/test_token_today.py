"""token_today: class -> plan-of-record join, geometry naming and stage currency labels (no git, no plan files)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import token_today as T  # noqa: E402

PLAN = "2026-11-12T09:05:23Z"
DIE = dict(die="s81", label="S81 data die", plan="p/plan.json", commit="a" * 40, date=PLAN, subject="s", w=10.0, h=5.0,
           instances=[["fW0_p1_b0", "partition", 0, 0, 1, 1, "col_h10_r0_p1__t1__cl574cc59d"],
                      ["eng/u_eng", "hard core", 1, 1, 1, 1, "dsdv_eng_rr_h1"],
                      ["svc0", "partition", 2, 2, 1, 1, "svc_hi_0"]])
RULES = {"designs": {"ds_rom": {"classes": {
    "field": {"rules": [["s81", r"^(col_h(9|10)_.*)$"]], "confidence": "inferred", "why": "ROM columns"},
    "su": {"rules": [["s81", r"^nothing_matches$"]], "confidence": "named", "why": "x"}}}}}


def make():
    t = T.Today.__new__(T.Today)
    t.S = dict(generated=1794654047.0, dies=[], token={"release_lines": ["TOK.DS whole-die · RUNNING", "TOK.HBM x · BLOCKED"], "token_pass": []})
    t.rules, t.now, t.dies, t._cn = RULES, "2026-11-14T00:00:00Z", {"s81": dict(DIE, plan_date=PLAN)}, {}
    t._geo = {"s81": DIE, "s81_head": dict(DIE, die="s81_head", instances=[])}
    return t


def test_label_current_vs_october():
    assert T.label("2026-10-08T18:24:33-07:00", PLAN) == "October record"
    assert T.label("2026-11-13T00:00:00Z", PLAN) == "current"
    assert T.label(None, PLAN) == "unknown"


def test_class_nodes_match_masters_with_variant_suffix():
    cn = make().class_nodes("ds_rom")
    assert cn["field"]["instances"] == ["fW0_p1_b0"] and cn["field"]["masters"] == ["col_h10_r0_p1__t1__cl574cc59d"]
    assert cn["su"]["instances"] == []


def test_apply_replaces_geometry_keeps_october_and_labels_unmapped():
    t = make()
    t.stages = lambda design: ([dict(stage="s", records=[], newest="2026-10-08T00:00:00Z", status="October record")], PLAN)
    t.today_tokens = lambda design: {}
    rec = dict(classes=[dict(id="field", elements=["old"], instances=["old*"]), dict(id="su", elements=["o"], instances=["o*"])],
               geometry=dict(key="ds_s81_layer"), repo_head="abc")
    t.apply(rec, "ds_rom")
    assert rec["geometry"]["october"] == dict(key="ds_s81_layer") and rec["geometry"]["key"].startswith("plan:")
    assert rec["classes"][0]["instances"] == ["fW0_p1_b0"] and rec["classes"][0]["october_instances"] == ["old*"]
    assert rec["classes"][1]["instances"] == [] and rec["classes"][1]["mapping"]["grade"] == "none"
    assert rec["currency"]["cycles"] == "October record" and rec["export"]["generated"] == "2026-11-14T00:00:00Z"
