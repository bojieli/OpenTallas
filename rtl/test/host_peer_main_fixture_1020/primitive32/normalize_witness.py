# Preserve Yosys raw WaveJSON (which may contain unescaped hierarchical names)
# and also emit a JSON-parser-safe copy; never alter solver data or verdict.
from pathlib import Path
import json,re,hashlib
for d in ("cold_invert_d","cold_hold_clk"):
 p=Path(d)/"cold_counterexample.json";raw=p.read_text()
 safe=re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})',r'\\\\',raw)
 obj=json.loads(safe);out=p.with_name("cold_counterexample.normalized.json")
 out.write_text(json.dumps(obj,indent=2)+"\n")
 out.with_suffix(".receipt.json").write_text(json.dumps(dict(raw_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),normalization="escape invalid hierarchical-name backslashes only",normalized_sha256=hashlib.sha256(out.read_bytes()).hexdigest()),indent=2)+"\n")
 print(d,"normalized raw WaveJSON syntax only",list(obj))
