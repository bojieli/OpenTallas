"""WAVE-FLOW-R2 11-17 (COORD, KV-R3 gap): the staged child-view files a prov_views failure read are item inputs; a view fix releases the item."""
import kit_wave as KW

WHY = "PLAN: PROVISIONAL view FAIL @prov_views: PROV_FAIL qkd_hr_phy_adp: configured detailed abstract not accepted"


def cfg(stage_dir="/srv/s/kvview_stage/qkd_hr_phy_adp"):
    return {"dies": {"kv": {"src_sha": "s", "_src_overlay": "o", "_plan_sha": "p", "event": "e", "enabled": True,
                            "_prov_deps": {"hub_wi": ["qkd_hr_phy_adp"]},
                            "prov_view_sources": {"qkd_hr_phy_adp": [{"host": "epyc9", "dir": stage_dir, "detailed_lef": "detail_view.lef",
                                                                      "detailed_receipt": "detail_receipt.json"}]}}}}


def rec():
    return {"die": "kv", "item": "hub_wi", "block_sha": "b", "stage": "prov_views"}


def test_view_inputs_name_every_staged_file(monkeypatch):
    monkeypatch.setattr(KW, "view_sha", lambda host, p, **k: "h:" + p.rsplit("/", 1)[-1])
    v = KW.view_inputs(cfg(), "kv", "hub_wi")
    names = sorted(k.rsplit("/", 1)[-1] for k in v)
    assert names == ["detail_receipt.json", "detail_view.lef", "qkd_hr_phy_adp.lef", "qkd_hr_phy_adp_ff.lib", "qkd_hr_phy_adp_tt.lib"]
    assert all(k.startswith("epyc9:/srv/s/kvview_stage/") for k in v)
    assert KW.view_inputs(cfg(), "kv", "other_item") == {}


def test_a_view_fix_releases_the_item_and_unrelated_changes_do_not(monkeypatch):
    state = {"receipt": "r1"}
    monkeypatch.setattr(KW, "view_sha", lambda host, p, **k: state["receipt"] if p.endswith("detail_receipt.json") else "same")
    monkeypatch.setattr(KW, "stage_tools_digest", lambda root=None, group="", files=None: "t")
    st = {}
    KW.note_fail_key(cfg(), st, rec(), "PLAN", WHY)
    assert "views" in st["fail_keys"]["kv|hub_wi"]["parts"]
    bl, why, chg = KW.fail_key_gate(cfg(), st, "kv", "hub_wi", "b")
    assert bl and chg == []                              # nothing changed: still refused
    state["receipt"] = "r2"                              # KV-R3 re-stages the receipt
    bl, why, chg = KW.fail_key_gate(cfg(), st, "kv", "hub_wi", "b")
    assert not bl and chg == ["views"]


def test_old_key_without_views_is_not_released_by_their_presence(monkeypatch):
    monkeypatch.setattr(KW, "view_sha", lambda host, p, **k: "x")
    monkeypatch.setattr(KW, "stage_tools_digest", lambda root=None, group="", files=None: "t")
    st = {}
    KW.note_fail_key(cfg(), st, rec(), "PLAN", WHY)
    st["fail_keys"]["kv|hub_wi"]["parts"].pop("views")
    assert KW.fail_key_gate(cfg(), st, "kv", "hub_wi", "b")[0]
