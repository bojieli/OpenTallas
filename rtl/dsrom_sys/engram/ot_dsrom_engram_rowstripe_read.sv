`timescale 1ns/1ps
// Opt-in ROWSTRIPE controller adapter. Boot/runtime ownership mux is external.
// Six reserved rows, one outstanding request per PC, nine protected atoms per
// row. Every real controller stream drains every cycle: up to six independent
// PCs may return simultaneously into the reserved per-row buffers. Generation
// wrap fails closed and requires reset/fence; it never aliases a stale return.
module ot_dsrom_engram_rowstripe_read #(parameter [71:0] READ_INJECT=0,parameter integer CANONICAL=0,parameter integer APERTURE=0,parameter integer MAX_PC_ATOMS=19775388)(
    input wire ck,rst_n,
    input wire aperture_valid,
    input wire [64*30-1:0] pc_base,pc_limit,
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
    reg [29:0] out_addr;reg [16:0] out_tag;reg [3:0] out_len;
    reg [30:0] local_start[0:5];reg [1:0] issued[0:5];
    reg [3:0] resolved_idx[0:5],resolved_len[0:5];
    function automatic [34:0] inverse(input [4:0] p,input [30:0] a);
        reg [30:0] t;reg [4:0] bank;
        begin t=a>>2;bank=(p^t^(t>>5))&31;inverse=({4'b0,t}<<7)|({30'b0,bank}<<2)|(a&3);end
    endfunction
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
    assign hq_ready=!fault && hq_tag<6 && !active[hq_tag] && !pc_busy[req_pc] && generation[hq_tag]!=(CANONICAL ? 14'h0fff : 14'h3fff);
    genvar p,j,w;
    generate for(p=0;p<64;p=p+1) begin:g_rq
        assign rq[p*341+:341]={256'd0,32'd0,out_tag,out_len,out_addr,1'b0,out_v[p]};
    end
    for(j=0;j<6;j=j+1) begin:g_row
        assign selected[j]=(next_atom[j]<9) ? buffer[j][next_atom[j]] : 288'd0;
        for(w=0;w<4;w=w+1) begin:g_ecc
            ot_s81_secded_enc72 enc(.d(cap_data[j][w*64+:64]),.c(encoded[j][w*72+:72]));
            ot_s81_secded_dec72 dec(.c(selected[j][w*72+:72]^READ_INJECT),.d(decoded[j][w*64+:64]),.ce(corrected[j][w]),.ue(uncorrectable[j][w]));
        end
    end endgenerate
    wire [30:0] incoming_local=(row/64)*9+(APERTURE ? {1'b0,pc_base[req_pc*30+:30]} : 31'd0);
    wire [31:0] incoming_end={1'b0,incoming_local}+32'd9;
    wire [34:0] incoming_global=inverse(req_pc[4:0],incoming_local);
    reg [30:0] send_local;reg [3:0] send_len;reg [34:0] send_global;
    integer t,pick,send,physical,base,localpc;
    always @(*) begin
        pick=-1;send=-1;send_local=0;send_len=0;send_global=0;
        for(t=5;t>=0;t=t-1) begin
            if(active[t] && seen[t]==9'h1ff && next_atom[t]<9) pick=t;
            if(CANONICAL && active[t] && issued[t]<3) send=t;
            if(CANONICAL) begin
                case(cap_tag[t][1:0])
                    0:begin resolved_idx[t]=cap_idx[t];resolved_len[t]=4-local_start[t][1:0];end
                    1:begin resolved_idx[t]=cap_idx[t]+4-local_start[t][1:0];resolved_len[t]=4;end
                    default:begin resolved_idx[t]=cap_idx[t]+8-local_start[t][1:0];resolved_len[t]=1+local_start[t][1:0];end
                endcase
            end else begin resolved_idx[t]=cap_idx[t];resolved_len[t]=9;end
        end
        if(send>=0) begin
            case(issued[send])
                0:begin send_local=local_start[send];send_len=4-local_start[send][1:0];end
                1:begin send_local=local_start[send]+4-local_start[send][1:0];send_len=4;end
                default:begin send_local=local_start[send]+8-local_start[send][1:0];send_len=1+local_start[send][1:0];end
            endcase
            send_global=inverse(pc[send][4:0],send_local);
        end
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
            active<=0;pc_busy<=0;out_v<=0;out_addr<=0;out_tag<=0;out_len<=0;cap_v<=0;
            hr_valid<=0;hr_tag<=0;hr_idx<=0;hr_data<=0;ce<=0;fault<=0;
            for(t=0;t<6;t=t+1) begin generation[t]<=0;seen[t]<=0;next_atom[t]<=0;pc[t]<=0;local_start[t]<=0;issued[t]<=0;end
        end else begin
            out_v<=0;ce<=0;
            for(t=0;t<6;t=t+1) begin
                physical=pc[t];base=(physical/32)*8896;localpc=physical%32;
                cap_v[t]<=active[t] && rd_q[base+8864+localpc];
                if(cap_v[t]) begin
                    if(!active[t] ||
                       (CANONICAL ? (cap_tag[t][16:5]!=generation[t][11:0] || cap_tag[t][4:2]!=t[2:0] || cap_tag[t][1:0]>=3) : cap_tag[t]!={generation[t],t[2:0]}) ||
                       cap_idx[t]>=resolved_len[t] || resolved_idx[t]>=9 || seen[t][resolved_idx[t]]) fault<=1;
                    else begin buffer[t][resolved_idx[t]]<=encoded[t];seen[t][resolved_idx[t]]<=1;end
                end
            end
            // Reject a return on an unowned PC; a stale return never gets
            // hidden merely because the requested tag is currently inactive.
            for(t=0;t<64;t=t+1) if(rd_q[(t/32)*8896+8864+t%32] && !pc_busy[t]) fault<=1;
            if(hq_valid && hq_ready) begin
                if(hq_len!=9 || hq_atom%9!=0 || (CANONICAL && !APERTURE) ||
                   (APERTURE && (!aperture_valid || pc_base[req_pc*30+:30]>=pc_limit[req_pc*30+:30] || pc_limit[req_pc*30+:30]>MAX_PC_ATOMS || incoming_end[31:30]!=0 || incoming_end>{2'b0,pc_limit[req_pc*30+:30]})) ||
                   (CANONICAL && incoming_global[34:30]!=0)) fault<=1;
                else begin
                    active[hq_tag]<=1;pc_busy[req_pc]<=1;pc[hq_tag]<=req_pc;
                    generation[hq_tag]<=generation[hq_tag]+1'b1;seen[hq_tag]<=0;next_atom[hq_tag]<=0;
                    local_start[hq_tag]<=incoming_local;
                    if(CANONICAL) issued[hq_tag]<=0;
                    else begin
                        issued[hq_tag]<=3;out_v<=64'b1<<req_pc;out_addr<=incoming_local[29:0];out_len<=8;
                        out_tag<={generation[hq_tag]+14'd1,hq_tag};
                    end
                end
            end
            if(send>=0 && !fault) begin
                if(send_global[34:30]!=0 || {1'b0,send_local}+send_len>{2'b0,pc_limit[pc[send]*30+:30]}) fault<=1;
                else begin
                    issued[send]<=issued[send]+1'b1;out_v<=64'b1<<pc[send];
                    out_addr<=send_global[29:0];out_len<=send_len;
                    out_tag<={generation[send][11:0],send[2:0],issued[send]};
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
