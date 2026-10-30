"""OWNER 2026-10-30 00:10 (3)(B): physical strap_* alias over a native ID port (HBM SU lane_exp0_id).

The hardened master exposes strap_lane_lane_id[10:0] (METHODOLOGY 1.8 strap_* name, sdc_lint unchanged) and wires it
to its native lane_lane_id inside its own wrapper; the plan maps the logical ID onto the alias explicitly
(hard core physical_id_alias).  Exact master + width only; the native name never becomes a physical static pin.
"""
import copy
import json
from pathlib import Path

import pytest

from tools.die_plan import check, schema, sdc_lint
from tools.die_plan.hbm_n4_lanemap import declared_lid
from tools.die_plan.parent_id_straps import (logical_id_straps, type_parent_id_straps,
                                             validate_parent_id_straps)

SU = 'ot_hbm_su_static_pgslice_lg__lane_exp0_id'
A, N, W = 'strap_lane_lane_id', 'lane_lane_id', 11
PINS = [f'{A}[{i}]' for i in range(W)]


def hc(value=16, form='straps'):
    d = dict(inst='u_su_Q1_lane_exp0', module=SU, physical_id_alias={A: N})
    if form == 'straps':
        d['straps'] = [dict(port=A, width=W, value=f"{W}'b{value:0{W}b}")]
    else:
        d['parent_id_straps'] = {A: dict(width=W, value=value)}
    return d


@pytest.mark.parametrize('form', ['straps', 'parent_id_straps'])
@pytest.mark.parametrize('value', [0, 16, 2047])
def test_exact_alias_on_exact_master_is_accepted(form, value):
    d = hc(value, form)
    assert validate_parent_id_straps(d, {A: W}, PINS, actual_module=SU) == {A: dict(width=W, value=value)}
    assert logical_id_straps(d) == {N: dict(width=W, value=value)}
    assert type_parent_id_straps({'hard_cores': [d]}) == {'u_su_Q1_lane_exp0': {A: dict(width=W, value=value)}}


def _mut(**kw):
    d = hc()
    for k, v in kw.items():
        if v is None:
            d.pop(k)
        else:
            d[k] = v
    return d


@pytest.mark.parametrize('d,kw', [
    (_mut(physical_id_alias=None), {}),                                    # alias strap without the plan mapping
    (_mut(physical_id_alias={A: 'lane_id'}), {}),                          # mapped to another native port
    (_mut(physical_id_alias={'strap_lane_id': N}), {}),                    # mapping names an unapproved alias
    (_mut(physical_id_alias={}), {}),
    (_mut(physical_id_alias=[A]), {}),
    (_mut(module='ot_hbm_su_static_pgslice_lg__lane_exp0'), {}),          # wrong (old literal-ID) master
    (_mut(module='ot_hgi_sm_xload_cl2_bdring'), {}),
    (hc(), dict(actual_module='ot_hbm_su_static_pgslice_lg__lane_exp1')),   # actual bound master differs
    (_mut(straps=[dict(port=A, width=10, value=16)]), {}),                 # inexact width
    (_mut(straps=[dict(port=A, width=W, value=2048)]), {}),
    (_mut(straps=[dict(port=A, width=W, value="10'b0000010000")]), {}),
    (_mut(parent_id_straps={N: dict(width=W, value=16)}), {}),             # native ALSO declared: one ID, one pin
    (hc(), dict(inputs={N: W})),                                           # actual input is the native name only
    (hc(), dict(pins=[f'{N}[{i}]' for i in range(W)])),                    # native-named physical pins
    (hc(), dict(pins=PINS[:-1])),
])
def test_alias_misuse_is_rejected(d, kw):
    with pytest.raises(ValueError):
        validate_parent_id_straps(d, **kw)


def test_mapping_without_alias_strap_or_on_other_ids_is_rejected():
    with pytest.raises(ValueError):    # a mapping on a plain native declaration grants nothing
        validate_parent_id_straps(dict(module=SU, physical_id_alias={A: N}, parent_id_straps={N: dict(width=W, value=0)}))
    with pytest.raises(ValueError):
        validate_parent_id_straps(dict(module='ot_hfd_coll_q2_hard_v8g__ring_ag', physical_id_alias={'strap_qid': 'qid'},
                                       parent_id_straps={'strap_qid': dict(width=2, value=2)}))


def test_plans_without_alias_are_unchanged():
    d = {'parent_id_straps': {N: dict(width=5, value=3)}}
    assert validate_parent_id_straps(d, {N: 5}) == d['parent_id_straps']
    assert logical_id_straps(d) == d['parent_id_straps']
    assert declared_lid({'parent_id_straps': {N: {'width': 5, 'value': 19}}}) == 19
    assert declared_lid({'params': {'LID': 7}}) == 7


def test_lane_identity_reads_native_through_alias():
    assert declared_lid(hc(16, 'parent_id_straps')) == 16
    assert declared_lid(hc(16, 'straps')) == 16
    assert declared_lid({**hc(16, 'straps'), 'physical_id_alias': None}) is None   # no mapping: not a lane ID


def _plan(core):
    p = json.loads((Path(schema.__file__).parent / 'examples/tiny_plan.json').read_text())
    tn = next(iter(p['partition_types']))
    h = dict(core, origin_um=[8.64, 8.64], outline_um=[17.28, 17.28],
             pins=[dict(name=n, layer='M5', xy=[0, 0]) for n in PINS])
    p['partition_types'][tn]['hard_cores'] = [h]
    return p, h


@pytest.mark.parametrize('form', ['straps', 'parent_id_straps'])
def test_schema_and_g0_accept_exact_alias_only(form):
    p, h = _plan(hc(16, form))
    assert schema.validate_structure(p) == []
    r = check.Report(completeness=True)
    check.check_taps_cores(schema.Plan(p), r)
    assert not any('physical_id_alias' in e['msg'] or 'declared physical pins' in e['msg'] for e in r.errors())
    bad = copy.deepcopy(p)
    bad['partition_types'][next(iter(p['partition_types']))]['hard_cores'][0].pop('physical_id_alias')
    assert schema.validate_structure(bad)
    bad = copy.deepcopy(p)
    bad['partition_types'][next(iter(p['partition_types']))]['hard_cores'][0]['physical_id_alias'] = {'lane_lane_id': A}
    assert schema.validate_structure(bad)
    h['pins'] = [dict(name=f'{N}[{i}]', layer='M5', xy=[0, 0]) for i in range(W)]
    r = check.Report(completeness=True)
    check.check_taps_cores(schema.Plan(p), r)
    assert any('declared physical pins' in e['msg'] for e in r.errors())


def test_formal_schema_alias_width():
    js = pytest.importorskip('jsonschema')
    item = schema._core_id_straps['items']
    js.validate({'port': A, 'width': W, 'value': "11'b00000010000"}, item)
    js.validate({'port': 'strap_hid', 'width': 2, 'value': "2'b11"}, item)
    js.validate({'port': 'strap_tile_tid', 'width': 6, 'value': "6'b011111"}, item)
    for d in [{'port': A, 'width': 2, 'value': "2'b11"}, {'port': A, 'width': W, 'value': "6'b011111"},
              {'port': 'strap_hid', 'width': W, 'value': "11'b00000010000"}]:
        with pytest.raises(js.ValidationError):
            js.validate(d, item)


def test_sdc_lint_unchanged_alias_is_a_normal_strap():
    base = dict(period_ps=833, insertion_ps=250, insertion_tol_ps=40, clock_ports=['clk'], outputs=['o'])
    sdc = ("create_clock -name clk -period 833 [get_ports clk]\n"
           f"set_false_path -from [get_ports {{{A}}}]\n")
    ok = sdc_lint.lint(sdc, inputs=[A, 'd'], straps=[A], **base)
    native = sdc_lint.lint(sdc.replace(A, N), inputs=[N, 'd'], straps=[N], **base)
    assert not any('straps' in e for e in ok)
    assert any("must be named strap_<id>" in e for e in native)


def _bind_vehicle(module, alias=True, value=16):
    from types import SimpleNamespace
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from test_bind_wavefront import emitter, plan
    raw = plan()
    d = dict(inst="u_su", module=SU, parent_id_straps={A: dict(width=W, value=value)})
    if alias:
        d["physical_id_alias"] = {A: N}
    raw["partition_types"]["src"]["contents"] = [d]
    b = emitter(raw)
    part = next(p for p in b.parts if b.parts[p]["type"] == "src")
    b.F.cells = [SimpleNamespace(path="p.u_su", ports={A: list(range(1, W + 1))}, module=module, params={})]
    b.G.dirs = {0: {A: "input"}}
    b.G.kind = ["leaf"]
    b.members[part] = [0]
    b.rel_of = lambda ci: "u_su"
    b.tparams["src"] = {("strap", "u_su", A, i): [str((value >> i) & 1)] for i in range(W)}
    b.tvals["src"] = {part: {k: v[0] for k, v in b.tparams["src"].items()}}
    b.sinks = {(0, A, i): ("strap",) for i in range(W)}
    b.collect_gaps = True
    return raw, b


def test_binder_alias_becomes_parent_tied_strap_port(tmp_path):
    raw, b = _bind_vehicle(SU)
    b.emit(tmp_path)
    assert not any("u_su" in g for g in getattr(b, "emit_gaps", []))
    (nm, d), = b.parent_id_ports["src"].items()
    assert nm.startswith("strap_") and d == dict(leaf="u_su", port=A, width=W)
    rtl = (tmp_path / "rtl" / (raw["partition_types"]["src"]["module"] + ".sv")).read_text()
    assert f"input wire [{W - 1}:0] {nm}" in rtl
    assert {v[nm]["value"] for v in b.parent_id_values.values()} == {16}


@pytest.mark.parametrize("module,alias,value", [("ot_hbm_su_static_pgslice_lg__lane_exp0", True, 16),
                                                (SU, False, 16), (SU, True, 17)])
def test_binder_alias_wrong_master_mapping_or_value_is_a_gap(tmp_path, module, alias, value):
    raw, b = _bind_vehicle(module, alias, value)
    if value == 17:            # declared 17, as-built literal 16
        part = next(iter(b.tvals["src"]))
        b.tparams["src"] = {("strap", "u_su", A, i): [str((16 >> i) & 1)] for i in range(W)}
        b.tvals["src"] = {part: {k: v[0] for k, v in b.tparams["src"].items()}}
    b.emit(tmp_path)
    assert any("u_su" in g or "physical_id_alias" in g for g in b.emit_gaps)
    assert not (tmp_path / "rtl/tiny_bound_top.sv").exists()
