from pathlib import Path
import json
root=Path('.');b=json.loads((root/'candidate/boundary.json').read_text());s=(root/'rtl/test/qwen_dv/static_stream/tb_stream.sv').read_text()
s=s.replace('parameter integer MUT=0, STATIC=1','parameter integer MUT=0, STATIC=1')
s=s.replace("reg cfg=0;", "reg[3:0] sid=0;reg[1:0] dir=0;reg[27:0] tag=0;reg cfg=0;")
s=s.replace(".sid(4'd3)",'.sid(sid)').replace(".cfg_dir(2'd3)",'.cfg_dir(dir)').replace(".cfg_tag(28'h1234567)",'.cfg_tag(tag)')
s=s.replace('qfd_dv_stream_packer #(.MUT(MUT),.STATIC_PACKER(STATIC)) u_q','qfd_dv_stream_controls u_q')
names={'rst_n':'rst','cfg_v':'cfg','sw_i':'sw','se_i':'se','xw_we':'we','xw_addr':'addr','xw_data':'data','sid':'sid'}
ports={}
for x in b:ports.setdefault(x['port'],[]).append(x)
extra=[]
for pn,rows in ports.items():
 vals=[]
 for x in reversed(rows):
  src=names[x['source_port']];v=src if x['source_port'] in ('rst_n','cfg_v') else f"{src}[{x['source_bit']}]"
  if x['source_port']=='sw_i' and x['source_bit']==1087:v=f"({v} ^ (MUT==1))"
  if x['source_port']=='rst_n':v=f"(MUT==3 ? 1'b1 : {v})"
  vals.append(v)
 extra.append('.'+pn+'({'+','.join(vals)+'})')
s=s.replace('qfd_dv_stream_controls u_q(.ck(ck),.rst_n(rst),.sid(sid),','qfd_dv_stream_controls u_q('+','.join(extra)+",.ck(ck),.rst_n(rst),.sid(sid ^ (MUT==2 ? 4'd1 : 4'd0)),")
s=s.replace('cfg=rst&&age==17;', "cfg=rst&&(age==17||cycle%31==0);sid=4'(cycle%16);dir=2'(cycle%4);tag=28'(cycle*12345);")
s=s.replace('sw[1083:1080]=15;se[1083:1080]=15;', "sw[1083:1080]=4'(cycle%16);se[1083:1080]=4'((cycle+5)%16);")
s=s.replace('  if(age>=20 && {u_l.nm,u_l.nb,u_l.pbad} !== {u_q.nm,u_q.nb,u_q.pbad}) $fatal(1,"PACKER_INTERNAL_MISMATCH cycle%0d MUT%0d",cycle,MUT);','')
s=s.replace('  if(age>=20&&', '  if(!rst && {qe[1087],qw[1087],qtw,qv,qbad,qf} !== {le[1087],lw[1087],ltw,lv,lbad,lf}) $fatal(1,"STREAM_RESET_MISMATCH cycle%0d MUT%0d",cycle,MUT);\n  if(age>=20&&')
s=s.replace('STATIC_STREAM_EQ PASS words10000 resets2 ownpack/pass/taps/faults alloutputs','STREAM_CONTROLS_EQ PASS edges10000 resets2 varyingSID/config concurrentrelay/taps/fullcompletion alloutputs')
(root/'candidate/tb_controls.sv').write_text(s)
