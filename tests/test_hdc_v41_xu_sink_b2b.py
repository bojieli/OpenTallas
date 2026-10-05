"""Back-to-back Sinkhorn ops through the V4.1 XU and the v41x XU adapter (rtl/test/tb_hdc_v41_xu_sink_b2b.sv,
tools/dsrom_sink_b2b_sweep.py): with the default-off acceptance handshake OFF every gap of 0 or 1 cycle after a
result hangs (the MTP ITER deadlock at pc 4386); ON every case passes and the cases that pass in both take
identical cycles.  The committed sweep record must pass and be current."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/dsrom_sink_handshake_20261004/b2b_sweep/result.json"


def test_sweep_record_passes_and_is_current():
    r = json.loads(REC.read_text())
    assert r["pass"]
    for unit in ("xu", "adapt"):
        c = r["configs"][unit]
        assert c["off"]["hang"] == 14 and c["off"]["hang_gaps"] == [0, 1]
        assert c["on"]["cases"] == 105 and c["on"]["hang"] == 0 and c["on"]["mismatch"] == 0
        assert c["cases_ok_in_both"] == 91 and c["cycle_identical_where_both_ok"]
        assert any("dspark_sink_handshake" in s for s in c["on"]["sources"])
    for p, h in r["input_sha256"].items():
        assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h, p


def test_successor_adapter_differs_only_in_the_handshake():
    a = (ROOT / "rtl/hdc/v41x/ot_hdc_v41x_xu_adapt.sv").read_text().splitlines()
    b = (ROOT / "rtl/hdc/v41/dspark_sink_handshake/ot_hdc_v41x_xu_adapt.sv").read_text().splitlines()
    import difflib
    changed = [l[1:] for l in difflib.unified_diff(a, b, lineterm="", n=0)
               if l[:1] in "+-" and not l.startswith(("+++", "---"))]
    assert all(("sk_" in l or "SINK_HANDSHAKE" in l or "`endif" in l) for l in changed), changed
