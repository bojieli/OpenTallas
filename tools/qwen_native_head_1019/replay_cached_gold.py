"""Recheck frozen production logs against original golden without RTL reruns."""
import hashlib
import importlib.util
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("driver", root / "tools/qwen_native_head_1019/run_production.py")
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
B = driver.B
B.MU_NU, B.FACE = 4, 1
B.VFLAGS[:] = ["+define+OT_QFD_DV_SAFE_STORAGE", "-GSU_LT=1", "-GHD_W130=1"]
records = []

def cached(name, ev, work, mut, ncyc, n=2):
    assert mut == 0
    evfile, logfile = work / f"{name}.ev", work / f"{name}.log"
    # Preserve immutable events. Recreated stimulus must match before its log is used.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "events"
        ev.write(fresh)
        assert fresh.read_bytes() == evfile.read_bytes(), f"stimulus mismatch: {name}"
    out = {}
    for line in logfile.read_text().splitlines():
        if line.strip():
            c, nm, h = line.split()
            out.setdefault(nm, []).append((int(c) - B.RESET_WARM, int(h.replace("x", "0").replace("X", "0").replace("z", "0"), 16)))
    out["S0SC"] = [(c, B.conv48(w)) for c, w in out.get("S0SU", [])]
    out["S1SC"] = [(c, B.conv48(w)) for c, w in out.get("S1SD", [])]
    out["S1DD"] = out.get("S0DD", [])
    out["S1E"] = out.get("S1E", [])
    records.append({"name": name, "log_sha256": hashlib.sha256(logfile.read_bytes()).hexdigest(), "events_sha256": hashlib.sha256(evfile.read_bytes()).hexdigest()})
    return out

B.run_sim2 = cached
B.install()
verdicts = []
for bench in "acfgkqmone":
    ok, count, errs = B.BENCHES[bench](root / "out/positive/m0", 0)
    print(f"CACHED_GOLD {bench} {ok}/{count} errors={errs}")
    assert ok == count and not errs
    verdicts.append({"bench": bench, "ok": ok, "count": count, "errors": errs})
Path("cached_gold_receipt.json").write_text(json.dumps({"RTL_rerun": False, "stimulus_byte_match": True, "results": verdicts, "logs": records}, indent=2) + "\n")
