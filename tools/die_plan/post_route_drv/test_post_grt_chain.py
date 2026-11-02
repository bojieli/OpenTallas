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
