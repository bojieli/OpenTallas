"""HBM-MU-QUAD-6/EP (COORD 10-27): every hard core keeps >= 1 routing channel per direction through each macro column /
row, and plan channel demand <= 0.6 track use (check.core_channel_findings / check_core_channels, G0C core_channels)."""
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check

MW, MH = 171.288, 77.784
OUT = [250.56, 375.84]


def _ep(x0, ys, channels=None):
    cm = dict(status="KNOWN", outline_um=OUT,
              macros=[dict(name=f"m{i}", rect_um=[x0, y, x0 + MW, y + MH]) for i, y in enumerate(ys)])
    if channels is not None:
        cm["channels"] = channels
    return cm


RP1 = _ep(34.56, [35.1, 121.5, 210.06, 289.98])          # planU6c rp1 pack: gaps 8.616 / 10.776 / 2.136
EP6 = _ep(12.96, [7.02, 97.74, 194.94, 285.66])          # HBM-MU-QUAD-6/EP: gaps 12.936 / 19.416 / 12.936


class _T:
    def __init__(self, types):
        self.types = types


def _plan(tmp_path, cm, status="KNOWN"):
    cm = dict(cm, status=status)
    (tmp_path / "core_macros.json").write_text(json.dumps(dict(schema="opentallas.core_macros.v1", halo_um=0.0,
                                                               cores=dict(hfd_ep_static=cm))))
    return _T(dict(NW_io=dict(outline_um=[1000.0, 1000.0], hard_cores=[
        dict(inst="u_ep_N0", module="hfd_ep_static", origin_um=[0.0, 0.0], outline_um=OUT)])))


def _run(P, d, completeness=True):
    R = check.Report(completeness)
    out = check.check_core_channels(P, R, d)
    return out, [i for i in R.errors() if i["check"] == "core_channels"], R


def test_rp1_stack_has_no_channel_fails(tmp_path):
    f = check.core_channel_findings(RP1)
    bad = [x for x in f if not x["ok"]]
    assert len(bad) == 1 and bad[0]["dir"] == "H" and bad[0]["macros"] == 4
    assert abs(bad[0]["widest_interior_um"] - 10.776) < 1e-6
    out, errs, _ = _run(_plan(tmp_path, RP1), tmp_path)
    assert out["failing_modules"] == ["hfd_ep_static"] and len(errs) == 1 and "horizontal channel" in errs[0]["msg"]


def test_ep_replan_passes(tmp_path):
    f = check.core_channel_findings(EP6)
    assert all(x["ok"] for x in f)
    assert [x["macros"] for x in f if x["dir"] == "V"] == [1, 1, 1, 1]     # each SRAM row: W 12.96 / E 66.3 strips
    out, errs, _ = _run(_plan(tmp_path, EP6), tmp_path)
    assert out["checked"] == 1 and not errs


def test_channel_demand_track_use(tmp_path):
    ok = _ep(12.96, [7.02, 97.74, 194.94, 285.66], [dict(name="c2", dir="H", span_um=[175.524, 194.94], demand_nets=42)])
    f = [x for x in check.core_channel_findings(ok) if x["kind"] == "channel"][0]
    assert f["ok"] and abs(f["tracks"] - (404 + 539 * 0.5)) < 1e-6 and f["use"] < 0.1
    hot = _ep(12.96, [7.02, 97.74, 194.94, 285.66], [dict(name="N", dir="H", span_um=[363.444, 375.84], demand_nets=931)])
    out, errs, _ = _run(_plan(tmp_path, hot), tmp_path)
    assert len(errs) == 1 and "track use" in errs[0]["msg"]


def test_single_macro_needs_an_end_band():
    full = dict(status="KNOWN", outline_um=[100.0, 100.0], macros=[dict(name="m", rect_um=[20.0, 0.0, 80.0, 100.0])])
    bad = [x for x in check.core_channel_findings(full) if not x["ok"]]
    assert len(bad) == 1 and bad[0]["dir"] == "H"                     # spans the full height: no horizontal route
    ok = dict(full, macros=[dict(name="m", rect_um=[20.0, 0.0, 80.0, 80.0])])
    assert all(x["ok"] for x in check.core_channel_findings(ok))


def test_unknown_warns_and_is_g0c(tmp_path):
    assert "core_channels" in check.G0C_CHECKS
    out, errs, R = _run(_plan(tmp_path, RP1, status="UNKNOWN"), tmp_path)
    assert not errs and out["unknown"] == 1 and any(i["check"] == "core_channels" and i["level"] == "WARN" for i in R.items)
    out, errs, R = _run(_plan(tmp_path, RP1), tmp_path, completeness=False)
    assert not errs and any(i["msg"].startswith("[G0C]") for i in R.items)
