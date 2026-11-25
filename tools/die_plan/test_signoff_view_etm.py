"""VIEW-FF-1125: every sign-off corner session writes its timing model; cmd_run publishes <design>_<corner>.lib."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff as SO  # noqa: E402


def test_each_corner_session_writes_its_timing_model():
    for c in ("tt", "ff"):
        t = SO.session_tcl(c, ([], []), "/base/6_final.spef")
        assert f"write_timing_model -library_name \"[current_design]_{c}\" /out/etm_{c}.lib" in t
        assert t.index("write_timing_model") < t.index("so DONE 1")
        assert "catch {write_timing_model" in t                 # a failure never ends the session


def test_publish_copies_ff_and_tt_with_the_design_name(tmp_path):
    for c in ("tt", "ff"):
        (tmp_path / c).mkdir()
        (tmp_path / c / f"etm_{c}.lib").write_text(f"library (m_{c}) {{}}\n")
    got = SO.publish_etms(tmp_path, {"tt": {"design": "ot_m"}, "ff": {"design": "ot_m"}})
    assert (tmp_path / "ot_m_ff.lib").read_text() == "library (m_ff) {}\n"
    assert set(got) == {"tt", "ff"} and got["ff"].endswith("ot_m_ff.lib")


def test_publish_reports_missing_model_without_failing(tmp_path):
    (tmp_path / "ff").mkdir()
    got = SO.publish_etms(tmp_path, {"ff": {"design": "ot_m"}, "tt": {}})
    assert got == {"ff": "no timing model written", "tt": "no design name in the session"}
