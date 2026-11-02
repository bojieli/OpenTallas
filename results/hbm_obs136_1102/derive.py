"""Finite SOURCE13 OBS physical-input projection; producer lemmas are external."""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--rtl-out',type=Path)
args=parser.parse_args()
IN=ROOT/'inputs'
OUT=ROOT/'generated'
OUT.mkdir(exist_ok=True)
for source,manifest in [('hbm_arch_root.sv','root_manifest.json'),
                        ('ot_hbm_obs_leaf.sv','obs_manifest.json'),
                        ('ot_rst_relay.sv','rst_manifest.json')]:
    expected=json.loads((IN/manifest).read_text())['sha256']
    assert hashlib.sha256((IN/source).read_bytes()).hexdigest()==expected,source
root=(IN/'hbm_arch_root.sv').read_text()
call=re.search(r'ot_hbm_obs_leaf #\(.*?\) u_u_obs_C \(\n(.*?)\n    \);',root,re.S)
assert call
expr=re.search(r'\.obs\(\{(.*?)\}\)',call[1],re.S)[1]
fields=[]
for value in expr.split(','):
    m=re.fullmatch(r'\s*(\w+)\[(\d+)(?::(\d+))?\]\s*',value)
    assert m,value
    name,hi,lo=m[1],int(m[2]),int(m[3] or m[2])
    assert hi>=lo
    fields.append((name,hi,lo))
mapping=[]
for name,hi,lo in reversed(fields):
    base=len(mapping)
    mapping.extend(dict(logical=base+offset,source=name,source_bit=bit)
                   for offset,bit in enumerate(range(lo,hi+1)))
assert len(mapping)==144
removed_by_source={'L125m_i_q':{3,4},'L117_i_q':{3,4},
                   'L118_i_q':{4,5},'L117m_i_q':{3,4}}
removed=[row['logical'] for row in mapping if row['source_bit'] in removed_by_source.get(row['source'],set())]
assert removed==[16,17,29,30,42,43,55,56],removed
retained=[row for row in mapping if row['logical'] not in removed]
assert len(retained)==136
for index,row in enumerate(retained):row['physical']=index

def expand(name):
    return '{'+f'{name}[135:49], 2\'b00, {name}[48:38], 2\'b00, {name}[37:27], 2\'b00, {name}[26:16], 2\'b00, {name}[15:0]'+'}'

gold=re.sub(r'^`line[^\n]*\n','',(IN/'ot_hbm_obs_leaf.sv').read_text(),flags=re.M)
header_end=gold.index(')(')+2
candidate=('// Default-off finite SOURCE13 root OBS specialization; no global selector.\n'
           '// Eight constants are reconstructed only AFTER136-wide p1/p2 capture.\n'
           'module ot_hbm_obs_leaf_fc136 #(\n'
           '    parameter integer LID=0,\n'
           '    parameter [511:0] SYNC_MASK=512\'d0\n)(\n'+gold[header_end:].lstrip('\n'))
candidate=candidate.replace('input  wire [N-1:0] obs','input  wire [135:0] obs',1)
candidate=candidate.replace('    localparam integer NW',
    '''    localparam integer N=144;
    localparam integer MUT=0;
    generate if (LID != 0 || SYNC_MASK != 512'd0) begin:g_unsupported_profile
        OT_HBM_OBS_FC136_REQUIRES_ROOT_LID0_SYNC0 refuse();
    end endgenerate
    localparam integer NW''',1)
candidate=candidate.replace('reg [N-1:0] p1, p2;','reg [135:0] p1, p2;',1)
anchor='    always @(posedge clk) begin p1 <= obs; p2 <= p1; end\n'
assert candidate.count(anchor)==1
candidate=candidate.replace(anchor,anchor+
    '    wire [143:0] logical_p1 = '+expand('p1')+';\n'+
    '    wire [143:0] logical_p2 = '+expand('p2')+';\n')
candidate=candidate.replace('(p1 & ~sm) | (p2 & sm)','(logical_p1 & ~sm) | (logical_p2 & sm)',1)
(OUT/'ot_hbm_obs_leaf_fc136.sv').write_text(candidate)
if args.rtl_out:
    args.rtl_out.parent.mkdir(parents=True,exist_ok=True)
    args.rtl_out.write_text(candidate)

# Root integration is a proposal for the independently pruned carriers. Never
# apply it to old-width buses or change the selected source root in this tool.
projected=[]
for name,hi,lo in fields:
    deleted=removed_by_source.get(name,set())
    keep=[bit for bit in range(lo,hi+1) if bit not in deleted]
    translated=[bit-sum(c<bit for c in deleted) for bit in keep]
    assert translated==list(range(translated[0],translated[-1]+1))
    projected.append(name+('['+str(translated[-1])+':'+str(translated[0])+']' if len(translated)>1 else '['+str(translated[0])+']'))
newcall=call[0].replace(call[0][:call[0].index('u_u_obs_C')],
                       'ot_hbm_obs_leaf_fc136 #(.LID(0), .SYNC_MASK(512\'d0)) ')
newcall=newcall.replace('{'+expr+'}','{'+', '.join(projected)+'}')
(OUT/'root_obs_fc136_PROPOSAL.sv').write_text('// Requires the matching four carrier projections; NOT APPLIED.\n'+newcall+'\n')

def view(text,name,p1,p2):
    text=re.sub(r'module\s+\w+', 'module '+name,text,count=1)
    text,n=re.subn(r'(output reg\s+\[31:0\]\s+r_d)\s*\n\);',
        r'\1,\n    output wire [586:0] proof_state\n);',text,count=1)
    assert n==1
    state='{'+', '.join([p1,p2,'sticky','a_v','a_idx','a_d','b_v','b_idx','b_d',
                         'oh0','oh1','clr','r_v','r_idx','r_d','lrst_n'])+'}'
    return text.replace('endmodule','    assign proof_state = '+state+';\nendmodule',1)

(OUT/'gold_view.sv').write_text(view(gold,'obs_gold_view','p1','p2'))
(OUT/'candidate_view.sv').write_text(view(candidate,'obs_candidate_view','logical_p1','logical_p2'))
mutant=view(candidate,'obs_candidate_view','logical_p1','logical_p2')
# Wrong retained bit, not a deleted bit or producer-constant assumption.
mutant=mutant.replace('p1[15:0]}','p1[15:1], p1[1]}',1)
assert mutant!=view(candidate,'obs_candidate_view','logical_p1','logical_p2')
(OUT/'mutant_view.sv').write_text(mutant)
miter='''module projection_miter(input wire clk,rst_n,input wire [135:0] obs136,
 input wire q_v,input wire[7:0]q_idx,input wire[31:0]q_d,output wire mismatch);
 wire[143:0]gold_obs=EXPAND;
 wire[586:0]gs,cs;wire gv,cv;wire[7:0]gi,ci;wire[31:0]gd,cd;
 obs_gold_view #(.N(144),.LID(0),.SYNC_MASK(512'd0),.MUT(0)) g(
 .clk(clk),.rst_n(rst_n),.obs(gold_obs),.q_v(q_v),.q_idx(q_idx),.q_d(q_d),
 .r_v(gv),.r_idx(gi),.r_d(gd),.proof_state(gs));
 obs_candidate_view #(.LID(0),.SYNC_MASK(512'd0)) c(
 .clk(clk),.rst_n(rst_n),.obs(obs136),.q_v(q_v),.q_idx(q_idx),.q_d(q_d),
 .r_v(cv),.r_idx(ci),.r_d(cd),.proof_state(cs));
 // Only proof monitors initialize. DUT state is universally unconstrained.
 reg[2:0] reset_edges=0;reg qualified=0;
 always @(posedge clk)if(!qualified)begin
  if(!rst_n)begin if(reset_edges==3)qualified<=1;else reset_edges<=reset_edges+1'b1;end
  else reset_edges<=0;
 end
 assign mismatch=qualified && (gs!=cs || {gv,gi,gd}!={cv,ci,cd});
endmodule
'''.replace('EXPAND',expand('obs136'))
(OUT/'projection_miter.sv').write_text(miter)
bench='''`timescale 1ns/1fs
module tb_projection;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,q_v=0;reg[7:0]q_idx=0;reg[31:0]q_d=0;reg[135:0]obs136=0;
 wire[143:0]gold_obs=EXPAND;
 wire gv,cv;wire[7:0]gi,ci;wire[31:0]gd,cd;
 ot_hbm_obs_leaf #(.N(144),.LID(0),.SYNC_MASK(512'd0),.MUT(0)) g(
 .clk(clk),.rst_n(rst_n),.obs(gold_obs),.q_v(q_v),.q_idx(q_idx),.q_d(q_d),.r_v(gv),.r_idx(gi),.r_d(gd));
 ot_hbm_obs_leaf_fc136 #(.LID(0),.SYNC_MASK(512'd0)) c(
 .clk(clk),.rst_n(rst_n),.obs(obs136),.q_v(q_v),.q_idx(q_idx),.q_d(q_d),.r_v(cv),.r_idx(ci),.r_d(cd));
 integer checked=0,cycles=0,i,j,logical_bit;
 always @(posedge clk)begin
  #0.000001;
  if(cycles>=6)begin
   if({gv,gi,gd}!=={cv,ci,cd})$fatal(1,"OBS136_PROJECTION_MISMATCH cycle=%0d gold=%h candidate=%h",cycles,{gv,gi,gd},{cv,ci,cd});
   checked=checked+1;
  end
  cycles=cycles+1;
 end
 function integer old_index(input integer physical);
  begin
   if(physical<16)old_index=physical;
   else if(physical<27)old_index=physical+2;
   else if(physical<38)old_index=physical+4;
   else if(physical<49)old_index=physical+6;
   else old_index=physical+8;
  end
 endfunction
 initial begin
  repeat(6)@(negedge clk);rst_n=1;
  // Every retained input is exercised at its OLD logical debug-word index.
  for(i=0;i<136;i=i+1)begin
   @(negedge clk);obs136=136'd1<<i;q_v=1;q_d=0;
   logical_bit=old_index(i);q_idx=logical_bit/32;
   repeat(8)@(negedge clk);
   obs136=0;q_idx=16|(logical_bit/32); // sticky read and same-bank clear
   repeat(8)@(negedge clk);
  end
  // Live/sticky/padded words, nonmatching LID, passthrough data and q bubbles.
  for(i=0;i<1024;i=i+1)begin
   @(negedge clk);obs136={$random,$random,$random,$random,$random};
   q_idx=i%256;q_v=(i%7!=0);q_d=$random;
   if(i==333 || i==777)begin
    #0.1;rst_n=0;repeat(5)@(negedge clk);rst_n=1;
   end
  end
  q_v=0;obs136=0;repeat(10)@(negedge clk);
  $display("OBS136_LOCKSTEP_PASS checked=%0d retained136 oldlogical144 allquerybytes sticky_clear warmreset no_added_cycles",checked);
  $finish;
 end
endmodule
'''.replace('EXPAND',expand('obs136'))
(OUT/'tb_projection.sv').write_text(bench)
# Runtime mutant uses the same wrong retained bit as the formal view.
mutant_production=candidate.replace('p1[15:0]}','p1[15:1], p1[1]}',1)
assert mutant_production!=candidate
(OUT/'mutant_production.sv').write_text(mutant_production)
receipt=dict(scope='FINITE_SOURCE13_ROOT_OBS144_TO_PHYSICAL136_PROJECTION_ONLY',
    selected=dict(N=144,LID=0,SYNC_MASK=0,MUT=0),new_master='ot_hbm_obs_leaf_fc136',
    physical_inputs=136,logical_indices=144,removed_logical_indices=removed,
    removed=[r for r in mapping if r['logical'] in removed],retained=retained,
    reconstructed_after_capture=True,q_r_added_cycles=0,
    new_source_capture_widths=dict(p1=136,p2=136),old_source_capture_widths=dict(p1=144,p2=144),
    producer_constant_semantics_proved=False,full_R2_closed=False,physical_qualified=False,
    default_selector_changed=False,proposal_applied=False)
(OUT/'projection.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('OBS136_DERIVED removed='+','.join(map(str,removed))+' retained136 logical144; no source adoption')
