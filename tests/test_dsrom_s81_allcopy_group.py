import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('allcopy', ROOT / 'tools/dsrom_s81_allcopy_group.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


@pytest.mark.parametrize('bit', [0, 63, 82, 83, 165, 166, 248, 249, 255])
def test_every_chunk_detects_mutant(bit):
    images = [0] * 6
    images[5] = 1 << bit
    assert not m.qualified_images(images)


def test_expected_image_is_not_copy_consensus():
    assert m.qualified_images([7] * 6)
    assert not m.qualified_images([7] * 6, expected=3)
    with pytest.raises(ValueError):
        m.qualified_images([7] * 5)


def test_calendar_and_capacity():
    model = m.build()
    assert model['calendar'][-1]['end_edge'] == 18
    assert model['service']['bank_service_II_slow_edges'] == 32
    assert model['service']['bank_pipeline_capacity_rows'] == 1
    assert model['WQD4_max_service']['predecessor_wait_ns'] == pytest.approx(3 * 32 / .9)
    assert model['validator']['physical_leaf_replicas'] == 60
    assert model['ports']['macro_instances_unchanged'] == 24


def test_positive_slot_cost_without_admission():
    model = m.build()
    assert model['area']['incremental_logic50_mm2'] > 0
    assert model['slot']['outline_um'][1] > 347.76
    assert model['limits']['engine_RTL_admitted'] is False
    assert model['slot']['actual_parent_home'] is None
