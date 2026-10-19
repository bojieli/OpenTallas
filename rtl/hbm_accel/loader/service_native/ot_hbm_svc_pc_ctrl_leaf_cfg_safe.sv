`timescale 1ns/1ps
// HBM-BW 2026-10-19: MULTI-ROW successor of ot_hbm_svc_pc_ctrl_leaf_cfg (that module stays byte-identical).  Same ports,
// same K/response skids, same 32-entry queue + write-payload / response SRAMs, same PHY-side output flops.  The single
// active-row state machine (IDLE/DESC/DRAIN/RUN: a request to another row waited until every queued access AND every read
// response had left, then a precharge-all and a new descriptor) is gone: every queued access carries its own DRAM row
// into ot_hbm_r14_aq_pc_mr (per-bank open row, ACT ahead from the queue, precharge when no queued access needs the
// open row), so a K request is accepted whenever the queue has room.  Measured cause and numbers: lanes/HBM-BW.md.
module ot_hbm_svc_pc_ctrl_leaf_cfg_safe #(
    parameter integer MRKEY=1,
    // RQ (HBM-BW): read responses reserved per PC (posted + in flight + landed, untaken).  The as-built 32 covered only
    // the ~30-cycle column -> K-response round trip, so the queue ran nearly empty and no ACT could be issued ahead;
    // 128 (a power of two: ring pointers) covers the 64-entry queue + the round trip; the 128x256 response SRAM already
    // holds 128 rows.
    parameter integer RQ=128,
    // QD (HBM-BW): access-queue depth in sectors (leaf queue + sequencer queue).  The queue is the ACT lookahead: an
    // entry's bank is activated when it is queued, so QD cycles of column work must cover the ACT sequencing of a block's
    // four banks (tRRD/slot ~4 cycles each) + tRCD 19 + a refresh ACT-blocking window (16): 32 left no margin.
    // A deeper QD128 experiment uses existing SRAM capacity but lowers the
    // measured DS rate81.83..83.08 by reducing idle banks for refresh pull-in.
    // Keep the measured production-optimal64-sector queue as the default.
    parameter integer QD=64,
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
    // Negative-control witness: corrupt tag bit zero at pending identity write.
    parameter integer BW_MUT_ID_TAG=0
)(
    input wire clk,rst_n,
    input wire [4:0]pc_id,
    input wire [7:0]refresh_reload,
    input wire k_v,output wire k_rdy,input wire k_we,
    input wire[29:0]k_addr,input wire[3:0]k_len,input wire[16:0]k_tag,
    input wire[255:0]k_wdata,input wire[31:0]k_wstrb,
    output wire kr_v,input wire kr_rdy,
    output wire[16:0]kr_tag,output wire[3:0]kr_beat,output wire[255:0]kr_data,
    output wire[17:0]kr_v_regions,
    output reg k_wr_done,
    output wire row_v,output wire[2:0]row_op,output wire[4:0]row_bank,output wire[18:0]row_row,
    output wire col_v,col_we,output wire[4:0]col_bank,col_col,
    output wire[255:0]col_data,output wire[31:0]col_strb,
    input wire dram_rvalid,input wire[255:0]dram_rdata,
    output wire pc_fault,output reg[5:0]owner_fault_split
);
    // the rst_n port drives only the registered reset relay (assert asynchronous, release after 3 clk edges)
    // Identical-depth KEPT relay copies release on the existing edge. Region
    // zero owns accounting and the AQ port; the remaining copies stay local
    // to return capture, native K, native KR, metadata, PHY, and diagnostics.
    // Region seven is spare; regions 8..71 feed same-edge AQ bank/tournament resets.
    wire [71:0] region_rst_n;
    wire lrst_n=region_rst_n[0];
    ot_rst_relay #(.REGIONS(72)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(region_rst_n));
    // Native PHY-return pin capture: valid and all payload bits enter flops
    // together before response FIFO accounting/address/identity logic. This
    // adds one HBM edge before block-ready; normal on-die calendars do not
    // gain a runtime stall or a credit mechanism. RREG=0 is diagnostic history.
    wire ret_v; wire [255:0] ret_data;
    generate if(RREG!=0)begin:g_phy_return
        reg v;reg [255:0]data;
        always @(posedge clk) data<=dram_rdata;
        always @(posedge clk or negedge region_rst_n[1])
            if(!region_rst_n[1]) v<=1'b0; else v<=dram_rvalid;
        assign ret_v=v;assign ret_data=data;
    end else begin:g_raw_phy_return
        assign ret_v=dram_rvalid;assign ret_data=dram_rdata;
    end endgenerate
    reg [4:0]pc_id_q;reg [7:0]refresh_reload_q;
    always @(posedge clk)begin pc_id_q<=pc_id;refresh_reload_q<=refresh_reload;end
    wire i_v,i_we;wire[29:0]i_addr;wire[3:0]i_len;wire[16:0]i_tag;wire[255:0]i_wdata;wire[31:0]i_wstrb;
    wire i_rdy;
    reg sticky;
    localparam integer QW=$clog2(QD);
    reg[QW-1:0]wp,rp,ep;reg[QW:0]count,unposted;
    // Address successors are computed before column eligibility arrives.
    // cv/posted selects a registered address, never a conditional carry chain.
    (* keep="true",dont_touch="true" *) reg[QW-1:0]rp_plus1,ep_plus1;
    wire[63:0]queue_head,queue_post; // SRAM-backed four-bank metadata, two read replicas
    /*reg[63:0]queue[0:QD-1];*/          // {we,bank[4:0],col[4:0],tag[16:0],beat[3:0],wstrb[31:0]} = bits 319:256
    wire[14:0]qrow_post; /*reg[14:0]qrow[0:QD-1];*/           // the DRAM row of each queued access (multi-row)
    wire[255:0]head_wdata;
    reg fresh_v;reg[QW-1:0]fresh_slot;
    localparam integer RQW=$clog2(RQ);
    reg[RQW:0]read_reserved,pending_count,response_count;
    reg[RQW-1:0]pending_wp,pending_rp,response_wp,response_rp;
    wire[255:0]pending_meta,response_meta;
    wire[20:0]head_identity=response_meta[20:0];reg head_valid;
    wire[255:0]response_data;
    wire[29:0]incoming=i_addr;
    wire[18:0]incoming_row={4'b0,incoming[29:15]};
    wire[4:0]incoming_pc=incoming[6:2]^incoming[11:7]^incoming[16:12];
    wire[3:0]length=i_len;
    wire legal;wire raw_legal=length>=1 && length<=4 && (!i_we || length==1) &&
        {1'b0,incoming[1:0]}+length<=4 && incoming_pc==pc_id_q && {1'b0,incoming}+length<=31'd703125000;
    wire wr,cv,cwe,caq;wire[4:0]cb,cc;
    wire[319:0]head={queue_head,head_wdata},push={queue_post,256'b0};
    wire push_read=!push[319];
    wire enqueue=unposted!=0 && (!push_read || read_reserved<RQ) && !sticky;
    wire accepted=i_v&&i_rdy;wire posted=enqueue&&wr;
    // One arithmetic cone feeds kept same-edge count captures. At22 regions
    // the shared next-count bus drives23 D pins per bit, including count.
    wire[QW:0]queue_count_next=count+(accepted?6'(length):6'd0)-(cv?6'd1:6'd0);
    wire posted_read=posted&&push_read;
    wire column_read=cv&&!cwe;
    wire j_v,j_rdy;
    wire head_valid_next=response_read?1'b1:response_take?1'b0:head_valid;
    wire response_take=j_v&&j_rdy;
    assign i_rdy=!sticky&&!pc_fault&&legal&&count+length<=QD;
    wire kfront_fault;
    generate if(KREG!=0)begin:g_kreg
        // Released H9b native pin contract: pure data/valid capture, then a
        // three-entry ring. No external pin controls a wide payload mux.
        reg kp_we,k_rdy_q;
        localparam integer KREGIONS=(341+15)/16;
        (* keep="true",dont_touch="true" *) reg[KREGIONS-1:0]kv_regions,ready_seen_regions;
        wire[KREGIONS-1:0]push_regions,pop_regions,valid_regions;
        reg[29:0]kp_addr;reg[3:0]kp_len;reg[16:0]kp_tag;reg[31:0]kp_strb;reg[255:0]kp_data;
        always @(posedge clk)begin kp_we<=k_we;kp_addr<=k_addr;kp_len<=k_len;kp_tag<=k_tag;kp_strb<=k_wstrb;kp_data<=k_wdata;end
        wire kp_legal=kp_len>=1&&kp_len<=4&&(!kp_we||kp_len==1)&&
          {1'b0,kp_addr[1:0]}+kp_len<=4&&(kp_addr[6:2]^kp_addr[11:7]^kp_addr[16:12])==pc_id_q&&
          {1'b0,kp_addr}+kp_len<=31'd703125000;
        wire[2:0]n,nn;
        ot_hbm_svc_ring_bw_safe #(.WIDTH(341),.DEPTH(3),.REGIONAL(1)) u_kring(.clk(clk),.rst_n(region_rst_n[2]),
          .in_v(push_regions[0]),.in_data({kp_legal,kp_we,kp_addr,kp_len,kp_tag,kp_strb,kp_data}),
          .out_v(i_v),.pop(i_v&&i_rdy),.out_data({legal,i_we,i_addr,i_len,i_tag,i_wstrb,i_wdata}),
          .cnt(n),.cnt_next(nn),.fault(kfront_fault),
          .in_v_regions(push_regions),.pop_regions(pop_regions),.out_v_regions(valid_regions));
        for(genvar r=0;r<KREGIONS;r=r+1)begin:g_control
          // Same-edge replicas of architectural queue accounting. Local
          // acceptance uses independent state; shared next-count arithmetic
          // drives only23 D pins per bit, never wide pointer enables.
          (* keep="true",dont_touch="true" *) reg[QW:0]count_q;
          wire ready_local=!sticky&&!pc_fault&&legal&&count_q+length<=QD;
          assign push_regions[r]=kv_regions[r]&&ready_seen_regions[r];
          assign pop_regions[r]=valid_regions[r]&&ready_local;
          always @(posedge clk or negedge lrst_n)
            if(!lrst_n)count_q<=0;
            else count_q<=queue_count_next;
          always @(posedge clk)if(!region_rst_n[2])begin
            kv_regions[r]<=0;ready_seen_regions[r]<=0;
          end else begin kv_regions[r]<=k_v;ready_seen_regions[r]<=k_rdy_q;end
        end
        always @(posedge clk)if(!region_rst_n[2])begin k_rdy_q<=0;end
          else begin k_rdy_q<=k_rdy_q?(nn<3'd2):(nn<=3'd2);end
        assign k_rdy=k_rdy_q;
    end else begin:g_raw_k
        assign i_v=k_v;assign i_we=k_we;assign i_addr=k_addr;assign i_len=k_len;assign i_tag=k_tag;
        assign i_wdata=k_wdata;assign i_wstrb=k_wstrb;assign k_rdy=i_rdy;assign legal=raw_legal;assign kfront_fault=0;
    end endgenerate

    assign j_v=head_valid&&!sticky&&!pc_fault;
    generate if(KRREG!=0)begin:g_krreg
        // Same-edge ready captures feed two adjacent eight-bit slices each.
        // Raw ready sees18 FF D pins; each retained copy feeds only local
        // valid/update logic, preserving the released previous-edge ABI.
        (* keep="true",dont_touch="true" *) reg[17:0]ready_q;
        (* keep="true",dont_touch="true" *) reg[17:0]head_valid_regions;
        wire[17:0]admission_regions;
        for(genvar r=0;r<18;r=r+1)begin:g_control
          always @(posedge clk or negedge lrst_n)
            if(!lrst_n)head_valid_regions[r]<=0;
            else head_valid_regions[r]<=head_valid_next;
          assign admission_regions[r]=head_valid_regions[r]&&!sticky&&!pc_fault;
        end
        always @(posedge clk)if(!region_rst_n[3])ready_q<=0;else ready_q<={18{kr_rdy}};
        ot_hbm_svc_pin_skid2_bw_safe #(.WIDTH(277),.REGIONAL(1)) u_skid(
            .clk(clk),.rst_n(region_rst_n[3]),.in_v(j_v),.in_r(j_rdy),
            .in_data({head_identity[20:4],head_identity[3:0],response_data}),
            .out_v(kr_v),.out_r_regions(ready_q),.out_data({kr_tag,kr_beat,kr_data}),.in_v_regions(admission_regions),.out_v_regions(kr_v_regions));
    end else begin:g_raw_kr
        assign kr_v=j_v;assign j_rdy=kr_rdy;assign kr_v_regions={18{j_v}};
        assign kr_tag=head_identity[20:4];assign kr_beat=head_identity[3:0];assign kr_data=response_data;
    end endgenerate
    wire r_v;wire[2:0]r_op;wire[4:0]r_bank;wire[18:0]r_row;
    generate if(OREG!=0)begin:g_oreg
        reg q_rv,q_cv,q_cwe;reg[2:0]q_rop;reg[4:0]q_rbank,q_cb,q_cc;reg[18:0]q_rrow;reg[255:0]q_cd;reg[31:0]q_cs;
        always @(posedge clk or negedge region_rst_n[5])
            if(!region_rst_n[5])begin q_rv<=0;q_cv<=0;q_cwe<=0;end else begin q_rv<=r_v;q_cv<=cv;q_cwe<=cwe;end
        always @(posedge clk)begin q_rop<=r_op;q_rbank<=r_bank;q_rrow<=r_row;q_cb<=cb;q_cc<=cc;q_cd<=head[255:0];q_cs<=head[287:256];end
        assign row_v=q_rv;assign row_op=q_rop;assign row_bank=q_rbank;assign row_row=q_rrow;
        assign col_v=q_cv;assign col_we=q_cwe;assign col_bank=q_cb;assign col_col=q_cc;assign col_data=q_cd;assign col_strb=q_cs;
    end else begin:g_comb
        assign row_v=r_v;assign row_op=r_op;assign row_bank=r_bank;assign row_row=r_row;
        assign col_v=cv;assign col_we=cwe;assign col_bank=cb;assign col_col=cc;
        assign col_data=head[255:0];assign col_strb=head[287:256];
    end endgenerate
    // Released H9b diagnostic ABI: six separately registered fault classes.
    // Internal sticky traffic kill retains its original edge; pins follow one
    // diagnostic edge later, as on the released native controller.
    reg[5:0]fault_detail;
    always @(posedge clk)if(!region_rst_n[6])begin fault_detail<=0;owner_fault_split<=0;end
    else begin
      owner_fault_split<=fault_detail;
      if(i_v&&!legal)fault_detail[0]<=1;
      if(cv&&(count==0||cwe!=head[319]||cb!=head[318:314]||cc!=head[313:309]||(!cwe&&!caq)||
          (WPAY!=0&&cwe&&fresh_v&&fresh_slot==rp)))fault_detail[1]<=1;
      if(column_read&&pending_count>=RQ)fault_detail[2]<=1;
      if(ret_v&&(pending_count==0||(response_count>=RQ&&!response_take)))fault_detail[3]<=1;
      if((response_take&&(read_reserved==0||response_count==0))||read_reserved>RQ||pending_count>RQ||response_count>RQ)fault_detail[4]<=1;
      if(kfront_fault)fault_detail[5]<=1;
    end
    generate if(WPAY!=0)begin:g_wpay
        // write payload SRAM: written once per accepted write (writes are length 1), read every edge at the next head
        wire[QW-1:0]wpay_raddr=cv?rp_plus1:rp;
        ot_sram_1r1w_128x256_m1_r2c2 u_write_payload(
            .clk(clk),.r_ce_in(1'b1),.r_addr_in(7'(wpay_raddr)),.rd_out(head_wdata),
            .w_ce_in(accepted&&i_we),.w_addr_in(7'(wp)),.wd_in(i_wdata),.w_mask_in({256{1'b1}}),
            .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    end else begin:g_wflops
        reg[255:0]wq[0:QD-1];
        always @(posedge clk) if(accepted)for(integer b=0;b<4;b=b+1)if(b<length)wq[QW'(wp+b)]<=i_wdata;
        assign head_wdata=wq[rp];
    end endgenerate
    wire response_read=!sticky&&((!head_valid&&response_count!=0)||(response_take&&response_count>1));
    wire[RQW-1:0]response_read_address=response_take?response_rp+1'b1:response_rp;
    wire response_write=ret_v&&pending_count!=0&&!sticky;
    ot_sram_1r1w_128x256_m1_r2c2 u_response_payload(
        .clk(clk),.r_ce_in(response_read),.r_addr_in(7'(response_read_address)),.rd_out(response_data),
        .w_ce_in(response_write),.w_addr_in(7'(response_wp)),.wd_in(ret_data),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    // Four write banks admit a len-4 request on one edge. Two synchronous
    // read replicas serve posting and completion independently. No indexed flop
    // storage; forwarding covers same-edge SRAM read/write ambiguity.
    wire[255:0]qh[0:3],qe[0:3];
    reg[78:0]mf_data[0:3];
    wire[3:0]meta_we;wire[QW-3:0]meta_wa[0:3];
    wire[QW-1:0]next_rp=cv?rp_plus1:rp,next_ep=posted?ep_plus1:ep;
    wire[78:0]mh,me;
    // Twenty retained four-bit regions. Each owns pointer selectors and
    // forwarding-address/valid captures on the original metadata edge.
    // Data and SRAM schedules are unchanged; actual mapped fanout is audited.
    for(genvar s=0;s<20;s=s+1)begin:META_SELECT
      localparam integer LO=4*s;
      localparam integer BITS=(79-LO<4)?79-LO:4;
      wire meta_rst_n=region_rst_n[4+(s%3)];
      (* keep="true",dont_touch="true" *) reg[1:0]rp_sel,ep_sel;
      (* keep="true",dont_touch="true" *) reg[QW-3:0]rp_hi,ep_hi;
      always @(posedge clk or negedge meta_rst_n)
        if(!meta_rst_n)begin rp_sel<=0;ep_sel<=0;rp_hi<=0;ep_hi<=0;end
        else begin rp_sel<=next_rp[1:0];ep_sel<=next_ep[1:0];
          rp_hi<=next_rp[QW-1:2];ep_hi<=next_ep[QW-1:2];end
      wire[BITS-1:0]hbank[0:3],ebank[0:3];
      for(genvar b=0;b<4;b=b+1)begin:FORWARD
        (* keep="true",dont_touch="true" *) reg mf_valid;
        (* keep="true",dont_touch="true" *) reg[QW-3:0]mf_address;
        always @(posedge clk or negedge meta_rst_n)
          if(!meta_rst_n)mf_valid<=0;else mf_valid<=meta_we[b];
        always @(posedge clk)mf_address<=meta_wa[b];
        assign hbank[b]=(mf_valid&&mf_address==rp_hi)?
          mf_data[b][LO+:BITS]:qh[b][LO+:BITS];
        assign ebank[b]=(mf_valid&&mf_address==ep_hi)?
          mf_data[b][LO+:BITS]:qe[b][LO+:BITS];
      end
      assign mh[LO+:BITS]=hbank[rp_sel];
      assign me[LO+:BITS]=ebank[ep_sel];
    end
    // Real regional row sources: every word selects with its own retained
    // one-hot metadata bank identity, captured on the existing read edge.
    // The existing local forwarding identities are reused; no new SRAM port
    // or data stage is introduced. Each AQ region feeds four look-row banks.
    wire[8*19-1:0]qrow_post_regions;
    for(genvar g=0;g<8;g=g+1)begin:POST_ROW_REGION
      wire[14:0]word_data;
      for(genvar k=0;k<2;k=k+1)begin:WORD
        localparam integer LO=k*8;
        localparam integer BITS=(15-LO<8)?15-LO:8;
        localparam integer M=2*g+k;
        (* keep="true",dont_touch="true" *) reg[3:0]bank_oh;
        wire mrst_n=region_rst_n[4+(g%3)];
        always @(posedge clk or negedge mrst_n)
          if(!mrst_n)bank_oh<=4'b0001;
          else bank_oh<=4'b0001<<next_ep[1:0];
        wire[BITS-1:0]bank_word[0:3];
        for(genvar b=0;b<4;b=b+1)begin:BANK
          wire hit=META_SELECT[M].FORWARD[b].mf_valid&&
            META_SELECT[M].FORWARD[b].mf_address==META_SELECT[M].ep_hi;
          assign bank_word[b]=hit?mf_data[b][64+LO+:BITS]:qe[b][64+LO+:BITS];
        end
        assign word_data[LO+:BITS]=(bank_word[0]&{BITS{bank_oh[0]}})|
          (bank_word[1]&{BITS{bank_oh[1]}})|(bank_word[2]&{BITS{bank_oh[2]}})|
          (bank_word[3]&{BITS{bank_oh[3]}});
      end
      assign qrow_post_regions[g*19+:19]={4'b0,word_data};
    end
    assign queue_head=mh[63:0];assign queue_post=me[63:0];assign qrow_post=me[78:64];
    for(genvar b=0;b<4;b=b+1)begin:METADATA
      wire[1:0]j=2'(b)-wp[1:0];wire we=accepted&&{1'b0,j}<length;
      wire[QW-1:0]wa=wp+QW'(j);
      wire[78:0]wd={incoming[29:15],i_we,incoming[14:12]^incoming[19:17],(2'(incoming[1:0]+j)^incoming[16:15]),incoming[11:7],i_tag,4'(j),i_wstrb};
      assign meta_we[b]=we;assign meta_wa[b]=wa[QW-1:2];
      always @(posedge clk)mf_data[b]<=wd;
      ot_sram_1r1w_128x256_m1_r2c2 u_head(.clk(clk),.r_ce_in(1'b1),.r_addr_in(7'(next_rp>>2)),.rd_out(qh[b]),
        .w_ce_in(we),.w_addr_in(7'(wa>>2)),.wd_in({177'b0,wd}),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
      ot_sram_1r1w_128x256_m1_r2c2 u_post(.clk(clk),.r_ce_in(1'b1),.r_addr_in(7'(next_ep>>2)),.rd_out(qe[b]),
        .w_ce_in(we),.w_addr_in(7'(wa>>2)),.wd_in({177'b0,wd}),.w_mask_in({256{1'b1}}),
        .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    end
    ot_sram_1r1w_128x256_m1_r2c2 u_pending_identity(.clk(clk),.r_ce_in(1'b1),
      .r_addr_in(7'(ret_v?pending_rp+1'b1:pending_rp)),.rd_out(pending_meta),
      .w_ce_in(column_read),.w_addr_in(7'(pending_wp)),.wd_in({235'b0,head[308:288]^(BW_MUT_ID_TAG!=0?21'd16:21'd0)}),.w_mask_in({256{1'b1}}),
      .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    ot_sram_1r1w_128x256_m1_r2c2 u_response_identity(.clk(clk),.r_ce_in(response_read),
      .r_addr_in(7'(response_read_address)),.rd_out(response_meta),
      .w_ce_in(response_write),.w_addr_in(7'(response_wp)),.wd_in({235'b0,pending_meta[20:0]}),.w_mask_in({256{1'b1}}),
      .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    ot_hbm_r14_aq_pc_safe #(.ROW_REGIONS(8),.WQ(QD),.MRKEY(MRKEY)) controller(
        .clk(clk),.rst_n(region_rst_n[7]),.reset_regions(region_rst_n[71:8]),.slot_parity(pc_id_q[0]),.refresh_reload(refresh_reload_q),
        .row_v(r_v),.row_op(r_op),.row_bank(r_bank),.row_row(r_row),
        .col_v(cv),.col_bank(cb),.col_col(cc),.ref_fault(pc_fault),
        .wr_v(enqueue),.wr_bank(push[318:314]),.wr_col(push[313:309]),.wr_row({4'b0,qrow_post}),.wr_row_regions(qrow_post_regions),.wr_rd(push_read),.wr_r(wr),
        .col_we(cwe),.col_aq(caq),.dbg_held());
    always @(posedge clk or negedge lrst_n)begin
        if(!lrst_n)begin
            sticky<=0;wp<=0;rp<=0;ep<=0;rp_plus1<=1;ep_plus1<=1;count<=0;unposted<=0;
            read_reserved<=0;pending_count<=0;response_count<=0;pending_wp<=0;pending_rp<=0;response_wp<=0;response_rp<=0;
            head_valid<=0;k_wr_done<=0;fresh_v<=0;fresh_slot<=0;
        end else begin
            k_wr_done<=0;
            if((i_v&&!legal)||kfront_fault)sticky<=1;
            if(accepted)wp<=wp+QW'(length);
            count<=queue_count_next;
            unposted<=unposted+(accepted?6'(length):6'd0)-(posted?6'd1:6'd0);
            read_reserved<=read_reserved+(posted_read?6'd1:6'd0)-(response_take?6'd1:6'd0);
            pending_count<=pending_count+(column_read?6'd1:6'd0)-(ret_v?6'd1:6'd0);
            response_count<=response_count+(ret_v?6'd1:6'd0)-(response_take?6'd1:6'd0);
            if(posted)begin ep<=ep_plus1;ep_plus1<=ep_plus1+1'b1;end
            fresh_v<=accepted&&i_we;fresh_slot<=wp;
            if(cv)begin
                if(count==0 || cwe!=head[319] || cb!=head[318:314] || cc!=head[313:309] || (!cwe&&!caq))sticky<=1;
                if(WPAY!=0 && cwe && fresh_v && fresh_slot==rp)sticky<=1;
                rp<=rp_plus1;rp_plus1<=rp_plus1+1'b1;
                if(cwe)k_wr_done<=1;
                else begin
                    if(pending_count>=RQ)sticky<=1;
                    pending_wp<=pending_wp+1'b1;
                end
            end
            if(ret_v)begin
                if(pending_count==0 || (response_count>=RQ&&!response_take))sticky<=1;
                else begin pending_rp<=pending_rp+1'b1;response_wp<=response_wp+1'b1;end
            end
            head_valid<=head_valid_next;
            if(response_take)begin
                if(read_reserved==0||response_count==0)sticky<=1;
                response_rp<=response_rp+1'b1;
            end
            if(read_reserved>RQ||pending_count>RQ||response_count>RQ)sticky<=1;
        end
    end
endmodule
`default_nettype wire
