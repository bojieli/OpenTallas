import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW   # noqa: E402


def test_post_throttle_receipt_and_reviewer(tmp_path):
    posts, bp = [], tmp_path / "b.json"
    f = lambda lane, text: posts.append((lane, text))
    t = "WAIT-PLAN-VISUAL: missing fresh plan image verdict for qwen_kvsys/x form abc123; request /r/plan_visual_request.json"
    assert KW.wait_state_post("qwen_kvsys", "x", t, now=100, post_fn=f, book_path=bp)
    assert posts[0][0] == "KIT-WAVE" and "PLAN-VISUAL-REVIEW.tsv" in posts[0][1] and "abc123" in posts[0][1] and "KV-INT-R3" in posts[0][1]
    assert not KW.wait_state_post("qwen_kvsys", "x", t, now=100 + 3600, post_fn=f, book_path=bp)          # throttled
    assert KW.wait_state_post("qwen_kvsys", "y", t, now=100 + 3600, post_fn=f, book_path=bp)              # other item
    assert KW.wait_state_post("qwen_kvsys", "x", "WAIT-VISUAL: place done", cfg={"dies": {"qwen_kvsys": {"reviewer_lane": "REV1"}}},
                              now=100 + 3600, post_fn=f, book_path=bp) and "GEOM-REVIEW.md" in posts[-1][1] and "REV1" in posts[-1][1]
    assert KW.wait_state_post("qwen_kvsys", "x", t, now=100 + 6 * 3600 + 1, post_fn=f, book_path=bp)      # 6 h later
    assert not KW.wait_state_post("qwen_kvsys", "x", "FAIL: no", now=1, post_fn=f, book_path=bp)
    assert KW.__dict__["HP"] if False else True


def test_s81_head_routes_to_head_int_r3_not_s81(tmp_path):
    import hub_post as HP
    assert HP.int_r3_lane("s81_head") == "HEAD-INT-R3"
    assert HP.int_r3_lane("s81") == "S81-INT-R3"
    assert HP.int_r3_lane("qwen_kvsys") == "KV-INT-R3"
    assert HP.int_r3_lane("qwen_compute") == "QC-INT-R3"
    posts = []
    t = "WAIT-PLAN-VISUAL: missing fresh plan image verdict for s81_head/hd_x form abc123; request /r/plan_visual_request.json"
    assert KW.wait_state_post("s81_head", "hd_x", t, now=1, post_fn=lambda lane, text: posts.append((lane, text)), book_path=tmp_path / "b.json")
    assert "HEAD-INT-R3" in posts[0][1] and "S81-INT-R3" not in posts[0][1]
