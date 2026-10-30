import sys,json
from pathlib import Path
import argparse,hashlib,shutil
HERE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=a.out;out.mkdir(parents=True,exist_ok=True)
source=HERE.parent/'tok_hbm_1030/canonical_resident_cached/stream.json'
p=json.loads(source.read_text());runs=json.loads((HERE/'actual_window_runs.json').read_text())
assert runs and runs[0]['half']==0
for r in runs:
 m=p['records'][r['source_record']];start,end=m['hbm_range'];address=r['source_byte']
 assert m['kind']=='load' and start<=address<address+r['n']*4<=end
 assert r['destination_word']==m['vm_words'][0]+(address-start)//4
 assert r['stack']==3,'This fixture must not silently adopt another production backing'
def descriptor(src,dst,n):
 return(5<<2)|(src<<5)|(1<<77)|(1<<93)|(5<<95)|(dst<<98)|(1<<170)|(1<<186)|(n<<206)
def decode(sector):
 return {'slot':(((sector>>7)&1)<<5)|(((sector>>12)&7)<<2)|(sector&3)}
descs=[];counts=[];checks=[]
def payload(phase,leaf,group,slot,w):return(0x3e800000+phase*0x1000000+leaf*0x10000+group*0x1000+slot*8+w)&0xffffffff
for r in runs:
 local=r['source_byte']&((1<<35)-1);fixture=(2<<35)|local
 descs.append(descriptor(fixture,r['destination_word'],r['n']));counts.append(r['n']//8)
for phase in range(3):
 for r in runs:
  for i in range(r['n']//8):
   sector=((r['source_byte']&((1<<35)-1))>>5)+i;d=decode(sector);pc=((sector>>2)^(sector>>7)^(sector>>12))&31;assert pc<16
   data=sum(payload(phase,pc&7,(pc>>3)&1,d['slot'],w)<<(32*w)for w in range(8));vm=r['destination_word']+8*i;packet=(1<<280)|((vm>>3)<<264)|(data<<8)|255;checks.append(packet)
(out/'fixture_desc.mem').write_text(''.join(f'{x:057x}\n'for x in descs));(out/'fixture_steps.mem').write_text(''.join(f'{x:08x}\n'for x in counts));(out/'fixture_expected.mem').write_text(''.join(f'{x:071x}\n'for x in checks))
meta=dict(status='STACK2_MECHANISM_FIXTURE_NO_PRODUCTION_REBASE',actual_source_window_bundle=990,original_stack=3,fixture_stack=2,local_geometry_preserved=True,source_quad=2,window_row=runs[0]['row'],window_col=runs[0]['col'],descriptors_per_epoch=len(runs),packets_per_epoch=sum(counts),epochs=3,expected_packets=len(checks),expected_VMwords=len(checks)*8,VMquads=sorted({(r['destination_word']+i*8)>>16 for r in runs for i in range(r['n']//8)}),payload='deterministic opaqueU32 externalpin sectors, phase/leaf/group/slot/word distinct; not checkpoint compute results',holds=['No productionstack/addressreservation/calendaradoption','actualPHYsourceksharefillinterface starts at ownedleaf fillpins','actualVMbank slot6/physicalcommit notinstantiated; packetboundary checked'])
(out/'fixture.json').write_text(json.dumps(meta,indent=1)+'\n')
template=(HERE/'tb_provider_template.sv').read_text().replace('@@ND@@',str(len(runs))).replace('@@NP@@',str(len(checks))).replace('@@ROW@@',str(runs[0]['row'])).replace('@@COL@@',str(runs[0]['col']));(out/'tb_provider.sv').write_text(template);print(json.dumps(meta))
