# HEAD-RTL-5 2026-10-26: repo-relative supplement to the s81_head plan `sources` for tools/s81_head/head_die_portbind.py
# (die_port_bind --manifest-only).  Each entry = a module of the die's RTL closure that no partition type's `sources`
# lists; the instantiating source is named.  Move these into the plan type sources with the next PLAN-DELTA.
rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv                        # ot_s81ph_mem1r1w: ot_s81ph_link_ep_safe4 (u_rb/u_fifo), ot_s81hd_lep_core_nr (u_m); WREG + rst_n -> only this copy elaborates
rtl/hdc/ot_hdc_fp32_f12.sv                                      # ot_hdc_fp32_add_f12_l4: ot_s81hd_fadd (ot_s81hd_elem.sv)
rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_return.sv                 # dsdv_hostb_return: dsdv_hostb_stage_hbc
rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv                        # ot_pdie_serdes: ot_s81hd_serdes (digital link layer over behavioural PMA)
physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v   # macro model: dsdv_mu_land_head_nr
rtl/hdc/ot_hdc_prefix.sv                                        # ot_hdc_inc_k, ot_hdc_ksadd_k: ot_hdc_fp32_add_f12 (header: "Needs rtl/hdc/ot_hdc_prefix.sv")
rtl/hdc/ot_hdc_fastfp.sv                                        # ot_hdc_lzc32: ot_hdc_fp32_add_f12 (header: "Needs rtl/hdc/ot_hdc_fastfp.sv")
rtl/dsrom_sys/s81_link/ot_s81_kp4_enc.sv                        # ot_s81_kp4_enc: ot_pdie_serdes
rtl/dsrom_sys/s81_link/ot_s81_kp4_dec.sv                        # ot_s81_kp4_dec: ot_pdie_serdes
physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v   # macro model: ot_s81ph_mem1r1w SRAM=1
