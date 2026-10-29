from pathlib import Path
import json,math,re
r=Path(__file__).parent
profiles=json.load(open(r.parent/'leaf_profiles.json'))
gbp=Path('/srv/opentallas-scratch/claude/wt/codex-head-gearbox-1029/results/head_gearbox_core_1029/plan/pins.json')
ep=[];cr=[]
def pin(name,x,y,layer,face):return dict(name=name,x=round(x,4),y=round(y,4),layer=layer,face=face)
# Retain the exact gearbox original bit/layer. Parent GB origin y60.48 is an
# M4/M6-preserving8.64multiple; no half-track center offset.
for p in json.load(open(gbp)):
 if p['face']=='E':ep.append(pin(p['name'],0,p['y']+60.48,p['layer'],'W'))
# Native credit port bijection to endpoint logical ports; no swizzle/no state.
pairs=[]
for i in range(552):pairs.append((f'in_data[{i}]',f'ep_in_d[{i}]','input'))
pairs += [('in_last','ep_in_d[552]','input'),('in_valid','ep_in_v','input'),('in_ready','ep_in_r','output')]
for i in range(552):pairs.append((f'out_data[{i}]',f'ep_out_d[{i}]','output'))
pairs += [('out_last','ep_out_d[552]','output'),('out_valid','ep_out_v','output')]
for i in range(3):pairs.append((f'out_ready_v[{i}]',f'ep_out_r[{i}]','input'))
for direction,layer,step,off in [('input','M4',.048,.024),('output','M6',.064,.032)]:
 q=[p for p in pairs if p[2]==direction]
 for i,(en,cn,_) in enumerate(q):
  y=off+round((8.4+i*.336-off)/step)*step
  ep.append(pin(en,328.32,y+77.76,layer,'E'));cr.append(pin(cn,0,y,layer,'W'))
# Parent-facing native credit frame ports: exact553-bit data includes last.
for direction,layer,step,off,ports in [('input','M4',.048,.024,['lo_d','lo_v','li_r']),('output','M6',.064,.032,['li_d','li_v','lo_r'])]:
 names=[]
 for b in ports:names += [f'{b}[{i}]' for i in range(553)] if b.endswith('_d') else [b]
 for i,n in enumerate(names):cr.append(pin(n,112.32,off+round((8.4+i*.336-off)/step)*step,layer,'E'))
# Independent existing reset leaves remain distinct ports. Initial preparation
# places them on N; parent reset-tree/clock reviews must qualify these entries.
for pins,role,w,h in [(ep,'ep',328.32,362.88),(cr,'credit',112.32,207.36)]:
 rst=[]
 if role=='ep':rst=[f'rst_v[{i}]' for i in range(17)]+[f'mem_rst_n[{i}]' for i in range(176)]
 else:rst=['rst_in_n','rst_out_n']+[f'head_rst_n[{i}]' for i in range(35)]
 for i,n in enumerate(rst):pins.append(pin(n,.024+round((w/2-(len(rst)-1)*.336/2+i*.336-.024)/.048)*.048,h,'M5','N'))
 pins.append(pin('fault',w-8.664,h,'M5','N'))
 pins.append(pin('clk',.024+round((w/2-.024)/.048)*.048,h/2,'M5','interior'))
 expected={}
 if role=='ep':expected={k:v['width'] for k,v in json.load(open(r.parent/'native_cut/ep_context_mask.json')).items()}
 else:
  sv=(r.parents[2]/'rtl/dsrom_sys/s81_head/ot_s81hd_credit_native.sv').read_text()
  for _,wid,n in re.findall(r'(input|output) wire (\[[^]]+\] )?(\w+)',sv.split(');',1)[0]):expected[n]=int(re.search(r'\[(\d+):',wid)[1])+1 if wid else 1
 names={n if w==1 else f'{n}[{i}]' for n,w in expected.items() for i in range(w)}
 assert len(pins)==len(names) and {p['name'] for p in pins}==names,(role,len(pins),len(names),names-{p['name'] for p in pins})
 (r/f'{role}_pins.json').write_text(json.dumps(pins,indent=1)+'\n')
print('Prepared EP2607bits/credit2261bits; exact GB face and1112bit EP↔credit bijection; reset/clock review pending.')
