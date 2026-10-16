from pathlib import Path
import json,gzip,subprocess
B=Path(__file__).resolve().parent;R='/home/ubuntu/wt/s81-vm-merge-0600';leaves=json.loads((B/'actual-pins-538/leaves.json').read_text())['leaves'];mods=json.load(gzip.open(B/'actual-pins-538/models.json.gz','rt'));cache={};joins={}
with gzip.open(B/'graph-native/pin_join.jsonl.gz','rt')as f:
 for line in f:
  d=json.loads(line)
  for c in d.get('consumers',[]):
   if c[0]>=0 and (c[1]in ['ck','clk','s_ck','t_ck']or c[1].startswith('ck_')):joins[tuple(c[:3])]=d['drivers']
rows=[]
for i,l in enumerate(leaves):
 key=(l['kit'],l['physical_cell'])
 if key not in cache:
  p=f'physical/ref_tile/{key[0]}/views/{key[1]}/insertion.json';cmd=['git','-C',R,'show','0ca4b7f37:'+p];r=subprocess.run(cmd,capture_output=True,text=True);ins=None
  if r.returncode==0:ins=json.loads(r.stdout)
  if l['path']=='dut.u_wfc.u_ret':
   p='/home/ubuntu/artifacts/s81-vm-0600/ret/views-final/dsfd_vm_wfc_return/insertion.json';ins=json.loads(Path(p).read_text())
  cache[key]=(p,ins)
 p,ins=cache[key]
 for port,v in l['ports'].items():
  if v['direction']=='input'and (port in ['ck','clk','s_ck','t_ck']or port.startswith('ck_')):
   m=mods[l['pin_source']]['pins'].get(port);rows.append(dict(path=l['path'],kit=l['kit'],clock_pin=port,physical_cell=l['physical_cell'],outline_um=l['outline_um'],clock_anchor_um=m['anchor_um']if m else None,clock_layer=m['anchor_layer']if m else None,parent_source=joins.get((i,port,0)),insertion_source=p,insertion=ins,native_status=l['native_status']))
out=dict(scope='Source-pinned per-hard-leaf clock pins, actual local geometry and insertion receipts. Each physical root requires die phi-minus-R delivery; inherited presence is not qualification.',leaf_clock_roots=len(rows),missing_clock_anchor=sum(not x['clock_anchor_um']for x in rows),missing_insertion=sum(x['insertion']is None for x in rows),roots=rows)
(B/'actual-pins-538/clock_manifest.json').write_text(json.dumps(out,indent=1)+'\n');print({k:v for k,v in out.items()if k!='roots'})
