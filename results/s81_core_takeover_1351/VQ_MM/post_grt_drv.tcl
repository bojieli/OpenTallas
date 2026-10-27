source /work/kit_modes_eco.tcl
global_route -start_incremental
repair_design -slew_margin 40 -cap_margin 20
# Extracted u_c bus: repair remaining BUFx3 siblings as one physical family (r11 residual _60630_/B).
foreach n {place4014 place4015 place4016 place4017 place4018 place4019 place4020 place4021 place4022 place4023 place4024 place4025 place4026 place4027 place4028 place4029 place4030 place4031 place4032 place4033 place4034 place4035 place4036 place4037 place4039 place4041 place4042 place4043 place4044 place4046 place4048 place4051 place4052 place4055 place4057 place4065 place4066 place4067 place4068 place4070 place4072 place4073 place4074 place4075 place4076 place4077 place4078 place4079 place4080 place4081 place4082 place4083 place4084 place4085 place4086 place4087 place4088 place4089 place4090} {
 if {[llength [get_cells $n]] != 1} { error "missing measured slew driver $n" }
 replace_cell $n BUFx10_ASAP7_75t_R
}
if {[llength [info procs ot_repair_timing]] == 0} { error "missing coupled TT/FF repair helper" }
ot_repair_timing {-setup -hold -setup_margin 0 -hold_margin 5 -max_buffer_percent 100}
detailed_placement
check_placement -verbose
global_route -end_incremental
estimate_parasitics -global_routing

kit_modes_eco_done
