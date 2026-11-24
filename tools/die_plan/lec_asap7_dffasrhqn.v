// LEC functional model of ASAP7 DFFASRHQNx1_ASAP7_75t_R, written from its liberty ff(IQN,IQNN) group:
//   clear "!SETN" (IQN = 0), preset "!RESETN" (IQN = 1), clear_preset_var1/2 L (both active -> IQN = 0: clear wins),
//   clocked_on "CLK", next_state "!D", pin QN = IQN.
// Why (KV-PV-CAP 11-24): yosys 0.67 read_liberty imports this cell as $_DFFSR_PNN_ with S = RESETN & ~SETN, i.e. the set is
// active whenever SETN = 1, so every async-reset synchroniser mapped to DFFASRHQN is held in reset forever in a sequential
// gate-level LEC (frame-6 counterexample on the kv3_pv_v3 probe kit).  Read this file with read_verilog -overwrite AFTER the
// liberty files; the state wire is named IQN like the liberty model, so QN-state start-value handling stays the same.
module DFFASRHQNx1_ASAP7_75t_R (input CLK, input D, input RESETN, input SETN, output QN);
    reg IQN;
    always @(posedge CLK or negedge SETN or negedge RESETN)
        if (!SETN) IQN <= 1'b0;
        else if (!RESETN) IQN <= 1'b1;
        else IQN <= ~D;
    assign QN = IQN;
endmodule
