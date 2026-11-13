"""DIE-S81-89 11-13: lower_gu RT_LAT follows the dsdv_gunit_l1f_bf form of record (recipe defines)."""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
ENV_AT_IMPORT = os.environ.get('OT_GUNIT_BF_DEFINES')
import lower_gu as L  # noqa: E402


def test_delta_per_form():
    assert L.rt_form_delta(()) == 0                                              # gf2
    assert L.rt_form_delta(('OT_GUNIT_BF_M1REG',)) == 1                          # gf3
    assert L.rt_form_delta(('OT_GUNIT_BF_M1REG', 'OT_GUNIT_BF_C1REG')) == 2      # gf4
    assert L.rt_form_delta(('OT_S81_GUNIT_NAT32',)) == 0                         # not a bf define


def test_unknown_bf_define_fails_closed():
    with pytest.raises(ValueError, match='RT_FORM_DELTAS'):
        L.rt_form_delta(('OT_GUNIT_BF_M1REG', 'OT_GUNIT_BF_NEWFORM'))


def test_defines_from_recipe_and_env(tmp_path, monkeypatch):
    r = tmp_path / 'recipes.json'
    r.write_text(json.dumps({L.BF_CORE: {'defines': ['OT_GUNIT_BF_C1REG', 'OT_GUNIT_BF_M1REG']}}))
    monkeypatch.delenv(L.BF_DEFINES_ENV, raising=False)
    assert L.bf_defines(r) == ('OT_GUNIT_BF_C1REG', 'OT_GUNIT_BF_M1REG')
    monkeypatch.setenv(L.BF_DEFINES_ENV, '')
    assert L.bf_defines(r) == ()
    monkeypatch.setenv(L.BF_DEFINES_ENV, 'OT_GUNIT_BF_M1REG')
    assert L.bf_defines(r) == ('OT_GUNIT_BF_M1REG',)


def test_module_constants_follow_the_bf_form():
    defs = L.bf_defines() if ENV_AT_IMPORT is None else tuple(sorted(d for d in ENV_AT_IMPORT.replace(',', ' ').split()))
    d = L.rt_form_delta(defs)
    assert (L.RT_LAT_N, L.RT_LAT_S) == (L.RT_LAT_BASE_N + d, L.RT_LAT_BASE_S + d)
