# CLAUDE HBM-ABSTRACTS die view PDN = the HBM die PDN contract (tools/dsrom_s81_fulldie.py _gen_pg_lef / case_irm, the
# model the r16g IR verdict was measured with): the die owns M8/M9 (bump-aligned straps); every block exposes M7 PG
# stripes 0.288 um wide on a 10.8 um pitch (VDD at x = 1.0, VSS at x = 6.4 + k * 10.8) that the die grid drops onto
# through M7-M8 vias.  Inside: M1/M2 rails, M5 straps, M6 straps, M7 stripes.  Signals route M2-M7 (route_view.sh
# MAXL), so the view leaves M8/M9 to the die.  A view whose hard sub-macros carry M8/M9 PG breaks this contract:
# report it as a defect (the sub-block must be re-hardened with its PDN top at M7).
add_global_connection -net {VDD} -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}
add_pdn_stripe -grid {top} -layer {M1} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M2} -width {0.018} -pitch {0.54} -offset {0} -followpins
add_pdn_stripe -grid {top} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.288} -pitch {5.4} -offset {0.600}
add_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {5.112} -pitch {10.8} -offset {1.0}
add_pdn_connect -grid {top} -layers {M1 M2}
add_pdn_connect -grid {top} -layers {M2 M5}
add_pdn_connect -grid {top} -layers {M5 M6}
add_pdn_connect -grid {top} -layers {M6 M7}
# hfd_cmdproc: the command-memory SRAM macros (ot_sram_2rw_512x64_m4_r2c2, PG pins on M4) get M5 straps over the macro
# connected down to their M4 PG pins and up to the M6 straps of the top grid.
define_pdn_grid -macro -cells {ot_sram_2rw_512x64_m4_r2c2} -halo {2 2 2 2} -voltage_domains {CORE} -name {sram}
add_pdn_stripe -grid {sram} -layer {M5} -width {0.12} -spacing {0.072} -pitch {5.4} -offset {0.300}
add_pdn_connect -grid {sram} -layers {M4 M5}
add_pdn_connect -grid {sram} -layers {M5 M6}
# halo 2: cp9_pd55 PDN-0008 (the macro sits within 2.02 um of a row end; halo 5 overlapped 296 rows)
