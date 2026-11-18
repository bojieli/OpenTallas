"""ROUTED-KEEP 11-18: a failed verdict never deletes a routed attempt's results (PROBE_DELETE run for real on a scratch kit)"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
import pytest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import autopilot as AP

ROOT = "/srv/opentallas-scratch2/claude/lanes"


def kit(routed):
    k = tempfile.mkdtemp(prefix="routed-keep-test-", dir=ROOT)
    base = Path(k) / "run/results/asap7/dp_x/base"
    base.mkdir(parents=True)
    (Path(k) / "config.mk").write_text("x\n")
    for n in (["5_1_grt.odb", "6_final.odb", "6_final.spef"] if routed else ["5_1_grt.odb"]):
        (base / n).write_text("x")
    return k


def probe(k):
    p = subprocess.run([sys.executable, "-I", "-c", AP.PROBE_DELETE, json.dumps({"kit": k, "dry": False})], capture_output=True, text=True, timeout=300)
    return json.loads([x for x in p.stdout.splitlines() if x.startswith("AP_JSON ")][-1][8:])


@pytest.mark.skipif(not os.path.isdir(ROOT) or not shutil.which("docker"), reason="needs a build host scratch root")
def test_routed_attempt_is_kept_unrouted_failed_data_goes():
    k = kit(True)
    try:
        r = probe(k)
        assert r.get("preserved") and "routed attempt" in r["reason"] and (Path(k) / "run/results/asap7/dp_x/base/6_final.odb").exists()
    finally:
        shutil.rmtree(k)
    k = kit(False)
    try:
        r = probe(k)
        assert not r.get("preserved") and not (Path(k) / "run/results").exists() and (Path(k) / "config.mk").exists()
    finally:
        shutil.rmtree(k)
