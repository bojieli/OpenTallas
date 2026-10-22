import concurrent.futures,json,pathlib,subprocess,hashlib,datetime
A=pathlib.Path(__file__).resolve().parent;B=A.parent;R=B/'failed_resume_1019'
M=json.loads((R/'view_manifest_proposal.json').read_text());CELLS=M['corrected_cells']
outputs={c:'/srv/opentallas-scratch/claude/hd4g/gen2e2/failed_resume_1019/'+c for c in CELLS}
outputs.update(ot_hgi_sfu_core_split3='/srv/opentallas-scratch/claude/hd4g/gen2e2/source_unique_d14c90171/sfu',ot_hbm_su_static_pgslice_lg__pv0='/srv/opentallas-scratch/claude/hd4g/gen2e2/source_unique_d14c90171/pgslice_correct_top')
def collect(host):
 cells=CELLS if host=='ot-epyc4' else [c for c in CELLS if c not in ['ot_hgi_sfu_core_split3','ot_hbm_su_static_pgslice_lg__pv0']]
 code='HELPER_EXPECTED='+repr(json.loads((R/'source_audit.json').read_text())['helper_sha256'])+'\nEXPECTED='+repr(json.loads((R/'expected_inputs.json').read_text()))+'\nCELLS='+repr(cells)+'\nOUTPUTS='+repr(outputs)+'\n'+(A/'audit_remote.py').read_text()
 try:
  p=subprocess.run(['ssh','-o','ConnectTimeout=8',host,'python3 -'],input=code,text=True,capture_output=True,timeout=110)
  return host,json.loads(p.stdout) if p.returncode==0 else {'collection_error':p.stderr}
 except Exception as e:return host,{'collection_error':str(e)}
result=dict(concurrent.futures.ThreadPoolExecutor(max_workers=3).map(collect,['ot-epyc4','ot-epyc5','ot-epyc6']))
(A/'corrected_verified_receipts.json').write_text(json.dumps(result,indent=2)+'\n')
print({h:{c:r.get('error',r.get('status')) if isinstance(r,dict) else r for c,r in rows.items()} for h,rows in result.items()})
