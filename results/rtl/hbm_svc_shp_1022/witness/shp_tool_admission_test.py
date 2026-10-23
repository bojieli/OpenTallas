import sys,hashlib,shutil,tempfile,os
sys.path.insert(0,'tools/ref_tile'); sys.path.insert(0,'tools')
import async_gray_fifo_constraints as A
from pathlib import Path
srcs=['rtl/lib/ot_reset_sync.sv','rtl/lib/ot_rst_fanout.sv',A.SHP_SOURCE]
def run(root):
    t=tuple((p,hashlib.sha256((Path(root)/p).read_bytes()).hexdigest()) for p in srcs)
    A.elaborate.cache_clear()
    try: A.elaborate(str(root),'ot_hbm_svc_async_fifo_shp',t,(('WIDTH',279),('DEPTH',8),('SW',14))); return 'ADMITTED'
    except ValueError as e: return 'REFUSED: '+str(e)[:160]
print('v4d actual (SW 14):',run(Path('.').resolve()))
for name,old,new in [('leaf d=1',".d(wr_online),.rst_n(gw_l0)",".d(1'b1),.rst_n(gw_l0)"),
                     ('rs reset from rd_reset',"negedge gr_reset[s/GE]) if(!gr_reset[s/GE]) rs<=","negedge rd_reset) if(!rd_reset) rs<="),
                     ('leaf rst from both_reset',".rst_n_in(rd_reset),.d(rd_online)",".rst_n_in(both_reset),.d(rd_online)")]:
    d=Path(tempfile.mkdtemp())
    for p in srcs:
        (d/p).parent.mkdir(parents=True,exist_ok=True); shutil.copy(p,d/p)
    f=d/A.SHP_SOURCE; s=f.read_text(); assert old in s,name; f.write_text(s.replace(old,new))
    print(name,':',run(d.resolve()))
