"""DIE-HBM-32 10-30: opt-in shallow density-tap CTS form; the default form stays byte-identical."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("coregen_dtap", HERE / "gen_core_kit_hbm.py")
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)

OLD = ("override export CTS_ARGS = -sink_clustering_enable -repair_clock_nets -delay_buffer_derate 0.5 "
       "-sink_clustering_max_diameter 30 -sink_clustering_size 20 -distance_between_buffers 40 -balance_levels")


def test_default_form_unchanged():
    assert coregen.density_cts_lines(0.5) == [OLD]
    assert coregen.density_cts_lines(0.5, False) == [OLD]


def test_shallow_form():
    lines = coregen.density_cts_lines(0.5, True)
    assert lines[0] == "export OT_DTAP_ISO = 0"
    assert "-distance_between_buffers 100" in lines[1] and "-sink_clustering_size 30" in lines[1]
    assert "-sink_clustering_max_diameter 60" in lines[1] and lines[1].startswith("override export CTS_ARGS = ")


def test_derate_passthrough():
    assert "-delay_buffer_derate 0.3 " in coregen.density_cts_lines(0.3)[0]
    assert "-delay_buffer_derate 0.3 " in coregen.density_cts_lines(0.3, True)[1]
