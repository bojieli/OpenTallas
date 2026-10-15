#!/usr/bin/env python3
"""Immutable source/output hashes for remote fixed-calendar receipts."""
import argparse,datetime,hashlib,json,pathlib,shutil,socket
p=argparse.ArgumentParser();p.add_argument('directory',type=pathlib.Path);a=p.parse_args();src=pathlib.Path(__file__).parent
shutil.copyfile(src/'g96_bridge_calendar.py',a.directory/'compiler.py')
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return dict(bytes=p.stat().st_size,sha256=h.hexdigest())
files={}
for name in ['calendar.json','expanded_uops.jsonl','expanded_bridge.jsonl','model.json','independent_audit.json','independent_bridge_audit.json','cause_analysis.json','compiler.py']:
 files[name]=digest(a.directory/name)
sources={n:digest(src/n) for n in ['g96_calendar.py','g96_bridge_calendar.py','audit_g96.py','audit_g96_bridge.py','analyze_g96.py','v2_layout_source.json']}
v=json.loads((a.directory/'calendar.json').read_text());summ=list(v['expanded_program_summary'].values())
r=dict(schema='hcoll.g96.immutable.calendar.receipt.v1',host=socket.gethostname(),created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,sources=sources,expanded_program=dict(owners=len(summ),distinct_words_min=min(x['distinct_expanded_words'] for x in summ),distinct_words_max=max(x['distinct_expanded_words'] for x in summ),active_words_min=min(x['active_words'] for x in summ),active_words_max=max(x['active_words'] for x in summ),counted_affine_compression='UNVERIFIED; distinct-word count is not a counted-program lower bound'),qualification='Candidate compiler/calendar proof only; native extra program/catalog join, physical relays, full FEC/board clock contract and native SU composition unqualified')
(a.directory/'manifest.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
