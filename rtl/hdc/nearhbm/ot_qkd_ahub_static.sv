`timescale 1ns/1ps
// Selected TP8 six-root profile of ot_qkd_ahub_die. Actual ot_nhb_zh and
// ot_qkh_recip_leaf arithmetic is unchanged. PBST/PVLG are absent: native
// PV256/finalize is a separate real producer/consumer, not this legacy path.
// Ages are edges after the external start sample. The compiler supplies all
// producer and publication edges; checks never postpone an operation.
module qkd_ahub_static_core #(
    parameter [63:0] LMAX_IN_AGE=0,
    parameter [63:0] Z_IN_AGE=0,
    parameter integer Z_IN_STRIDE=16,
    parameter integer LMAX_ISSUE_AGE=0,
    parameter integer Z_START_AGE=0,
    parameter integer Z_LEVEL_GAP=10,
    parameter integer RECIP_ISSUE_AGE=0,
    parameter integer RECIP_RETURN_AGE=0,
    parameter integer RZ_PUBLISH_AGE=0
)(
    input wire clk,rst_n,start,active_layer_parity,
    input wire [15:0] request_epoch,input wire [5:0] active_layer,
    input wire [13:0] T,
    input wire [3:0] si_valid,si_g,si_any,input wire [63:0] si_epoch,input wire [23:0] si_layer,
    input wire [7:0] si_type,si_hh,
    input wire [15:0] si_k,
    input wire [127:0] si_data,
    output reg [143:0] am,
    output reg [3:0] zh_start,
    output reg [511:0] zh_we,zh_sid,
    output reg [15:0] zh_iv,
    output reg [3:0] zh_g,
    output reg [23:0] zh_p,
    input wire [255:0] zh_root,
    input wire [15:0] zh_err,
    output reg rc_v,
    output reg [31:0] rc_x,
    input wire [31:0] rc_y,
    input wire rc_vo,rc_fault,
    output reg rz_valid,
    output reg [1:0] rz_head,
    output reg [31:0] rz_data,
    output reg [15:0] rz_epoch,output reg rz_publish,
    output wire [127:0] rz4,
    output reg fault
);
    wire [3:0] rn;
    ot_rst_pipe #(.REGIONS(4),.STAGES(2)) u_rr (.clk(clk),.rst_n_in(rst_n),.rst_n(rn));
    reg active,parity;reg [15:0] epoch;reg [5:0] layer;
    reg [15:0] age;
    wire [16:0] edge_age={1'b0,age}+17'd1;
    integer st,h,j,lev,base,np,burst;
    reg [3:0] lm_slot,z_slot,done_slot;
    reg [7:0] slot_h;
    reg [15:0] slot_k;
    always @* begin
        lm_slot=0;z_slot=0;done_slot=0;slot_h=0;slot_k=0;
        for(integer s=0;s<4;s=s+1)begin
            if(active && edge_age>=LMAX_IN_AGE[16*s+:16] && edge_age<LMAX_IN_AGE[16*s+:16]+4)begin
                lm_slot[s]=1;slot_h[2*s+:2]=2'(edge_age-LMAX_IN_AGE[16*s+:16]);
            end
            if(active && edge_age>=Z_IN_AGE[16*s+:16] && edge_age<Z_IN_AGE[16*s+:16]+16*Z_IN_STRIDE)begin
                if((edge_age-Z_IN_AGE[16*s+:16])%Z_IN_STRIDE<4)begin
                    z_slot[s]=1;slot_h[2*s+:2]=2'((edge_age-Z_IN_AGE[16*s+:16])%Z_IN_STRIDE);
                    slot_k[4*s+:4]=4'((edge_age-Z_IN_AGE[16*s+:16])/Z_IN_STRIDE);
                end
            end
            done_slot[s]=active && edge_age==Z_IN_AGE[16*s+:16]+16*Z_IN_STRIDE;
        end
    end
    reg [3:0] lm_b,z_b,any_b;
    reg [7:0] hh_b;
    reg [15:0] k_b;
    reg [127:0] data_b;
    reg start_b;
    always @(posedge clk or negedge rn[0])
        if(!rn[0])begin active<=0;age<=0;epoch<=0;parity<=0;layer<=0;start_b<=0;lm_b<=0;z_b<=0;end
        else begin
            start_b<=start;lm_b<=lm_slot;z_b<=z_slot;
            if(start)begin active<=1;age<=0;epoch<=request_epoch;parity<=active_layer_parity;layer<=active_layer;lm_b<=0;z_b<=0;end
            else if(active && age!=16'hffff)age<=age+1'b1;
        end
    always @(posedge clk)begin any_b<=si_any;hh_b<=slot_h;k_b<=slot_k;data_b<=si_data;end
    reg [31:0] lm[0:15];
    reg [15:0] lany;
    reg [127:0] zseen[0:3];
    reg [15:0] lm_seen;
    reg [3:0] done_seen;
    always @(posedge clk or negedge rn[1])
        if(!rn[1])begin lany<=0;lm_seen<=0;done_seen<=0;for(integer a=0;a<4;a=a+1)zseen[a]<=0;end
        else if(start_b)begin lany<=0;lm_seen<=0;done_seen<=0;for(integer a=0;a<4;a=a+1)zseen[a]<=0;end
        else begin
            for(integer a=0;a<4;a=a+1)begin
                if(lm_b[a])begin lany[4*a+hh_b[2*a+:2]]<=any_b[a];lm_seen[4*a+hh_b[2*a+:2]]<=1;end
                if(done_slot[a])done_seen[a]<=1;
                if(z_b[a])zseen[hh_b[2*a+:2]][{1'b0,k_b[4*a+:4],2'(a)}]<=1;
            end
        end
    always @(posedge clk)for(integer a=0;a<4;a=a+1)if(lm_b[a])lm[4*a+hh_b[2*a+:2]]<=data_b[32*a+:32];
    always @(posedge clk or negedge rn[0])if(!rn[0])zh_start<=0;else zh_start<={4{start_b}};
    always @(posedge clk)begin
        zh_we<=0;zh_sid<={4{data_b}};
        for(integer a=0;a<4;a=a+1)if(z_b[a])zh_we[128*hh_b[2*a+:2]+{1'b0,k_b[4*a+:4],2'(a)}]<=1;
    end
    function automatic fgt(input [31:0] a,input [31:0] b);
        fgt=(a[31]!=b[31])?!a[31]:(!a[31]?(a[30:0]>b[30:0]):(a[30:0]<b[30:0]));
    endfunction
    function automatic [32:0] fmax2(input [31:0] x,input ax,input [31:0] y,input ay);
        fmax2=!ax?{ay,y}:(!ay?{1'b1,x}:{1'b1,(fgt(y,x)?y:x)});
    endfunction
    wire m_issue=active && edge_age>=LMAX_ISSUE_AGE && edge_age<LMAX_ISSUE_AGE+4;
    wire [1:0] mh=2'(edge_age-LMAX_ISSUE_AGE);
    reg ma_v,mb_v,mo_v;
    reg [1:0] ma_h,mb_h,mo_h;
    reg [127:0] ma_x;
    reg [3:0] ma_a;
    reg [63:0] mb_x;
    reg [1:0] mb_a;
    reg [31:0] mo_data;
    wire [32:0] m01=fmax2(ma_x[31:0],ma_a[0],ma_x[63:32],ma_a[1]);
    wire [32:0] m23=fmax2(ma_x[95:64],ma_a[2],ma_x[127:96],ma_a[3]);
    wire [32:0] mfin=fmax2(mb_x[31:0],mb_a[0],mb_x[63:32],mb_a[1]);
    always @(posedge clk or negedge rn[1])
        if(!rn[1])begin ma_v<=0;mb_v<=0;mo_v<=0;for(integer a=0;a<4;a=a+1)am[36*a+35]<=0;end
        else begin ma_v<=m_issue&&!start;mb_v<=ma_v&&!start;mo_v<=mb_v&&!start;
            for(integer a=0;a<4;a=a+1)am[36*a+35]<=mo_v&&!start;end
    always @(posedge clk)begin
        ma_h<=mh;mb_h<=ma_h;mo_h<=mb_h;
        for(integer a=0;a<4;a=a+1)begin ma_x[32*a+:32]<=lm[4*a+mh];ma_a[a]<=lany[4*a+mh];end
        mb_x<={m23[31:0],m01[31:0]};mb_a<={m23[32],m01[32]};mo_data<=mfin[31:0];
        for(integer a=0;a<4;a=a+1)am[36*a+:35]<={1'b0,mo_h,mo_data};
    end
    // Same six levels, pair order, four lanes, and fixed drain as qkd_ahub_core.
    // Unroll level offsets at elaboration; no completion/count/ready drives issue.
    reg [3:0] issue;
    reg [5:0] pair_base;
    always @*begin
        issue=0;pair_base=0;base=Z_START_AGE;
        for(integer l=1;l<=6;l=l+1)begin
            np=64>>l;burst=(np+3)/4;
            if(active && edge_age>=base && edge_age<base+burst)begin
                pair_base=6'((edge_age-base)*4);
                for(integer a=0;a<4;a=a+1)issue[a]=((edge_age-base)*4+a)<np;
            end
            base=base+burst+Z_LEVEL_GAP;
        end
    end
    always @(posedge clk or negedge rn[2])if(!rn[2])zh_iv<=0;else zh_iv<=start?16'd0:{4{issue}};
    always @(posedge clk)begin zh_g<=0;zh_p<={4{pair_base}};end
    reg [255:0] zroot_q;
    always @(posedge clk)zroot_q<=zh_root;
    wire recip_issue=active && edge_age>=RECIP_ISSUE_AGE && edge_age<RECIP_ISSUE_AGE+4;
    wire recip_return=active && edge_age>=RECIP_RETURN_AGE && edge_age<RECIP_RETURN_AGE+4;
    wire [1:0] recip_head=2'(edge_age-RECIP_ISSUE_AGE);
    wire [1:0] return_head=2'(edge_age-RECIP_RETURN_AGE);
    reg [31:0] rz[0:3];
    reg [3:0] rz_seen;
    for(genvar a=0;a<4;a=a+1)assign rz4[32*a+:32]=rz[a];
    always @(posedge clk or negedge rn[3])
        if(!rn[3])begin rc_v<=0;rz_valid<=0;rz_publish<=0;rz_seen<=0;rz_epoch<=0;end
        else begin
            rc_v<=recip_issue&&!start;rz_valid<=recip_return&&!start;
            rz_publish<=active && edge_age==RZ_PUBLISH_AGE && !start;
            rz_epoch<=epoch;
            if(start)rz_seen<=0;else if(recip_return)rz_seen[return_head]<=1;
        end
    always @(posedge clk)begin
        rc_x<=zroot_q[64*recip_head+:32];
        rz_head<=return_head;rz_data<=rc_y;
        if(recip_return)rz[return_head]<=rc_y;
    end
    always @(posedge clk or negedge rn[3])
        if(!rn[3])fault<=0;
        else if(start)fault<=(T!=8192)||(active_layer_parity!=active_layer[0]);
        else if(active)begin
            if(active_layer_parity!=parity || active_layer!=layer || request_epoch!=epoch || |zh_err || rc_fault || (rc_vo!=recip_return) ||
                (m_issue && lm_seen!=16'hffff) ||
                ((|issue) && (done_seen!=4'hf || zseen[0][63:0]!=64'hffffffffffffffff || zseen[1][63:0]!=64'hffffffffffffffff ||
                    zseen[2][63:0]!=64'hffffffffffffffff || zseen[3][63:0]!=64'hffffffffffffffff)) ||
                (edge_age==RZ_PUBLISH_AGE && rz_seen!=4'hf))fault<=1;
            for(integer a=0;a<4;a=a+1)begin
                if(si_valid[a]!=(lm_slot[a]||z_slot[a]||done_slot[a]))fault<=1;
                if(si_valid[a] && (si_epoch[16*a+:16]!=epoch || si_layer[6*a+:6]!=layer || si_g[a] ||
                    si_type[2*a+:2]!=(lm_slot[a]?0:z_slot[a]?1:2) ||
                    ((lm_slot[a]||z_slot[a]) && si_hh[2*a+:2]!=slot_h[2*a+:2]) ||
                    (z_slot[a] && si_k[4*a+:4]!=slot_k[4*a+:4])))fault<=1;
            end
        end
    initial begin
        if(LMAX_IN_AGE==0 || Z_IN_AGE==0 || LMAX_ISSUE_AGE<1 || Z_START_AGE<1 || Z_LEVEL_GAP<10 ||
            RECIP_ISSUE_AGE<=Z_START_AGE+77 || RECIP_RETURN_AGE<=RECIP_ISSUE_AGE || RZ_PUBLISH_AGE<RECIP_RETURN_AGE+4 || Z_IN_STRIDE<4)
            $fatal(1,"unsealed/invalid static AHUB calendar");
    end
endmodule

module ot_qkd_ahub_static_die #(
    parameter [63:0] LMAX_IN_AGE=0,Z_IN_AGE=0,
    parameter integer Z_IN_STRIDE=16,LMAX_ISSUE_AGE=0,Z_START_AGE=0,Z_LEVEL_GAP=10,
    parameter integer RECIP_ISSUE_AGE=0,RECIP_RETURN_AGE=0,RZ_PUBLISH_AGE=0,
    parameter integer ZW_RLY=0,ZR_RLY=0,RX_RLY=1,RY_RLY=1
)(
    input wire ck_core,ck_recip,input wire [3:0] ck_zh,
    input wire rst_n,start,active_layer_parity,input wire [15:0] request_epoch,input wire [5:0] active_layer,input wire [13:0] T,
    input wire [3:0] si_valid,si_g,si_any,input wire [63:0] si_epoch,input wire [23:0] si_layer,input wire [7:0] si_type,si_hh,
    input wire [15:0] si_k,input wire [127:0] si_data,
    output wire [143:0] am,output wire rz_valid,output wire [1:0] rz_head,
    output wire [31:0] rz_data,output wire [15:0] rz_epoch,output wire rz_publish,
    output wire [127:0] rz_vector,output wire fault
);
    wire [3:0] zh_start,zh_g;wire [511:0] zh_we,zh_sid;wire [15:0] zh_iv,zh_err;
    wire [23:0] zh_p;wire [255:0] zh_root;
    wire rc_v,rc_vo,rc_fault;wire [31:0] rc_x,rc_y;
    qkd_ahub_static_core #(.LMAX_IN_AGE(LMAX_IN_AGE),.Z_IN_AGE(Z_IN_AGE),.Z_IN_STRIDE(Z_IN_STRIDE),
        .LMAX_ISSUE_AGE(LMAX_ISSUE_AGE),.Z_START_AGE(Z_START_AGE),.Z_LEVEL_GAP(Z_LEVEL_GAP),
        .RECIP_ISSUE_AGE(RECIP_ISSUE_AGE),.RECIP_RETURN_AGE(RECIP_RETURN_AGE),.RZ_PUBLISH_AGE(RZ_PUBLISH_AGE)) u_core (
        .clk(ck_core),.rst_n(rst_n),.start(start),.active_layer_parity(active_layer_parity),.request_epoch(request_epoch),.active_layer(active_layer),.T(T),
        .si_valid(si_valid),.si_type(si_type),.si_g(si_g),.si_hh(si_hh),.si_k(si_k),.si_any(si_any),.si_epoch(si_epoch),.si_layer(si_layer),.si_data(si_data),
        .am(am),.zh_start(zh_start),.zh_we(zh_we),.zh_sid(zh_sid),.zh_iv(zh_iv),.zh_g(zh_g),.zh_p(zh_p),.zh_root(zh_root),.zh_err(zh_err),
        .rc_v(rc_v),.rc_x(rc_x),.rc_y(rc_y),.rc_vo(rc_vo),.rc_fault(rc_fault),
        .rz_valid(rz_valid),.rz_head(rz_head),.rz_data(rz_data),.rz_epoch(rz_epoch),.rz_publish(rz_publish),.rz4(rz_vector),.fault(fault));
    for(genvar a=0;a<4;a=a+1)begin:g_zh
        wire [267:0] zi;wire [67:0] zo,zot;
        ot_qkd_drly #(.W(268),.N(ZW_RLY)) u_ri (.clk(ck_zh[a]),
            .d({zh_start[a],zh_we[128*a+:128],zh_sid[128*a+:128],zh_iv[4*a+:4],zh_g[a],zh_p[6*a+:6]}),.q(zi));
        ot_nhb_zh u_zh (.clk(ck_zh[a]),.rst_n(rst_n),.start(zi[267]),.zs_we(zi[266:139]),.sid(zi[138:11]),.ziv(zi[10:7]),.zg(zi[6]),.zp(zi[5:0]),.root(zot[63:0]),.zerr(zot[67:64]));
        ot_qkd_drly #(.W(68),.N(ZR_RLY)) u_ro (.clk(ck_core),.d(zot),.q(zo));
        assign zh_root[64*a+:64]=zo[63:0];assign zh_err[4*a+:4]=zo[67:64];
    end
    wire [32:0] rx;wire [33:0] ry,ryt;
    ot_qkd_drly #(.W(33),.N(RX_RLY)) u_rx (.clk(ck_recip),.d({rc_v,rc_x}),.q(rx));
    ot_qkh_recip_leaf u_recip (.clk(ck_recip),.rst_n(rst_n),.v(rx[32]),.x(rx[31:0]),.y(ryt[31:0]),.vo(ryt[32]),.fault(ryt[33]));
    ot_qkd_drly #(.W(34),.N(RY_RLY)) u_ry (.clk(ck_core),.d(ryt),.q(ry));
    assign rc_y=ry[31:0];assign rc_vo=ry[32];assign rc_fault=ry[33];
endmodule
