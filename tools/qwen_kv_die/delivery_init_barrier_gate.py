#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess
p=pathlib.Path.cwd(); src=p/'ot_qwen_xdelivery_init_barrier.sv';orig=src.read_text()
cases=[('disabled','tb_qwen_xdelivery_init_disabled',None,None,None),('controller', 'tb_qwen_xdelivery_init_barrier',None,None,None),('field_composition','tb_qwen_xdelivery_init_field',None,None,None),('field_live_mask_mutant','tb_qwen_xdelivery_init_field','FIELD_LIVE_MASK',None,'actual bank initialization fault'),('actual_bank','tb_qwen_xdelivery_init_bank',None,None,None),('barrier_bypass','tb_qwen_xdelivery_init_barrier','(&initialized)','1\'b1','dispatch before bank initialization'),('context_bypass','tb_qwen_xdelivery_init_barrier','bank_init_context[b*TOKEN_W+:TOKEN_W]!=held_context','1\'b0','stale initialization context escaped'),('version_bypass','tb_qwen_xdelivery_init_barrier','bank_init_version[b*32+:32]!=held_version','1\'b0','stale initialization version escaped')]
cases=cases+[('participant_bypass','tb_qwen_xdelivery_init_barrier','bank_init_participants[b*(TILES/BANKS)+:(TILES/BANKS)]!=participants[b*(TILES/BANKS)+:(TILES/BANKS)]',"1'b0",'wrong initialization participants escaped'),('early_receipt','tb_qwen_xdelivery_init_bank','assign init_v=ENABLE && pending && !fault;','assign init_v=ENABLE && !fault;','receipt before actual bank BEGIN'),('fault_receipt','tb_qwen_xdelivery_init_bank','assign init_v=ENABLE && pending && !fault;','assign init_v=ENABLE && pending;','receipt certified BEGIN/event collision'),('receipt_drop','tb_qwen_xdelivery_init_bank','if(init_v && init_ack) pending<=0;','if(init_v) pending<=0;','receipt not retained until ACK')]
r={'scope':'DEFAULT_OFF_INITIALIZATION_COMPONENT_NOT_PHYSICAL_OR_GLOBAL_PEER_BINDING','sources':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.glob('*.sv')},'cases':[]}
for name,top,old,new,expect in cases:
 text=orig;tb=p/(top+'.sv')
 if old=='FIELD_LIVE_MASK':
  field=tb.read_text();a='mp[0]<=held_participants[b*48+:48]';assert field.count(a)==1
  field=field.replace(a,'mp[0]<=offer_participants[b*48+:48]');tb=p/(name+'_tb.sv');tb.write_text(field)
 elif old:
  assert text.count(old)==1,(name,text.count(old));text=text.replace(old,new)
 f=p/(name+'.sv');f.write_text(text)
 b=subprocess.run(['iverilog','-g2012','-s',top,'-o',name+'.vvp','ot_qwen_xdelivery_lifetime.sv',str(f),str(tb)],capture_output=True,text=True)
 (p/(name+'.build.log')).write_text(b.stdout+b.stderr);assert b.returncode==0,b.stderr
 v=subprocess.run(['vvp',name+'.vvp'],capture_output=True,text=True,timeout=20);out=v.stdout+v.stderr;(p/(name+'.log')).write_text(out)
 if expect:assert v.returncode!=0 and expect in out,(name,out)
 else:assert v.returncode==0 and 'PASS ' in out,(name,out)
 r['cases'].append({'case':name,'exit':v.returncode,'output':out.strip(),'source_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'testbench_sha256':hashlib.sha256(tb.read_bytes()).hexdigest()});print('PASS '+name,flush=True)
(p/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
