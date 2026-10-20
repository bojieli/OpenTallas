#!/usr/bin/env python3
"""Build independent red reference from original SU source; sc from direct scalar interface.
Run at repository root. Recovered leaf source is passed in, never rewritten.
"""
from pathlib import Path
import re,sys
out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
s=Path(sys.argv[1]).read_text()
def module(name):
 return re.search(r'module '+name+r'\b.*?endmodule',s,re.S).group()
red=module('qfd_dv_s5_red'); hdr=red[:red.index('    localparam')].replace('qfd_dv_s5_red','red_reference',1)
su=Path('rtl/qwen_dv/qfd_dv_su8_entries.sv').read_text()
b=su[su.index('    reg              rd_v, rd_mx'):su.index('    wire f_red;')]
b=b.replace('rd_v, rd_mx','rd_mx').replace('l_red[1:0]','l_red0').replace('l_redsq[0]','l_redsq0').replace('l_last[0]','l_last0').replace('l_raddr[0 +: AW]','l_raddr0').replace('posedge clk','posedge ck')
inst=su[su.index('    ot_hdc_vreduce #(.SW(SW)'):su.index('    end else begin : g_red_entries')].replace('.clk(clk)','.clk(ck)').replace('reducer_busy','busy').replace('f_red','fault')
ref=hdr+''' localparam integer SW=8, AW=24, LV=4;
 reg r1,r2,rc;
 always @(posedge ck or negedge rst_n) if(!rst_n) begin r1<=0;r2<=0;end else begin r1<=1;r2<=r1;end
 always @(posedge ck or negedge r2) if(!r2) rc<=0;else rc<=1;
 wire rst_c=rc;
'''+b+inst+'endmodule\n'
# Scalar reference independently unpacks the packed cfg, then calls the original scalar module.
sc=module('qfd_dv_s5_sc'); sh=sc[:sc.index('    wire rst;')].replace('qfd_dv_s5_sc','sc_reference',1)
ref+=sh+''' reg r1,r2;
 always @(posedge ck or negedge rst_n) if(!rst_n) begin r1<=0;r2<=0;end else begin r1<=1;r2<=r1;end
 wire cv,root,dir,fuse; wire[5:0] nb,amnb; wire[23:0] ss,rx; wire[31:0] eps;wire[4:0] k;
 assign {cv,root,dir,nb,ss,fuse,rx,eps,k,amnb}=sc_cfg;
 qfd_dv_scalar2 #(.MU_NU(4)) u_ref(.ck(ck),.rst_n(r2),.cfg_v(cv),.cfg_root(root),.cfg_rdir(dir),.cfg_nb(nb),.cfg_ss(ss),.cfg_fuse(fuse),.cfg_rx(rx),.cfg_eps(eps),.cfg_k(k),.cfg_amnb(amnb),
 .dn_i(dn_i),.dn_o(dn_o),.up_i(up_i),.up_o(up_o),
 .ps_v(red_we && red_addr[23:22]==3),.ps_idx({2'b00,red_addr[21:0]}),.ps_val(red_data),
 .rb_v((|vm_we) && vm_win0==3),.rb_val(vm_wdata0),.am_v(am_v),.am_idx(am_idx),.am_val(am_val),.am_u(am_u),
 .w1_we(w1_we),.w1_addr(w1_addr),.w1_data(w1_data),.tok_v(tok_v),.tok_idx(tok_idx),.tok_own(tok_own),.tok_val(tok_val),.tok_user(tok_user),.busy(busy),.fault(fault));
 endmodule
'''
(out/'references.sv').write_text(ref)
for kind,source in [('red',red),('sc',sc)]:
 ports=re.findall(r'(input|output)\s+(?:wire|reg)\s*(\[[^\]]+\])?\s*(\w+)\s*[,\n)]',source[:source.index(');')+2])
 t='`timescale 1ns/1ps\nmodule tb_'+kind+';\nreg ck=0;always #5 ck=~ck;reg rst_n=0;integer cycle;\n'
 for d,w,n in ports:
  if n in ('ck','rst_n'):continue
  t+=('reg ' if d=='input' else 'wire ')+(w or '')+' '+n+('=0;' if d=='input' else ', ref_'+n+';')+'\n'
 def con(ref):
  args=[]
  for d,w,n in ports:
   sig=('ref_'+n if ref and d=='output' else n)
   if not ref and n==('l_redsq0' if kind=='red' else 'dn_i'):sig='('+sig+' ^ MUT)'
   args.append('.'+n+'('+sig+')')
  return ','.join(args)
 t+='localparam integer MUT=`MUT;\nqfd_dv_s5_'+kind+' dut('+con(False)+');\n'+kind+'_reference refdut('+con(True)+');\n'
 t+='initial begin repeat(4) @(negedge ck);rst_n=1;\nfor(cycle=0;cycle<800;cycle=cycle+1) begin @(negedge ck);\n'
 if kind=='red':
  t+="l_ov=(cycle%20<16)?8'hff:0; l_last0=(cycle%20==15);l_red0=(cycle<400)?1:2;l_redsq0=(cycle>=200 && cycle<400);l_raddr0=cycle/20;\nfor(integer j=0;j<8;j=j+1) l_out[j*32+:32]=32'h3f000000+((cycle*8+j)<<12);\n"
 else:
  t+="sc_cfg=0;dn_i=0;up_i=0;red_we=0;vm_we=0;am_v=0;\nif(cycle==10) sc_cfg={1'b1,1'b0,1'b0,6'd4,24'd0,1'b0,24'd12,32'd0,5'd0,6'd2};\nif(cycle>20 && cycle<100 && cycle%4==0) dn_i={1'b1,3'd2,12'd0,32'h3f800000+cycle};\nif(cycle>100 && cycle<180 && cycle%4==0) up_i={1'b1,3'd5,12'd0,8'd0,24'(cycle)};\nif(cycle==200) sc_cfg={1'b1,1'b1,1'b0,6'd4,24'd0,1'b0,24'd12,32'd0,5'd0,6'd2};\nif(cycle>=210 && cycle<214) begin red_we=1;red_addr={2'b11,22'(cycle-210)};red_data=32'h3f800000;end\nif(cycle==400 || cycle==450) begin am_v=1;am_idx=cycle;am_val=32'h40000000;am_u=2;end\n"
 t+='#1;end\nrepeat(200) @(negedge ck);$display("PASS '+kind+' 800 stimulus cycles");$finish;end\nalways @(negedge ck) if(rst_n && cycle>8) begin #2;\n'
 for d,w,n in ports:
  if d=='output':t+='if('+n+' !== ref_'+n+') $fatal(1,"MISMATCH '+kind+' '+n+' cycle=%0d",cycle);\n'
 t+='end\nendmodule\n';(out/('tb_'+kind+'.sv')).write_text(t)
