`timescale 1ns/1ps
// Isolated A2 controlled write proposal; no production adoption.
module s81_a2_controller #(parameter NSRC=53,BASE=0)(
 input wire ck_control,rst_n,
 input wire [NSRC-1:0] src_v,input wire [8*NSRC-1:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 output reg [167:0] ids,output reg [7:0] dr_v,
 output reg [15:0] dr_s,output reg fault
);
 reg rst_pin_q;reg [1:0] rr;
 always @(posedge ck_control) rst_pin_q<=rst_n;
 always @(posedge ck_control)if(!rst_pin_q)rr<=0;else rr<={rr[0],1'b1};
`ifdef S81_A2_MUT_HELD_RESET
 wire rn=1'b1;
`else
 wire rn=rr[1];
`endif
 reg [2:0] control_epoch,own_epoch_q,header_pin;
 reg [11:0] payload_pin;
 always @(posedge ck_control)begin
  header_pin<=header_epoch;payload_pin<=payload_epoch;own_epoch_q<=control_epoch;
  if(!rn)control_epoch<=0;else control_epoch<=control_epoch+3'd1;
 end
 wire phase_bad=(header_pin!=own_epoch_q) ||
   (payload_pin[2:0]!=own_epoch_q) || (payload_pin[5:3]!=own_epoch_q) ||
   (payload_pin[8:6]!=own_epoch_q) || (payload_pin[11:9]!=own_epoch_q);
 reg [2*NSRC-1:0] lane;reg [NSRC-1:0] lv;
    // saturating 2-bit add: 3 = "3 or more"
    function automatic [1:0] sat3(input [1:0] a, input [1:0] b);
        reg [2:0] t; begin t = a + b; sat3 = t[2] ? 2'd3 : t[1:0]; end
    endfunction
    localparam integer NP = 64;                            // tree width >= NSRC
    reg [NSRC-1:0] s_v; reg [8*NSRC-1:0] s_bank;            // source pin registers, edge P
    always @(posedge ck_control) begin
        s_bank <= src_bank;
        if (!rn) s_v <= {NSRC{1'b0}}; else s_v <= src_v;
    end
    reg [NSRC-1:0] lane_v_d; reg [2*NSRC-1:0] lane_d; reg lane_bad_d;
    always @* begin : p_lane integer c, d, w, k; reg [4:0] bc, bd; reg [1:0] t [0:NP-1]; reg [1:0] n;
        lane_bad_d = 1'b0;
        for (c = 0; c < NSRC; c = c + 1) begin
            bc = s_bank[8*c +: 5] ^ {s_bank[8*c+5 +: 3], 2'b00};
            for (d = 0; d < NP; d = d + 1) begin
                t[d] = 2'd0;
                if (d < c) begin
                    bd = s_bank[8*d +: 5] ^ {s_bank[8*d+5 +: 3], 2'b00};
                    t[d] = {1'b0, s_v[d] && bd == bc};
                end
            end
            for (w = NP / 2; w >= 1; w = w / 2)              // balanced tree, log2(NP) levels
                for (k = 0; k < w; k = k + 1) t[k] = sat3(t[2*k], t[2*k+1]);
            n = t[0];
`ifdef OT_VM_WSCHED_MUT_LANE
            lane_d[2*c +: 2] = 2'd0;                  // MUTANT: every record on lane 0 (dispatch duplicate)
`else
            lane_d[2*c +: 2] = n;
`endif
            lane_v_d[c] = s_v[c] && n != 2'd3;
            if (s_v[c] && n == 2'd3) lane_bad_d = 1'b1;
        end
    end

 reg [8*NSRC-1:0] bank_d;
 reg lane_bad;
 always @(posedge ck_control)begin
  bank_d<=s_bank;lane<=lane_d;
  if(!rn)begin lv<=0;lane_bad<=0;end
  else begin lv<=lane_v_d;lane_bad<=lane_bad_d;end
 end
 reg [167:0] id_d;reg [23:0] id_valid;
 integer g,c;reg [4:0] bc;
 always @*begin
  id_d=0;id_valid=0;bc=0;
  for(g=0;g<24;g=g+1)for(c=0;c<NSRC;c=c+1)begin
   bc=bank_d[8*c+:5]^{bank_d[8*c+5+:3],2'b00};
   if(lv[c] && bc==BASE+g/3 && lane[2*c+:2]==g%3)begin
    id_d[g*7+:6]=c;id_d[g*7+6]=1;
   end
  end
  for(g=0;g<24;g=g+1)id_valid[g]=ids[g*7+6];
 end
 always @(posedge ck_control)if(!rn)ids<=0;else begin
`ifdef S81_A2_MUT_ID
  ids<={id_d[166:0],id_d[167]};
`else
  ids<=id_d;
`endif
 end
 reg [23:0] h0,h1,h2;
 reg [7:0] drain_v_d;reg [15:0] drain_s_d;reg drain_bad;
 integer b;reg l0,l1,l2;
 always @*begin
  drain_v_d=0;drain_s_d=0;drain_bad=0;l0=0;l1=0;l2=0;
  for(b=0;b<8;b=b+1)begin
   l0=h0[3*b];l1=h1[3*b+1];l2=h2[3*b+2];
`ifdef S81_A2_MUT_DRAIN
   l1=h0[3*b+1];
`endif
   drain_v_d[b]=l0|l1|l2;
   drain_s_d[2*b+:2]=l0?0:l1?1:2;
   if((l0&&l1)||(l0&&l2)||(l1&&l2))drain_bad=1;
  end
 end
 always @(posedge ck_control)begin
  if(!rn)begin h0<=0;h1<=0;h2<=0;dr_v<=0;dr_s<=0;fault<=0;end
  else begin
   h0<=id_valid;h1<=h0;h2<=h1;
   dr_v<=drain_v_d;dr_s<=drain_s_d;
   fault<=fault|lane_bad|drain_bad|phase_bad;
  end
 end
endmodule

`timescale 1ns/1ps
`default_nettype none
// Five real W0 leaves replace the scalar 29,203-sink source register.
// All roots reserve the same compiler edge; no data stage or scheduling age is
// added. Each leaf has its own clock pin and local reset release. Epoch outputs
// are observation only: mismatches fault in the control leaf and never gate data.
module s81_a2_w0_payload #(parameter integer NSRC=53)(
 input wire ck,rst_n,
 input wire [4*NSRC-1:0] i_mask,input wire [128*NSRC-1:0] i_data,
 output reg [4*NSRC-1:0] o_mask,output reg [128*NSRC-1:0] o_data,
 output reg [2:0] o_epoch
);
 reg rst_pin_q;reg [1:0] rr;
 always @(posedge ck)rst_pin_q<=rst_n;
 always @(posedge ck)if(!rst_pin_q)rr<=0;else rr<={rr[0],1'b1};
 always @(posedge ck)begin
  o_mask<=i_mask;
`ifdef OT_VM_W0_MUT_SLICE
  o_data<=i_data^{{(128*NSRC-1){1'b0}},1'b1};
`else
  o_data<=i_data;
`endif
  if(!rr[1])o_epoch<=0;else begin
`ifdef S81_A2_MUT_EPOCH
   o_epoch<=o_epoch+3'd2;
`else
   o_epoch<=o_epoch+3'd1;
`endif
  end
 end
endmodule
module s81_a2_w0_header #(parameter integer NSRC=53)(
 input wire ck,rst_n,
 input wire [NSRC-1:0] i_v,input wire [14*NSRC-1:0] i_row,input wire [8*NSRC-1:0] i_tag,
 output reg [NSRC-1:0] o_v,output reg [14*NSRC-1:0] o_row,output reg [8*NSRC-1:0] o_tag,
 output reg [2:0] o_epoch
);
 reg rst_pin_q;reg [1:0] rr;
 always @(posedge ck)rst_pin_q<=rst_n;
 always @(posedge ck)if(!rst_pin_q)rr<=0;else rr<={rr[0],1'b1};
 always @(posedge ck)begin
  if(!rr[1])o_v<=0;else o_v<=i_v;
  o_row<=i_row;o_tag<=i_tag;
  if(!rr[1])o_epoch<=0;else begin
`ifdef S81_A2_MUT_EPOCH
   o_epoch<=o_epoch+3'd2;
`else
   o_epoch<=o_epoch+3'd1;
`endif
  end
 end
endmodule
`default_nettype wire

// Eleven actual roots per quarter. IDs and drains come only from its controller.
module s81_a2_quarter #(parameter NSRC=53,BASE=0)(
 input wire ck_control,ck_meta,input wire [7:0] ck_data,input wire ck_fault,
 input wire rst_control_n,rst_meta_n,input wire [7:0] rst_data_n,input wire rst_fault_n,
 input wire [NSRC-1:0] src_v,input wire [8*NSRC-1:0] src_bank,
 input wire [2:0] header_epoch,input wire [11:0] payload_epoch,
 input wire [14*NSRC-1:0] i_row,input wire [4*NSRC-1:0] i_mask,
 input wire [8*NSRC-1:0] i_tag,input wire [128*NSRC-1:0] i_data,
 output wire [7:0] o_v,output wire [111:0] o_row,output wire [31:0] o_mask,
 output wire [63:0] o_tag,output wire [1023:0] o_data,output wire fault
);
 wire [167:0] ids;wire [7:0] dv;wire [15:0] ds;
 wire fc,fm;wire [7:0] fd;
 wire [26*NSRC-1:0] mi;wire [207:0] mo;
 s81_a2_controller #(.NSRC(NSRC),.BASE(BASE)) u_control(
  ck_control,rst_control_n,src_v,src_bank,header_epoch,payload_epoch,ids,dv,ds,fc);
 genvar s,k;
 generate for(s=0;s<NSRC;s=s+1)begin
  assign mi[26*s+:26]={i_tag[8*s+:8],i_mask[4*s+:4],i_row[14*s+:14]};
 end
 for(k=0;k<8;k=k+1)begin
  assign {o_tag[8*k+:8],o_mask[4*k+:4],o_row[14*k+:14]}=mo[26*k+:26];
  wire [16*NSRC-1:0] di;wire [127:0] dout;wire [7:0] unused_v;
  for(s=0;s<NSRC;s=s+1)begin assign di[16*s+:16]=i_data[128*s+16*k+:16];end
  s81_area_stripe #(.NSRC(NSRC),.W(16)) u_data(
   ck_data[k],rst_data_n[k],di,ids,dv,ds,unused_v,dout,fd[k]);
  for(s=0;s<8;s=s+1)begin assign o_data[128*s+16*k+:16]=dout[16*s+:16];end
 end endgenerate
 s81_area_stripe #(.NSRC(NSRC),.W(26)) u_meta(
  ck_meta,rst_meta_n,mi,ids,dv,ds,o_v,mo,fm);
 s81_area_id_fault_join u_fault(ck_fault,rst_fault_n,{fd,fm,fc},fault);
endmodule

// Wires-only parent over five W0 roots and sixteen eleven-root quarters.
module s81_a2_controlled(
 input wire ck_header,input wire [3:0] ck_payload,
 input wire [15:0] ck_control,ck_meta,ck_fault,input wire [127:0] ck_data,
 input wire rst_header_n,input wire [3:0] rst_payload_n,
 input wire [15:0] rst_control_n,rst_meta_n,rst_fault_n,input wire [127:0] rst_data_n,
 input wire [52:0] i_v,input wire [741:0] i_row,input wire [423:0] i_tag,
 input wire [847:0] i_mask,input wire [27135:0] i_data,
 output wire [127:0] o_slice_v,output wire [1791:0] o_slice_row,
 output wire [1023:0] o_slice_tag,output wire [511:0] o_mask,
 output wire [16383:0] o_data,output wire [15:0] o_fault
);
 wire [52:0] header_v;
 wire [741:0] header_row;wire [423:0] header_tag;
 wire [2:0] header_epoch;wire [11:0] payload_epoch;
 wire [423:0] src_bank;
 s81_a2_w0_header u_header(ck_header,rst_header_n,i_v,i_row,i_tag,
  header_v,header_row,header_tag,header_epoch);
 genvar s,x,q,b;
 generate for(s=0;s<53;s=s+1)begin:raw_bank
  assign src_bank[8*s+:8]=i_row[14*s+:8];
 end
 for(x=0;x<4;x=x+1)begin:payload
  wire [6783:0] di,dout;wire [211:0] mi,mout;
  for(s=0;s<53;s=s+1)begin:source
   assign di[128*s+:128]=i_data[512*s+128*x+:128];
   assign mi[4*s+:4]=i_mask[16*s+4*x+:4];
  end
  s81_a2_w0_payload u_payload(ck_payload[x],rst_payload_n[x],mi,di,mout,dout,payload_epoch[3*x+:3]);
  for(q=0;q<4;q=q+1)begin:quarter
   wire [7:0] vo;wire [111:0] ro;wire [31:0] mo;
   wire [63:0] to;wire [1023:0] dataout;
   localparam I=x*4+q;
   s81_a2_quarter #(.BASE(q*8)) u_quarter(
    ck_control[I],ck_meta[I],ck_data[8*I+:8],ck_fault[I],
    rst_control_n[I],rst_meta_n[I],rst_data_n[8*I+:8],rst_fault_n[I],
    i_v,src_bank,header_epoch,payload_epoch,header_row,mout,header_tag,dout,
    vo,ro,mo,to,dataout,o_fault[I]);
   for(b=0;b<8;b=b+1)begin:bank
    assign o_slice_v[x*32+q*8+b]=vo[b];
    assign o_slice_row[(x*32+q*8+b)*14+:14]=ro[14*b+:14];
    assign o_slice_tag[(x*32+q*8+b)*8+:8]=to[8*b+:8];
    assign o_mask[(q*8+b)*16+x*4+:4]=mo[4*b+:4];
    assign o_data[(q*8+b)*512+x*128+:128]=dataout[128*b+:128];
   end
  end
 end endgenerate
endmodule
