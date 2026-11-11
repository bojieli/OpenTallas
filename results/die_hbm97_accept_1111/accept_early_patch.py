#!/usr/bin/env python3
"""DIE-HBM-97 (C) u_control acceptance rebalance, define-gated (OT_DMA_ACCEPT_EARLY), 0 cycles.

Applies to ot_hgi_dma_back_static_vp4_banks.sv (module ot_hgi_dma_back_static_vp4_controller).
With the define off the preprocessed token stream is the original (only `ifdef/`define lines are added), so every
other user elaborates byte-identically (eq/identity.sh).

With the define on:
 1. horizontal end sum one stage earlier: q_hbase_end (p->q) and b_hend = q_hbase_end + b_hprod-operands (q->b);
    c-stage acceptance is compare-only (was 41-bit add + compare, routed TT -108 ps b_mv -> c_hok).
 2. valid_move registered: c_valid_0..3 <= AND of the next c_* terms (keep, 4 copies split by load group g<5/<9/<13/else);
    cv copies cv_0..3 (keep) for the same groups.
 3. chunks copies chunks_i (issue), chunks_m (match/nd regs), chunks_c (read enables/masks), chunks_a (drain address
    regs), each with its own drain_slot_* compare.
 4. bank_read_addr carry-select: {lo3+b carry ? hi+1 : hi, (lo3+b)[2:0]} with one shared 29-bit increment.
FORMAL (with -DFORMAL): inductive invariants proving each new signal equals the one it replaces wherever it is used.
NEG controls: OT_DMA_ACCEPT_EARLY_NEG (c_valid drops the hok term), _NEG2 (b_hend +1), _NEG3 (carry-select hi+2).
Usage: accept_early_patch.py IN.sv OUT.sv
"""
import sys

src = open(sys.argv[1]).read()


def rep(old, new):
    global src
    n = src.count(old)
    assert n == 1, (n, old[:80])
    src = src.replace(old, new)


S = '`OT_ACC_SEL'

# 0. selector macro + declarations
rep("""    wire [6:0] bank_read_slot,bank_write_slot;
    reg [255:0] bank_read_addr;
""", """    wire [6:0] bank_read_slot,bank_write_slot;
    reg [255:0] bank_read_addr;
`ifdef OT_DMA_ACCEPT_EARLY
`define OT_ACC_SEL(e,o) e
`else
`define OT_ACC_SEL(e,o) o
`endif
""")
rep("""    reg [7:0] chunks,issue_index,drain_index,row_chunks,column;
""", """    reg [7:0] chunks,issue_index,drain_index,row_chunks,column;
`ifdef OT_DMA_ACCEPT_EARLY
    // (C) per-consumer copies; keep: same value, separate drivers (no merge back into one star net)
    (* keep = "true" *) reg [7:0] chunks_i,chunks_m,chunks_c,chunks_a;
    (* keep = "true" *) reg c_valid_0,c_valid_1,c_valid_2,c_valid_3;
    (* keep = "true" *) reg cv_0,cv_1,cv_2,cv_3;
    reg [40:0] q_hbase_end,b_hend;
`endif
""")
rep("""    reg [7:0] drain_column;
""", """    reg [7:0] drain_column;
`ifdef OT_DMA_ACCEPT_EARLY
    // (C) bank read address carry-select: one shared 29-bit increment instead of eight 32-bit adds
    function automatic [31:0] cs_addr(input [28:0] hi, input [28:0] hi1, input [2:0] lo, input [3:0] k);
        reg [3:0] s;
        begin s={1'b0,lo}+k; cs_addr={s[3]?hi1:hi,s[2:0]}; end   // exact: lo+k <= 15, carry into hi is 0 or 1
    endfunction
`ifdef OT_DMA_ACCEPT_EARLY_NEG3
    wire [28:0] dc_hi1=drain_chunk_hbm[36:8]+29'd2;
`else
    wire [28:0] dc_hi1=drain_chunk_hbm[36:8]+29'd1;
`endif
`endif
""")
# 1. slot / valid wires
rep("""    wire issue_slot=busy&&!cv&&issue_index<chunks&&m_issue;
    wire drain_slot=busy&&!cv&&drain_index<chunks&&m_drain;
    wire valid_move=c_static_ok&&c_vok&&c_nchunk_ok&&c_hok&&c_ilead_ok&&c_lag_ok;
""", """    wire issue_slot=busy&&!cv&&issue_index<%s(chunks_i,chunks)&&m_issue;
    wire drain_slot=busy&&!cv&&drain_index<chunks&&m_drain;
`ifdef OT_DMA_ACCEPT_EARLY
    wire drain_slot_m=busy&&!cv&&drain_index<chunks_m&&m_drain;
    wire drain_slot_c=busy&&!cv&&drain_index<chunks_c&&m_drain;
    wire drain_slot_a=busy&&!cv&&drain_index<chunks_a&&m_drain;
    wire valid_move=c_valid_0;
`else
    wire valid_move=c_static_ok&&c_vok&&c_nchunk_ok&&c_hok&&c_ilead_ok&&c_lag_ok;
`endif
""" % S)
rep("""            assign chunk_cv[g]=cv;
            assign chunk_valid[g]=valid_move;
""", """            assign chunk_cv[g]=%s((g<5?cv_0:g<9?cv_1:g<13?cv_2:cv_3),cv);
            assign chunk_valid[g]=%s((g<5?c_valid_0:g<9?c_valid_1:g<13?c_valid_2:c_valid_3),valid_move);
""" % (S, S))
# 4. carry-select read address
rep("""        for(integer b=0;b<8;b=b+1)bank_read_addr[b*32+:32]<=drain_chunk_hbm[36:5]+32'(b)+((MUT==1&&b==1)?32'd1:32'd0);
""", """`ifdef OT_DMA_ACCEPT_EARLY
        for(integer b=0;b<8;b=b+1)bank_read_addr[b*32+:32]<=cs_addr(drain_chunk_hbm[36:8],dc_hi1,drain_chunk_hbm[7:5],4'(b)+((MUT==1&&b==1)?4'd1:4'd0));
`else
        for(integer b=0;b<8;b=b+1)bank_read_addr[b*32+:32]<=drain_chunk_hbm[36:5]+32'(b)+((MUT==1&&b==1)?32'd1:32'd0);
`endif
""")
# match registers use drain_slot_m
rep("""        m_drain<=drain_slot?1'b1:""", """        m_drain<=%s(drain_slot_m,drain_slot)?1'b1:""" % S)
rep("""        m_pre<=drain_slot?1'b0:""", """        m_pre<=%s(drain_slot_m,drain_slot)?1'b0:""" % S)
rep("""else if(drain_slot)nd_m2<=inc32(nd_m2);""", """else if(%s(drain_slot_m,drain_slot))nd_m2<=inc32(nd_m2);""" % S)
rep("""else if(drain_slot)nd_m3<=inc32(nd_m3);""", """else if(%s(drain_slot_m,drain_slot))nd_m3<=inc32(nd_m3);""" % S)
# CONTROL: reset + copies
rep("""            pending_sectors<=0;
            for(integer t=0;t<8;t=t+1)expect_mask[t]<=0;
""", """            pending_sectors<=0;
`ifdef OT_DMA_ACCEPT_EARLY
            chunks_i<=0;chunks_m<=0;chunks_c<=0;chunks_a<=0;cv_0<=0;cv_1<=0;cv_2<=0;cv_3<=0;
`endif
            for(integer t=0;t<8;t=t+1)expect_mask[t]<=0;
""")
rep("""            cv<=b_v;mv_src<=0;mv_done<=0;wb_reserve_v<=0;
""", """            cv<=b_v;mv_src<=0;mv_done<=0;wb_reserve_v<=0;
`ifdef OT_DMA_ACCEPT_EARLY
            cv_0<=b_v;cv_1<=b_v;cv_2<=b_v;cv_3<=b_v;
`endif
""")
rep("""            if(busy&&!cv&&drain_index<chunks)begin
                if(drain_slot)begin
                    if(drain_index+1'b1<chunks)begin""", """            if(busy&&!cv&&drain_index<%s(chunks_c,chunks))begin
                if(%s(drain_slot_c,drain_slot))begin
                    if(drain_index+1'b1<%s(chunks_c,chunks))begin""" % (S, S, S))
rep("""            read_mask_q<=drain_slot?drain_mask:8'd0;""", """            read_mask_q<=%s(drain_slot_c,drain_slot)?drain_mask:8'd0;""" % S)
rep("""            first_drain_q<=drain_slot&&drain_index==0;""", """            first_drain_q<=%s(drain_slot_c,drain_slot)&&drain_index==0;""" % S)
rep("""            if(drain_slot)begin
                drain_index<=drain_index+1'b1;""", """            if(%s(drain_slot_a,drain_slot))begin
                drain_index<=drain_index+1'b1;""" % S)
rep("""                else begin chunks<=8'(c_nchunk);row_chunks<=c_rchunk;""", """                else begin chunks<=8'(c_nchunk);row_chunks<=c_rchunk;
`ifdef OT_DMA_ACCEPT_EARLY
                    chunks_i<=8'(c_nchunk);chunks_m<=8'(c_nchunk);chunks_c<=8'(c_nchunk);chunks_a<=8'(c_nchunk);
`endif
""")
# 1+2. early sum, registered acceptance, carry-select function, FORMAL invariants (before the RR_RT generate)
rep("""    // HBM-BANKLAT-DMA 10-19: RR_RT>7 (d4g lanes).""", """`ifdef OT_DMA_ACCEPT_EARLY
    // (C) acceptance one edge early from the same b-stage operands; the hend sum moves one stage earlier.
    wire [18:0] e_vend=b_vbase_end+19'(b_vprod[16:0]);
    wire e_static_ok=b_static_ok&&b_mv[44:22]==0&&b_vprod[40:17]==0;
    wire e_vok=(b_mv[44:5]<65536&&41'(e_vend)<=65536)||(b_mv[44:5]>=65536&&41'(e_vend)<=98304);
    wire e_hok=b_hend[40:37]==0&&b_hend[36:35]==stk_q&&{1'b0,b_hend[34:0]}<=STACK_BYTES;
    wire e_nchunk_ok=b_nchunk>0&&b_nchunk<=128;
    wire e_ilead_ok=$signed(b_ci_m2-cycle_q)>=1;
    wire e_lag_ok=$signed(b_cd-b_ci)>=RR_RT+3;
`ifdef OT_DMA_ACCEPT_EARLY_NEG
    wire e_valid=e_static_ok&&e_vok&&e_nchunk_ok&&e_ilead_ok&&e_lag_ok;
`else
    wire e_valid=e_static_ok&&e_vok&&e_nchunk_ok&&e_hok&&e_ilead_ok&&e_lag_ok;
`endif
    always @(posedge clk) begin
        q_hbase_end<={4'b0,p_mv[134:98]}+(41'(p_mv[219:206])<<2);
`ifdef OT_DMA_ACCEPT_EARLY_NEG2
        b_hend<=q_hbase_end+41'(q_hlo)+(41'(q_hhi)<<16)+41'd1;
`else
        b_hend<=q_hbase_end+41'(q_hlo)+(41'(q_hhi)<<16);
`endif
        c_valid_0<=e_valid;c_valid_1<=e_valid;c_valid_2<=e_valid;c_valid_3<=e_valid;
    end
`ifdef FORMAL
    // Edges since local reset release (saturating); every pipeline valid bit implies its depth.
    reg [2:0] f_age;
    always @(posedge clk or negedge local_rst_n)
        if(!local_rst_n)f_age<=0;else if(f_age!=3'd7)f_age<=f_age+3'd1;
    wire f_valid_ref=c_static_ok&&c_vok&&c_nchunk_ok&&c_hok&&c_ilead_ok&&c_lag_ok;
    always @* begin
        assert(!a_v||f_age>=1); assert(!p_valid||f_age>=2); assert(!q_valid||f_age>=3);
        assert(!b_v||f_age>=4); assert(!cv||f_age>=5);
        if(f_age>=2)assert(q_hbase_end=={4'b0,q_mv[134:98]}+(41'(q_mv[219:206])<<2));
        if(f_age>=3)assert(b_hend==b_hbase_end+b_hprod);
        // valid_move/chunk_valid are only consumed under cv (or its copies, equal to cv)
        if(cv)assert(c_valid_0==f_valid_ref&&c_valid_1==f_valid_ref&&c_valid_2==f_valid_ref&&c_valid_3==f_valid_ref);
        assert(cv_0==cv&&cv_1==cv&&cv_2==cv&&cv_3==cv);
        assert(chunks_i==chunks&&chunks_m==chunks&&chunks_c==chunks&&chunks_a==chunks);
        assert(drain_slot_m==drain_slot&&drain_slot_c==drain_slot&&drain_slot_a==drain_slot);
        for(integer b=0;b<8;b=b+1)
            assert(cs_addr(drain_chunk_hbm[36:8],dc_hi1,drain_chunk_hbm[7:5],4'(b)+((MUT==1&&b==1)?4'd1:4'd0))==
                   drain_chunk_hbm[36:5]+32'(b)+((MUT==1&&b==1)?32'd1:32'd0));
    end
`endif
`endif
    // HBM-BANKLAT-DMA 10-19: RR_RT>7 (d4g lanes).""")
open(sys.argv[2], 'w').write(src)
print("patched", sys.argv[2])
