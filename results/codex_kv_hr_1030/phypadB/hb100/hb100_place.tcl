foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*.lib*] {read_liberty $l}
read_db /work/run/results/asap7/hc_qkd_hr_phy_pad__86_4x95_04/base/6_final.odb
read_sdc /work/run/results/asap7/hc_qkd_hr_phy_pad__86_4x95_04/base/6_final.sdc
set ::env(RESULTS_DIR) /work/hb100
source /work/clk_freeze.tcl
ot_clk_freeze
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set orig {};set ck {}
foreach n [ot_clk_dbnets] {dict set ck [$n getName] 1}
foreach i [$b getInsts] {
 set n [$i getName];set m [[$i getMaster] getName]
 if {[regexp {^(FILLER|FILL|DECAP)} $m]} {odb::dbInst_destroy $i;continue}
 dict set orig $n [list [$i getLocation] $m]
 set movable [expr {[regexp {(^|/)hold[0-9]+$} $n] && $m eq "BUFx2_ASAP7_75t_R"}]
 foreach t [$i getITerms] {set net [$t getNet];if {$net ne "NULL" && [dict exists $ck [$net getName]]} {set movable 0}}
 if {$movable} {$i setPlacementStatus PLACED} else {$i setPlacementStatus LOCKED}
}
set master [[ord::get_db] findMaster HB4xp67_ASAP7_75t_R]
if {$master eq "NULL"} {error "missing HB4 master"}
set a [$b findInst {hold5271}];set mid [$b findInst {hold2907}];set z [$b findInst {hold5272}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold7383}];set mid [$b findInst {hold6854}];set z [$b findInst {hold4360}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5419}];set mid [$b findInst {hold2965}];set z [$b findInst {hold5420}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5383}];set mid [$b findInst {hold2969}];set z [$b findInst {hold5384}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5011}];set mid [$b findInst {hold2797}];set z [$b findInst {hold5012}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5323}];set mid [$b findInst {hold2941}];set z [$b findInst {hold5324}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5039}];set mid [$b findInst {hold2757}];set z [$b findInst {hold5040}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5239}];set mid [$b findInst {hold2823}];set z [$b findInst {hold5240}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5251}];set mid [$b findInst {hold2851}];set z [$b findInst {hold5252}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5023}];set mid [$b findInst {hold2789}];set z [$b findInst {hold5024}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5051}];set mid [$b findInst {hold2811}];set z [$b findInst {hold5052}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5695}];set mid [$b findInst {hold3105}];set z [$b findInst {hold5696}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5471}];set mid [$b findInst {hold2983}];set z [$b findInst {hold5472}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5215}];set mid [$b findInst {hold2839}];set z [$b findInst {hold5216}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5439}];set mid [$b findInst {hold2955}];set z [$b findInst {hold5440}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5255}];set mid [$b findInst {hold2921}];set z [$b findInst {hold5256}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5139}];set mid [$b findInst {hold2849}];set z [$b findInst {hold5140}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5107}];set mid [$b findInst {hold2767}];set z [$b findInst {hold5108}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4911}];set mid [$b findInst {hold2713}];set z [$b findInst {hold4912}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5699}];set mid [$b findInst {hold3107}];set z [$b findInst {hold5700}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5467}];set mid [$b findInst {hold2999}];set z [$b findInst {hold5468}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5155}];set mid [$b findInst {hold2891}];set z [$b findInst {hold5156}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5789}];set mid [$b findInst {hold3174}];set z [$b findInst {hold5790}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5235}];set mid [$b findInst {hold2829}];set z [$b findInst {hold5236}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4923}];set mid [$b findInst {hold2719}];set z [$b findInst {hold4924}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5111}];set mid [$b findInst {hold2861}];set z [$b findInst {hold5112}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5055}];set mid [$b findInst {hold2765}];set z [$b findInst {hold5056}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5327}];set mid [$b findInst {hold2929}];set z [$b findInst {hold5328}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5623}];set mid [$b findInst {hold3067}];set z [$b findInst {hold5624}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5855}];set mid [$b findInst {hold3266}];set z [$b findInst {hold5856}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4915}];set mid [$b findInst {hold2727}];set z [$b findInst {hold4916}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5547}];set mid [$b findInst {hold3031}];set z [$b findInst {hold5548}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5191}];set mid [$b findInst {hold2887}];set z [$b findInst {hold5192}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5295}];set mid [$b findInst {hold2885}];set z [$b findInst {hold5296}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5159}];set mid [$b findInst {hold2773}];set z [$b findInst {hold5160}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5083}];set mid [$b findInst {hold2809}];set z [$b findInst {hold5084}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5407}];set mid [$b findInst {hold2967}];set z [$b findInst {hold5408}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5343}];set mid [$b findInst {hold2909}];set z [$b findInst {hold5344}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4943}];set mid [$b findInst {hold2755}];set z [$b findInst {hold4944}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5599}];set mid [$b findInst {hold3041}];set z [$b findInst {hold5600}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5783}];set mid [$b findInst {hold3166}];set z [$b findInst {hold5784}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5655}];set mid [$b findInst {hold3079}];set z [$b findInst {hold5656}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5785}];set mid [$b findInst {hold3168}];set z [$b findInst {hold5786}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5639}];set mid [$b findInst {hold3077}];set z [$b findInst {hold5640}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5435}];set mid [$b findInst {hold2959}];set z [$b findInst {hold5436}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5103}];set mid [$b findInst {hold2833}];set z [$b findInst {hold5104}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5411}];set mid [$b findInst {hold2985}];set z [$b findInst {hold5412}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5515}];set mid [$b findInst {hold3009}];set z [$b findInst {hold5516}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5589}];set mid [$b findInst {hold3060}];set z [$b findInst {hold5590}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5431}];set mid [$b findInst {hold2987}];set z [$b findInst {hold5432}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5663}];set mid [$b findInst {hold3083}];set z [$b findInst {hold5664}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5507}];set mid [$b findInst {hold3005}];set z [$b findInst {hold5508}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5853}];set mid [$b findInst {hold3258}];set z [$b findInst {hold5854}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4995}];set mid [$b findInst {hold2753}];set z [$b findInst {hold4996}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5063}];set mid [$b findInst {hold2735}];set z [$b findInst {hold5064}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5247}];set mid [$b findInst {hold2911}];set z [$b findInst {hold5248}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5151}];set mid [$b findInst {hold2799}];set z [$b findInst {hold5152}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5003}];set mid [$b findInst {hold2745}];set z [$b findInst {hold5004}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5187}];set mid [$b findInst {hold2801}];set z [$b findInst {hold5188}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4999}];set mid [$b findInst {hold2781}];set z [$b findInst {hold5000}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5593}];set mid [$b findInst {hold3038}];set z [$b findInst {hold5594}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5733}];set mid [$b findInst {hold3120}];set z [$b findInst {hold5734}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5075}];set mid [$b findInst {hold2805}];set z [$b findInst {hold5076}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5315}];set mid [$b findInst {hold2917}];set z [$b findInst {hold5316}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5459}];set mid [$b findInst {hold2989}];set z [$b findInst {hold5460}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5335}];set mid [$b findInst {hold2923}];set z [$b findInst {hold5336}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5475}];set mid [$b findInst {hold3003}];set z [$b findInst {hold5476}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4927}];set mid [$b findInst {hold2731}];set z [$b findInst {hold4928}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5399}];set mid [$b findInst {hold2949}];set z [$b findInst {hold5400}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4979}];set mid [$b findInst {hold2721}];set z [$b findInst {hold4980}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5487}];set mid [$b findInst {hold2993}];set z [$b findInst {hold5488}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5591}];set mid [$b findInst {hold3061}];set z [$b findInst {hold5592}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4967}];set mid [$b findInst {hold2771}];set z [$b findInst {hold4968}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4939}];set mid [$b findInst {hold2763}];set z [$b findInst {hold4940}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5375}];set mid [$b findInst {hold2945}];set z [$b findInst {hold5376}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5099}];set mid [$b findInst {hold2787}];set z [$b findInst {hold5100}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5119}];set mid [$b findInst {hold2863}];set z [$b findInst {hold5120}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5799}];set mid [$b findInst {hold3198}];set z [$b findInst {hold5800}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4947}];set mid [$b findInst {hold2733}];set z [$b findInst {hold4948}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5917}];set mid [$b findInst {hold3308}];set z [$b findInst {hold5918}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5491}];set mid [$b findInst {hold2995}];set z [$b findInst {hold5492}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5815}];set mid [$b findInst {hold3218}];set z [$b findInst {hold5816}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5443}];set mid [$b findInst {hold2979}];set z [$b findInst {hold5444}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4907}];set mid [$b findInst {hold2711}];set z [$b findInst {hold4908}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5371}];set mid [$b findInst {hold2937}];set z [$b findInst {hold5372}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5455}];set mid [$b findInst {hold2997}];set z [$b findInst {hold5456}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5519}];set mid [$b findInst {hold3011}];set z [$b findInst {hold5520}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5347}];set mid [$b findInst {hold2935}];set z [$b findInst {hold5348}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5415}];set mid [$b findInst {hold2977}];set z [$b findInst {hold5416}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5945}];set mid [$b findInst {hold3312}];set z [$b findInst {hold5946}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5223}];set mid [$b findInst {hold2875}];set z [$b findInst {hold5224}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5523}];set mid [$b findInst {hold3019}];set z [$b findInst {hold5524}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5171}];set mid [$b findInst {hold2855}];set z [$b findInst {hold5172}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold4959}];set mid [$b findInst {hold2737}];set z [$b findInst {hold4960}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5287}];set mid [$b findInst {hold2873}];set z [$b findInst {hold5288}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5447}];set mid [$b findInst {hold2961}];set z [$b findInst {hold5448}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5423}];set mid [$b findInst {hold2963}];set z [$b findInst {hold5424}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5007}];set mid [$b findInst {hold2751}];set z [$b findInst {hold5008}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5047}];set mid [$b findInst {hold2815}];set z [$b findInst {hold5048}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
set a [$b findInst {hold5959}];set mid [$b findInst {hold3340}];set z [$b findInst {hold5960}]
set n1 [[$a findITerm Y] getNet];set n2 [[$mid findITerm Y] getNet];set out [[$z findITerm Y] getNet]
if {[llength [$n1 getITerms]]!=2 || [llength [$n2 getITerms]]!=2 || [llength [$n1 getBTerms]] || [llength [$n2 getBTerms]]} {error "nonlinear contraction"}
[$a findITerm Y] disconnect
odb::dbInst_destroy $mid
odb::dbInst_destroy $z
odb::dbNet_destroy $n1
odb::dbNet_destroy $n2
if {![$a swapMaster $master]} {error "swap refused"}
[$a findITerm Y] connect $out
detailed_placement -max_displacement {20 8}
check_placement -verbose
ot_clk_freeze_assert post_hb100
set f [open /work/hb100/moved_buffers.tsv w];set maxshift 0;set count 0
foreach i [$b getInsts] {
 set n [$i getName];if {![dict exists $orig $n]} {error "unexpected cell $n"}
 lassign [dict get $orig $n] oldxy oldmaster
 lassign $oldxy ox oy;lassign [$i getLocation] x y
 if {$x!=$ox || $y!=$oy} {
  if {![regexp {(^|/)hold[0-9]+$} $n]} {error "moved frozen cell $n"}
  set dist [expr {(abs($x-$ox)+abs($y-$oy))/double($u)}]
  puts $f "$n\t$ox\t$oy\t$x\t$y\t$dist";incr count;set maxshift [expr {max($maxshift,$dist)}]
 }
}
close $f
write_db /work/hb100/3_place.odb
write_def /work/hb100/3_place.def
write_verilog /work/hb100/3_place.v
puts "HB100_PLACED replacements100 moved$count maxshift$maxshift"
