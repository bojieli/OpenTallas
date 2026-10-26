import hashlib,json,sys
from pathlib import Path
k=Path(sys.argv[1]);m=json.loads((k/"IMMUTABLE_COHORT.json").read_text())
for rel,expected in m["files"].items():
 actual=hashlib.sha256((k/rel).read_bytes()).hexdigest()
 if actual!=expected:raise SystemExit("NATIVE_COHORT_CHANGED "+rel)
print("NATIVE_COHORT PASS source/config/pins/netlist exact0890")

if (k/"FROZEN_SYNTH_CACHE.json").is_file():
 for rel,expected in json.loads((k/"FROZEN_SYNTH_CACHE.json").read_text())["files"].items():
  if hashlib.sha256((k/rel).read_bytes()).hexdigest()!=expected:raise SystemExit("FROZEN_SYNTH_CACHE_CHANGED "+rel)
 print("FROZEN_SYNTH_CACHE PASS original0890/Odb4e4d")
