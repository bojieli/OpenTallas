from pathlib import Path
import json,numpy as np
b=Path('/srv/opentallas-scratch2/claude/codex-qc-crom-cal-1025');log=b/'representative/qk/run_qk_m0.log';out=Path('/srv/opentallas-scratch2/claude/codex-qca0-0719/actual_qk');out.mkdir(parents=True,exist_ok=True)
got={};beats=[];errors=[]
for line in log.read_text().splitlines():
 parts=line.split()
 if len(parts)!=3 or parts[1]!='S0DD':continue
 cycle=int(parts[0]);w=int(parts[2],16);kind=(w>>545)&3;mask=(w>>537)&255
 if not ((w>>547)&1):errors.append({'kind':'invalid_emitted_beat','cycle':cycle})
 for lane in range(8):
  if not (mask>>lane)&1:continue
  addr=(w>>(345+24*lane))&0xffffff;v=(w>>(89+32*lane))&0xffffffff;key=(kind,addr)
  if key in got:errors.append({'kind':'duplicate','key':key})
  got[key]=v
 beats.append({'cycle':cycle,'kind':kind,'mask':mask})
fx=np.load(b/'stgdie/fx/L0_qk.npz');res={}
for name,kind,n in [('q',0,512),('k',1,128),('v',2,128)]:
 vals=[got.get((kind,i)) for i in range(n)];missing=[i for i,v in enumerate(vals) if v is None]
 if missing:errors.append({'kind':'missing','role':name,'addresses':missing});continue
 (out/(name+'.hex')).write_text(''.join(f'{v:08x}\n' for v in vals))
 gold=np.asarray(fx['gold_'+name],dtype=np.float32).view(np.uint32).reshape(-1)
 bad=[i for i,(a,e) in enumerate(zip(vals,gold)) if a!=int(e)]
 res[name]={'actual_words':len(vals),'gold_words':int(gold.size),'mismatches':len(bad),'first_bad':bad[:4], 'first_cycle':min(x['cycle'] for x in beats if x['kind']==kind),'last_cycle':max(x['cycle'] for x in beats if x['kind']==kind)}
 if len(gold)!=n or bad:errors.append({'kind':'gold_mismatch','role':name,'addresses':bad})
summary={'source_log':str(log),'source_lowering':str(b/'representative/qk/lowering_qk.json'),'source_fixture':str(b/'stgdie/fx/L0_qk.npz'),'payload_source':'actual RTL S0DD output; golden used only for comparison','packing':'valid[547];kind[546:545];mask[544:537];addr[lane]bits345+24*lane+:24;fp32[lane]bits89+32*lane+:32;low89bitsunusedmetadata','order':'q.hex indexes0..511 by actual kind0 globalQ address; four128wide heads','beats':len(beats),'unique_elements':len(got),'roles':res,'errors':errors,'verdict':'PASS' if not errors else 'FAIL'}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));raise SystemExit(bool(errors))
