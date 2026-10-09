# Yosys minimum physical-binding gate. Run with the actual ASAP7 liberty
# already read and the source compiled with SYNTHESIS; no place/route here.
hierarchy -top ot_s81_bf_input_holdseat -chparam W 1672 -chparam SEATS 4
proc
flatten
opt
check -assert
select -assert-count 6688 t:HB2xp67_ASAP7_75t_R
stat
puts "BF_HOLDSEAT_TECH_PASS bits=1672 seats=4 masters=6688"
