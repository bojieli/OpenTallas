# Bench: QC embedding + RoPE row read at bound transport (QC-TRANSPORT-FIX 11-08)

`tb_emb_transport_fix.sv` instantiates the real `qfd_native59_dv_headprep_obs1 #(.ROPE(1), .EMB_RT_CODE, .EMB_RT_SCALE)`
and `qfd_embedding_word_provider #(.ROPE, .ROPE_FF)` with run-time stage counts on the six crossings
(+D_CRE/+D_CA/+D_CQ/+D_SRE/+D_SA/+D_SQ) and checks all 73 words (64 code, BF16 scale, 8 RoPE) on dr_o.
Parameters are Verilator defines: `+define+RC=<EMB_RT_CODE> +define+RS=<EMB_RT_SCALE> +define+PFF=<ROPE_FF> +define+PROPE=<ROPE>`.
