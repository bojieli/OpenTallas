#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,tarfile,re
p=Path(__file__).resolve().parent
cases=[]
for c in range(26,30):
 t=(p/f'scheduler_descriptor_case{c}.log').read_text()
 m=re.search(r'DESC_PASS case=(\d+) pending_errors=(\d+) priority_collisions=(\d+) errors=(\d+) owner_events=(\d+) edges=(\d+)',t);assert m
 cases.append(dict(zip(['case','pending_edges','certification_priority_collisions','descriptor_errors','owner_events','edges'],map(int,m.groups()))))
for c in range(26):assert f'SCHED_PASS case={c}' in (p/f'scheduler_descriptor_baseline_run_case{c}.log').read_text()
assert 'SCHED_PASS case=0' in (p/'scheduler_descriptor_baseline_run_default.log').read_text()
mut=json.loads((p/'scheduler_descriptor_baseline_run_mutants.json').read_text());assert len(mut)==6 and all(x['caught'] for x in mut)
con=json.loads((p/'scheduler_descriptor_baseline_run_contract.json').read_text());assert len(con)==4 and all(x['caught'] for x in con)
newmut=json.loads((p/'scheduler_descriptor_mutant.json').read_text());assert newmut['caught']
old=p/'scheduler_descriptor_history_26a737'
assert 'DESC_FOREIGN_CONSUMED_REPORT' in (old/'scheduler_descriptor_case29.log').read_text()
files=[]
for f in sorted(p.rglob('*')):
 if not f.is_file() or any(x.endswith('_obj') or x=='obj' for x in f.relative_to(p).parts):continue
 if f.suffix not in ['.sv','.sh','.py','.json','.log','.txt','.sha256']:continue
 if f.name=='scheduler_descriptor_receipt.json':continue
 files.append(dict(path=str(f.relative_to(p)),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
r=dict(scope='private conditional SU scheduler component only',source_sha256=hashlib.sha256((p/'private/ot_host_if_pb2_observed_rc.sv').read_bytes()).hexdigest(),frozen_source_commit='8858a45b0',total_positive_cases=30,source_history=[dict(source_sha256='547f8188db0df993799272336b6745c1e2f56a8429107dc9d8d81d5d43bc4416',evidence_commit='c7dfb37e8',receipt='scheduler_run_receipt.json',scope='prior26case corpus; descriptor races explicitly open'),dict(source_sha256='26a737ff9c0e325baa45846abbcf4246fd93290f8f87b958f0070d8f065cde42',scope='D_ERR repaired; current26/27/28 pass; duplicate-tag29 causal failure archived'),dict(source_sha256='acf1208a092735df94d7555f76b19c9971b9ae4701e9dcbdc96c02a8ab5b14c2',source_commit='8858a45b0',scope='explicit owner-record;30positive cases plus57outputmiter and7mutants and4refusals')],fixture=dict(H=40,deadline=8,NSLOT=1,ENG_CTX=1,MODE=0,MU_OUT=0,NW=18,PLB=13,FMT=1),fleet=dict(host='ot-epyc6',verilator='5.050',positive_and_baseline_unit='oth-ubuntu-3665366-1792446237',descriptor_mutant_unit='oth-ubuntu-3667109-1792446284',historical_alias_failure_unit='oth-ubuntu-3664954-1792446209',remote_dir=str(p)),new_cases=cases,baseline_cases=26,default_original_outputs=57,baseline_mutants=mut,contract_refusals=con,descriptor_mutant=newmut,historical_alias_failure='26a737 source fails case29 DESC_FOREIGN_CONSUMED_REPORT',files=files)
(p/'scheduler_descriptor_receipt.json').write_text(json.dumps(r,indent=2)+'\n')
with tarfile.open(p/'scheduler_descriptor_evidence.tar.gz','w:gz') as a:
 for f in files:a.add(p/f['path'],arcname=f['path'])
 a.add(p/'scheduler_descriptor_receipt.json',arcname='scheduler_descriptor_receipt.json')
print(json.dumps(dict(archive_bytes=(p/'scheduler_descriptor_evidence.tar.gz').stat().st_size,files=len(files),source=r['source_sha256'],cases=cases)))
