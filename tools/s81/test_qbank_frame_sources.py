#!/usr/bin/env python3
"""Compare actual old/new qbank placement functions on every pinned q element."""
import ast,json,math,subprocess,sys
from pathlib import Path
from types import SimpleNamespace
from s81.qbank_frame_audit import lef,read_json
from s81.qbank_frame import require_bank_views,PINNED_VIEWS

def main():
    q=lef(Path(sys.argv[2]));plan=read_json(Path(sys.argv[1]));master='ot_v41_rom_elem_q_qxpq_w10'
    base=Path(sys.argv[2]).parent
    files={'dsfd_qbank_S':Path(sys.argv[3]),'dsfd_qbank_N':base/'dsfd_qbank_N.lef'}
    views={m:dict(job=PINNED_VIEWS[m][0],w=lef(fp)['size'][0],h=lef(fp)['size'][1],text=fp.read_text()) for m,fp in files.items()}
    require_bank_views(views)
    for change in ['job','w','h','text']:
        invalid={m:dict(v) for m,v in views.items()};v=invalid['dsfd_qbank_S'];v[change]=v[change]+('bad' if isinstance(v[change],str) else .048)
        try:require_bank_views(invalid)
        except AssertionError:pass
        else:raise AssertionError('stale/mismatched actual bank admitted: '+change)

    pm={k.split('|')[1]:v for k,v in plan['pins'].items() if k.startswith(master+'|')}
    rq=dict(name=master,w=q['size'][0],h=q['size'][1],pins={k:(r[0][0],r[0][1]) for k,r in q['pins'].items()})
    def ctx():
        def inst(name,master,x,y,w,h,**kw):return SimpleNamespace(name=name,master=master,x=x,y=y,w=w,h=h,**kw)
        return dict(QBANK_IN=('x0','x1','cfg','go'),QBANK_OUT=('r0','r1','st'),Q_X1B=False,PIN_ALIGN=True,BANK_PORTS={},BANK_H=6.48,GX=.432,GY=2.16,SHAVE=.024,real_ports_r8=lambda:{master:pm},QBANK_HARD_FRAME=False,up=lambda v,g:round(math.ceil(v/g-1e-8)*g,6),dn=lambda v,g:round(math.floor(v/g+1e-8)*g,6),Inst=inst)
    def extract(src,c):
        ns=[n for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and n.name in ['_q_port_face','_q_port_xc','_q_banks']]
        exec(compile(ast.Module(body=ns,type_ignores=[]),'actualqbankfunctions','exec'),c)
    a,b=ctx(),ctx();old=subprocess.check_output(['git','show','17b13fb06:tools/dsrom_s81_fulldie.py'],text=True);new=Path('tools/dsrom_s81_fulldie.py').read_text();extract(old,a);extract(new,b)
    proof=[];actual={i['name']:i for i in plan['insts']}
    for e in plan['insts']:
        if e['kind']!='q':continue
        args=(int(e['name'][1:]),e['x'],e['y'],rq,e['region']);o=a['_q_banks'](*args);n=b['_q_banks'](*args);assert o==n,e['name']
        for prior in o:
            assert all(abs(getattr(prior,k)-actual[prior.name][k])<1e-6 for k in ['x','y','w','h']),('source function differs from pinned generated slot',prior)
        b['QBANK_HARD_FRAME']=True;c=b['_q_banks'](*args);b['QBANK_HARD_FRAME']=False
        assert len(c)==2
        for oa,ca in zip(o,c):
            assert oa.name==ca.name and oa.x==ca.x
            h,dy=(25.896,-19.44) if oa.master.endswith('_S') else (8.616,0)
            assert abs(ca.h-h)<1e-7 and abs(ca.y-oa.y-dy)<1e-7,(oa,ca)
        proof.append(e['name'])
    print('QBANK_SOURCE PASS',len(proof),'q elements default identical;',2*len(proof),'candidate full nominal bank frames; actual LEF collision/pin replay separately uses unshaved dimensions')
if __name__=='__main__':main()
