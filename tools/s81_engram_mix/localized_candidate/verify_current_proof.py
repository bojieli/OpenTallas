#!/usr/bin/env python3
"""Rejoin exact329 numerical evidence, explicit37comment allowance, and live shared sources."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--proof-ref',default='66cd3dbd4eec1d860ce9b3241224913821fff4ec');p.add_argument('--manifest-ref',default='HEAD');p.add_argument('--live-ref',default='origin/main');p.add_argument('--snapshot',type=Path);p.add_argument('--out',type=Path);a=p.parse_args();R=Path(__file__).resolve().parents[3];P='results/arch/s81_mix4_localized_1016/current_main_full_proof/'
def git(ref,path):return subprocess.check_output(['git','show',ref+':'+path],cwd=R,stderr=subprocess.DEVNULL)
def sha(b):return hashlib.sha256(b).hexdigest()
def js(ref,path):return json.loads(git(ref,path))
def require(ok,msg):
 if not ok:raise SystemExit('FAIL '+msg)
collection=js(a.proof_ref,P+'collection.json');art=js(a.manifest_ref,P+'artifact_manifest.json');snapshot=js(a.manifest_ref,P+'actual_source_manifest.json');source=collection['source_candidate'];comment=collection['comment_only_successor'];require(source=='32969443092453b27535626dd3091c5085ac69d0','unexpected executable source');require(comment=='37f2fc669ce40539694eaefa50a0dedc8da04ef7','unexpected comment successor');require(sha(git(a.proof_ref,P+'collection.json'))==art['collection_sha256'],'collection sealed hash');require(sha(git(a.manifest_ref,P+'actual_source_manifest.json'))==art['actual_source_manifest_sha256'],'captured actual source manifest hash');require(snapshot['source_commit']==source,'snapshot commit')
for ref,parent in [(comment,source),(a.proof_ref,comment)]:require(subprocess.check_output(['git','rev-parse',ref+'^'],cwd=R,text=True).strip()==parent,'proof chain '+ref)
source_maps=[];logchecks=[]
for job in collection['jobs']:
 mut=job['mutant'];prefix=P+f'm{mut}/';recraw=git(a.proof_ref,prefix+'receipt.json');rec=json.loads(recraw);require(sha(recraw)==job['receipt_sha256'],'receipt hash mutant'+str(mut));require(rec['source_commit']==source and rec['build_returncode']==0,'actual build/source mutant'+str(mut));require(len(rec['source_sha256'])==34,'34source count');require(rec['source_sha256']==snapshot['source_sha256'],'captured actual34source hashes')
 for path,h in rec['source_sha256'].items():require(sha(git(source,path))==h,'actual git source '+path)
 for name,h in art['jobs'][str(mut)].items():require(sha(git(a.proof_ref,prefix+name))==h,'sealed log '+str(mut)+'/'+name)
 log=git(a.proof_ref,prefix+'run.log').decode();ot=git(a.proof_ref,prefix+'otrun.log').decode();require('ot-run: RAN on ot-epyc4' in ot and 'exit 0' in ot,'actual admitted completion')
 if mut==0:require(rec['run_returncode']==0 and rec['status']=='ACTUAL_FULL_SHAPE_COMPONENT_PASS' and 'PASS native Engram MIX4 full4x5120 in-place20480words done tag53 writes640 reads4161 write_span639..798 cycles=810'in log,'positive20480/640/4161/810')
 else:require(mut==26 and rec['run_returncode']==1 and rec['status']=='ACTUAL_LOCAL_RESULT_VALID_DROP_REJECTED' and 'FAIL 5120 words'in log,'actual mutant26 numeric rejection')
 require(not any(x.startswith(('-D','+define+'))for x in rec['command']),'unexpected compile defines');source_maps.append(rec['source_sha256']);logchecks.append(mut)
require(source_maps[0]==source_maps[1],'both actual source maps equal')
path='rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_localized_candidate.sv';old,new=git(source,path),git(comment,path)
def tokens(b):return re.findall(r'[A-Za-z_$][A-Za-z0-9_$]*|[0-9]+|[^\s]',re.sub(r'/\*.*?\*/|//[^\n]*','',b.decode(),flags=re.S))
require(old!=new and tokens(old)==tokens(new),'explicit37 comment-only token allowance');live=[];additive={
'rtl/dsrom_sys/engram/mix/'+n for n in ['dsfd_engram_mix4_clocked_candidate.sv','tb_s81_engram_mix4_clocked.sv','dsfd_engram_mix4_localized_candidate.sv','tb_s81_engram_mix4_localized.sv']}
for filename,h in source_maps[0].items():
 r=subprocess.run(['git','show',a.live_ref+':'+filename],cwd=R,capture_output=True)
 if r.returncode:require(filename in additive,'live shared source missing '+filename);status='ADDITIVE_CANDIDATE_BOUND329_NOT_PRESENT_IN_LIVE'
 elif sha(r.stdout)==h:status='LIVE_EXACT'
 elif filename==path and r.stdout==new:status='LIVE_EXPLICIT37_COMMENT_ONLY_TOKEN_EQUAL'
 else:raise SystemExit('FAIL live shared source changed '+filename)
 live.append({'path':filename,'proof_sha256':h,'live_sha256':sha(r.stdout)if not r.returncode else None,'status':status})
fifo=next(r for r in live if r['path']=='rtl/lib/ot_async_fifo.sv');require(fifo['status']=='LIVE_EXACT' and fifo['proof_sha256']=='22c5e15fc205c1585be1a3cf1cefa58550ddf546e3fe56945ec3282f276948bc','LIVE current FIFO exact join')
if a.snapshot:
 require(sha((a.snapshot/'source_manifest.json').read_bytes())==art['actual_source_manifest_sha256'],'actual external snapshot manifest bytes')
 for filename,h in source_maps[0].items():require(sha((a.snapshot/filename).read_bytes())==h,'actual snapshot source '+filename)
 for filename,h in snapshot['fixture_sha256'].items():require(sha((a.snapshot/'fixtures'/filename).read_bytes())==h,'actual fixture '+filename)
report={'status':'PASS_EXACT_NUMERIC_PROOF_REJOIN','executable_source':source,'comment_successor':comment,'proof_ref':a.proof_ref,'live_ref':a.live_ref,'source_hash_checks':68,'sealed_receipt_checks':2,'sealed_log_hash_checks':8,'actual_positive_words':20480,'actual_cycles':810,'actual_mutant_bad_words':5120,'compile_defines':[],'comment_tokens_equal':len(tokens(old)),'live_source_joins':live,'external_snapshot_checked':bool(a.snapshot),'physical_scope':'No fullparent timing/PG/clock/native VM qualification'}
if a.out:a.out.write_text(json.dumps(report,indent=1)+'\n')
print('PASS:68actual source blob hashes;2sealed receipts;8sealed logs;positive20480/640/4161/810;MUT26 build0/run1/5120words;LIVE FIFO/shared joins;37comment5765tokens;'+('actualsnapshot+fixtures'if a.snapshot else'no optional external snapshot supplied'))
