"""FLOW-OPS-1300 item 13 (FLEET-WATCH-R7): an idle failed / superseded wave attempt_N dir is not protected by the die work_root ANCESTOR entry; it stays refused when it is
listed itself (latest attempts of live / queued rows), holds something listed, holds a signed or unsigned-routed result, or a live process names it."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import ot_delete_guard as G
import build_protected_live as B


def tree(tmp_path):
    root = str(tmp_path).replace(str(tmp_path), "/srv/opentallas-scratch2/claude/x")  # canon form used only for the list
    return root


def mk(base, rel, files=()):
    d = os.path.join(base, rel)
    os.makedirs(d, exist_ok=True)
    for f, txt in files:
        p = os.path.join(d, f); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(txt)
    return d


def test_attempt_dirs_under_the_work_root(tmp_path, monkeypatch):
    # the guard canonicalises /srv paths; run on real dirs by mapping a fake /srv prefix onto tmp_path
    base = str(tmp_path / "srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave")
    real = lambda p: p.replace("/srv/", str(tmp_path) + "/srv/", 1)
    wr = "/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave"
    item = wr + "/s81/ev1/items/t1"
    for n in (1, 2, 3, 4):
        mk(real(item), f"attempt_{n}", [("logs/x.log", "x")])
    mk(real(item), "attempt_2", [("gen/t1/signoff.json", json.dumps({"verdict": "SIGNED"}))])
    monkeypatch.setattr(G, "canon", lambda p: p.replace(str(tmp_path), "").rstrip("/"))
    monkeypatch.setattr(G.os.path, "islink", lambda p: False)
    monkeypatch.setattr(G.os.path, "realpath", lambda p: os.path.abspath(p))
    monkeypatch.setattr(G, "attempt_signed", lambda ad: os.path.exists(real(ad) + "/gen/t1/signoff.json"))
    monkeypatch.setattr(G, "routed_unsigned_refusal", lambda t: None)
    prot = {wr, item + "/attempt_4", wr + "/s81/ev1/items/t1/attempt_3/gen/bind_of_record"}
    ref = lambda p, pt="": G.refuse(p, protected=prot, ptext=pt, current={}, allow=set())
    assert ref(item + "/attempt_1") is None                                        # idle failed attempt: only the rows container covered it
    assert ref(item + "/attempt_1/logs") is None
    assert ref(item + "/attempt_2").startswith("protected")
    assert ref(item + "/attempt_3").startswith("protected")                         # holds a listed bind of record
    assert ref(item + "/attempt_4").startswith("protected")                         # latest attempt of a live row, listed exactly
    assert ref(item) is not None and ref(wr) is not None                            # the running item dir and the container stay protected
    assert ref(item + "/attempt_1", pt="python3 x --dir " + item + "/attempt_1/gen").startswith("live process")


def test_live_attempt_paths_from_the_wave_state(tmp_path):
    st = {"items": {
        "a": {"status": "ENQUEUED", "attempt": 5, "work": "/srv/opentallas-scratch2/claude/w/runs/s81/kit-wave/s81/e/items/t1"},
        "b": {"status": "RETRY-INFRA", "attempt": 1, "kit": "epyc7:/srv/opentallas-scratch2/claude/w/runs/s81/kit-wave/s81/e/items/t2/gen/t2"},
        "c": {"status": "CANCELLED", "attempt": 3, "work": "/srv/opentallas-scratch2/claude/w/runs/s81/kit-wave/s81/e/items/t3"},
        "d": {"status": "FAIL", "attempt": 2, "work": "/srv/opentallas-scratch2/claude/w/runs/s81/kit-wave/s81/e/items/t4"}}}
    f = tmp_path / "state.json"; f.write_text(json.dumps(st))
    out = set()
    B.live_attempt_paths(str(tmp_path), out, lambda p: p, state_file=str(f))
    w = "/srv/opentallas-scratch2/claude/w/runs/s81/kit-wave/s81/e/items/"
    assert out == {w + "t1", w + "t1/attempt_5", w + "t1/attempt_4", w + "t2", w + "t2/attempt_1"}
