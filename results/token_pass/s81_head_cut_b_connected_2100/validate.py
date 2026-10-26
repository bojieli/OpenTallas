#!/usr/bin/env python3
"""Validate collected replay evidence without compiling or replaying RTL."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def require(ok, why):
    if not ok: raise ValueError(why)

source=json.loads((R/'source/source_identity.json').read_text())
verified=json.loads((R/'source/verified_source_and_inputs.json').read_text())
require(len(source['files'])==verified['source_files']==903,'903 source identities required')
require(not verified['mismatches'],'staged source identity mismatch')
for name in ('a.json','rec.hex'):
    require(sha(R/'raw'/name)==verified['extra_inputs']['out/'+name]['sha256'],'CUT-A continuity: '+name)
a=json.loads((R/'raw/a.json').read_text())
require(a['pass_']==a['tiles']==253,'CUT-A 253/253 prerequisite')
result=json.loads((R/'raw/result.json').read_text())
cases=result['cases']
for name, verdict in [('a','PASS'),('a_mut','FAIL'),('b','PASS'),('b_mut_rec','FAIL'),('b_mut_slice','FAIL')]:
    require(cases.get(name,{}).get('verdict')==verdict,'missing or incorrect '+name+' verdict')
require(result['ok'] is True,'original head-cut reporter did not pass')
require(cases['b']['face_ok']==253 and cases['b']['face_fail']==0,'253 exact connected input faces required')
for name, verdict in [('b','PASS'),('b_mut_rec','FAIL'),('b_mut_slice','FAIL')]:
    log=(R/'raw'/f'{name}.log').read_text()
    require(re.search(r'^'+verdict+r' head_die',log,re.M) is not None,'original log verdict '+name)
    require(not re.search(r'^PASS head_die',log,re.M) if verdict=='FAIL' else not re.search(r'^FAIL head_die',log,re.M),'conflicting log verdict '+name)
    require((R/'raw'/f'{name}.exit').exists(),'original process exit record '+name)
gold=json.loads((R/'inputs/golden.json').read_text())
match=re.search(r'^PASS head_die token (\d+) bits ([0-9a-fA-F]+)',(R/'raw/b.log').read_text(),re.M)
require(match is not None and int(match[1])==gold['token']['row'] and int(match[2],16)==int(gold['token']['bits'],16),'actual connected token differs from golden')
identity=json.loads((R/'build/binary_runtime_identity.json').read_text())
require(not identity['source_mismatches'],'final source mismatch')
require(identity['source_identity_sha256']==sha(R/'source/source_identity.json'),'source manifest changed')
require(identity['extra_inputs']==verified['extra_inputs'],'tool, bind, image or CUT-A input changed during run')
for name in ('b','b_mut_slice'):
    recorded=(R/'raw'/f'binary_{name}.sha256').read_text().split()[0]
    require(recorded==identity['binaries'][name]['sha256'],'binary identity continuity '+name)
    build=(R/'build'/('obj_'+name)/'Vtb_s81hd_diecut__verFiles.dat').read_text()
    require('OT_S81HD_CTL_MUT_SLICE' in build if name=='b_mut_slice' else 'OT_S81HD_CTL_MUT_SLICE' not in build,'selected slice mutant build define '+name)
    require(identity['runtime'][name]['libraries'],'runtime library identities '+name)
preflight=(R/'raw/preflight_missing_autoload/build_b.log').read_text()
require('ot_s81_kp4_dec' in preflight and '%Error' in preflight,'original missing-autoload failure not preserved')
receipt=dict(schema='opentallas.s81.connected_head_evidence.v1',ok=True,
 scope='CUT-A full per-tile arithmetic plus CUT-B connected bound die with CUT-A replayed bundle output faces; not full-token, native pipeline or physical qualification',
 source_files=903,tiles=253,exact_input_faces=253,token=gold['token'],cycles=cases['b']['cycles'],
 mutants={k:cases[k] for k in ('a_mut','b_mut_rec','b_mut_slice')},
 binaries=identity['binaries'],original_result_ok=result['ok'],original_preflight_failure_preserved=True,
 hashes={str(p.relative_to(R)):sha(p) for directory in ('raw','source','inputs','build') for p in sorted((R/directory).rglob('*')) if p.is_file()})
(R/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('PASS connected head evidence: 253 exact input faces, correct token, and three causal mutants; scoped CUT evidence only')
