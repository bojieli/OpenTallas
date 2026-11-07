import re,sys
# patches the original ot_pdie_serdes.sv: rate matcher OT_S81_RM_STAGED, reset replicas OT_S81_SERDES_RST_COPIES
src=open(sys.argv[1]).read(); new=open(sys.argv[2]).read()
a=src.index("    reg flt;\n    always @(posedge wclk or negedge wrst_n)\n        if (!wrst_n) begin wp <= 0; wp_g <= 0; flt <= 1'b0; end")
b=src.index("    reg f1, f2; always @(posedge rclk or negedge rrst_n)")
old=src[a:b]
flt="    reg flt;\n"
src=src[:a]+flt+"`ifdef OT_S81_RM_STAGED\n"+new+"`else\n"+old.replace(flt,"",1)+"`endif\n"+src[b:]
# reset copies
o="    wire rn_t = rs_t[1], rn_r = rs_r[1];\n"
i=src.index(o)
src=src[:i]+o+"""`ifdef OT_S81_SERDES_RST_COPIES
    // S81-RCK-4 11-07: kept identical copies of the last reset synchroniser stage, one per consumer (TT rs_t -> u_rm/u_enc recovery -264..-700)
    (* keep *) reg rs_t_enc, rs_t_rm;
    always @(posedge clk or negedge rst) if (!rst) begin rs_t_enc <= 1'b0; rs_t_rm <= 1'b0; end else begin rs_t_enc <= rs_t[0]; rs_t_rm <= rs_t[0]; end
    wire rn_t_enc = rs_t_enc, rn_t_rm = rs_t_rm;
`else
    wire rn_t_enc = rn_t, rn_t_rm = rn_t;
`endif
"""+src[i+len(o):]
c="ot_s81_kp4_enc #(.MUT(EMUT)) u_enc (.clk(clk), .rst_n(rn_t), .tx_v(rn_t),"
assert c in src
src=src.replace(c,"ot_s81_kp4_enc #(.MUT(EMUT)) u_enc (.clk(clk), .rst_n(rn_t_enc), .tx_v(rn_t_enc),",1)
c=".rclk(clk), .rrst_n(rn_t), .r_d(rx),\n        .fault(rm_flt));\n    // ---- status (ck)"
assert c in src
src=src.replace(c,".rclk(clk), .rrst_n(rn_t_rm), .r_d(rx),\n        .fault(rm_flt));\n    // ---- status (ck)",1)
open(sys.argv[3],'w').write(src)
