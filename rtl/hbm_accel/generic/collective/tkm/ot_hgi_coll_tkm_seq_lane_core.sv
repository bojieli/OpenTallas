`timescale 1ns/1ps
// Own-flop core after four ingress lanes leave the root. Original closed tile remains separate.
module ot_hgi_coll_tkm_seq_lane_core #(
    parameter integer KMAX = 64,      // the die instance sets 2,048 (ot_hgi_coll_ep TKM_KMAX); a small default keeps read-time elaboration cheap
    parameter integer DEL  = 4,
    parameter integer FW   = 512,
    parameter integer PWT  = FW + 33,
    parameter integer CAP  = 64,
    parameter integer MUT  = 0
) (
    output wire [339:0] chain_entry,
    output wire chain_valid,
    input wire [339:0] chain_up,
    output wire [((KMAX+63)/64)-1:0] chain_clr, chain_conv,
    output wire [6*((KMAX+63)/64)-1:0] chain_tt,
    output wire [7*((KMAX+63)/64)-1:0] chain_tl,
    input wire [84*((KMAX+63)/64)-1:0] chain_tau,
    input wire [((KMAX+63)/64)-1:0] chain_busy,
    input wire [DEL-1:0] lane_d0v,lane_d1v,
    input wire [DEL-1:0] lane_fault,lane_dv,lane_ldv,
    input wire[2719:0]lane_heads0,lane_heads1,lane_heads2,lane_heads3,
    input wire[31:0]lane_masks0,lane_masks1,lane_masks2,lane_masks3,
    input wire[7:0]lane_epoch0,lane_epoch1,lane_epoch2,lane_epoch3,
    input wire[2:0]lane_hn0,lane_hn1,lane_hn2,lane_hn3,
    output reg[DEL*8-1:0]lane_take_epochs,
    input wire [DEL*8-1:0] lane_nv_mask,
    input wire [DEL*8-1:0] lane_occ,
    output reg [DEL*8-1:0] lane_take,
    output reg [DEL-1:0] lane_pop,
    output reg lane_live,
    output wire [82:0] lane_tau,
    output wire [7:0] lane_g,lane_gb,
    output wire [15:0] lane_pf,
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,          // one edge: configuration below valid
    input  wire [11:0]          cfg_n,          // this rank's n (informational: validity is the sender's pad marker)
    input  wire [12:0]          cfg_k,          // k: O.n must equal min(k, elements received)
    input  wire [7:0]           cfg_g,          // group size
    input  wire [7:0]           cfg_gbase,      // the group's first rank (flit src - gbase = q)
    input  wire [15:0]          cfg_pf,         // ceil(n / 8)
    input  wire [12:0]          cfg_nout,       // O.n = min(k, the group's elements), 1 .. KMAX
    input  wire [39:0]          cfg_obase,      // O: VM word address (16-word aligned)
    input  wire [39:0]          cfg_rbase,      // R: VM word address (16-word aligned)
    input  wire                 cfg_has_r,
    output wire buf_w_v,buf_r_v,output wire[9:0]buf_w_addr,buf_r_addr,output wire[339:0]buf_w_data,
    input wire buf_rd_v,input wire[339:0]buf_rd_data,
    input wire w_v, pack_empty,
    input wire[3:0] pack_queued,input wire[9:0] pack_lines,
    output reg pack_start,pack_cell_v,pack_last,
    output reg[339:0]pack_cell,output reg[1:0]pack_slot,
    output wire[12:0]pack_nout,output wire[39:0]pack_obase,pack_rbase,output wire pack_has_r,
    output reg                  busy,
    output reg                  done,           // one edge: every output line accepted
    output reg                  fault,
    output reg  [31:0]          stat_cycles,    // start -> done
    output reg  [31:0]          stat_ins,       // blocks inserted
    output reg  [31:0]          stat_surv       // survivors taken
);
    // Internal counters / busy keep their own state; the ports are separate same-edge copies with no internal
    // fanout so the flow can place them at their pins (measured R2: 273 reg->out paths, worst stat_surv -622 ps,
    // were the feedback-loaded counters themselves driving the face).
    reg [31:0] st_cyc, st_ins, st_surv; reg busy_q;

    localparam integer W  = 4;
    localparam integer C  = KMAX / W;
    localparam integer EW = 85;               // {region, valid, okey, ~id, ~q, ~j, nz}
    localparam integer KW = 83;
    localparam integer VB = 83;               // the valid bit (bit EW-1 is the region tag)
    localparam integer CB = $clog2(C + 1);
    localparam integer QW = 8 * EW;            // FIFO word: 8 elements
    // ---------------------------------------------------------------- element helpers
    function automatic [31:0] okey(input [31:0] x);
        reg [31:0] c;
        begin
            c = (x == 32'h8000_0000) ? 32'h0 : x;
            okey = c[31] ? ~c : (c | 32'h8000_0000);
        end
    endfunction
    function automatic [31:0] unkey(input [31:0] k, input nz);
        unkey = nz ? 32'h8000_0000 : (k[31] ? (k & 32'h7FFF_FFFF) : ~k);
    endfunction
    function automatic [KW-1:0] vkey(input [EW-1:0] e);
        vkey = e[VB:1];
    endfunction
    function automatic [KW-1:0] ikey(input [EW-1:0] e);
        ikey = {e[83], e[50:19], e[82:51], e[18:1]};
    endfunction
    // insertion key (84 bits): {valid, ~region, body}: region 0 = the value order (selection phase), region 1 = the id
    // order (re-insertion phase, always below region 0); an invalid element is 0 (the lowest)
    function automatic [KW:0] key2(input [EW-1:0] e);
        reg [KW-1:0] b_;
        begin
            b_ = e[84] ? ikey(e) : vkey(e);
            key2 = e[83] ? {1'b1, ~e[84], b_[KW-2:0]} : {(KW+1){1'b0}};
        end
    endfunction
    // KEY FORM (r3, the chain's storage format): T = {key2(e), nz} -- T[EW-1:1] is the 84-bit insertion key, so the
    // tiles compare stored bits with no key mux; tinv restores the element (an invalid element is 0 in both forms)
    function automatic [EW-1:0] tform(input [EW-1:0] e);
        tform = e[83] ? {key2(e), e[0]} : {EW{1'b0}};
    endfunction
    function automatic [EW-1:0] tinv(input [EW-1:0] t);
        reg [81:0] b_;
        begin
            b_ = t[82:1];
            tinv = !t[84] ? {EW{1'b0}} : (!t[83] ? {1'b1, 1'b1, b_[49:18], b_[81:50], b_[17:0], t[0]} : {1'b0, 1'b1, b_, t[0]});
        end
    endfunction
    // ---------------------------------------------------------------- configuration
    reg [11:0] n_q; reg [7:0] g_q, gb_q; reg [15:0] pf_q; reg [12:0] nout_q; reg [39:0] ob_q, rb_q; reg hr_q;
    reg [23:0] tot_q;                          // G pf flits expected
    reg [CB-1:0] cact_q;                       // ceil(nout / 4) active cells
    reg [CB-1:0] tc_q; reg [1:0] ts_q;         // tau position (nout - 1) -> cell, slot
    // ---------------------------------------------------------------- phases
    localparam [3:0] P_IDLE = 4'd0, P_INS = 4'd1, P_DRAIN = 4'd2, P_CONV1 = 4'd3, P_CLR2 = 4'd4, P_INS2 = 4'd5,
                     P_DRAIN2 = 4'd6, P_OUT = 4'd7, P_FLUSH = 4'd8, P_CLR0 = 4'd9;
    reg [3:0] ph;

    // ---------------------------------------------------------------- delivery credits + decode + FIFO
    wire [DEL-1:0] rr_dummy;
    wire [2:0] rr;
    // three relay copies (main control / lane take+epoch / small flight+count state): the measured single relay
    // output drove 2,686 loads (955 flops); each region now has its own registered copy
    ot_rst_relay #(.REGIONS(3),.SYNC_STAGES(2),.TREE_STAGES(1))u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
    wire rn=rr[0],rn_l=rr[1],rn_s=rr[2];
    reg[3:0]pack_queued_pin;reg[9:0]pack_lines_pin;
    reg pack_empty_pin,pack_tail,w_v_pin;reg[DEL*8-1:0]occ_pin;
    reg[DEL-1:0]early0_pin,early1_pin,landing_pin,fault_pin;
    always @(posedge clk)begin pack_queued_pin<=pack_queued;pack_lines_pin<=pack_lines;pack_empty_pin<=pack_empty;
     w_v_pin<=w_v;occ_pin<=lane_occ;early0_pin<=lane_d0v;early1_pin<=lane_d1v;landing_pin<=lane_ldv;fault_pin<=lane_fault;end
    always @(posedge clk or negedge rn_s)if(!rn_s)pack_tail<=0;else pack_tail<=pack_cell_v;
    reg[DEL-1:0]count_v;reg[DEL*8-1:0]count_mask;
    always @(posedge clk or negedge rn_s)if(!rn_s)count_v<=0;else count_v<=lane_dv;
    always @(posedge clk)count_mask<=lane_nv_mask;
    wire [DEL-1:0] d2_v=count_v,d0_v=early0_pin,d1_v=early1_pin;
    wire [DEL-1:0] ld_v=landing_pin;
    wire [7:0]occ[0:DEL-1];
    wire [679:0]st_e[0:DEL-1][0:2];
    wire [7:0]st_m[0:DEL-1][0:2],dn[0:DEL-1];
    wire [1:0]st_n[0:DEL-1];
    assign lane_tau=tau;
    assign lane_g=g_q;assign lane_gb=gb_q;assign lane_pf=pf_q;
    wire[10879:0]lane_heads={lane_heads3,lane_heads2,lane_heads1,lane_heads0};
    wire[127:0]lane_masks={lane_masks3,lane_masks2,lane_masks1,lane_masks0};
    wire[31:0]lane_epochs={lane_epoch3,lane_epoch2,lane_epoch1,lane_epoch0};
    wire[11:0]lane_hn={lane_hn3,lane_hn2,lane_hn1,lane_hn0};
    // Four head mirrors cover the registered command round trip without reusing a stale mask.
    reg[DEL*2720-1:0]head_pin;reg[DEL*32-1:0]mask_pin;
    reg[DEL*8-1:0]epoch_pin;reg[DEL*3-1:0]hn_pin;
    reg[7:0]consume_epoch[0:DEL-1],consume_mask[0:DEL-1];
    wire ins_live = (ph == P_INS); reg [DEL-1:0] sel_pop;
    always @(posedge clk)begin head_pin<=lane_heads;mask_pin<=lane_masks;epoch_pin<=lane_epochs;hn_pin<=lane_hn;end
    // Mirror selection is REGISTERED (structural repair of the measured 23-level consume_epoch -> e1 stage and the
    // 5,074-load subtract nets): the offset consume_epoch - epoch_pin that the old code subtracted after the edge is
    // formed before it from the next-state values (consume_epoch + pop, lane_epochs = next epoch_pin, lane_hn =
    // next hn_pin) and stored one-hot, one private copy per 85-bit element / mask, so the cycle behaviour is
    // identical (offset_reg(t) == consume_epoch(t) - epoch_pin(t)) and no subtract or shared select fans out.
    // During reset ins_live is 0 and consume_epoch is 0, so the stored offset is 0 - epoch, as before.
    for(genvar l=0;l<DEL;l=l+1)begin:g_lane_faces
     wire[7:0]d0=consume_epoch[l]-lane_epochs[8*l+:8];
     wire[7:0]d1=consume_epoch[l]+8'd1-lane_epochs[8*l+:8];
     wire take_pop=ins_live&&sel_pop[l];
     wire[3:0]oh0={d0==8'd3,d0==8'd2,d0==8'd1,d0==8'd0},oh1={d1==8'd3,d1==8'd2,d1==8'd1,d1==8'd0};
     wire hv0=d0<8'(lane_hn[3*l+:3]),hv1=d1<8'(lane_hn[3*l+:3]);
     (* keep *)reg[3:0]oh_e[0:7];(* keep *)reg[3:0]oh_m;(* keep *)reg hv;
     always @(posedge clk)begin
      for(integer i=0;i<8;i=i+1)oh_e[i]<=take_pop?oh1:oh0;
      oh_m<=take_pop?oh1:oh0;hv<=take_pop?hv1:hv0;
     end
     for(genvar i=0;i<8;i=i+1)begin:g_el
      assign st_e[l][0][85*i+:85]=({85{oh_e[i][0]}}&head_pin[2720*l+85*i+:85])|({85{oh_e[i][1]}}&head_pin[2720*l+680+85*i+:85])
                                 |({85{oh_e[i][2]}}&head_pin[2720*l+1360+85*i+:85])|({85{oh_e[i][3]}}&head_pin[2720*l+2040+85*i+:85]);
     end
     assign st_e[l][1]='0;assign st_e[l][2]='0;
     assign st_m[l][0]=({8{oh_m[0]}}&mask_pin[32*l+:8])|({8{oh_m[1]}}&mask_pin[32*l+8+:8])
                      |({8{oh_m[2]}}&mask_pin[32*l+16+:8])|({8{oh_m[3]}}&mask_pin[32*l+24+:8]);
     assign st_m[l][1]='0;assign st_m[l][2]='0;
     assign dn[l]=consume_mask[l];assign occ[l]=occ_pin[8*l+:8];
     assign st_n[l]=hv?2'd1:2'd0;
    end
    always @(posedge clk or negedge rn_l)begin
     if(!rn_l)begin
      lane_take<=0;lane_pop<=0;lane_take_epochs<=0;
      for(integer l=0;l<DEL;l=l+1)begin consume_epoch[l]<=0;consume_mask[l]<=0;end
     end else begin
      lane_pop<=ins_live?sel_pop:'0;
      for(integer l=0;l<DEL;l=l+1)begin
       lane_take[8*l+:8]<=ins_live?sel_take[l]:8'd0;
       lane_take_epochs[8*l+:8]<=consume_epoch[l];
       if(ins_live)begin
        if(sel_pop[l])begin consume_epoch[l]<=consume_epoch[l]+1'b1;consume_mask[l]<=0;end
        else consume_mask[l]<=(MUT==5)?8'd0:(consume_mask[l]|sel_take[l]);
       end
      end
     end
    end
    reg start_p; reg [11:0] cfg_n_p; reg [12:0] cfg_k_p, cfg_nout_p; reg [7:0] cfg_g_p, cfg_gbase_p; reg [15:0] cfg_pf_p;
    reg [39:0] cfg_obase_p, cfg_rbase_p; reg cfg_has_r_p;
    always @(posedge clk) begin
        cfg_n_p <= cfg_n; cfg_k_p <= cfg_k; cfg_nout_p <= cfg_nout; cfg_g_p <= cfg_g; cfg_gbase_p <= cfg_gbase; cfg_pf_p <= cfg_pf;
        cfg_obase_p <= cfg_obase; cfg_rbase_p <= cfg_rbase; cfg_has_r_p <= cfg_has_r;
    end
    reg [23:0] rcv;                            // flits received (decoded)
    reg [18:0] nel;                            // valid (non-pad) elements received
    reg [12:0] k_q;
    // ---------------------------------------------------------------- tau
    reg [KW-1:0] tau;
    // ---------------------------------------------------------------- staging (3 a lane) + select
    // entry pipeline
    reg          e1_v; reg [EW-1:0] e1 [0:3];
    reg          e2_v; reg [EW-1:0] e2 [0:3]; reg [5:0] e2_ge;   // pairwise compares for the rank sort
    // ---------------------------------------------------------------- the chain of hardened tiles (el1011-hbm-idx rebuild)
    // textbook audit (owner 10-11): the flat 2,048 x 85-b array (one clock root over 1,800 um, one entry bus to every
    // cell, 8,192 key compares in one edge) is now NT tiles of PT positions (ot_hgi_coll_tkm_tile, ~12k flops, own clock
    // tree): a tile keeps its best PT of what reached it and passes its bottom 4 down on a registered seam; an upward
    // conveyor (one presented-top register a seam) empties the chain from the top.  Two passes: value key, top nout ->
    // an SRAM cell buffer, chain cleared, id key, conveyed out as O / R lines.  Control reaches every tile at equal depth.
    localparam integer PT = (KMAX < 64) ? KMAX : 64;
    localparam integer NT = KMAX / PT;
    localparam integer NG2 = (NT + 3) / 4;
    localparam integer TW = 6, LW = 7;
    localparam integer BD = KMAX / 4;
    localparam integer BA = (BD <= 2) ? 1 : $clog2(BD);
    reg  [TW-1:0] tau_t; reg [LW-1:0] tau_l;
    reg  ctl_conv, ctl_clr;
    reg  [NG2-1:0] g_conv, g_clr; reg [TW-1:0] g_tt [0:NG2-1]; reg [LW-1:0] g_tl [0:NG2-1];
    reg  dconv1, dconv2, dconv3;
    reg  eb_v; reg [4*EW-1:0] eb;
    wire [4*EW-1:0] t_ovf [0:NT]; wire t_ovf_v [0:NT]; wire [4*EW-1:0] t_up [0:NT];
    wire [KW:0] t_tau [0:NT-1]; wire t_busy [0:NT-1];
    assign t_ovf[0] = eb; assign t_ovf_v[0] = eb_v; assign t_up[NT] = '0;
    assign chain_entry = eb;
    assign chain_valid = eb_v;
    assign t_up[0] = chain_up;
    for (genvar t = 0; t < NT; t = t + 1) begin : g_face
        assign chain_clr[t] = g_clr[t / 4];
        assign chain_conv[t] = g_conv[t / 4];
        assign chain_tt[6*t +: 6] = g_tt[t / 4];
        assign chain_tl[7*t +: 7] = g_tl[t / 4];
        assign t_tau[t] = chain_tau[84*t +: 84];
        assign t_busy[t] = chain_busy[t];
    end
    reg [NG2-1:0] gb_busy; reg [KW:0] g_tau [0:NG2-1]; reg any_busy; reg [KW:0] tau_b;
    always @(posedge clk) begin : trees
        reg [KW:0] o_; reg b_;
        for (integer g = 0; g < NG2; g = g + 1) begin
            g_conv[g] <= ctl_conv; g_clr[g] <= ctl_clr; g_tt[g] <= tau_t; g_tl[g] <= tau_l;
            o_ = '0; b_ = 1'b0;
            for (integer x = 0; x < 4; x = x + 1) if (g * 4 + x < NT) begin o_ = o_ | t_tau[g * 4 + x]; b_ = b_ | t_busy[g * 4 + x]; end
            g_tau[g] <= o_; gb_busy[g] <= b_;
        end
        o_ = '0; for (integer g = 0; g < NG2; g = g + 1) o_ = o_ | g_tau[g];
        tau_b <= o_; any_busy <= |gb_busy;
        dconv1 <= ctl_conv; dconv2 <= dconv1; dconv3 <= dconv2;   // r3: the tiles shift 3 edges after ctl_conv: capture t_up[0] then
    end
    // the SRAM cell buffer (pass 1 -> pass 2): BD cells of 4 elements, registered write port, captured read
    reg  bw_v; reg [BA-1:0] bw_a; reg [4*EW-1:0] bw_d;
    reg  br_v; reg [BA-1:0] br_a; reg br_q, rd2_v; reg [4*EW-1:0] rd2;
    assign buf_w_v=bw_v;assign buf_w_addr=10'(bw_a);assign buf_w_data=bw_d;
    assign buf_r_v=br_v;assign buf_r_addr=10'(br_a);
    reg[3:0]br_flight;
    always @(posedge clk or negedge rn_s)if(!rn_s)br_flight<=0;else br_flight<={br_flight[2:0],br_v};
    always @(posedge clk)rd2<=buf_rd_data;
    reg [BA:0] cnv, cap, rdn; reg [12:0] cneed; reg [3:0] qcnt; reg [3:0] wcnt;
    integer c, s, a, b, l, i;
    assign pack_nout=nout_q;assign pack_obase=ob_q;assign pack_rbase=rb_q;assign pack_has_r=hr_q;
    // Account for every issued line until the separate packer publishes its count.
    // The returned queued count can lag safely: line debt includes all pending cells.
    wire [10:0] lines_iss = 11'((cnv + 1 + 3) >> 2);
    wire [11:0] lq_need = 12'(pack_queued_pin) + 12'(lines_iss - 11'(pack_lines_pin)) * (hr_q ? 12'd2 : 12'd1);
    wire pgo = (ph == P_OUT) && (13'(cnv) < cneed) && (lq_need <= 12'd8);
    // select (combinational over the registered staging heads)
    reg [EW-1:0] sel_e [0:3]; reg [2:0] sel_n; reg [7:0] sel_take [0:DEL-1];
    function automatic[3:0]pop8(input[7:0]m);
        reg[1:0]a,b,c,d;reg[2:0]ab,cd;
        begin a=2'(m[0])+2'(m[1]);b=2'(m[2])+2'(m[3]);c=2'(m[4])+2'(m[5]);d=2'(m[6])+2'(m[7]);
         ab=3'(a)+3'(b);cd=3'(c)+3'(d);pop8=4'(ab)+4'(cd);end
    endfunction
    always @* begin : selc
        reg[7:0]available[0:DEL-1];reg[3:0]counts[0:DEL-1];reg[5:0]prefix[0:DEL-1];reg[5:0]rank_,total;
        for(integer l_=0;l_<DEL;l_=l_+1)begin
         available[l_]=(st_n[l_]!=0)?(st_m[l_][0]&~dn[l_]):8'd0;
         counts[l_]=pop8(available[l_]);
        end
        // DEL=4 fixed production shape: balanced, independent lane/slot prefixes.
        prefix[0]=0;prefix[1]=6'(counts[0]);prefix[2]=6'(counts[0])+6'(counts[1]);
        prefix[3]=(6'(counts[0])+6'(counts[1]))+6'(counts[2]);
        total=(6'(counts[0])+6'(counts[1]))+(6'(counts[2])+6'(counts[3]));
        for(integer s_=0;s_<4;s_=s_+1)sel_e[s_]='0;
        for(integer l_=0;l_<DEL;l_=l_+1)begin
         sel_take[l_]=0;
         for(integer i_=0;i_<8;i_=i_+1)begin
          rank_=prefix[l_]+6'(pop8(available[l_]&8'((9'd1<<i_)-1)));
          sel_take[l_][i_]=available[l_][i_]&&(rank_<4);
          for(integer s_=0;s_<4;s_=s_+1)
           if(available[l_][i_]&&rank_==s_&&!(MUT==2&&s_==3))sel_e[s_]=sel_e[s_]|st_e[l_][0][85*i_+:85];
         end
         sel_pop[l_]=(st_n[l_]!=0)&&((available[l_]&~sel_take[l_])==0);
        end
        sel_n=(total>4)?3'd4:3'(total);
    end
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            begin busy_q <= 0; busy <= 0; end lane_live<=0;ph <= P_IDLE; fault <= 1'b0; done <= 1'b0; pack_start<=0;pack_cell_v<=0;pack_cell<=0;pack_slot<=0;pack_last<=0;
            begin st_cyc <= 32'd0; stat_cycles <= 32'd0; end begin st_ins <= 32'd0; stat_ins <= 32'd0; end begin st_surv <= 32'd0; stat_surv <= 32'd0; end
            n_q <= 12'd1; k_q <= 13'd1; nel <= 19'd0; g_q <= 8'd1; gb_q <= 8'd0; pf_q <= 16'd1; nout_q <= 13'd1; ob_q <= 40'd0; rb_q <= 40'd0; hr_q <= 1'b0;
            tot_q <= 24'd0; cact_q <= '0; tc_q <= '0; ts_q <= 2'd0; rcv <= 24'd0; tau <= '0;
            start_p<=0;e1_v<=0;e2_v<=0;
            ctl_conv <= 1'b0; ctl_clr <= 1'b0; eb_v <= 1'b0; bw_v <= 1'b0; br_v <= 1'b0; br_q <= 1'b0; rd2_v <= 1'b0;
            cnv <= '0; cap <= '0; rdn <= '0; cneed <= 13'd0; qcnt <= 4'd0; wcnt <= 4'd0; tau_t <= '0; tau_l <= '0;
        end else begin
            done <= 1'b0;pack_start<=0;pack_cell_v<=0;
            if (busy_q) begin st_cyc <= st_cyc + 32'd1; stat_cycles <= st_cyc + 32'd1; end
            start_p <= start;
            tot_q <= 24'(g_q) * 24'(pf_q);           // from the registered configuration (no input -> logic paths)
            cact_q <= CB'((nout_q + 13'd3) >> 2);
            tc_q <= CB'((nout_q - 13'd1) >> 2); ts_q <= 2'(nout_q - 13'd1);
            tau_t <= TW'((nout_q - 13'd1) / PT); tau_l <= LW'((nout_q - 13'd1) % PT);
            cneed <= (nout_q + 13'd3) >> 2;
            for(l=0;l<DEL;l=l+1)if(fault_pin[l])fault<=1'b1;
            if(ph==P_INS)begin:cnt
                reg[3:0]n_[0:DEL-1];reg[4:0]pair0,pair1;
                for(integer l=0;l<DEL;l=l+1)begin
                    n_[l]=4'(count_mask[8*l])+4'(count_mask[8*l+1])+4'(count_mask[8*l+2])+4'(count_mask[8*l+3])+
                          4'(count_mask[8*l+4])+4'(count_mask[8*l+5])+4'(count_mask[8*l+6])+4'(count_mask[8*l+7]);
                    if(!count_v[l])n_[l]=0;
                end
                pair0=5'(n_[0])+5'(n_[1]);pair1=5'(n_[2])+5'(n_[3]);
                nel<=nel+19'(pair0)+19'(pair1);
            end
            if (ph == P_INS) rcv <= rcv + 24'(d2_v[0]) + 24'(d2_v[1]) + 24'(d2_v[2]) + 24'(d2_v[3]);
            if ((rcv + 24'(d2_v[0]) + 24'(d2_v[1]) + 24'(d2_v[2]) + 24'(d2_v[3])) > tot_q && ph == P_INS) fault <= 1'b1;
            // ---- tau (2 edges behind the array)
            tau <= vkey(tinv({tau_b, 1'b0}));
            // ---- entry: select -> e1 -> (compares) e2 -> rank-sorted block -> broadcast insertion
            // (re-insertion: the top cell, tagged region 1 -- the id order)
            e1_v <= (ins_live && (sel_n != 3'd0)) || rd2_v;
            for (s = 0; s < 4; s = s + 1) e1[s] <= rd2_v ? rd2[EW*s +: EW] : sel_e[s];
            if (ins_live && sel_n != 3'd0) begin st_surv <= st_surv + 32'(sel_n); stat_surv <= st_surv + 32'(sel_n); end
            e2_v <= e1_v;
            for (s = 0; s < 4; s = s + 1) e2[s] <= e1[s];
            e2_ge[0] <= key2(e1[0]) >= key2(e1[1]); e2_ge[1] <= key2(e1[0]) >= key2(e1[2]); e2_ge[2] <= key2(e1[0]) >= key2(e1[3]);
            e2_ge[3] <= key2(e1[1]) >= key2(e1[2]); e2_ge[4] <= key2(e1[1]) >= key2(e1[3]); e2_ge[5] <= key2(e1[2]) >= key2(e1[3]);
            // ---- the array (X / bk: reset-free data flops in their own block below)
            begin : entry
                reg [1:0] r0, r1, r2, r3;
                r0 = 2'(!e2_ge[0]) + 2'(!e2_ge[1]) + 2'(!e2_ge[2]);
                r1 = 2'(e2_ge[0]) + 2'(!e2_ge[3]) + 2'(!e2_ge[4]);
                r2 = 2'(e2_ge[1]) + 2'(e2_ge[3]) + 2'(!e2_ge[5]);
                r3 = 2'(e2_ge[2]) + 2'(e2_ge[4]) + 2'(e2_ge[5]);
                eb_v <= e2_v;
                for (s = 0; s < 4; s = s + 1)
                    eb[EW*s +: EW] <= tform(((r0 == 2'(s)) ? e2[0] : {EW{1'b0}}) | ((r1 == 2'(s)) ? e2[1] : {EW{1'b0}}) |
                                            ((r2 == 2'(s)) ? e2[2] : {EW{1'b0}}) | ((r3 == 2'(s)) ? e2[3] : {EW{1'b0}}));
                if (e2_v && (ph == P_INS || ph == P_DRAIN)) begin st_ins <= st_ins + 32'd1; stat_ins <= st_ins + 32'd1; end
            end
            // ---- the chain controls (one-edge pulses / levels; the tiles act 2 edges later)
            ctl_clr <= 1'b0; bw_v <= 1'b0;
            ctl_conv <= ((ph == P_CONV1) && (13'(cnv) < cneed)) || pgo;
            if (((ph == P_CONV1) && (13'(cnv) < cneed)) || pgo) cnv <= cnv + 1'b1;
            qcnt <= (!e1_v && !e2_v && !eb_v && !any_busy && !br_v && !(|br_flight) && !buf_rd_v && !rd2_v) ? ((qcnt == 4'd15) ? qcnt : qcnt + 4'd1) : 4'd0;
            // pass-1 capture: the top cell leaving the chain -> the buffer, id order tag (region 1), positions >= nout dropped
            if (ph == P_CONV1 && dconv3) begin
                for (s = 0; s < 4; s = s + 1) begin : c1
                    reg [EW-1:0] e_;
                    e_ = tinv(t_up[0][EW*s +: EW]);
                    bw_d[EW*s +: EW] <= (13'({cap, 2'(s)}) < nout_q) ? (e_ | {e_[83], {(EW-1){1'b0}}}) : {EW{1'b0}};
                end
                bw_v <= 1'b1; bw_a <= BA'(cap); cap <= cap + 1'b1;
            end
            // pass-2 feed: buffer cells read one an edge, captured, then into the entry sorter
            br_v <= (ph == P_INS2) && (13'(rdn) < cneed);
            if ((ph == P_INS2) && (13'(rdn) < cneed)) begin br_a <= BA'(rdn); rdn <= rdn + 1'b1; end
            br_q <= br_v; rd2_v <= buf_rd_v;
            if(ph==P_OUT&&dconv3)begin
                pack_cell_v<=1;pack_cell<=t_up[0];pack_slot<=cap[1:0];pack_last<=(13'(cap)+13'd1==cneed);
                cap<=cap+1'b1;
            end
            // ---- phase control
            case (ph)
                P_IDLE: if (start_p) begin
                    begin busy_q <= 1; busy <= 1; end
                    n_q <= cfg_n_p; k_q <= cfg_k_p; nel <= 19'd0; g_q <= cfg_g_p; gb_q <= cfg_gbase_p; pf_q <= cfg_pf_p; nout_q <= cfg_nout_p;
                    ob_q <= cfg_obase_p; rb_q <= cfg_rbase_p; hr_q <= cfg_has_r_p;
                    rcv <= 24'd0; tau <= '0;
                    begin st_ins <= 32'd0; stat_ins <= 32'd0; end begin st_surv <= 32'd0; stat_surv <= 32'd0; end begin st_cyc <= 32'd0; stat_cycles <= 32'd0; end
                    pack_start<=1;
                    ctl_clr <= 1'b1; wcnt <= 4'd0;
                    ph <= P_CLR0;
                end
                // the chain clears 2 edges after ctl_clr; the tau tree settles 3 more
                P_CLR0: begin wcnt <= wcnt + 4'd1; tau <= '0; if (wcnt == 4'd7)begin ph <= P_INS;lane_live<=1;end end
                P_INS: if (rcv == tot_q && d0_v == '0 && d1_v == '0 && d2_v == '0 && lane_dv == '0 && occ[0] == 8'd0 && occ[1] == 8'd0 && occ[2] == 8'd0 && occ[3] == 8'd0 && ld_v == '0 &&
                           st_n[0] == 2'd0 && st_n[1] == 2'd0 && st_n[2] == 2'd0 && st_n[3] == 2'd0)
                    begin ph <= P_DRAIN;lane_live<=0;end
                P_DRAIN: if (qcnt >= 4'd4) begin
                    // O.n must be min(k, the group's elements): a record whose O.n disagrees faults (E_RANGE)
                    if (19'(nout_q) != ((19'(k_q) < nel) ? 19'(k_q) : nel)) fault <= 1'b1;
                    cnv <= '0; cap <= '0;
                    ph <= (MUT == 4) ? P_OUT : P_CONV1;
                end
                P_CONV1: if (13'(cap) == cneed) begin ctl_clr <= 1'b1; wcnt <= 4'd0; ph <= P_CLR2; end
                P_CLR2: begin wcnt <= wcnt + 4'd1; if (wcnt == 4'd4) begin rdn <= '0; ph <= P_INS2; end end
                P_INS2: if (13'(rdn) == cneed) ph <= P_DRAIN2;
                P_DRAIN2: if (qcnt >= 4'd4) begin cnv <= '0; cap <= '0; ph <= P_OUT; end
                P_OUT: if (13'(cap) == cneed && pack_empty_pin && !pack_cell_v && !pack_tail && !dconv1 && !dconv2 && !dconv3) ph <= P_FLUSH;
                P_FLUSH: if (!w_v_pin) begin ph <= P_IDLE;begin busy_q <= 0; busy <= 0; end done <= 1'b1; end
                default:begin ph <= P_IDLE;begin busy_q <= 0; busy <= 0; end lane_live<=0;end
            endcase
        end
    end
endmodule
