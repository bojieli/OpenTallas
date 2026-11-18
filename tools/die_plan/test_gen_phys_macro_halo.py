"""HALO-1 (S81-GEOM-OPUS 11-18): hard_cores[].halo_um -> placement-blockage ring after place_macro; none = no lines."""
import gen_phys as GP


def _placed():
    return [{"inst": "u_bound.u_u_cf", "inst_db": "u_bound.u_u_cf", "x": 1.0, "y": 2.0, "o": "R0"},
            {"inst": "u_bound.u_u_t0", "inst_db": "u_bound.u_u_t0", "x": 3.0, "y": 4.0, "o": "R0"}]


def test_no_halo_key_is_byte_identical():
    t = {"hard_cores": [{"inst": "u_bound.u_u_cf", "module": "m", "origin_um": [1, 2]}]}
    assert GP.macro_halo_lines(t, _placed()) == []


def test_halo_rows_emit_one_ring_call_per_core():
    t = {"hard_cores": [{"inst": "u_bound.u_u_cf", "module": "m", "origin_um": [1, 2], "halo_um": 5.0},
                        {"inst": "u_bound.u_u_t0", "module": "m", "origin_um": [3, 4], "halo_um": 0}]}
    out = GP.macro_halo_lines(t, _placed())
    assert "proc ot_macro_halo" in out[1]
    assert out[2:] == ["ot_macro_halo {u_bound.u_u_cf} 5"]


def test_halo_on_unplaced_core_fails_closed():
    import pytest
    t = {"hard_cores": [{"inst": "u_r0.u_zz", "module": "m", "origin_um": [1, 2], "halo_um": 5.0}]}
    with pytest.raises(ValueError, match="HALO-1"):
        GP.macro_halo_lines(t, _placed())
