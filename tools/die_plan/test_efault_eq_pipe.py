import json
import pytest
import efault_eq_pipe as X

def doc():
    def cell(buses, age):
        return {"module": "ot_dp_efault", "params": {"AGE": age, "N": len(buses)},
                "conns": {"clk": [{"net": "clk"}], "rst_n": [{"net": "rst_n"}], "eq": [{"epoch": b} for b in buses]}}
    return {"types": {"kv3_pv_v1": {"cells": {"u_efault": cell(["a", "ctl_dcfg", "ctl_cmd", "ctl_req_t", "ctl_req_valid"], 13)}},
                      "kv3_pv_v2": {"cells": {"u_efault": cell(["a", "ctl_cmd"], 4)}},
                      "kv3_hg": {"cells": {"u_efault": cell(["x"], 4)}}}}

D = {"ctl_dcfg": 1, "ctl_cmd": 1, "ctl_req_t": 1, "ctl_req_valid": 2}

def test_vector_packs_nibbles_lsb_first():
    lit, d = X.eq_vector(doc()["types"]["kv3_pv_v1"]["cells"]["u_efault"]["conns"]["eq"], D)
    assert d == [0, 1, 1, 1, 2] and lit == "20'h21110"

def test_default_off_changes_nothing():
    d, rows = X.apply(doc(), {})
    assert d == doc() and rows == []

def test_rows_and_untouched_cells():
    d, rows = X.apply(doc(), D)
    assert [r["pointer"] for r in rows] == ["/types/kv3_pv_v1/cells/u_efault/params/EQ_PIPE_V",
                                           "/types/kv3_pv_v2/cells/u_efault/params/EQ_PIPE_V"]
    assert rows[0]["old"] is None and rows[0]["new"] == "20'h21110" and rows[1]["new"] == "8'h10"
    assert "EQ_PIPE_V" not in d["types"]["kv3_hg"]["cells"]["u_efault"]["params"]
    assert d["types"]["kv3_pv_v1"]["cells"]["u_efault"]["params"]["AGE"] == 13      # AGE unchanged: the cell adds the depth itself
    assert d["types"]["kv3_pv_v1"]["cells"]["u_efault"]["conns"] == doc()["types"]["kv3_pv_v1"]["cells"]["u_efault"]["conns"]

def test_idempotent():
    d, _ = X.apply(doc(), D)
    d2, rows = X.apply(d, D)
    assert d2 == d and rows == []

def test_types_filter_and_errors():
    d, rows = X.apply(doc(), D, types={"kv3_pv_v1"})
    assert len(rows) == 1
    with pytest.raises(ValueError):
        X.apply(doc(), {"nope": 1})
    with pytest.raises(ValueError):
        X.apply(doc(), {"ctl_cmd": 16})

def test_cell_interface_accepts_the_literal():
    """the binder sizes the eq port from N with the literal param present (bind_plancells.width path)"""
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "tools"))
    import die_port_bind as D
    f = root / "rtl/lib/ot_dp_efault.sv"
    m = {x.name: x for x in D.parse_modules(f.read_text(errors="replace"), str(f))}["ot_dp_efault"]
    lit, _ = X.eq_vector([{"epoch": b} for b in ("a", "ctl_cmd")], D_ := {"ctl_cmd": 1})
    assert m.width("eq", m.env({"N": "2", "AGE": "4", "EQ_PIPE_V": lit})) == 2
