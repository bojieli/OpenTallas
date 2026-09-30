"""Record check for the wide selected-CKV fetch (results/rtl/v41x_ckv_sel_attn_wide.json): source pins current,
full geometry (H16 D512 TD32 NL4 T640) exact through ID table -> ot_chip_v41x_ckv_pc_fetch (P=4 ports/stack,
SRAM slot store) -> all-gather -> collector -> merger -> engine, n_sel < 512 and all-owner cases, negative controls."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/v41x_ckv_sel_attn_wide.json"


def test_wide_record():
    r = json.loads(REC.read_text())
    assert r["status"] == "pass" and r["fetch"].startswith("wide fetch") and not r["stale_sources"]
    for rel, h in r["source_sha256"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == h, rel
    ex = {x["tag"]: x for x in r["exact_full_geometry"]}
    assert {"full1m", "full1m_lat259", "short300", "skew1m", "tail46"} <= set(ex)
    for x in ex.values():
        e = x["fields"]["V41XATTN"]
        assert x["pass_"] and e["sc_errors"] == 0 and e["pv_errors"] == 0
        assert e["sc_checked"] == 16 * x["T"] and e["pv_checked"] == 16 * 512
    assert ex["full1m"]["owners_die_stack"] == 16 and ex["short300"]["n_sel"] == 300
    assert ex["full1m"]["cycles"]["fetch_latency_last_id_to_last_row_staged"] <= 560
    assert ex["full1m"]["cycles"]["staging_overlaps_qk"]
    assert all(x["pass_"] for x in r["rows_only_reduced"])
    assert {m["mutation"] for m in r["negative_controls"] if m["caught"]} == \
        {"hbm_row_corrupted", "selection_unsorted", "source_unpublished"}
