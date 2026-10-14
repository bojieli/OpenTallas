#!/usr/bin/env python3
"""Run actual TP8 RTL on eight rank payloads. Expected is observer-only."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read_words(p):
 words=[line.strip() for line in p.read_text().splitlines() if line.strip()]
 for word in words:
  if len(word)!=128:raise ValueError(f'{p}: word must contain sixteen binary32 lanes (128 hex characters)')
  int(word,16)
 return words

def pack_identity(identity):
 fields=[('epoch',16,65535),('stage',6,37),('token',18,151935),('position',13,8191),('segment',6,63)]
 packed=0
 for name,width,limit in fields:
  value=identity[name]
  if type(value) is not int or not 0<=value<=limit:raise ValueError(f'invalid native59 {name}: {value}')
  packed=(packed<<width)|value
 return packed

def run(exe,ranks,out,words,identities,nmsg=1,mode=0,expected=None,gap=0,skew=0):
 if len(ranks)!=8 or mode not in (0,1) or words<1 or nmsg<1 or nmsg>4096 or not 0<=gap<=100 or skew<0 or nmsg*8*words>65536 or (mode==0 and words%2):raise ValueError('invalid real collective shape')
 if len(identities)!=nmsg:raise ValueError('one source accepted identity required per message')
 tags=[pack_identity(i) for i in identities]
 out.mkdir(parents=True,exist_ok=False);vec=out/'input';vec.mkdir()
 (vec/'identity.hex').write_text('\n'.join(f'{tag:015x}' for tag in tags)+'\n')
 (out/'source_identity.json').write_text(json.dumps(identities,indent=2)+'\n')
 payload=[read_words(p) for p in ranks]
 if any(len(p)!=words*nmsg for p in payload):raise ValueError('rank file length differs from shape')
 ordered=[]
 for msg in range(nmsg):
  for g in range(8):
   rank=4*(g%2)+g//2
   ordered.extend(payload[rank][msg*words:(msg+1)*words])
 (vec/'part.hex').write_text('\n'.join(ordered)+'\n');(vec/'mode.hex').write_text((str(mode)+'\n')*nmsg)
 if expected:
  sums=read_words(expected)
  if len(sums)!=words*nmsg:raise ValueError('expected word count differs from shape')
  (vec/'sum.hex').write_text('\n'.join(sums)+'\n')
 args=[str(exe.resolve()),f'+VEC={vec.resolve()}',f'+OUT={out.resolve()}',f'+NMSG={nmsg}',f'+WORDS={words}',f'+CHECK={int(expected is not None)}',f'+TAGFILE={(vec/"identity.hex").resolve()}',f'+GAP={gap}',f'+SKEW={skew}']
 result=subprocess.run(args,capture_output=True,text=True);(out/'run.log').write_text(result.stdout+result.stderr)
 # Verilator $finish exits0 even FAIL; require explicit observed RTL PASS.
 ok=result.returncode==0 and any(line.strip()=='PASS' for line in result.stdout.splitlines())
 count=nmsg*words*(8 if mode else 1)
 for rank in range(8):
  p=out/f'rank{rank}.out';rows=[line.split() for line in p.read_text().splitlines()] if p.exists() else []
  if len(rows)!=count or any(len(r)!=8 or int(r[5])!=0 or int(r[7],16)!=tags[int(r[1])] for r in rows):ok=False
  if rows:(out/f'rank{rank}.hex').write_text('\n'.join(r[0] for r in rows)+'\n')
 receipt={'scope':'ACTUAL_NATIVE59_TP8_RTL_COLLECTIVE_NOT_FULL_TOKEN','ok':ok,'executable_sha256':digest(exe),'input_sha256':[digest(p) for p in ranks],'expected_observer_sha256':digest(expected) if expected else None,'words':words,'messages':nmsg,'mode':mode,'rank_to_bench_index':[2*(r%4)+r//4 for r in range(8)],'TAGW':59,'identity_fields':['epoch16','stage6','token18','position13','segment6'],'identity_sha256':digest(out/'source_identity.json'),'WT':0,'CT':0,'MEMM':0,'QMEM':0,'ICR':32,'LATU':14,'LATS':40,'BPC':3600,'core_period_fs':833334,'command':args,'output_sha256':[digest(out/f'rank{r}.hex') if (out/f'rank{r}.hex').exists() else None for r in range(8)]}
 (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
 return ok

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);p.add_argument('--ranks',type=Path,nargs=8,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--identities',type=Path,required=True);p.add_argument('--words',type=int,required=True);p.add_argument('--messages',type=int,default=1);p.add_argument('--mode',type=int,default=0);p.add_argument('--expected',type=Path);p.add_argument('--gap',type=int,default=0);p.add_argument('--skew',type=int,default=0);a=p.parse_args()
 raise SystemExit(0 if run(a.exe,a.ranks,a.out,a.words,json.loads(a.identities.read_text()),a.messages,a.mode,a.expected,a.gap,a.skew) else 1)
