#!/usr/bin/env python3
"""Versioned source successor; original production modules remain byte-identical."""
from pathlib import Path
import re,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'rtl/qwen_sys/tile_parent_banked_20261015';OUT.mkdir(exist_ok=True)
FROZEN_INPUTS={'rtl/hdc/ot_qwen_w12_matvec.sv': '113f17dddbb3986b714cd4e7df04856c9675aa2affea34774b5cf56888b842a5', 'rtl/hdc/ot_qwen_rom_tile_w12.sv': 'cd8200cb36e4273e78d21a66a816a15e5c3b59b7cb678a692e7c8a51956634b2', 'rtl/physical/ot_qwen_rom_tile_nk.sv': '319061d4c2037e4503b7766bd60bfcb91516d36b708d756d8be18f2ace3b8c54', 'rtl/physical/qfd_tile_nk_slot.sv': 'd0f082b2efe651abbec5f093fe92798b8952dbafa01a5c6ea8741c69e5e50893'}
for n,expected in FROZEN_INPUTS.items():
 assert __import__("hashlib").sha256((ROOT/n if "ROOT" in globals() else root/n).read_bytes()).hexdigest()==expected, "original parent source changed: "+n
def module(path,name):
 s=(ROOT/path).read_text();m=re.search(r'^module '+name+r'\b.*?^endmodule',s,re.M|re.S);assert m,name;return m[0]
def replace(s,a,b):
 assert s.count(a)==1,(a[:90],s.count(a));return s.replace(a,b)
names=['strap']+[f'rqr_{side}_{i}' for side in ['south','north'] for i in range(4)]+[f'mq_wrom_{i}' for i in range(4)]+[f'xdelay_{i}' for i in range(8)]+[f'tx{g}_r{r}_lo' for g in range(8) for r in range(2)]+['face_n_a','face_n_b','face_n_y','face_t_out','face_tap','s2_word_0','s2_word_1','node_stage_n_a','node_stage_n_b','node_stage_n_y','node_stage_t_out']+[f'return_{side}_{i}' for side in ['south','north'] for i in range(4)]+['xdelay_extra','s2_x_full']
assert len(names)==58
idx={n:i for i,n in enumerate(names)}
def q(n,off=0,w=1):return f'bank_q[{idx[n]*514+off} +: {w}]'
def d(n,off=0,w=1):return f'bank_d[{idx[n]*514+off} +: {w}]'
def drive(n,expr,w):return f'assign {d(n,0,w)} = {expr};\n'+(f'assign {d(n,w,514-w)} = 0;\n' if w<514 else '')
ports='''    input wire [58*514-1:0] bank_q,
    output wire [58*514-1:0] bank_d,
    input wire [13:0] rst_child_n,
'''
# Full original issue/FP32 control machinery is retained. Only existing captures
# are exchanged for literal actual bank pins; TX compression is after RNE/mask.
s=module('rtl/hdc/ot_qwen_w12_matvec.sv','ot_qwen_w12_matvec_part').replace('module ot_qwen_w12_matvec_part','module ot_qwen_w12_matvec_part_banked_v1',1)
s=replace(s,'    input wire [7:0] ck_lsl,',ports+'    input wire [7:0] ck_lsl,')
s=replace(s,'    parameter integer CHILD_CLOCKS = 0,','    parameter integer TX_MUT = 0,\n    parameter integer CHILD_CLOCKS = 0,')
for a,b in [('reg [GL*W*((INT8_WEIGHT != 0 && WCONV == 0) ? 8 : 16)-1:0] mq_wrom;','wire [GL*W*((INT8_WEIGHT != 0 && WCONV == 0) ? 8 : 16)-1:0] mq_wrom;'),('reg [GL*32-1:0]   mq_x;','wire [GL*32-1:0]   mq_x;'),('reg [GL*W*32-1:0] s2_w, s3_w;','wire [GL*W*32-1:0] s2_w; reg [GL*W*32-1:0] s3_w;'),('reg [GL*32-1:0]   s2_x, s3_x;','wire [GL*32-1:0] s2_x; reg [GL*32-1:0] s3_x;')]:s=replace(s,a,b)
a=s.index('            mq_wrom <= wrom_q;');b=s.index('            s3_w <= s2_w;',a)
s=s[:a]+'            mq_kv <= kv_q;\n'+s[b:]
needle='    genvar xg;'
cap=''
for k in range(4):cap+=drive(f'mq_wrom_{k}',f'wrom_q[{256*k} +:256]',256)+f'assign mq_wrom[{256*k} +:256]={q(f"mq_wrom_{k}",0,256)};\n'
cap+=f'assign mq_x={q("xdelay_6",128,128)};\n'+drive('s2_x_full',"{mq_x[127:112],(TX_MUT==3 ? 16'b0:mq_x[111:96]),mq_x[95:80],(TX_MUT==3 ? 16'b0:mq_x[79:64]),mq_x[63:48],(TX_MUT==3 ? 16'b0:mq_x[47:32]),mq_x[31:16],(TX_MUT==3 ? 16'b0:mq_x[15:0])}",128)+f'assign s2_x={q("s2_x_full",0,128)};\n'
cap+='wire [1023:0] s2_bf_d;\ngenvar bl;\ngenerate for(bl=0;bl<64;bl=bl+1)begin:g_bank_bf\n assign s2_bf_d[16*bl+:16]=!s1b_gm[bl/16] ? 16\'b0 : s1b_wsrc ? mq_kv[32*bl+16+:16] : mq_wrom[16*bl+:16];\nend endgenerate\n'
for k in range(2):
 cap+=drive(f's2_word_{k}',f'{{2\'b0,s2_bf_d[{512*k} +:512]}}',514)
 for lane in range(32):cap+=f'assign s2_w[{32*(32*k+lane)} +:32]={{{q(f"s2_word_{k}",16*lane,16)},16\'b0}};\n'
s=replace(s,needle,cap+needle)
# The PART1 consumer uses only split from the delayed instruction tag.
# Keep full32 operands BEFORE RNE; remove unused tag transport explicitly.
s=replace(s,'reg  [TW-1:0] s1_tag, s1b_tag, s2_tag, s3_tag;', '''reg [3:0] s1_split,s1b_split,s2_split,s3_split;
    wire [TW-1:0] s1_tag={5'b0,s1_split,{(TW-9){1'b0}}};
    wire [TW-1:0] s1b_tag={5'b0,s1b_split,{(TW-9){1'b0}}};
    wire [TW-1:0] s2_tag={5'b0,s2_split,{(TW-9){1'b0}}};
    wire [TW-1:0] s3_tag={5'b0,s3_split,{(TW-9){1'b0}}};''')
s=replace(s,'wire [TW-1:0] m_tag;', "wire [3:0] m_split;")
s=replace(s,'ot_hdc_delay #(.W(TW + G + 3), .D(MEM_EXTRA)) u_mt', 'ot_hdc_delay #(.W(4 + G + 3), .D(MEM_EXTRA)) u_mt')
s=replace(s,'.d({e_tag, e_gm, e_first, e_wsrc, e_round}), .q({m_tag, m_gm, m_first, m_wsrc, m_round})', '.d({e_split, e_gm, e_first, e_wsrc, e_round}), .q({m_split, m_gm, m_first, m_wsrc, m_round})')
s=replace(s,'s1_tag <= m_tag; s1b_tag <= s1_tag; s2_tag <= s1b_tag; s3_tag <= s2_tag;', 's1_split<=m_split;s1b_split<=s1_split;s2_split<=s1b_split;s3_split<=s2_split;')
s=replace(s,'    localparam integer LW =', '''`ifndef SYNTHESIS
    initial if(W!=16 || G!=4 || PART!=1 || HIER!=2 || HIER_HARD!=1 || XTX!=2 || WCONV!=1 || MUL_LAT!=8)
       $fatal(1,"banked_v1 source only supports exact fixed native tile configuration");
`endif
    localparam integer LW =''')
# Exact real bank endpoints are literals per generated LSL index.
a=s.index('                if (XTX > 0) begin : g_tx');b=s.index('                // Native physical parent',a)
new='''                wire [197:0] pack_d;
                wire [389:0] unpack_q;
                ot_qwen_tx198_codec #(.MUT(TX_MUT==3 ? 0:TX_MUT)) codec(.full_d(tx_d),.packed_d(pack_d),.packed_q(tx_bank_q),.full_q(unpack_q));
                wire [197:0] tx_bank_q;
'''
for g in range(8):
 new+=f'                if(g=={g})begin:g_tx_bank{g}\n'+drive(f'tx{g}_r0_lo',"{58'b0,pack_d}",256)+drive(f'tx{g}_r1_lo',q(f'tx{g}_r0_lo',0,256),256)+f'assign tx_bank_q={q(f"tx{g}_r1_lo",0,198)};\nend\n'
new+='                assign tx_q=unpack_q;\n'
s=s[:a]+new+s[b:]
s=s.replace('.rst_n(rst_l), .v_d(tx_q[XW-1])','.rst_n(rst_child_n[5+g]), .v_d(tx_q[XW-1])')
part_owned={n for n in names if n.startswith(('mq_wrom_','tx','s2_word_')) or n=='s2_x_full'}
logic_owned={n for n in names if n.startswith(('rqr_','return_','xdelay_'))}
top_owned=set(names)-part_owned-logic_owned
s=s.rsplit('endmodule',1)[0]+''.join(f'assign {d(n,0,514)}=0;\n'for n in names if n not in part_owned)+'endmodule\n'
(OUT/'ot_qwen_w12_matvec_part_banked_v1.sv').write_text(s)
# ROM source wrapper logic: original real rpair children, original issue logic,
# new existing-edge packet banks plus balanced extra return edge.
s=module('rtl/hdc/ot_qwen_rom_tile_w12.sv','ot_qwen_rom_tile_logic_w12').replace('module ot_qwen_rom_tile_logic_w12','module ot_qwen_rom_tile_logic_banked_v1',1)
s=replace(s,'    input wire [CODE_BANKS-1:0] ck_rpair,',ports+'    input wire [CODE_BANKS-1:0] ck_rpair,')
s=replace(s,'    parameter integer CHILD_CLOCKS = 0','    parameter integer TX_MUT = 0,\n    parameter integer CHILD_CLOCKS = 0')
s=replace(s,'localparam integer ME_EXTRA = MEM_EXTRA + RX;','localparam integer ME_EXTRA = MEM_EXTRA + RX + 1; // actual balanced return capture (+1)')
s=replace(s,'reg  [TG*32-1:0] xl_q;','wire [TG*32-1:0] xl_q;')
s=replace(s,'    ot_hdc_delay #(.W(TG*32), .D(ME_EXTRA)) u_xm (.clk(clk), .rst_n(rst_n), .d(xl_r), .q(xl_i));','    // Literal fixed nine-stage path; spare alias captures keep all128 bits.\n')
# Emit each physical x bank once, with independent alias payload.
logical=['xdelay_0','xdelay_3','xdelay_1','xdelay_2','xdelay_extra','xdelay_4','xdelay_5','xdelay_6','xdelay_7']
xcode=f'assign xl_q={q("xdelay_0",128,128)};\n'
for j,n in enumerate(logical):
 low='xl_r' if j==0 else q(logical[j-1],0,128)
 high='xl' if n=='xdelay_0' else q('xdelay_7',0,128) if n=='xdelay_6' else "128'b0"
 xcode+=drive(n,f'{{{high},{low}}}',256)
xcode+=f'assign xl_i={q(logical[-1],0,128)};\n'
s=replace(s,'    // Literal fixed nine-stage path; spare alias captures keep all128 bits.\n',xcode)
s=replace(s,'always @(posedge clk) begin ib_q <= ib; xl_q <= xl; end','always @(posedge clk) begin ib_q <= ib; end')
s=s.replace('ot_qwen_w12_matvec_part #(','ot_qwen_w12_matvec_part_banked_v1 #(.TX_MUT(TX_MUT),',1)
s=replace(s,'        .ck_lsl(ck_lsl),','        .bank_q(bank_q),.bank_d(bank_d),.rst_child_n(rst_child_n),\n        .ck_lsl(ck_lsl),')
s=s.replace('.rst_n(rst_n), .ce_d(ce_pre[b])','.rst_n(rst_child_n[b]), .ce_d(ce_pre[b])')
# Native node uses new balanced input and output stages (one extra each).
s=replace(s,'.rst_n(rst_n), .a(na_x), .b(n_b), .va(n_va),','.rst_n(rst_child_n[13]), .a(na_x), .b(n_b), .va(n_va),')
a='''                (* keep *) reg [2*2*PWB-1:0] gs_q, gn_q;
                always @(posedge clk) begin gs_q <= rw[CODE_BANKS]; gn_q <= rwn[CODE_BANKS]; end
                assign wrom_q = gs_q | gn_q;'''
b='wire [1023:0] gs_q,gn_q,gs_r,gn_r;\n'
for side,rw,qq,rr in [('south','rw','gs_q','gs_r'),('north','rwn','gn_q','gn_r')]:
 for k in range(4):
  b+=drive(f'rqr_{side}_{k}',f'{rw}[CODE_BANKS][{256*k} +:256]',256)+f'assign {qq}[{256*k} +:256]={q(f"rqr_{side}_{k}",0,256)};\n'+drive(f'return_{side}_{k}',f'{qq}[{256*k} +:256]',256)+f'assign {rr}[{256*k} +:256]={q(f"return_{side}_{k}",0,256)};\n'
b+='assign wrom_q=gs_r|gn_r;'
s=replace(s,a,b)
s=s.replace('.bank_d(bank_d)', '.bank_d(bank_d_me)')
s=replace(s,'    localparam integer IBW =', '    wire [58*514-1:0] bank_d_me;\n    localparam integer IBW =')
s=s.rsplit('endmodule',1)[0]+''.join(f'assign {d(n,0,514)}='+ (f'bank_d_me[{idx[n]*514} +:514]' if n in part_owned else '0')+';\n'for n in names if n not in logic_owned)+'endmodule\n'
(OUT/'ot_qwen_rom_tile_logic_banked_v1.sv').write_text(s)
# Stable clock/root index manifest. Geometry may select H/V or legal orientations
# through a later explicitly hashed generator input, never an old parent receipt.
manifest=[]
for i,n in enumerate(names):
 master='qkh_packet_v256'
 if n=='strap':master='qkh_packet_v16'
 elif n=='face_tap':master='qwen_glue_v508'
 elif n.startswith(('face_','node_stage_','s2_word_')):master='qwen_glue_v514'
 elif n.startswith(('rqr_','mq_wrom_')) or n.startswith('xdelay_') and n not in ['xdelay_3','xdelay_extra']:master='qkh_packet_h256'
 manifest.append({'index':i,'inst':n,'master':master,'clock_port':f'ck_bank[{i}]','reset_target_index':i})
(OUT/'bank_manifest.json').write_text(json.dumps({'schema':'qwen.compute.parent_banked_v1','banks':manifest,'roots':{'data':58,'child':14,'reset':11,'residual':1},'status':'SOURCE_ASSEMBLY_NOT_PHYSICAL_QUALIFICATION'},indent=2)+'\n')
print('generated versioned logic, matvec and58-bank manifest')
# Bind current actual geometry variants and source-exact reset assignments.
plan=json.loads((ROOT/'physical/qwen_tile_glue_banks_1015/parent_plan_tx198.json').read_text())
body={x['inst']:x for x in plan['bodies']};assert [x['instance'] for x in plan['data_bank_clock_index']]==names
for z in manifest:z['master']=body[z['inst']]['master']
reset_names=['reset_root','reset_mid_w','reset_mid_e','reset_mid_high','reset_branch_w_low','reset_branch_w_mid','reset_branch_w_high0','reset_branch_w_high1','reset_branch_e_low','reset_branch_e_mid','reset_branch_e_high']
assert all(n in body for n in reset_names)
reset_assign={x['sink']:(x['source'],int(re.search(r'\[(\d+)\]',x['source_pin'])[1])) for x in plan['reset']['target_assignment']}
child_names=[]
for i in range(5):child_names.append(next(n for n in body if f'g_rb[{i}]' in n))
for i in range(8):child_names.append(next(n for n in body if f'g_sl[{i}]' in n))
child_names.append(next(n for n in body if n.endswith('.u_node')))
def rst_for(n):
 a,b=reset_assign[n];return f'r_{a}[{b}]'
top='''// Versioned native-parent successor. Geometry and source components are
// prerequisites only: actual residual clock/pin/PG/cut/STA qualification open.
module qfd_tile_nk_banked_v1 #(
`ifndef SYNTHESIS
 parameter integer ROM_TILE=-1,
`endif
 parameter integer GT=3072, SMIN=7, MUT=0
)(
 input wire ck, input wire [57:0] ck_bank, input wire [10:0] ck_reset,
 input wire [13:0] ck_child, input wire rst_n,
 input wire [15:0] tile_id, input wire [507:0] tap,
 input wire [513:0] n_a,n_b, output wire [513:0] n_y,t_out,
 output wire tie_hi,tie_lo
);
 assign tie_hi=1'b1;assign tie_lo=1'b0;
 wire [58*514-1:0] bank_d,bank_q;
'''
for n in reset_names:top+=f'wire [15:0] r_{n};\n'
for i,n in enumerate(reset_names):
 if i==0:rs='rst_n'
 else:
  legs=[x for x in plan['reset']['source_topology'] if x['sink']==n]
  unique={(x['source'],x['source_pin']) for x in legs};assert len(unique)==1
  src,pin=next(iter(unique));bit=int(pin[2:-1]);rs=f'r_{src}[{bit}]'
 top+=f'qkh_packet_v16 {n}(.clk(ck_reset[{i}]),.rst_n(1\'b1),.d({{16{{{rs}}}}}),.q(r_{n}));\n'
for z in manifest:
 n=z['inst'];i=z['index'];master=z['master'];width=514 if master=='qwen_glue_v514' else 508 if master=='qwen_glue_v508' else 16 if master=='qkh_packet_v16' else 256
 top+=f'{master} {n}(.clk(ck_bank[{i}]),.rst_n({rst_for(n)}),.d({d(n,0,width)}),.q({q(n,0,width)}));\n'
 if width<514:top+=f'assign {q(n,width,514-width)}=0;\n'
# Residual reset endpoint has no assigned physical home, and is recorded as such.
used={(a,b)for a,b in reset_assign.values()};free=next((n,k)for n in reset_names[4:] for k in range(16)if(n,k)not in used)
top+=f'wire rst_core_n=r_{free[0]}[{free[1]}]; // UNPLACED residual root reset target\nwire [13:0] rst_child_n;\n'
for i,n in enumerate(child_names):top+=f'assign rst_child_n[{i}]={rst_for(n)};\n'
for n,expr,w in [('strap','tile_id',16),('face_tap','tap',508),('face_n_a','n_a',514),('face_n_b','n_b',514),('node_stage_n_a',q('face_n_a',0,514),514),('node_stage_n_b',q('face_n_b',0,514),514),('face_n_y',q('node_stage_n_y',0,514),514),('face_t_out',q('node_stage_t_out',0,514),514)]:top+=drive(n,expr,w)
top+=f'''wire [513:0] na={q('node_stage_n_a',0,514)},nb={q('node_stage_n_b',0,514)};
 wire [507:0] tap_q={q('face_tap',0,508)};
 wire [511:0] to,ny;wire tv,nvy,tile_fault;
 reg tf,fy,mis;
 always @(posedge ck or negedge rst_core_n)begin
  if(!rst_core_n)begin tf<=0;fy<=0;mis<=0;end
  else begin tf<=tile_fault;mis<=mis|(na[512]^nb[512]);fy<=na[513]|nb[513]|mis;end
 end
'''+drive('node_stage_n_y','{fy,nvy,ny}',514)+drive('node_stage_t_out','{tf,tv,to}',514)+f'''assign n_y={q('face_n_y',0,514)};assign t_out={q('face_t_out',0,514)};
 ot_qwen_rom_tile_logic_banked_v1 #(
`ifndef SYNTHESIS
 .ROM_TILE(ROM_TILE),
`endif
 .TX_MUT(MUT),.NW(18),.GT(GT),.TG(4),.SMIN(SMIN),.CODE_BANKS(5),.KV_LOCAL(0),
 .MEM_EXTRA(1),.ACC_LAT(7),.FAST_ISSUE(1),.KV_PREP(4),.MUL_LAT(8),.TREE_LAT(7),
 .ROM_PIPE(1),.ROM_ARELAY(2),.ROM_CAP2(1),.ROM_CAPX(2),.LRST(3),.ARPB(1),.MPR(1),
 .HIER(2),.HIER_HARD(1),.TOREG(1),.TIDR(1),.LRR(1),.RPH(2),.RQR(1),.XTX(2),.ANR(1),.NDH(1),.CHILD_CLOCKS(1)) u_logic(
 .bank_q(bank_q),.bank_d(bank_d),.rst_child_n(rst_child_n),
 .ck_rpair(ck_child[4:0]),.ck_lsl(ck_child[12:5]),.ck_node(ck_child[13]),
 .clk(ck),.rst_n(rst_core_n),.tile_id({q('strap',0,16)}),.ib_go(tap_q[0]),.ib(tap_q[379:1]),.xl(tap_q[507:380]),
 .t_out(to),.t_vout(tv),.n_a(na[511:0]),.n_b(nb[511:0]),.n_va(na[512]),.n_y(ny),.n_vy(nvy),.fault(tile_fault),
 .rom_ce(),.rom_addr(),.rom_addr_n(),.rom_addr_b(),.rom_req_m(),.rom_rd(2660'b0),
 .kvs_r_ce(),.kvs_r_addr(),.kvs_rd(512'b0),.kv_re(),.kv_addr(),.kv_q(2048'b0));
endmodule
'''
top=top.replace('.bank_d(bank_d)', '.bank_d(bank_d_logic)')
top=top.replace('wire [58*514-1:0] bank_d,bank_q;', 'wire [58*514-1:0] bank_d,bank_q,bank_d_logic;')
top=top.rsplit('endmodule',1)[0]+''.join(f'assign {d(n,0,514)}=bank_d_logic[{idx[n]*514} +:514];\n'for n in names if n not in top_owned)+'endmodule\n'
(OUT/'qfd_tile_nk_banked_v1.sv').write_text(top)
manifest_doc={'schema':'qwen.compute.parent_banked_v1','banks':manifest,'roots':{'data':58,'child':14,'reset':11,'residual':1},'geometry_candidate_sha256':plan['candidate_sha256'],'reset_nodes':reset_names,'child_order':child_names,'residual_reset_unplaced':{'source':free[0],'bit':free[1]},'status':'SOURCE_ASSEMBLY_NOT_PHYSICAL_QUALIFICATION'}
(OUT/'bank_manifest.json').write_text(json.dumps(manifest_doc,indent=2)+'\n')
print('generated actual58 data,11 reset,14 child,1 residual root top')
