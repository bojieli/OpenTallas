`timescale 1ns/1ps
// Candidate X_IDX replacement for ot_hdc_core_v41x.  It uses four HBM3E
// replicated-image key selectors, the quarter-order kmerge, one pooled FP4
// block-dot tile and idx_pool_finish.  The interface mirrors idx_adapt except
// that HBM request and response buses have four stacks.  The key writer must
// broadcast each encoded update to all four full images.
//
// This is a correctness-rate adapter: its single G4/M2 tile back-pressures
// the 64-key kmerge beat.  Production rate needs replicated tile slices.
module ot_hdc_v41x_idx_pool_adapt #(
    parameter integer W=16, G=4, IL=8, AW=24, NW=16, MP=2,
    parameter integer IH=32, NPC=32, HAW=28, HLENW=4, HTAGW=16, HBEATW=4,
    parameter integer SHARDED=0
) (
    input wire clk, rst_n, go,
    output wire ready,
    output reg idle,
    input wire [AW-1:0] cfg_ik_base,
    input wire [NW-1:0] i_nout, i_k,
    input wire [AW-1:0] i_wbase, i_xbase, i_xks, i_xjs, i_xcs,
    input wire [1:0] i_hg,
    input wire i_round,
    input wire [AW-1:0] i_obase,
    input wire i_mmode, i_oen, i_fuse,
    input wire [AW-1:0] i_wts,
    output reg [MP*G-1:0] x_re,
    output reg [MP*G*AW-1:0] x_addr,
    input wire [MP*G*32-1:0] x_q,
    output reg ov,
    output reg [MP*G-1:0] o_we,
    output reg [MP*G*AW-1:0] o_addr,
    output reg [MP*G*W-1:0] o_mask,
    output reg [MP*G*W*32-1:0] o_data,
    output wire [4*NPC-1:0] h_req_v,
    input wire [4*NPC-1:0] h_req_rdy,
    output wire [4*NPC*HAW-1:0] h_req_addr,
    output wire [4*NPC*HLENW-1:0] h_req_len,
    output wire [4*NPC*HTAGW-1:0] h_req_tag,
    input wire [4*NPC-1:0] h_rsp_v,
    output wire [4*NPC-1:0] h_rsp_rdy,
    input wire [4*NPC*HTAGW-1:0] h_rsp_tag,
    input wire [4*NPC*HBEATW-1:0] h_rsp_beat,
    input wire [4*NPC*256-1:0] h_rsp_data,
    output reg fault,
    output reg [31:0] dbg_ops, dbg_elems,
    output wire [47:0] dbg_keys_streamed, dbg_hbm_beats,
    output reg [47:0] dbg_keys_scored, dbg_headsums_fused
);
    localparam integer QE=IH*128, HW=20;
    localparam [2:0] A_IDLE=0, A_LOAD=1, A_DRAIN=2, A_WEIGHTS=3, A_START=4, A_RUN=5;
    reg [2:0] st;
    reg [NW-1:0] n;
    reg [AW-1:0] xbase,xks,xjs,xcs,wts,wbase,obase;
    reg rnd,oen,cfg_bad,rd_bad,qbad;
    reg [12:0] qe,q1_e,q2_e;
    reg q1_v,q2_v;
    reg [15:0] qv [0:QE+IH-1];
    reg [5:0] qh;
    reg [1:0] qb;
    reg [NW-1:0] kdim;
    reg [12:0] qtotal;
    reg [2:0] drain;
    reg [NW:0] done_count;
    assign ready=st==A_IDLE;

    function automatic [15:0] bf16(input [31:0] x);
        bf16=x[31:16]+((x[15] && (x[14:0]!=0 || x[16])) ? 16'd1 : 16'd0);
    endfunction
    integer g;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin st<=A_IDLE;qe<=0;q1_v<=0;q2_v<=0;x_re<=0;qh<=0;drain<=0; end
        else begin
            x_re<=0;q1_v<=0;q2_v<=q1_v;
            case(st)
                A_IDLE: if(go) begin
                    n<=i_nout;xbase<=i_xbase;xks<=i_xks;xjs<=i_xjs;xcs<=i_xcs;
                    wts<=i_wts;wbase<=i_wbase;obase<=i_obase;rnd<=i_round;oen<=i_oen;
                    cfg_bad<=!i_fuse || (i_k!=32 && i_k!=128) || !i_mmode || ((IL<<i_hg)!=IH);
                    kdim<=i_k;qtotal<=IH*i_k+IH;
                    qe<=0;qh<=0;qb<=0;st<=A_LOAD;
                end
                A_LOAD: begin
                    x_re[G-1:0]<={G{1'b1}};q1_v<=1;
                    qe<=qe+G;
                    if(qe+G>=qtotal) begin drain<=3;st<=A_DRAIN;end
                end
                A_DRAIN: if(drain!=0) drain<=drain-1'b1; else st<=A_WEIGHTS;
                A_WEIGHTS: if(qb==((kdim>>5)-1)) begin
                    qb<=0;
                    if(qh==IH-1) st<=A_START; else qh<=qh+1'b1;
                end else qb<=qb+1'b1;
                A_START: st<=A_RUN;
                A_RUN: if(done_count>=n && !(|ks_busy) && !merge_v && !batch_busy) st<=A_IDLE;
                default: st<=A_IDLE;
            endcase
        end
    end
    always @(posedge clk) begin
        q1_e<=qe;q2_e<=q1_e;
        for(g=0;g<G;g=g+1)
            x_addr[g*AW +: AW] <= (qe+g<IH*kdim) ?
                xbase+(((qe+g)/kdim)/IL)*xcs+(((qe+g)/kdim)%IL)*xjs+((qe+g)%kdim)*xks :
                wts+qe+g-IH*kdim;
        if(q2_v)
            for(g=0;g<G;g=g+1)
                if(q2_e+g<qtotal) qv[q2_e+g]<= (rnd && q2_e+g<IH*kdim) ? bf16(x_q[32*g +: 32]) : x_q[32*g+16 +: 16];
    end
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) rd_bad<=0;
        else if(st==A_IDLE && go) rd_bad<=0;
        else if(q2_v)
            for(integer k=0;k<G;k=k+1)
                if(q2_e+k<qtotal && !(rnd && q2_e+k<IH*kdim) && x_q[32*k +: 16]!=0) rd_bad<=1;
    end

    // Convert each QDQ4 block to the pooled tile's E4M3 activation port.
    // The reduced vehicle's K=32 uses one block and pads the other three.
    function automatic [7:0] e2m1_to_e4m3(input [3:0] c);
        reg [7:0] mag;
        begin
            case(c[2:0])
                0:mag=8'h00;1:mag=8'h30;2:mag=8'h38;3:mag=8'h3c;
                4:mag=8'h40;5:mag=8'h44;6:mag=8'h48;default:mag=8'h4c;
            endcase
            e2m1_to_e4m3={c[3],mag[6:0]};
        end
    endfunction
    function automatic [136:0] enc32(input [32*16-1:0] v);
        reg [7:0] emax,e,u;
        reg [6:0] m;
        reg bad,any;
        reg [127:0] c;
        integer i,d;
        begin
            emax=0;bad=0;any=0;c=0;
            for(i=0;i<32;i=i+1) if(v[16*i +: 15]!=0) begin
                any=1;if(v[16*i+7 +: 8]>emax) emax=v[16*i+7 +: 8];
            end
            u=any ? emax-8'd2 : 8'd0;
            if(any && (emax<2 || emax>254 || u>252)) bad=1;
            for(i=0;i<32;i=i+1) begin
                e=v[16*i+7 +: 8];m=v[16*i +: 7];
                if(v[16*i +: 15]!=0) begin
                    d=e-emax+2;
                    if(e==0 || e==255 || m[5:0]!=0) bad=1;
                    case(d)
                        2:c[4*i +: 3]=m[6]?3'd7:3'd6;
                        1:c[4*i +: 3]=m[6]?3'd5:3'd4;
                        0:c[4*i +: 3]=m[6]?3'd3:3'd2;
                        -1:begin c[4*i +: 3]=3'd1;if(m[6]) bad=1;end
                        default:bad=1;
                    endcase
                    c[4*i+3]=v[16*i+15];
                end
            end
            enc32={bad,u,c};
        end
    endfunction
    reg [511:0] qrow;
    reg [136:0] qenc;
    reg [263:0] qword [0:IH*4-1];
    reg [IH*32-1:0] qscale;
    integer h,d;
    always @* begin
        for(d=0;d<32;d=d+1) qrow[16*d +: 16]=qv[qh*kdim+32*qb+d];
        qenc=enc32(qrow);
    end
    always @(posedge clk) if(st==A_WEIGHTS) begin
        for(h=0;h<32;h=h+1) qword[4*qh+qb][8*h +: 8]<=e2m1_to_e4m3(qenc[4*h +: 4]);
        qword[4*qh+qb][263:256]<=qenc[135:128];
        qscale[32*qh+8*qb +: 8]<=qenc[135:128];
        if(qenc[136]) qbad<=1;
    end
    always @(posedge clk) if(st==A_IDLE && go) qbad<=0;
    wire w_v=st==A_WEIGHTS && qb==((kdim>>5)-1);
    wire [31:0] w_qsc=kdim==32 ? {24'd0,qenc[135:128]} :
        {qenc[135:128],qscale[32*qh +: 24]};

    wire scan_cmd=st==A_START;
    wire [AW-1:0] ik_off=wbase-cfg_ik_base;
    wire [3:0] ks_busy;
    wire merge_v,merge_r;
    wire [63:0] merge_kv,merge_ref;
    wire [3:0] merge_last;
    wire [64*544-1:0] merge_key;
    wire [47:0] merge_refcnt;
    reg [47:0] keys_sum,hb_sum;
    wire shard_fault;
    generate if(SHARDED != 0) begin:g_sharded
        wire shard_busy;
        wire [47:0] shard_keys,shard_beats;
        // A per-user compact base sector must be supplied through the
        // existing weight-base offset. Full multi-user slice geometry is a
        // separate integration gate; no silent fourfold replication here.
        ot_hdc_v41x_idx_shard_reader #(.NPC(NPC),.HAW(HAW),.TAGW(HTAGW),
            .LENW(HLENW),.BEATW(HBEATW)) reader (
            .clk(clk),.rst_n(rst_n),.cmd_v(scan_cmd),
            .cmd_base_sec(HAW'((ik_off>>7)*17)),.cmd_nkeys(30'(n)),
            .busy(shard_busy),.fault(shard_fault),
            .req_v(h_req_v),.req_rdy(h_req_rdy),.req_addr(h_req_addr),
            .req_len(h_req_len),.req_tag(h_req_tag),
            .rsp_v(h_rsp_v),.rsp_rdy(h_rsp_rdy),.rsp_tag(h_rsp_tag),
            .rsp_beat(h_rsp_beat),.rsp_data(h_rsp_data),
            .o_valid(merge_v),.o_ready(merge_r),.o_kv(merge_kv),
            .o_last(merge_last),.o_key(merge_key),.o_ref(merge_ref),
            .cnt_keys_streamed(shard_keys),.cnt_hbm_beats(shard_beats),
            .cnt_refused(merge_refcnt));
        assign ks_busy={3'b000,shard_busy};
        always @* begin keys_sum=shard_keys;hb_sum=shard_beats;end
    end else begin:g_replicated
        wire [3:0] sv,sr;
        wire [4*16-1:0] skv;
        wire [4*16*544-1:0] skey;
        wire [4*48-1:0] ks_cnt,hb_cnt;
        genvar s;
        for(s=0;s<4;s=s+1) begin:g_stack
            ot_hdc_v41x_idx_pool_replica #(.S(s),.NPC(NPC),.AW(HAW),.HW(HW),
                .TAGW(HTAGW),.LENW(HLENW),.BEATW(HBEATW)) stream (
                .clk(clk),.rst_n(rst_n),.cmd_v(scan_cmd),.cmd_base((ik_off>>7)*17),
                .cmd_nkeys(n),.busy(ks_busy[s]),
                .req_v(h_req_v[s*NPC +: NPC]),.req_rdy(h_req_rdy[s*NPC +: NPC]),
                .req_addr(h_req_addr[s*NPC*HAW +: NPC*HAW]),
                .req_len(h_req_len[s*NPC*HLENW +: NPC*HLENW]),
                .req_tag(h_req_tag[s*NPC*HTAGW +: NPC*HTAGW]),
                .rsp_v(h_rsp_v[s*NPC +: NPC]),.rsp_rdy(h_rsp_rdy[s*NPC +: NPC]),
                .rsp_tag(h_rsp_tag[s*NPC*HTAGW +: NPC*HTAGW]),
                .rsp_beat(h_rsp_beat[s*NPC*HBEATW +: NPC*HBEATW]),
                .rsp_data(h_rsp_data[s*NPC*256 +: NPC*256]),
                .o_valid(sv[s]),.o_ready(sr[s]),.o_kv(skv[16*s +: 16]),
                .o_key(skey[16*544*s +: 16*544]),
                .cnt_keys_streamed(ks_cnt[48*s +: 48]),.cnt_hbm_beats(hb_cnt[48*s +: 48]));
        end
        ot_hdc_v41x_idx_kmerge #(.NS(4),.FQ(4)) merge (
            .clk(clk),.rst_n(rst_n),.cmd_v(scan_cmd),.cmd_nkeys(n),
            .i_valid(sv),.i_ready(sr),.i_kv(skv),.i_key(skey),
            .o_valid(merge_v),.o_ready(merge_r),.o_kv(merge_kv),.o_last(merge_last),
            .o_key(merge_key),.o_ref(merge_ref),.cnt_refused(merge_refcnt));
        assign shard_fault=1'b0;
        always @* begin
            keys_sum=0;hb_sum=0;
            for(integer t=0;t<4;t=t+1) begin
                keys_sum=keys_sum+ks_cnt[48*t +: 48];
                hb_sum=hb_sum+hb_cnt[48*t +: 48];
            end
        end
    end endgenerate
    assign dbg_keys_streamed=keys_sum;
    assign dbg_hbm_beats=hb_sum;

    wire [7:0] rq_v,rq_src,rq_split;
    wire [8*20-1:0] rq_a;
    wire [8*14-1:0] rq_q;
    wire [8*4-1:0] rq_plg,rq_tag;
    wire [8*16-1:0] rq_rg;
    reg [8*4*MP*264-1:0] xx[0:1];
    integer j,p,c,row,blk;
    always @(posedge clk) begin
        for(j=0;j<32;j=j+1) begin
            c=j%8;row=rq_a[20*c +: 20]*8+2*(j/8)+((j%8)>=4);blk=j%4;
            for(p=0;p<MP;p=p+1)
                xx[0][(j*MP+p)*264 +: 264]<=rq_v[c] && (kdim==128 || blk==0) ?
                    qword[4*((row%(IH/MP))*MP+p)+blk] : 264'd0;
        end
        xx[1]<=xx[0];
    end
    wire b_valid,b_write,b_fault,b_busy,b_protocol;
    wire [29:0] b_index;
    wire [15:0] b_score;
    ot_hdc_v41x_idx_pool_batch #(.G(4),.M(MP),.IH(IH),.AW(20),.RL(2)) batch (
        .clk(clk),.rst_n(rst_n),.cmd_v(scan_cmd),.cmd_nkeys(n),
        .b_valid(merge_v),.b_ready(merge_r),.b_kv(merge_kv),.b_ref(merge_ref),
        .b_keep(64'hffff_ffff_ffff_ffff),.b_key(merge_key),
        .w_v(w_v),.w_head(qh),.w_w(qv[IH*kdim+qh]),.w_qsc(w_qsc),
        .rq_v(rq_v),.rq_a(rq_a),.rq_q(rq_q),.rq_plg(rq_plg),.rq_tag(rq_tag),
        .rq_src(rq_src),.rq_split(rq_split),.rq_rg(rq_rg),.rd_x(xx[1]),
        .o_valid(b_valid),.o_write(b_write),.o_index(b_index),.o_score(b_score),
        .o_fault(b_fault),.busy(b_busy),.protocol_fault(b_protocol));
    wire batch_busy=b_busy;

    integer l;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin
            ov<=0;o_we<=0;o_addr<=0;o_mask<=0;o_data<=0;
            fault<=0;idle<=1;dbg_ops<=0;dbg_elems<=0;dbg_keys_scored<=0;dbg_headsums_fused<=0;done_count<=0;
        end else begin
            ov<=0;o_we<=0;o_addr<=0;o_mask<=0;o_data<=0;
            if(st==A_IDLE && go) begin
                dbg_ops<=dbg_ops+1;done_count<=0;
                fault<=0;
            end
            if(b_valid && b_write) begin
                ov<=1;o_we[0]<=oen;
                o_addr[0 +: AW]<=obase+b_index/W;
                for(l=0;l<W;l=l+1)
                    if(l==b_index%W) begin
                        o_mask[l]<=1;o_data[32*l +: 32]<={b_score,16'd0};
                    end
                dbg_elems<=dbg_elems+1;
                done_count<=done_count+1;
                dbg_keys_scored<=dbg_keys_scored+1;
                dbg_headsums_fused<=dbg_headsums_fused+IH;
                if(b_fault) fault<=1;
            end
            if(rd_bad || cfg_bad || qbad || b_protocol || shard_fault) fault<=1;
            idle <= (st==A_IDLE) && !go && !b_busy && !(|ks_busy) && !merge_v && !(|o_we);
        end
    end
endmodule
