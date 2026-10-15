#!/usr/bin/env python3
"""Full persistent H16 state reuse with distinct actual Machine head vectors."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from make_p_machine_fixture import generate
from make_p_producer_calendar import IO,packed

def unpack(word,layout):
    fields={};shift=0
    for name,width in layout:
        fields[name]=(word>>shift)&((1<<width)-1);shift+=width
    return fields

p=argparse.ArgumentParser();p.add_argument('--per-head-cases',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();oracle=a.out/'oracle';generate(oracle,0x3d3504f3)
flat=a.out/'flat';flat.mkdir(parents=True,exist_ok=True)
for rows in (128,640):
    for src,dst in [('raw_sc','SC'),('expected_mb','MB'),('expected_se','SE'),('expected_e','E'),('expected_eb','EB')]:
        (flat/f'{dst}{rows}.hex').write_text(''.join((oracle/f't{rows}_h{h:02d}'/f'{src}.hex').read_text() for h in range(16)))
subprocess.run([sys.executable,str(Path(__file__).with_name('prepare_p_h16_loop_cases.py')),'--fixture',str(flat),'--per-head-cases',str(a.per_head_cases),'--out',str(a.out/'cases')],check=True)
for rows in (128,640):
    for src,dst in [('expected_scaled_sc','expected_scaled'),('expected_e','expected_e')]:
        shutil.copyfile(oracle/f't{rows}_h15'/f'{src}.hex',a.out/'cases'/f't{rows}_h16'/f'{dst}.hex')
base=a.out/'cases'/'t640_h16';mut=a.out/'cases'/'mutant_rne';shutil.copytree(base,mut,dirs_exist_ok=True)
words=[]
for word in (mut/'io.hex').read_text().split():
    fields=unpack(int(word,16),IO);fields['drain_round_bf16']=0;words.append(packed(fields,IO))
(mut/'io.hex').write_text(''.join(f'{w:0118x}\n' for w in words))
e=[int(x,16) for x in (flat/'E640.hex').read_text().split()];eb=[int(x,16) for x in (flat/'EB640.hex').read_text().split()]
(a.out/'scope.json').write_text(json.dumps({'source':'actualMachine canonical3records, seed15101571, fullhead_dim512 scale3d3504f3','heads':16,'profiles':[128,640],'external_starts_per_profile':1,'host_reconfiguration_between_heads':0,'T640_nontrivial_RNE_words':sum(x!=y for x,y in zip(e,eb)),'initialization_only':'rawSC','expected_only':['MB','SE','scaledSC','rawE','EB'],'native_whole_kernel_qualified':False,'physical_qualified':False,'production_qualified':False},indent=2)+'\n')
