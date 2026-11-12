import re,os
s=open('ksh.sv').read()
os.makedirs('eq',exist_ok=True)
ref=open('eq/ref.sv').read() if os.path.exists('eq/ref.sv') else open('ref.sv').read()
def dbg(t,name):
    t=t.replace("output wire [WIDTH-1:0]out_data\n);","output wire [WIDTH-1:0]out_data,output wire d_hv,d_tv,output wire [WIDTH-1:0]d_hd,d_td\n);",1)
    t=t.replace("endmodule","    assign d_hv=head_valid;assign d_tv=tail_valid;assign d_hd=head_data;assign d_td=tail_data;\nendmodule",1)
    return t.replace("module ot_hbm_svc_pin_skid2","module "+name,1) if "module ot_hbm_svc_pin_skid2 " in t or "module ot_hbm_svc_pin_skid2 #" in t else t.replace("module ot_hbm_svc_pin_skid2_pf","module "+name,1)
pf=re.search(r"module ot_hbm_svc_pin_skid2_pf.*?endmodule",s,re.S).group(0)
enh=re.search(r"\(\* keep_hierarchy, keep \*\) module ot_hbm_svc_skid_enh.*?endmodule",s).group(0)
gold=dbg(ref,"skid_gold"); 
def build(pf_text,name):
    return enh+"\n"+dbg(pf_text,name)
open('eq/eqD_gold.sv','w').write(gold)
open('eq/eqD_gate.sv','w').write(build(pf,"skid_gate"))
open('eq/eqD_mut.sv','w').write("`define OT_KSH_MUT_D\n"+build(pf,"skid_gate")+"\n`undef OT_KSH_MUT_D\n")
open('eq/eqD_miter.sv','w').write('''module miter #(parameter integer W=277)(input wire clk,rst_n,in_v,out_r,input wire[W-1:0]in_data);
 wire gr,gv,dr,dv,ghv,gtv,dhv,dtv;wire[W-1:0]go,do_,ghd,gtd,dhd,dtd;
 skid_gold #(.WIDTH(W)) g(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_r(gr),.in_data(in_data),.out_v(gv),.out_r(out_r),.out_data(go),.d_hv(ghv),.d_tv(gtv),.d_hd(ghd),.d_td(gtd));
 skid_gate #(.WIDTH(W)) d(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_r(dr),.in_data(in_data),.out_v(dv),.out_r(out_r),.out_data(do_),.d_hv(dhv),.d_tv(dtv),.d_hd(dhd),.d_td(dtd));
 always @* begin
  assert(gr==dr); assert(gv==dv); assert(!gv||go==do_);
  assert(ghv==dhv); assert(gtv==dtv); assert(!ghv||ghd==dhd); assert(!gtv||gtd==dtd);
 end
endmodule
''')
for n,g in (("eqD","eqD_gate.sv"),("eqD_mut","eqD_mut.sv")):
    open(f'eq/{n}.ys','w').write(f"""read_verilog -formal -sv eq/eqD_gold.sv eq/{g} eq/eqD_miter.sv
hierarchy -top miter
proc; flatten; opt_clean -purge
setattr -mod -unset keep_hierarchy ot_hbm_svc_skid_enh
hierarchy -top miter; flatten; opt_clean -purge
async2sync
sat -tempinduct -prove-asserts -set-init-zero -maxsteps 8 -verify -show-ports
""")
# E: whole-core EQ, STSEL vs plain
open('eq/eqE.ys','w').write("""read_verilog -sv -DOT_KSH_STSEL src/ot_hbm_svc_async_fifo.sv src/ot_hbm_svc_ring_h9b_ff.sv ksh.sv
hierarchy -top ot_hbm_svc_vm_kshare_splitstrap -chparam KRL1 1
setattr -mod -unset keep_hierarchy ot_hbm_svc_ksh_phase_ff
setattr -unset keep a:keep
proc; flatten; opt_clean; opt_merge -share_all; opt_clean
rename ot_hbm_svc_vm_kshare_splitstrap gate
design -stash gate
read_verilog -sv src/ot_hbm_svc_async_fifo.sv src/ot_hbm_svc_ring_h9b_ff.sv src/ref_orig.sv
hierarchy -top ot_hbm_svc_vm_kshare_splitstrap -chparam KRL1 1
proc; flatten; opt_clean
rename ot_hbm_svc_vm_kshare_splitstrap gold
design -stash gold
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
async2sync
equiv_make gold gate equiv
hierarchy -top equiv
opt_clean
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status -assert
""")
