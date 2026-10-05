import hashlib
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden_v41 as G  # noqa: E402
import rtl_hdc_v41_blockdot_campaign as campaign  # noqa: E402

PHYSICAL = ROOT / "results/physical_abi3/asap7/hdc/v41"
TOPS = ("ot_hdc_actquant", "ot_hdc_fp4qdq", "ot_hdc_blockdot")


def test_committed_record_is_current_and_passes():
    record = json.loads(campaign.OUT.read_text())
    assert record["status"] == "pass"
    assert record["real_operands"]["enabled"]
    for sim in record["simulations"]:
        assert sim["pass"]
        for unit in ("actquant", "fp4qdq"):
            assert sim[unit]["mismatches"] == 0 and sim[unit]["checked"] == sim[unit]["vectors"]
        assert sim["blockdot"]["mismatches"] == 0 and sim["blockdot"]["checked"] == sim["blockdot"]["rows"]
    for sat in record["saturation_unreachable"].values():
        assert sat["blocks_where_the_clip_acts"] == 0
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_physical_records_route_the_committed_sources():
    for top in TOPS:
        body = json.loads((PHYSICAL / top / "physical.json").read_text())
        assert body["design"]["top"] == top
        for src in body["design"]["sources"]:
            assert hashlib.sha256((ROOT / src["path"]).read_bytes()).hexdigest() == src["sha256"], src["path"]


def test_code_tables_invert_the_golden_tables():
    codes = np.array([c for c in range(256) if (c & 0x7F) != 0x7F])
    assert np.array_equal(campaign.e4m3_codes(G.E4M3[codes]), codes)
    assert np.array_equal(campaign.e2m1_codes(G.E2M1), np.arange(16))
