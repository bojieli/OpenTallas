#!/usr/bin/env python3
"""Verify source copies and inherited finite static records; never compile/generate."""
import argparse,gzip,hashlib,json
from pathlib import Path
p=Path(__file__).resolve().parent
for r in json.loads((p/'sources.json').read_text()):
 b=(p/r['copy']).read_bytes()
 assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'],r['path']
m=json.loads((p/'model.json').read_text())
b=gzip.decompress((p/'source/7e5150af5__results__arch__qwen_programme_store_1019__table_manifest.json.gz').read_bytes())
assert hashlib.sha256(b).hexdigest()==m['static_assets']['manifest_uncompressed_sha256']
j=json.loads(b);assert len(j['stages'])==36
counts=dict(prog_all_users=0,btab=0,crom=0)
for st in j['stages']:
 assert len(st['slices'])==12
 for sl in st['slices']:
  assert len(sl['prog_users'])==4 and all(len(x)==6 for x in sl['prog_users'])
  counts['prog_all_users']+=sum(map(len,sl['prog_users']))
  counts['btab']+=len(sl['btab']);counts['crom']+=len(sl['crom'])
assert counts==m['static_assets']['valid_record_counts_all36']
cp=json.loads((p/'source/7e5150af5__results__arch__qwen_programme_store_1019__checkpoint__checkpoint_compare.json').read_text())
assert cp['manifest_sha256']==hashlib.sha256(b).hexdigest() and cp['verdict']=='PASS'
assert len(cp['layers'])==36 and all(x['verdict']=='PASS' for x in cp['layers'])
r=json.loads((p/'producer_recovery.json').read_text());assert len(r)==18 and all(x['match'] for x in r)
assert sum(m['state']['loader_each']['enumeration'].values())==1101
print('EXTRACTION_PASS: pinned sources; exact c632 manifest; 36 inherited checkpoint PASS; 18 producer pins; source state counts')
ap=argparse.ArgumentParser();ap.add_argument('--extraction-only',action='store_true');a=ap.parse_args()
if not a.extraction_only:
 print('UNRESOLVED: constructor/table transport/installed first-use/L/E/QSLOT absent; full graph REFUSE')
 raise SystemExit(2)
