import re, sys, os
D = sys.argv[1]
gold = open(os.path.join(D, "src/gold_lgroup2_gp.sv")).read()
gate = open(os.path.join(D, "src/gate_lgroup2_gp.sv")).read()
M = "module ot_hgi_su_lgroup2_gp #("
assert gold.count(M) == 1 and gate.count(M) == 1

# 1. sim reference: gold renamed
open(os.path.join(D, "ref.sv"), "w").write(gold.replace(M, "module ot_hgi_su_lgroup2_gp_ref #("))

# 2. EQ gold: the same module, sw_* delayed one edge INSIDE (ports keep their names so equiv_make pairs ports and cells)
hdr_end = gold.index("    localparam integer N = 16")
head, body = gold[:hdr_end], gold[hdr_end:]
body2 = re.sub(r"\bsw_(v|addr|mask|d)\b", lambda m: "dsw_" + m.group(1), body)
dly = ("    reg [7:0] dsw_v; reg [119:0] dsw_addr; reg [63:0] dsw_mask; reg [2047:0] dsw_d;\n"
       "    always @(posedge clk) begin dsw_v <= sw_v; dsw_addr <= sw_addr; dsw_mask <= sw_mask; dsw_d <= sw_d; end\n")
open(os.path.join(D, "gold_d.sv"), "w").write(head + dly + body2)

# 3. negative controls on the gate (wrong shift on one consumer each)
def nc(old, new, name):
    assert gate.count(old) == 1, old
    open(os.path.join(D, name), "w").write(gate.replace(old, new))
nc("assign ev[b] = q_v;", "assign ev[b] = (b == 7) ? sw_v : q_v;", "nc1.sv")           # bank 7 write valid one edge early
nc("        assign ed = q_d;\n", "        assign ed = {q_d[2047:256], sw_d[255:0]};\n", "nc2.sv")  # lane 0 stage data one edge early
open(os.path.join(D, "gate.sv"), "w").write(gate)

sram = """module ot_sram_1r1w_2048x32_m8_r0c0_g32 (input wire clk, input wire r_ce_in, input wire [10:0] r_addr_in, output reg [31:0] rd_out,
    input wire w_ce_in, input wire [10:0] w_addr_in, input wire [31:0] wd_in, input wire w_mask_in);
    reg [31:0] mem [0:2047];
    integer i; initial begin for (i = 0; i < 2048; i = i + 1) mem[i] = 32'd0; rd_out = 32'd0; end
    always @(posedge clk) begin
        if (r_ce_in) rd_out <= mem[r_addr_in];
        if (w_ce_in && w_mask_in) mem[w_addr_in] <= wd_in;
    end
endmodule
"""
open(os.path.join(D, "sram_model.sv"), "w").write(sram)

for tag, f in (("E", "gate.sv"), ("NC1", "nc1.sv"), ("NC2", "nc2.sv")):
    ys = f"""read_liberty -lib /eq/lib/ot_sram_1r1w_2048x32_m8_r0c0_g32_tt.lib
read_verilog -sv -DSYNTHESIS -DOT_OPSG_GP -DOT_OPSG_ROT /eq/src/ot_hgi_su_lbank_n32.sv /eq/gold_d.sv
hierarchy -top ot_hgi_su_lgroup2_gp
proc; flatten; async2sync; opt_clean
rename ot_hgi_su_lgroup2_gp gold
design -stash gold
read_liberty -lib /eq/lib/ot_sram_1r1w_2048x32_m8_r0c0_g32_tt.lib
read_verilog -sv -DSYNTHESIS -DOT_OPSG_GP -DOT_OPSG_ROT -DOT_OPSG_E /eq/src/ot_hgi_su_lbank_n32.sv /eq/{f}
hierarchy -top ot_hgi_su_lgroup2_gp
proc; flatten; async2sync; opt_clean
rename ot_hgi_su_lgroup2_gp gate
design -stash gate
design -copy-from gold -as gold gold
design -copy-from gate -as gate gate
equiv_make gold gate equiv
hierarchy -top equiv
opt_clean
equiv_simple -seq 4
equiv_induct -seq 4
equiv_status -assert
"""
    open(os.path.join(D, f"eq_{tag}.ys"), "w").write(ys)
print("prepared")
