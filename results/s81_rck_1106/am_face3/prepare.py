from pathlib import Path
import subprocess,re,json,hashlib
BASE='28fc7bcb68f0d9771a3a5454f817921894d05f63'
w=Path('/srv/opentallas-scratch3/claude/wt/codex-lec-transfer-1106');p=Path(__file__).parent
rel='rtl/dsrom_sys/s81_link/ot_s81_kp4_dsyn.sv'
old=subprocess.check_output(['git','-C',str(w),'show',BASE+':'+rel]).decode();new=(w/rel).read_text()
common=subprocess.check_output(['git','-C',str(w),'show',BASE+':rtl/dsrom_sys/s81_link/ot_s81_kp4_common.sv']).decode()
rst=re.search(r'module ot_s81_kp4_rst\b.*?endmodule',common,re.S).group()
helper=re.search(r'module ot_s81_kp4_am_face3\b.*?endmodule',new,re.S).group()
def literal(src):return src[src.index('    localparam integer NT'):src.index('    // ================= syndromes')]
head='module CORE(input clk,rst_n,p_v,input [543:0] p_d,EXTRA output [1716:0] state,output reg lock,output reg [31:0] n_relock);\n'
trail='\nassign state={rs_n,am_ok,pv,wc,cand,miss,lock,n_relock,x0,x1,x2,xs[0],xs[1],xs[2],xs[3]};\nendmodule\n'
base=head.replace('CORE','am_old').replace('EXTRA','')+literal(old)+trail
cand=head.replace('CORE','am_new').replace('EXTRA','input [8:0] am_face3,')+literal(new)+trail
(p/'old_literal.sv').write_text(base);(p/'reset_literal.sv').write_text(rst+'\n')
for kind in ['good','wrong_group','wrong_xor','wrong_threshold','wrong_valid','wrong_payload','wrong_reset']:
 h,c=helper,cand
 if kind=='wrong_group':h=h.replace('pop4(amx[3:0])','pop4(amx[7:4])')
 if kind=='wrong_xor':h=h.replace("12'hA5C","12'hA5D")
 if kind=='wrong_threshold':c=c.replace("am_distance <= 4'd2","am_distance <= 4'd3")
 if kind=='wrong_payload':c=c.replace('x1 <= x0','x1 <= p_d')
 if kind=='wrong_reset':c=c.replace('if (!rs_n[0])','if (!rst_n)')
 (p/(kind+'.sv')).write_text(h+'\n'+c)
 # Wrong valid epoch is a wrapper mutation; the core remains literal.
(p/'tb.sv').write_text('''`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,p_v=0;reg [543:0] raw=0,face=0;reg face_v=0;
always @(posedge clk) begin face<=raw;face_v<=p_v;end
wire [8:0] parts;ot_s81_kp4_am_face3 u_parts(.clk(clk),.p_d(raw),.parts(parts));
wire [1716:0] a,b;wire al,bl;wire [31:0] an,bn;
am_old u_old(.clk(clk),.rst_n(rst_n),.p_v(face_v),.p_d(face),.state(a),.lock(al),.n_relock(an));
`ifdef WRONG_VALID
am_new u_new(.clk(clk),.rst_n(rst_n),.p_v(p_v),.p_d(face),.am_face3(parts),.state(b),.lock(bl),.n_relock(bn));
`else
am_new u_new(.clk(clk),.rst_n(rst_n),.p_v(face_v),.p_d(face),.am_face3(parts),.state(b),.lock(bl),.n_relock(bn));
`endif
integer cycle,j,locked=0,resets=0;reg prior=0;
initial begin
for(cycle=0;cycle<20000;cycle=cycle+1) begin
 @(negedge clk);
 for(j=0;j<17;j=j+1) raw[32*j+:32]=$urandom;
 if(cycle>=12 && cycle<4108) raw[543:532]=cycle-12;
 else raw[543:532]=(cycle%10==0)?12'hA5C:12'hFFF;
 p_v=(cycle<10000)?1:($urandom%5!=0);
 rst_n=(cycle>=12 && !(cycle>=6000 && cycle<6010) && !(cycle>=12000 && cycle<12009) && !(cycle>=16000 && cycle<16011));
 if(!rst_n) resets=resets+1;
 @(posedge clk);#0.1;
 if(cycle>8 && a!==b) begin $display("DIFF cycle=%0d am=%b/%b pv=%b/%b lock=%b/%b state_x=%b",cycle,u_old.am_ok,u_new.am_ok,u_old.pv,u_new.pv,al,bl,((^a)===1'bx || (^b)===1'bx));$fatal(1,"literal payload/valid/reset/FSM calendar mismatch");end
 if(al&&!prior) locked=locked+1;prior=al;
end
if(locked<2)$fatal(1,"missing native lock acquisition coverage");
$display("PASS cycles=20000 exhaustive_headers=4096 lock_acquisitions=%0d reset_edges=%0d state_bits=1717 added_ff=9 added_full_cycles=0",locked,resets);
$finish;
end
endmodule
''')
manifest={rel:hashlib.sha256((w/rel).read_bytes()).hexdigest(),'old_commit':BASE,'extraction':'literal localparam/reset/AM/FSM/x0-x2/xs prefix; unchanged syndrome arithmetic outside mechanism'}
(p/'source.json').write_text(json.dumps(manifest,indent=1)+'\n')

land=subprocess.check_output(['git','-C',str(w),'show',BASE+':rtl/common/landed_parent/ot_pl_land.sv']).decode()
pad=re.search(r'module ot_pl_pad\b.*?endmodule',land,re.S).group()
(p/'face_literal.sv').write_text(pad+'\n')
tb=(p/'tb.sv').read_text().replace('reg [543:0] raw=0,face=0;reg face_v=0;','reg [543:0] raw=0;wire [543:0] face;wire face_v;')
tb=tb.replace('always @(posedge clk) begin face<=raw;face_v<=p_v;end','ot_pl_pad #(.W(544),.N(1)) u_face_p_d(.ck(clk),.d(raw),.q(face));\not_pl_pad #(.W(1),.N(1)) u_face_p_v(.ck(clk),.d(p_v),.q(face_v));')
(p/'tb.sv').write_text(tb)
# Preprocess both complete real source files with the feature OFF. Only
# whitespace/comments/line annotations may differ from the prior source.
gf=subprocess.check_output(['git','-C',str(w),'show',BASE+':rtl/dsrom_sys/s81_link/ot_s81_gf1024.svh'])
(p/'ot_s81_gf1024.svh').write_bytes(gf)
for inc in set(re.findall(r'`include "([^"]+)"',old)):
 (p/inc).write_bytes(subprocess.check_output(['git','-C',str(w),'show',BASE+':rtl/dsrom_sys/s81_link/'+inc]))
for rel in ['rtl/dsrom_sys/s81_link/ot_s81_kp4_dsyn.sv','rtl/dsrom_sys/s81_link/lp/ot_s81_kp4_dec_native_flat_lp.sv']:
 prior=subprocess.check_output(['git','-C',str(w),'show',BASE+':'+rel]);now=(w/rel).read_bytes();outs=[]
 for label,data in [('old',prior),('off',now)]:
  src=p/(Path(rel).stem+'_'+label+'.sv');dest=src.with_suffix('.pre');src.write_bytes(data)
  subprocess.run(['iverilog','-g2012','-E','-I'+str(p),'-o',str(dest),str(src)],check=True)
  text=dest.read_text();text=re.sub(r'`line[^\n]*','',text);text=re.sub(r'//[^\n]*|/\*.*?\*/','',text,flags=re.S);outs.append(re.sub(r'\s+','',text))
 assert outs[0]==outs[1], 'default-off source differs: '+rel
print('DEFAULT_OFF_FULL_SOURCES_IDENTICAL')
