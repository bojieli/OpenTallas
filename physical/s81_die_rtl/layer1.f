# S81 layer1 die RTL manifest (s81-die-rtl-bind 2026-10-14, owner NO STUBS rule): the production RTL of every die master
# the generator instantiates under its die name, with the build defines the die composes it with.  Files listed here
# win over any other definition of the same module (tools/die_port_bind.py -f; the flat reference masters of the same
# name stay for the lockstep benches).  The case glue (stations / relays / end blocks) comes from the generator's
# netlist mode (die_glue.sv, --rtl-file); hard-macro behavioural models (ROM bit array, PHY PMA) are children of real RTL.
+define+OT_S81PH_COLL_JOB
+define+S81PH_GTH_DIE_CLOCKS
+define+S81PH_GTH_CONTROL_STRIP
# gather: 32 hardened root leaves + control leaf + 133 CLOSED relay strip, one clock entry per child (ck_l / ck_r)
rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_gather_c_cl.sv
# capture: wires-only cluster of CLOSED leaves, one clock entry per child (ck_g / ck_x / ck_c / ck_ka / ck_kb / ck_sb /
# ck_sn, ckv_x / ckv_d / ckv_r); source of the CLOSED dsfd_capt_x8_dual view (fa0792786)
rtl/dsrom_sys/s81_ph/ctrl_c/dsfd_sp_capture_c_cl.sv
# field configuration sequencer (7 cfg ROMs a pair)
rtl/v41die/ot_s81_cfg7_seq.sv
# cfg ROM macro model (bit array; the macro is hard IP)
physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v
# hard-macro behavioural models (SRAM / ROM bit arrays) instantiated by the RTL (children of real RTL only)
+libdir+physical/asap7_memory_macros_v2
# WFC stage kit: the hardened cluster of the PRICED kit (dsfd_wfc_stg_cl) under the die master name, with the hop
# endpoint (engine 7)
+define+DSFD_WFC_STG_CL_DIE
# STATIC die form (S-VM F7 2026-10-15): no t_lir / f_lor grant pins; static RX / TX message buffers, TX on the
# compiler's reserved edges (last RX arrival + TX_OFF); gate tools/dsrom_wfc_static_bench.py
+define+DSFD_WFC_STG_STATIC
rtl/dsrom_sys/mtp/dsfd_wfc_stg_cl.sv
+libdir+physical/s81_ph_views/mtp/macros
# BF pair (x512): the CLOSED compact199 views under their die names (tools/s81/gen_bf_die_wrappers.py: die bit i = the
# view pin tools/s81/bf_direct_pins.groups names; closed routes' parameters); dsfd_bf_front.xb = the native BF stream
rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv
rtl/dsrom_sys/s81_die_bind/dsfd_bf_front.sv
rtl/s81/ot_s81_bf_front.sv
rtl/v41rom/ot_v41_bf_col.sv
rtl/v41rom/ot_v41_bf_front_core.sv
# BF weight ROM macro model (bit array; the macro is hard IP)
physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v
# stage sequencer (--rtl-bind): the STATIC issuer (owner 2026-10-14 18:59: calendar-fixed issue, no credits); layer1
# die name dsfd_stage_seq_static_c8 = engines 0..7 + VM engine 12 (gate rtl/dsrom_sys/s81_static_control/test/run_static_c8.sh)
rtl/dsrom_sys/s81_static_control/dsfd_stage_seq_static_c8.sv
rtl/dsrom_sys/s81_static_control/dsfd_stage_seq_static_c.sv
rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv
rtl/dsrom_sys/s81_static_control/ot_s81_fixed_mailbox.sv
# PQ core slot (--rtl-bind master dsfd_sp_pq_n): the production native core cluster + ROM register / x-lane leaves.
# Core leaf set = these OT_PQ_* defines (tools/dsrom_s81_fulldie.py pq_rtl_clock_ports() reads them: one source).  The
# PQ's pinned-only modules come from its pinned tree; the repo copies of the shared float modules are supersets whose
# default parameters are the pinned behaviour (el1011-q-sp: L = 3 = the original adders), so they serve both.
+define+OT_PQ_ROM_PORTS
rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_core_native.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ctl_native.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ctl_fixed_native.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ix_sram.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ix_pin_variants.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ix_split_native.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_aq_split_native.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_sram.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_split_native.sv
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_one_native.sv
# PQ count-only return leaves (topology G, --pq-cnt): ot_s81_pq_rwbc15 / rwbc2 in the gather | capture seam
rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_rwbc.sv
physical/s81_pq_hier/pinned/rtl/hdc/v41x/ot_dsrom_aq12t.sv
physical/s81_pq_hier/pinned/rtl/hdc/v41x/ot_dsrom_aq12m.sv
physical/s81_pq_hier/pinned/rtl/v41die/ot_v41_pqc_tiles.sv
physical/s81_pq_hier/pinned/physical/dsrom_field_spine/ot_v41_pqc_tile_tops.sv
physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v

# Static VM: real 128-bank SRAM service, fixed-phase serial crossings, and engine 12.
# Pin mismatches with older die/collective recipes remain errors; no legacy port adapter.
rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm_static.sv
rtl/dsrom_sys/s81_ph/vm/ot_s81_vm_x34.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_core.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_wsched.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_wstage128.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_wdispatch128.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_rsched.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_landing.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static512_suhc.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_suhc_return_map.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_slice128_suhc.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_suhc_fsr.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_scatter.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_relay128.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_bank128.sv
physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_return.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_seq_static.sv

# Production static VM s2: real capture, WFC and scheduled scan/gather services.
+define+DSFD_SP_VM_MIX4
rtl/dsrom_sys/s81_ph/vm/ot_s81_vm_x43.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_capl.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_cap_leaf.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_cap.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_wfc.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_xio.sv

# S-BIND 2026-10-15: remaining static VM s2 source closure (tools/s81_vm/static_master_gate.sh file list)
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_fsr_bank8.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_fsr_quartets.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_read_leaf.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_read_quartets.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_read_valid.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_read_valid_quartets.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_read_router.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_write_capture128.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_scatter_b8_out.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_scatter_lane.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_relay128_b8.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_relay128_b4.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_w0.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_wcontrol.sv
rtl/dsrom_sys/s81_ph/vm/dsfd_vm_static_capl_pipe.sv

# S-BIND 2026-10-15 --static-coll: static collective die master dsfd_sp_collective_static_c and its closure
# (physical/s81_static_collective_proposal_1014/fullslab_module_manifest.json on codex/s81-static-collective-1014 @574f05810;
# all 25 source hashes verified)
rtl/dsrom_sys/s81_static_collective/dsfd_sp_collective_static_c.sv
rtl/dsrom_sys/s81_static_collective/s81_static_collective_slab.sv
rtl/dsrom_sys/s81_static_collective/s81_static_calendar_controller.sv
rtl/dsrom_sys/s81_static_collective/s81_static_fmt1_rank_dynamic_clocked.sv
rtl/dsrom_sys/s81_static_collective/s81_static_fmt1_core_dynamic.sv
rtl/dsrom_sys/s81_static_collective/s81_static_fmt1_lane_dynamic.sv
rtl/dsrom_sys/s81_static_collective/s81_static_fmt1_codec_dynamic.sv
rtl/dsrom_sys/s81_static_collective/s81_static_tp4_endpoint_dynamic.sv
rtl/dsrom_sys/s81_static_collective/s81_static_fmt1_gearbox.sv
rtl/dsrom_sys/s81_static_collective/s81_static_fmt1_channels_clocked.sv
rtl/dsrom_sys/s81_static_collective/s81_static_raw_fmt1_lane.sv
rtl/dsrom_sys/s81_static_collective/s81_static_raw_fmt1_codec.sv
rtl/dsrom_sys/s81_static_collective/s81_static_raw_vm_rows.sv
rtl/dsrom_sys/s81_ph/coll/dsfd_coll_static_channels.sv
rtl/dsrom_sys/s81_static_hc/s81_static_hc_reduce.sv
rtl/dsrom_sys/s81_static_hc/s81_static_hc_assemble.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_fp32_add_rne_preexp.sv
rtl/hdc/ot_hdc_prefix.sv
rtl/link/ot_link_crc32.sv
physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v
rtl/dsrom_sys/s81_ph/coll/dsfd_coll_ck.sv
rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv
rtl/dsrom_sys/s81_ph/ot_s81ph_coll_rstc.sv
rtl/dsrom_sys/s81_ph/ot_s81_pll_bb.sv
rtl/dsrom_sys/s81_static_collective/s81_static_vm_boundary.sv

# S-BIND 2026-10-15 --suhc-static-issue: SU / HC endpoints issue on the compiler command edge (no f_inp die pin)
+define+DSFD_SUHC_STATIC_ISSUE
rtl/dsrom_sys/s81_suhc/dsfd_sp_su_c.sv
rtl/dsrom_sys/s81_suhc/dsfd_sp_hc_c.sv
rtl/dsrom_sys/s81_suhc/dsfd_sp_hc.sv

# S-BIND 2026-10-15 --bf-x2-static: one packed static x lane word xw/xe[1100:0] {x2 536 | legacy 564 | v} from the PQ
# lane encoder (dsfd_pq_lx), column entry ot_s81_static_column_ingress (glue dsfd_cfifo), BF xb from the lane
+define+DSFD_PQ_STATIC_X2
rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv
rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress.sv

# S-BIND 2026-10-15 --bf-static-prog: static BF front (compiled programme f_prog 38 + io_clk) and the BF sequencer with
# the programme producer (descriptor in the cfg ROM spare columns); gates: tools/s81/bf_txn_bench.py --die-pair
# --static-prog 0 (real BF bench, TXN MATCH, mutants), rtl/v41die/test/run_cfg7_bfp_gate.sh
rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_static.sv
rtl/v41die/ot_s81_cfg7_seq_bfp.sv
rtl/dsrom_sys/s81_die_bind/ot_s81_bf_prog_seq.sv
