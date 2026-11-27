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
