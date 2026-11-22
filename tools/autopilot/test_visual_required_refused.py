"""VISUAL-NOBLOCK (FLOW-OPS-R2 11-22, FABLE-FLOW-2200 item 1): kit_wave_edit refuses setting review_before_route.required;
apply_reviewed_tree_marker drops it (advisory review)."""
import kit_wave_edit as E


def doc(req=None):
    rb = {"event": "E", "all_items": True}
    if req is not None:
        rb["required"] = req
    return {"dies": {"s81": {"event": "E", "review_before_route": rb}, "qwen_kvsys": {"event": "K"}}}


def test_setting_required_is_refused():
    assert E.required_review_problems(doc(), doc(True))
    new = doc()
    new["dies"]["qwen_kvsys"]["review_before_route"] = {"event": "K", "items": ["a"], "required": True}
    assert any("qwen_kvsys" in p for p in E.required_review_problems(doc(), new))


def test_removing_or_keeping_or_advisory_is_allowed():
    assert E.required_review_problems(doc(True), doc()) == []
    assert E.required_review_problems(doc(True), doc(True)) == []       # unrelated edits on a die that already has it pass
    assert E.required_review_problems(doc(), doc(False)) == []
    assert E.required_review_problems(doc(), doc()) == []
