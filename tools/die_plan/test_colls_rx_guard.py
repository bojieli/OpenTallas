"""Coll_s RX-stable istations guard (QC-INT-R2-COLLX 11-26): stock plan-site istations.tcl accepted, a native sidecar refused."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys as GP  # noqa: E402
import kit_istations as KI  # noqa: E402

T = {"relay_sites": {"u_a/q": [1.0, 2.0], "u_b/q": [3.0, 4.0]}}


def test_stock_writer_output_is_accepted(tmp_path):
    f = tmp_path / "istations.tcl"
    f.write_text(KI.relay_sites_only_tcl("coll_s", T))
    assert GP.colls_rx_istations_guard("coll_s", T, [f]) == []


def test_native_sidecar_is_refused(tmp_path):
    f = tmp_path / "istations.tcl"
    f.write_text(KI.relay_sites_only_tcl("coll_s", T) + "# native station\nplace u_x 9 9\n")
    with pytest.raises(ValueError, match="direct plan relay_sites"):
        GP.colls_rx_istations_guard("coll_s", T, [f])


def test_no_sidecar_passes_through():
    assert GP.colls_rx_istations_guard("coll_s", T, []) == []
