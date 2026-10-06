# Generated CP236 pin-only hook. Turing allocation; Harvey sole launch.
# Source after canonical four-box + association hooks, before placement.
# Do not apply to a routed checkpoint: its old wires would be stale.
set ot_pin_block [ord::get_db_block]
if {[$ot_pin_block getDbUnitsPerMicron]!=1000} {error "CP access units changed"}
proc ot_cp_access_regions {} {
 set out {}; set b [ord::get_db_block]
 foreach name {cp_body cp_association} {
  set r [$b findRegion $name]; if {$r eq "NULL"} {error "Missing CP fence $name"}
  set boxes {}; foreach box [$r getBoundaries] {
   lappend boxes [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]]
  }; lappend out $name [lsort $boxes]
 }; return $out
}
set ot_pin_before [ot_cp_access_regions]
set ot_pin_expected {cp_body {{17280 17280 60480 56160} {17280 60480 60480 64800} {22464 56160 60480 60480} {60480 17280 64800 64800}} cp_association {{17280 56160 22464 60480}}}
if {$ot_pin_before ne $ot_pin_expected} {error "CP allocation differs"}
set ot_pin_names {
 {clk}
 {por_n}
 {launch_v[0]}
 {launch_v[1]}
 {launch_pc[0]}
 {launch_pc[1]}
 {launch_pc[2]}
 {launch_pc[3]}
 {launch_pc[4]}
 {launch_pc[5]}
 {launch_pc[6]}
 {launch_pc[7]}
 {launch_pc[8]}
 {launch_pc[9]}
 {launch_pc[10]}
 {launch_pc[11]}
 {launch_pc[12]}
 {launch_pc[13]}
 {launch_pc[14]}
 {launch_pc[15]}
 {launch_pc[16]}
 {launch_pc[17]}
 {launch_pc[18]}
 {launch_pc[19]}
 {launch_pc[20]}
 {launch_pc[21]}
 {launch_pc[22]}
 {launch_pc[23]}
 {launch_pc[24]}
 {launch_pc[25]}
 {launch_pc[26]}
 {launch_pc[27]}
 {launch_pc[28]}
 {launch_pc[29]}
 {launch_pc[30]}
 {launch_pc[31]}
 {cp_job[0]}
 {cp_job[1]}
 {cp_job[2]}
 {cp_job[3]}
 {cp_job[4]}
 {cp_job[5]}
 {cp_job[6]}
 {cp_job[7]}
 {cp_job[8]}
 {cp_job[9]}
 {cp_job[10]}
 {cp_job[11]}
 {cp_job[12]}
 {cp_job[13]}
 {cp_job[14]}
 {cp_job[15]}
 {cp_job[16]}
 {cp_job[17]}
 {cp_job[18]}
 {cp_job[19]}
 {cp_job[20]}
 {cp_job[21]}
 {cp_job[22]}
 {cp_job[23]}
 {cp_job[24]}
 {cp_job[25]}
 {cp_job[26]}
 {cp_job[27]}
 {cp_job[28]}
 {cp_job[29]}
 {cp_job[30]}
 {cp_job[31]}
 {cp_gen[0]}
 {cp_gen[1]}
 {cp_gen[2]}
 {cp_gen[3]}
 {launch_token[0]}
 {launch_token[1]}
 {launch_token[2]}
 {launch_token[3]}
 {launch_token[4]}
 {launch_token[5]}
 {launch_token[6]}
 {launch_token[7]}
 {launch_token[8]}
 {launch_token[9]}
 {launch_token[10]}
 {launch_token[11]}
 {launch_token[12]}
 {launch_token[13]}
 {launch_token[14]}
 {launch_token[15]}
 {launch_token[16]}
 {launch_pos[0]}
 {launch_pos[1]}
 {launch_pos[2]}
 {launch_pos[3]}
 {launch_pos[4]}
 {launch_pos[5]}
 {launch_pos[6]}
 {launch_pos[7]}
 {launch_pos[8]}
 {launch_pos[9]}
 {launch_pos[10]}
 {launch_pos[11]}
 {launch_pos[12]}
 {launch_pos[13]}
 {launch_pos[14]}
 {launch_pos[15]}
 {launch_pos[16]}
 {launch_pos[17]}
 {launch_pos[18]}
 {launch_pos[19]}
 {native_launch[0]}
 {native_launch[1]}
 {lease_v}
 {lease_granted}
 {release_v}
 {release_r}
 {exec_done}
 {exec_fault}
 {retired_original_ops[0]}
 {retired_original_ops[1]}
 {retired_original_ops[2]}
 {retired_original_ops[3]}
 {shared_fault}
 {owned}
 {pending}
 {quiet}
 {selected}
 {done}
 {fault}
 {selected_pc[0]}
 {selected_pc[1]}
 {selected_pc[2]}
 {selected_pc[3]}
 {selected_pc[4]}
 {selected_pc[5]}
 {selected_pc[6]}
 {selected_pc[7]}
 {selected_pc[8]}
 {selected_pc[9]}
 {selected_pc[10]}
 {selected_pc[11]}
 {selected_pc[12]}
 {selected_pc[13]}
 {selected_pc[14]}
 {selected_pc[15]}
 {selected_pc[16]}
 {selected_pc[17]}
 {selected_pc[18]}
 {selected_pc[19]}
 {selected_pc[20]}
 {selected_pc[21]}
 {selected_pc[22]}
 {selected_pc[23]}
 {selected_pc[24]}
 {selected_pc[25]}
 {selected_pc[26]}
 {selected_pc[27]}
 {selected_pc[28]}
 {selected_pc[29]}
 {selected_pc[30]}
 {selected_pc[31]}
 {held_job[0]}
 {held_job[1]}
 {held_job[2]}
 {held_job[3]}
 {held_job[4]}
 {held_job[5]}
 {held_job[6]}
 {held_job[7]}
 {held_job[8]}
 {held_job[9]}
 {held_job[10]}
 {held_job[11]}
 {held_job[12]}
 {held_job[13]}
 {held_job[14]}
 {held_job[15]}
 {held_job[16]}
 {held_job[17]}
 {held_job[18]}
 {held_job[19]}
 {held_job[20]}
 {held_job[21]}
 {held_job[22]}
 {held_job[23]}
 {held_job[24]}
 {held_job[25]}
 {held_job[26]}
 {held_job[27]}
 {held_job[28]}
 {held_job[29]}
 {held_job[30]}
 {held_job[31]}
 {held_gen[0]}
 {held_gen[1]}
 {held_gen[2]}
 {held_gen[3]}
 {held_token[0]}
 {held_token[1]}
 {held_token[2]}
 {held_token[3]}
 {held_token[4]}
 {held_token[5]}
 {held_token[6]}
 {held_token[7]}
 {held_token[8]}
 {held_token[9]}
 {held_token[10]}
 {held_token[11]}
 {held_token[12]}
 {held_token[13]}
 {held_token[14]}
 {held_token[15]}
 {held_token[16]}
 {held_pos[0]}
 {held_pos[1]}
 {held_pos[2]}
 {held_pos[3]}
 {held_pos[4]}
 {held_pos[5]}
 {held_pos[6]}
 {held_pos[7]}
 {held_pos[8]}
 {held_pos[9]}
 {held_pos[10]}
 {held_pos[11]}
 {held_pos[12]}
 {held_pos[13]}
 {held_pos[14]}
 {held_pos[15]}
 {held_pos[16]}
 {held_pos[17]}
 {held_pos[18]}
 {held_pos[19]}
 {exec_owned}
 {new_request_permit}
 {association_fault}
}
foreach name $ot_pin_names {if {[$ot_pin_block findBTerm $name] eq "NULL"} {error "Missing pin $name"}}
place_pin -pin_name {clk} -layer M6 -location {17.280 17.360}
place_pin -pin_name {por_n} -layer M6 -location {17.280 17.488}
place_pin -pin_name {launch_v[0]} -layer M6 -location {17.280 17.616}
place_pin -pin_name {launch_v[1]} -layer M6 -location {17.280 17.744}
place_pin -pin_name {launch_pc[0]} -layer M6 -location {17.280 17.872}
place_pin -pin_name {launch_pc[1]} -layer M6 -location {17.280 18.000}
place_pin -pin_name {launch_pc[2]} -layer M6 -location {17.280 18.128}
place_pin -pin_name {launch_pc[3]} -layer M6 -location {17.280 18.256}
place_pin -pin_name {launch_pc[4]} -layer M6 -location {17.280 18.384}
place_pin -pin_name {launch_pc[5]} -layer M6 -location {17.280 18.512}
place_pin -pin_name {launch_pc[6]} -layer M6 -location {17.280 18.640}
place_pin -pin_name {launch_pc[7]} -layer M6 -location {17.280 18.768}
place_pin -pin_name {launch_pc[8]} -layer M6 -location {17.280 18.896}
place_pin -pin_name {launch_pc[9]} -layer M6 -location {17.280 19.024}
place_pin -pin_name {launch_pc[10]} -layer M6 -location {17.280 19.152}
place_pin -pin_name {launch_pc[11]} -layer M6 -location {17.280 19.280}
place_pin -pin_name {launch_pc[12]} -layer M6 -location {17.280 19.408}
place_pin -pin_name {launch_pc[13]} -layer M6 -location {17.280 19.536}
place_pin -pin_name {launch_pc[14]} -layer M6 -location {17.280 19.664}
place_pin -pin_name {launch_pc[15]} -layer M6 -location {17.280 19.792}
place_pin -pin_name {launch_pc[16]} -layer M6 -location {17.280 19.920}
place_pin -pin_name {launch_pc[17]} -layer M6 -location {17.280 20.048}
place_pin -pin_name {launch_pc[18]} -layer M6 -location {17.280 20.176}
place_pin -pin_name {launch_pc[19]} -layer M6 -location {17.280 20.304}
place_pin -pin_name {launch_pc[20]} -layer M6 -location {17.280 20.432}
place_pin -pin_name {launch_pc[21]} -layer M6 -location {17.280 20.560}
place_pin -pin_name {launch_pc[22]} -layer M6 -location {17.280 20.688}
place_pin -pin_name {launch_pc[23]} -layer M6 -location {17.280 20.816}
place_pin -pin_name {launch_pc[24]} -layer M6 -location {17.280 20.944}
place_pin -pin_name {launch_pc[25]} -layer M6 -location {17.280 21.072}
place_pin -pin_name {launch_pc[26]} -layer M6 -location {17.280 21.200}
place_pin -pin_name {launch_pc[27]} -layer M6 -location {17.280 21.328}
place_pin -pin_name {launch_pc[28]} -layer M6 -location {17.280 21.456}
place_pin -pin_name {launch_pc[29]} -layer M6 -location {17.280 21.584}
place_pin -pin_name {launch_pc[30]} -layer M6 -location {17.280 21.712}
place_pin -pin_name {launch_pc[31]} -layer M6 -location {17.280 21.840}
place_pin -pin_name {cp_job[0]} -layer M6 -location {17.280 21.968}
place_pin -pin_name {cp_job[1]} -layer M6 -location {17.280 22.096}
place_pin -pin_name {cp_job[2]} -layer M6 -location {17.280 22.224}
place_pin -pin_name {cp_job[3]} -layer M6 -location {17.280 22.352}
place_pin -pin_name {cp_job[4]} -layer M6 -location {17.280 22.480}
place_pin -pin_name {cp_job[5]} -layer M6 -location {17.280 22.608}
place_pin -pin_name {cp_job[6]} -layer M6 -location {17.280 22.736}
place_pin -pin_name {cp_job[7]} -layer M6 -location {17.280 22.864}
place_pin -pin_name {cp_job[8]} -layer M6 -location {17.280 22.992}
place_pin -pin_name {cp_job[9]} -layer M6 -location {17.280 23.120}
place_pin -pin_name {cp_job[10]} -layer M6 -location {17.280 23.248}
place_pin -pin_name {cp_job[11]} -layer M6 -location {17.280 23.376}
place_pin -pin_name {cp_job[12]} -layer M6 -location {17.280 23.504}
place_pin -pin_name {cp_job[13]} -layer M6 -location {17.280 23.632}
place_pin -pin_name {cp_job[14]} -layer M6 -location {17.280 23.760}
place_pin -pin_name {cp_job[15]} -layer M6 -location {17.280 23.888}
place_pin -pin_name {cp_job[16]} -layer M6 -location {17.280 24.016}
place_pin -pin_name {cp_job[17]} -layer M6 -location {17.280 24.144}
place_pin -pin_name {cp_job[18]} -layer M6 -location {17.280 24.272}
place_pin -pin_name {cp_job[19]} -layer M6 -location {17.280 24.400}
place_pin -pin_name {cp_job[20]} -layer M6 -location {17.280 24.528}
place_pin -pin_name {cp_job[21]} -layer M6 -location {17.280 24.656}
place_pin -pin_name {cp_job[22]} -layer M6 -location {17.280 24.784}
place_pin -pin_name {cp_job[23]} -layer M6 -location {17.280 24.912}
place_pin -pin_name {cp_job[24]} -layer M6 -location {17.280 25.040}
place_pin -pin_name {cp_job[25]} -layer M6 -location {17.280 25.168}
place_pin -pin_name {cp_job[26]} -layer M6 -location {17.280 25.296}
place_pin -pin_name {cp_job[27]} -layer M6 -location {17.280 25.424}
place_pin -pin_name {cp_job[28]} -layer M6 -location {17.280 25.552}
place_pin -pin_name {cp_job[29]} -layer M6 -location {17.280 25.680}
place_pin -pin_name {cp_job[30]} -layer M6 -location {17.280 25.808}
place_pin -pin_name {cp_job[31]} -layer M6 -location {17.280 25.936}
place_pin -pin_name {cp_gen[0]} -layer M6 -location {17.280 26.064}
place_pin -pin_name {cp_gen[1]} -layer M6 -location {17.280 26.192}
place_pin -pin_name {cp_gen[2]} -layer M6 -location {17.280 26.320}
place_pin -pin_name {cp_gen[3]} -layer M6 -location {17.280 26.448}
place_pin -pin_name {launch_token[0]} -layer M6 -location {17.280 26.576}
place_pin -pin_name {launch_token[1]} -layer M6 -location {17.280 26.704}
place_pin -pin_name {launch_token[2]} -layer M6 -location {17.280 26.832}
place_pin -pin_name {launch_token[3]} -layer M6 -location {17.280 26.960}
place_pin -pin_name {launch_token[4]} -layer M6 -location {17.280 27.088}
place_pin -pin_name {launch_token[5]} -layer M6 -location {17.280 27.216}
place_pin -pin_name {launch_token[6]} -layer M6 -location {17.280 27.344}
place_pin -pin_name {launch_token[7]} -layer M6 -location {17.280 27.472}
place_pin -pin_name {launch_token[8]} -layer M6 -location {17.280 27.600}
place_pin -pin_name {launch_token[9]} -layer M6 -location {17.280 27.728}
place_pin -pin_name {launch_token[10]} -layer M6 -location {17.280 27.856}
place_pin -pin_name {launch_token[11]} -layer M6 -location {17.280 27.984}
place_pin -pin_name {launch_token[12]} -layer M6 -location {17.280 28.112}
place_pin -pin_name {launch_token[13]} -layer M6 -location {17.280 28.240}
place_pin -pin_name {launch_token[14]} -layer M6 -location {17.280 28.368}
place_pin -pin_name {launch_token[15]} -layer M6 -location {17.280 28.496}
place_pin -pin_name {launch_token[16]} -layer M6 -location {17.280 28.624}
place_pin -pin_name {launch_pos[0]} -layer M6 -location {17.280 28.752}
place_pin -pin_name {launch_pos[1]} -layer M6 -location {17.280 28.880}
place_pin -pin_name {launch_pos[2]} -layer M6 -location {17.280 29.008}
place_pin -pin_name {launch_pos[3]} -layer M6 -location {17.280 29.136}
place_pin -pin_name {launch_pos[4]} -layer M6 -location {17.280 29.264}
place_pin -pin_name {launch_pos[5]} -layer M6 -location {17.280 29.392}
place_pin -pin_name {launch_pos[6]} -layer M6 -location {17.280 29.520}
place_pin -pin_name {launch_pos[7]} -layer M6 -location {17.280 29.648}
place_pin -pin_name {launch_pos[8]} -layer M6 -location {17.280 29.776}
place_pin -pin_name {launch_pos[9]} -layer M6 -location {17.280 29.904}
place_pin -pin_name {launch_pos[10]} -layer M6 -location {17.280 30.032}
place_pin -pin_name {launch_pos[11]} -layer M6 -location {17.280 30.160}
place_pin -pin_name {launch_pos[12]} -layer M6 -location {17.280 30.288}
place_pin -pin_name {launch_pos[13]} -layer M6 -location {17.280 30.416}
place_pin -pin_name {launch_pos[14]} -layer M6 -location {17.280 30.544}
place_pin -pin_name {launch_pos[15]} -layer M6 -location {17.280 30.672}
place_pin -pin_name {launch_pos[16]} -layer M6 -location {17.280 30.800}
place_pin -pin_name {launch_pos[17]} -layer M6 -location {17.280 30.928}
place_pin -pin_name {launch_pos[18]} -layer M6 -location {17.280 31.056}
place_pin -pin_name {launch_pos[19]} -layer M6 -location {17.280 31.184}
place_pin -pin_name {native_launch[0]} -layer M6 -location {17.280 31.312}
place_pin -pin_name {native_launch[1]} -layer M6 -location {17.280 31.440}
place_pin -pin_name {lease_v} -layer M6 -location {17.280 31.568}
place_pin -pin_name {lease_granted} -layer M6 -location {17.280 31.696}
place_pin -pin_name {release_v} -layer M6 -location {17.280 31.824}
place_pin -pin_name {release_r} -layer M6 -location {17.280 31.952}
place_pin -pin_name {exec_done} -layer M6 -location {17.280 32.080}
place_pin -pin_name {exec_fault} -layer M6 -location {17.280 32.208}
place_pin -pin_name {retired_original_ops[0]} -layer M6 -location {17.280 32.336}
place_pin -pin_name {retired_original_ops[1]} -layer M6 -location {17.280 32.464}
place_pin -pin_name {retired_original_ops[2]} -layer M6 -location {17.280 32.592}
place_pin -pin_name {retired_original_ops[3]} -layer M6 -location {17.280 32.720}
place_pin -pin_name {shared_fault} -layer M6 -location {17.280 32.848}
place_pin -pin_name {owned} -layer M6 -location {17.280 32.976}
place_pin -pin_name {pending} -layer M6 -location {17.280 33.104}
place_pin -pin_name {quiet} -layer M6 -location {17.280 33.232}
place_pin -pin_name {selected} -layer M6 -location {17.280 33.360}
place_pin -pin_name {done} -layer M6 -location {17.280 33.488}
place_pin -pin_name {fault} -layer M6 -location {17.280 33.616}
place_pin -pin_name {selected_pc[0]} -layer M6 -location {17.280 33.744}
place_pin -pin_name {selected_pc[1]} -layer M6 -location {17.280 33.872}
place_pin -pin_name {selected_pc[2]} -layer M6 -location {17.280 34.000}
place_pin -pin_name {selected_pc[3]} -layer M6 -location {17.280 34.128}
place_pin -pin_name {selected_pc[4]} -layer M6 -location {17.280 34.256}
place_pin -pin_name {selected_pc[5]} -layer M6 -location {17.280 34.384}
place_pin -pin_name {selected_pc[6]} -layer M6 -location {17.280 34.512}
place_pin -pin_name {selected_pc[7]} -layer M6 -location {17.280 34.640}
place_pin -pin_name {selected_pc[8]} -layer M6 -location {17.280 34.768}
place_pin -pin_name {selected_pc[9]} -layer M6 -location {17.280 34.896}
place_pin -pin_name {selected_pc[10]} -layer M6 -location {17.280 35.024}
place_pin -pin_name {selected_pc[11]} -layer M6 -location {17.280 35.152}
place_pin -pin_name {selected_pc[12]} -layer M6 -location {17.280 35.280}
place_pin -pin_name {selected_pc[13]} -layer M6 -location {17.280 35.408}
place_pin -pin_name {selected_pc[14]} -layer M6 -location {17.280 35.536}
place_pin -pin_name {selected_pc[15]} -layer M6 -location {17.280 35.664}
place_pin -pin_name {selected_pc[16]} -layer M6 -location {17.280 35.792}
place_pin -pin_name {selected_pc[17]} -layer M6 -location {17.280 35.920}
place_pin -pin_name {selected_pc[18]} -layer M6 -location {17.280 36.048}
place_pin -pin_name {selected_pc[19]} -layer M6 -location {17.280 36.176}
place_pin -pin_name {selected_pc[20]} -layer M6 -location {17.280 36.304}
place_pin -pin_name {selected_pc[21]} -layer M6 -location {17.280 36.432}
place_pin -pin_name {selected_pc[22]} -layer M6 -location {17.280 36.560}
place_pin -pin_name {selected_pc[23]} -layer M6 -location {17.280 36.688}
place_pin -pin_name {selected_pc[24]} -layer M6 -location {17.280 36.816}
place_pin -pin_name {selected_pc[25]} -layer M6 -location {17.280 36.944}
place_pin -pin_name {selected_pc[26]} -layer M6 -location {17.280 37.072}
place_pin -pin_name {selected_pc[27]} -layer M6 -location {17.280 37.200}
place_pin -pin_name {selected_pc[28]} -layer M6 -location {17.280 37.328}
place_pin -pin_name {selected_pc[29]} -layer M6 -location {17.280 37.456}
place_pin -pin_name {selected_pc[30]} -layer M6 -location {17.280 37.584}
place_pin -pin_name {selected_pc[31]} -layer M6 -location {17.280 37.712}
place_pin -pin_name {held_job[0]} -layer M6 -location {17.280 37.840}
place_pin -pin_name {held_job[1]} -layer M6 -location {17.280 37.968}
place_pin -pin_name {held_job[2]} -layer M6 -location {17.280 38.096}
place_pin -pin_name {held_job[3]} -layer M6 -location {17.280 38.224}
place_pin -pin_name {held_job[4]} -layer M6 -location {17.280 38.352}
place_pin -pin_name {held_job[5]} -layer M6 -location {17.280 38.480}
place_pin -pin_name {held_job[6]} -layer M6 -location {17.280 38.608}
place_pin -pin_name {held_job[7]} -layer M6 -location {17.280 38.736}
place_pin -pin_name {held_job[8]} -layer M6 -location {17.280 38.864}
place_pin -pin_name {held_job[9]} -layer M6 -location {17.280 38.992}
place_pin -pin_name {held_job[10]} -layer M6 -location {17.280 39.120}
place_pin -pin_name {held_job[11]} -layer M6 -location {17.280 39.248}
place_pin -pin_name {held_job[12]} -layer M6 -location {17.280 39.376}
place_pin -pin_name {held_job[13]} -layer M6 -location {17.280 39.504}
place_pin -pin_name {held_job[14]} -layer M6 -location {17.280 39.632}
place_pin -pin_name {held_job[15]} -layer M6 -location {17.280 39.760}
place_pin -pin_name {held_job[16]} -layer M6 -location {17.280 39.888}
place_pin -pin_name {held_job[17]} -layer M6 -location {17.280 40.016}
place_pin -pin_name {held_job[18]} -layer M6 -location {17.280 40.144}
place_pin -pin_name {held_job[19]} -layer M6 -location {17.280 40.272}
place_pin -pin_name {held_job[20]} -layer M6 -location {17.280 40.400}
place_pin -pin_name {held_job[21]} -layer M6 -location {17.280 40.528}
place_pin -pin_name {held_job[22]} -layer M6 -location {17.280 40.656}
place_pin -pin_name {held_job[23]} -layer M6 -location {17.280 40.784}
place_pin -pin_name {held_job[24]} -layer M6 -location {17.280 40.912}
place_pin -pin_name {held_job[25]} -layer M6 -location {17.280 41.040}
place_pin -pin_name {held_job[26]} -layer M6 -location {17.280 41.168}
place_pin -pin_name {held_job[27]} -layer M6 -location {17.280 41.296}
place_pin -pin_name {held_job[28]} -layer M6 -location {17.280 41.424}
place_pin -pin_name {held_job[29]} -layer M6 -location {17.280 41.552}
place_pin -pin_name {held_job[30]} -layer M6 -location {17.280 41.680}
place_pin -pin_name {held_job[31]} -layer M6 -location {17.280 41.808}
place_pin -pin_name {held_gen[0]} -layer M6 -location {17.280 41.936}
place_pin -pin_name {held_gen[1]} -layer M6 -location {17.280 42.064}
place_pin -pin_name {held_gen[2]} -layer M6 -location {17.280 42.192}
place_pin -pin_name {held_gen[3]} -layer M6 -location {17.280 42.320}
place_pin -pin_name {held_token[0]} -layer M6 -location {17.280 42.448}
place_pin -pin_name {held_token[1]} -layer M6 -location {17.280 42.576}
place_pin -pin_name {held_token[2]} -layer M6 -location {17.280 42.704}
place_pin -pin_name {held_token[3]} -layer M6 -location {17.280 42.832}
place_pin -pin_name {held_token[4]} -layer M6 -location {17.280 42.960}
place_pin -pin_name {held_token[5]} -layer M6 -location {17.280 43.088}
place_pin -pin_name {held_token[6]} -layer M6 -location {17.280 43.216}
place_pin -pin_name {held_token[7]} -layer M6 -location {17.280 43.344}
place_pin -pin_name {held_token[8]} -layer M6 -location {17.280 43.472}
place_pin -pin_name {held_token[9]} -layer M6 -location {17.280 43.600}
place_pin -pin_name {held_token[10]} -layer M6 -location {17.280 43.728}
place_pin -pin_name {held_token[11]} -layer M6 -location {17.280 43.856}
place_pin -pin_name {held_token[12]} -layer M6 -location {17.280 43.984}
place_pin -pin_name {held_token[13]} -layer M6 -location {17.280 44.112}
place_pin -pin_name {held_token[14]} -layer M6 -location {17.280 44.240}
place_pin -pin_name {held_token[15]} -layer M6 -location {17.280 44.368}
place_pin -pin_name {held_token[16]} -layer M6 -location {17.280 44.496}
place_pin -pin_name {held_pos[0]} -layer M6 -location {17.280 44.624}
place_pin -pin_name {held_pos[1]} -layer M6 -location {17.280 44.752}
place_pin -pin_name {held_pos[2]} -layer M6 -location {17.280 44.880}
place_pin -pin_name {held_pos[3]} -layer M6 -location {17.280 45.008}
place_pin -pin_name {held_pos[4]} -layer M6 -location {17.280 45.136}
place_pin -pin_name {held_pos[5]} -layer M6 -location {17.280 45.264}
place_pin -pin_name {held_pos[6]} -layer M6 -location {17.280 45.392}
place_pin -pin_name {held_pos[7]} -layer M6 -location {17.280 45.520}
place_pin -pin_name {held_pos[8]} -layer M6 -location {17.280 45.648}
place_pin -pin_name {held_pos[9]} -layer M6 -location {17.280 45.776}
place_pin -pin_name {held_pos[10]} -layer M6 -location {17.280 45.904}
place_pin -pin_name {held_pos[11]} -layer M6 -location {17.280 46.032}
place_pin -pin_name {held_pos[12]} -layer M6 -location {17.280 46.160}
place_pin -pin_name {held_pos[13]} -layer M6 -location {17.280 46.288}
place_pin -pin_name {held_pos[14]} -layer M6 -location {17.280 46.416}
place_pin -pin_name {held_pos[15]} -layer M6 -location {17.280 46.544}
place_pin -pin_name {held_pos[16]} -layer M6 -location {17.280 46.672}
place_pin -pin_name {held_pos[17]} -layer M6 -location {17.280 46.800}
place_pin -pin_name {held_pos[18]} -layer M6 -location {17.280 46.928}
place_pin -pin_name {held_pos[19]} -layer M6 -location {17.280 47.056}
place_pin -pin_name {exec_owned} -layer M6 -location {17.280 47.184}
place_pin -pin_name {new_request_permit} -layer M6 -location {17.280 47.312}
place_pin -pin_name {association_fault} -layer M6 -location {17.280 47.440}
if {[ot_cp_access_regions] ne $ot_pin_before} {error "CP fences changed"}
puts "OT_CP_PIN_ACCESS pins=236 M6_step_dbu=128 same_body4_association1"
