"""The physical seam and the native numeric ports are one interface."""
import copy
from types import SimpleNamespace as S
import qwen_rom_fulldie as F
import qwen_rom_fulldie_b3r2 as B


def setup(native=True):
    su=F.Master('qfd_sp_su64_sfu',100,100,7,'test');vm=F.Master('qfd_sp_vector_memory_par',100,100,7,'test')
    # Stale pre-seam aliases deliberately live on opposite edges.
    su.face('va0',2,'E','M4',20,1);su.face('vq0',4,'E','M4',30,1)
    vm.face('sa0',2,'W','M4',20,1);vm.face('sq0',4,'W','M4',30,1)
    def pins(m,k,w):
        out=[]
        for p,rs in getattr(m,'assigned_fragment_rects',{}).items():
            out.extend((f'{p}[{i}]',L,r) for i,(L,r) in enumerate(rs))
        cp=copy.copy(m);cp.ports={p:sp for p,sp in m.ports.items() if sp[0]!='xy'};cp.order=[p for p in m.order if p in cp.ports]
        return out+F.pin_rects(cp,k,w)
    v=S(SU_VM_NORTH=True,masters=lambda *a:copy.deepcopy({'qfd_sp_su64_sfu':su,'qfd_sp_vector_memory_par':vm}),pin_rects=pins)
    I=lambda n,m,y:S(name=n,master=m,x=0,y=y,w=100,h=100,orient='R0',domain='core')
    model=dict(insts=[I('sp_vector_memory','qfd_sp_vector_memory_par',0),I('sp_su64_sfu','qfd_sp_su64_sfu',100.024)],buses=[],
               port_join={'qfd_sp_su64_sfu':{'va0':('va',[0,1]),'vq0':('vq',[0,1,2,3])},
                          'qfd_sp_vector_memory_par':{'sa0':('sa',[0,1]),'sq0':('sq',[0,1,2,3])}})
    if native:model['native_graph_bind']={'qualified':False}
    return v,model


def test_native_seam_is_not_an_extra_raw_bus():
    v,m=setup();B._su_vm_bus(v,m,2,4)
    assert m['buses']==[]
    masters=v.masters(m,1)
    for a,b in [('va0','sa0'),('vq0','sq0')]:
        su,vm=masters['qfd_sp_su64_sfu'],masters['qfd_sp_vector_memory_par']
        pa=v.pin_rects(su,1,{p:s[1] for p,s in su.ports.items()})
        pb=v.pin_rects(vm,1,{p:s[1] for p,s in vm.ports.items()})
        pa=[(p,L,r) for p,L,r in pa if p.startswith(a+'[')]
        pb=[(p,L,r) for p,L,r in pb if p.startswith(b+'[')]
        assert len(pa)==len(pb) and pa
        for (_,la,ra),(_,lb,rb) in zip(pa,pb):
            assert la==lb=='M5'
            assert abs((ra[0]+ra[2])-(rb[0]+rb[2]))<1e-9
            assert ra[1]==0 and rb[3]==100
    assert 'sq' not in masters['qfd_sp_vector_memory_par'].ports and 'vq' not in masters['qfd_sp_su64_sfu'].ports


def test_historical_non_native_seam_keeps_raw_buses():
    v,m=setup(False);B._su_vm_bus(v,m,2,4)
    assert [b for b,*_ in m['buses']]==['su_vm_a','su_vm_q']
