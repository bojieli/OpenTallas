// Additive HBM H7 candidate: six local registered sticky fault classes replace
// the single global fault flop. Their OR kills internal traffic on exactly the
// original edge. Each physical fault output is itself a flop; a parent may
// aggregate the six registered outputs on a separately declared diagnostic edge.
// The legacy scalar-port master and its source remain unchanged.
// Baseline SHA256: 961f061e4846868c71f83c4ed6304d361e9ab853d8d6c7a06312caf212cfeb48
`timescale 1ns/1ps
// H-DIE 2026-10-15: ONE pseudo-channel of ot_hbm_svc_native_sector_pipeline_stack as a hardenable die leaf (the stack's
// g_pc[P] body verbatim, per-PC slices renamed to scalar ports; the stack's ca_fault channel-pair check and fault OR stay
// in the parent ot_hbm_svc_native_sector_pipeline_leaves).  Real controller: actual ot_hbm_r14_stream_pc sequencer +
// same-row FIFO32 + 32 reserved responses in an actual 128x256 SRAM.  K side faces the SM service group; row/column/data
// side faces the PHY-only abstract (the only modelled boundary).  clk = this PC's pc_clk root.
// OREG=1 (H-DIE 2026-10-15, die default): every PHY-side command output (row_*, col_*, write data/strobe) leaves from a
// flop -- one uniform extra cycle on the command path to the PHY (relative DRAM command timing unchanged); the read
// return path is unchanged.  OREG=0 is the stack body exactly.
// KREG=1 (die default): the K request enters a 2-entry pin-registered skid; k_rdy = skid not full (a register), so no
// K input reaches k_rdy or the queue combinationally; one extra hbm cycle on the request, full rate.  KREG=0: as the stack.
// KRREG=1 (die default): the K response leaves through a 2-entry skid whose registers drive kr_v/kr_tag/kr_beat/kr_data;
// kr_rdy only pops the skid.  One extra hbm cycle on the response, full rate.  KRREG=0: as the stack.
// H9b (H-PC Claude 2026-10-16): H9 + native pin boundary. H9 CTS native probe failed capture 404.8 ps on 37 inputs
// (k_addr/k_len legality adder, k_v -> skid push select, kr_rdy -> skid pop select). H9b: every K input lands in a pure
// pin flop (data unconditional, kp_v = k_v && k_rdy); legality is computed from the pin flops into a 3-entry ring;
// k_rdy is a register = (ring_next + kp_next <= 2) (full rate; +1 K request edge, ledgered). KR: H9 2-entry skid (outputs from flops), kr_rdy
// is pin-registered: READY-LATENCY-1 contract, a beat transfers at t when kr_v(t) && kr_rdy(t-1) (consumers keep a
// 1-entry slot). Rings move no data on pop. All other logic is H9 verbatim. RMUT (bench): 1 K ring slice skew, 2 KR
// pops on the unregistered kr_rdy (ready-latency-0), 3 k_rdy credit off by one (allows 3 in flight -> overflow fault).
module ot_hbm_svc_pc_ctrl_leaf_cfg_h9b #(
    parameter integer OREG=1,
    parameter integer KREG=1,
    parameter integer KRREG=1,
    parameter integer RREG=1,
    // WPAY=1 (H-DIE 2026-10-15 22:50, physical default): the 256-bit write payload of the 32-entry same-row queue lives
    // in a real 128x256 SRAM (rows 0..31) instead of 8,192 queue flops + a 32:1 x 256 head mux; the clock root drops
    // from 15,219 to ~7k sinks.  The payload is read continuously at the NEXT head (rp, or rp+1 on a column pop), so
    // the head word is valid one edge after any pop.  A write column issued less than two edges after its own payload
    // write would read the old word: that is checked (sticky fault), never silently stretched.  WPAY=0 = flops.
    parameter integer WPAY=1,
    // QREG=1 (H-HARDEN 2026-10-16, H6 route TT -50.14 / 888 D pins): same edges and decisions, fewer levels from
    // flops -- (a) the same-row queue is written at its FREE slots wp..wp+3 (count+b<32) every edge instead of under
    // `accepted` (K legality/same-row -> i_rdy -> 2,048-flop enable was -41 ps); an accept writes exactly the slots it
    // always wrote, and a free slot is never read before an accept rewrites it (push/head are read only at valid slots;
    // col_data/col_strb are sampled only with col_v); (b) the push entry queue[ep] is a REGISTER (push_q) maintained
    // exactly, so ep -> 32:1 mux -> bank decode -> controller queue (-46.6 ps) starts from flops; (c) the response
    // identity reads both candidate slots from registered addresses and selects late; (d) controller PHYS_WACT 2.
    // QREG=0 is H6 exactly.
    parameter integer QREG=1,
    parameter integer RMUT=0
)(
    input wire clk,rst_n,
    input wire [4:0]pc_id,
    input wire [7:0]refresh_reload,
    input wire k_v,output wire k_rdy,input wire k_we,
    input wire[29:0]k_addr,input wire[3:0]k_len,input wire[16:0]k_tag,
    input wire[255:0]k_wdata,input wire[31:0]k_wstrb,
    output wire kr_v,input wire kr_rdy,
    output wire[16:0]kr_tag,output wire[3:0]kr_beat,output wire[255:0]kr_data,
    output reg k_wr_done,
    output wire row_v,output wire[2:0]row_op,output wire[4:0]row_bank,output wire[18:0]row_row,
    output wire col_v,col_we,output wire[4:0]col_bank,col_col,
    output wire[255:0]col_data,output wire[31:0]col_strb,
    input wire dram_rvalid,input wire[255:0]dram_rdata,
    output reg pc_fault,
    output reg [5:0] owner_fault_split   // H9b: pin copies, one edge after the internal sticky classes
);
    // H9b native launch: the sticky fault classes and the refresh fault fan out to i_rdy/j_v/queue enables; the pins get
    // dedicated copy flops (one reporting edge later; sticky diagnostics, no traffic edge changes).
    reg [5:0] ofs; wire pc_fault_i;
    always @(posedge clk)
        if(!reset_regions[0])begin owner_fault_split<=6'd0;pc_fault<=1'b0;end
        else begin owner_fault_split<=ofs;pc_fault<=pc_fault_i;end

    localparam[1:0]IDLE=0,DESC=1,DRAIN=2,RUN=3;
    // the rst_n port drives only the registered reset relay (assert asynchronous, release after 3 clk edges)
    wire [7:0] reset_regions; wire lrst_n=reset_regions[0];
    ot_rst_relay #(.REGIONS(8)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(reset_regions));
    // Native PHY-return pin capture: valid and all payload bits enter flops
    // together before response FIFO accounting/address/identity logic. This
    // adds one HBM edge before block-ready; normal on-die calendars do not
    // gain a runtime stall or a credit mechanism. RREG=0 is diagnostic history.
    wire ret_v; wire [255:0] ret_data;
    generate if(RREG!=0)begin:g_phy_return
        reg v;reg [255:0]data;
        always @(posedge clk) data<=dram_rdata;
        always @(posedge clk)
            if(!reset_regions[1]) v<=1'b0; else v<=dram_rvalid;
        assign ret_v=v;assign ret_data=data;
    end else begin:g_raw_phy_return
        assign ret_v=dram_rvalid;assign ret_data=dram_rdata;
    end endgenerate
    reg [4:0]pc_id_q;reg [7:0]refresh_reload_q;
    always @(posedge clk)begin pc_id_q<=pc_id;refresh_reload_q<=refresh_reload;end
    // pc_id_qq: second strap stage for the K legality compare (H-PCCTRL 2026-10-16).  pc_id_q is the pin register at the
    // E-face strap pins; the measured H3 TT limiter was pc_id_q -> incoming_pc compare -> legal -> i_rdy -> K skid enable
    // (-65.3 ps), led by the E-face wire.  The strap is a die constant held through reset (lrst_n releases 3 edges after
    // rst_n), so the extra stage is equal to pc_id_q on every edge the controller runs; no cycle changes.
    reg [4:0]pc_id_qq;
    always @(posedge clk) pc_id_qq<=pc_id_q;
    wire i_v,i_we;wire[29:0]i_addr;wire[3:0]i_len;wire[16:0]i_tag;wire[255:0]i_wdata;wire[31:0]i_wstrb;
    wire i_rdy;
    reg[1:0]state;wire sticky=|ofs;reg[18:0]active_row;reg[31:0]observed_open;
    reg[4:0]wp,rp,ep;reg[5:0]count,unposted;
    reg[63:0]queue[0:31];          // {we,bank[4:0],col[4:0],tag[16:0],beat[3:0],wstrb[31:0]} = bits 319:256
    wire[255:0]head_wdata;
    reg fresh_v;reg[4:0]fresh_slot;
    reg[5:0]read_reserved,pending_count,response_count;
    reg[4:0]pending_wp,pending_rp,response_wp,response_rp;
    reg[20:0]pending_identity[0:31],response_identity[0:31];
    reg[20:0]head_identity;reg head_valid;
    wire[255:0]response_data;
    wire[29:0]incoming=i_addr;
    wire[18:0]incoming_row={4'b0,incoming[29:15]};
    wire[4:0]incoming_pc=incoming[6:2]^incoming[11:7]^incoming[16:12];
    wire[3:0]length=i_len;
    wire raw_legal=length>=1 && length<=4 && (!i_we || length==1) &&
        {1'b0,incoming[1:0]}+length<=4 && incoming_pc==pc_id_qq && {1'b0,incoming}+length<=31'd703125000;
    wire legal;
    // (H9 pin-side k_legal removed: H9b computes kp_legal from the pin flops)
    wire same_row=incoming_row==active_row;
    wire dr,wr,cv,cwe,caq;wire[4:0]cb,cc;
    reg[63:0]push_q;reg[4:0]ep1;reg[4:0]response_rp1;
    reg[63:0]head_q;reg[4:0]rp1;      // QREG: == queue[rp] / rp+1 on every edge (head metadata from a register)
    wire[319:0]head={(QREG!=0)?head_q:queue[rp],head_wdata},push={(QREG!=0)?push_q:queue[ep],256'b0};
    wire push_read=!push[319];
    wire enqueue=state==RUN && unposted!=0 && (!push_read || read_reserved<32) && !sticky;
    wire accepted=i_v&&i_rdy;wire posted=enqueue&&wr;
    wire posted_read=posted&&push_read;
    wire column_read=cv&&!cwe;
    wire j_v,j_rdy;
    wire response_take=j_v&&j_rdy;
    wire row_idle=count==0&&read_reserved==0;
    assign i_rdy=!sticky&&!pc_fault_i&&legal&&count+length<=32&&
        (state==IDLE || (state==RUN && (same_row || row_idle)));
    // ---- K pin boundary (H9b): pin flops, legality from flops, 3-entry ring, registered k_rdy
    reg kp_v,k_rdy_q;   // kp_v: combinational from the kv_q/k_rdy_seen flops
    reg kp_we; reg[29:0]kp_addr; reg[3:0]kp_len; reg[16:0]kp_tag; reg[31:0]kp_wstrb; reg[255:0]kp_wdata;
    always @(posedge clk)begin kp_we<=k_we;kp_addr<=k_addr;kp_len<=k_len;kp_tag<=k_tag;kp_wstrb<=k_wstrb;kp_wdata<=k_wdata;end
    wire kp_legal=kp_len>=1 && kp_len<=4 && (!kp_we || kp_len==1) &&
        {1'b0,kp_addr[1:0]}+kp_len<=4 &&
        (kp_addr[6:2]^kp_addr[11:7]^kp_addr[16:12])==pc_id_qq &&
        {1'b0,kp_addr}+kp_len<=31'd703125000;
    wire [2:0] kq_cnt,kq_next; wire kq_fault;
    wire k_pop=i_v&&i_rdy;
    ot_hbm_svc_ring_h9b #(.WIDTH(341),.DEPTH(3),.MUT(RMUT==1)) u_kring(
        .clk(clk),.rst_n(reset_regions[4]),.in_v(kp_v),
        .in_data({kp_legal,kp_we,kp_addr,kp_len,kp_tag,kp_wstrb,kp_wdata}),
        .out_v(i_v),.pop(k_pop),.out_data({legal,i_we,i_addr,i_len,i_tag,i_wstrb,i_wdata}),
        .cnt(kq_cnt),.cnt_next(kq_next),.fault(kq_fault));
    // credit: an accept at t lands in kp at t and in the ring at t+1; ring_next + kp_next <= 2 keeps it within 3 entries
    wire [2:0] k_lim=(RMUT==3)?3'd3:3'd2;
    // k_v enters a pure pin flop; the accept is kv_q && the k_rdy the producer saw (k_rdy_seen). The credit assumes an
    // accept on every ready edge (no pin in the k_rdy cone): ring_next + 1 <= 2 while ready, else <= 2.
    reg kv_q,k_rdy_seen;
    always @(posedge clk)
        if(!reset_regions[4])begin kv_q<=1'b0;k_rdy_seen<=1'b0;k_rdy_q<=1'b0;end
        else begin kv_q<=k_v; k_rdy_seen<=k_rdy_q; k_rdy_q<=k_rdy_q?(kq_next<k_lim):(kq_next<=k_lim); end
    always @* kp_v=kv_q&&k_rdy_seen;
    assign k_rdy=k_rdy_q;

    assign j_v=head_valid&&!sticky&&!pc_fault_i;
    // ---- KR pin boundary (H9b): kr_rdy pin-registered (ready-latency-1); the H9 per-64b skid keeps every KR output
    // pin on a flop (flop-first); its pop is kr_v && kr_rdy_q, so no pin reaches the 277-bit select.
    reg kr_rdy_q; wire krq_fault=1'b0;
    always @(posedge clk) if(!reset_regions[5]) kr_rdy_q<=1'b0; else kr_rdy_q<=kr_rdy;
    ot_hbm_svc_pin_skid2_h9 #(.WIDTH(277)) u_skid_kr(
        .clk(clk),.rst_n(reset_regions[5]),.in_v(j_v),.in_r(j_rdy),
        .in_data({head_identity[20:4],head_identity[3:0],response_data}),
        .out_v(kr_v),.out_r((RMUT==2)?kr_rdy:kr_rdy_q),.out_data({kr_tag,kr_beat,kr_data}));
    wire r_v;wire[2:0]r_op;wire[4:0]r_bank;wire[18:0]r_row;
    generate if(OREG!=0)begin:g_oreg
        reg q_rv,q_cv,q_cwe;reg[2:0]q_rop;reg[4:0]q_rbank,q_cb,q_cc;reg[18:0]q_rrow;reg[255:0]q_cd;reg[31:0]q_cs;
        always @(posedge clk)
            if(!reset_regions[2])begin q_rv<=0;q_cv<=0;q_cwe<=0;end else begin q_rv<=r_v;q_cv<=cv;q_cwe<=cwe;end
        always @(posedge clk)begin q_rop<=r_op;q_rbank<=r_bank;q_rrow<=r_row;q_cb<=cb;q_cc<=cc;q_cd<=head[255:0];q_cs<=head[287:256];end
        assign row_v=q_rv;assign row_op=q_rop;assign row_bank=q_rbank;assign row_row=q_rrow;
        assign col_v=q_cv;assign col_we=q_cwe;assign col_bank=q_cb;assign col_col=q_cc;assign col_data=q_cd;assign col_strb=q_cs;
    end else begin:g_comb
        assign row_v=r_v;assign row_op=r_op;assign row_bank=r_bank;assign row_row=r_row;
        assign col_v=cv;assign col_we=cwe;assign col_bank=cb;assign col_col=cc;
        assign col_data=head[255:0];assign col_strb=head[287:256];
    end endgenerate
    generate if(WPAY!=0)begin:g_wpay
        // write payload SRAM: written once per accepted write (writes are length 1), read every edge at the next head
        wire[4:0]wpay_raddr=cv?rp+5'd1:rp;
        ot_sram_1r1w_128x256_m1_r2c2 u_write_payload(
            .clk(clk),.r_ce_in(1'b1),.r_addr_in({2'b0,wpay_raddr}),.rd_out(head_wdata),
            .w_ce_in(accepted&&i_we),.w_addr_in({2'b0,wp}),.wd_in(i_wdata),.w_mask_in({256{1'b1}}),
            .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    end else begin:g_wflops
        reg[255:0]wq[0:31];
        always @(posedge clk) if(accepted)for(integer b=0;b<4;b=b+1)if(b<length)wq[5'(wp+b)]<=i_wdata;
        assign head_wdata=wq[rp];
    end endgenerate
    wire response_read=!sticky&&((!head_valid&&response_count!=0)||(response_take&&response_count>1));
    wire[4:0]response_read_address=response_take?response_rp+5'd1:response_rp;
    wire response_write=ret_v&&pending_count!=0&&!sticky;
    ot_sram_1r1w_128x256_m1_r2c2 u_response_payload(
        .clk(clk),.r_ce_in(response_read),.r_addr_in({2'b0,response_read_address}),.rd_out(response_data),
        .w_ce_in(response_write),.w_addr_in({2'b0,response_wp}),.wd_in(ret_data),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    ot_hbm_r14_stream_pc_strap_h9 #(.ENABLE(1),.REF_MODE(1),.WR_EN(1),.AQ_RD(1),.WQ(32),.PHYS_WACT((QREG!=0)?2:1)) controller(
        .reset_regions(reset_regions),.slot_parity(pc_id_q[0]),.refresh_reload(refresh_reload_q),
        .clk(clk),.rst_n(lrst_n),.desc_v(state==DESC),.desc_r(dr),.desc_row(active_row),.desc_n(11'd0),
        .go(1'b1),.next_posted(1'b0),.row_v(r_v),.row_prio(),.row_gnt(1'b1),
        .row_op(r_op),.row_bank(r_bank),.row_row(r_row),
        // desc_n=0 uses the actual access queue only. AQ reads never
        // consume the separate streaming-reader credit counter.
        .col_v(cv),.col_bank(cb),.col_col(cc),.cred_ret(3'b0),.busy(),.ref_fault(pc_fault_i),
        .wr_v(enqueue),.wr_bank(push[318:314]),.wr_col(push[313:309]),.wr_r(wr),
        .col_we(cwe),.wr_rd(push_read),.col_aq(caq));
    // QREG: the four entries an accept at wp would write (beat b), the exact next push entry, both identity candidates
    wire[255:0]qentry;
    for(genvar b=0;b<4;b=b+1)begin:g_qentry
        assign qentry[b*64+:64]={i_we,incoming[14:12]^incoming[19:17],(2'(incoming[1:0]+b)^incoming[16:15]),incoming[11:7],i_tag,4'(b),i_wstrb};
    end
    wire[4:0]ep_n=posted?ep1:ep;
    wire[4:0]ep_off=ep_n-wp;
    wire ep_hit=ep_off<5'd4 && count+6'(ep_off)<6'd32;
    wire[63:0]push_n=ep_hit?qentry[ep_off[1:0]*64+:64]:(posted?queue[ep1]:push_q);
    wire[4:0]rp_n=cv?rp1:rp;
    wire[4:0]rp_off=rp_n-wp;
    wire rp_hit=rp_off<5'd4 && count+6'(rp_off)<6'd32;
    wire[63:0]head_n=rp_hit?qentry[rp_off[1:0]*64+:64]:(cv?queue[rp1]:head_q);
    // push_q/head_q track queue[ep]/queue[rp] exactly, also through reset (ep = rp = 0 while lrst_n is low).
    always @(posedge clk) if(QREG!=0)begin
        push_q<=lrst_n?push_n:queue[0];
        head_q<=lrst_n?head_n:queue[0];
    end
    // H8: pending_wp is a FREE slot whenever pending_count<32. Refresh it
    // unconditionally from the registered command head; a column-read edge
    // writes the same identity as H7. A live pending entry is never overwritten.
    // Removes column validity/legality from 672 identity-flop write enables.
    always @(posedge clk) if(lrst_n && pending_count<32)
        pending_identity[pending_wp]<=head[308:288];
    wire[20:0]rid_rp=response_identity[response_rp],rid_rp1=response_identity[response_rp1];
    always @(posedge clk)begin
        if(!reset_regions[3])begin
            state<=IDLE;ofs<=0;active_row<=0;observed_open<=0;wp<=0;rp<=0;ep<=0;count<=0;unposted<=0;
            read_reserved<=0;pending_count<=0;response_count<=0;pending_wp<=0;pending_rp<=0;response_wp<=0;response_rp<=0;
            head_identity<=0;head_valid<=0;k_wr_done<=0;fresh_v<=0;fresh_slot<=0;ep1<=5'd1;response_rp1<=5'd1;rp1<=5'd1;
        end else begin
            k_wr_done<=0;
            if(i_v&&!legal)ofs[0]<=1;
            if(QREG!=0)begin
                for(integer b=0;b<4;b=b+1)if(count+6'(b)<6'd32)queue[5'(wp+b)]<=qentry[b*64+:64];
                if(cv)rp1<=rp1+1'b1;
                if(posted)ep1<=ep1+1'b1;
                if(response_take)response_rp1<=response_rp1+1'b1;
            end
            if(accepted)begin
                if(QREG==0)for(integer b=0;b<4;b=b+1)if(b<length)
                    queue[5'(wp+b)]<={i_we,incoming[14:12]^incoming[19:17],(2'(incoming[1:0]+b)^incoming[16:15]),incoming[11:7],i_tag,4'(b),i_wstrb};
                wp<=wp+5'(length);
                if(state==IDLE || !same_row)begin active_row<=incoming_row;state<=DESC;end
            end
            count<=count+(accepted?6'(length):6'd0)-(cv?6'd1:6'd0);
            unposted<=unposted+(accepted?6'(length):6'd0)-(posted?6'd1:6'd0);
            read_reserved<=read_reserved+(posted_read?6'd1:6'd0)-(response_take?6'd1:6'd0);
            pending_count<=pending_count+(column_read?6'd1:6'd0)-(ret_v?6'd1:6'd0);
            response_count<=response_count+(ret_v?6'd1:6'd0)-(response_take?6'd1:6'd0);
            if(posted)ep<=ep+1'b1;
            if(r_v)begin
                case(r_op)
                    0:observed_open[r_bank]<=0;
                    1:observed_open[r_bank]<=1;
                    5:observed_open<=0;
                    default:;
                endcase
            end
            if(state==DESC && dr)state<=DRAIN;
            if(state==DRAIN && observed_open==0)state<=RUN;
            fresh_v<=accepted&&i_we;fresh_slot<=wp;
            if(cv)begin
                if(state!=RUN || count==0 || cwe!=head[319] || cb!=head[318:314] || cc!=head[313:309] || (!cwe&&!caq))ofs[1]<=1;
                if(WPAY!=0 && cwe && fresh_v && fresh_slot==rp)ofs[2]<=1;
                rp<=rp+1'b1;
                if(cwe)k_wr_done<=1;
                else begin
                    if(pending_count>=32)ofs[3]<=1;
                    pending_wp<=pending_wp+1'b1;
                end
            end
            if(ret_v)begin
                if(pending_count==0 || (response_count>=32&&!response_take))ofs[3]<=1;
                else begin response_identity[response_wp]<=pending_identity[pending_rp];pending_rp<=pending_rp+1'b1;response_wp<=response_wp+1'b1;end
            end
            if(response_read)begin head_identity<=(QREG!=0)?(response_take?rid_rp1:rid_rp):response_identity[response_read_address];head_valid<=1;end
            else if(response_take)head_valid<=0;
            if(response_take)begin
                if(read_reserved==0||response_count==0)ofs[4]<=1;
                response_rp<=response_rp+1'b1;
            end
            if(read_reserved>32||pending_count>32||response_count>32)ofs[5]<=1;
            if(kq_fault||krq_fault)ofs[5]<=1;   // H9b ring overflow/underflow
        end
    end
endmodule
`default_nettype wire
