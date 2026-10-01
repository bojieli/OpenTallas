"""CPU-only refusal tests for the guard around the unchanged QC-NAM rule."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("guard", Path(__file__).parents[1] / "tools/qcnam_finalize_guard.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)


def gen():
    return [dict(name=f"gen{i}", ids=[0] * 256, prompt_len=128) for i in range(8)]


@pytest.mark.parametrize("change", ["partial", "short", "missing", "duplicate"])
def test_rejects_incomplete_greedy(change):
    rows = gen()
    if change == "partial":
        rows[0]["partial"] = True
    elif change == "short":
        rows[0]["ids"].pop()
    elif change == "missing":
        rows.pop()
    else:
        rows[0]["name"] = rows[1]["name"]
    with pytest.raises(ValueError):
        G.validate_gen(rows)


def test_complete_greedy():
    G.validate_gen(gen())


def test_partial_greedy_after_success_status_is_still_rejected(tmp_path):
    (tmp_path / "status").write_text("start now\nend rc=0 now\n")
    (tmp_path / "log.txt").write_text("done 123\n")
    G.completed(tmp_path)
    rows = gen()
    rows[0]["partial"] = True
    with pytest.raises(ValueError):
        G.validate_gen(rows)


@pytest.mark.parametrize("status", ["start now\n", "end rc=1 now\n", "end rc=0 now\nstart again\n"])
def test_completion_ignores_stale_success(tmp_path, status):
    (tmp_path / "status").write_text(status)
    (tmp_path / "log.txt").write_text("done 123\n")
    with pytest.raises(ValueError):
        G.completed(tmp_path)


def test_live_lane_blocks_before_reading_results(monkeypatch, tmp_path):
    obs = tmp_path / "obs.json"
    obs.write_text(json.dumps(dict(source_sha256={"tool": "hash"})))
    monkeypatch.setattr(G, "source_identity", lambda: {"tool": "hash"})
    monkeypatch.setattr(G, "active_jobs", lambda: [dict(pid=2637364)])
    monkeypatch.setattr(G, "snapshot_identity", lambda: pytest.fail("must not touch result/snapshot validation"))
    monkeypatch.setattr("sys.argv", ["guard", "--observation", str(obs), "--finalize", "--out", str(tmp_path / "out.json")])
    assert G.main() == 2
    assert not (tmp_path / "out.json").exists()


def test_changed_source_blocks(monkeypatch, tmp_path):
    obs = tmp_path / "obs.json"
    obs.write_text(json.dumps(dict(source_sha256={"tool": "old"})))
    monkeypatch.setattr(G, "source_identity", lambda: {"tool": "new"})
    monkeypatch.setattr("sys.argv", ["guard", "--observation", str(obs)])
    with pytest.raises(ValueError, match="source identity"):
        G.main()


def vehicle():
    name = "mmlu1000"
    args = dict(G.SPECS[name], max_layers=0, mmlu_seed=0, resume=True, snapshot=str(G.SNAP),
                gen_file=None, stress_ctx=2048)
    for k, f in (("out", "run.json"), ("raw_out", "raw.json"), ("partial", "partial.json"), ("work", "work")):
        args[k] = str(G.RUNS / name / f)
    ins = {"quant": {"q": dict(nan_in=0, inf_in=0, nan_out=0, inf_out=0, saturated=0)},
           "mv": {"v": dict(nan_in=0, inf_in=0, nan_out=0, inf_out=0)}, "norm": {"n": dict(nan=0, inf=0)}, "probe": {}}
    layers = []
    for i in range(40):
        l = dict(layer=i, instr={m: copy.deepcopy(ins) for m in ("b", "b_nam")})
        l["instr"]["b_nam"]["probe"] = {"q": dict(e_b=dict(mean=1, rows=256), e_n=dict(mean=1, rows=256))}
        for k in ("router", "hidden_rel_rms", "router_by_pos", "index", "index_by_pos"):
            l[k] = {m: 0 for m in G.FREE[1:]} if not k.startswith("index") or i in (2, 8, 14, 20, 24, 28, 32, 36) else {}
        for key, bucket, count, flips, rate in (
            ("router", "router_by_pos", "tokens", "tokens_with_flip", "flip_rate"),
            ("index", "index_by_pos", "queries", "queries_with_diff", "query_flip_rate"),
        ):
            for m in l[key]:
                l[key][m] = {count: 1000, flips: 0, rate: 0}
                l[bucket][m] = {count: [1000] + [0] * 8, "flips": [0] * 9}
        layers.append(l)
    rec = dict(schema="opentallas.deepseek-v41-flash-norm-after-matvec.v1.run", args=args, layers=layers,
               head_instr={m: copy.deepcopy(ins) for m in ("b", "b_nam")})
    raw = {m: [dict(kind="mmlu", mmlu_index=i, answer=0, pick=0, nan_logits=0, inf_logits=0) for i in range(1000)] for m in G.FREE}
    return rec, raw


def test_complete_vehicle():
    rec, raw = vehicle()
    G.validate_run("mmlu1000", rec, raw, gen())


@pytest.mark.parametrize("change", ["depth", "mode", "seed", "snapshot", "metric", "index", "instr", "head", "raw", "paired", "duplicates"])
def test_rejects_missing_or_mispaired_vehicle(change):
    rec, raw = vehicle()
    if change == "depth":
        rec["layers"].pop()
    elif change == "mode":
        rec["args"]["modes"] = "a,b,b_nam"
    elif change == "seed":
        rec["args"]["mmlu_seed"] = 1
    elif change == "snapshot":
        rec["args"]["snapshot"] = "/other"
    elif change == "metric":
        del rec["layers"][0]["router"]["b_nam"]
    elif change == "index":
        rec["layers"][2]["index"] = {}
    elif change == "instr":
        rec["layers"][0]["instr"]["b_nam"]["probe"] = {}
    elif change == "head":
        rec["head_instr"]["b_nam"]["norm"] = {}
    elif change == "raw":
        raw["b_nam"].pop()
    elif change == "paired":
        raw["b_nam"][0]["answer"] = 1
    else:
        raw["a"][0]["mmlu_index"] = 1
    with pytest.raises((ValueError, KeyError)):
        G.validate_run("mmlu1000", rec, raw, gen())


@pytest.mark.parametrize("change", ["buckets", "rate", "probe", "norm"])
def test_rejects_empty_or_inconsistent_samples(change):
    rec, raw = vehicle()
    l = rec["layers"][0]
    if change == "buckets":
        l["router_by_pos"]["b_nam"]["tokens"] = [0] * 9
    elif change == "rate":
        l["router"]["b_nam"]["flip_rate"] = 1
    elif change == "probe":
        l["instr"]["b_nam"]["probe"]["q"]["e_n"]["rows"] = 0
    else:
        del l["instr"]["b_nam"]["norm"]["n"]["nan"]
    with pytest.raises(ValueError):
        G.validate_run("mmlu1000", rec, raw, gen())


def test_existing_verdict_cannot_be_overwritten(monkeypatch, tmp_path):
    obs = tmp_path / "obs.json"
    obs.write_text(json.dumps(dict(source_sha256={}, snapshot_identity={}, job_sha256={})))
    out = tmp_path / "verdict.json"
    out.write_text('immutable FAIL\n')
    monkeypatch.setattr(G, "source_identity", lambda: {})
    monkeypatch.setattr(G, "snapshot_identity", lambda: {})
    monkeypatch.setattr(G, "active_jobs", lambda: [])
    monkeypatch.setattr(G, "JOBS", tmp_path / "jobs")
    monkeypatch.setattr("sys.argv", ["guard", "--observation", str(obs), "--finalize", "--out", str(out)])
    with pytest.raises(ValueError, match="immutable"):
        G.main()
    assert out.read_text() == 'immutable FAIL\n'
