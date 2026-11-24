"""LAUNCH-GUARD 11-23 (COORD, Fable flow review): FIX 1 LOOK-BEFORE-LAUNCH admission (lbl_gate + kit_wave.launch / run-item / autopilot),
FIX 3 no unchanged retry of a deterministic failure (kit_wave.same_input_repeat_refused, pending_row_live)."""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import lbl_gate as LBL
import kit_wave as KW

HDR = ("# VIS-COVERAGE header\n"
       "die\ttype\tfamily\tvis_lane\trender_paths\tverdict\tcause_class\tstructural_row\trow_status\tupdated\n")


def vis(*rows):
    return HDR + "".join(f"{d}\t{t}\t{f}\tVIS\t-\tv\tc\tsr\t{s}\tu\n" for d, t, f, s in rows)


TABLE = vis(("S81", "s81sl_leaf__t30", "leaf", "DRAFT"), ("S81", "col_h9_r1__t1__cl1a2b3c4d__pv11112222", "col_h9_r1", "IN-EVENT"),
            ("S81", "col_h10_r1__t1__cl95b37463__pv0713a75a", "col_h10", "PRE-PASS"), ("S81", "col_h10_r1__t1__cl95b37463__pv86f5e3b9", "col_h10", "PROBE-PASS"),
            ("KV", "kv3_hgi_v3", "kv3_hgi", "DRAFT"), ("QC", "sle_su_c", "sle_su", "PRE-PASS"), ("HEAD", "hd_ctl", "hd_ctl", "NONE-NEEDED"),
            ("QC", "glue", "glue", "SIGNED"))


class AP:
    HUB_NAME = "intel2"

    def __init__(self, text=TABLE):
        self.text, self.lines = text, []

    def read_coord(self, rel):
        assert rel == LBL.REL
        return self.text

    def log(self, m):
        self.lines.append(m)


def setup_function(_f):
    LBL.reset_cache()


# ---------------------------------------------------------------- lbl_gate
def test_status_lookup_strips_ot_prefix_and_matches_the_die():
    rows = LBL.parse(TABLE)
    assert LBL.lookup(rows, "ot_s81sl_leaf__t30", "s81")[0] == "DRAFT"
    assert LBL.lookup(rows, "kv3_hgi_v3", "qwen_kvsys")[0] == "DRAFT"
    assert LBL.lookup(rows, "kv3_hgi_v3", "s81") == (None, "")              # another die's row never decides
    assert LBL.lookup(rows, "hd_ctl", "s81_head")[0] == "NONE-NEEDED"


def test_refused_statuses_and_allowed_statuses():
    rows = LBL.parse(TABLE)
    assert LBL.check("ot_s81sl_leaf__t30", "s81", rows=rows)[:2] == (True, "LBL-DRAFT")
    assert LBL.check("sle_su_c", "qwen_compute", rows=rows)[:2] == (True, "LBL-PRE-PASS")
    for item, die in (("hd_ctl", "s81_head"), ("glue", "qwen_compute"), ("col_h9_r1__t1__cl1a2b3c4d__pv11112222", "s81")):
        assert LBL.check(item, die, rows=rows)[0] is False, item


def test_probe_through_row_past_the_review_sla_launches():
    rows = LBL.parse(vis(("S81", "s81sl_leaf__t31", "leaf", "PROBE-THROUGH"), ("KV", "kv3_hgi_v3", "kv3_hgi", "DRAFT")))
    assert LBL.check("ot_s81sl_leaf__t31", "s81", rows=rows)[:2] == (False, "LBL-PROBE-THROUGH-OK")
    assert LBL.check("kv3_hgi_v3", "qwen_kvsys", rows=rows)[:2] == (True, "LBL-DRAFT")


def test_a_new_variant_takes_its_siblings_and_any_allowed_sibling_allows():
    rows = LBL.parse(TABLE)
    got = LBL.check("col_h10_r1__t1__cl95b37463__pvdeadbeef", "s81", rows=rows)
    assert got[0] is False and got[1] == "LBL-PROBE-PASS-OK"
    assert LBL.check("col_h9_r1__t1__cl1a2b3c4d__pv99999999", "s81", rows=rows)[0] is False


def test_probe_kits_and_untracked_types_are_never_held():
    rows = LBL.parse(TABLE)
    assert LBL.check("ot_s81sl_leaf__t30", "s81", env={"OT_PROBE_THROUGH": "1"}, rows=rows)[:2] == (False, "LBL-PROBE")
    for g in ("place", "geom", "grt", "cts"):
        assert LBL.check("ot_s81sl_leaf__t30", "s81", goal=g, rows=rows)[0] is False
    assert LBL.check("ot_s81sl_leaf__t30", "s81", goal="route", rows=rows)[0] is True
    assert LBL.check("brand_new_type", "s81", rows=rows)[:2] == (False, "LBL-NOROW")


def test_table_is_cached_for_five_minutes_and_unreadable_means_not_held(tmp_path, monkeypatch):
    monkeypatch.setattr(LBL, "CACHE", str(tmp_path / "c.tsv"))
    monkeypatch.setenv("OT_COORD_DIR", str(tmp_path / "nocoord"))
    monkeypatch.setattr(LBL, "_read_hub", lambda hub: None)
    monkeypatch.setattr(LBL, "_read_local", lambda: (None, ""))
    (tmp_path / "c.tsv").write_text(TABLE)
    assert LBL.load(now=1000.0)[0]                                            # no reader: the fresh disk cache serves hosts without ~/coord
    LBL.reset_cache()
    n = []
    r1 = LBL.load(reader=lambda: (n.append(1), TABLE)[1], now=1000.0)
    LBL.load(reader=lambda: (n.append(1), TABLE)[1], now=1000.0 + 299)
    assert r1[0] and len(n) == 1                                              # cached
    LBL.load(reader=lambda: (n.append(1), TABLE)[1], now=1000.0 + 301)
    assert len(n) == 2                                                        # refreshed after 5 min
    LBL.reset_cache()
    assert LBL.check("ot_s81sl_leaf__t30", "s81", reader=lambda: "", now=5000.0)[:2] == (False, "LBL-NOTABLE")


# ---------------------------------------------------------------- kit_wave.launch gate (FIX 1)
def cfg_(**die):
    d = {"enabled": True, "event": "EV1", "src_sha": "src1"}
    d.update(die)
    return {"dies": {"s81": d, "qwen_kvsys": dict(d), "qwen_compute": dict(d)}}


def test_wave_launch_of_a_draft_type_is_refused_and_logged_lbl_status():
    ap, st = AP(), {}
    assert KW.lbl_launch_refused(ap, cfg_(), st, "s81", {"item": "ot_s81sl_leaf__t30"}) is True
    assert any("LAUNCH-REFUSED s81/ot_s81sl_leaf__t30: LBL-DRAFT" in l for l in ap.lines)
    assert st["lbl_refused"]["s81|ot_s81sl_leaf__t30"]["code"] == "LBL-DRAFT"
    # the three hub-b0383bc leaks
    LBL.reset_cache()
    assert KW.lbl_launch_refused(AP(), cfg_(), {}, "qwen_kvsys", {"item": "kv3_hgi_v3"}) is True
    assert KW.lbl_launch_refused(AP(), cfg_(), {}, "qwen_compute", {"item": "sle_su_c"}) is True


def test_wave_probe_item_env_and_passed_rows_launch():
    c = cfg_(item_env={"ot_s81sl_leaf__t30": {"OT_PROBE_THROUGH": "1"}})
    assert KW.lbl_launch_refused(AP(), c, {}, "s81", {"item": "ot_s81sl_leaf__t30"}) is False
    assert KW.lbl_launch_refused(AP(), cfg_(), {}, "s81", {"item": "col_h9_r1__t1__cl1a2b3c4d__pv11112222"}) is False
    assert KW.lbl_launch_refused(AP(), cfg_(lbl_gate=False), {}, "s81", {"item": "ot_s81sl_leaf__t30"}) is False


def test_launch_calls_the_gate_before_any_build(monkeypatch):
    monkeypatch.setattr(KW, "scheduler_current", lambda AP: True)
    monkeypatch.setattr(KW, "hub_launch_held", lambda *a: False)
    monkeypatch.setattr(KW, "event_pending_wait", lambda *a: False)
    hit = []
    monkeypatch.setattr(KW, "tool_skew_refuse", lambda *a: hit.append(1) or True)
    assert KW.launch(AP(), cfg_(), {}, "s81", {"item": "ot_s81sl_leaf__t30"}, "intel2") is None
    assert hit == []                                                           # refused at the LBL gate


def test_private_run_item_sign_off_goal_is_refused_probe_goal_runs(monkeypatch, tmp_path):
    monkeypatch.setattr(LBL, "CACHE", str(tmp_path / "lbl/c.tsv"))
    monkeypatch.setattr(LBL, "load", lambda **k: (LBL.parse(TABLE), "t"))
    sp = {"private": {"lane": "L"}, "die": "s81", "item": "ot_s81sl_leaf__t30", "gen_env": {}}
    assert KW.private_lbl_refusal(sp, "route").startswith("LBL-DRAFT")
    assert "ot_s81sl_leaf__t30\tLBL-DRAFT" in (tmp_path / "lbl/refusals.log").read_text()
    assert KW.private_lbl_refusal(sp, "auto").startswith("LBL-DRAFT")
    assert KW.private_lbl_refusal(sp, "grt") == "" and KW.private_lbl_refusal(sp, "geom") == ""
    assert KW.private_lbl_refusal(dict(sp, gen_env={"OT_PROBE_THROUGH": "1"}), "route") == ""
    assert KW.private_lbl_refusal(dict(sp, private=None), "route") == ""         # a wave spec: gated in launch()


def test_autopilot_lane_queue_row_waits_wave_rows_and_running_jobs_do_not(monkeypatch):
    import autopilot as AP_
    monkeypatch.setattr(AP_, "read_coord", lambda rel: TABLE)
    r = {"die": "s81", "type": "ot_s81sl_leaf__t30", "goal": "route", "mode": "", "geom_ref": "AUTO-GEOM REVIEW x", "kit": "epyc2:/srv/x/kits/t30/gen"}
    assert AP_.lbl_queue_hold(r).startswith("LBL-DRAFT")
    assert AP_.lbl_queue_hold(dict(r, geom_ref="AUTO-GEOM KIT-WAVE 18a2688b741 epyc2:/x")) == ""
    assert AP_.lbl_queue_hold(dict(r, goal="grt")) == ""
    assert AP_.lbl_queue_hold(r, {"attempts": 1, "status": "WAIT-LBL"}) == ""
    assert AP_.lbl_queue_hold(dict(r, kit="epyc2:/srv/x/probe_t30/gen")) == ""
    assert "WAIT-LBL" in AP_.WAITS


# ---------------------------------------------------------------- FIX 3: same-input repeat
BLOCK = "45d7e1127cc07cd758d461137234a246cf5033d56723bbb7d9e9b33caaf3d517"


def st_with(rec, ledger_inputs=None):
    st = {"items": {f"s81|dsdv_slice_c1x_C__t10|b{BLOCK[:13]}": rec}}
    if ledger_inputs is not None:
        st["repeat_ledger"] = {f"s81|dsdv_slice_c1x_C__t10@EV1": {"att": [{"n": rec["attempt"], "cls": "PLAN", "inputs": ledger_inputs}], "inputs": ledger_inputs, "state": ""}}
    return st


def failed(attempt=2, **k):
    r = {"die": "s81", "item": "dsdv_slice_c1x_C__t10", "attempt": attempt, "status": "ENQUEUED", "q_status": "FAIL", "q_class": "PLAN", "event": "EV1",
         "block_sha": BLOCK, "started": 1000.0, "updated": 2000.0,
         "q_reason": "FAIL_POSTPLACE PLACE-SETUP-STOP wns -733.30 ps < -300 ps", "input_parts": {"pc": {"src": "src1"}, "env": {"OT_PGCAP": "1"}}}
    r.update(k)
    return r


R = {"item": "dsdv_slice_c1x_C__t10", "block_sha": BLOCK}


def test_place_setup_stop_on_an_unchanged_block_event_src_is_refused():
    ap = AP()
    st = st_with(failed(), {"block": BLOCK, "src": "src1", "tools": ""})
    assert KW.same_input_repeat_refused(ap, cfg_(), st, "s81", R) is True
    assert any("DESIGN-SAME-INPUT" in l and "dsdv_slice_c1x_C__t10" in l for l in ap.lines)


def test_any_digest_change_releases():
    st = st_with(failed())
    assert KW.same_input_repeat_refused(AP(), cfg_(), st, "s81", dict(R, block_sha="f" * 64)) is False
    assert KW.same_input_repeat_refused(AP(), cfg_(event="EV2"), st, "s81", R) is False
    assert KW.same_input_repeat_refused(AP(), cfg_(src_sha="src2"), st, "s81", R) is False
    assert KW.same_input_repeat_refused(AP(), cfg_(item_env={"dsdv_slice_c1x_C__t10": {"OT_KEEP_WIRES": "x"}}), st, "s81", R) is False


def test_grt_label_routing_and_unsignable_cancel_are_design_classes():
    for k in ({"q_class": "ROUTING", "q_reason": "grt-overflow GRT-0116"}, {"status": "CANCELLED", "q_status": "CANCELLED", "q_class": "", "class": "CANCEL-UNSIGNABLE"},
              {"q_class": "", "q_reason": "GRT-LABEL DESIGN-FAIL: overflow 9688 at round 10"}):
        assert KW.same_input_repeat_refused(AP(), cfg_(), st_with(failed(**k)), "s81", R) is True, k


def test_superseded_operator_and_flow_failures_are_not_held():
    for k in ({"status": "CANCELLED", "q_status": "", "q_class": "", "class": "SUPERSEDED", "q_reason": ""},
              {"q_class": "FLOW", "q_reason": "tool input file missing"}):
        assert KW.same_input_repeat_refused(AP(), cfg_(), st_with(failed(**k)), "s81", R) is False, k


def test_unblock_line_and_a_retry_key_added_after_the_failure_release():
    st = st_with(failed())
    c = cfg_()
    c["_unblocks"] = [("dsdv_slice_c1x_C__t10", "*")]
    assert KW.same_input_repeat_refused(AP(), c, st, "s81", R) is False
    c = cfg_(retry=["dsdv_slice_c1x_C__t10@2"])
    st["retry_seen"] = {"s81|EV1|dsdv_slice_c1x_C__t10@2": 2500.0}
    assert KW.same_input_repeat_refused(AP(), c, st, "s81", R) is False
    st["retry_seen"] = {"s81|EV1|dsdv_slice_c1x_C__t10@2": 1500.0}              # seen before the failure ended: not an answer to it
    assert KW.same_input_repeat_refused(AP(), c, st, "s81", R) is True
    c["dies"]["s81"]["_retry_auto"] = {"dsdv_slice_c1x_C__t10@2": 1}
    st["retry_seen"] = {"s81|EV1|dsdv_slice_c1x_C__t10@2": 2500.0}              # a pending-row key never counts as a fresh answer
    assert KW.same_input_repeat_refused(AP(), c, st, "s81", R) is True


def test_infra_keeps_one_free_retry_then_waits():
    inf = dict(status="FAIL", q_status=None, q_class="", **{"class": "INFRA"}, reason="infra (INFRA-VIEW-MISSING: view qfd_dv_s8x_btab missing)")
    st = st_with(failed(attempt=24, **inf))
    assert KW.same_input_repeat_refused(AP(), cfg_(), st, "s81", R, now=2100.0) is False     # first infra failure: free retry
    st["items"][next(iter(st["items"]))].update(attempt=25, updated=2600.0)
    assert KW.same_input_repeat_refused(AP(), cfg_(), st, "s81", R, now=2700.0) is True      # the same infra cause again
    assert KW.same_input_repeat_refused(AP(), cfg_(), st, "s81", R, now=2600.0 + KW.INFRA_REPEAT_WAIT_S + 1) is False


def test_stale_pending_row_of_an_older_event_is_not_a_key():
    """kit_wave_pending.tsv 6d4bed7abfe s81 dsdv_slice_c1x_C__t10@3 (11-05) released attempt 3 of event 18a2688b741 (11-23 00:07)"""
    rec = failed(attempt=3, started=time.mktime(time.strptime("2026-11-23 00:07", "%Y-%m-%d %H:%M")))
    st = {"items": {"k": rec}}
    assert KW.pending_row_live(st, "s81", "dsdv_slice_c1x_C__t10@3", "2026-11-22 07:22 PST") is False   # row seen before the attempt started
    assert KW.pending_row_live(st, "s81", "dsdv_slice_c1x_C__t10@3", "2026-11-23 01:30 PST") is True
    assert KW.pending_row_live(st, "s81", "dsdv_slice_c1x_C__t10@5", "2026-11-23 01:30 PST") is False   # not the latest attempt: no pre-release


def test_release_pending_drops_stale_rows():
    rec = failed(attempt=3, started=time.mktime(time.strptime("2026-11-23 00:07", "%Y-%m-%d %H:%M")))
    st = {"items": {"k": rec}, "pending_released": {"6d4bed7abfe|hub|s81|dsdv_slice_c1x_C__t10@3": "2026-11-22 07:22 PST"}}
    c = cfg_()
    rows = [{"sha": "6d4bed7abfe", "scope": "hub", "die": "s81", "retry": "dsdv_slice_c1x_C__t10@3", "lane": "KW"}]
    KW.release_pending(c, st, rows, lambda *a: True, {})
    assert "dsdv_slice_c1x_C__t10@3" not in (c["dies"]["s81"].get("retry") or [])


def test_place_setup_stop_below_minus_300_is_design_even_when_stored_infra_or_flow():
    """COORD 11-23: seqhost__t1 attempts 4-6 all PLACE-SETUP-STOP wns -479.73 ps on one block / event / src"""
    for k in ({"q_class": "", "class": "INFRA", "status": "FAIL", "q_status": None, "reason": "FAIL_POSTPLACE PLACE-SETUP-STOP wns -479.73 ps < -300 ps"},
              {"q_class": "FLOW"}):
        assert KW._rec_design_class(failed(**k)).startswith("PLACE-SETUP-STOP -"), k
        assert KW.same_input_repeat_refused(AP(), cfg_(), st_with(failed(**k)), "s81", R) is True, k


def test_an_older_design_failure_is_not_hidden_by_a_later_cancelled_attempt():
    st = st_with(failed())
    st["items"]["later"] = failed(attempt=3, status="CANCELLED", q_status="", q_class="", **{"class": "SUPERSEDED"}, q_reason="", started=3000.0, updated=3100.0)
    assert KW.same_input_repeat_refused(AP(), cfg_(), st, "s81", R) is True
    assert KW.same_input_repeat_refused(AP(), cfg_(src_sha="src2"), st, "s81", R) is False
    c = cfg_(retry=["dsdv_slice_c1x_C__t10@3"])
    st["retry_seen"] = {"s81|EV1|dsdv_slice_c1x_C__t10@3": 2500.0}
    assert KW.same_input_repeat_refused(AP(), c, st, "s81", R) is False
