import pytest
"""hgi_b2 (B2 four-cluster distributed-VM die): the chained reduction is the golden csum8 order for any split, and the
B2 export of a tiny Qwen layer is exact on every rank while both broken machines are refused."""
import json

import numpy as np
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
    spec = np.frombuffer((out / "b2" / "vm0_spec.bin").read_bytes(), "<u4")       # SPEC v0.5 die image
    assert spec.size == 360448
    vm0 = np.frombuffer((out / "vm0.bin").read_bytes(), "<u4") if (out / "vm0.bin").exists() else None
    if vm0 is not None and vm0.size > 262144:                                     # HC aperture relocated to 294,912
        assert np.array_equal(spec[294912:294912 + vm0.size - 262144], vm0[262144:])
    for q in range(4):
        s = np.frombuffer((out / "b2" / f"vm0_s{q}.bin").read_bytes(), "<u4")
        assert np.array_equal(s[:65536], spec[q * 65536:(q + 1) * 65536]) and np.array_equal(s[65536:], spec[262144:294912])
    assert "REPLX" in str(v["modes"])
    cap = v["capacity"]                                                            # liveness reuse
    assert cap["mirror_words"] <= cap["logical_mirror_words"] and cap["peak_live_mirror"] <= cap["mirror_words"]
    for m in ("stale_mirror", "chain_naive", "alias_dead"):
        rc, out = _export(tmp_path, "--b2-mutant", m)
        assert rc == 3, m
        assert json.loads((out / "b2" / "verdict.json").read_text())["violations"] > 0


def test_spec_v05_decode():
    from hgi_b2 import b2 as B
    assert B.SPEC_WORDS == 360448 and B.HCAP_BASE == 294912 and B.REPL_BASE == 262144
    assert B.decode(3 * 65536 + 7) == ("slice", 3, 7)
    assert B.decode(262144 + 5) == ("repl", 5) and B.decode(294911) == ("repl", 32767)
    assert B.decode(294912) == ("hcap", 0) and B.decode(360447) == ("hcap", 65535)
    assert B.spec_of_logical_aperture(262144 + 9) == 294912 + 9
    with pytest.raises(ValueError):
        B.decode(360448)
