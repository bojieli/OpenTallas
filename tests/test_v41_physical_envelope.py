import math
import pytest
from tools.audit_v41_physical_envelope import capacity


def test_single_reticle_rejected_even_before_compute():
    r = capacity(815, 307527990600, 9379500)
    assert not r['capacity_fits_with_all_area_available']
    assert r['minimum_devices_if_entire_area_were_rom'] == 42


def test_square_wafer_distinguishes_engram_placement():
    assert capacity(45000, 307527990600, 9379500)['capacity_fits_with_all_area_available']
    assert not capacity(45000, 510286023000, 9379500)['capacity_fits_with_all_area_available']


def test_reserve_is_charged_and_gross_area_is_not_required_area():
    r = capacity(math.pi*150**2, 510286023000, 9379500)
    assert r['rom_area_required_mm2'] == pytest.approx(55514.688786)
    assert r['area_left_before_compute_sram_fabric_mm2'] < 16000
