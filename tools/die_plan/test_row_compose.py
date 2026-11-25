"""ROLLING COMPOSE (COMPOSE-FAST 11-25): ledger order, publish on READY, drop rows that no longer apply, bisect a failing batch."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import row_compose as RC  # noqa: E402
import row_gate as RG  # noqa: E402


def _ready(led, name, rowfile, order=None, finished="2026-11-25T10:00:00Z", verdict="READY"):
    Path(rowfile).write_text(json.dumps({"ops": []}) + name)
    rec = dict(schema=RG.SCHEMA, verdict=verdict, lane=name, finished=finished,
               rows=[dict(kind="ops", path=str(rowfile), sha256=RG.sha(rowfile))])
    if order is not None:
        rec["order"] = order
    (Path(led) / f"{name}.json").write_text(json.dumps(rec))


def _setup(tmp_path):
    src = tmp_path / "src"
    (src / "p").mkdir(parents=True)
    (src / "p" / "base.json").write_text("{}")
    led = tmp_path / "led"
    led.mkdir()
    return src, led


class FakeGate:
    """writes the ROW-READY a gate would: READY unless a failing lane is in the batch; a 'stale' lane does not apply"""

    def __init__(self, fail=(), stale=()):
        self.fail, self.stale, self.calls = set(fail), set(stale), []

    def __call__(self, cmd, **k):
        out = Path(cmd[cmd.index("--out") + 1])
        rows = [c.split(":", 1)[1] for c in cmd if c.startswith("ops:")]
        lanes = [Path(r).stem for r in rows]
        self.calls.append(lanes)
        (out / "tree" / "p").mkdir(parents=True, exist_ok=True)
        name = cmd[cmd.index("--plan-name") + 1]
        (out / "tree" / "p" / name).write_text(json.dumps(lanes))
        recs = [dict(kind="ops", path=r, sha256=RG.sha(r), rc=3 if Path(r).stem in self.stale else 0,
                     dropped=Path(r).stem in self.stale) for r in rows]
        bad = [x for x in lanes if x in self.fail and x not in self.stale]
        rr = dict(schema=RG.SCHEMA, verdict="NOT-READY" if bad else "READY", why=[f"bind fails on {bad}"] if bad else [],
                  rows=recs, plan=dict(rel=f"p/{name}", sha256=RG.sha(out / "tree" / "p" / name)), seconds=dict(total=1))
        (out / "ROW-READY.json").write_text(json.dumps(rr))

        class R:
            returncode = 0 if not bad else 1
        return R()


def _args(tmp_path, src, led):
    return ["roll", "--die", "kv", "--ledger", str(led), "--pub", str(tmp_path / "pub"), "--src", str(src),
                                  "--base", "p/base.json", "--asbuilt", "p/ab.json", "--once", "--local"]


def _round(tmp_path, src, led, fake, monkeypatch):
    monkeypatch.setattr(RC.subprocess, "run", fake)
    monkeypatch.setattr(RG, "ot_delete", lambda p, log: 0)
    return RC.main(_args(tmp_path, src, led))


def test_order_is_ledger_deterministic(tmp_path):
    src, led = _setup(tmp_path)
    _ready(led, "b", tmp_path / "b.ops", finished="2026-11-25T09:00:00Z")
    _ready(led, "a", tmp_path / "a.ops", finished="2026-11-25T10:00:00Z")
    _ready(led, "z", tmp_path / "z.ops", order=1, finished="2026-11-25T11:00:00Z")
    _ready(led, "n", tmp_path / "n.ops", verdict="NOT-READY")
    assert [r["lane"] for r in RC.read_ledger(led)] == ["z", "b", "a"]


def test_publish_then_idle_then_new_row(tmp_path, monkeypatch):
    src, led = _setup(tmp_path)
    _ready(led, "a", tmp_path / "a.ops")
    _ready(led, "b", tmp_path / "b.ops")
    fake = FakeGate(stale={"b"})
    assert _round(tmp_path, src, led, fake, monkeypatch) == 0
    st = json.loads((tmp_path / "pub" / "compose_state.json").read_text())
    assert st["current"]["round"] == 1 and st["current"]["plan"] == "p/plan_roll_kv_r001.json" and len(st["included"]) == 1
    assert list(st["rejected"].values())[0]["lane"] == "b"
    assert json.loads((tmp_path / "pub" / "current.json").read_text())["tree"].endswith("rounds/r001/tree")
    # the plan moved, so b (rejected on the old plan) is retried once; then nothing is pending: no gate
    assert _round(tmp_path, src, led, fake, monkeypatch) == 0 and fake.calls[-1] == ["b"]
    n = len(fake.calls)
    assert _round(tmp_path, src, led, fake, monkeypatch) == 0 and len(fake.calls) == n        # idle now
    _ready(led, "c", tmp_path / "c.ops")
    assert _round(tmp_path, src, led, fake, monkeypatch) == 0 and fake.calls[-1] == ["c"]
    st = json.loads((tmp_path / "pub" / "compose_state.json").read_text())
    assert st["current"]["round"] == 3 and st["history"][1]["applied"] == []


def test_failing_batch_bisects_to_the_bad_row(tmp_path, monkeypatch):
    src, led = _setup(tmp_path)
    for i, x in enumerate("abcd"):
        _ready(led, x, tmp_path / f"{x}.ops", finished=f"2026-11-25T10:0{i}:00Z")
    fake = FakeGate(fail={"c"})
    rcs = [_round(tmp_path, src, led, fake, monkeypatch) for _ in range(5)]
    assert fake.calls[:4] == [["a", "b", "c", "d"], ["a", "b"], ["c", "d"], ["c"]]
    st = json.loads((tmp_path / "pub" / "compose_state.json").read_text())
    assert rcs[0] == 1 and fake.calls[4] == ["d"]
    assert [v["lane"] for v in st["rejected"].values()] == ["c"] and len(st["included"]) == 3
