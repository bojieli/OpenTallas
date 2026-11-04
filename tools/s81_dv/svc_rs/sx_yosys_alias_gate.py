from pathlib import Path
import subprocess
import argparse
a=argparse.ArgumentParser();a.add_argument('--out',type=Path,required=True);args=a.parse_args()
w=Path(__file__).resolve().parents[3];d=args.out;d.mkdir(parents=True,exist_ok=True)
p='rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_sx.sv'
old=subprocess.check_output(['git','-C',str(w),'show','b1a212543:'+p],text=True)
new=(w/p).read_text()
(d/'old.sv').write_text(old.replace('module dsdv_svc_sx #(','module sx_old #('))
(d/'new.sv').write_text(new.replace('module dsdv_svc_sx #(','module sx_new #('))
mut=new.replace('assign face_gout[4*r + f] = gout[NR+1];','assign face_gout[4*r + f] = gout[NR];')
(d/'mut.sv').write_text(mut.replace('module dsdv_svc_sx #(','module sx_new #('))
(d/'old.sv').write_text(old.replace('module dsdv_svc_sx #(','module sx_old #(').replace('dsdv_sx_rly_', 'old_sx_rly_'))
h=(w/'rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_sx_hrow.sv').read_text();h=h[h.index('module dsdv_svc_sx_hrow #('):];h=h[:h.index(');')+2]
h+='''
assign go_n=l_i ^ gi_e; assign go_e=l_i ^ gi_s; assign go_s=l_i ^ gi_w; assign go_w=l_i ^ gi_n;
assign so_n=si_e ^ l_i[137:0];assign so_e=si_s ^ l_i[137:0];assign so_s=si_w ^ l_i[137:0];assign so_w=si_n ^ l_i[137:0];
assign rt_o=l_i ^ gi_n ^ gi_e ^ gi_s ^ gi_w;assign t_o=l_i[38:0] ^ {35'd0,sid};always @* fault=^l_i ^ hb;
endmodule
'''
for suffix in ['NS','EW','SN','WE']:
 h+=f'module dsfd_dvrly_276_{suffix}(input wire ck,rs,input wire [275:0] i,output reg [275:0] o,output wire ck_o); assign ck_o=ck; always @(posedge ck) if(!rs)o<=0;else o<=i; endmodule\n'
(d/'stubs.sv').write_text(h)
inputs={'ck':1,'rst':1,'sid':4,'l_v':1,'l_d':2132,'gi_v':4,'gi_d':8528,'si_v':4,'si_d':4304}
outputs={'go_v':4,'go_d':8528,'so_v':4,'so_d':4304,'rt_v':1,'rt_d':2132,'t_v':1,'t_tag':20,'t_y':128,'t_f':4,'fault':1}
t='module tb;\n'
for n,width in inputs.items():t+=f'reg [{width-1}:0] {n};\n'
for k,(nr,mask) in enumerate((nr,m) for nr in [0,1,2] for m in [0,5,15]):
 for variant in ['old','new']:
  for n,width in outputs.items():t+=f'wire [{width-1}:0] {n}_{variant}{k};\n'
  con=[f'.{n}({n})' for n in inputs]+[f'.{n}({n}_{variant}{k})' for n in outputs]
  t+=f'sx_{variant} #(.NR({nr}),.FM_GI(4\'d{mask}),.FM_GO(4\'d{mask}),.FM_SI(4\'d{mask}),.FM_SO(4\'d{mask})) u_{variant}{k}('+','.join(con)+');\n'
t+='integer cyc,j; initial begin ck=0;rst=0;sid=0;l_v=0;l_d=0;gi_v=0;gi_d=0;si_v=0;si_d=0;\n'
t+='for(cyc=0;cyc<260;cyc=cyc+1) begin ck=0;rst=(cyc>3);sid=$random;l_v=$random;gi_v=$random;si_v=$random;\n'
for n in ['l_d','gi_d','si_d']:t+=f'for(j=0;j<$bits({n});j=j+1) {n}[j]=$random;\n'
t+='#5;ck=1;#5; if(cyc>8)begin\n'
for k in range(9):
 a=','.join(n+'_old'+str(k) for n in outputs);b=','.join(n+'_new'+str(k) for n in outputs)
 t+=f'if({{{a}}}!=={{{b}}}) $fatal(1,"SX_ALIAS_MISMATCH case{k} cycle%0d",cyc);\n'
t+='end end $display("SX_ALIAS_LOCKSTEP PASS 9configs 251cycles alloutputs");$finish;end endmodule\n'
(d/'tb.sv').write_text(t)
