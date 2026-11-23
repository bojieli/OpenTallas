"""DESIGN-REPEAT-1122 (COORD 22:3x): kv512_C relaunched 4x on the same plan / bind / env (only the rt moved), each FAIL at -1154 ps.  The second
identical design failure holds the row; a plan / bind / env change or a retry key releases it; infra failures never count."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402

REASON = ("FAIL_POSTPLACE PLACE-SETUP-STOP wns -1154.54 ps < -300 ps (TT, post-place; routing cannot close it) "
          "start=u_bound.u_s.gf_q[2]$_DFF_P_ end=u_bound.g_bank[2].u_mem; place ODB /srv/x/attempt_{a}/place/3_place.odb in {t} s")


def ip(src="3c913dbdfb23", env=None, tools="t1"):
    return {"v": 2, "noenv": "n" + tools, "env": env or {"OT_PGCAP": "1"}, "fam": {"flow": tools}, "stg": {"place": tools},
            "pc": {"block": "f870", "src": src, "overlay": "ov" + tools, "snapshot": "12af", "bind_context": "ac2f", "views": ""}}


def rec(a, parts, reason=REASON):
    return {"status": "ENQUEUED", "q_status": "FAIL", "q_stage": "place", "q_class": "PLAN", "attempt": a,
            "q_reason": reason.format(a=a, t=300 + a), "input_parts": parts, "block_sha": "f870"}


def run(monkeypatch, now_parts, history):
    monkeypatch.setattr(KW, "input_parts", lambda cfg, die, item, b=None: now_parts)
    r = {}
    out = ""
    for a, parts in history:                      # each attempt overwrites the row record, as the wave does; design_fails carries over
        nr = rec(a, parts)
        nr["design_fails"] = r.get("design_fails", {})
        r = nr
        out = KW.design_repeat_hold({}, "s81", {"item": "dsdv_slice_kv512_C__t1"}, r)
    return out, r


def test_second_identical_design_fail_holds_even_when_tools_moved(monkeypatch):
    out, _ = run(monkeypatch, ip(tools="t3"), [(1, ip(tools="t1"))])
    assert out == ""                                                     # one failure: the relaunch (e.g. on a tool fix) is allowed
    out, r = run(monkeypatch, ip(tools="t3"), [(1, ip(tools="t1")), (2, ip(tools="t2"))])
    assert out.startswith("DESIGN-REPEAT") and "-1154.54" in out and "dsdv_slice_kv512_C__t1@2" in out
    assert len(r["design_fails"]) == 2


def test_plan_or_env_change_releases(monkeypatch):
    hist = [(1, ip()), (2, ip())]
    assert run(monkeypatch, ip(src="newsrc"), hist)[0] == ""
    assert run(monkeypatch, ip(env={"OT_PGCAP": "0"}), hist)[0] == ""
    assert run(monkeypatch, ip(), hist)[0].startswith("DESIGN-REPEAT")


def test_different_failure_or_infra_does_not_count(monkeypatch):
    monkeypatch.setattr(KW, "input_parts", lambda cfg, die, item, b=None: ip())
    r1 = rec(1, ip())
    KW.design_repeat_hold({}, "s81", {"item": "x"}, r1)
    r2 = rec(2, ip(), reason="FAIL_POSTPLACE PLACE-SETUP-STOP wns -800.00 ps < -300 ps")
    r2["design_fails"] = r1["design_fails"]
    assert KW.design_repeat_hold({}, "s81", {"item": "x"}, r2) == ""
    r3 = rec(3, ip(), reason="make: *** [x] Error 247")
    r3["design_fails"] = copy.deepcopy(r2["design_fails"])
    assert KW.design_repeat_hold({}, "s81", {"item": "x"}, r3) == "" and "3" not in r3["design_fails"]


def test_signature_ignores_paths_times_attempts():
    a, b = rec(1, ip()), rec(4, ip())
    assert KW.fail_signature(a) == KW.fail_signature(b) and "-1154.54" in KW.fail_signature(a)
