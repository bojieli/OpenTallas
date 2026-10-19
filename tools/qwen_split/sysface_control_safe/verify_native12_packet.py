#!/usr/bin/env python3
"""Verify the committed candidate and source-pinned compressed proof graphs."""
import gzip,hashlib,json
from pathlib import Path
from check_graph import check
from check_emitted import check as check_emitted
p=Path('results/rtl/sysface_native12_1019');source=Path('rtl/qwen_split/generated/qfd_sys_face_control_safe_native12_1019.sv')
for profile in ['cold','legacy']:
 q=p/profile;r=json.loads((q/'receipt.json').read_text())
 raw=gzip.decompress((q/'original.json.gz').read_bytes());assert hashlib.sha256(raw).hexdigest()==r['source_graph_sha256']
 original=json.loads(raw);candidate=json.loads(gzip.decompress((q/'graph.json.gz').read_bytes()))
 proof=check(original,candidate,r);(q/'graph_proof.json').write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n');print(profile,json.dumps(proof,sort_keys=True))
 for name,h in r['manifest']['source_sha256'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,'source changed: '+name
 if profile=='cold':
  assert hashlib.sha256(source.read_bytes()).hexdigest()==r['emitted_sha256']
  compiled=json.loads(gzip.decompress((q/'roundtrip.json.gz').read_bytes()))
  emitted=check_emitted(candidate,compiled,source.read_text());assert emitted==json.loads((q/'emitted_proof.json').read_text())
print('SYSFACE_NATIVE12_COMMITTED_PACKET_PASS source hashes; structural induction; emitted RTL; actual generic FF/pin census')
