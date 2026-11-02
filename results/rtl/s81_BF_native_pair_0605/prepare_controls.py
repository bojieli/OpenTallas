from pathlib import Path
import json
R=Path('/srv/opentallas-scratch2/claude/codex-ds-bf-native-pair-0605');B=R/'images';base=[(int(t),int(k),int(v,16))for t,k,v in(x.split()for x in(B/'actual_producer.txt').read_text().splitlines())]
for name in ['wrong_operand','wrong_date','wrong_class','wrong_status','late_accept','initial_GW_family0','wrong_write_bank']:
 d=R/name;d.mkdir(exist_ok=False)
 for p in B.iterdir():
  if p.name!='producer.txt':(d/p.name).symlink_to(p.resolve())
 ev=base[:]
 if name=='wrong_operand':text=(B/'wrong_operand_producer.txt').read_text()
 else:
  changes=0;out=[]
  for t,k,v in ev:
   if name=='wrong_date'and k==0 and ((v>>(47+94))&1):t+=1;changes+=1
   if name=='late_accept'and k==0 and ((v>>47)&1):t+=1;changes+=1
   if name=='initial_GW_family0'and k==0 and ((v>>(47+120))&1):v^=1<<(47+121);changes+=1
   if name=='wrong_write_bank'and k==0 and ((v>>(47+120))&1):v^=1<<(47+122);changes+=1
   if name=='wrong_class'and k==2 and ((v>>276)&1):v^=6;changes+=1
   out.append((t,k,v))
  if name!='wrong_status':assert changes==(64 if name=='wrong_class'else 1),(name,changes)
  text=''.join(f'{t} {k} {v:x}\n'for t,k,v in sorted(out))
 (d/'producer.txt').write_text(text)
(R/'controls.json').write_text(json.dumps(dict(wrong_operand='same genuine calendar and payload headers/dates, earlier normalize-scale placeholder BF values',wrong_date='one actual source calendar START command one edge late; independent original source-date oracle retained',late_accept='issuer accept GO one edge later, calendar START unchanged; admission slack probe, no predeclared negative verdict',wrong_class='64 actual gather packet header kind fields BF2→Q1; unchanged payload/dates; genuine producer family decoder/read-valid guard retained',initial_GW_family0='GW family BF→Q with initial parity0 is an identity probe: both native write-bank parity states reset0',wrong_write_bank='GW parity0→1 with unchanged phase/read tag0; native bank-read-valid guard retained',wrong_status='restores original fixture error by presenting nonselected Q {fault,busy}=11'),indent=2)+'\n')
