#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,tarfile,os
os.chdir(Path(__file__).resolve().parent)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
expected='547f8188db0df993799272336b6745c1e2f56a8429107dc9d8d81d5d43bc4416'
assert sha('private/ot_host_if_pb2_observed_rc.sv')==expected
cases=[]
for c in range(26):
 t=Path(f'scheduler_run_case{c}.log').read_text();m=re.search(r'SCHED_PASS case=(\d+) edges=(\d+) issues=(\d+) rawdone=(\d+) commits=(\d+) writes=(\d+)',t)
 assert m and int(m[1])==c,(c,'missingPASS')
 cases.append(dict(zip(['case','edges','issues','rawdone','commits','writes'],map(int,m.groups()))))
mutants=json.loads(Path('scheduler_run_mutants.json').read_text());assert len(mutants)==6 and all(x['caught'] for x in mutants)
contracts=json.loads(Path('scheduler_run_contract.json').read_text());assert len(contracts)==4 and all(x['caught'] for x in contracts)
assert 'SCHED_PASS case=0' in Path('scheduler_run_default.log').read_text()
assert 'Verilator 5.050' in Path('scheduler_run_version.log').read_text()
assert 'QUEUE_OBSERVED peak=14 issues=14 current=14' in Path('scheduler_run_case21.log').read_text()
paths=sorted(p for p in Path('.').rglob('*') if p.is_file() and not any('obj' in part for part in p.parts) and p.suffix in {'.log','.json','.sv','.py','.sh','.txt'} and p.name!='scheduler_run_receipt.json')
files=[dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)) for p in paths]
with tarfile.open('scheduler_run_evidence.tar.gz','w:gz') as tf:
 for p in paths:tf.add(p,arcname=str(p),recursive=False)
receipt=dict(scope='SU functional scheduler COMPONENT_FIXTURE_ONLY; no native health/production calendar or physical claim',
 final_source_sha256=expected,bench_sha256=sha('scheduler_bench.sv'),original_sha256=sha('scheduler_run_original.sv'),
 fleet_host='ot-epyc6',fleet_unit='oth-ubuntu-3659500-1792445966',admission_gb=32,threads=8,disk_admission_gb=20,
 tool=Path('scheduler_run_version.log').read_text().strip(),fixture=dict(H=12,deadline=8,NSLOT=1,ENG_CTX=1,MODE=0,MU_OUT=0,NW=18,PLB=13,FMT=1,health_identity_domain='HOST_DESCRIPTOR_COMPONENT'),
 cases=cases,default_off_miter=dict(original_output_ports=57,trace='one complete healthy descriptor, prompt, engine, CQ and CSR counter read',verdict='PASS'),
 causal_mutants=mutants,contract_refusals=contracts,legal_queue_observed=14,nominal_queue=16,complete_reachability_bound_proven=False,
 open=['actual native TAG59 health/owner binding','production regional clocks, phase, H/deadline, full retirement plane','MU4','physical SRAM, reset, fanout and timing','exhaustive transaction/interleaving proof','raw POR in every DMA phase','exhaustive MSI payload/strobe checks','descriptor-error enqueue race between I_IDLE and real I_GO occupancy cut'],
 artifact_sha256=sha('scheduler_run_evidence.tar.gz'),files=files,
 object_bytes=sum(p.stat().st_size for p in Path('scheduler_run_obj').rglob('*') if p.is_file()))
Path('scheduler_run_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(cases=len(cases),mutants=len(mutants),contracts=len(contracts),source=expected,artifact_bytes=Path('scheduler_run_evidence.tar.gz').stat().st_size)))
