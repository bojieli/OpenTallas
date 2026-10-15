#!/usr/bin/env python3
"""Actual Machine rawSC fixture and independent production-programme mutants.

Reuses the already-built actual producer binary without recompilation. Mutants
change real command/IO SRAM payloads, leaving expected answers unchanged.
"""
import argparse,json,shutil,sys
from pathlib import Path
from make_p_machine_fixture import generate
from make_p_producer_calendar import AUX,IO,packed


def unpack(word,layout):
    fields={};shift=0
    for name,width in layout:
        fields[name]=(word>>shift)&((1<<width)-1);shift+=width
    return fields


parser=argparse.ArgumentParser();parser.add_argument('--canonical-cases',type=Path,required=True)
parser.add_argument('--sfu-tools',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
a=parser.parse_args();sys.path.insert(0,str(a.sfu_tools))
from sfu_control_image import unpack as sfu_unpack,pack as sfu_pack
oracle=a.out/'oracle';generate(oracle,0x3d3504f3)
cases=a.out/'cases';cases.mkdir(parents=True,exist_ok=True)
for rows in (128,640):
    target=cases/f't{rows}_directed'
    shutil.copytree(a.canonical_cases/f't{rows}_h00',target,dirs_exist_ok=True)
    source=oracle/f't{rows}_h00'
    raw=[int(x,16) for x in (source/'raw_sc.hex').read_text().split()]
    (target/'raw_sc_sectors.hex').write_text(''.join(f'{sum(raw[8*s+w]<<(32*w) for w in range(8)):064x}\n' for s in range(rows//8)))
    for kind in ('mb','se','e','eb'):
        shutil.copyfile(source/f'expected_{kind}.hex',target/f'expected_{kind}.hex')
    shutil.copyfile(source/'expected_scaled_sc.hex',target/'expected_scaled.hex')
base=cases/'t640_directed'
for kind in ('max','sum','exp','rne'):
    target=cases/f'mutant_{kind}';shutil.copytree(base,target,dirs_exist_ok=True)
    if kind in ('max','sum'):
        words=[]
        for text in (target/'aux.hex').read_text().split():
            fields=unpack(int(text,16),AUX)
            if fields['command_v'] and fields['command_op']==(3 if kind=='max' else 1):fields['source_word']=0
            words.append(packed(fields,AUX))
        (target/'aux.hex').write_text(''.join(f'{w:046x}\n' for w in words))
    elif kind=='exp':
        words=[]
        for text in (target/'arithmetic.hex').read_text().split():
            fields=sfu_unpack(int(text,16))
            if fields['ci_sfu']==1:fields['ci_sfu']=0
            if fields['cs_sfu']==1:fields['cs_sfu']=0
            words.append(sfu_pack(fields))
        (target/'arithmetic.hex').write_text(''.join(f'{w:0436x}\n' for w in words))
    else:
        words=[]
        for text in (target/'io.hex').read_text().split():
            fields=unpack(int(text,16),IO);fields['drain_round_bf16']=0
            words.append(packed(fields,IO))
        (target/'io.hex').write_text(''.join(f'{w:0118x}\n' for w in words))
e=[int(x,16) for x in (base/'expected_e.hex').read_text().split()]
eb=[int(x,16) for x in (base/'expected_eb.hex').read_text().split()]
(a.out/'scope.json').write_text(json.dumps({'golden':'actual hgi_sim.machine.u_su_vop three canonical records','rawSC':'seed15101571 random finite moderate scores','scale_bits':'3d3504f3','full_head_dim':512,'T':[128,640],'head':0,'nontrivial_RNE_words_T640':sum(x!=y for x,y in zip(e,eb)),'mutants':['MAX actual source index0','SUM actual source index0','EXP disabled in actual arithmetic programme','RNE disabled in actual IO programme'],'native_whole_kernel_qualified':False},indent=2)+'\n')
