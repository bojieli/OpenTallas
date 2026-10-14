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
