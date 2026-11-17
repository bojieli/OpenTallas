from pathlib import Path
import subprocess,re,sys,json,hashlib
w,p=map(Path,sys.argv[1:])
BASE='28fc7bcb68f0d9771a3a5454f817921894d05f63'
def src(ref,rel):return subprocess.check_output(['git','-C',str(w),'show',ref+':'+rel],text=True)
rel='rtl/dsrom_sys/s81_link/ot_s81_kp4_dsyn.sv'
old=src(BASE,rel);new=(w/rel).read_text()
common=src('HEAD','rtl/dsrom_sys/s81_link/ot_s81_kp4_common.sv')
land=src('HEAD','rtl/common/landed_parent/ot_pl_land.sv')
def literal(s):return s[s.index('    localparam integer NT'):s.index('    // ================= syndromes')]
head='module CORE(input clk,rst_n,p_v,input [543:0] p_d,EXTRA output [1716:0] state,output reg lock,output reg [31:0] n_relock);\n'
trail='\nassign state={rs_n,am_ok,pv,wc,cand,miss,lock,n_relock,x0,x1,x2,xs[0],xs[1],xs[2],xs[3]};\nendmodule\n'
(p/'old_literal.sv').write_text(head.replace('CORE','am_old').replace('EXTRA','')+literal(old)+trail)
helper=re.search(r'module ot_s81_kp4_am_face3\b.*?endmodule',new,re.S).group()
(p/'good.sv').write_text(helper+'\n'+head.replace('CORE','am_new').replace('EXTRA','input [8:0] am_face3,')+literal(new)+trail)
(p/'reset_literal.sv').write_text(re.search(r'module ot_s81_kp4_rst\b.*?endmodule',common,re.S).group()+'\n')
(p/'face_literal.sv').write_text(re.search(r'module ot_pl_pad\b.*?endmodule',land,re.S).group()+'\n')
(p/'source.json').write_text(json.dumps(dict(golden=BASE,source_sha256=hashlib.sha256(new.encode()).hexdigest(),head=subprocess.check_output(['git','-C',str(w),'rev-parse','HEAD'],text=True).strip()),indent=2)+'\n')
