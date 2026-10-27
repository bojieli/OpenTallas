"""S81-CORE-LAT-R14 10-27: multi-root cores are refused; face_guard skip names every clock root.
    python3 -m pytest -q -p no:cacheprovider --noconftest test_gen_core_kit_legacy_multiroot.py"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_core_kit_legacy as G  # noqa: E402

CRS4 = {"top": "dsfd_cfifo_crs4", "clock_port": "cr",
        "clock_ports": ["cr", "cr_s", "xk[0]", "xk[1]", "xk[2]", "xk[3]"], "reset_ports": ["rst"]}


def test_clock_roots_fold_bus_bits():
    assert G.clock_roots(CRS4) == ["cr", "cr_s", "xk"]
    assert G.clock_roots({"clock_port": "ck"}) == ["ck"]
    assert G.clock_roots({"clock_port": "clk", "clock_ports": ["clk[0]"]}) == ["clk"]


def test_single_root_not_refused():
    assert G.multi_root_refusal("m", {"clock_port": "ck", "clock_ports": ["ck"]}) is None
    assert G.multi_root_refusal("m", {"clock_port": "ck"}) is None


def test_multi_root_refused_names_every_root():
    msg = G.multi_root_refusal("dsfd_cfifo_crs4", CRS4)
    assert msg and "multi-root" in msg and "['cr', 'cr_s', 'xk']" in msg


def test_generator_refuses_crs4():
    r = subprocess.run([sys.executable, str(HERE / "gen_core_kit_legacy.py"), "--module", "dsfd_cfifo_crs4",
                        "--out", "/tmp/ot_mr_test_out", "--suffix", "t"], capture_output=True, text=True)
    assert r.returncode != 0 and "multi-root core ['cr', 'cr_s', 'xk']" in r.stderr, r.stderr[-1500:]
    assert not Path("/tmp/ot_mr_test_out/dsfd_cfifo_crs4_t").exists()
