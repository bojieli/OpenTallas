from pathlib import Path
import re,importlib.util,json
base=Path(__file__).parent; out=base/'coupon';out.mkdir(exist_ok=True)
helper=Path('/srv/opentallas-scratch/claude/wt/codex-kv-pc-collar-1029/physical/die_plan/qwen_kvsys/cores/harden/kvspc_input_collar.py')
sp=importlib.util.spec_from_file_location('collar',helper);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
s=(base/'source/rtl/qkd_kv_pc_chain_station_b.sv').read_text();h=s[:s.index(');')];h=re.sub(r'\(\*.*?\*\)','',h,flags=re.S)
ports=re.findall(r'^\s*(input|output)\s+(?:wire|reg)\s*(\[[^]\n]+\])?\s*(\w+)\s*[,)]',h,re.M)
# Last port lacks a delimiter in source header; include the terminating parenthesis.
last=re.search(r'output\s+reg\s+(fault)\s*$',h)
if last:ports.append(('output','','fault'))
assert len({n for _,_,n in ports})==len(ports)
ins=[p for p in ports if p[0]=='input'];outs=[p for p in ports if p[0]=='output']
def bits(w):
 if not w:return 1
 a,b=map(int,w.strip('[]').split(':'));return abs(a-b)+1
print('ports',ins,outs)
wrapper='`timescale 1ns/1ps\nmodule pc_chain_collar_good (\n'+',\n'.join(f'    {d} wire {"[0:0]" if n=="ck" else w} {n}' for d,w,n in ports)+'\n);\n    qkd_kv_pc_chain_station_b u_leaf (\n'+',\n'.join(f'        .{n}({n+"[0]" if n=="ck" else n})' for d,w,n in ports)+'\n    );\nendmodule\n'
wrapper,rec=m.transform_wrapper(wrapper,enabled=True)
(out/'input_collar.json').write_text(json.dumps(rec,indent=2))
(out/'wrappers.sv').write_text(wrapper+wrapper.replace('pc_chain_collar_good','pc_chain_collar_badbit').replace('pcin_di <= di;','pcin_di <= di ^ 780\'d4;')+wrapper.replace('pc_chain_collar_good','pc_chain_collar_badreset').replace('pcin_rst_n <= rst_n;',"pcin_rst_n <= 1'b1;"))
(out/'qkd_kv_pc_chain_station_b.sv').write_text(s);(out/'ot_kvpc_pin_ff.sv').write_text((base/'source/rtl/ot_kvpc_pin_ff.sv').read_text())
lines=['`timescale 1ns/1ps','module tb;','reg clk=0;always #5 clk=~clk;']
for d,w,n in ins:
 if n!='ck':lines.append(f'reg {w} {n}=\'0;')
for pref in ['g','p','b','r']:
 for d,w,n in outs:lines.append(f'wire {w} {pref}_{n};')
for pref,mod in [('g','qkd_kv_pc_chain_station_b'),('p','pc_chain_collar_good'),('b','pc_chain_collar_badbit'),('r','pc_chain_collar_badreset')]:
 con=[]
 for d,w,n in ports:con.append(f'.{n}({"clk" if n=="ck" else n if d=="input" else pref+"_"+n})')
 lines.append(f'{mod} u_{pref} ('+', '.join(con)+');')
pack=lambda p:'{'+','.join(p+'_'+n for _,_,n in outs)+'}'
wid=sum(bits(w) for _,w,n in outs)
lines +=[f'reg [{wid-1}:0] prior;always @(posedge clk) prior<={pack("g")};','integer cyc,bad=0,bitcaught=0,resetcaught=0,bootbeats=0,writerbeats=0,issues=0;','integer j;','initial begin','pc=5\'d5;cfg_stack=2\'d1;','for(cyc=0;cyc<4096;cyc=cyc+1)begin',' @(negedge clk);',' if(cyc>12)begin',f'  if({pack("p")} !== prior)begin bad=bad+1;if(bad<5)$display("BAD cyc=%0d",cyc);end',f'  if({pack("b")} !== prior)bitcaught=bitcaught+1;',f'  if({pack("r")} !== prior)resetcaught=resetcaught+1;',' end',' if(p_land_es[0])bootbeats=bootbeats+1; if(p_wes[0])writerbeats=writerbeats+1;if(p_emb_issue_v)issues=issues+1;'," rst_n=(cyc%512>=8);di='0;land_er='0;",' for(j=0;j<780;j=j+32)di={di,32\'($urandom)};',' di[0]=0;di[1]=0;di[615]=0;di[616]=0;di[719]=0;di[754]=0;di[779]=0;'," di[6:2]=5'd5;di[11:7]=5'd5;",' case(cyc%8)'," 0:di[779]=1'b1;", " 1:begin di[0]=1'b1;di[553]=1'b1;end", " 2:begin di[615]=1'b1;di[621:617]=5'd5;end", " 3:begin di[754]=1'b1;di[759:755]=5'd5;di[762:760]=3'd0;di[778:763]=16'd3;end", " 4:begin di[719]=1'b1;di[737:720]=18'd5;end",' default:begin end',' endcase','end','$display("COLLAR cycles=%0d bad=%0d bitcaught=%0d resetcaught=%0d boot=%0d writer=%0d issue=%0d",cyc,bad,bitcaught,resetcaught,bootbeats,writerbeats,issues);','if(bad!=0 || bitcaught==0 || resetcaught==0 || bootbeats<100 || writerbeats<100 || issues==0)$fatal(1,"COLLAR FAIL");','$finish;end','endmodule']
(out/'tb.sv').write_text('\n'.join(lines)+'\n')
