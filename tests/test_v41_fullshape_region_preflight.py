import subprocess
import sys

from tools.v41_fullshape_region_preflight import ROOT, build

import pytest

pytestmark = pytest.mark.skip(reason="historical Codex record ported by claude/w0-codex-reconcile: its tool asserts source gaps that 9be3f0f1 has since closed (die W_HBM, 30-bit wq_addr, sharded index, program bind digest); regenerate before citing")


def test_fullshape_region_preflight_exposes_current_gaps_and_optimistic_capacity():
    rec = build()
    actual = rec["actual_instantiation"]
    assert not actual["die_tile_idx_sharded"]
    assert not actual["selected_ckv_mux_client_connected"]
    assert not actual["rope_guard_proves_ckv_and_weight_region_floor"]
    assert rec["contexts"]["1048576"]["optimistic_compact_sharded_users_bound"] == 859
    assert rec["contexts"]["200000"]["optimistic_compact_sharded_users_bound"] == 4449
    for case in rec["contexts"].values():
        assert not case["model_users_fit_optimistic_layout"]
    assert not rec["contexts"]["1048576"]["current_key_slice_fits_one_user"]


def test_strict_region_gate_fails_until_layout_is_connected():
    p = subprocess.run([sys.executable, "tools/v41_fullshape_region_preflight.py", "--require-ready"],
                       cwd=ROOT, capture_output=True, text=True, check=False)
    assert p.returncode == 2
    assert '"full_shape_region_gate": "blocked"' in p.stdout
