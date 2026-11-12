# Build EQ fragments for forms A and B by extracting the exact RTL text from ksh.sv (no hand copies of logic).
import re,os
s=open('ksh.sv').read()
os.makedirs('eq',exist_ok=True)
def between(a,b,inc_b=True):
  i=s.index(a); j=s.index(b,i)
  return s[i:j+(len(b) if inc_b else 0)]
popg=re.search(r"\(\* keep_hierarchy, keep \*\) module ot_hbm_svc_skid_popg.*?endmodule",s,re.S).group(0)
# ---- form A: lane VM response branch
blkA=between("  wire c_pop_vm,f_wv,tag_bad;wire[FW-1:0]f_wd;\n","  wire f_ov,f_un;\n",False)
def fragA(name,defs,shift):
  d="".join("`define %s\n"%x for x in defs)
  u="".join("`undef %s\n"%x for x in defs)
  body=f"""{d}module {name}(input wire hbm_clk,hrst_q,c_v,vm_phase,f_r_unused,d_r,cm_bank,input wire[15:0]cm_epoch,input wire[276:0]c_d,
 output wire o_c_r,o_pop,output wire o_wv,o_tbad,output wire[278:0]o_wd);
 localparam integer FW=279,RW=277;
 wire f_r=1'b1;wire c_r;wire[16:0]rt=c_d[RW-1-:17];wire[3:0]rb=c_d[259:256];
{blkA}
 assign o_c_r=c_r;assign o_pop=c_pop_vm;
"""
  if shift:
    body+=""" reg q_v,q_t;reg[278:0]q_d;
 always @(posedge hbm_clk or negedge hrst_q)if(!hrst_q)q_v<=1'b0;else q_v<=f_wv;
 always @(posedge hbm_clk)begin q_d<=f_wd;q_t<=tag_bad;end
 assign o_wv=q_v;assign o_tbad=q_v&&q_t;assign o_wd=q_v?q_d:279'd0;
"""
  else:
    body+=""" assign o_wv=f_wv;assign o_tbad=tag_bad;assign o_wd=f_wv?f_wd:279'd0;
"""
  return body+"endmodule\n"+u
def fr(t,name): return t.replace("module fragA(","module %s("%name).replace("f_r_unused","f_r").replace(" wire f_r=1'b1;","")
open('eq/bpA_gold.sv','w').write(fr(fragA('fragA',[],False),'bpA_gold'))
open('eq/bpA_gate.sv','w').write(popg+"\n"+fr(fragA('fragA',['OT_KSH_VMSTG'],False),'bpA_gate'))
open('eq/bpA_mut.sv','w').write(popg+"\n"+fr(fragA('fragA',['OT_KSH_VMSTG','OT_KSH_MUT_A'],False),'bpA_gate'))
open('eq/fragA_gold.sv','w').write(fragA('fragA',[],True))
open('eq/fragA_gate.sv','w').write(popg+"\n"+fragA('fragA',['OT_KSH_VMSTG'],False))
open('eq/fragA_mut.sv','w').write(popg+"\n"+fragA('fragA',['OT_KSH_VMSTG','OT_KSH_MUT_A'],False))
# ---- form B: stream WB count pipeline
fns=between(" function automatic [2:0] ov(","endfunction\n")+between(" function automatic [7:0] wcnt(","endfunction\n")
blkB=between(" reg wv1,wv2,wv3;"," wire wf_wr_ready,wf_ov",False)
def fragB(name,defs,shift):
  d="".join("`define %s\n"%x for x in defs); u="".join("`undef %s\n"%x for x in defs)
  body=f"""{d}module {name}(input wire stream_clk,srst_q,wbw_v,input wire[29:0]wbw_base,input wire[11:0]wbw_total,input wire[2:0]sm_s,
 output wire o_v,output wire[73:0]o_d);
 localparam integer WQW=30+12+32;
{fns}{blkB}
"""
  if shift:
    body+=""" reg q_v;reg[WQW-1:0]q_d;
 always @(posedge stream_clk or negedge srst_q)if(!srst_q)q_v<=1'b0;else q_v<=wq_v;
 always @(posedge stream_clk)q_d<=wq_d;
 assign o_v=q_v;assign o_d=q_d;
"""
  else: body+=" assign o_v=wq_v;assign o_d=wq_d;\n"
  return body+"endmodule\n"+u
open('eq/fragB_gold.sv','w').write(fragB('fragB',[],True))
open('eq/fragB_gate.sv','w').write(fragB('fragB',['OT_KSH_WCNT2'],False))
open('eq/fragB_mut.sv','w').write(fragB('fragB',['OT_KSH_WCNT2','OT_KSH_MUT_B'],False))
# ---- form C: whole skid module vs ot_hbm_svc_pin_skid2
srl=re.search(r"module ot_hbm_svc_pin_skid2_srl.*?endmodule",s,re.S).group(0)
open('eq/srl_gate.sv','w').write(popg+"\n"+srl+"\n")
open('eq/srl_mut.sv','w').write("`define OT_KSH_MUT_C\n"+popg+"\n"+srl+"\n`undef OT_KSH_MUT_C\n")
def ys(name,gold,gtop,gate,gatetop,params=""):
  open(f'eq/{name}.ys','w').write(f"""read_verilog -sv {gold}
hierarchy -top {gtop}
{params.format(m=gtop)}
proc; flatten; opt_clean
rename {gtop} gold
design -stash gold
read_verilog -sv {gate}
hierarchy -top {gatetop}
{params.format(m=gatetop)}
setattr -mod -unset keep_hierarchy ot_hbm_svc_skid_popg
setattr -unset keep a:keep
proc; flatten; opt_clean; opt_merge -share_all; opt_clean
rename {gatetop} gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
async2sync
equiv_make gold gate equiv
hierarchy -top equiv
opt_clean
equiv_simple -seq 4
equiv_induct -seq 4
equiv_status -assert
""")
ys('eqA','fragA_gold.sv','fragA','fragA_gate.sv','fragA')
ys('eqA_mut','fragA_gold.sv','fragA','fragA_mut.sv','fragA')
ys('eqB','fragB_gold.sv','fragB','fragB_gate.sv','fragB')
ys('eqB_mut','fragB_gold.sv','fragB','fragB_mut.sv','fragB')
P="chparam -set WIDTH 277 {m}"
ys('eqC','ref.sv','ot_hbm_svc_pin_skid2','srl_gate.sv','ot_hbm_svc_pin_skid2_srl',P)
ys('eqC_mut','ref.sv','ot_hbm_svc_pin_skid2','srl_mut.sv','ot_hbm_svc_pin_skid2_srl',P)
