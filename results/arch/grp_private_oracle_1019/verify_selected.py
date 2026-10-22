#!/usr/bin/env python3
import json,re,hashlib,sys
from pathlib import Path
R=Path(sys.argv[1]);C=json.loads(Path(sys.argv[2]).read_text());out={}
for n,v in C.items():
 p=R/v['path'];t=p.read_text()
 if n.startswith('ot_sram_'):b=t
 else:
  m=re.search(r'(?ms)^\s*module\s+('+re.escape(n)+r')\b(.*?^\s*endmodule\b)',t)
  b='module '+m.group(1)+m.group(2)
 sha=hashlib.sha256(b.encode()).hexdigest();out[n]=dict(match=sha==v['sha256'],sha256=sha)
print(json.dumps(out,indent=2));assert all(v['match'] for v in out.values())
