# st_a scale-wait SRAM delay with registered read output (QC-TYPES-12, 2026-11-08)

Module `qfd_dv_sram_delay_orq` in `rtl/qwen_dv/qfd_dv_redstn2_gsafe.sv`, used only by `u_scale_wait` (W 512, D 3).
Read address is one edge earlier and `rd_out` goes through an unreset flop; latency D and the warm mask are unchanged.
Lock-step `tb_orq.sv` against the unmodified `qfd_dv_sram_delay` with a behavioral 1R1W SRAM (X-init unique, reset pulse every 50021 edges, seeds 7/11/12): D=3,4,14 PASS over 200000 edges; MUT=1 (address off by one) and MUT=2 (flop bypassed) FAIL as required. Run `run.sh` (paths fixed to the lane scratch).
