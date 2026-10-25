import numpy as np
from ft_knee_sites import allocate_bank_chain,spine
from tools.die_trial.legal_sites import RowAllocator

def alloc():
 return RowAllocator((4.32,4.32,1438.56,1222.56),cell_size=(1.404,.27),column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))

def case(a,b,fin,fout,depth):
 path,banks,stats,hops=allocate_bank_chain(alloc(),a,b,fin,fout,depth)
 # stations lie monotonically on the shared Manhattan spine (arclength targets may straddle a knee):
 # the summed Manhattan legs equal the end-to-end Manhattan length (no detour, no backtrack)
 assert abs(sum(float(abs(q-p).sum()) for p,q in zip(path,path[1:]))-float(abs(path[-1]-path[0]).sum()))<1e-3,path
 assert max(hops)<=403
 assert len(banks)+1>=depth
 return len(banks)+1

def main():
 y=np.linspace(6.144,116.516,514)
 a=np.column_stack((np.zeros(514),y));b=a.copy();b[:,0]=1442.88
 assert case(a,b,'W','E',4)==4,'unnecessary extra straight-path cycle'
 a=np.column_stack((np.full(514,1442.88),np.linspace(242.304,353.828,514)))
 b=np.column_stack((np.linspace(129.408,239.78,514),np.zeros(514)))
 assert case(a,b,'E','S',4)==4,'knee can relocate within outgoing window band without added cycle'
 a=np.column_stack((np.zeros(514),np.linspace(20,120,514)))
 b=np.column_stack((np.full(514,1442.88),np.linspace(300,400,514)))
 assert case(a,b,'W','E',4)>=5
 print('PASS3: straight depth preserved; mandatory L and Z knees; actual paired bits<=403um; exact rowlegal sites')
if __name__=='__main__':main()


def test_some_aligned_bits_keep_the_common_segment_topology():
    # One bit is straight, one needs a Z. Both must use the common station bands.
    import numpy as np
    from tools.die_plan.ft_knee_sites import allocate_bank_chain
    from tools.die_trial.legal_sites import RowAllocator
    a = np.array([[10., 1256.], [20., 1256.]])
    b = np.array([[10., 4.32], [30., 4.32]])
    alloc = RowAllocator((4.32,4.32,100.,1260.),cell_size=(1.404,.27),
                         column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
    path,banks,stats,hops = allocate_bank_chain(alloc,a,b,"N","S",4)
    assert len(banks) >= 3
    assert all(bank.shape == a.shape for bank in banks)
    assert max(hops) <= 403.
