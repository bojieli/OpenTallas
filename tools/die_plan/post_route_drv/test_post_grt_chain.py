import importlib.util
from pathlib import Path

import pytest

s = importlib.util.spec_from_file_location('chain', Path(__file__).with_name('post_grt_chain.py'))
C = importlib.util.module_from_spec(s)
s.loader.exec_module(C)


def fixture(tmp_path):
    (tmp_path / 'grt_post_core.tcl').write_text('# generated\n' + '\n'.join(C.LEGACY_WRAPPER) + '\n')
    (tmp_path / 'post_grt_drv.tcl').write_text('# generated\n' + '\n'.join(C.LEGACY_REPAIR) + '\n')
    (tmp_path / 'grt_post.tcl').write_text('ot_vclk_bind tt\not_pg_require_bound grt_post\n')


def test_exact_legacy_repair_removed_but_gate_chain_retained(tmp_path):
    fixture(tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    assert C.stage(tmp_path)['skipped_generated_repair']
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/grt_post.tcl\n'
    assert all((tmp_path / n).read_bytes() == b for n, b in before.items())


@pytest.mark.parametrize('name,extra', [('post_grt_drv.tcl', '\nrepair_timing -setup\n'),
                                    ('grt_post_core.tcl', '\nsource /work/custom_gate.tcl\n')])
def test_unknown_repair_or_wrapper_refuses_instead_of_dropping_custom_work(tmp_path, name, extra):
    fixture(tmp_path)
    p = tmp_path / name
    p.write_text(p.read_text() + extra)
    with pytest.raises(ValueError, match='unrecognized'):
        C.stage(tmp_path)
    assert not (tmp_path / 'prd_post_grt_chain.tcl').exists()


def test_ordinary_nonrepair_custom_hook_unchanged(tmp_path):
    (tmp_path / 'grt_post_core.tcl').write_text('source /work/custom_gate.tcl\n')
    assert not C.stage(tmp_path)['skipped_generated_repair']
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/grt_post_core.tcl\n'


def test_no_core_hook_is_empty(tmp_path):
    assert not C.stage(tmp_path)['skipped_generated_repair']
    assert not (tmp_path / 'prd_post_grt_chain.tcl').read_text()


def test_final_repair_tail_skipped_with_gate_chain_retained(tmp_path):
    fixture(tmp_path)
    core = tmp_path / 'grt_post_core.tcl'
    core.write_text(core.read_text() + '\n'.join(C.FINAL_REPAIR_TAIL) + '\n')
    (tmp_path / 'core_final_repair.tcl').write_text('repair_timing -setup\n')
    rec = C.stage(tmp_path)
    assert rec['skipped_generated_repair'] and rec['skipped_final_repair']
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/grt_post.tcl\n'


def test_core_flow_bare_final_repair_tail_skipped(tmp_path):
    # the form tools/die_plan/core_flow.py writes: hooks, grt_post.tcl, then only the final repair
    fixture(tmp_path)
    core = tmp_path / 'grt_post_core.tcl'
    core.write_text(core.read_text() + 'source /work/core_final_repair.tcl\n')
    (tmp_path / 'core_final_repair.tcl').write_text('repair_timing -setup\n')
    rec = C.stage(tmp_path)
    assert rec['skipped_generated_repair'] and rec['skipped_final_repair']
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/grt_post.tcl\n'


def test_bare_final_repair_tail_without_its_file_refuses(tmp_path):
    fixture(tmp_path)
    core = tmp_path / 'grt_post_core.tcl'
    core.write_text(core.read_text() + 'source /work/core_final_repair.tcl\n')
    with pytest.raises(ValueError, match='unrecognized'):
        C.stage(tmp_path)


@pytest.mark.parametrize('tail', [['write_db /work/pre_final_state.odb', 'source /work/core_final_repair.tcl'],
                                  ['source /work/core_final_repair.tcl', 'source /work/custom_gate.tcl'],
                                  ['write_db /work/pre_final_state.odb', 'source /work/custom_gate.tcl']])
def test_partial_or_foreign_final_tail_refuses(tmp_path, tail):
    fixture(tmp_path)
    core = tmp_path / 'grt_post_core.tcl'
    core.write_text(core.read_text() + '\n'.join(tail) + '\n')
    (tmp_path / 'core_final_repair.tcl').write_text('repair_timing -setup\n')
    with pytest.raises(ValueError, match='unrecognized'):
        C.stage(tmp_path)


def test_variant_a_legacy_repair_without_hold_line_skipped(tmp_path):
    fixture(tmp_path)
    (tmp_path / 'post_grt_drv.tcl').write_text('# variant A\n' + '\n'.join(C.LEGACY_REPAIRS[1]) + '\n')
    assert 'repair_timing -hold -hold_margin 5 -max_buffer_percent 100' not in C.LEGACY_REPAIRS[1]
    assert C.stage(tmp_path)['skipped_generated_repair']
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/grt_post.tcl\n'


def test_variant_a_with_extra_setup_repair_still_refuses(tmp_path):
    fixture(tmp_path)
    (tmp_path / 'post_grt_drv.tcl').write_text('\n'.join(C.LEGACY_REPAIRS[1] + ['repair_timing -setup']) + '\n')
    with pytest.raises(ValueError, match='unrecognized'):
        C.stage(tmp_path)


def test_two_mode_generated_repair_body_skipped_alike(tmp_path):
    """DIE-QC-66 11-03: the OT_HOLD_MM form of the generated body (QC A0 NL b3h kit) is the same repair class."""
    fixture(tmp_path)
    (tmp_path / 'post_grt_drv.tcl').write_text('# generated\n' + '\n'.join(
        ('  ' + c if c.startswith(('ot_', 'repair_timing')) else c) for c in C.LEGACY_REPAIR_MM) + '\n')
    assert C.stage(tmp_path)['skipped_generated_repair']
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/grt_post.tcl\n'
    # one changed knob in the MM body -> refuse
    p = tmp_path / 'post_grt_drv.tcl'
    p.write_text(p.read_text().replace('-hold_margin 5 -repair_tns 100', '-hold_margin 5 -repair_tns 50'))
    (tmp_path / 'prd_post_grt_chain.tcl').unlink()
    with pytest.raises(ValueError, match='unrecognized'):
        C.stage(tmp_path)


def test_core_flow_form_without_post_grt_drv_skips_final_repair_only(tmp_path):
    """DIE-KV-67/CL 11-04: native KV core kits: no post_grt_drv.tcl; hooks + gate chain stay, final repair goes."""
    (tmp_path / 'grt_post_core.tcl').write_text('# generated\nsource /work/kit_hook.tcl\nsource /work/grt_post.tcl\n'
                                                'source /work/core_final_repair.tcl\n')
    (tmp_path / 'grt_post.tcl').write_text('ot_vclk_bind tt\n')
    (tmp_path / 'core_final_repair.tcl').write_text('repair_timing -setup\n')
    rec = C.stage(tmp_path)
    assert rec['skipped_final_repair'] and not rec['skipped_generated_repair']
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/kit_hook.tcl\nsource /work/grt_post.tcl\n'


def test_core_flow_form_without_gate_chain_or_repair_file_unchanged(tmp_path):
    (tmp_path / 'grt_post_core.tcl').write_text('source /work/core_final_repair.tcl\n')
    (tmp_path / 'core_final_repair.tcl').write_text('repair_timing -setup\n')
    assert 'skipped_final_repair' not in C.stage(tmp_path)
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/grt_post_core.tcl\n'
    (tmp_path / 'grt_post_core.tcl').write_text('source /work/grt_post.tcl\nsource /work/core_final_repair.tcl\n')
    (tmp_path / 'core_final_repair.tcl').unlink()
    assert 'skipped_final_repair' not in C.stage(tmp_path)


# ECO-CLOCK-HOOK (KW-FIX-44 11-09): the post-GRT chain of a post-route ECO never re-runs a kit clock-tree editor
def core_flow_form(tmp_path, hooks):
    (tmp_path / 'grt_post.tcl').write_text('ot_vclk_bind tt\n')
    (tmp_path / 'core_final_repair.tcl').write_text('repair_timing -setup\n')
    (tmp_path / 'grt_post_core.tcl').write_text(
        '# GENERATED by tools/die_plan/core_flow.py\n' + ''.join(f'source /work/{h}\n' for h in hooks[0])
        + 'source /work/grt_post.tcl\n' + ''.join(f'source /work/{h}\n' for h in hooks[1])
        + 'source /work/core_final_repair.tcl\n')


def test_tx_vS_form_subtree_balance_skipped_with_final_repair(tmp_path):
    # epyc7 die-s81-85/txvSeco/i1: grt_post.tcl, subtree_balance.tcl, core_final_repair.tcl
    core_flow_form(tmp_path, ([], ['subtree_balance.tcl']))
    rec = C.stage(tmp_path)
    assert rec['skipped_final_repair'] and rec['skipped_clock_hooks'] == ['subtree_balance.tcl']
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/grt_post.tcl\n'


@pytest.mark.parametrize('hook', sorted(C.CLOCK_EDIT_HOOKS))
def test_clock_editing_hook_mutant_never_reaches_the_chain(tmp_path, hook):
    # mutant: a kit adds any clock-tree editor before or after the gate chain; a data hook beside it is kept
    core_flow_form(tmp_path, (['custom_gate.tcl', hook], [hook]))
    rec = C.stage(tmp_path)
    chain = (tmp_path / 'prd_post_grt_chain.tcl').read_text()
    assert hook not in chain and 'source /work/custom_gate.tcl' in chain and 'source /work/grt_post.tcl' in chain
    assert 'core_final_repair' not in chain and rec['skipped_clock_hooks'] == [hook, hook]


def test_clock_hook_without_final_repair_inlines_the_rest(tmp_path):
    (tmp_path / 'grt_post_core.tcl').write_text('source /work/custom_gate.tcl\nsource /work/tapbal_grt.tcl\n')
    rec = C.stage(tmp_path)
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/custom_gate.tcl\n'
    assert rec['skipped_clock_hooks'] == ['tapbal_grt.tcl'] and not rec.get('skipped_final_repair')


def test_legacy_drv_wrapper_with_clock_hook_still_skips_repair(tmp_path):
    fixture(tmp_path)
    core = tmp_path / 'grt_post_core.tcl'
    core.write_text(core.read_text() + 'source /work/subtree_balance.tcl\n')
    rec = C.stage(tmp_path)
    assert rec['skipped_generated_repair'] and rec['skipped_clock_hooks'] == ['subtree_balance.tcl']
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/grt_post.tcl\n'


def test_data_only_kit_unchanged(tmp_path):
    (tmp_path / 'grt_post_core.tcl').write_text('source /work/custom_gate.tcl\n')
    rec = C.stage(tmp_path)
    assert 'skipped_clock_hooks' not in rec
    assert (tmp_path / 'prd_post_grt_chain.tcl').read_text() == 'source /work/grt_post_core.tcl\n'
