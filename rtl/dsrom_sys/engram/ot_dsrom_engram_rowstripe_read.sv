`timescale 1ns/1ps
// Opt-in ROWSTRIPE controller adapter. Boot/runtime ownership mux is external.
// Six reserved rows, one outstanding request per PC, nine protected atoms per
// row. Every real controller stream drains every cycle: up to six independent
// PCs may return simultaneously into the reserved per-row buffers. Generation
// wrap fails closed and requires reset/fence; it never aliases a stale return.
module ot_dsrom_engram_rowstripe_read #(parameter [71:0] READ_INJECT=0)(
    input wire ck,rst_n,
    input wire hq_valid,output wire hq_ready,
    input wire [30:0] hq_atom,input wire [3:0] hq_len,input wire [2:0] hq_tag,
    output wire [64*341-1:0] rq,input wire [2*8896-1:0] rd,
    output reg hr_valid,input wire hr_ready,
    output reg [2:0] hr_tag,output reg [3:0] hr_idx,output reg [255:0] hr_data,
    output reg ce,fault
);
    reg [63:0] pc_busy,out_v;
    reg [5:0] pc[0:5];
    reg [5:0] active;
    reg [13:0] generation[0:5];
    reg [8:0] seen[0:5];
    reg [3:0] next_atom[0:5];
    reg [29:0] out_addr;reg [16:0] out_tag;
    reg [2*8896-1:0] rd_q;
    reg [5:0] cap_v;
    reg [255:0] cap_data[0:5];
    reg [16:0] cap_tag[0:5];reg [3:0] cap_idx[0:5];
    wire [287:0] encoded[0:5];
    reg [287:0] buffer[0:5][0:8];
    wire [287:0] selected[0:5];
    wire [255:0] decoded[0:5];wire [3:0] corrected[0:5],uncorrectable[0:5];
    wire [30:0] row=hq_atom/9;
    wire [5:0] req_pc=(row%2)*32+(row/2)%32;
    assign hq_ready=!fault && hq_tag<6 && !active[hq_tag] && !pc_busy[req_pc] && generation[hq_tag]!=14'h3fff;
    genvar p,j,w;
    generate for(p=0;p<64;p=p+1) begin:g_rq
        assign rq[p*341+:341]={256'd0,32'd0,out_tag,4'd8,out_addr,1'b0,out_v[p]};
    end
    for(j=0;j<6;j=j+1) begin:g_row
        assign selected[j]=(next_atom[j]<9) ? buffer[j][next_atom[j]] : 288'd0;
        for(w=0;w<4;w=w+1) begin:g_ecc
            ot_s81_secded_enc72 enc(.d(cap_data[j][w*64+:64]),.c(encoded[j][w*72+:72]));
            ot_s81_secded_dec72 dec(.c(selected[j][w*72+:72]^READ_INJECT),.d(decoded[j][w*64+:64]),.ce(corrected[j][w]),.ue(uncorrectable[j][w]));
        end
    end endgenerate
    integer t,pick,physical,base,localpc;
    always @(*) begin
        pick=-1;
        for(t=5;t>=0;t=t-1)
            if(active[t] && seen[t]==9'h1ff && next_atom[t]<9) pick=t;
    end
    always @(posedge ck) begin
        rd_q<=rd;
        for(t=0;t<6;t=t+1) begin
            physical=pc[t];base=(physical/32)*8896;localpc=physical%32;
            cap_data[t]<=rd_q[base+localpc*256+:256];
            cap_tag[t]<=rd_q[base+8192+localpc*17+:17];
            cap_idx[t]<=rd_q[base+8736+localpc*4+:4];
        end
    end
    always @(posedge ck or negedge rst_n) begin
        if(!rst_n) begin
            active<=0;pc_busy<=0;out_v<=0;out_addr<=0;out_tag<=0;cap_v<=0;
            hr_valid<=0;hr_tag<=0;hr_idx<=0;hr_data<=0;ce<=0;fault<=0;
            for(t=0;t<6;t=t+1) begin generation[t]<=0;seen[t]<=0;next_atom[t]<=0;pc[t]<=0;end
        end else begin
            out_v<=0;ce<=0;
            for(t=0;t<6;t=t+1) begin
                physical=pc[t];base=(physical/32)*8896;localpc=physical%32;
                cap_v[t]<=active[t] && rd_q[base+8864+localpc];
                if(cap_v[t]) begin
                    if(!active[t] || cap_tag[t]!={generation[t],t[2:0]} || cap_idx[t]>=9 || seen[t][cap_idx[t]]) fault<=1;
                    else begin buffer[t][cap_idx[t]]<=encoded[t];seen[t][cap_idx[t]]<=1;end
                end
            end
            // Reject a return on an unowned PC; a stale return never gets
            // hidden merely because the requested tag is currently inactive.
            for(t=0;t<64;t=t+1) if(rd_q[(t/32)*8896+8864+t%32] && !pc_busy[t]) fault<=1;
            if(hq_valid && hq_ready) begin
                if(hq_len!=9 || hq_atom%9!=0) fault<=1;
                else begin
                    active[hq_tag]<=1;pc_busy[req_pc]<=1;pc[hq_tag]<=req_pc;
                    generation[hq_tag]<=generation[hq_tag]+1'b1;seen[hq_tag]<=0;next_atom[hq_tag]<=0;
                    out_v<=64'b1<<req_pc;out_addr<=(row/64)*9;
                    out_tag<={generation[hq_tag]+14'd1,hq_tag};
                end
            end
            if(hr_valid && hr_ready && hr_idx==8) begin
                active[hr_tag]<=0;pc_busy[pc[hr_tag]]<=0;
            end
            if(!hr_valid || hr_ready) begin
                hr_valid<=0;
                if(pick>=0 && !fault) begin
                    if(|uncorrectable[pick]) fault<=1;
                    else begin
                        hr_valid<=1;hr_tag<=pick[2:0];hr_idx<=next_atom[pick];hr_data<=decoded[pick];
                        ce<=|corrected[pick];next_atom[pick]<=next_atom[pick]+1'b1;
                    end
                end
            end
            if(fault) begin out_v<=0;hr_valid<=0;end
        end
    end
endmodule
