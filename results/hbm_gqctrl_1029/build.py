from pathlib import Path
p=Path(__file__).parent
stages=['s0','s1','s2a','s2','s7','s8','s9','s10']
for mode in ['old','new','mut']:
 s=(p/('old.sv' if mode=='old' else 'new.sv')).read_text()
 s=s.replace('module ot_hbm_xp_aq_tree13 #','module ctrl_'+mode+' #',1)
 s=s.replace('output reg           fault\n','output reg           fault,\n    output wire [7:0] stage_v, stage_fp4\n',1)
 s=s.replace('\nendmodule','\nassign stage_v={'+','.join(t+'_v' for t in stages)+'};\nassign stage_fp4={'+','.join(t+'_fp4' for t in stages)+'};\nendmodule')
 if mode=='mut':
  assert s.count('s8_fp4 <= s7_fp4;')==1
  s=s.replace('s8_fp4 <= s7_fp4;','s8_fp4 <= ~s7_fp4;')
 (p/('ctrl_'+mode+'.sv')).write_text(s)
for mode in ['new','mut']:
 (p/('m_'+mode+'.v')).write_text('''module m(input clk,rst_n,v,fp4,input[1023:0]x,output bad);
wire[7:0] av,bv,af,bf;
ctrl_old a(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.x(x),.stage_v(av),.stage_fp4(af));
ctrl_'''+mode+''' b(.clk(clk),.rst_n(rst_n),.v(v),.fp4(fp4),.x(x),.stage_v(bv),.stage_fp4(bf));
assign bad=(| (av^bv)) || (| ((af^bf)&av));
endmodule
''')
 (p/(mode+'.ys')).write_text('read_verilog -sv ot_hdc_delay.sv ot_hbm_xp_aq_scale13.sv ctrl_old.sv ctrl_'+mode+'.sv m_'+mode+'.v\nhierarchy -top m; proc; flatten; opt -full; memory; opt_clean; async2sync; dffunmap\nsat -verify -seq 20 -set-at 1 rst_n 0 -prove bad 0 -set-def-inputs -show-ports\n')
