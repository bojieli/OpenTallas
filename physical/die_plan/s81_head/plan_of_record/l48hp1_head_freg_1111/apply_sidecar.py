#!/usr/bin/env python3
"""apply_sidecar.py PREP_DIR SIDECAR.json[.gz]: put the event's bind sidecar into a prepared dir (prepare_cut.py output) and refresh
wave_prepare.json sidecar_sha256 (head_wave_kit_rtl export refuses a changed sidecar otherwise).  Run before republish.py."""
import gzip, hashlib, json, sys
from pathlib import Path
prep = Path(sys.argv[1]); src = Path(sys.argv[2])
raw = gzip.open(src).read() if src.suffix == ".gz" else src.read_bytes()
(prep / "source_sidecar.json").write_bytes(raw)
w = json.loads((prep / "wave_prepare.json").read_text())
w["sidecar_sha256"] = hashlib.sha256(raw).hexdigest()
(prep / "wave_prepare.json").write_text(json.dumps(w, indent=1) + "\n")
print("sidecar sha256", w["sidecar_sha256"])
