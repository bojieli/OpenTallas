s=open("tb_subdie.sv").read()
s=s.replace("    reg arst_n = 0, hbm_rn = 0, host_rn = 0, die_rn = 0, bg = 0;","""    reg arst_n = 0, host_rn = 0, die_rn = 0, hbm_rn_r = 0, bg_r = 0;
`ifdef SEQ
    // the die reset sequencer itself (ot_qwen_sys_rst_seq, links up) drives hbm_rst_n and boot_go;
    // T_HBM_GO = the RTL default, or `SEQ_GO (negative control: the old settle 4)
    wire hbm_rn, bg; wire s_host_rn, s_lrn, s_drn, s_rdy, s_bf; wire [3:0] s_st, s_err; wire [31:0] s_cyc;
    ot_qwen_sys_rst_seq #(.NL(1), .ND(1)
`ifdef SEQ_GO
        , .T_HBM_GO(`SEQ_GO)
`endif
    ) u_seq (.clk(clk), .por_n(arst_n), .soft_rst(1'b0), .link_up(1'b1), .boot_done(1'b0), .boot_ok(1'b0),
        .host_rst_n(s_host_rn), .link_rst_n(s_lrn), .hbm_rst_n(hbm_rn), .boot_go(bg), .die_rst_n(s_drn), .sys_ready(s_rdy),
        .boot_fault(s_bf), .boot_state(s_st), .boot_err(s_err), .boot_cycles(s_cyc));
    reg hq = 0; always @(posedge clk) begin hq <= hbm_rn; if (hbm_rn && !hq) $display("SUB cyc %0d hbm_rn released (seq)", cyc); if (bg) $display("SUB cyc %0d boot_go pulse (seq)", cyc); end
`else
    wire hbm_rn = hbm_rn_r, bg = bg_r;
`endif""")
open("tb_subdie_seq.sv","w").write(s)
p=open("probe_subdie.svh").read()
p=p.replace("hbm_rn = 1; $display","hbm_rn_r = 1; $display").replace("begin hbm_rn = 0; end","begin hbm_rn_r = 0; end").replace("@(posedge clk); bg = 1; @(posedge clk); bg = 0;","@(posedge clk); bg_r = 1; @(posedge clk); bg_r = 0;")
p=p.replace('`include "probe_k.svh"\n',"")
open("probe_subdie.svh","w").write(p)
