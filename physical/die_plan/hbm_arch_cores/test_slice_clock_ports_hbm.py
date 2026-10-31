"""HBM-CORES-KITS-30 (COORD 10-30 exp0 ruling B): gen_core_kit_hbm passes its root pins to MS.kit_apply for a
multi-root slice (clock_entries[]); a single-entry slice keeps the old call (None, existing multi-port kits unchanged)."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
import master_slice as MS  # noqa: E402

spec = importlib.util.spec_from_file_location("coregen_msports", HERE / "gen_core_kit_hbm.py")
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)

MOD = "fixture_core"
PORTS = ["clk_a[0]", "clk_a[1]"]


def _slice(multi):
    sl = dict(schema=MS.SCHEMA, die="hbm", kind="core", type=MOD, module=MOD, instances=[], frozen=False,
              master_plan_sha256="TRIAL-no-frozen-master-plan", outline_um=[100, 100],
              latency=dict(common_clock_latency_ps=dict(TT=250, FF=202.5), tol_ps=20, early_taps=False),
              keepouts=[], bays=[], entry_pins=[], hard_cores=[], corridors=[], gates={})
    if multi:
        sl["islands"] = [dict(name=p, rect_um=[0, 0, 100, 100]) for p in PORTS]
        sl["clock_entries"] = [dict(port=p, island=p, clock_pin=dict(layer="M5", xy_um=[20 + 10 * i, 50]),
                                    latency=dict(common_clock_latency_ps=dict(TT=250, FF=202.5)))
                               for i, p in enumerate(PORTS)]
    else:
        sl["core_clock_port"] = "clk_a[0]"
        sl["islands"] = [dict(name="clock_entry", rect_um=[40, 40, 60, 60], centre_um=[50, 50],
                              clock_pin=dict(layer="M5", xy_um=[50, 50]))]
    return sl


def _dir(tmp_path, multi):
    d = tmp_path / ("multi" if multi else "single")
    d.mkdir()
    sl = _slice(multi)
    assert MS.validate(sl) == [], MS.validate(sl)
    (d / f"{MOD}.json").write_text(json.dumps(sl))
    return d


def test_no_slice_dir_keeps_old_call():
    assert coregen.slice_clock_ports(None, MOD, PORTS) is None


def test_single_entry_slice_keeps_old_call(tmp_path):
    assert coregen.slice_clock_ports(_dir(tmp_path, False), MOD, PORTS) is None


def test_multi_root_slice_gets_generator_pins(tmp_path):
    d = _dir(tmp_path, True)
    assert coregen.slice_clock_ports(d, MOD, PORTS) == PORTS
    kd = tmp_path / "kit"
    kd.mkdir()
    # the pre-fix call (no pins) is refused by kit_apply's root check; the generator pins pass that check
    with pytest.raises(MS.SliceError, match="multi-root slice entries"):
        MS.kit_apply(kd, MOD, [100, 100], d, None, True, kind="core")
    try:
        MS.kit_apply(kd, MOD, [100, 100], d, None, True, kind="core", clock_ports=coregen.slice_clock_ports(d, MOD, PORTS))
    except MS.SliceError as exc:
        assert "multi-root" not in str(exc)
    with pytest.raises(MS.SliceError, match="multi-root slice entries"):
        MS.kit_apply(kd, MOD, [100, 100], d, None, True, kind="core", clock_ports=PORTS[:1])
