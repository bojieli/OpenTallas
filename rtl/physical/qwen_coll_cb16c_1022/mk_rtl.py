#!/usr/bin/env python3
"""CB16c-COLL 10-22: derive the regional-split body copies from the face RTL at 2919e5896 by exact substitutions."""
import re, sys, pathlib
WT = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2])
def module(path, name):
    t = (WT / path).read_text()
    m = re.search(r'(?ms)^module %s\b.*?^endmodule\b' % re.escape(name), t)
    assert m, name
    return m.group(0)
def sub(text, old, new, n=1):
    c = text.count(old)
    assert c == n, (old[:80], c)
    return text.replace(old, new)

# 1. RX CDC channel with the output register external (o_data = rd_stage; the slice is the old o_data stage)
ch = module('rtl/physical/ot_qfd_static_transport.sv', 'qfd_static_ch546_regional')
ch = sub(ch, 'module qfd_static_ch546_regional (', 'module qfd_static_ch546_regional_ox (')
ch = sub(ch, 'output reg o_valid,output reg [545:0] o_data,', 'output reg o_valid,output wire [545:0] o_data,')
ch = sub(ch, 'always @(posedge rck)begin ra<=r_addr;rd_stage<=memory_data;o_data<=rd_stage;end',
         'always @(posedge rck)begin ra<=r_addr;rd_stage<=memory_data;end\n'
         ' // CB16c-COLL: the o_data stage is the face rx_data slice (qfd_coll_eslice182 on an rx_rck entry), outside.\n'
         ' assign o_data=rd_stage;')

# 2. codec with the PHY-region RX path XR edges longer (slice in front of the RX ring): expected tokens follow XR later
lk = module('rtl/physical/qwen_coll_safe_1019/ot_coll_phy_land.sv', 'ot_qwen_static_slot_link_pl')
lk = sub(lk, 'module ot_qwen_static_slot_link_pl #(', 'module ot_qwen_static_slot_link_plx #(')
lk = sub(lk, 'LD=2, LK=1, BWREG=1, BLOCAL=0', 'LD=2, LK=1, BWREG=1, BLOCAL=0, XR=1')
lk = sub(lk, '''    reg [LK-1:0] ev_q;
    reg [6*LK-1:0] es_q;
    always @(posedge ck[0]) if(!rs_c[2]) ev_q<={LK{1'b0}}; else ev_q<={ev_q,rx_expect_v};
    always @(posedge ck[0]) es_q<={es_q,rx_expect_slot};
    wire ev_l=ev_q[LK-1];
    wire [5:0] es_l=es_q[6*LK-1-:6];''',
'''    // CB16c-COLL: the frame reaches this ring XR edges after the face pin (phy_rx slice + phy_rx_valid/phy_up regs),
    // so the expected tokens (issued at the pin cycle) follow by LK + XR edges.
`ifdef OT_CB16C_MUT_NOXR
    localparam integer LE = LK;
`else
    localparam integer LE = LK + XR;
`endif
    reg [LE-1:0] ev_q;
    reg [6*LE-1:0] es_q;
    always @(posedge ck[0]) if(!rs_c[2]) ev_q<={LE{1'b0}}; else ev_q<={ev_q,rx_expect_v};
    always @(posedge ck[0]) es_q<={es_q,rx_expect_slot};
    wire ev_l=ev_q[LE-1];
    wire [5:0] es_l=es_q[6*LE-1-:6];''')

# 3. face body: SAFE=1 PLAND=1 TOK_REG=1 OT_COLL_REGIONAL form of qfd_coll_static_face with the four pin ranks moved out
fc = module('rtl/physical/ot_qfd_coll_static_face.sv', 'qfd_coll_static_face')
fc = sub(fc, 'module qfd_coll_static_face #(', 'module qfd_coll_static_face_x #(')
fc = sub(fc, ' PLAND=0, PLD=2, PLK=1\n)(', ' PLAND=0, PLD=2, PLK=1,\n // CB16c-COLL 10-22: XT extra TX edges after phy_tx (face slice), XR extra RX edges before the RX ring (face slice +\n // phy_rx_valid / phy_up regs). Caller L = original L + XT + XR.\n XT=1, XR=1\n)(')
# tx_data pin register = the face tx slice (qfd_coll_eslice182 on a cal_ck entry): td_q removed, same edge count
fc = sub(fc, '  reg ts_q,tv_q,ps_q;reg[FW-1:0]td_q;reg[3:0]cf_q;\n  always @(posedge cal_ck)begin ts_q<=tx_slot;tv_q<=tx_valid;td_q<=tx_data;ps_q<=peer_slot;end',
             '  reg ts_q,tv_q,ps_q;reg[3:0]cf_q;\n  // CB16c-COLL: td_q is the face tx_data slice (outside, on its own cal_ck entry); tx_data arrives registered.\n  always @(posedge cal_ck)begin ts_q<=tx_slot;tv_q<=tx_valid;ps_q<=peer_slot;end')
fc = sub(fc, 'assign {tx_slot_i,tx_valid_i,tx_data_i,peer_slot_i}={ts_q,tv_q,td_q,ps_q};assign cdc_fault=cf_q;',
             'assign {tx_slot_i,tx_valid_i,tx_data_i,peer_slot_i}={ts_q,tv_q,tx_data,ps_q};assign cdc_fault=cf_q;')
fc = sub(fc, ' localparam integer PTX = PLAND ? 1+PLK : 0;   // extra TX edges controller -> PHY pin\n localparam integer PRX = PLAND ? PLK : 0;     // extra RX edges PHY pin -> controller',
             ' localparam integer PTX = (PLAND ? 1+PLK : 0) + XT;   // extra TX edges controller -> PHY pin (incl. the face slice)\n'
             '`ifdef OT_CB16C_MUT_NOXR\n localparam integer PRX = PLAND ? PLK : 0;\n`else\n localparam integer PRX = (PLAND ? PLK : 0) + XR;     // extra RX edges PHY pin -> controller (incl. the face slice)\n`endif\n'
             '`ifdef OT_CB16C_MUT_NOXT\n localparam integer PSL = 4 + PTX - XT;\n`else\n localparam integer PSL = 4 + PTX;\n`endif')
fc = sub(fc, 'ot_coll_dly1 #(.N(4+PTX),.SAFE_RING(1))u_slots(', 'ot_coll_dly1 #(.N(PSL),.SAFE_RING(1))u_slots(')
for a in ('`ifdef OT_COLL_REGIONAL\n qfd_static_ch546_regional u_tx(\n`else\n qfd_static_ch546 u_tx(\n`endif\n',):
    fc = sub(fc, a, ' qfd_static_ch546_regional u_tx(\n')
fc = sub(fc, '`ifdef OT_COLL_REGIONAL\n qfd_static_ch546_regional u_rx(\n`else\n qfd_static_ch546 u_rx(\n`endif\n', ' qfd_static_ch546_regional_ox u_rx(\n')
# PHY pins: TX frame + valid reach the face pin XT edges later (slice / valid reg); RX valid / up XR regs before the ring
fc = sub(fc, ''' ot_qwen_static_slot_link_pl #(.FW(FW),.CW(32),.SAFE(SAFE),.LD(PLD),.LK(PLK))u_codec(.ck(codec_ck),.phy_ck(codec_phy_ck),.rst_n(rst_n),''',
''' wire c_ptv,x_prv,x_up;
 // CB16c-COLL XT/XR = 1: phy_tx (597) and phy_rx (597) ranks are the face E slices on codec0p entries; the 1-bit
 // valid / up companions get the same one edge here, on codec_phy_ck beside the body's PHY band.
 reg ptv_q,prv_q,up_q;
 always @(posedge codec_phy_ck)begin ptv_q<=c_ptv;prv_q<=phy_rx_valid;up_q<=phy_up;end
 assign phy_tx_valid=ptv_q;assign x_prv=prv_q;assign x_up=up_q;
 initial if(XT!=1 || XR!=1 || !PLAND || !SAFE || !TOK_REG)$error("qfd_coll_static_face_x: built for XT=XR=1, PLAND, SAFE, TOK_REG");
 ot_qwen_static_slot_link_plx #(.FW(FW),.CW(32),.SAFE(SAFE),.LD(PLD),.LK(PLK),.XR(XR))u_codec(.ck(codec_ck),.phy_ck(codec_phy_ck),.rst_n(rst_n),''')
fc = sub(fc, ''' .p_tx_up(phy_up),.p_tx_v(phy_tx_valid),.p_tx_flit(phy_tx),.p_rx_v(phy_rx_valid),.p_rx_flit(phy_rx),
 .rx_v(codec_valid),.rx_flit(codec_data),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
 end else begin:g_codec''', ''' .p_tx_up(x_up),.p_tx_v(c_ptv),.p_tx_flit(phy_tx),.p_rx_v(x_prv),.p_rx_flit(phy_rx),
 .rx_v(codec_valid),.rx_flit(codec_data),.epoch_abort(epoch_abort),.fault_cause(fault_cause));
 end else begin:g_codec''')
# rx calendar: the peer's TX extras now include its slice (PTX); the RX CDC write follows PRX (incl. XR)
assert '.PHY(PHY+PTX)' in fc and '.WX(PRX)' in fc
hdr = ('`timescale 1ns/1ps\n'
'// CB16c-COLL 10-22 (ALT to the flat qfd_coll_face_*_pl leaves; STEWARD-QKc / SQC-CB16c): regional split of a Qwen\n'
'// collective face. GENERATED by mk_rtl.py from the face RTL at 2919e5896 by exact substitutions (do not hand-edit):\n'
'//   qfd_static_ch546_regional_ox  = qfd_static_ch546_regional with o_data = rd_stage (its o_data rank -> rx slice)\n'
'//   ot_qwen_static_slot_link_plx  = ot_qwen_static_slot_link_pl with the expected RX tokens LK + XR edges late\n'
'//   qfd_coll_static_face_x        = qfd_coll_static_face (SAFE/PLAND/TOK_REG/REGIONAL form) with td_q -> tx slice,\n'
'//                                   o_data -> rx slice, phy_tx +XT (slice), phy_rx +XR (slice) consumed by the calendar\n')
(OUT / 'qfd_coll_face_cx_body.sv').write_text(hdr + '\n' + ch + '\n\n' + lk + '\n\n' + fc + '\n')
print('wrote', OUT / 'qfd_coll_face_cx_body.sv')
