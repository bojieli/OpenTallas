"""S81-COL-CLK-1116 Spec 0: clock.core_pin_lead_ps (ROM clock pin lead in core_latency rows) and clock.tap_core_src."""
import copy
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import core_clock_contract as CC
import gen_phys as G
import schema as S

LEAD = [{"module_re": "ot_rom_.*", "pin": "clk", "lead_ps": 255}]


def _p(clock=None):
    ck = {"taps": []}
    ck.update(clock or {})
    return SimpleNamespace(clock={"insertion_ps": 450, "insertion_tol_ps": 20, "insertion_ff_ps": 364.5},
                           types={"T": {"hard_cores": [], "clock": ck}})


def _legacy_rows():
    return [dict(inst="u_bound.u_u_c10_0", module="ot_rom_4096x72_m8", pin="clk", rise_ps=0.0, fall_ps=0.0, tap="grid",
                 basis="legacy_etm_max_bound"),
            dict(inst="u_bound.u_u_s10", module="dsfd_s", pin="clk[0]", rise_ps=271.22, fall_ps=290.0, tap="grid",
                 basis="legacy_etm_max_bound"),
            dict(inst="u_bound.u_u_c11_0", module="ot_rom_4096x72_m8", pin="ck", rise_ps=5.0, fall_ps=5.0, tap="grid")]


def test_absent_key_is_identity():
    rows = _legacy_rows()
    assert G.apply_core_pin_lead(_p(), "T", rows) is rows


def test_lead_applies_to_matching_module_and_pin_only():
    rows = _legacy_rows()
    before = copy.deepcopy(rows)
    out = G.apply_core_pin_lead(_p({"core_pin_lead_ps": LEAD}), "T", rows)
    assert rows == before                                   # inputs not mutated
    assert out[0]["rise_ps"] == 255 and out[0]["fall_ps"] == 255 and out[0]["basis"] == "declared_lead"
    assert out[1] == before[1] and out[2] == before[2]      # other module / other pin untouched


def test_mean_contract_corners_ff_scaled():
    row = dict(inst="u_bound.u_u_c10_0", module="ot_rom_4096x72_m8", pin="clk", rise_ps=100.0, fall_ps=100.0, tap="grid",
               corners={"tt": {"mean_ps": 100.0}, "ff": {"mean_ps": 81.0}}, basis="parent_budget")
    out = G.apply_core_pin_lead(_p({"core_pin_lead_ps": LEAD}), "T", [row])[0]
    assert out["rise_ps"] == 355 and out["corners"]["tt"]["mean_ps"] == 355
    assert out["corners"]["ff"]["mean_ps"] == pytest.approx(81.0 + 255 * 364.5 / 450, abs=0.01)
    assert out["basis"] == "parent_budget" and out["lead_basis"] == "declared_lead"
    assert row["corners"]["tt"]["mean_ps"] == 100.0


def test_core_latency_files_writes_lead_rows():
    p = _p({"core_pin_lead_ps": LEAD})
    p.types["T"]["hard_cores"] = [dict(inst="u_bound.u_u_c10_0", module="ot_rom_4096x72_m8")]
    import cores as C
    with tempfile.TemporaryDirectory() as d, patch.object(C, "latency_table", return_value=_legacy_rows()[:1]), \
            patch.object(G, "core_tap_rows", return_value=[]):
        G.core_latency_files(p, "T", Path(d))
        assert (Path(d) / "core_latency.txt").read_text().splitlines()[1] == "u_bound.u_u_c10_0 clk 255 grid"
        assert json.loads((Path(d) / "core_latency.json").read_text())["rows"][0]["lead_ps"] == 255


def test_schema_keys():
    ck = S.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]["clock"]["properties"]
    assert ck["tap_core_src"] == {"enum": ["tree"]}
    it = ck["core_pin_lead_ps"]["items"]
    assert set(it["required"]) == {"module_re", "pin", "lead_ps"} and it["additionalProperties"] is False
    on_disk = json.loads((Path(G.__file__).with_name("die_plan.schema.json")).read_text())
    assert on_disk == json.loads(json.dumps(S.SCHEMA))


def test_etap_src_export_is_gated_on_etap_and_tree():
    src = Path(G.__file__).read_text()
    i = src.index('cfg.append("export OT_TAP_CORE_ETAP = 1")')
    blk = src[i:i + 400]
    assert 'tap_core_src") == "tree"' in blk and 'cfg.append("export OT_TAP_CORE_SRC = tree")' in blk


def test_inst_re_negative_lag_hits_named_instance_only():
    # USKEW-1 (S81-GEOM-OPUS 11-18): late capture on col_h9_r2 bank bn11 only, by plan or physical name
    rows = [dict(inst='u_bound.u_u_bn11', logical_inst='u_r2.u_bn11', module='dsfd_qbank_N', pin='ck[0]', rise_ps=268.66,
                 tap='grid'),
            dict(inst='u_bound.u_u_bn10', logical_inst='u_r2.u_bn10', module='dsfd_qbank_N', pin='ck[0]', rise_ps=268.66,
                 tap='grid')]
    spec = [{'module_re': 'dsfd_qbank_N', 'pin': 'ck[0]', 'lead_ps': -45, 'inst_re': r'u_r2\.u_bn1[12]'}]
    out = G.apply_core_pin_lead(_p({'core_pin_lead_ps': spec}), 'T', rows)
    assert out[0]['rise_ps'] == pytest.approx(223.66) and out[1] == rows[1]


def test_schema_accepts_lag_rejects_zero():
    import jsonschema
    sch = S.SCHEMA['properties']['partition_types']['additionalProperties']['properties']['clock']['properties']['core_pin_lead_ps']
    jsonschema.validate([{'module_re': 'm', 'pin': 'ck[0]', 'lead_ps': -45, 'inst_re': 'u_x'}], sch)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate([{'module_re': 'm', 'pin': 'ck[0]', 'lead_ps': 0}], sch)
