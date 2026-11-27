import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW   # noqa: E402

CFG = {"dies": {"qc": {"die_owner": "QC-OWN"}}}
SKIP = {"outside configured only_items": ["a", "b"]}


def run(st, d, picks, skip, now, posts):
    return KW.allowlist_stale_step(CFG, st, "qc", d, picks, skip, now=now, post_fn=lambda lane, text: posts.append((lane, text)))


def test_empty_list_posts_after_1h_once_per_6h_and_resets():
    st, posts, d = {}, [], {"only_items": []}
    assert not run(st, d, [], SKIP, 1000, posts) and not posts       # first seen
    assert not run(st, d, [], SKIP, 1000 + 3600, posts)              # exactly 1 h: not yet
    assert run(st, d, [], SKIP, 1000 + 3601, posts) and len(posts) == 1
    assert posts[0][0] == "KIT-WAVE" and "qc" in posts[0][1] and "(empty)" in posts[0][1]
    assert not run(st, d, [], SKIP, 1000 + 3 * 3600, posts) and len(posts) == 1     # throttled
    assert run(st, d, [], SKIP, 1000 + 3601 + 6 * 3600, posts) and len(posts) == 2
    assert not run(st, d, ["x"], SKIP, 1000 + 20 * 3600, posts) and "qc" not in st["allow_stale"]   # a pick resets the state


def test_nonmatching_list_and_no_false_positives():
    st, posts = {}, []
    d = {"only_items": ["zz"]}
    run(st, d, [], SKIP, 0, posts)
    assert run(st, d, [], SKIP, 4000, posts)
    st2, p2 = {}, []
    run(st2, d, [], dict(SKIP, **{"live job (another lane)": ["zz"]}), 0, p2)   # allowed item matched a row (in flight)
    assert not run(st2, d, [], dict(SKIP, **{"live job (another lane)": ["zz"]}), 9999, p2) and not p2
    assert not run({}, {"only_items": None}, [], SKIP, 9999, p2) and not p2    # no list at all
    st3 = {}
    run(st3, {"only_items": []}, [], {}, 0, p2)                               # nothing dropped = nothing eligible
    assert not run(st3, {"only_items": []}, [], {}, 9999, p2) and not p2
