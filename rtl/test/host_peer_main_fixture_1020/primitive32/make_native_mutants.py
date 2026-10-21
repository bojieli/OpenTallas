from pathlib import Path
import re,json,hashlib,shutil
r=Path.cwd()
for d,mut in [("native_invert_d","invert_d"),("native_hold_clk","hold_clk")]:
 t=r/d;(t/"models").mkdir(parents=True,exist_ok=True)
 for f in ["original.v","qkd_hr_core_peer_n32.sv","canonical_ASR_normalized.v","canonical_DFF_normalized.v","macro_bb.v","run_peer_native.sh"]:shutil.copy2(r/f,t/f)
 shutil.copy2(r/"models/comb_models.v",t/"models/comb_models.v")
 shutil.copy2(r/"tb_peer_native_copycheck.sv",t/"tb_peer_native.sv")
 p=t/"qkd_hr_core_peer_n32.sv";s=p.read_text();hit=re.search(r"(?m)^.*\bu59981_c1 \(.*?\);$",s);assert hit
 old=hit.group()
 if mut=="invert_d":new,n=re.subn(r"\.D\(([^()]+)\)",r".D(~\1)",old)
 else:new,n=re.subn(r"\.CLK\(([^()]+)\)",".CLK(1'b0)",old)
 assert n==1;p.write_text(s[:hit.start()]+new+s[hit.end():]);(t/"mutation.json").write_text(json.dumps(dict(mutant=mut,old=old,new=new,sha256=hashlib.sha256(p.read_bytes()).hexdigest()),indent=2))
