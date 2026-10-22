from pathlib import Path
import json,copy
s=Path('/home/ubuntu/scratch/codex-selected-su-minimum-1021/stage');r=json.load(open(s/'replay.json'));b=json.load(open(s/'slice/boundary.json'));m=json.load(open(s/'emit/manifest.json'))['records'][0];e=json.load(open(s/'emit/images/r037_su/record.json'))['expect'][0]
last={};drop=[]
for i,x in sorted(enumerate(r['events']),key=lambda v:(v[1].get('dom',''),v[1].get('cyc',0),v[0])):
 if x['k']!='D':continue
 key=x['dom'],x['port'];value=int(x['val'],16)
 if last.get(key,0)==value:drop.append(i)
 last[key]=value
assert len(drop)==6
base=[x for i,x in enumerate(r['events']) if i not in drop];vals=e['value'];data=sum((v or 0)<<(32*i) for i,v in enumerate(vals));numeric=dict(k='C',dom='serial',cyc=m['compiled_commit_serial'],port='vm:'+format(e['sector'],'x'),val=format(data,'064x'),mask='f'*64,rec=37,src='actual native VM SRAM check; four output words plus unchanged inactive neighbours')
faults=[x for x in b['outputs'] if 'fault' in x['name'].lower()];by={x['name']:x for x in faults};names=['su_SW0__fault','su_SW0__lg_fault','sucore_SW__fault','pgp_SW__fault','subr_SW__fault'];groups=[names,[x['name'] for x in faults if x['name'] not in names]]
for groupidx,names in enumerate(groups):
 q=copy.deepcopy(r);q['events']=copy.deepcopy(base)+[numeric.copy()]
 if groupidx==1:q['events'].append(dict(numeric,cyc=numeric['cyc']+64,src='retained native SRAM value through 64 more serial edges; no intervening producer'))
 for name in names:q['events'].append(dict(k='C',dom='serial',cyc=numeric['cyc']+80,port=name,val='0',mask=format((1<<by[name]['width'])-1,'x'),src='selected source sticky protocol fault must remain zero'))
 q['events'].sort(key=lambda x:(x.get('dom',''),x.get('cyc',0),x['k']));q['removed_redundant_holds']=[r['events'][i] for i in drop];q['policy']='Same immutable programmes and source inputs; only initial-zero/same-value holds removed under generated TB zero initialization. Explicit checks split across identical deterministic runs to fit preserved NEV553 binary.'
 assert sum(x['k']!='M' for x in q['events'])+1<=553
 name='checks_'+str(groupidx);(s/name).mkdir(exist_ok=True);(s/name/'replay.json').write_text(json.dumps(q,indent=2)+'\n')
 if groupidx==0:
  mutant=copy.deepcopy(q);pre=[x for x in mutant['events'] if x['k']=='M'];assert len(pre)==1;word=int(pre[0]['val'],16);pre[0]['val']=format((word&~0xffffffff)|0x3f800000,'064x');mutant['mutation']='First actual router input changed to FP32+1; expected comparison remains unchanged.';(s/'checks_mutant').mkdir(exist_ok=True);(s/'checks_mutant/replay.json').write_text(json.dumps(mutant,indent=2)+'\n')
 print(name,'checks',sum(x['k']=='C' for x in q['events']),'nonM',sum(x['k']!='M' for x in q['events']))
