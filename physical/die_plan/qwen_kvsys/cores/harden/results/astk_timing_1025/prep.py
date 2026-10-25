import re,sys,shutil
from pathlib import Path
src,out,mode=Path(sys.argv[1]),Path(sys.argv[2]),sys.argv[3]
sys.path.insert(0,str(Path(__file__).parent)); import astk_timing_regs as T
out.mkdir(parents=True,exist_ok=True)
for f in src.glob("*.sv"): shutil.copy(f,out/f.name)
for f in src.glob("*.v"): shutil.copy(f,out/f.name)
orig={}
for fn,m in [("qkd_astk_static_leaves.sv","qkd_astk_ctl_s"),("qkd_astk_leaves.sv","qkd_astk_zn"),("qkd_astk_zn_head_p.sv","qkd_astk_zn_head_p")]:
    t=(src/fn).read_text(); i=t.index("module "+m+" "); j=t.index("endmodule",i)+9
    orig[m]=t[i:j].replace("module "+m+" ","module "+m+"_o ",1)
T.apply_kit(out, mode=="mut")
(out/"orig_mods.sv").write_text("`timescale 1ns/1ps\n"+"\n".join(orig.values())+"\n")
