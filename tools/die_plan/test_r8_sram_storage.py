import pytest
import r8
import schema
from test_r8_strap_pads import _binder


def test_storage_default_optin_and_depth_guard():
    assert r8.strap_pad_storage({}, 'u', 'x', 62) == 'flop'
    spec = {'r8_strap_pad_storage': {'u.x': 'sram32'}}
    assert r8.strap_pad_storage(spec, 'u', 'x', 24) == 'sram32'
    assert r8.strap_pad_storage(spec, 'u', 'other', 62) == 'flop'
    assert r8.strap_pad_storage(spec, 'u', 'x', 32) == 'sram32'
    for n in [-1, 33, 63]:
        with pytest.raises(ValueError, match='32 words'):
            r8.strap_pad_storage(spec, 'u', 'x', n)
    with pytest.raises(ValueError):
        r8.strap_pad_storage({'r8_strap_pad_storage': {'u.x': 'typo'}}, 'u', 'x', 24)


def test_binder_site_storage_is_explicit_and_hardware_bounded():
    b = _binder({'a': [2, 0, 0], 'b': [26, 0, 0]})
    b.types = {'T': {'r8_strap_pad_max': 63, 'r8_strap_pad_storage': {'u.x': 'sram32'}}}
    b.r8_strap_sites({'T': ['a', 'b']})
    site = next(iter(b.r8_sites['T'].values()))
    assert not b.errors
    assert (site['base'], site['span'], site['storage']) == (2, 24, 'sram32')
    assert site['counts'] == {'a': 0, 'b': 24}
    default = _binder({'a': [2, 0, 0], 'b': [26, 0, 0]})
    default.types = {'T': {'r8_strap_pad_max': 63}}
    default.r8_strap_sites({'T': ['a', 'b']})
    assert 'storage' not in next(iter(default.r8_sites['T'].values()))
    over = _binder({'a': [0, 0, 0], 'b': [63, 0, 0]})
    over.types = b.types
    over.r8_strap_sites({'T': ['a', 'b']})
    assert not over.r8_sites and any('32 words' in e for e in over.errors)


def test_storage_schema_accepts_exact_leaf_port_only():
    import jsonschema
    field = schema.SCHEMA['properties']['partition_types']['additionalProperties']['properties']['r8_strap_pad_storage']
    jsonschema.validate({'hsl3.fi': 'sram32'}, field)
    for value in [{'hsl3.fi': 'flop'}, {'hsl3': 'sram32'}, ['sram32']]:
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(value, field)


def test_sram_parser_shape_and_default_legacy_compatibility():
    import r8_strap_lec as L
    import r8_sram_lec as S
    text = ('module m (\n    input wire [4:0] strap_r8pad_hsl3_fi // parent-tied R8 pad-count strap\n);\n'
            '    ot_dp_dly_cnt_sram #(.W(291), .DMAX(24), .CW(5), .BASE(0)) u_bank '
            '(.clk(clk), .strap_cnt(strap_r8pad_hsl3_fi), .d(x), .q(q));\nendmodule\n')
    bank = L.banks_of(text)[0]
    assert S.shape_ok(bank) and L.structure_ok(text)
    assert not L.structure_ok(text.replace('.BASE(0)', '.BASE(2)'))
    assert not L.structure_ok(text.replace('[4:0]', '[3:0]'))
    assert not S.shape_ok(dict(bank, DMAX=63, CW=6))
    assert not S.shape_ok(dict(bank, W=292))
    h = L.harness('T', [bank], {bank['site']:24}, {bank['site']:24}, 'v')
    assert '.BASE(0)' in h and 'ot_dp_dly_cnt_sram' in h and "5'd24" in h
    nominal = S.bench_text([(bank, 0), (bank, 24)])
    mutant = S.bench_text([(bank, 0), (bank, 24)], True)
    assert "strap_cnt(5'd0)" in nominal and "strap_cnt(5'd1)" in mutant
    assert 'reg [290:0]' in nominal and 'warm_reset' in nominal
    assert S.digest(S.ROOT / S.MODULE) == S.MODULE_SHA
    assert S.digest(S.ROOT / S.MACRO) == S.MACRO_SHA


def test_selected_tie_mismatch_fails_before_native_tools(tmp_path):
    import r8_sram_lec as S
    bank = dict(module='ot_dp_dly_cnt_sram', W=291, BASE=0, DMAX=24, CW=5, site='strap_r8pad_hsl3_fi')
    r = S.qualify('T', [bank], [{'gold': {bank['site']:24}, 'ties': {bank['site']:19}}], tmp_path)
    assert r['verdict'] == 'FAIL' and not r['rows']
    assert 'tie differs' in r['reason']
