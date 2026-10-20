import pathlib,json,hashlib,tarfile
out=pathlib.Path('/srv/opentallas-scratch/claude/qw-native59-terminal-1019')
for n in ['safe3','safe3b']:
 root=pathlib.Path('/srv/opentallas-scratch/claude/ref_gate/qfd_native59_dv_service_'+n+'-20261019-113209/src')
 m=json.loads(pathlib.Path('/tmp/qw-n59-'+n+'-manifest.json').read_text());rows={r['path']:r for r in m['files']};audit=[]
 with tarfile.open(out/(n+'.consumed_sources.tar.gz'),'w:gz') as t:
  for r in m['consumed']['paths']:
   p=root/r;h=hashlib.sha256(p.read_bytes()).hexdigest();a={'path':r,'sha256':h,'expected':rows[r]['sha256'],'match':h==rows[r]['sha256']};audit.append(a);t.add(p,arcname=r,recursive=False)
 (out/(n+'.consumed_audit.json')).write_text(json.dumps(audit,indent=2)+'\n')
 print(n,len(audit),all(x['match'] for x in audit))
