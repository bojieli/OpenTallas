import pathlib,re
from pin_plan import PACK
HERE=pathlib.Path(__file__).parent;OUT=HERE/'static_id';OUT.mkdir(exist_ok=True)
s=(PACK/'ot_hbm_su_static_lane_pinreg.sv').read_text();s=s.replace('module ot_hbm_su_static_lane_pinreg #(', 'module ot_hbm_su_static_lane_pinreg__static_id #(\n    parameter integer STATIC_LANE_ID = 0,')
s=s.replace('d_in = {lane_id,','d_in = {(STATIC_LANE_ID != 0) ? 11\'d0 : lane_id,')
s=s.replace('assign {q_lane_id, q_ld_c,','wire [10:0] q_captured_id;\n    assign q_lane_id = (STATIC_LANE_ID != 0) ? lane_id : q_captured_id;\n    assign {q_captured_id, q_ld_c,')
(OUT/'ot_hbm_su_static_lane_pinreg__static_id.sv').write_text(s)
for top in ['ot_hnx_su_exp__rst3','ot_hnx_su_plain4__lid9_rst3']:
 s=(PACK/(top+'.sv')).read_text().replace('module '+top+' (','module '+top+'__static_id #(parameter integer STATIC_LANE_ID=0) (')
 s=s.replace('ot_hbm_su_static_lane_pinreg #(', 'ot_hbm_su_static_lane_pinreg__static_id #(.STATIC_LANE_ID(STATIC_LANE_ID), ')
 (OUT/(top+'__static_id.sv')).write_text(s)
# Minimum mechanism vehicle: complete native pinreg boundary, actual KIND/LN/LAT.
s=(PACK/'ot_hbm_su_static_lane_pinreg.sv').read_text().split(') (',1)[1].split(');',1)[0]
ports=[]
for d,width,names in re.findall(r'(input|output)\s+wire\s*(\[[^\]]+\])?\s*([^;]+?)(?=,?\n\s*(?:input|output)|$)',s,re.S):
 names=names.strip().rstrip(',')
 for n in names.split(','):
  n=n.strip();assert re.fullmatch(r'\w+',n),(d,width,n)
  w=1
  if width:
   ex=width.strip('[]').split(':')[0];w=eval(ex,{},dict(LN=7,AW=24,CW=24))+1
  ports.append((d,n,w))
assert len(ports)>60,len(ports)
b='`timescale 1ns/1ps\nmodule tb;\nparameter integer KIND=1;\ninteger id,cyc,errors=0,mutants=0;\nreg clk=0; always #5 clk=~clk;\n'
for d,n,w in ports:
 if d=='input':b+='reg '+(f'[{w-1}:0] 'if w>1 else'')+n+';\n'
 else:
  for tag in ['ref','opt','mut']:b+='wire '+(f'[{w-1}:0] 'if w>1 else'')+tag+'_'+n+';\n'
for tag,mod,params in [('ref','ot_hbm_su_static_lane_pinreg',''),('opt','ot_hbm_su_static_lane_pinreg__static_id',',.STATIC_LANE_ID(1)'),('mut','ot_hbm_su_static_lane_pinreg__static_id',',.STATIC_LANE_ID(1)')]:
 b+=mod+' #(.LN(7),.KIND(KIND),.LEAF(1),.MLAT(4),.ALAT(4),.FETCH_EXTRA_EDGES(2)'+params+') u_'+tag+'('+','.join('.'+n+'('+((tag+'_'+n)if d=='output'else('(lane_id^11\'d1)'if tag=='mut'and n=='lane_id'else n))+')'for d,n,w in ports)+');\n'
outputs=[n for d,n,w in ports if d=='output'];b+='wire ['+str(sum(w for d,n,w in ports if d=='output')-1)+':0] ref_all={'+','.join('ref_'+n for n in outputs)+'},opt_all={'+','.join('opt_'+n for n in outputs)+'},mut_all={'+','.join('mut_'+n for n in outputs)+'};\n'
b+='initial begin if(!$value$plusargs("ID=%d",id)) id=0;\n'
for d,n,w in ports:
 if d=='input':b+=n+"='0;\n"
b+="rst_n=1; lane_id=id; #1 rst_n=0;\nfor(cyc=0;cyc<180;cyc=cyc+1)begin\n @(negedge clk);\n"
for d,n,w in ports:
 if d!='input'or n in ['clk_stage','clk_insert','rst_n','lane_id']:continue
 b+=n+"={"+str((w+31)//32)+"{$random}};\n" # full native input bits, strobes/config overridden below
b+="rst_n=(cyc>=5 && !(cyc>=90&&cyc<96));\nld=(cyc==10||cyc==100);emit=(cyc==40||cyc==130);\nld_c={35{24'd1}};o_v=0;i_v=0;no=24'd2048;ni=24'd2048;ls=3;lvw=11;vb={5{24'd0}};obase=24'd32;aibase=24'd64;krow=24'd96;srcs=8'h00;cx_srcs=8'h00;\nif(cyc>100&&cyc%7==0)begin vi_q[3]=1'bx;rd_q[7]=1'bz;end\nend\n$display(\"RESULT KIND%0d ID%0d ERR%0d MUT%0d\",KIND,id,errors,mutants);if(errors) $fatal(1,\"lockstep\");$finish;end\nalways @*begin clk_stage={8{clk}};clk_insert={4{clk}};end\nalways @(posedge clk or negedge rst_n) begin #1; if(ref_all!==opt_all)begin errors=errors+1;if(errors<4)$display(\"DIFF cyc%0d ref%h opt%h\",cyc,ref_all,opt_all);end if(ref_all!==mut_all)mutants=mutants+1;end\nendmodule\n"
(OUT/'lockstep.sv').write_text(b)
print('generated',len(ports),'ports',sum(w for d,n,w in ports if d=='output'),'outputbits')
