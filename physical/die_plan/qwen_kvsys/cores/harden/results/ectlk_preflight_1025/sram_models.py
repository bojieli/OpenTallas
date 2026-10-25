import re,sys
from pathlib import Path
T=Path(sys.argv[1]); out=[]
for sfx in ["","_o"]:
    for (d,w) in [(128,256),(64,128),(256,128)]:
        a=(d-1).bit_length()
        out.append(f"""module ot_sram_1r1w_{d}x{w}_m1_r2c2{sfx} (input wire clk, input wire r_ce_in, input wire [{a-1}:0] r_addr_in, output reg [{w-1}:0] rd_out,
 input wire w_ce_in, input wire [{a-1}:0] w_addr_in, input wire [{w-1}:0] wd_in, input wire [{w-1}:0] w_mask_in,
 input wire [1:0] rr_en, input wire [13:0] rr_addr, input wire [1:0] cr_en, input wire [15:0] cr_sel);
 reg [{w-1}:0] m [0:{d-1}];
 always @(posedge clk) begin if (r_ce_in) rd_out <= m[r_addr_in]; if (w_ce_in) m[w_addr_in] <= (m[w_addr_in] & ~w_mask_in) | (wd_in & w_mask_in); end
endmodule""")
(T/"sram_models.sv").write_text("`timescale 1ns/1ps\n"+"\n".join(out)+"\n")
