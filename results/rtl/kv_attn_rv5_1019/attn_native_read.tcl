foreach f {AO_RVT_TT_nldm_211120.lib.gz INVBUF_RVT_TT_nldm_220122.lib.gz OA_RVT_TT_nldm_211120.lib.gz SEQ_RVT_TT_nldm_220123.lib SIMPLE_RVT_TT_nldm_211120.lib.gz} { read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_$f }
read_db /audit/routes/gate/work/orfs/results/asap7/opentallas_qkd_kvs_attn_fl_asap7_ref_gate/base/4_1_cts.odb
write_verilog /out/attn_rv3_cts.v
set n 0; set b 0; set u 0
set f [open /out/attn_rv3_pg.tsv w]
foreach i [[ord::get_db_block] getInsts] {
 foreach t [$i getITerms] {
  set mt [$t getMTerm]; set sig [$mt getSigType]
  if {$sig ne "POWER" && $sig ne "GROUND"} {continue}
  incr n; set net [$t getNet]
  if {$net eq "NULL"} {incr u; puts $f "[$i getName]\t[$mt getName]\tUNBOUND"} else {incr b}
 }
}
close $f
puts "NATIVE_PG total=$n bound=$b unbound=$u"
exit
