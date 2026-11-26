"""C-LANDING-STATUS-UNDRIVEN: collector local sources without a landed ring are dropped, driven ones kept."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landings as CL  # noqa: E402


def src(b):
    return dict(name=b, ready=f"landing_ready_{b}", fault=f"landing_fault_{b}")


def test_stale_sidecar_source_is_dropped_driven_kept():
    logic = ["    wire landing_ready_ft0_i, landing_fault_ft0_i;", "    wire landing_ready_i_host_hbm_rst_n, landing_fault_i_host_hbm_rst_n;"]
    keep, stale = CL.drop_undriven_local_sources([src("ft0_i"), src("i_host_die_rst_n"), src("i_host_hbm_rst_n")], logic)
    assert [k["name"] for k in keep] == ["ft0_i", "i_host_hbm_rst_n"]
    assert stale == ["i_host_die_rst_n"]


def test_output_port_status_counts_as_driven_and_prefix_names_do_not_alias():
    keep, stale = CL.drop_undriven_local_sources([src("a"), src("ab")], [], ["    output wire landing_ready_ab", "    output wire landing_fault_ab"])
    assert [k["name"] for k in keep] == ["ab"] and stale == ["a"]


def test_all_driven_is_unchanged():
    logic = ["    wire landing_ready_x, landing_fault_x;"]
    keep, stale = CL.drop_undriven_local_sources([src("x")], logic)
    assert keep == [src("x")] and stale == []
