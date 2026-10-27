read_db /source/6_final.odb
set block [ord::get_db_block]
foreach name {ft_ck0_i ft_ck0_o ft_ck1_i ft_ck1_o ft_mesh_i ft_mesh_o ft_rst_i ft_rst_o ft_mstrap_i rst_n} {
  set bt [$block findBTerm $name]
  if {$bt == "NULL"} {puts "CENSUS_MISSING\t$name"; continue}
  set net [$bt getNet]
  puts "CENSUS_NET\t$name\t[$net getName]\t[llength [$net getITerms]]\t[llength [$net getBTerms]]"
  foreach it [$net getITerms] {
    set inst [$it getInst];set mt [$it getMTerm];set master [$inst getMaster]
    puts "CENSUS_TERM\t$name\t[$inst getName]\t[$master getName]\t[$mt getName]\t[$mt getIoType]"
  }
  foreach bp [$net getBTerms] {puts "CENSUS_PORT\t$name\t[$bp getName]\t[$bp getIoType]"}
}
exit
