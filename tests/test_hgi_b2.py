"""hgi_b2 (B2 four-cluster distributed-VM die): the chained reduction is the golden csum8 order for any split, and the
B2 export of a tiny Qwen layer is exact on every rank while both broken machines are refused."""
import json
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))


def test_chain_equals_golden_csum():
    from hgi_b2 import reduce as RD
    assert RD.selftest(seed=3) == 0


def _export(tmp, *extra):
    from hgi_sim import test_tiny as TT
    snap = tmp / "snap"
    if not (snap / "model.safetensors").exists():
        snap.mkdir(parents=True, exist_ok=True)
        TT.write_snapshot(snap)
    out = tmp / ("out" + "_".join(extra))
    p = subprocess.run([sys.executable, "-m", "hgi_e2e.export", "qwen", "--snapshot", str(snap), "--cache",
                        str(snap / "img"), "--layer", "0", "--position", "100", "--out", str(out), "--layout", "b2",
                        *extra], cwd=TOOLS, capture_output=True, text=True)
    return p.returncode, out


def test_tiny_qwen_b2_exact_and_mutants_refused(tmp_path):
    rc, out = _export(tmp_path)
    v = json.loads((out / "b2" / "verdict.json").read_text())
    assert rc == 0 and v["exact"] and v["violations"] == 0
    assert v["capacity"]["fits"] and v["stats"]["chain_reductions"] > 0
    assert all(len(set(w)) <= 2 for w in v["work_per_cluster"].values())          # balanced by construction
    meta = json.loads((out / "meta.json").read_text())
    assert all("cluster" in r for r in meta["records"])                           # the harness's placement input
    assert (out / "b2" / "slice.npy").exists() and v["ring_cycles"]["per_layer"]
    for m in ("stale_mirror", "chain_naive"):
        rc, out = _export(tmp_path, "--b2-mutant", m)
        assert rc == 3, m
        assert json.loads((out / "b2" / "verdict.json").read_text())["violations"] > 0
