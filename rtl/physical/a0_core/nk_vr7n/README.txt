NK vR7-new (qfd_tile_nk_a0c, counted re-sign epyc6 dq97/nk_eco2_resign_fc, flow-20261109-fc-qc) source files.

These 5 files are the exact bytes the signed NK view was built from (git blobs equal to the kit rtl/ and to
tools/qwen_dv/qc_nk_clock_1113/captured/rtl/). They are not copied onto the shared canonical paths
(rtl/physical/ot_qwen_rom_tile_nk.sv, a0_core/qfd_tile_nk_a0c.sv, a0_rc14_selected_2000/{qfd_tile_nk_rp2_45,
ot_qwen_w12_matvec_land32}.sv, a0_rc15_selected_2000/ot_qwen_rom_tile_w12_land32.sv) because those carry
later features other users instantiate (IDLE_UCK + ck_u port, CHILD_CLOCKS, GLOBAL_KV_CONST0, REGROOT,
ICG_K_NODE) that the NK form predates; a byte-equal overwrite would remove them. The other 25 NK RTL files
are byte-equal to existing main files. DIE-QC-97 11-09.
