#!/usr/bin/env python3
"""Real Machine DEN+normalization oracle; SC/PV/SINK alone initialize DUT.

PV is an explicit external producer boundary, not an actual QK/PV proof.
"""
import argparse,json,sys,shutil
from pathlib import Path
import numpy as np
from make_p_machine_fixture import generate,Machine,Die,u_su_vop,MDesc,Rec,sut_decode,I
from make_p_producer_calendar import compile_head,IO,packed

def words(p):return np.array([int(x,16) for x in p.read_text().split()],dtype=np.uint32)
def write_words(p,w):p.write_text(''.join(f'{int(x):08x}\n' for x in w))
def sectors(p,w):
    assert len(w)%8==0
    p.write_text(''.join(f'{sum(int(w[k+j])<<(32*j) for j in range(8)):064x}\n' for k in range(0,len(w),8)))
def unpack(word):
    f={};shift=0
    for name,width in IO:f[name]=(word>>shift)&((1<<width)-1);shift+=width
    return f

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out',type=Path);ap.add_argument('--sfu-tools',type=Path,required=True);ap.add_argument('--canonical-p',type=Path);ap.add_argument('--canonical-pv',type=Path);ap.add_argument('--canonical-per-head',type=Path)
    a=ap.parse_args();oracle=a.out/'oracle';generate(oracle,0x3d3504f3)
    if a.canonical_p:
        for rows in (128,640):
            for h in range(16):
                o=oracle/f't{rows}_h{h:02d}'
                for src,dst,n in [('SC','raw_sc',rows),('MB','expected_mb',1),('SE','expected_se',1),('E','expected_e',rows),('EB','expected_eb',rows)]:
                    values=words(a.canonical_p/f'{src}{rows}.hex');write_words(o/f'{dst}.hex',values[h*n:(h+1)*n])
                shutil.copyfile(a.canonical_per_head/f't{rows}_h{h:02d}'/'expected_scaled.hex',o/'expected_scaled_sc.hex')
    rng=np.random.default_rng(15101572)
    for rows in (128,640):
        case=a.out/f't{rows}_h16';compile_head(rows,0,a.sfu_tools,case,normalize=True)
        raw=[];pv=[];sink=[];mb=[];se=[];eb=[];den=[];norm=[]
        for h in range(16):
            o=oracle/f't{rows}_h{h:02d}';raw.extend(words(o/'raw_sc.hex'));mb.extend(words(o/'expected_mb.hex'));se.extend(words(o/'expected_se.hex'));eb.extend(words(o/'expected_eb.hex'))
            d=Die(0,None);m=Machine([d]);V=lambda base,n,**kw:MDesc(base=base,n=n,**kw)
            values=(rng.integers(-65536,65536,512).astype(np.float32)/np.float32(1024)).astype(np.float32)
            values[:2]=[0.,-0.]
            sn=np.float32([-100,-4,-1,0,1,2,3,5,6,7,8,9,10,.5,4,20][h])
            if a.canonical_pv:
                values=words(a.canonical_pv/f'PV{rows}.hex')[h*512:(h+1)*512].view(np.float32)
                sn=words(a.canonical_pv/f'SINK{rows}.hex')[h:h+1].view(np.float32)[0]
            d.vm[0]=sn.view(np.uint32);d.vm[1]=mb[-1];d.vm[2]=se[-1];d.vm[512:1024]=values.view(np.uint32)
            def run(tag,desc,**fields):
                sut=sut_decode(0);sut.update(fields);u_su_vop(m,Rec('SU','VOP',sut=sut,desc=desc,tag=tag),0)
            run('attend.den',{'A':V(0,1),'B':V(1,1,ibcast=1),'C':V(2,1,ibcast=1),'O':V(3,1)},ad=I.AD_NEGB,sfu=I.SFU_EXP,e1=I.E1_ADDC,dst=I.DST_VM)
            run('attend.norm',{'A':V(512,512),'B':V(3,512,ibcast=1),'O':V(2048,512)},m1=I.M1_DIVB,rnd=1,dst=I.DST_VM)
            sink.append(d.vm[0]);pv.extend(d.vm[512:1024]);den.append(d.vm[3]);norm.extend(d.vm[2048:2560])
        sectors(case/'raw_sc_sectors.hex',raw);sectors(case/'raw_pv_sectors.hex',pv);sectors(case/'sink_sectors.hex',sink)
        for name,data in [('mb',mb),('se',se),('eb',eb),('den',den),('norm',norm)]:write_words(case/f'expected_{name}.hex',data)
        for src,dst in [('expected_scaled_sc','expected_scaled'),('expected_e','expected_e')]:shutil.copyfile(oracle/f't{rows}_h15'/f'{src}.hex',case/f'{dst}.hex')
        model=json.loads((case/'calendar.json').read_text());model.update(heads=16,external_starts=1,rawPV_actual_producer_bound=False,dut_initialization_only=['rawSC','rawPV','SINK']);(case/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    for mutant in ('omit_se','bypass_div','disable_rne'):
        src=a.out/'t640_h16';dst=a.out/f'mutant_{mutant}';shutil.copytree(src,dst,dirs_exist_ok=True)
        # Mutate real arithmetic programme fields by re-encoding literal rows.
        sys.path.insert(0,str(a.sfu_tools));from sfu_control_image import FIELDS
        field={'omit_se':'cs_e1','bypass_div':'cm_m1','disable_rne':'co_rnd'}[mutant]
        shift=0
        for name,width in FIELDS:
            if name==field:break
            shift+=width
        else:raise ValueError(field)
        data=[]
        for word in (dst/'arithmetic.hex').read_text().split():
            w=int(word,16)
            # Only this opcode occurs in normalization tail (P co_rnd is0).
            value=(w>>shift)&((1<<width)-1)
            if (mutant=='omit_se' and value==2) or (mutant=='bypass_div' and value==4) or (mutant=='disable_rne' and value==1):w&=~(((1<<width)-1)<<shift)
            if mutant=='bypass_div':
                off=0
                for n,bits in FIELDS:
                    if n=='cp_m1':
                        if (w>>off)&7==4:w&=~(7<<off)
                        break
                    off+=bits
            data.append(w)
        (dst/'arithmetic.hex').write_text(''.join(f'{w:0436x}\n' for w in data))
if __name__=='__main__':main()
