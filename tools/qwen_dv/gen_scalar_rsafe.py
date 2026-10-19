#!/usr/bin/env python3
"""Production scalar reset/finite-ring variant; preserve arithmetic/data edges."""
import json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import die_port_bind as P
from reset_partition import statement_end,NBA

def bankify(text,module,clock,reset,rootfn):
 m=next(m for m in P.parse_modules(text,'safe scalar') if m.name==module)
 widths={n:m.width(n,m.env()) for n in m.ports}
 for x in re.finditer(r'\breg\s*(\[[^\]]+\])?\s*([^;]+);',m.body):
  rng=x.group(1);w=1
  if rng:
   hi,lo=rng[1:-1].split(':');w=abs(P.ev(hi,m.env())-P.ev(lo,m.env()))+1
  for n in x.group(2).split(','):
   n=n.strip().split('=')[0].strip()
   if re.fullmatch(r'\w+',n):widths[n]=w
 changes=[];banks=[]
 pat=re.compile(r'\balways\s*@\s*\([^)]*\bnegedge\s+'+reset+r'\s*\)')
 for a in pat.finditer(text):
  stop=statement_end(text,a.end());block=text[a.start():stop]
  # Reset arms are all literal zero; every retained clock arm stays verbatim.
  body=block[block.index(')')+1:].strip()
  if body.startswith('begin'):body=body[len('begin'):].strip();body=body[:body.rfind('end')].strip()
  cond=re.match(r'if\s*\(\s*!'+reset+r'\s*\)',body);assert cond,body[:80]
  end=statement_end(body,cond.end());resetarm=body[cond.end():end]
  for x in NBA.finditer(resetarm):
   assert P.ev(x.group(3).strip(),m.env()) == 0,x.group()
  normal=body[end:].strip();assert normal.startswith('else'),normal[:80];normal=normal[4:].strip()
  assignments=list(NBA.finditer(normal));assert not any(x.group(2) for x in assignments),module
  targets=sorted({x.group(1) for x in assignments});clones=[]
  for n in targets:
   w=widths[n];ix=len(banks);banks.append({'target':n,'bits':w})
   nxt=f'safe_next_{n}'
   def sub(x):return f'{nxt} = {x.group(3)};' if x.group(1)==n else ';'
   comb=NBA.sub(sub,normal)
   clones.append(f'reg [{w-1}:0] {nxt};\nalways @* begin {nxt}={n}; {comb} end\nqfd_dv_reset_bank #(.W({w})) safe_b_{n}(.ck({clock}),.rst_n({rootfn(ix)}),.d({nxt}),.q({n}));')
  changes.append((a.start(),stop,'\n'.join(clones)))
 for a,b,t in reversed(changes):text=text[:a]+t+text[b:]
 return text,banks

def extract(path,module):
 s=P.preprocess(P.strip_comments((ROOT/path).read_text()),{'OT_QFD_DV_SAFE_STORAGE':''})
 a=s.index('module '+module);b=s.index('endmodule',a)+len('endmodule');return s[a:b]

s=extract('rtl/qwen_dv/qfd_dv_scalar2.sv','qfd_dv_scalar2')
a=s.index('    integer k;');s=s[:a]+s[a:].replace('    integer k;','',1)
a=s.index('    always @(posedge ck or negedge rst_n)',s.index('wire [5:0] cnt_n'))
b=statement_end(s,s.index(')',a)+1)
old=s[a:b]
# Slot state is not reset in the original; retain its reset hold using a
# separate kept leaf per 32-bit slot. Preserve d,u,own write priority.
new='''always @(posedge ck or negedge rst_n) begin
 if(!rst_n) begin cnt<=0;trig<=0;end
 else begin
 trig<=0;
 if(cfg_v) cnt<=0;
 else if((d_ps||u_ps||o_ps)&&cnt_n==nb&&nb!=0) begin trig<=1;cnt<=0;end
 else cnt<=cnt_n;
 end
end
wire[31:0] slot_reset;
qfd_dv_reset_tree #(.N(32)) u_slot_rt(.ck(ck),.rst_n(safe_group[3]),.q(slot_reset));
generate for(genvar sr=0;sr<32;sr=sr+1) begin:g_slot_safe
 always @(posedge ck) if(slot_reset[sr]) begin
 if(cfg_v) s[sr]<=0;
 else begin
 if(d_ps&&dn_i[36:32]==sr) s[sr]<=dn_i[31:0];
 if(u_ps&&up_i[36:32]==sr) s[sr]<=up_i[31:0];
 if(o_ps&&ps_idx[4:0]==sr) s[sr]<=ps_val;
 end end
end endgenerate
'''
s=s[:a]+new+s[b:]
s,banks=bankify(s,'qfd_dv_scalar2','ck','rst_n',lambda i:f'safe_group[{0 if i<24 else 3}]')
assert len(banks)<48,len(banks)
s=s.replace('endmodule','wire[3:0] safe_group;\nqfd_dv_reset_tree #(.N(4)) u_reset_groups(.ck(ck),.rst_n(rst_n),.q(safe_group));\nendmodule')
# Arithmetic/valid child roots: one retained front copy per qadd; root group1
# has31 children, group2 owns5valid pipes+2FP+2valid+rsqrt(18roots)=27.
s=s.replace('.rst_n(rst_n)', '.rst_n(safe_group[2])')
s=s.replace('u_reset_groups(.ck(ck),.rst_n(safe_group[2])','u_reset_groups(.ck(ck),.rst_n(rst_n)')
s=s.replace('u_a (.clk(ck), .rst_n(safe_group[2])','u_a (.clk(ck), .rst_n(safe_group[1])')
# Rename only this soft subtree; hard lane sources remain unchanged.
rename={'ot_hdc_qadd':'qfd_safe_qadd','ot_hdc_qmul':'qfd_safe_qmul','ot_hdc_rsqrt_q':'qfd_safe_rsqrt','ot_hdc_vline':'qfd_safe_vline','ot_hdc_fp32_add_fast':'qfd_safe_add_fast','ot_hdc_fp32_mul_fast':'qfd_safe_mul_fast'}
extra=[];records={'scalar_banks':banks}
for name in ['ot_hdc_fp32_add_fast','ot_hdc_fp32_mul_fast']:
 x=extract('rtl/hdc/ot_hdc_fastfp.sv',name)
 x,bs=bankify(x,name,'clk','rst_n',lambda i:'safe_front')
 x=x.replace('endmodule','wire safe_front;\nqfd_dv_reset_tree #(.N(1)) u_front(.ck(clk),.rst_n(rst_n),.q(safe_front));\nendmodule')
 records[name]=bs;extra.append(x)
for name in ['ot_hdc_qadd','ot_hdc_qmul']:extra.append(extract('rtl/hdc/ot_hdc_fastfp.sv',name))
x=extract('rtl/hdc/ot_hdc_sfu_q.sv','ot_hdc_rsqrt_q')
x=x.replace('ot_hdc_delay','qfd_dv_ring_delay')
extra.append(x)
extra.append('''module qfd_safe_vline #(parameter integer D=1)(input wire clk,rst_n,v,output wire[D:0] vd);
 wire[D-1:0] line;
 qfd_dv_reset_bank #(.W(D)) u_b(.ck(clk),.rst_n(rst_n),.d((line<<1)|v),.q(line));
 assign vd={line,v};
endmodule''')
alltext=s+'\n'+'\n'.join(extra)
for a,b in rename.items():alltext=re.sub(r'\b'+a+r'\b',b,alltext)
(ROOT/'rtl/qwen_dv/qfd_dv_scalar2_rsafe.sv').write_text('// Generated by tools/qwen_dv/gen_scalar_rsafe.py\n'+alltext+'\n')
(ROOT/'results/arch/safe_qw_slice_1019/scalar_bank_model.json').write_text(json.dumps(records,indent=2)+'\n')
print('SAFE_SCALAR_BANKS',len(banks))
