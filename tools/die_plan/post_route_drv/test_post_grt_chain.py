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
