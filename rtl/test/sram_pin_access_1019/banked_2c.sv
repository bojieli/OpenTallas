// Project-native narrow SRAM banks. One registered read edge; no added state.
// The caller must prevent a simultaneous same-address read/write across clocks.
module ot_sram_banked_2c_1019 #(
  parameter integer WORDS=32, BITS=546, MUT=0,
  parameter integer AW=$clog2(WORDS)
)(input wire rclk,wclk,r_ce_in,w_ce_in,
  input wire [AW-1:0] r_addr_in,w_addr_in,
  input wire [BITS-1:0] wd_in,w_mask_in,
  output wire [BITS-1:0] rd_out);
  localparam integer N=(BITS+63)/64;
  localparam integer PW=WORDS<32?32:WORDS;
  localparam integer PA=$clog2(PW);
  wire [N*64-1:0] wd={{(N*64-BITS){1'b0}},wd_in};
  wire [N*64-1:0] mask={{(N*64-BITS){1'b0}},w_mask_in};
  wire [N*64-1:0] rd;
  wire [PA-1:0] ra={{(PA-AW){1'b0}},r_addr_in};
  wire [PA-1:0] wa={{(PA-AW){1'b0}},w_addr_in};
  assign rd_out=rd[BITS-1:0];
  for(genvar i=0;i<N;i=i+1) begin:b
    localparam integer O=(MUT==1)?((i+1)%N):i;
    wire [63:0] wm=MUT==2?~mask[i*64+:64]:mask[i*64+:64];
    if(PW==32) begin:d32
      ot_sram_1r1w2c_32x64_m1 m(.rclk(rclk),.wclk(wclk),
        .r_ce_in(r_ce_in),.w_ce_in(w_ce_in),.r_addr_in(ra),.w_addr_in(wa),
        .wd_in(wd[i*64+:64]),.w_mask_in(wm),.rd_out(rd[O*64+:64]));
    end else if(PW==128) begin:d128
      ot_sram_1r1w2c_128x64_m1 m(.rclk(rclk),.wclk(wclk),
        .r_ce_in(r_ce_in),.w_ce_in(w_ce_in),.r_addr_in(ra),.w_addr_in(wa),
        .wd_in(wd[i*64+:64]),.w_mask_in(wm),.rd_out(rd[O*64+:64]));
    end else if(PW==256) begin:d256
      ot_sram_1r1w2c_256x64_m1 m(.rclk(rclk),.wclk(wclk),
        .r_ce_in(r_ce_in),.w_ce_in(w_ce_in),.r_addr_in(ra),.w_addr_in(wa),
        .wd_in(wd[i*64+:64]),.w_mask_in(wm),.rd_out(rd[O*64+:64]));
    end else begin:bad
      initial $fatal(1,"unsupported physical depth");
    end
  end
endmodule
