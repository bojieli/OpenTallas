"""KV-102 r249: a plan hard_cores row with a tree-relative view is a kit macro view (kv3_hub_C qkd_ahub had no source)."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind  # noqa: E402


def test_relative_and_absolute_views(tmp_path):
    v = tmp_path / "physical/views/qkd_ahub"
    v.mkdir(parents=True)
    (v / "qkd_ahub.lef").write_text("")
    a = tmp_path / "abs/pcc"
    a.mkdir(parents=True)
    (a / "qkd_kvs_pcc.lef").write_text("")
    rows = [dict(module="qkd_ahub", lef="physical/views/qkd_ahub/qkd_ahub.lef"),
            dict(module="qkd_kvs_pcc", lef=str(a / "qkd_kvs_pcc.lef")),
            dict(module="missing", lef="physical/views/missing/missing.lef"),
            dict(module="other", lef="physical/views/qkd_ahub/qkd_ahub.lef"),
            dict(module="nolef")]
    assert bind.plan_row_views(rows, tmp_path) == {"qkd_ahub": v, "qkd_kvs_pcc": a}
