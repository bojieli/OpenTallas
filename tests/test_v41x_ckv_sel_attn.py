"""Record check for the selected-CKV path (results/rtl/v41x_ckv_sel_attn.json, the single-port fetch; historical
since the wide fetch record results/rtl/v41x_ckv_sel_attn_wide.json): source pins equal the sources at the record's
git_head, every full-geometry case exact, the n_sel < 512 and all-owner cases present, negative controls caught."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "results/rtl/v41x_ckv_sel_attn.json"


def _rec():
    return json.loads(REC.read_text())


def test_status_and_source_pins_at_record_head():
    r = _rec()
    assert r["status"] == "pass"
    assert not r["stale_sources"] and not r["sources_dirty_at_record"]
    for rel, h in r["source_sha256"].items():
        blob = subprocess.run(["git", "show", f"{r['git_head']}:{rel}"], cwd=ROOT, check=True,
                              capture_output=True).stdout
        assert hashlib.sha256(blob).hexdigest() == h, rel


def test_full_geometry_exact_cases():
    r = _rec()
    ex = {x["case"]: x for x in r["exact_full_geometry"]}
    assert {"full1m", "short300", "skew1m", "tail46"} <= set(ex)
    for x in ex.values():
        assert x["pass_"], x["case"]
        e = x["fields"]["V41XATTN"]
        assert e["sc_errors"] == 0 and e["pv_errors"] == 0 and e["jobs"] == 1
        assert e["sc_checked"] == 16 * x["T"] and e["pv_checked"] == 16 * 512
        assert x["fields"]["CKVROWS"]["errors"] == 0 and x["fields"]["CKVROWS"]["checked"] == x["T"]
        assert x["fields"]["CKVSEL"]["faults"] == 0 and x["fields"]["CKVSEL"]["hbm_missing"] == 0
    assert ex["full1m"]["T"] == 640 and ex["full1m"]["owners_die_stack"] == 16
    assert ex["short300"]["n_sel"] == 300 < 512
    assert ex["full1m"]["cycles"]["staging_overlaps_qk"]


def test_reduced_rows_and_negative_controls():
    r = _rec()
    assert r["rows_only_reduced"] and all(x["pass_"] for x in r["rows_only_reduced"])
    names = {m["mutation"]: m["caught"] for m in r["negative_controls"]}
    assert names == {"hbm_row_corrupted": True, "selection_unsorted": True, "source_unpublished": True}
