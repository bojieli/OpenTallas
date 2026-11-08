"""Physical-wrapper parameters must be bound and consumed separately from leaves."""
import copy
from types import SimpleNamespace
import pytest
import kit_macro_rtl as M
import kit_core_clocks as K

NATIVE = '''module T(input wire clk, input wire d);
    qfd_tile_nl_rp2_romleaf_rr u_u_t_3_0 (
        .ck(clk),
        .ck_u(clk),
        .d(d)
    );
endmodule
'''


def context():
    core = dict(inst='u_t30', module='qfd_tile_nl_a0c', params={'IDLE_UCK': 1}, params_scope=M.SCOPE)
    typ = dict(hard_cores=[core], contents=[dict(inst='u_t30', parent_id_leaf='u_t_3_0')])
    ctx = SimpleNamespace(plan=dict(partition_types={'T': typ}, partitions=[dict(name='P', type='T')]),
                          members={'P': [0]}, F=SimpleNamespace(cells=[SimpleNamespace(
                              module='qfd_tile_nl_rp2_romleaf_rr', path='root.u_t_3_0')]),
                          rel_of=lambda ci: 'u_t_3_0')
    return ctx, core, typ


def apply(ctx, core, typ, rows=None, bound=None, swaps=None):
    original, converted = K.swap_native_cores(NATIVE, [core])
    return M.apply(original if bound is None else bound, 'T', typ, ctx.plan['partitions'],
                   [M.obligation(ctx, 'P', core)] if rows is None else rows,
                   converted if swaps is None else swaps, lambda rel: 'u_' + rel)


def test_physical_scope_keeps_native_leaf_and_requires_explicit_identity():
    ctx, core, typ = context()
    row = M.obligation(ctx, 'P', core)
    assert row['leaf'] == 'root.u_t_3_0'
    assert row['native_module'] == 'qfd_tile_nl_rp2_romleaf_rr'
    assert row['params'] == {'IDLE_UCK': 1}
    assert M.validate(ctx, [row]) == [row]
    out, receipt = apply(ctx, core, typ)
    assert 'qfd_tile_nl_a0c #(.IDLE_UCK(1)) u_t30 (' in out
    assert '.ck(clk)' in out and '.d(d)' in out
    assert receipt[0]['cycles_changed'] == 0
    assert receipt[0]['source_bind_changed'] is False
    assert 'qfd_tile_nl_rp2_romleaf_rr u_u_t_3_0' in NATIVE


def test_default_bound_leaf_behavior_is_unchanged():
    ctx, core, typ = context()
    core.pop('params_scope')
    assert M.spec(core) is None
    assert M.validate(ctx, []) == []
    converted, swaps = K.swap_native_cores(NATIVE, [core])
    out, receipt = apply(ctx, core, typ, rows=[], bound=converted, swaps=swaps)
    assert out == converted and receipt == []


@pytest.mark.parametrize('change,match', [
    (lambda c,t,x: c.update(module='arbitrary_wrapper'), 'no typed wrapper contract'),
    (lambda c,t,x: c.update(params={'UNKNOWN': 1}), 'unsupported'),
    (lambda c,t,x: c.update(params={'IDLE_UCK': '1'}), 'unsupported'),
    (lambda c,t,x: c.update(params={'IDLE_UCK': 2}), 'unsupported'),
    (lambda c,t,x: t['contents'][0].pop('parent_id_leaf'), 'parent_id_leaf'),
    (lambda c,t,x: x.F.cells[0].__setattr__('module', 'wrong_body'), 'native module'),
    (lambda c,t,x: x.members.update(P=[0, 0]), 'binds 2 leaves'),
])
def test_bad_typed_binding_fails_closed(change, match):
    ctx, core, typ = context()
    change(core, typ, ctx)
    with pytest.raises(ValueError, match=match):
        M.obligation(ctx, 'P', core)


def test_missing_or_duplicate_obligation_cannot_pass_bind_or_kit():
    ctx, core, typ = context()
    row = M.obligation(ctx, 'P', core)
    for rows in ([], [row, row]):
        with pytest.raises(ValueError, match='obligation'):
            M.validate(ctx, rows)
        with pytest.raises(ValueError, match='obligation'):
            apply(ctx, core, typ, rows=rows)


@pytest.mark.parametrize('field,value', [('params', {'IDLE_UCK': 0}), ('module', 'wrong'),
                                        ('native_module', 'wrong'), ('native_rel', 'wrong')])
def test_stale_obligation_cannot_select_a_different_physical_wrapper(field, value):
    ctx, core, typ = context()
    row = M.obligation(ctx, 'P', core)
    row[field] = value
    with pytest.raises(ValueError, match='identity differs'):
        apply(ctx, core, typ, rows=[row])


def test_missing_or_wrong_native_swap_cannot_be_skipped():
    ctx, core, typ = context()
    for swaps in ([], [dict(inst='u_t30', module='qfd_tile_nl_a0c', native_module='wrong',
                           native_leaf='u_u_t_3_0', cycles_changed=0)]):
        with pytest.raises(ValueError, match='swap not proved'):
            apply(ctx, core, typ, swaps=swaps)


def test_unknown_scope_is_not_silently_treated_as_bound_leaf():
    ctx, core, typ = context()
    core['params_scope'] = 'typo'
    with pytest.raises(ValueError, match='unknown params_scope'):
        M.validate(ctx, [])



def test_sc_hook_emits_obligation_and_does_not_mutate_logical_parameters():
    import importlib.util
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / 'physical/die_plan/qwen_compute/bind/sc_hard_params.py'
    ms = importlib.util.spec_from_file_location('sc_hard_params_test', path)
    hook = importlib.util.module_from_spec(ms)
    ms.loader.exec_module(hook)
    ctx, core, typ = context()
    params, rows = hook.regen(ctx)
    assert params == {} and rows == [M.obligation(ctx, 'P', core)]
    # Dropping the explicit scope restores the real original failure, not a skip.
    core.pop('params_scope')
    with pytest.raises(ValueError, match='binds 0 leaves'):
        hook.regen(ctx)


def test_binder_rejects_physical_scope_without_an_obligation_hook():
    import bind
    ctx, core, typ = context()
    ctx.ab, ctx.errors = {}, []
    bind.Binder.regen_params(ctx)
    assert len(ctx.errors) == 1 and 'obligation' in ctx.errors[0]
    core.pop('params_scope')
    ctx.errors = []
    bind.Binder.regen_params(ctx)
    assert ctx.errors == []
