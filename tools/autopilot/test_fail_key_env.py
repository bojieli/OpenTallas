import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW


def cfg(env):
    return {"dies": {"s": {"src_sha": "a", "plan_sha": "p", "item_env": {"t37": env}}}}


def test_an_item_env_change_releases_the_fail_key_but_only_for_new_style_keys():
    c = cfg({"OT_GPL_HPWL_RATIO": "1.3"})
    parts = KW.kit_digest_parts(c, "s", {"item": "t37", "block_sha": "b"})
    assert parts["env"]
    st = {"fail_keys": {"s|t37": {"key": "k", "cls": "FLOW", "stage": "place", "why": "PLACE-HPWL 1.40 x > limit 1.3", "n": 1, "parts": parts}}}
    assert KW.fail_key_gate(c, st, "s", "t37", "b")[0] is True                      # same inputs: still blocked
    c2 = cfg({"OT_GPL_HPWL_RATIO": "1.5"})                                          # the HPWL fix lands in item_env
    blocked, why, changed = KW.fail_key_gate(c2, st, "s", "t37", "b")
    assert blocked is False and "env" in changed
    old = {k: v for k, v in parts.items() if k != "env"}                            # a key stored before the env part existed is not released by its absence
    st["fail_keys"]["s|t37"]["parts"] = old
    assert KW.fail_key_gate(c2, st, "s", "t37", "b")[0] is True
