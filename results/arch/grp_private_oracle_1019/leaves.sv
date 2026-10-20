`timescale 1ns/1ps
module qkd_kv_front_cal #(parameter integer MUT = 0) (
    input wire hck, rst_n,
    input wire cfg_we, input wire [7:0] cfg_addr, input wire [63:0] cfg_data,
    input wire kgo_h, input wire vgo_h, input wire [13:0] ctx_t,
    output reg [3:0] blk_go,
    output reg fault
);
    (* keep *) reg rn;
    always @(posedge hck) rn <= rst_n;
    reg kgo_q, vgo_q, we_q; reg [7:0] ad_q; reg [63:0] cd_q; reg [13:0] ctx_q;
    always @(posedge hck or negedge rn)
        if (!rn) begin kgo_q <= 1'b0; vgo_q <= 1'b0; we_q <= 1'b0; end
        else begin kgo_q <= kgo_h; vgo_q <= vgo_h; we_q <= cfg_we; end
    always @(posedge hck) begin ad_q <= cfg_addr; cd_q <= cfg_data; ctx_q <= ctx_t; end
    reg [1:0] s_c; reg [2:0] e_c; reg [7:0] g0_c; reg [3:0] kg_c, vg_c; reg [8:0] kp_c, vp_c;
    always @(posedge hck or negedge rn)
        if (!rn) begin s_c <= 0; e_c <= 0; g0_c <= 0; kg_c <= 0; vg_c <= 0; kp_c <= 9'h1ff; vp_c <= 9'h1ff; end
        else if (we_q) case (ad_q)
            8'd0: begin s_c <= cd_q[4:3]; e_c <= cd_q[2:0]; end
            8'd2: g0_c <= cd_q[7:0] - 8'd3;
            8'd4: begin kp_c <= cd_q[8:0]; kg_c <= cd_q[12:9]; end
            8'd5: begin vp_c <= cd_q[8:0]; vg_c <= cd_q[12:9]; end
            default: ;
        endcase
    // ---- closed-form stream lengths (the same as qkd_kv_landing_cal) ----
    reg [13:0] t_l;
    wire signed [15:0] xk = $signed({2'b0, (kgo_q ? ctx_q : t_l)}) - $signed({7'b0, s_c, 7'b0}) - $signed({13'b0, e_c});
    wire signed [15:0] xv = $signed({2'b0, t_l}) - $signed({7'b0, s_c, 7'b0}) - $signed({10'b0, e_c[2:1], 4'b0}) - $signed({15'b0, e_c[0]});
    function automatic [8:0] cnt(input signed [15:0] x, input integer sh);
        reg [8:0] r; reg [3:0] c0, c1; reg [9:0] h0, h1;
        begin
            r = x[8:0];
            h0 = ({1'b0, r} + 10'((1 << sh) - 1)) >> sh; h1 = (r > 9'd64) ? ({1'b0, r} - 10'd64 + 10'((1 << sh) - 1)) >> sh : 10'd0;
            c0 = (h0 >= 8) ? 4'd8 : 4'(h0); c1 = (h1 >= 8) ? 4'd8 : 4'(h1);
            cnt = (x <= 0) ? 9'd0 : (x[15:9] >= 7'd16) ? 9'd256 : {x[12:9], 4'b0} + {5'b0, c0} + {5'b0, c1};
        end
    endfunction
    // ---- block releases ----
    reg act, vpass; reg [5:0] b, nb; reg [8:0] w;     // w = HBM edges until block b's release
    wire [8:0] pp = vpass ? vp_c : kp_c; wire [3:0] pg = vpass ? vg_c : kg_c;
    wire [8:0] i1 = {b + 6'd1, 3'b0};                  // first sector of the next block
    wire pace = (MUT != 2) && (i1 >= pp);
    wire start = kgo_q | vgo_q;
    wire [8:0] nk = cnt(xk, 3), nv = cnt(xv, 1);
    wire [8:0] rnd = (MUT == 1) ? 9'd0 : 9'd7;          // MUT 1: blocks = floor(n / 8)
    wire rel = act && (w == 9'd0);
    always @(posedge hck or negedge rn)
        if (!rn) begin act <= 0; vpass <= 0; b <= 0; nb <= 0; w <= 0; t_l <= 0; fault <= 0; blk_go <= 0; end
        else begin
            blk_go <= {4{rel}};
            if (start) begin
                if (act) fault <= 1'b1;
                if (kgo_q && vgo_q) fault <= 1'b1;
                if (kgo_q) t_l <= ctx_q;
                vpass <= vgo_q; b <= 0;
                nb <= kgo_q ? 6'((nk + rnd) >> 3) : 6'((nv + rnd) >> 3);
                act <= kgo_q ? (nk != 0) : (nv != 0);
                w <= {1'b0, g0_c} - 9'd1;               // released on edge A + G0 (A = this capture edge)
            end else if (act) begin
                if (rel) begin
                    b <= b + 6'd1; w <= 9'd7 + (pace ? {5'b0, pg} : 9'd0);
                    if (b + 6'd1 == nb) act <= 1'b0;
                end else w <= w - 9'd1;
            end
        end
endmodule
module qkd_static_kv_landing_seg #(
    parameter integer MUT=0,HOP_MUT=0
)(
    input wire ck,input wire rst_n,
    input wire [1:0] cfg_stack,input wire [2:0] cfg_group,
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    input wire [3:0] expected_put,input wire [39:0] expected_sector,
    input wire [3:0] actual_valid,input wire [39:0] actual_sector,
    input wire [63:0] actual_epoch,input wire [23:0] actual_layer,input wire [1023:0] actual_data,
    input wire req_valid,input wire [13:0] req_t,input wire req_v,
    input wire [15:0] req_epoch,input wire [5:0] req_layer,
    input wire vreq_valid,input wire [13:0] vreq_t,
    output wire rsp_valid,output wire [1023:0] rsp_data,output wire [13:0] rsp_t,
    output wire rsp_v,output wire [15:0] rsp_epoch,output wire [5:0] rsp_layer,output wire fault
);
    wire [3:0] get,gv,ov,pf,vv;
    wire [55:0] gt,ot;
    wire [63:0] ge,oe;
    wire [23:0] gl,ol;
    wire [1023:0] od;
    wire [3:0] get_d,gv_d,ov_d,pf_d,vv_d;
    wire [55:0] gt_d,ot_d;
    wire [63:0] ge_d,oe_d;
    wire [23:0] gl_d,ol_d;
    wire [1023:0] od_d;
    for(genvar branch=0;branch<4;branch=branch+1)begin:g_hop
      // ls3 (KVELEM 2026-10-16): ls2 EARLY_FAIL_HOLD stalled at -44.7 ps on the FF removal check rst_n port -> hop rn
      // RESETN (async capture straight from the pin; hold repair cannot pad a removal arc). The branch's hop reset is now
      // a synchronous D capture of rst_n (a data path, as the landing PCs/rowctl already do: rn <= rst_n), one per branch
      // beside its hops. Cost: hop reset deassertion +1 edge (reset guard only; no traffic cycle changes).
      (* keep *) reg hrn;
      always @(posedge ck) hrn <= rst_n;
      qkd_static_kv_hop38 #(.MUT(HOP_MUT==2 && branch==0))u_req(
        .ck(ck),.rst_n(hrn),
        .a({gl[6*branch+:6],ge[16*branch+:16],gv[branch],gt[14*branch+:14],get[branch]}),
        .b({gl_d[6*branch+:6],ge_d[16*branch+:16],gv_d[branch],gt_d[14*branch+:14],get_d[branch]}));
      qkd_static_kv_hop295 #(.MUT(HOP_MUT==1 && branch==0))u_rsp(
        .ck(ck),.rst_n(hrn),
        .a({pf[branch],ol[6*branch+:6],oe[16*branch+:16],vv[branch],ot[14*branch+:14],od[256*branch+:256],ov[branch]}),
        .b({pf_d[branch],ol_d[6*branch+:6],oe_d[16*branch+:16],vv_d[branch],ot_d[14*branch+:14],od_d[256*branch+:256],ov_d[branch]}));
    end
    qkd_static_kv_rowctl #(.VREQ(1)) u_rowctl(
      .ck(ck),.rst_n(rst_n),.req_valid(req_valid),.req_t(req_t),.req_v(req_v),.req_epoch(req_epoch),.req_layer(req_layer),
      .vreq_valid(vreq_valid),.vreq_t(vreq_t),.arm(arm),.epoch(epoch),.layer(layer),
      .pc_get(get),.pc_get_t(gt),.pc_get_v(gv),.pc_get_epoch(ge),.pc_get_layer(gl),
      .pc_valid(ov_d),.pc_data(od_d),.pc_t(ot_d),.pc_v(vv_d),.pc_epoch(oe_d),.pc_layer(ol_d),.pc_fault(pf_d),
      .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),.fault(fault));
    genvar q;
    generate for(q=0;q<4;q=q+1)begin:g_pc
      // ls5 (KVELEM 2026-10-16): CHECK_PIPE 1 = the put/get checker one edge behind the data path on relay registers
      // (ls4 gate: every failing endpoint was checker logic fed by ps_q over ~400 ps of wire); FAULT_PIPE kept; WRITE_PIPE 0
      // (SRAM write / read edges, the landing latency 8 and the calendar are unchanged).
      qkd_static_kv_landing_pc #(.MUT(MUT),.VMAP(1),.FAULT_PIPE(1),.WRITE_PIPE(0),.CHECK_PIPE(1))u_pc(
       .ck(ck),.rst_n(rst_n),.cfg_stack(cfg_stack),.cfg_group(cfg_group),.arm(arm),.epoch(epoch),.layer(layer),
       .expected_put(expected_put[q]),.expected_sector(expected_sector[10*q+:10]),
       .actual_valid(actual_valid[q]),.actual_sector(actual_sector[10*q+:10]),
       .actual_epoch(actual_epoch[16*q+:16]),.actual_layer(actual_layer[6*q+:6]),.actual_data(actual_data[256*q+:256]),
       .get(get_d[q]),.get_t(gt_d[14*q+:14]),.get_v(gv_d[q]),.get_epoch(ge_d[16*q+:16]),.get_layer(gl_d[6*q+:6]),
       .out_valid(ov[q]),.out_data(od[256*q+:256]),.out_t(ot[14*q+:14]),
       .out_v(vv[q]),.out_epoch(oe[16*q+:16]),.out_layer(ol[6*q+:6]),.fault(pf[q]));
    end endgenerate
endmodule
module qkd_static_kv_phase_launch #(
 parameter integer PH0=0, SAFE_LOW_U=0, SAFE_HIGH_U=0, META_HOLD_CORE=0, MUT=0
)(
 input wire ck,rst_n,hck,hrst_n,
 input wire ctrl_go,kgo,vgo,input wire[13:0]ctx_t,input wire[15:0]epoch,input wire[5:0]layer,
 output reg ctrl_go_h,kgo_h,vgo_h,output reg[13:0]ctx_t_h,output reg[15:0]epoch_h,output reg[5:0]layer_h,
 output reg fault_core,fault_hbm,output reg idle_core,idle_hbm
);
 initial begin
  if(PH0<0||PH0>=768||SAFE_LOW_U<=0||SAFE_HIGH_U>=768||SAFE_HIGH_U<SAFE_LOW_U||META_HOLD_CORE<6||META_HOLD_CORE>255)
   $fatal(1,"actual phase profile and held-metadata budget required");
 end
 (* keep *)reg rn,hr;
 always @(posedge ck)rn<=rst_n;
 always @(posedge hck)hr<=hrst_n;
 reg[2:0]go_q,tag;reg[35:0]meta_q,held;
 reg[9:0]q;reg[7:0]hold_q;reg[7:0]lane_hold[0:2];
 wire[9:0]next_gap=(q==0)?10'd768:q;
 wire phase_ok=(next_gap>=10'(SAFE_LOW_U)&&next_gap<=10'(SAFE_HIGH_U));
 reg gap_bad;integer i;
 always @*begin
  gap_bad=0;for(integer k=0;k<3;k=k+1)if(go_q[k]&&lane_hold[k]!=0)gap_bad=1;
 end
 always @(posedge ck)meta_q<={ctx_t,epoch,layer};
 always @(posedge ck or negedge rn)begin
  if(!rn)begin
   go_q<=0;tag<=0;held<=0;q<=10'(PH0);hold_q<=0;fault_core<=0;idle_core<=0;
   for(i=0;i<3;i=i+1)lane_hold[i]<=0;
  end else begin
   go_q<={vgo,kgo,ctrl_go};
   q<=(q>=625)?q-10'd625:q+10'd143;
   if(hold_q!=0)hold_q<=hold_q-1'b1;
   for(i=0;i<3;i=i+1)if(lane_hold[i]!=0)lane_hold[i]<=lane_hold[i]-1'b1;
   idle_core<=hold_q==0&&go_q==0&&!ctrl_go&&!kgo&&!vgo;
   if(|go_q)begin
    if((!phase_ok&&MUT!=2)||gap_bad||(hold_q!=0&&held!=meta_q))fault_core<=1;
    else if(!fault_core)begin
     tag<=tag^go_q;held<=meta_q;hold_q<=8'(META_HOLD_CORE);
     for(i=0;i<3;i=i+1)if(go_q[i])lane_hold[i]<=8'(META_HOLD_CORE);
    end
   end
  end
 end
 (* async_reg="true" *)reg[2:0]tag_meta,tag_sync;
 reg[2:0]seen;
 wire[2:0]observed=(MUT==1)?tag_meta:tag_sync;
 wire[2:0]events=observed^seen;
 always @(posedge hck or negedge hr)begin
  if(!hr)begin
   tag_meta<=0;tag_sync<=0;seen<=0;ctrl_go_h<=0;kgo_h<=0;vgo_h<=0;
   ctx_t_h<=0;epoch_h<=0;layer_h<=0;fault_hbm<=0;idle_hbm<=0;
  end else begin
   tag_meta<=tag;tag_sync<=tag_meta;seen<=observed;
   {vgo_h,kgo_h,ctrl_go_h}<=events;
   if(|events)begin
    {ctx_t_h,epoch_h,layer_h}<=held^((MUT==3)?36'd1:36'd0);
    if(held[35:22]<1||held[35:22]>8192||held[5:0]>35)fault_hbm<=1;
   end
   idle_hbm<=tag_meta==tag_sync&&tag_sync==seen&&{vgo_h,kgo_h,ctrl_go_h}==0;
  end
 end
endmodule
module qkd_static_kv_drain_guard4 #(parameter integer MUT = 0) (
    input wire ck, rst_n,
    input wire [3:0] ctrl_idle_core, ring_idle_core,
    input wire [3:0] ctrl_idle_hbm, front_idle_hbm, ring_idle_hbm,
    input wire [3:0] ctrl_fault_core, ctrl_completion_fault_core, ctrl_intake_fault_core, ring_fault_core,
    input wire [3:0] ctrl_fault_hbm, ctrl_output_fault_hbm, ctrl_calendar_fault_hbm, ring_fault_hbm,
    input wire [3:0] front_fault_overflow_hbm, front_fault_go_hbm, front_hold_hbm,
    input wire upstream_quiet, upstream_fault,
    output reg drained, fault
);
    (* keep *) reg rn;
    always @(posedge ck) rn <= rst_n;
    // Every asynchronous observation crosses independently. Synchronizing a
    // combinational reduction in the HBM domain would create an unregistered
    // boundary cone and would not establish a real source-domain observation.
    (* async_reg = "true" *) reg [11:0] idle_meta, idle_sync;
    (* async_reg = "true" *) reg [27:0] fault_meta, fault_sync;
    reg [7:0] idle_core_q; reg [15:0] fault_core_q;
    reg quiet_q, upstream_fault_q, quiet_prev;
    always @(posedge ck or negedge rn) begin
        if (!rn) begin
            idle_meta <= 0; idle_sync <= 0;
            fault_meta <= 0; fault_sync <= 0;
            idle_core_q <= 0; fault_core_q <= 0;
            quiet_q <= 0; upstream_fault_q <= 0;
            quiet_prev <= 0; drained <= 0; fault <= 0;
        end else begin
            idle_meta <= {ctrl_idle_hbm, front_idle_hbm, ring_idle_hbm};
            idle_sync <= idle_meta;
            fault_meta <= {ctrl_fault_hbm, ctrl_output_fault_hbm, ctrl_calendar_fault_hbm, ring_fault_hbm,
                           front_fault_overflow_hbm, front_fault_go_hbm, front_hold_hbm};
            fault_sync <= fault_meta;
            idle_core_q <= {ctrl_idle_core, ring_idle_core};
            fault_core_q <= {ctrl_fault_core, ctrl_completion_fault_core, ctrl_intake_fault_core, ring_fault_core};
            quiet_q <= upstream_quiet; upstream_fault_q <= upstream_fault;
            quiet_prev <= ((MUT == 1) || (&idle_sync)) && (&idle_core_q) && quiet_q &&
                          !(|fault_sync) && !(|fault_core_q) && !upstream_fault_q && !fault;
            drained <= quiet_prev && ((MUT == 1) || (&idle_sync)) && (&idle_core_q) && quiet_q &&
                       !(|fault_sync) && !(|fault_core_q) && !upstream_fault_q && !fault;
            if (MUT != 2 && ((|fault_sync) || (|fault_core_q) || upstream_fault_q)) fault <= 1;
        end
    end
endmodule
module qkd_kv_cfault_node #(parameter integer R = 4, parameter integer STAGES = 1, parameter integer MUT = 0)(
    input  wire         ck,
    input  wire         rst_n,
    input  wire [R-1:0] fault_in,
    output wire         fault
);
    // MUT 1: leaf 0 dropped (the OR ignores input 0)
    wire [R-1:0] m = (MUT == 1) ? {fault_in[R-1:1], 1'b0} : fault_in;
    wire [STAGES:0] q;                                   // q[0] is the OR (combinational); q[1..STAGES] are flops
    assign q[0] = |m;
    genvar s;
    for (s = 1; s <= STAGES; s = s + 1) begin : st
        reg r;
        always @(posedge ck or negedge rst_n)
            if (!rst_n) r <= 1'b0;
            else        r <= q[s-1];
        assign q[s] = r;
    end
    assign fault = q[STAGES];
endmodule
module qkd_static_kv_boot_cdc #(parameter integer HAS_SEAL=0,MUT=0)(
 input wire ck,rst_n,hck,hrst_n,
 input wire cfg_we,input wire[7:0]cfg_addr,input wire[63:0]cfg_data,input wire cfg_last,
 output reg sink_we,output reg[7:0]sink_addr,output reg[63:0]sink_data,output reg sink_seal,
 output reg applied_hbm,output reg fault_core,output reg fault_hbm
);
 initial if(HAS_SEAL!=0&&HAS_SEAL!=1)$fatal(1,"explicit boot seal law required");
 wire ready,valid,overflow,underflow;wire[72:0]word;
 reg sealed_source;reg seal_pending,finish1,finish2;
 ot_async_fifo #(.WIDTH(73),.DEPTH(16),.EXT_RST(0))u_fifo(
 .wr_clk(ck),.wr_rst_n(rst_n),.wr_valid(cfg_we&&!sealed_source&&!fault_core),.wr_ready(ready),
 .wr_data({cfg_last,cfg_addr,cfg_data}),.wr_overflow(overflow),
 .rd_clk(hck),.rd_rst_n(hrst_n),.rd_valid(valid),.rd_ready(!seal_pending&&!applied_hbm),
 .rd_data(word),.rd_underflow(underflow));
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin sealed_source<=0;fault_core<=0;end
  else begin
   if(overflow||(cfg_we&&(!ready||sealed_source)))fault_core<=1;
   if(cfg_we&&cfg_last)sealed_source<=1;
  end
 end
 always @(posedge hck or negedge hrst_n)begin
  if(!hrst_n)begin sink_we<=0;sink_addr<=0;sink_data<=0;sink_seal<=0;applied_hbm<=0;fault_hbm<=0;seal_pending<=0;finish1<=0;finish2<=0;end
  else begin
   sink_we<=0;sink_seal<=0;finish1<=seal_pending;finish2<=finish1;
   if(underflow)fault_hbm<=1;
   if(seal_pending)begin sink_seal<=1'(HAS_SEAL);seal_pending<=0;end
   if(finish2)applied_hbm<=1;
   if(valid&&!seal_pending&&!applied_hbm)begin
    sink_we<=1;sink_addr<=word[71:64]^((MUT==1)?8'd1:8'd0);sink_data<=word[63:0];
    if(word[72])seal_pending<=1;
   end
   if(MUT==2&&valid)applied_hbm<=1;
  end
 end
endmodule
module qkd_kv_landing_cal #(parameter integer MUT = 0, parameter integer PH0 = 0) (
    input wire ck, rst_n,
    input wire cfg_we, input wire [7:0] cfg_addr, input wire [63:0] cfg_data,
    input wire kgo, input wire vgo,
    input wire [13:0] ctx_t, input wire [15:0] epoch, input wire [5:0] layer,
    output reg arm, output reg [15:0] l_epoch, output reg [5:0] l_layer,
    output reg [3:0] l_put, output reg [39:0] l_sector,
    output reg [3:0] r_put, output reg [39:0] r_sector, output reg [15:0] r_epoch, output reg [5:0] r_layer,
    output reg fault
);
    // ---- reset captured at its pin; every input pin registered ----
    (* keep *) reg rn;
    always @(posedge ck) rn <= rst_n;
    reg kgo_q, vgo_q, we_q;
    reg [7:0] ad_q; reg [63:0] cd_q; reg [13:0] ctx_q; reg [15:0] ep_q; reg [5:0] ly_q;
    always @(posedge ck or negedge rn)
        if (!rn) begin kgo_q <= 1'b0; vgo_q <= 1'b0; we_q <= 1'b0; end
        else begin kgo_q <= kgo; vgo_q <= vgo; we_q <= cfg_we; end
    always @(posedge ck) begin ad_q <= cfg_addr; cd_q <= cfg_data; ctx_q <= ctx_t; ep_q <= epoch; ly_q <= layer; end
    // ---- boot constants ----
    reg [1:0] s_c; reg [2:0] e_c; reg [9:0] xu_c; reg [7:0] h0_c; reg [3:0] rc_c, ld_c, kg_c, vg_c; reg [8:0] kp_c, vp_c;
    always @(posedge ck or negedge rn)
        if (!rn) begin s_c <= 0; e_c <= 0; xu_c <= 0; h0_c <= 0; rc_c <= 0; ld_c <= 0; kg_c <= 0; vg_c <= 0; kp_c <= 9'h1ff; vp_c <= 9'h1ff; end
        else if (we_q) case (ad_q)
            8'd0: begin s_c <= cd_q[4:3]; e_c <= cd_q[2:0]; end
            8'd1: xu_c <= cd_q[9:0];
            8'd2: h0_c <= cd_q[7:0];
            8'd3: begin rc_c <= cd_q[3:0]; ld_c <= cd_q[7:4]; end
            8'd4: begin kp_c <= cd_q[8:0]; kg_c <= cd_q[12:9]; end
            8'd5: begin vp_c <= cd_q[8:0]; vg_c <= cd_q[12:9]; end
            default: ;
        endcase
    // ---- core / HBM phase: q = u until the next HBM edge at / after this edge ----
    reg [9:0] q;
    always @(posedge ck or negedge rn)
        if (!rn) q <= 10'(PH0);
        else q <= (q >= 10'd625) ? q - 10'd625 : q + ((MUT == 2) ? 10'd144 : 10'd143);
    // ---- closed-form stream lengths (latched T of the layer) ----
    reg [13:0] t_l;
    // K row t = 512 a + 128 s + 64 b + 8 c + e; V row t = 512 a + 128 s + 64 b + 16 l + 2 c + par (e = {l, par})
    wire signed [15:0] xk = $signed({2'b0, (kgo_q ? ctx_q : t_l)}) - $signed({7'b0, s_c, 7'b0}) - $signed({13'b0, e_c});
    wire signed [15:0] xv = $signed({2'b0, t_l}) - $signed({7'b0, s_c, 7'b0}) - $signed({10'b0, e_c[2:1], 4'b0}) - $signed({15'b0, e_c[0]});
    // K t6 = 0 rows below x (order B first segment)
    function automatic [7:0] cnt0(input signed [15:0] x);
        reg [8:0] r; reg [9:0] h;
        begin
            r = x[8:0]; h = ({1'b0, r} + 10'd7) >> 3;
            cnt0 = (x <= 0) ? 8'd0 : (x[15:9] >= 7'd16) ? 8'd128 : {x[13:9], 3'b0} + ((h >= 10'd8) ? 8'd8 : 8'(h));
        end
    endfunction
    // QK calendar order: ns = 128 (T >> 9) + min(128, max(0, T[8:0] - 128 s)) > 1024 -> sector-ascending scan
    wire [13:0] tk = kgo_q ? ctx_q : t_l;
    wire ordb = (tk[13:9] > 5'd8) || (tk[13:9] == 5'd8 && {1'b0, tk[8:0]} > {1'b0, s_c, 7'b0});
    function automatic [8:0] cnt(input signed [15:0] x, input integer sh);   // rows below x: 16 per 512; c stride 1 << sh
        reg [8:0] r; reg [3:0] c0, c1; reg [9:0] h0, h1;
        begin
            r = x[8:0];
            h0 = ({1'b0, r} + 10'((1 << sh) - 1)) >> sh; h1 = (r > 9'd64) ? ({1'b0, r} - 10'd64 + 10'((1 << sh) - 1)) >> sh : 10'd0;
            c0 = (h0 >= 8) ? 4'd8 : 4'(h0); c1 = (h1 >= 8) ? 4'd8 : 4'(h1);
            cnt = (x <= 0) ? 9'd0 : (x[15:9] >= 7'd16) ? 9'd256 : {x[12:9], 4'b0} + {5'b0, c0} + {5'b0, c1};
        end
    endfunction
    // ---- pass state ----
    reg act, vpass, have_layer;
    reg [8:0] i, n; reg [7:0] nb0; reg kb;
    reg signed [19:0] d;                                // u until put i becomes visible, at the next edge
    wire [10:0] ta = (q >= xu_c) ? {1'b0, q} : {1'b0, q} + 11'd768;     // A - k0 in u (XU < 768: at most one HBM edge later)
    wire signed [19:0] t0 = $signed({9'b0, ta}) + $signed({2'b0, h0_c, 9'b0}) + $signed({3'b0, h0_c, 8'b0})
                          + $signed({6'b0, rc_c, 9'b0}) + $signed({9'b0, rc_c, 6'b0}) + $signed({10'b0, rc_c, 5'b0})
                          + $signed({11'b0, rc_c, 4'b0}) + $signed({15'b0, rc_c}) - 20'sd625;
    wire start = kgo_q | vgo_q;
    // ring pacing: put i + 1 starts a paced front block -> GAP more HBM edges (768 u each)
    wire [8:0] pp = vpass ? vp_c : kp_c; wire [3:0] pg = vpass ? vg_c : kg_c;
    wire [8:0] i1 = i + 9'd1;
    wire pace = (i1 >= pp) && (i1[2:0] == pp[2:0]);
    wire signed [19:0] gapu = $signed({6'b0, pg, 10'b0}) - $signed({8'b0, pg, 8'b0});
    wire emit = act && (d <= 0);
    wire [7:0] vo = i[7:0];
    wire [9:0] sec = vpass ? {1'b1, 1'b0, ((MUT == 1) ? vo[7] : vo[3]), ((MUT == 1) ? {vo[3], vo[6:4]} : vo[7:4]), vo[2:0]}
                           : (MUT == 3) ? {2'b0, vo}
                           : kb ? ((vo < nb0) ? {2'b0, vo} : {2'b0, 1'b1, 7'(vo - nb0)})
                           : {2'b0, vo[3], vo[7:4], vo[2:0]};
    always @(posedge ck or negedge rn)
        if (!rn) begin act <= 0; vpass <= 0; have_layer <= 0; i <= 0; n <= 0; d <= 0; nb0 <= 0; kb <= 0; t_l <= 0; fault <= 0; arm <= 0; end
        else begin
            arm <= kgo_q;
            if (start) begin
                if (act && !(emit && i + 9'd1 == n)) fault <= 1'b1;
                if (vgo_q && !have_layer) fault <= 1'b1;
                act <= 1'b1; i <= 0; d <= t0; vpass <= vgo_q;
                if (kgo_q) begin
                    have_layer <= 1'b1; t_l <= ctx_q; n <= cnt(xk, 3); nb0 <= cnt0(xk); kb <= ordb;
                end else n <= cnt(xv, 1);
            end else if (act) begin
                if (i == n) act <= 1'b0;
                else if (emit) begin i <= i + 9'd1; d <= d - 20'sd625 + 20'sd768 + (pace ? gapu : 20'sd0); if (i + 9'd1 == n) act <= 1'b0; end
                else d <= d - 20'sd625;
            end
            if (kgo_q && vgo_q) fault <= 1'b1;
        end
    // ---- outputs: return slots now, landing LD edges later (all registered) ----
    wire put_now = emit && i < n && !start;
    reg [10:0] dl [0:7];                                // LD 0..8 (return slot output register + <= 6 relays)
    integer k;
    always @(posedge ck or negedge rn)
        if (!rn) begin r_put <= 0; l_put <= 0; for (k = 0; k < 8; k = k + 1) dl[k] <= 0; end
        else begin
            r_put <= {4{put_now}};
            dl[0] <= {put_now, sec};
            for (k = 1; k < 8; k = k + 1) dl[k] <= dl[k-1];
            l_put <= {4{(ld_c == 0) ? put_now : dl[3'(ld_c - 4'd1)][10]}};
        end
    always @(posedge ck) begin
        r_sector <= {4{sec}};
        l_sector <= {4{(ld_c == 0) ? sec : dl[3'(ld_c - 4'd1)][9:0]}};
        if (start) begin r_epoch <= ep_q; r_layer <= ly_q; end
        if (kgo_q) begin l_epoch <= ep_q; l_layer <= ly_q; end
    end
endmodule
module ot_async_fifo #(
    parameter integer WIDTH = 32,
    parameter integer DEPTH = 4,
    // EXT_RST 1 (el1013-s81-vmfe/B8, coordinator decision 10-13): wr_rst_n / rd_rst_n are ALREADY the two domains' own
    // conditioned resets (each the output of that domain's reset synchroniser + registered tree, both synchronisers
    // cleared by the SAME asynchronous source, so an assertion still flushes both sides together).  No conditioner is
    // built here and no flop of one domain reaches a reset pin of the other: every recovery / removal arc is same-clock.
    parameter integer EXT_RST = 0
`ifdef OT_VMFE_FCC_PIPE
    , parameter integer FIFO_PIPE = 0, parameter integer PIPE_CHUNK = 128
`endif
) (
    input  wire             wr_clk,
    input  wire             wr_rst_n,
    input  wire             wr_valid,
    output wire             wr_ready,
    input  wire [WIDTH-1:0] wr_data,
    output reg              wr_overflow,
    input  wire             rd_clk,
    input  wire             rd_rst_n,
    output wire             rd_valid,
    input  wire             rd_ready,
    output wire [WIDTH-1:0] rd_data,
    output reg              rd_underflow
`ifdef OT_SPVM_RESET_ACK
    , output wire wr_reset_live, output wire rd_reset_live
`endif
);
    initial begin
        if (DEPTH < 4 || (DEPTH & (DEPTH-1)) != 0)
            $error("ot_async_fifo DEPTH must be a power of two >= 4");
    end

    localparam integer ADDR_W = $clog2(DEPTH);
    localparam integer PTR_W = ADDR_W + 1;
    wire fifo_async_rst_n = wr_rst_n && rd_rst_n;
    wire wr_domain_rst_n;
    wire rd_domain_rst_n;
    generate if (EXT_RST != 0) begin : g_xr
        assign wr_domain_rst_n = wr_rst_n;
        assign rd_domain_rst_n = rd_rst_n;
    end else begin : g_ir
        ot_reset_sync wr_reset_conditioner (
            .clk(wr_clk), .async_rst_n(fifo_async_rst_n),
            .sync_rst_n(wr_domain_rst_n));
        ot_reset_sync rd_reset_conditioner (
            .clk(rd_clk), .async_rst_n(fifo_async_rst_n),
            .sync_rst_n(rd_domain_rst_n));
    end endgenerate

    reg [WIDTH-1:0] mem [0:DEPTH-1];
`ifdef OT_VMFE_FCC_PIPE
    wire [PTR_W-1:0] wr_gray_visible;
`endif
    reg [PTR_W-1:0] wr_bin, wr_gray;
    reg [PTR_W-1:0] rd_bin, rd_gray;
    (* async_reg = "true" *) reg [PTR_W-1:0] rd_gray_w1, rd_gray_w2;
    (* async_reg = "true" *) reg [PTR_W-1:0] wr_gray_r1, wr_gray_r2;
    reg wr_online, rd_online;
    (* async_reg = "true" *) reg rd_online_w1, rd_online_w2;
    (* async_reg = "true" *) reg wr_online_r1, wr_online_r2;
`ifdef OT_S81_HOST_PHASESAFE
    reg [PTR_W-1:0] wr_gray_seam, rd_gray_seam;
    reg wr_online_seam, rd_online_seam;
    // plain lockup latches (enable = pure source clock, no reset term; sources are 0 while their domain is reset)
    always @* if (!wr_clk) begin wr_gray_seam=wr_gray;wr_online_seam=wr_online;end
    always @* if (!rd_clk) begin rd_gray_seam=rd_gray;rd_online_seam=rd_online;end
`else
    wire [PTR_W-1:0] wr_gray_seam=wr_gray,rd_gray_seam=rd_gray;
    wire wr_online_seam=wr_online,rd_online_seam=rd_online;
`endif
    reg wr_full, rd_empty;
    wire wr_fire = wr_valid && wr_ready;
    wire rd_fire = rd_valid && rd_ready;
    wire [PTR_W-1:0] wr_increment = {{(PTR_W-1){1'b0}},wr_fire};
    wire [PTR_W-1:0] wr_bin_next = wr_bin + wr_increment;
    wire [PTR_W-1:0] wr_gray_next = (wr_bin_next >> 1) ^ wr_bin_next;
    wire [PTR_W-1:0] rd_increment = {{(PTR_W-1){1'b0}},rd_fire};
    wire [PTR_W-1:0] rd_bin_next = rd_bin + rd_increment;
    wire [PTR_W-1:0] rd_gray_next = (rd_bin_next >> 1) ^ rd_bin_next;
    wire wr_full_next;
    wire rd_empty_next;

    // For a binary reflected Gray pointer, full is the write pointer one lap
    // ahead of read, i.e. the synchronized read pointer with its two MSBs
    // inverted.
    assign wr_full_next = (wr_gray_next ==
                           {~rd_gray_w2[PTR_W-1:PTR_W-2],
                            rd_gray_w2[PTR_W-3:0]});
    assign rd_empty_next = (rd_gray_next == wr_gray_r2);
    assign wr_ready = wr_domain_rst_n && rd_online_w2 && !wr_full;
    assign rd_valid = rd_domain_rst_n && wr_online_r2 && !rd_empty;
`ifdef OT_SPVM_RESET_ACK
    // Existing local online/rendezvous states; fullness/emptiness is not reset readiness.
    assign wr_reset_live = wr_domain_rst_n && wr_online && rd_online_w2;
    assign rd_reset_live = rd_domain_rst_n && rd_online && wr_online_r2;
`endif
`ifdef OT_VMFE_FCC_PIPE
    generate if (FIFO_PIPE != 0) begin : g_pipe
        localparam integer NCH = (WIDTH + PIPE_CHUNK - 1) / PIPE_CHUNK;
        reg [WIDTH-1:0] data_q;
        reg [PTR_W-1:0] pub_q;
        wire [DEPTH-1:0] selected [0:NCH-1], read_sel [0:NCH-1];
        wire [DEPTH-1:0] w_sel = {{(DEPTH-1){1'b0}},1'b1} << wr_bin[ADDR_W-1:0];
`ifdef OT_VMFE_MUT_FCC_PIPE_SELECT
        // Candidate-specific negative control: select the following entry.
        wire [ADDR_W-1:0] bad_read_addr = rd_bin_next[ADDR_W-1:0] + 1'b1;
        wire [DEPTH-1:0] r_sel_next = {{(DEPTH-1){1'b0}},1'b1} << bad_read_addr;
`else
        wire [DEPTH-1:0] r_sel_next = {{(DEPTH-1){1'b0}},1'b1} << rd_bin_next[ADDR_W-1:0];
`endif
        always @(posedge wr_clk) data_q <= wr_data; // payload reset-free, no valid-gated fanout
        always @(posedge wr_clk or negedge wr_domain_rst_n)
            if (!wr_domain_rst_n) pub_q <= {PTR_W{1'b0}};
            else pub_q <= wr_gray; // publish only when the preceding accepted entry commits
        assign wr_gray_visible = pub_q;
        for (genvar pc=0;pc<NCH;pc=pc+1) begin : g_c
            localparam integer LO=pc*PIPE_CHUNK;
            localparam integer CW=(WIDTH-LO < PIPE_CHUNK) ? WIDTH-LO : PIPE_CHUNK;
            // Distinct kept per-chunk select flops cap each real Q fanout at128 bits.
            ot_async_fifo_select_copy #(.W(DEPTH),.ID(pc),.RESET_ONE(0)) u_wsel
              (.clk(wr_clk),.rst_n(wr_domain_rst_n),.d(w_sel & {DEPTH{wr_fire}}),.q(selected[pc]));
            ot_async_fifo_select_copy #(.W(DEPTH),.ID(100+pc),.RESET_ONE(1)) u_rsel
              (.clk(rd_clk),.rst_n(rd_domain_rst_n),.d(r_sel_next),.q(read_sel[pc]));
            always @(posedge wr_clk) begin : p_write integer pe;
                for(pe=0;pe<DEPTH;pe=pe+1)
                    if(selected[pc][pe]) mem[pe][LO+:CW] <= data_q[LO+:CW];
            end
            reg [CW-1:0] row_or;
            always @* begin : p_read integer pe;
                row_or={CW{1'b0}};
                for(pe=0;pe<DEPTH;pe=pe+1)
                    row_or=row_or | (mem[pe][LO+:CW] & {CW{read_sel[pc][pe]}});
            end
            assign rd_data[LO+:CW]=row_or;
        end
    end else begin : g_no_pipe
        assign wr_gray_visible=wr_gray;
        assign rd_data=mem[rd_bin[ADDR_W-1:0]];
        always @(posedge wr_clk) if(wr_domain_rst_n && wr_fire) mem[wr_bin[ADDR_W-1:0]] <= wr_data;
    end endgenerate
`else
`ifdef OT_S81_HOST_PHASESAFE
    reg [WIDTH-1:0] head_seam;
    always @* if (rd_clk) head_seam=mem[rd_bin[ADDR_W-1:0]];
    assign rd_data=head_seam;
`else
    assign rd_data = mem[rd_bin[ADDR_W-1:0]];
`endif
`endif

    always @(posedge wr_clk or negedge wr_domain_rst_n) begin
        if (!wr_domain_rst_n) begin
            rd_gray_w1 <= {PTR_W{1'b0}};
            rd_gray_w2 <= {PTR_W{1'b0}};
            rd_online_w1 <= 1'b0;
            rd_online_w2 <= 1'b0;
            wr_online <= 1'b0;
            wr_bin <= {PTR_W{1'b0}};
            wr_gray <= {PTR_W{1'b0}};
            wr_full <= 1'b0;
            wr_overflow <= 1'b0;
        end else begin
            wr_online <= 1'b1;
            rd_online_w1 <= rd_online_seam;
            rd_online_w2 <= rd_online_w1;
            rd_gray_w1 <= rd_gray_seam;
            rd_gray_w2 <= rd_gray_w1;
            // Valid may legally remain asserted while ready is low.
`ifndef OT_VMFE_FCC_PIPE
            if (wr_fire)
                mem[wr_bin[ADDR_W-1:0]] <= wr_data;
`endif
            wr_bin <= wr_bin_next;
            wr_gray <= wr_gray_next;
            wr_full <= wr_full_next;
        end
    end

    always @(posedge rd_clk or negedge rd_domain_rst_n) begin
        if (!rd_domain_rst_n) begin
            wr_gray_r1 <= {PTR_W{1'b0}};
            wr_gray_r2 <= {PTR_W{1'b0}};
            wr_online_r1 <= 1'b0;
            wr_online_r2 <= 1'b0;
            rd_online <= 1'b0;
            rd_bin <= {PTR_W{1'b0}};
            rd_gray <= {PTR_W{1'b0}};
            rd_empty <= 1'b1;
            rd_underflow <= 1'b0;
        end else begin
            rd_online <= 1'b1;
            wr_online_r1 <= wr_online_seam;
            wr_online_r2 <= wr_online_r1;
`ifdef OT_VMFE_FCC_PIPE
            wr_gray_r1 <= wr_gray_visible;
`else
            wr_gray_r1 <= wr_gray_seam;
`endif
            wr_gray_r2 <= wr_gray_r1;
            // Ready may legally remain asserted while valid is low.
            rd_bin <= rd_bin_next;
            rd_gray <= rd_gray_next;
            rd_empty <= rd_empty_next;
        end
    end

`ifndef SYNTHESIS
    // Gray pointers may only change one bit per local write/read event.
    reg [PTR_W-1:0] wr_gray_prev, rd_gray_prev;
    wire [PTR_W-1:0] wr_gray_delta = wr_gray ^ wr_gray_prev;
    wire [PTR_W-1:0] rd_gray_delta = rd_gray ^ rd_gray_prev;
    wire [PTR_W-1:0] gray_one = {{(PTR_W-1){1'b0}},1'b1};
    wire wr_gray_multi = |(wr_gray_delta & (wr_gray_delta - gray_one));
    wire rd_gray_multi = |(rd_gray_delta & (rd_gray_delta - gray_one));
    always @(posedge wr_clk or negedge wr_domain_rst_n) begin
        if (!wr_domain_rst_n)
            wr_gray_prev <= {PTR_W{1'b0}};
        else begin
            if (wr_gray_multi)
                $error("ot_async_fifo write Gray pointer changed multiple bits");
            wr_gray_prev <= wr_gray;
        end
    end
    always @(posedge rd_clk or negedge rd_domain_rst_n) begin
        if (!rd_domain_rst_n)
            rd_gray_prev <= {PTR_W{1'b0}};
        else begin
            if (rd_gray_multi)
                $error("ot_async_fifo read Gray pointer changed multiple bits");
            rd_gray_prev <= rd_gray;
        end
    end
`endif
endmodule
module ot_reset_sync #(
    parameter integer ASYNC_STAGES = 2
) (
    input  wire clk,
    input  wire async_rst_n,
    output wire sync_rst_n
);
    (* async_reg = "true" *) reg [ASYNC_STAGES-1:0] reset_pipe;

    always @(posedge clk or negedge async_rst_n) begin
        if (!async_rst_n)
            reset_pipe <= {ASYNC_STAGES{1'b0}};
        else
            reset_pipe <= {reset_pipe[ASYNC_STAGES-2:0],1'b1};
    end

    assign sync_rst_n = reset_pipe[ASYNC_STAGES-1];

`ifndef SYNTHESIS
    initial begin
        if (ASYNC_STAGES < 2)
            $error("ot_reset_sync requires at least two stages");
    end
`endif
endmodule
module ot_async_fifo_select_copy #(parameter integer W=16,ID=0,RESET_ONE=0)
(input wire clk,rst_n,input wire [W-1:0] d,output reg [W-1:0] q);
    (* keep = 1 *) wire [W-1:0] dq=d;
    always @(posedge clk or negedge rst_n)
        if(!rst_n) q <= RESET_ONE ? {{(W-1){1'b0}},1'b1} : {W{1'b0}};
        else q<=dq;
endmodule
module qkd_static_kv_hop295 #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire[294:0]a,output wire[294:0]b);
 qkd_static_kv_hop #(.W(295),.MUT(MUT))u(.*);
endmodule
module qkd_static_kv_hop38 #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire[37:0]a,output wire[37:0]b);
 qkd_static_kv_hop #(.W(38),.MUT(MUT))u(.*);
endmodule
module qkd_static_kv_landing_pc #(
    parameter integer MUT=0, parameter integer VMAP=0,
    // FAULT_PIPE 1 (KVELEM 2026-10-16, landing_seg ls4): the fault conditions are registered once (fq) before the sticky
    // fault flop: the ticket[ra]/valid[ra] compare cone no longer ends in the fault OR (gate: -105 ps at 770 ps on
    // u_pc.fault/D).  Fault reports one edge later; no slot or data edge moves.  0 = historical single-edge fault.
    parameter integer FAULT_PIPE=0,
    // WRITE_PIPE 1 (KVELEM 2026-10-16, landing_seg ls5): the put side (SRAM write ce/addr/data and the ticket write) is
    // registered once more (put_d/wa_d/tk_d/ad_d) beside the SRAM and the ticket array: ls3 gate TT -43.3 ps on
    // ticket[*]/D (wa decode from the face pin register) and -36.3 ps on u_rows/w_addr_in.  The row is written one edge
    // later; valid[] and every fault check keep the put_q edge.  0 = historical.
    parameter integer WRITE_PIPE=0,
    // CHECK_PIPE 1 (KVELEM 2026-10-16, landing_seg ls5): the put/get CHECKER (valid[] / ticket[] / armed / active epoch /
    // fault) runs one edge behind the data path on relay registers of every operand it reads (k_*).  The checker never
    // feeds data (SRAM write/read, out_* are unchanged), and put and get are delayed alike, so it sees the identical event
    // sequence and latches exactly the same faults one edge later.  Why: in the seg tile the put operands land at each PC's
    // quarter of the E face while get / arm / epoch arrive at the centre; the ls4 gate (TT, placement RC) had all 715
    // failing endpoints in the checker starting at ps_q (valid[*] -44.4, ticket[*][*] -31.5, fq -30.7, w_addr -21.6) through
    // ~400 ps of buffered wire.  The relays give that wire a full cycle and leave ps_q beside its pins and SRAM.  The ticket
    // keeps only {sector[9], ordinal[7]}: its low 7 bits are the row index itself (written at w_a = put_ord[6:0], read at
    // ra = get_ord[6:0]), so the 9-bit compare reduces to 2 bits exactly; valid[] is updated per bit (set_i | valid & ~clr_i,
    // the same next state without the shared wa == ra compare).  0 = historical checker on the _q edge.
    parameter integer CHECK_PIPE=0,
    // PRE_REG 1 (KVCTRL 1815, landing_seg_h): arm / epoch / layer / cfg_stack / cfg_group arrive ALREADY REGISTERED by an
    // identical register placed upstream (qkd_static_kv_landing_relay / _row, within measured reach of the shared
    // segment pins); arm_q / epoch_q / layer_q / stack_q / group_q are then those inputs (same edge from the segment pin,
    // the upstream arm register resets like arm_q). 0 = the PC's own input registers (default, unchanged).
    parameter integer PRE_REG=0
)(
    input wire ck, rst_n,
    input wire [1:0] cfg_stack,input wire [2:0] cfg_group,
    input wire arm,
    input wire [15:0] epoch,
    input wire [5:0] layer,
    input wire expected_put,
    input wire [9:0] expected_sector,
    input wire actual_valid,
    input wire [9:0] actual_sector,
    input wire [15:0] actual_epoch,
    input wire [5:0] actual_layer,
    input wire [255:0] actual_data,
    input wire get,
    input wire [13:0] get_t,
    input wire get_v,
    input wire [15:0] get_epoch,
    input wire [5:0] get_layer,
    output reg out_valid,
    output reg [255:0] out_data,
    output reg [13:0] out_t,
    output reg out_v,
    output reg [15:0] out_epoch,
    output reg [5:0] out_layer,
    output reg fault
);
    (* keep *) reg [1:0] stack_q;
    (* keep *) reg [2:0] group_q;
    generate if(PRE_REG==0)begin:g_cfg_r
      always @(posedge ck)begin stack_q<=cfg_stack;group_q<=cfg_group;end
    end else begin:g_cfg_w
      always @(*)begin stack_q=cfg_stack;group_q=cfg_group;end
    end endgenerate
    (* keep *) reg rn;
    always @(posedge ck) rn <= rst_n;
    (* keep *) reg arm_q, put_q, actual_q, get_q;
    (* keep *) reg [15:0] epoch_q, ae_q, ge_q;
    (* keep *) reg [5:0] layer_q, al_q, gl_q;
    (* keep *) reg [9:0] ps_q, as_q;
    (* keep *) reg [255:0] ad_q;
    (* keep *) reg [13:0] gt_q;
    (* keep *) reg gv_q;
    always @(posedge ck) begin
        ae_q<=actual_epoch;al_q<=actual_layer;
        ge_q<=get_epoch;gl_q<=get_layer;ps_q<=expected_sector;as_q<=actual_sector;
        ad_q<=actual_data;gt_q<=get_t;gv_q<=get_v;
    end
    always @(posedge ck or negedge rn)
      if(!rn)begin put_q<=0;actual_q<=0;get_q<=0;end
      else begin put_q<=expected_put;actual_q<=actual_valid;get_q<=get;end
    generate if(PRE_REG==0)begin:g_arm_r
      always @(posedge ck)begin epoch_q<=epoch;layer_q<=layer;end
      always @(posedge ck or negedge rn) if(!rn)arm_q<=0; else arm_q<=arm;
    end else begin:g_arm_w
      always @(*)begin epoch_q=epoch;layer_q=layer;arm_q=arm;end
    end endgenerate
    // Row ordinal = the controller's STREAM position of the sector, for K and V alike: rows < T of a group arrive in
    // ascending t, i.e. ascending {t[12:9], t[6], t[5:3] (K) / t[3:1] (V VMAP 1)} = {sec[6:3], sec[7], sec[2:0]}, a
    // gap-free prefix at any T, so with <= 64 rows outstanding (ring bound) no two live rows share a row.
    // (Q-VMWB 10-16: K used sec[7:0] = {t6, t[12:9], t[5:3]}: the t6 = 0 / 1 rows of one t[12:9] are 8 stream
    // positions apart on the same row -> alias at mid T; kv_calendar T 2048 / 4096: slack -4 / -19 core edges.)
    // MUT 3: the old K ordinal (bench negative control).
    function automatic [7:0] ordinal(input [9:0] sec);
        ordinal=(sec[9]||MUT!=3)?{sec[6:3],sec[7],sec[2:0]}:sec[7:0];
    endfunction
    wire gvm=(VMAP!=0)&&gv_q;
    wire [9:0] get_sector={gv_q,1'b0,gt_q[6],gt_q[12:9],gvm?gt_q[3:1]:gt_q[5:3]};
    wire [2:0] get_group=gvm?{gt_q[5:4],gt_q[0]}:gt_q[2:0];
    wire [7:0] put_ord=ordinal(ps_q),get_ord=ordinal(get_sector);
    wire [8:0] put_ticket={ps_q[9],put_ord},get_ticket={gv_q,get_ord};
    wire [6:0] wa=put_ord[6:0],ra=get_ord[6:0];
    reg [127:0] valid;
    reg [8:0] ticket[0:127];
    reg [15:0] active_epoch;
    reg [5:0] active_layer;
    reg armed;
    wire [255:0] mem_q;
    (* keep *) reg put_d;
    (* keep *) reg [6:0] wa_d;
    (* keep *) reg [8:0] tk_d;
    (* keep *) reg [255:0] ad_d;
    always @(posedge ck) begin wa_d<=wa;tk_d<=(MUT==1)?(put_ticket^9'b1):put_ticket;ad_d<=ad_q; end
    always @(posedge ck or negedge rn) if(!rn)put_d<=0; else put_d<=(WRITE_PIPE!=0)&&put_q;
    wire w_ce=(WRITE_PIPE!=0)?put_d:put_q;
    wire [6:0] w_a=(WRITE_PIPE!=0)?wa_d:wa;
    wire [255:0] w_d=(WRITE_PIPE!=0)?ad_d:ad_q;
    wire [8:0] w_tk=(WRITE_PIPE!=0)?tk_d:((MUT==1)?(put_ticket^9'b1):put_ticket);
    ot_sram_1r1w_128x256_m1_r2c2 u_rows(
      .clk(ck),.r_ce_in(get_q),.r_addr_in(ra),.rd_out(mem_q),
      .w_ce_in(w_ce),.w_addr_in(w_a),.wd_in(w_d),.w_mask_in({256{1'b1}}),
      .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
    reg read_q;
    reg [13:0] rt_q;
    reg rv_q;
    reg [15:0] re_q;
    reg [5:0] rl_q;
    always @(posedge ck) begin
      rt_q<=gt_q;rv_q<=gv_q;re_q<=ge_q;rl_q<=gl_q;
      out_t<=rt_q;out_v<=rv_q;out_epoch<=re_q;out_layer<=rl_q;
      out_data<=(MUT==2)?(mem_q^256'b1):mem_q;
      if(CHECK_PIPE==0 && w_ce)ticket[w_a]<=w_tk;
    end
    always @(posedge ck or negedge rn)
      if(!rn)begin read_q<=0;out_valid<=0;end
      else begin read_q<=get_q;out_valid<=read_q;end
    (* keep *) reg fq;
    generate if(CHECK_PIPE==0)begin:g_chk0
      // registered fault conditions (FAULT_PIPE 1): the same put/get checks as below, captured one edge before fault
      wire fq_put=put_q&&((!armed||ps_q[8]||as_q!=ps_q||ae_q!=active_epoch||al_q!=active_layer)||(valid[wa]&&!(get_q&&ra==wa)));
      wire fq_get=get_q&&(!armed||!valid[ra]||ticket[ra]!=get_ticket||ge_q!=active_epoch||gl_q!=active_layer||
                          gt_q[13]||get_group!=group_q||gt_q[8:7]!=stack_q);
      always @(posedge ck or negedge rn) if(!rn)fq<=0; else fq<=(FAULT_PIPE!=0)&&(fq_put||fq_get);
      always @(posedge ck or negedge rn)
        if(!rn)begin valid<=0;fault<=0;active_epoch<=0;active_layer<=0;armed<=0;end
        else begin
          if(FAULT_PIPE!=0 && fq)fault<=1;
          if(arm_q)begin
            if((|valid)||put_q||get_q)fault<=1;
            active_epoch<=epoch_q;active_layer<=layer_q;armed<=1;valid<=0;
          end
          if(put_q!=actual_q)fault<=1;
          if(put_q)begin
            if(FAULT_PIPE==0 && (!armed||ps_q[8]||as_q!=ps_q||ae_q!=active_epoch||al_q!=active_layer))fault<=1;
            if(FAULT_PIPE==0 && valid[wa]&&!(get_q&&ra==wa))fault<=1;
            valid[wa]<=1;
          end
          if(get_q)begin
            if(!armed||!valid[ra]||ticket[ra]!=get_ticket||ge_q!=active_epoch||gl_q!=active_layer||
               gt_q[13]||get_group!=group_q||gt_q[8:7]!=stack_q)begin if(FAULT_PIPE==0)fault<=1;end
            if(!(put_q&&wa==ra))valid[ra]<=0;
          end
        end
    end else begin:g_chk1
      // relay stage: every checker operand one edge later (put side computed beside its pin registers, get side beside
      // the request hop, arm / epoch from the centre); the placer sites the checker between them
      (* keep *) reg k_arm,k_put,k_act,k_get,k_pchk,k_gchk;
      (* keep *) reg [6:0] k_wa,k_ra;
      (* keep *) reg [1:0] k_ptk,k_gtk;
      (* keep *) reg [15:0] k_ae,k_ge,k_ep;
      (* keep *) reg [5:0] k_al,k_gl,k_ly;
      always @(posedge ck)begin
        k_wa<=wa;k_ra<=ra;
        k_ptk<={ps_q[9],put_ord[7]}^((MUT==1)?2'b01:2'b00);k_gtk<={gv_q,get_ord[7]};
        k_pchk<=ps_q[8]||as_q!=ps_q;
        k_gchk<=gt_q[13]||get_group!=group_q||gt_q[8:7]!=stack_q;
        k_ae<=ae_q;k_al<=al_q;k_ge<=ge_q;k_gl<=gl_q;k_ep<=epoch_q;k_ly<=layer_q;
      end
      always @(posedge ck or negedge rn)
        if(!rn)begin k_arm<=0;k_put<=0;k_act<=0;k_get<=0;end
        else begin k_arm<=arm_q;k_put<=put_q;k_act<=actual_q;k_get<=get_q;end
      reg [1:0] tk2[0:127];
      always @(posedge ck) if(k_put)tk2[k_wa]<=k_ptk;
      wire k_fput=k_put&&(!armed||k_pchk||k_ae!=active_epoch||k_al!=active_layer||(valid[k_wa]&&!(k_get&&k_ra==k_wa)));
      wire k_fget=k_get&&(!armed||!valid[k_ra]||tk2[k_ra]!=k_gtk||k_ge!=active_epoch||k_gl!=active_layer||k_gchk);
      always @(posedge ck or negedge rn) if(!rn)fq<=0; else fq<=(FAULT_PIPE!=0)&&(k_fput||k_fget);
      // per-bit next state = historical (arm clears, put sets, a get clears unless a put to the same row): set | valid & ~clr
      wire [127:0] v_set=k_put?(128'b1<<k_wa):128'b0, v_clr=k_get?(128'b1<<k_ra):128'b0;
      always @(posedge ck or negedge rn)
        if(!rn)begin valid<=0;fault<=0;active_epoch<=0;active_layer<=0;armed<=0;end
        else begin
          valid<=v_set|(valid&~v_clr&{128{!k_arm}});
          if(FAULT_PIPE!=0 && fq)fault<=1;
          if(FAULT_PIPE==0 && (k_fput||k_fget))fault<=1;
          if(k_arm)begin
            if((|valid)||k_put||k_get)fault<=1;
            active_epoch<=k_ep;active_layer<=k_ly;armed<=1;
          end
          if(k_put!=k_act)fault<=1;
        end
    end endgenerate
endmodule
module qkd_static_kv_rowctl #(parameter integer VREQ=0,parameter integer DATA=1)(
    input wire ck,rst_n,
    input wire req_valid,input wire [13:0] req_t,input wire req_v,
    input wire [15:0] req_epoch,input wire [5:0] req_layer,
    input wire vreq_valid,input wire [13:0] vreq_t,
    input wire arm,input wire [15:0] epoch,input wire [5:0] layer,
    output wire [3:0] pc_get,output wire [55:0] pc_get_t,output wire [3:0] pc_get_v,
    output wire [63:0] pc_get_epoch,output wire [23:0] pc_get_layer,
    input wire [3:0] pc_valid,input wire [1023:0] pc_data,input wire [55:0] pc_t,
    input wire [3:0] pc_v,input wire [63:0] pc_epoch,input wire [23:0] pc_layer,
    input wire [3:0] pc_fault,
    output reg rsp_valid,output reg [1023:0] rsp_data,output reg [13:0] rsp_t,
    output reg rsp_v,output reg [15:0] rsp_epoch,output reg [5:0] rsp_layer,output reg fault
);
    (* keep *) reg rn;
    always @(posedge ck)rn<=rst_n;
    (* keep *) reg rq;
    (* keep *) reg [13:0] tq;
    (* keep *) reg vq;
    (* keep *) reg [15:0] eq;
    (* keep *) reg [5:0] lq;
    always @(posedge ck)begin tq<=req_t;vq<=req_v;eq<=req_epoch;lq<=req_layer;end
    always @(posedge ck or negedge rn)if(!rn)rq<=0;else rq<=req_valid;
    wire collide;
    generate if(VREQ!=0)begin:g_vreq
      (* keep *) reg vrq;
      (* keep *) reg [13:0] vtq;
      always @(posedge ck)vtq<=vreq_t;
      always @(posedge ck or negedge rn)if(!rn)vrq<=0;else vrq<=vreq_valid;
      (* keep *) reg aq;(* keep *) reg [15:0] aeq;(* keep *) reg [5:0] alq;
      reg [15:0] ke;reg [5:0] kl;                  // epoch / layer the group is armed with
      reg mq;reg [13:0] mt;reg mv;reg [15:0] me;reg [5:0] ml;
      always @(posedge ck)begin
        aeq<=epoch;alq<=layer;
        if(aq)begin ke<=aeq;kl<=alq;end
        mt<=vrq?vtq:tq;mv<=vrq|vq;me<=vrq?ke:eq;ml<=vrq?kl:lq;
      end
      always @(posedge ck or negedge rn)if(!rn)aq<=0;else aq<=arm;
      always @(posedge ck or negedge rn)if(!rn)mq<=0;else mq<=rq|vrq;
      assign collide=rq&vrq;
      assign pc_get={4{mq}};assign pc_get_t={4{mt}};assign pc_get_v={4{mv}};
      assign pc_get_epoch={4{me}};assign pc_get_layer={4{ml}};
    end else begin:g_k
      assign collide=1'b0;
      assign pc_get={4{rq}};assign pc_get_t={4{tq}};assign pc_get_v={4{vq}};
      assign pc_get_epoch={4{eq}};assign pc_get_layer={4{lq}};
    end endgenerate
    (* keep *) reg [3:0] iv,ivv,ifault;
    (* keep *) reg [55:0] it;
    (* keep *) reg [63:0] ie;
    (* keep *) reg [23:0] il;
    generate if(DATA!=0)begin:g_data
      (* keep *) reg [1023:0] idata;
      always @(posedge ck)begin idata<=pc_data;rsp_data<=idata;end
    end else begin:g_nodata
      always @(*)rsp_data=1024'd0;
    end endgenerate
    always @(posedge ck)begin
      it<=pc_t;ivv<=pc_v;ie<=pc_epoch;il<=pc_layer;
      rsp_t<=it[13:0];rsp_v<=ivv[0];rsp_epoch<=ie[15:0];rsp_layer<=il[5:0];
    end
    always @(posedge ck or negedge rn)
      if(!rn)begin iv<=0;ifault<=0;rsp_valid<=0;fault<=0;end
      else begin
        iv<=pc_valid;ifault<=pc_fault;rsp_valid<=iv[0];
        if((|ifault)||iv!={4{iv[0]}}||collide)fault<=1;
        if(iv[0]&&((it!={4{it[13:0]}})||(ivv!={4{ivv[0]}})||(ie!={4{ie[15:0]}})||(il!={4{il[5:0]}})))fault<=1;
      end
endmodule
`timescale 1ns/1ps
// ot_sram_1r1w_128x256_m1_r2c2: ASAP7 1R1W SRAM 128 x 256, mux 1, 1 bank(s), 2 spare row(s), 2 spare IO column(s); OpenTallas tools/mem_compiler/sram_gen.py v1.0+aligned-v2
// verilator lint_off BLKSEQ
// verilator lint_off WIDTH
// verilator lint_off UNUSED
module ot_sram_1r1w_128x256_m1_r2c2 (
    input  wire clk,
    input  wire r_ce_in,
    input  wire [6:0] r_addr_in,
    output reg  [255:0] rd_out,
    input  wire w_ce_in,
    input  wire [6:0] w_addr_in,
    input  wire [255:0] wd_in,
    input  wire [255:0] w_mask_in,
    input  wire [1:0] rr_en,
    input  wire [13:0] rr_addr,
    input  wire [1:0] cr_en,
    input  wire [15:0] cr_sel
);
    localparam integer WORDS = 128;
    localparam integer BITS = 256;
    localparam integer MUX = 1;
    localparam integer AW = 7;
    localparam integer ROWS = 128;
    localparam integer NSR = 2;
    localparam integer NSC = 2;
    localparam integer PR = 130;
    localparam integer PC = 258;
    localparam integer RA = 7;
    localparam integer CB = 8;

    // physical array: main rows, then spare rows; columns bit-interleaved by MUX
    reg [PC-1:0] arr [0:PR-1];
    integer init_i;
    // Power-up content: zero in simulation.  Silicon powers up random; a March C-
    // self-test ends with its (r0) element, so a tested array holds zeros too.
    initial begin
`ifndef OT_MEM_NO_INIT
        for (init_i = 0; init_i < PR; init_i = init_i + 1) arr[init_i] = {PC{1'b0}};
`endif
    end

`ifdef OT_MEM_FAULTS
    localparam integer NF = 8;
    reg [3:0]  f_kind [0:NF-1];
    integer    f_r    [0:NF-1];
    integer    f_c    [0:NF-1];
    integer    f_ar   [0:NF-1];
    integer    f_ac   [0:NF-1];
    reg [1:0]  f_v    [0:NF-1];
    integer fk;
    initial for (fk = 0; fk < NF; fk = fk + 1) begin
        f_kind[fk] = 4'd0; f_r[fk] = 0; f_c[fk] = 0; f_ar[fk] = 0; f_ac[fk] = 0; f_v[fk] = 2'd0;
    end
`endif


    // ---- physical row and column after repair ------------------------------
    function automatic integer phys_row(input integer a);
        integer k, r;
        begin
            r = a / MUX;
            for (k = 0; k < NSR; k = k + 1)
                if (rr_en[k] && rr_addr[k*RA +: RA] == r[RA-1:0]) r = ROWS + k;
            phys_row = r;
        end
    endfunction

    function automatic integer phys_col(input integer b, input integer s);
        integer k, io;
        begin
            io = b;
            for (k = 0; k < NSC; k = k + 1)
                if (cr_en[k] && cr_sel[k*CB +: CB] == b[CB-1:0]) io = BITS + k;
            phys_col = io * MUX + s;
        end
    endfunction

    // ---- one cell, as the sense amplifier sees it ----------------------------
    function automatic cell_read(input integer r, input integer c);
        reg v;
`ifdef OT_MEM_FAULTS
        integer k;
`endif
        begin
            v = arr[r][c];
`ifdef OT_MEM_FAULTS
            for (k = 0; k < NF; k = k + 1) begin
                if ((f_kind[k] == 4'd1 || f_kind[k] == 4'd2) && f_r[k] == r && f_c[k] == c) v = (f_kind[k] == 4'd2);
                if (f_kind[k] == 4'd7 && f_r[k] == r && f_c[k] == c && arr[f_ar[k]][f_ac[k]] == f_v[k][0]) v = f_v[k][1];
                if (f_kind[k] == 4'd11 && f_r[k] == r) v = f_v[k][0];
                if (f_kind[k] == 4'd12 && f_c[k] == c) v = f_v[k][0];
            end
`endif
            cell_read = v;
        end
    endfunction

    task automatic cell_write(input integer r, input integer c, input reg v);
        reg old, nv;
`ifdef OT_MEM_FAULTS
        integer k;
`endif
        begin
            old = arr[r][c];
            nv = v;
`ifdef OT_MEM_FAULTS
            for (k = 0; k < NF; k = k + 1) begin
                if (f_kind[k] == 4'd3 && f_r[k] == r && f_c[k] == c && !old && v) nv = 1'b0;
                if (f_kind[k] == 4'd4 && f_r[k] == r && f_c[k] == c && old && !v) nv = 1'b1;
            end
`endif
            arr[r][c] = nv;
`ifdef OT_MEM_FAULTS
            if (old != nv)
                for (k = 0; k < NF; k = k + 1)
                    if (f_ar[k] == r && f_ac[k] == c && nv == f_v[k][0]) begin
                        if (f_kind[k] == 4'd5) arr[f_r[k]][f_c[k]] = ~arr[f_r[k]][f_c[k]];
                        if (f_kind[k] == 4'd6) arr[f_r[k]][f_c[k]] = f_v[k][1];
                    end
`endif
        end
    endtask

    // ---- decoder: the physical rows an access selects -------------------------
    // returns {sel_n[1:0], r1[31:0], r0[31:0]}; sel_n is 0 (no row: an open decoder
    // output), 1, or 2 (a multi-select).
    function automatic [65:0] decode(input integer a);
        integer r0, r1;
        reg [1:0] sel_n;
`ifdef OT_MEM_FAULTS
        integer k;
`endif
        begin
            r0 = phys_row(a);
            r1 = r0;
            sel_n = 2'd1;
`ifdef OT_MEM_FAULTS
            if (r0 < ROWS)
                for (k = 0; k < NF; k = k + 1) begin
                    if (f_kind[k] == 4'd8 && f_r[k] == r0) sel_n = 2'd0;
                    if (f_kind[k] == 4'd9 && f_r[k] == r0) begin r0 = f_ar[k]; r1 = r0; end
                    if (f_kind[k] == 4'd10 && f_r[k] == r0) begin r1 = f_ar[k]; sel_n = 2'd2; end
                end
`endif
            decode = {sel_n, r1[31:0], r0[31:0]};
        end
    endfunction

    function automatic [BITS-1:0] word_read(input integer a);
        integer b, s, r0, r1, n;
        reg [BITS-1:0] q;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (n == 0) q[b] = 1'b0;
                else if (n == 1) q[b] = cell_read(r0, phys_col(b, s));
                else q[b] = cell_read(r0, phys_col(b, s)) & cell_read(r1, phys_col(b, s));
            word_read = q;
        end
    endfunction


    task automatic word_write(input integer a, input [BITS-1:0] d, input [BITS-1:0] m);
        integer b, s, r0, r1, n;
        reg [65:0] dsel;
        begin
            dsel = decode(a);
            r0 = dsel[31:0]; r1 = dsel[63:32]; n = dsel[65:64];
            s = a % MUX;
            for (b = 0; b < BITS; b = b + 1)
                if (m[b] && n != 0) begin
                    cell_write(r0, phys_col(b, s), d[b]);
                    if (n == 2) cell_write(r1, phys_col(b, s), d[b]);
                end
        end
    endtask

    // read-before-write: a same-address read in the write cycle returns the old word
    always @(posedge clk) begin
        if (r_ce_in) rd_out <= word_read(r_addr_in);
        if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in);
    end
endmodule
// verilator lint_on BLKSEQ
// verilator lint_on WIDTH
// verilator lint_on UNUSED

module qkd_static_kv_hop #(parameter integer W=38,MUT=0)(
 input wire ck,rst_n,input wire [W-1:0] a,output reg [W-1:0] b);
 (* keep *) reg rn;
 always @(posedge ck or negedge rst_n)if(!rst_n)rn<=0;else rn<=1;
 always @(posedge ck or negedge rn)
  if(!rn)b<=0;
  else b<=MUT!=0 ? a^{{(W-2){1'b0}},2'b10} : a;
endmodule