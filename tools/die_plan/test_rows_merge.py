"""rows_merge (S81-LEAF-PLAN 11-15): two row files touching different fields of one type both land; the same field
changed to two different values is a conflict and keeps the first; points are atomic."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rows_merge as RM  # noqa: E402


def test_merge_and_conflict(tmp_path):
    base = dict(partition_types=dict(T=dict(a=1, b=[[0.0, 0.0], [1.0, 1.0]], c=dict(x=1))))
    (tmp_path / "base.json").write_text(json.dumps(base))
    (tmp_path / "r1.json").write_text(json.dumps(dict(T=dict(a=2, b=[[0.0, 5.0], [1.0, 1.0]], c=dict(x=1)))))
    (tmp_path / "r2.json").write_text(json.dumps(dict(T=dict(a=3, b=[[0.0, 0.0], [1.0, 1.0]], c=dict(x=1, y=2)))))
    rc = RM.main([str(tmp_path / "base.json"), str(tmp_path / "o.json"), str(tmp_path / "l.json"),
                  str(tmp_path / "r1.json"), str(tmp_path / "r2.json")])
    t = json.loads((tmp_path / "o.json").read_text())["partition_types"]["T"]
    led = json.loads((tmp_path / "l.json").read_text())
    assert rc == 3 and t == dict(a=2, b=[[0.0, 5.0], [1.0, 1.0]], c=dict(x=1, y=2))
    assert [c["path"] for c in led["conflicts"]] == [["a"]]


def test_point_is_atomic():
    assert RM.changes([0.0, 1.0], [2.0, 1.0]) == [((), [0.0, 1.0], [2.0, 1.0])]
