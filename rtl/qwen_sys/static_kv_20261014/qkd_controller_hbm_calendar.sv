`timescale 1ns/1ps
// Boot-sealed, compressed fixed-cycle controller producer. No arrival/ready inputs.
// One image is reusable at each compiled layer start; layer/epoch are captured
// at start. cfg slots 0..15 use addr[4] for the high half of each 128-bit word.
// Word: start[15:0], count[25:16], burst_minus1[29:26], gap[37:30],
// command[80:38], mask[83:81] (RD, static column, write column),
// substitute_row[84], static_read[85], last event pin edge <=65535.
// Event first pin edge = captured go edge + start + 2 (input/output pin FFs).
// Every descriptor advances independently on absolute cycles; collisions fault
// without delaying any following event. Image capacity is checked by compiler.
module qkd_controller_hbm_calendar #(parameter integer N=16, ROW0=64, MUT=0, CORE_CLOCK=0)(
 input wire hck,rst_n,
 input wire cfg_we,input wire [4:0] cfg_addr,input wire [63:0] cfg_data,
 input wire seal,go,input wire [15:0] epoch,input wire [5:0] layer,
 output reg static_cmd_owner,output reg [42:0] static_cmd,
 output reg reserved_rd,reserved_static_col,reserved_write_col,
 output reg [15:0] static_epoch,output wire expected_raw_valid,
 output reg fault,output reg idle
);
 initial if(N<1 || N>16)$fatal(1,"calendar descriptor capacity must be 1..16");
 (* keep *) reg rn;
 always @(posedge hck)rn<=rst_n;
 reg we_q,seal_q,go_q;reg [4:0] addr_q;reg [63:0] data_q;
 reg [15:0] epoch_q;reg [5:0] layer_q;
 always @(posedge hck)begin addr_q<=cfg_addr;data_q<=cfg_data;epoch_q<=epoch;layer_q<=layer;end
 always @(posedge hck or negedge rn)
 if(!rn)begin we_q<=0;seal_q<=0;go_q<=0;end
 else begin we_q<=cfg_we;seal_q<=seal;go_q<=go;end
 reg [127:0] image[0:N-1];reg [N-1:0] low_seen,high_seen;
 reg sealed;reg [15:0] active_epoch;reg [18:0] active_row;
 reg [15:0] wait_q[0:N-1];reg [9:0] left_q[0:N-1];reg [3:0] burst_q[0:N-1];
 wire [N-1:0] fire,live;
 genvar g;
 generate for(g=0;g<N;g=g+1)begin:events
 assign live[g]=left_q[g]!=0;
 assign fire[g]=live[g]&&(wait_q[g]==0);
 end endgenerate
 reg [42:0] event_cmd;reg [2:0] event_mask;
 reg static_read;integer fires,i;
 always @*begin
 event_cmd=0;event_mask=0;static_read=0;fires=0;
 for(integer k=0;k<N;k=k+1)if(fire[k])begin
 fires=fires+1;
 event_cmd=event_cmd | (image[k][84] ? {image[k][80:58],active_row,image[k][38]} : image[k][80:38]);
 event_mask=event_mask | image[k][83:81];static_read=static_read|image[k][85];
 end
 end
 wire raw,unused_put;wire [15:0] unused_epoch;
 // Compiler accounts original controller pin-to-raw offset exactly. This leaf
 // feeds the reservation pins, so its own two pin edges precede this pipe.
 qkd_static_kv_return_calendar #(.CORE_CLOCK(CORE_CLOCK)) raw_calendar(.pll_hbm(hck),.hrst(rn),
 .reserved_rd(reserved_rd),.reserved_static_read(reserved_static_col&&static_read_q),
 .reservation_epoch(static_epoch),.expected_raw_valid(raw),.compiled_hbm_put(unused_put),.expected_return_epoch(unused_epoch));
 assign expected_raw_valid=raw;
 reg static_read_q;
 always @(posedge hck or negedge rn)
 if(!rn)begin
 low_seen<=0;high_seen<=0;sealed<=0;active_epoch<=0;active_row<=0;
 static_cmd_owner<=0;static_cmd<=0;reserved_rd<=0;reserved_static_col<=0;reserved_write_col<=0;
 static_epoch<=0;static_read_q<=0;fault<=0;idle<=1;
 for(i=0;i<N;i=i+1)begin wait_q[i]<=0;left_q[i]<=0;burst_q[i]<=0;end
 end else begin
 static_cmd<=event_cmd;reserved_rd<=event_mask[0];reserved_static_col<=event_mask[1];reserved_write_col<=event_mask[2];
 static_epoch<=active_epoch;static_read_q<=static_read;idle<=!(|live);
 if(fires>1 || (event_mask!=0 && (event_mask&(event_mask-1))!=0))fault<=1;
 if(we_q)begin
 if(sealed || |live || addr_q[3:0]>=N)fault<=1;
 else if(addr_q[4])begin image[addr_q[3:0]][127:64]<=data_q;high_seen[addr_q[3:0]]<=1;end
 else begin image[addr_q[3:0]][63:0]<=data_q;low_seen[addr_q[3:0]]<=1;end
 end
 if(seal_q)begin if((&low_seen)&&(&high_seen)&&!(|live))sealed<=1;else fault<=1;end
 if(go_q)begin
 if(!sealed || |live || we_q)fault<=1;
 else begin
 active_epoch<=epoch_q;active_row<=19'(ROW0)+{13'b0,layer_q};static_cmd_owner<=1;idle<=0;
 for(i=0;i<N;i=i+1)begin
 wait_q[i]<=image[i][15:0]+16'(MUT==1);left_q[i]<=image[i][25:16];burst_q[i]<=0;
 end
 end
 end else for(i=0;i<N;i=i+1)if(live[i])begin
 if(fire[i])begin
 left_q[i]<=left_q[i]-10'd1;
 if(burst_q[i]==image[i][29:26])begin wait_q[i]<= (MUT==2)?16'd0:{8'b0,image[i][37:30]};burst_q[i]<=0;end
 else begin wait_q[i]<=0;burst_q[i]<=burst_q[i]+4'd1;end
 end else wait_q[i]<=wait_q[i]-16'd1;
 end
 end
endmodule
