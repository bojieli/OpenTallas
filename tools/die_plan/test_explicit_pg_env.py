"""Captured explicit PG intent must survive ordinary RFLOW=0 kit generation."""
import copy
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys
import schema
from test_g2 import PAIR

KEYS = ("OT_PG_TRACK_TRUTH", "OT_PG_TRACK_TRUTH_WIDE_SPACING", "OT_PG_CELL_KEEPOUT")


@pytest.mark.parametrize("captured", [
    {"OT_PG_TRACK_TRUTH": "1"},  # NF15 hd_st_n3_turn captured env
    {"OT_PG_TRACK_TRUTH": "1", "OT_PG_TRACK_TRUTH_WIDE_SPACING": "1",
     "OT_PG_CELL_KEEPOUT": "0"},  # NF15 hd_spn_end captured env
    {},  # no opt-in: preserve ordinary-type default
])
def test_captured_explicit_pg_flags_reach_generated_noncons_rflow0_config(tmp_path, monkeypatch, captured):
    # This is the same generator profile as the two production-shape NF15 GEN
    # outputs. A minimal type is enough to exercise config export, without P&R.
    for key in KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OT_RFLOW", "0")
    monkeypatch.setenv("OT_CONS_KIT", "0")
    monkeypatch.setenv("OT_TT_SETUP_REPAIR", "both")
    monkeypatch.setenv("OT_PGCAP", "1")
    for key, value in captured.items():
        monkeypatch.setenv(key, value)
    gen_phys.write_type_kit(schema.Plan(copy.deepcopy(PAIR)), "fa", str(tmp_path), [])
    config = (tmp_path / "fa/config.mk").read_text()
    exports = dict(re.findall(r"^export\s+(\w+)\s*=\s*(.*?)\s*$", config, re.M))
    assert exports["OT_PGCAP"] == "1" and exports["OT_TT_SETUP_REPAIR"] == "both"
    assert {key: exports[key] for key in KEYS if key in exports} == captured
