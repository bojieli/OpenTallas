"""KW-FIX-24 11-06 (COORD 19:2x stale-source class): gen hosts with an incomplete src/plan copy are dropped"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K


class FakeAP:
    HUB_NAME = "intel2"
    def __init__(self):
        self.logs = []
    def sh(self, argv, timeout=0):
        return 0, "", ""
    def log(self, m):
        self.logs.append(m)


def cfg():
    return {"dies": {"qwen_kvsys": {"gen_host": "epyc5", "gen_hosts": ["epyc5", "intel1", "intel2"], "event": "e",
                                    "src": "/s/src", "plan": "/p/plan_of_record/plan_c.json",
                                    "work_root": "/srv/opentallas-scratch3/claude/kw/runs"}}}


def fake(table):
    def run(h, cmd):
        if h not in table:
            raise OSError("unreachable")
        src, plan, miss = table[h]
        o = f"T /s/src {src}\nT /p/plan_of_record {plan}\n" + "".join(f"M {m}\n" for m in miss)
        return 0, o
    return run


def test_pruned_copy_dropped_and_logged():
    # KW-FIX-45 11-12 (COORD): the REQUIRED list decides; a low file count alone no longer drops a host (extra files on the
    # other host must not disqualify it); cfg src_count_check restores the old comparison with the largest copy
    c = cfg()
    bad = K.src_incomplete(FakeAP(), c, run=fake({"epyc5": (4000, 158, []), "intel1": (2600, 158,
                                                  ["/s/src/tools/die_plan/bind.py"]), "intel2": (4000, 2, [])}))
    assert set(bad) == {"intel1"}
    assert "bind.py missing" in bad["intel1"]["qwen_kvsys"]
    c["_src_incomplete"] = bad
    assert K.gen_hosts(c, "qwen_kvsys") == ["epyc5", "intel2"]
    c2 = cfg(); c2["src_count_check"] = True
    bad2 = K.src_incomplete(FakeAP(), c2, run=fake({"epyc5": (4000, 158, []), "intel2": (4000, 2, [])}))
    assert "2/158" in bad2["intel2"]["qwen_kvsys"]


def test_unreachable_never_dropped_and_whole_copies_kept():
    c = cfg()
    bad = K.src_incomplete(FakeAP(), c, run=fake({"epyc5": (4000, 158, []), "intel2": (3990, 158, [])}))
    assert bad == {}
    c["_src_incomplete"] = bad
    assert K.gen_hosts(c, "qwen_kvsys") == ["epyc5", "intel1", "intel2"]


def test_all_incomplete_stops_die_with_reason():
    c = cfg()
    c["_src_incomplete"] = {h: {"qwen_kvsys": "x"} for h in ("epyc5", "intel1", "intel2")}
    why = K.work_root_problem(c, "qwen_kvsys", hub_isdir=lambda p: True)
    assert why and "SRC-INCOMPLETE" in why


def test_opt_out():
    c = cfg(); c["src_probe"] = False
    assert K.src_incomplete(FakeAP(), c, run=fake({"epyc5": (1, 1, ["/x"])})) == {}


def test_bind_sources_required(tmp_path):
    b = tmp_path / "bind"; b.mkdir()
    (b / "bind.f").write_text("/x/src/rtl/a.sv\n/x/src/rtl/b.sv\n")
    c = cfg(); c["dies"]["qwen_kvsys"]["kit_rtl"] = {"mode": "bind", "bind_out": str(b), "asbuilt": "/x/asb.json"}
    trees, files = K.src_inputs(c, "qwen_kvsys")
    assert {"/x/src/rtl/a.sv", "/x/src/rtl/b.sv", "/x/asb.json"} <= set(files)
    bad = K.src_incomplete(FakeAP(), c, run=fake({"epyc5": (4000, 158, []), "intel2": (4000, 158, ["/x/src/rtl/b.sv"]),
                                                  "intel1": (4000, 158, [])}))
    assert set(bad) == {"intel2"} and "/x/src/rtl/b.sv missing" in bad["intel2"]["qwen_kvsys"]
