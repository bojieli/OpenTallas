import pathlib,json,hashlib,re,datetime
A=pathlib.Path(__file__).resolve().parent;B=A.parent;R=B/'failed_resume_1019';OLD=B/'original_verified_1019'
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
flat=lambda d:{c:dict(r,host=host) for host,rows in d.items() for c,r in rows.items() if isinstance(r,dict)}
orig=flat(load(OLD/'original_verified_receipts.json'));reuse=flat(load(A/'reuse_verified_receipts.json'));corr=flat(load(A/'corrected_verified_receipts.json'))
proposal=load(R/'view_manifest_proposal.json');expected=set(proposal['corrected_cells'])
# Keep every expected row, including not yet admitted rows; never relabel absence as PASS.
corr={c:corr.get(c,{'status':'INCOMPLETE_NOT_LAUNCHED_OR_NOT_COLLECTED'}) for c in sorted(expected)}
clients={}
for c,r in corr.items():
 p=R/(c+'.collect2.receipt.json');log=R/(c+'.collect2.client.log')
 if (R/(c+'.collect2.execution.json')).exists():
  receipt=load(p) if p.exists() else None;text=log.read_text(errors='replace') if log.exists() else ''
  clients[c]={'receipt':receipt,'terminal_RAN_exit0':bool(re.search(r'RAN.*exit[ =]0',text)),'log_sha256':h(log) if log.exists() else None,'receipt_sha256':h(p) if p.exists() else None}
  r['durable_client']=clients[c]
 else:r['client_evidence']='Existing artifacts independent of absent/orphaned original client; do not invent RAN rc'
 r['native_qualified']=False;r['PG_binding']='OPEN_HOLD';r['macro_area']='UNKNOWN_NOT_ZERO'
assert len(clients)==9,('durable client inventory',len(clients))
receipts={**{c:dict(r,receipt_group='reuse22') for c,r in reuse.items()},**{c:dict(r,receipt_group='original39') for c,r in orig.items()},**{c:dict(r,receipt_group='corrected18') for c,r in corr.items()}}
assert len(orig)==39 and len(reuse)==22 and len(corr)==18 and len(receipts)==79
views=load(B/'vplan_a/views.json');mapping={}
for c,v in views.items():
 r=receipts.get(c)
 if r:
  top=r.get('top','v16w_'+c);out=r.get('output');m=load(A/'reuse_metadata.json').get(c,{})
  if r['receipt_group']=='reuse22':out=m.get('remote');top=m.get('actual_top',top)
  mapping[c]={'receipt_group':r['receipt_group'],'host':r.get('host'),'output':out,'tt':out+'/'+top+'_synth_tt.lib' if out else None,'ff':out+'/'+top+'_synth_ff.lib' if out else None,'native_qualified':False,'PG_binding':'OPEN_HOLD'}
 else:
  mapping[c]={'receipt_group':'existing_routed_unbound_view','paths':{k:v.get(k) for k in ['lef','tt','ff','source','view_dir']},'native_qualified':False,'source_lineage_verified':v.get('source_lineage_verified',False),'PG_binding':'OPEN_HOLD'}
assert len(mapping)==142
failures={x['cell']:x['failure'] for x in load(R/'failed_only_resume.stable.json')['failed_only']}
assert len(failures)==18
rows=load(R/'failed_only_resume.stable.json')['failed_only']
drop_contract={x['cell']:{'row_env':x['row'][5],'DROP_empty':not x['row'][5].strip()} for x in rows}
assert len(drop_contract)==18 and all(x['DROP_empty'] for x in drop_contract.values())
GQ=proposal['old_successes']['ot_hgi_coll_gq_issue']['receipt']['rounds'];assert sum(x['rc']!=0 for x in GQ)==3
incomplete={c:r['status'] for c,r in corr.items() if r.get('status')!='PASS_SYNTH_ETM_IDENTITY_NOT_PHYSICAL'}
client_missing={c:r for c,r in clients.items() if not (r['receipt'] and r['receipt'].get('client_rc')==0 and r['terminal_RAN_exit0'])}
lineage=load(A/'corrected_source_lineage.json')
assert lineage and all(r['match'] for r in lineage.values()),'source lineage mismatch'
docker=load(A/'terminal_docker_audit.json')
assert set(docker)=={'ot-epyc4','ot-epyc6'} and all('error' not in r and not r['active_matching_output_mounts'] for r in docker.values()),'live/missing Docker audit'
manifest={'status':('COMPLETE_SOURCE_ARTIFACT_IDENTITY_REVIEW_REQUIRED_NO_S3' if not incomplete and not client_missing else 'INCOMPLETE_REVIEW_REQUIRED_NO_S3'),'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'6f783d0a1','inventory':{'jobs':79,'reuse':22,'original_successes':39,'failed_replays':18,'views':142},'receipts':receipts,'view_mapping':mapping,'DROP_contract':drop_contract,'preserved_original_failures':failures,'preserved_GQ_rounds':GQ,'incomplete_corrected':incomplete,'incomplete_durable_clients':client_missing,'required_next':'ROOT personal review and sole merger before separate next-stage authorization. All source/artifact receipts complete; PG/native/area qualification stays OPEN/HOLD. No S3/GEN/GO/adoption.','native_qualification':'OPEN_HOLD_ALL_ROWS_UNAUDITED_PG_BINDINGS_SOURCE_AND_AREA','source_inputs':{str(p):h(p) for p in [OLD/'original_verified_receipts.json',OLD/'original_source_lineage.json',OLD/'original_metadata_hashes.json',A/'corrected_verified_receipts.json',A/'reuse_verified_receipts.json',B/'vplan_a/views.json',B/'vplan_a/jobs.tsv',R/'failed_only_resume.stable.json',R/'input_audit_collect2.json',A/'corrected_source_lineage.json',A/'terminal_docker_audit.json',A/'terminal_client_receipts.json']}}
(A/'view_manifest_proposed_79x142.json').write_text(json.dumps(manifest,indent=2)+'\n')
print({'inventory':manifest['inventory'],'corrected_incomplete':incomplete,'durable_client_incomplete':list(client_missing),'corrected_complete':18-len(incomplete)})
