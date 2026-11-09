#!/usr/bin/env python3
"""S81-SVCC-1: digest of the synthetic H16 svc job (test_lower_svc_h8.synth / run / digest) under a given lower_svc
module file -- run once on the unmodified origin/main module to pin H16 byte-identity:
  python3 -I tools/s81_dv/layer_prog/svc/h8_digest.py <lower_svc.py of the base> > tools/s81_dv/layer_prog/svc/h8_digest_base.json"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
src = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location('lower_svc_under_test', src)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
import test_lower_svc_h8 as T  # noqa: E402

out = {}
for t in (128, 256):
    j = T.synth(16, T=t, mod=mod)
    out[str(t)] = T.digest(j, T.run(j, mod=mod), mod=mod)
print(json.dumps(dict(out, module=str(src)), indent=1))
