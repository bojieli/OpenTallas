import pathlib,subprocess
D=pathlib.Path('/work');s=(D/'coupon.sv').read_text()
for tag,text in [('good',s),('wrong_value',s.replace(".d(1'b0)",".d(1'b1)")),('omit_upstream',s.replace("ot_hbm_su_startup_ff1030 u_alo(.clk(clk),.d(1'b0),.q(a_lo30));","assign a_lo30=1'b0;"))]:
 (D/(tag+'.sv')).write_text(text)
 t='read_verilog -sv /work/rtl/ot_hbm_su_startup_ff1030.sv /work/rtl/ot_hdc_delay__su_startup_ff1030.sv /work/rtl/ot_hdc_w11_cut__su_startup_ff1030.sv /work/'+tag+'.sv; hierarchy -check -top coupon; synth -top coupon -flatten; write_json /work/'+tag+'.json'
 with open(D/(tag+'.log'),'w')as f:subprocess.run(['yosys','-p',t],stdout=f,stderr=subprocess.STDOUT,check=True)
print('THREE_SYNTH_VARIANTS_COMPLETE')
