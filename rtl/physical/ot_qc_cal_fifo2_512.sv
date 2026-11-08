`timescale 1ns/1ps
// Restricted replacement for calendar FIFO SRAMs whose addresses are 0/1 and repair inputs are zero.
// One registered read, CE hold, masked writes and read-before-write remain unchanged. No reset port.
(* keep_hierarchy="yes" *)
module ot_qc_cal_fifo2_inv(input wire a,output wire y);
  assign y=~a;
endmodule

// An 8-bit half of a 16-bit placement group. Local enables/select each fan to at most 8 data bits.
(* keep_hierarchy="yes" *)
module ot_qc_cal_fifo2_bank8(input wire clk,rce_n,ra_n,wce_n,wa_n,
    input wire[7:0]wd,mask,output reg[7:0]rd);
  reg[7:0]row0,row1;
  wire we0=!wce_n&&wa_n;
  wire we1=!wce_n&&!wa_n;
  initial begin
`ifndef OT_MEM_NO_INIT
    row0=8'd0;row1=8'd0;
`endif
  end
  always @(posedge clk)begin
    if(!rce_n)begin
      rd<=ra_n?row0:row1;
    end
    for(integer bit_i=0;bit_i<8;bit_i=bit_i+1)begin
      if(we0&&mask[bit_i])row0[bit_i]<=wd[bit_i];
      if(we1&&mask[bit_i])row1[bit_i]<=wd[bit_i];
    end
  end
endmodule

(* keep_hierarchy="yes" *)
module ot_qc_cal_fifo2_512(input wire clk,r_ce_in,input wire[5:0]r_addr_in,
    output wire[511:0]rd_out,input wire w_ce_in,input wire[5:0]w_addr_in,
    input wire[511:0]wd_in,w_mask_in,input wire[1:0]rr_en,input wire[11:0]rr_addr,
    input wire[1:0]cr_en,input wire[17:0]cr_sel);
`ifndef SYNTHESIS
  always @(posedge clk)begin
    if(r_addr_in[5:1]!==5'd0||w_addr_in[5:1]!==5'd0)$fatal(1,"fifo2 requires address bound 0/1");
    if(rr_en!==0||rr_addr!==0||cr_en!==0||cr_sel!==0)$fatal(1,"fifo2 requires literal-zero repair ports");
  end
`ifdef OT_MEM_FAULTS
  initial $fatal(1,"fifo2 fault-injection mode is not qualified");
`endif
`endif
  // Kept inverter tree: input fanout8; each trunk fanout2; branch fanout4; bank controls local.
  // Three inversions deliver negative controls to each 8-bit storage/read bank; no extra clock edge.
  for(genvar g=0;g<8;g=g+1)begin:g_trunk
    wire rce1,ra1,wce1,wa1;
    ot_qc_cal_fifo2_inv rc(.a(r_ce_in),.y(rce1));ot_qc_cal_fifo2_inv ra(.a(r_addr_in[0]),.y(ra1));
    ot_qc_cal_fifo2_inv wc(.a(w_ce_in),.y(wce1));ot_qc_cal_fifo2_inv wa(.a(w_addr_in[0]),.y(wa1));
    for(genvar sub=0;sub<2;sub=sub+1)begin:g_branch
      wire rce2,ra2,wce2,wa2;
      ot_qc_cal_fifo2_inv rc(.a(rce1),.y(rce2));ot_qc_cal_fifo2_inv ra(.a(ra1),.y(ra2));
      ot_qc_cal_fifo2_inv wc(.a(wce1),.y(wce2));ot_qc_cal_fifo2_inv wa(.a(wa1),.y(wa2));
      for(genvar group16=0;group16<2;group16=group16+1)begin:g_group16
        for(genvar half=0;half<2;half=half+1)begin:g_half
          localparam integer B=8*((g*2+sub)*4+group16*2+half);
          wire rce3,ra3,wce3,wa3;
          ot_qc_cal_fifo2_inv rc(.a(rce2),.y(rce3));ot_qc_cal_fifo2_inv ra(.a(ra2),.y(ra3));
          ot_qc_cal_fifo2_inv wc(.a(wce2),.y(wce3));ot_qc_cal_fifo2_inv wa(.a(wa2),.y(wa3));
          ot_qc_cal_fifo2_bank8 u_bank(.clk(clk),.rce_n(rce3),.ra_n(ra3),.wce_n(wce3),.wa_n(wa3),
             .wd(wd_in[B+:8]),.mask(w_mask_in[B+:8]),.rd(rd_out[B+:8]));
        end
      end
    end
  end
endmodule
