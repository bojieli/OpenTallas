import pathlib,json,subprocess,hashlib,time
root=pathlib.Path.cwd();manifest=json.loads((root/'manifest_proposal.json').read_text());opts=manifest['snapshot']['options'];args=['python3','tools/die_port_bind.py','die.v','--top',manifest['snapshot']['top'],'--rtl-root','rtl','--no-macro-dirs','--pad-file','pads.json']
for path in sorted({x['path'] for x in manifest['snapshot']['selected_sources'].values()}):args += ['--rtl-file',str(root/path)]
for model in opts['allow_model']:args += ['--allow-model',model]
for k,v in opts['defines'].items():args += ['--define',k+('='+v if v else '')]
for master,port in opts['straps']:args += ['--strap',master+':'+port]
assert hashlib.sha256((root/'manifest_proposal.json').read_bytes()).hexdigest()=='2beccb8e65b7a62733fd9265ce4a0397192de0315202ba1a912c257f8ec5ddf2'
admit=args+['--unread-review','source_intent_review.json','--unread-contract','contract.json','--unread-manifest','manifest_proposal.json','--unread-manifest-sha256','2beccb8e65b7a62733fd9265ce4a0397192de0315202ba1a912c257f8ec5ddf2','--out','candidate.json']
t=time.time()
with open(root/'candidate.log','w') as out:r=subprocess.run(admit,stdout=out,stderr=subprocess.STDOUT)
receipt=dict(returncode=r.returncode,elapsed_s=time.time()-t,args=admit,manifest_sha256=hashlib.sha256((root/'manifest_proposal.json').read_bytes()).hexdigest(),checker_sha256=hashlib.sha256((root/'tools/die_port_bind.py').read_bytes()).hexdigest(),helper_sha256=hashlib.sha256((root/'tools/die_bind_unread_manifest.py').read_bytes()).hexdigest(),source_epoch='d517a76ad',qualified_die=False)
if (root/'candidate.json').exists():
 c=json.loads((root/'candidate.json').read_text());old=json.loads((root/'diagnostic.json').read_text());receipt.update(summary=c['summary'],summary_identical=old['summary']==c['summary'],reviewed_unread=c.get('reviewed_unread'),child_modules=c['child_closure']['modules'],child_unresolved=c['child_closure']['unresolved_children'])
(root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
raise SystemExit(0 if receipt.get('summary_identical') and r.returncode==1 else 1)
