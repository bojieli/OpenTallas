"""B1 (FLOW-OPS-R2, FABLE-FLOW-0230): EMIT name checks before the bind -- EMITNAME (clock-landing instance names) and RELAYSINK
(relay_depth rows vs the elaborated leaves)."""
import json
import sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import bind_rowcheck as RC  # noqa: E402
import plan_gate_pre as G  # noqa: E402

BIND = 'import re\n\ndef sv_id(s):\n    s = re.sub(r"[^A-Za-z0-9_]", "_", s)\n    s = re.sub(r"_+", "_", s).strip("_")\n    return s if s and not s[0].isdigit() else "n" + s\n'
CL_OLD = ('import re\n\ndef ident(s):\n    return re.sub(r"[^A-Za-z0-9_]", "_", s)\n\n\nclass L:\n    def f(self, pn, p, modules, text):\n'
          '            pat = re.compile(r"(?m)^(    " + re.escape(modules[p["type"]]) +\n'
          '                             r"(?: #\\([^\\n]*\\))? " + re.escape(ident(pn)) + r" \\(\\n)(.*?)(\\n    \\);)", re.S)\n'
          '            raise LandingError(f"clock landing: expected exactly one bound instance {pn}")\n')


def tree(tmp, cl):
    d = tmp / "tools" / "die_plan"
    d.mkdir(parents=True)
    (d / "bind.py").write_text(BIND)
    (d / "clock_landings.py").write_text(cl)
    return tmp


def plan(tmp, names):
    p = tmp / "plan.json"
    p.write_text(json.dumps({"partitions": [{"name": n, "type": "t"} for n in names], "asbuilt": {"clock_landing_table": "x.json"}}))
    return str(p)


def test_emitname_old_tools_refuse_split_piece(tmp_path):
    t = tree(tmp_path, CL_OLD)
    f = G.check_emitname(str(t), plan(tmp_path, ["s_7N_C__strip_S", "s_8"]))
    assert len(f) == 1 and f[0].startswith("FAIL EMITNAME partition s_7N_C__strip_S") and "s_7N_C_strip_S" in f[0]


def test_emitname_current_tools_pass_and_collision(tmp_path):
    real = Path(__file__).resolve().parents[2]
    p = plan(tmp_path, ["s_7N_C__strip_S", "s_8"])
    assert G.check_emitname(str(real), p) == []
    f = G.check_emitname(str(real), plan(tmp_path, ["a__b", "a_b"]))
    assert any("share the bound instance name a_b" in x for x in f)
    nolanding = tmp_path / "p2.json"
    nolanding.write_text(json.dumps({"partitions": [{"name": "a__b"}, {"name": "a_b"}]}))
    assert G.check_emitname(str(real), str(nolanding)) == []


def yjs():
    leaf = {"type": "ot_rom", "connections": {"cfg_a": [1], "q": [2]}}
    return {"modules": {"top": {"cells": {"u_col": {"type": "col"}}},
                        "col": {"cells": {"u_r1.u_e5.u_w": leaf, "u_y_rt_3": {"type": "DFF", "connections": {"D": [3], "Q": [4]}}}},
                        "ot_rom": {"attributes": {"blackbox": 1}}}}


def test_relaysink_rows():
    pl = {"partition_types": {"h9": {"relay_depth": [
        {"inst": "u_r1_u_e5_u_w", "port": "cfg_a", "side": "sink", "D": 1},
        {"inst": "u_r1.u_e5.u_w", "port": "go", "side": "sink", "D": 1},
        {"inst": "u_r1_u_e9_u_w", "port": "cfg_a", "side": "sink", "D": 1},
        {"inst": "u_bout_unit_o0", "port": "d", "side": "sink", "D": 1}]}}}
    out = RC.check_relaysink(pl, {"top": "top"}, yjs())
    fails = [x for x in out if x.startswith("FAIL")]
    assert len(fails) == 2
    assert any("u_r1.u_e5.u_w (master ot_rom) has no port go" in x for x in fails)
    assert any("u_r1_u_e9_u_w.cfg_a is no leaf" in x for x in fails)
    assert any(x.startswith("WARN RELAYSINK 1 relay_depth row(s) on bind-generated") for x in out)
    assert RC.check_relaysink({"partition_types": {"h9": {}}}, {"top": "top"}, yjs()) == []
