"""cland_clock_contract.write: per-pin clk / fclk means from the census logs, checked against the signoff census."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cland_clock_contract as K  # noqa: E402


def _kit(tmp_path, n=3, mean=254.0):
    kit, out = tmp_path / "kit", tmp_path / "out"
    (kit / "signoff").mkdir(parents=True)
    corners = {c: {"insertion_pinflops": {"n": n, "mean": mean}} for c in ("tt", "ff")}
    (kit / "signoff" / "signoff.json").write_text(json.dumps({"verdict": "SIGNED", "corners": corners}))
    for c in ("tt", "ff"):
        (out / c).mkdir(parents=True)
        lines = [f"SO_CK 1 {mean - 1 + i} clk" for i in range(3)] + ["SO_CKP 1 0 254.0 243.3 clk",
                 "MK_FCK 1 80.5 fclk", "MK_FCK 1 81.5 fclk", "MK_FCK 0 70.0 fclk", "MK_DONE 1"]
        (out / c / "sta.log").write_text("\n".join(lines) + "\n")
    lib = tmp_path / "m_tt.lib"
    lib.write_text('library (x) { cell ("m") { } }')
    return kit, out, lib


def test_write_contract(tmp_path):
    kit, out, lib = _kit(tmp_path)
    K.write(kit, out, lib)
    d = json.loads((out / "clock_contract.json").read_text())
    assert d["schema"] == "opentallas.core_clock_contract.v1" and d["signed"] is True
    assert d["pins"]["clk"]["tt"]["mean_ps"] == 254.0 and d["pins"]["clk"]["tt"]["n"] == 3
    assert d["pins"]["fclk"]["ff"]["mean_ps"] == 81.0 and d["pins"]["fclk"]["ff"]["n"] == 2   # cone flops only


def test_write_refuses_census_mismatch(tmp_path):
    kit, out, lib = _kit(tmp_path, n=4)
    with pytest.raises(SystemExit, match="insertion_pinflops"):
        K.write(kit, out, lib)


def test_write_refuses_incomplete_log(tmp_path):
    kit, out, lib = _kit(tmp_path)
    (out / "ff" / "sta.log").write_text("SO_CK 1 254.0 clk\n")
    with pytest.raises(SystemExit, match="incomplete"):
        K.write(kit, out, lib)
