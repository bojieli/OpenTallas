# Physical normalization of published HEP w5e input hold chains, 2026-10-16.
# No RTL, state, clock, SDC, latency or acceptance change. This is a source-
# and input-ODB-bound candidate; reroute/extract/signoff/native audit is required.
if {[$block getName] ne "hfd_ep_static"} {error "HEP normalization block mismatch"}
if {![info exists ::env(OT_DB)] || ![file isfile $::env(OT_DB)]} {error "HEP input ODB missing"}
if {[lindex [exec sha256sum $::env(OT_DB)] 0] ne "f7e62335bfccbbbff7c70e8fd79e8882a1e41c84180dc0a6052b63999be92b80"} {
  error "HEP normalization input ODB hash mismatch"
}
set ot_hep_remove {hold21303 hold17507 hold21254 hold17498 hold21016 hold21410 hold21372 hold17296 hold21300 hold17622 hold17428 hold21050 hold21272 hold21132 hold22104 hold21674 hold21130 hold21294 hold21190 hold21086 hold17162 hold21182 hold21386 hold21278 hold21667 hold17278 hold17410 hold18069 hold17168 hold17634 hold17444 hold17628 hold18047 hold17234 hold17526 hold17244 hold17236 hold17294 hold17172 hold17494 hold21201 hold17528 hold18243 hold17240 hold17182 hold18189 hold18055 hold17265 hold17440 hold17486 hold20973 hold18051 hold17362 hold17989 hold17152 hold17150 hold21147 hold17192 hold21159 hold17209 hold17960 hold21045 hold21171 hold17427 hold21055 hold17475 hold17515 hold21119 hold20932 hold18004 hold21101 hold21289 hold20936 hold18036 hold18262 hold20945 hold21181 hold17479 hold17347 hold20924 hold17291 hold20920 hold17387 hold21267 hold17696 hold21179 hold17365 hold20930 hold17409 hold20971 hold21021 hold20981 hold17998 hold17267 hold18644 hold18570 hold17844 hold18084 hold20926 hold18054 hold18222 hold17439 hold21121 hold21125 hold17293 hold17335 hold18232 hold17978 hold18022 hold17357 hold21223 hold21043 hold18066 hold21141 hold18016 hold21105 hold18214 hold18006 hold21243 hold18226 hold18198 hold21033 hold17451 hold17401 hold21003 hold19348 hold21047 hold21261 hold21031 hold21265 hold21187 hold18178 hold17227 hold18018 hold17984 hold20961 hold21013 hold17259 hold21221 hold21167 hold17369 hold17992 hold19432 hold17431 hold18044 hold17301 hold21037 hold18228 hold17255 hold21143 hold17463 hold18014 hold17988 hold17337 hold18010 hold17379 hold18028 hold18208 hold21115 hold19408 hold19430 hold17980 hold20985 hold18000 hold17239 hold17914 hold17497 hold18172 hold17982 hold17433 hold17469 hold17423 hold19440 hold18220 hold17521 hold19306 hold21299 hold19504 hold21217 hold18192 hold19380 hold17976 hold18166 hold17996 hold19350 hold18030 hold19474 hold17838 hold19484 hold21305 hold18204 hold18194 hold18168 hold17808 hold17934 hold19442 hold19426 hold19444 hold19508 hold19292 hold17928 hold19446 hold18180 hold19458 hold19462 hold19282 hold19394 hold19514 hold19298 hold17920 hold19372 hold19422 hold17830 hold19506 hold19392 hold19402 hold19472 hold19480 hold19517 hold19286 hold19404 hold19364 hold19476 hold19366 hold18926 hold18611 hold19412 hold19494 hold19454 hold19502 hold19390 hold19368}
set ot_hep_swap {hold17525 BUFx2_ASAP7_75t_L hold17509 BUFx2_ASAP7_75t_L hold17812 BUFx2_ASAP7_75t_L hold17613 BUFx2_ASAP7_75t_L hold17511 BUFx2_ASAP7_75t_L hold17506 BUFx4_ASAP7_75t_R hold21411 BUFx2_ASAP7_75t_L hold21301 BUFx2_ASAP7_75t_L hold21029 BUFx4_ASAP7_75t_R hold21315 BUFx4_ASAP7_75t_R hold17503 BUFx4_ASAP7_75t_R hold21309 BUFx2_ASAP7_75t_L hold17491 BUFx4_ASAP7_75t_R hold21287 BUFx2_ASAP7_75t_L hold17811 BUFx2_ASAP7_75t_L}
# Validate the entire plan BEFORE its first mutation. Each removed output has
# exactly one signal sink and no external terminal. No clock net is changed.
foreach name [concat $ot_hep_remove [dict keys $ot_hep_swap]] {
  set inst [$block findInst $name]
  if {$inst eq "NULL" || [[$inst getMaster] getName] ne "BUFx2_ASAP7_75t_R"} {
    error "HEP normalization unexpected buffer $name"
  }
  foreach term [$inst getITerms] {
    if {[[$term getMTerm] getSigType] in {POWER GROUND}} continue
    set net [$term getNet]
    if {$net eq "NULL" || [$net getSigType] in {CLOCK POWER GROUND}} {
      error "HEP normalization non-signal net at $name"
    }
    if {[$term isOutputSignal] && ([llength [$net getITerms]] != 2 || [llength [$net getBTerms]] != 0)} {
      error "HEP normalization requires one internal sink at $name"
    }
  }
}
dict for {name master} $ot_hep_swap {
  if {[odb::dbMaster_find [ord::get_db] $master] eq "NULL"} {
    error "HEP normalization target master missing: $master (declare NATIVE_NORMALIZE_VT=LVT)"
  }
}
set ot_hep_n0 [llength [$block getInsts]]
remove_buffers {*}$ot_hep_remove
if {$ot_hep_n0 - [llength [$block getInsts]] != [llength $ot_hep_remove]} {
  error "HEP normalization removal census mismatch"
}
dict for {name master} $ot_hep_swap {replace_cell $name $master}
puts "OT_NATIVE_HEP normalized removed [llength $ot_hep_remove] resized [dict size $ot_hep_swap]; unchanged signoff and native audit required"
