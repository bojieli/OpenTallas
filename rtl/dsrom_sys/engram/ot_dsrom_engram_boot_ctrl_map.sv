`timescale 1ns/1ps
// Bridge Engram boot tagged sectors to the real dsfd_ctrl per-PC rq/wd API.
// This is a boot-exclusive controller client (decode admission is held until
// bootstrap finishes). One outstanding write per PC makes untagged wd exact;
// up to eight global writes queue while a PC is stalled. rk is intentionally
// not a completion: each PC owns eight request credits but only one is used.
// Request mapping: stack=global_atom[0], PC=global_atom[5:1],
// PC-local atom=global_atom>>6. No controller/PHY or route qualification claim.
module ot_dsrom_engram_boot_ctrl_map #(parameter integer ROWSTRIPE=0,parameter integer CANONICAL=0,parameter integer APERTURE=0,parameter integer MAX_PC_ATOMS=19775388) (
    input wire ck, rst_n,
    input wire aperture_valid,
    input wire [64*30-1:0] pc_base,pc_limit, // exclusive limit, PC-local32B atoms
    input wire [1:0] i_v,
    input wire [28:0] i_atom, // already stack-stripped
    input wire [2:0] i_tag,
    input wire [255:0] i_d,
    output wire [64*341-1:0] rq,
    input wire [63:0] wd,
    output reg [1:0] done_v,
    output reg [5:0] done_tag,
    output reg fault
);
    reg [1:0] iv_q;
    reg [28:0] ia_q;
    reg [2:0] it_q;
    reg [255:0] id_q;
    reg [63:0] wd_q;
    always @(posedge ck or negedge rst_n)
        if(!rst_n) begin iv_q<=0;wd_q<=0;end
        else begin iv_q<=i_v;wd_q<=wd;end
    always @(posedge ck) begin ia_q<=i_atom;it_q<=i_tag;id_q<=i_d;end

    reg [1:0] state [0:7]; // free, queued, sent, completion pending
    reg [5:0] pc [0:7];
    reg [29:0] atom [0:7];
    reg [255:0] data [0:7];
    reg [63:0] busy;
    reg [2:0] pc_tag [0:63];
    reg [63:0] out_v;
    reg [29:0] out_addr;
    reg [16:0] out_tag;
    reg [255:0] out_data;
    function automatic [34:0] inverse(input [4:0] p,input [30:0] a);
        reg [30:0] t;reg [4:0] bank;
        begin t=a>>2;bank=(p^t^(t>>5))&31;inverse=({4'b0,t}<<7)|({30'b0,bank}<<2)|(a&3);end
    endfunction
    reg [30:0] launch_local,launch_end;
    reg [34:0] launch_global;
    integer j, launch, ret_sw, ret_se;
    reg [5:0] incoming_pc;
    always @(*) begin
        launch=-1;ret_sw=-1;ret_se=-1;
        incoming_pc=(iv_q[1] ? 32 : 0)+(ROWSTRIPE ? ((ia_q/9)%32) : ia_q[4:0]);
        for(j=7;j>=0;j=j-1) begin
            if(state[j]==1 && !busy[pc[j]]) launch=j;
            if(state[j]==3 && !pc[j][5]) ret_sw=j;
            if(state[j]==3 && pc[j][5]) ret_se=j;
        end
        launch_local=0;launch_end=0;launch_global=0;
        if(launch>=0) begin
            launch_local={1'b0,atom[launch]}+(APERTURE ? {1'b0,pc_base[pc[launch]*30+:30]} : 31'd0);
            launch_end=launch_local+1;
            launch_global=CANONICAL ? inverse(pc[launch][4:0],launch_local) : {4'b0,launch_local};
        end
    end
    genvar p;
    generate for(p=0;p<64;p=p+1) begin:g_pc
        assign rq[p*341+:341]={out_data,32'hffffffff,out_tag,(CANONICAL ? 4'd1 : 4'd0),out_addr,1'b1,out_v[p]};
    end endgenerate
    always @(posedge ck or negedge rst_n) begin
        if(!rst_n) begin
            for(j=0;j<8;j=j+1) state[j]<=0;
            busy<=0;out_v<=0;out_addr<=0;out_tag<=0;out_data<=0;
            done_v<=0;done_tag<=0;fault<=0;
        end else begin
            out_v<=0;done_v<=0;
            for(j=0;j<64;j=j+1) if(wd_q[j]) begin
                if(!busy[j] || state[pc_tag[j]]!=2 || pc[pc_tag[j]]!=j[5:0]) fault<=1;
                else begin busy[j]<=0;state[pc_tag[j]]<=3;end
            end
            if(!fault) begin
                if(iv_q!=0) begin
                    if(iv_q==3 || state[it_q]!=0) fault<=1;
                    else begin
                        state[it_q]<=1;pc[it_q]<=incoming_pc;atom[it_q]<=ROWSTRIPE ? ((ia_q/9)/32)*9+ia_q%9 : ia_q[28:5];data[it_q]<=id_q;
                    end
                end
                if(launch>=0) begin
                    if((CANONICAL && !APERTURE) || launch_global[34:30]!=0 ||
                       (APERTURE && (!aperture_valid || pc_base[pc[launch]*30+:30]>=pc_limit[pc[launch]*30+:30] || pc_limit[pc[launch]*30+:30]>MAX_PC_ATOMS || launch_end[30] || launch_end>{1'b0,pc_limit[pc[launch]*30+:30]}))) fault<=1;
                    else begin
                        state[launch]<=2;busy[pc[launch]]<=1;pc_tag[pc[launch]]<=launch[2:0];
                        out_v<=64'b1<<pc[launch];
                        if(CANONICAL || APERTURE) out_addr<=launch_global[29:0];
                        else out_addr<={6'b0,atom[launch]};
                        out_tag<={14'b0,launch[2:0]};out_data<=data[launch];
                    end
                end
                if(ret_sw>=0) begin
                    state[ret_sw]<=0;done_v[0]<=1;done_tag[2:0]<=ret_sw[2:0];
                end
                if(ret_se>=0) begin
                    state[ret_se]<=0;done_v[1]<=1;done_tag[5:3]<=ret_se[2:0];
                end
            end
        end
    end
endmodule
