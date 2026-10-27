# QC-SU-F4G step 1: tree-net-only M5 V / M6 H guide rewrite (unchanged F4D guide_tree_m56.py) from the F4F post-hold GRT DB.
# env IN OUT0 OUT1 JSON
read_db $::env(IN)
write_guides $::env(OUT0)
exec python3 -I /work/guide_tree_m56.py $::env(OUT0) $::env(OUT1) $::env(JSON) >@ stdout 2>@ stderr
puts "F4G_GUIDES written $::env(OUT1)"
