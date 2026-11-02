from pathlib import Path
import json,re,collections,hashlib
src=Path('/srv/opentallas-scratch2/claude/codex-s81-ves-2042/kit/run/results/asap7/kl_ot_s81sl_ve_s_cw1728/base/6_final.def');out=Path('/srv/opentallas-scratch2/claude/codex-ves-h12-prep-0524');masters={};nets={};instnets=collections.defaultdict(dict);mode=None;name=None;head='';reading=False;seed=set()
def finish():
 global name,head
 if name is None:return
 conn=re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)',head);nets[name]=conn
 for inst,pin in conn:
  if inst!='PIN':instnets[inst][pin]=name
  if pin not in ['CLK','VDD','VSS'] and (inst.startswith('u_rst.') or pin in ['RESETN','SETN']):seed.add(name)
 if name=='rst_n':seed.add(name)
 name=None;head=''
for line in src.open():
 s=line.strip()
 if s.startswith('COMPONENTS '):mode='comp';continue
 if s=='END COMPONENTS':mode=None;continue
 if s.startswith('NETS '):mode='nets';continue
 if s=='END NETS':finish();break
 if mode=='comp':
  m=re.match(r'-\s+(\S+)\s+(\S+)',s)
  if m:masters[m[1]]=m[2]
 elif mode=='nets':
  if s.startswith('- '):finish();name=s.split()[1];reading=True
  if reading:
   head+=' '+s.split('+',1)[0]
   if '+' in s:reading=False
  if ';' in s:finish()
selected=set();todo=list(seed)
while todo:
 n=todo.pop()
 if n in selected:continue
 selected.add(n)
 for i,pin in nets[n]:
  if pin not in ['Y','H','L','QN'] or i=='PIN':continue
  master=masters[i]
  if master.startswith(('DFF','DLL','ICG')):continue
  for port,nn in instnets[i].items():
   if port not in ['Y','H','L','QN','CLK','VDD','VSS']:todo.append(nn)
protected_instances={i for n in selected for i,pin in nets[n] if i!='PIN'}
p=out/'RESET_PRESERVE.json';p.write_text(json.dumps({'source_DEF':str(src),'DEF_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'native_components':len(masters),'native_signal_nets':len(nets),'seed_nets':sorted(seed),'protected_nets':sorted(selected),'protected_instances':sorted(protected_instances),'root':'rst_n','policy':'Preserve reset topology/wires/incident poses and masters; not a clock reclassification or reset cycle change'},indent=2));(out/'reset_nets.txt').write_text('\n'.join(sorted(selected))+'\n');print('reset seeds',len(seed),'allnets',len(selected),'incidentinst',len(protected_instances))
