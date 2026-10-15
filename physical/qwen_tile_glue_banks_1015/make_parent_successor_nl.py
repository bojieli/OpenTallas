#!/usr/bin/env python3
"""qfd_tile_nl_banked_v1: the NODE-LESS compute tile with the SAME local clock-root partition as
qfd_tile_nk_banked_v1 (r13 NL helper, 2026-10-15).  Derived by text transformation of the frozen
NK banked sources (hash-guarded); the matvec part is SHARED unchanged with NK.

Differences vs NK banked (qfd_tile_nl has no n_a/n_b/n_y ports and NODE 0):
  * removed banks: face_n_b, face_n_y, node_stage_n_a, node_stage_n_b, node_stage_n_y; removed child: node leaf.
  * the node leaf's TOREG feed-through registers (NK: inside the CLOSED node leaf) become the logic's g_toreg
    capture, realised as ONE CLOSED qwen_glue_v514 bank 'to_reg' (slot of NK face_n_a; same edge, same value).
  * t_out path ages identical to NK: TOREG edge (to_reg) -> node_stage_t_out (+1, NK 'tileMEout+1') -> face_t_out.
  * fault bit: registered once (tf) before node_stage_t_out exactly as NK banked; the FAULT bench proves this is the
    reference's age (an unregistered variant reached t_out one cycle EARLY: c887 ct2 rt0, retained as a negative).
No other edge is added; ROM return +1 / xdelay9 / TX198 are the shared NK logic/matvec source.
"""
from pathlib import Path
import re,json,hashlib
ROOT=Path(__file__).resolve().parents[2]
NKD=ROOT/'rtl/qwen_sys/tile_parent_banked_20261015';OUT=ROOT/'rtl/qwen_sys/tile_parent_nl_banked_20261015';OUT.mkdir(exist_ok=True)
FROZEN={'rtl/qwen_sys/tile_parent_banked_20261015/ot_qwen_rom_tile_logic_banked_v1.sv':None,
        'rtl/qwen_sys/tile_parent_banked_20261015/qfd_tile_nk_banked_v1.sv':None,
        'rtl/physical/qfd_tile_nk_slot.sv':'d0f082b2efe651abbec5f093fe92798b8952dbafa01a5c6ea8741c69e5e50893'}
nkh=json.loads((ROOT/'results/rtl/qwen_compute_native_glue_1014/parent_banked_v1/source_hashes.json').read_text())
for n in FROZEN:
 want=FROZEN[n] or nkh[n]
 assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==want,'frozen input changed: '+n
def one(s,a,b):
 assert s.count(a)==1,(a[:100],s.count(a));return s.replace(a,b)
NK_NAMES=['strap']+[f'rqr_{side}_{i}' for side in ['south','north'] for i in range(4)]+[f'mq_wrom_{i}' for i in range(4)]+[f'xdelay_{i}' for i in range(8)]+[f'tx{g}_r{r}_lo' for g in range(8) for r in range(2)]+['face_n_a','face_n_b','face_n_y','face_t_out','face_tap','s2_word_0','s2_word_1','node_stage_n_a','node_stage_n_b','node_stage_n_y','node_stage_t_out']+[f'return_{side}_{i}' for side in ['south','north'] for i in range(4)]+['xdelay_extra','s2_x_full']
slot={n:i for i,n in enumerate(NK_NAMES)}
REMOVED=['face_n_b','face_n_y','node_stage_n_a','node_stage_n_b','node_stage_n_y']
TOR=slot['face_n_a']; slot['to_reg']=TOR
NL_NAMES=[('to_reg' if n=='face_n_a' else n) for n in NK_NAMES if n not in REMOVED]
assert len(NL_NAMES)==53
# ---- logic: g_toreg capture -> actual bank slot TOR
s=(NKD/'ot_qwen_rom_tile_logic_banked_v1.sv').read_text()
s=one(s,'module ot_qwen_rom_tile_logic_banked_v1','module ot_qwen_rom_tile_logic_nl_banked_v1')
s=one(s,'''        (* keep *) reg [W*32-1:0] t_out_q;
        (* keep *) reg            t_vout_q;
        always @(posedge clk) t_out_q <= t_out_i;
        always @(posedge clk or negedge rst_n) if (!rst_n) t_vout_q <= 1'b0; else t_vout_q <= t_vout_i;
        assign t_out = t_out_q;
        assign t_vout = t_vout_q;''',f'''        // NL: TOREG capture = actual CLOSED bank 'to_reg' (slot {TOR}); same edge and value
        assign bank_d_tor = {{1'b0, t_vout_i, t_out_i}};
        assign t_out = bank_q[{TOR*514} +: 512];
        assign t_vout = bank_q[{TOR*514+512}];''')
s=one(s,'    wire [58*514-1:0] bank_d_me;','    wire [58*514-1:0] bank_d_me;\n    wire [513:0] bank_d_tor;')
s=one(s,f'assign bank_d[{TOR*514} +: 514]=0;',f'assign bank_d[{TOR*514} +: 514]=bank_d_tor;')
s=s.replace('`ifndef SYNTHESIS\n    initial if(','`ifndef SYNTHESIS\n    initial if(',1)
s=one(s,'    localparam integer IBW =','''`ifndef SYNTHESIS
    initial if(NODE!=0 || TOREG!=1) $fatal(1,"nl_banked logic: NODE 0 / TOREG 1 only");
`endif
    localparam integer IBW =''')
(OUT/'ot_qwen_rom_tile_logic_nl_banked_v1.sv').write_text(s)
# ---- top: parse NK top for exact reset assignments, re-emit for NL
t=(NKD/'qfd_tile_nk_banked_v1.sv').read_text()
inst=re.compile(r'^(\w+) (\w+)\(\.clk\(ck_bank\[(\d+)\]\),\.rst_n\((r_\w+\[\d+\])\),\.d\(bank_d\[(\d+) \+: (\d+)\]\),\.q\(bank_q\[\d+ \+: \d+\]\)\);$',re.M)
nkb={m[2]:dict(master=m[1],ck=int(m[3]),rst=m[4],base=int(m[5]),w=int(m[6])) for m in inst.finditer(t)}
assert len(nkb)==58
child=dict(re.findall(r'^assign rst_child_n\[(\d+)\]=(r_\w+\[\d+\]);$',t,re.M));assert len(child)==14
resets=re.findall(r'^qkh_packet_v16 (reset_\w+)\(\.clk\(ck_reset\[\d+\]\),\.rst_n\(1\'b1\),\.d\(\{16\{(\S+?)\}\}\),\.q\(r_\w+\)\);$',t,re.M);assert len(resets)==11
core=re.search(r'^wire rst_core_n=(r_\w+\[\d+\]);',t,re.M)[1]
nkb['to_reg']=dict(master='qwen_glue_v514',rst=child['13'],base=TOR*514,w=514)   # node leaf's reset target, node's place
q=lambda n,w=None:f"bank_q[{slot[n]*514} +: {w or 514}]"
top=f'''// Versioned NODE-LESS native-parent successor (r13 NL helper 2026-10-15), generated by
// physical/qwen_tile_glue_banks_1015/make_parent_successor_nl.py from the frozen NK banked source.
// 53 CLOSED data banks (+11 reset +13 CLOSED children +1 residual root). Physical qualification OPEN.
module qfd_tile_nl_banked_v1 #(
`ifndef SYNTHESIS
 parameter integer ROM_TILE=-1,
`endif
 parameter integer GT=3072, SMIN=7, MUT=0
)(
 input wire ck, input wire [52:0] ck_bank, input wire [10:0] ck_reset,
 input wire [12:0] ck_child, input wire rst_n,
 input wire [15:0] tile_id, input wire [507:0] tap,
 output wire [513:0] t_out,
 output wire tie_hi,tie_lo
);
 assign tie_hi=1'b1;assign tie_lo=1'b0;
 wire [58*514-1:0] bank_d,bank_q,bank_d_logic;
'''
for i,(n,src) in enumerate(resets):top+=f'wire [15:0] r_{n};\n'
for i,(n,src) in enumerate(resets):top+=f"qkh_packet_v16 {n}(.clk(ck_reset[{i}]),.rst_n(1'b1),.d({{16{{{src}}}}}),.q(r_{n}));\n"
for i,n in enumerate(NL_NAMES):
 b=nkb[n];w=b['w']
 mut=''
 if n=='to_reg':
  # bench-only mutant 4 (to_reg bypass) without parameter overrides on the hard child (gate rule hard_child_params)
  top+=f"wire [513:0] tor_q;\n{b['master']} {n}(.clk(ck_bank[{i}]),.rst_n({b['rst']}),.d(bank_d[{b['base']} +: {w}]),.q(tor_q));\n"
  top+=f"`ifndef SYNTHESIS\nassign bank_q[{b['base']} +: {w}] = (MUT==4) ? bank_d[{b['base']} +: {w}] : tor_q;\n`else\nassign bank_q[{b['base']} +: {w}] = tor_q;\n`endif\n"
 else:
  top+=f"{b['master']} {n}(.clk(ck_bank[{i}]),.rst_n({b['rst']}),.d(bank_d[{b['base']} +: {w}]),.q(bank_q[{b['base']} +: {w}]));\n"
 if w<514:top+=f"assign bank_q[{b['base']+w} +: {514-w}]=0;\n"
for n in REMOVED:top+=f"assign bank_q[{slot[n]*514} +: 514]=0; assign bank_d[{slot[n]*514} +: 514]=0; // NK-only {n}\n"
top+=f'wire rst_core_n={core}; // UNPLACED residual root reset target (as NK)\nwire [13:0] rst_child_n;\n'
for i in range(13):top+=f"assign rst_child_n[{i}]={child[str(i)]};\n"
top+="assign rst_child_n[13]=1'b0; // no node leaf (NODE 0: inactive generate)\n"
top+=f'''assign bank_d[0 +: 16] = tile_id;
assign bank_d[16 +: 498] = 0;
assign bank_d[{slot['face_tap']*514} +: 508] = tap;
assign bank_d[{slot['face_tap']*514+508} +: 6] = 0;
assign bank_d[{slot['face_t_out']*514} +: 514] = {q('node_stage_t_out')};
 wire [507:0] tap_q={q('face_tap',508)};
 wire [511:0] to;wire tv,tile_fault;
 reg tf;
 always @(posedge ck or negedge rst_core_n) if(!rst_core_n) tf<=0; else tf<=tile_fault;
assign bank_d[{slot['node_stage_t_out']*514} +: 514] = {{tf,tv,to}};
assign t_out={q('face_t_out')};
 ot_qwen_rom_tile_logic_nl_banked_v1 #(
`ifndef SYNTHESIS
 .ROM_TILE(ROM_TILE),
`endif
 .TX_MUT(MUT==4 ? 0 : MUT),.NW(18),.GT(GT),.TG(4),.SMIN(SMIN),.CODE_BANKS(5),.KV_LOCAL(0),
 .MEM_EXTRA(1),.ACC_LAT(7),.FAST_ISSUE(1),.KV_PREP(4),.MUL_LAT(8),.TREE_LAT(7),
 .ROM_PIPE(1),.ROM_ARELAY(2),.ROM_CAP2(1),.ROM_CAPX(2),.LRST(3),.ARPB(1),.MPR(1),
 .HIER(2),.HIER_HARD(1),.TOREG(1),.TIDR(1),.LRR(1),.RPH(2),.RQR(1),.XTX(2),.ANR(1),.NDH(1),.NODE(0),.CHILD_CLOCKS(1)) u_logic(
 .bank_q(bank_q),.bank_d(bank_d_logic),.rst_child_n(rst_child_n),
 .ck_rpair(ck_child[4:0]),.ck_lsl(ck_child[12:5]),.ck_node(ck),
 .clk(ck),.rst_n(rst_core_n),.tile_id({q('strap',16)}),.ib_go(tap_q[0]),.ib(tap_q[379:1]),.xl(tap_q[507:380]),
 .t_out(to),.t_vout(tv),.n_a(512'b0),.n_b(512'b0),.n_va(1'b0),.n_y(),.n_vy(),.fault(tile_fault),
 .rom_ce(),.rom_addr(),.rom_addr_n(),.rom_addr_b(),.rom_req_m(),.rom_rd(2660'b0),
 .kvs_r_ce(),.kvs_r_addr(),.kvs_rd(512'b0),.kv_re(),.kv_addr(),.kv_q(2048'b0));
'''
top_owned={'strap','face_tap','face_t_out','node_stage_t_out'}|set(REMOVED)
for n in NK_NAMES:
 nn='to_reg' if n=='face_n_a' else n
 if nn in top_owned:continue
 top+=f"assign bank_d[{slot[nn]*514} +: 514]=bank_d_logic[{slot[nn]*514} +:514];\n"
top+='endmodule\n'
(OUT/'qfd_tile_nl_banked_v1.sv').write_text(top)
# ---- independent staged reference: original qfd_tile_nl + the SAME priced edges as NK's reference
#      (return +1 and tile output +1 come from the NK staged reference logic module; to_extra here)
ref=re.search(r'^module qfd_tile_nl\b.*?^endmodule',(ROOT/'rtl/physical/qfd_tile_nk_slot.sv').read_text(),re.M|re.S)[0]
ref=one(ref,'module qfd_tile_nl','module qfd_tile_nl_staged_reference')
ref=one(ref,'    ot_qwen_rom_tile_nk #(','    ot_qwen_rom_tile_nk_staged_reference #(')
ref=one(ref,'    (* keep *) reg [513:0] t_out_q;','    reg [513:0] to_extra;\n always @(posedge ck) to_extra<={tf,tv,to};\n    (* keep *) reg [513:0] t_out_q;')
ref=one(ref,'t_out_q[511:0]<=to;','t_out_q[511:0]<=to_extra[511:0];')
ref=one(ref,"reset_q ? {tf,tv} : 2'd0","reset_q ? to_extra[513:512] : 2'd0")
(OUT/'qfd_tile_nl_staged_reference.sv').write_text('// Numerical reference only: original qfd_tile_nl with the explicitly priced extra edges (needs the NK staged\n// reference logic/wrapper modules from rtl/qwen_sys/tile_parent_banked_20261015/qfd_tile_nk_staged_reference.sv).\n'+ref+'\n')
man={'schema':'qwen.compute.parent_nl_banked_v1','banks':[{'index':i,'inst':n,'master':nkb[n]['master'],'clock_port':f'ck_bank[{i}]','nk_slot':slot[n],'reset_target':nkb[n]['rst']} for i,n in enumerate(NL_NAMES)],
 'roots':{'data':53,'child':13,'reset':11,'residual':1},'removed_vs_nk':REMOVED+['u_node (CLOSED ot_qwen_tile_node)'],
 'added_vs_nk':{'to_reg':'qwen_glue_v514 at the node TOREG edge (NK: inside the node leaf); same edge'},
 'compiler_edges':'identical t_out age to NK banked; no n_* ports; ROM return +1, xdelay9, TX198 shared with NK',
 'status':'SOURCE_ASSEMBLY_NOT_PHYSICAL_QUALIFICATION'}
(OUT/'bank_manifest.json').write_text(json.dumps(man,indent=2)+'\n')
print('generated NL logic/top/reference: 53 data banks, 11 reset, 13 children')
