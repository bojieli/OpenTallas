set blk [ord::get_db_block]
set tech [ord::get_db_tech]
set mesh [$blk findNet ck_mesh]
if {$mesh == "NULL"} {error {missing actual ck_mesh net}}
foreach sw [$mesh getSWires] {odb::dbSWire_destroy $sw}
proc V {n} { global tech; set v [$tech findVia $n]; if {$v == "NULL"} { error "via $n missing" }; return $v }
proc LY {n} { global tech; return [$tech findLayer $n] }
set ot_ndr [$blk findNonDefaultRule CONTACT]
if {$ot_ndr == "NULL"} { error "clock NDR missing" }
proc RL {n} { global ot_ndr; return [$ot_ndr getLayerRule [LY $n]] }
proc rnet {nm} { global blk ot_ndr; set n [$blk findNet $nm]; if {$n == "NULL"} { error "missing clock net $nm" }; if {[$n isSpecial]} { $n clearSpecial }; foreach it [$n getITerms] { $it clearSpecial }; $n setSigType CLOCK; $n setNonDefaultRule $ot_ndr; set w [$n getWire]; if {$w != "NULL"} { odb::dbWire_destroy $w }; return [odb::dbWire_create $n] }
proc IT {i p} { global blk; set t [[$blk findInst $i] findITerm $p]; if {$t == "NULL"} { error "no iterm $i/$p" }; return $t }
proc BT {p} { global blk; set t [$blk findBTerm $p]; if {$t == "NULL"} { error "no bterm $p" }; return $t }
set e [odb::dbWireEncoder]
set em_saved_ndr $ot_ndr
if {[$blk findNonDefaultRule ot_explicit_mesh_ndr] == "NULL"} { create_ndr -name ot_explicit_mesh_ndr -width {M8 0.16 M9 0.16} -spacing {M8 0.08 M9 0.08} }
set ot_ndr [$blk findNonDefaultRule ot_explicit_mesh_ndr]
set w [rnet ck_mesh]
$e begin $w
$e newPath [LY M8] FIXED [RL M8]
set emj0 [$e addPoint 83472 136080]
$e newPath $emj0 FIXED [RL M8]
set emj1 [$e addPoint 84240 136080]
$e newPath $emj1 FIXED [RL M8]
set emj2 [$e addPoint 85472 136080]
$e newPath $emj1 FIXED [RL M8]
set emj3 [$e addTechVia [V {VIA89}]]
$e newPath $emj2 FIXED [RL M8]
set emj4 [$e addPoint 257040 136080]
$e newPath $emj3 FIXED [RL M9]
set emj5 [$e addPoint 84240 136170]
$e newPath $emj4 FIXED [RL M8]
set emj6 [$e addPoint 317520 136080]
$e newPath $emj4 FIXED [RL M8]
set emj7 [$e addTechVia [V {VIA89}]]
$e newPath $emj6 FIXED [RL M8]
set emj8 [$e addPoint 762480 136080]
$e newPath $emj6 FIXED [RL M8]
set emj9 [$e addTechVia [V {VIA89}]]
$e newPath $emj7 FIXED [RL M9]
set emj10 [$e addPoint 257040 135000]
$e newPath $emj7 FIXED [RL M9]
set emj11 [$e addPoint 257040 403920]
$e newPath $emj8 FIXED [RL M8]
set emj12 [$e addPoint 771120 136080]
$e newPath $emj8 FIXED [RL M8]
set emj13 [$e addTechVia [V {VIA89}]]
$e newPath $emj9 FIXED [RL M9]
set emj14 [$e addPoint 317520 132660]
$e newPath $emj10 FIXED [RL M9]
set emj15 [$e addPoint 257040 15056]
$e newPath $emj11 FIXED [RL M9]
set emj16 [$e addTechVia [V {VIA89}]]
$e newPath $emj11 FIXED [RL M9]
set emj17 [$e addPoint 257040 405000]
$e newPath $emj12 FIXED [RL M8]
set emj18 [$e addPoint 978144 136080]
$e newPath $emj12 FIXED [RL M8]
set emj19 [$e addTechVia [V {VIA89}]]
$e newPath $emj13 FIXED [RL M9]
set emj20 [$e addPoint 762480 28980]
$e newPath $emj16 FIXED [RL M8]
set emj21 [$e addPoint 83472 403920]
$e newPath $emj16 FIXED [RL M8]
set emj22 [$e addPoint 317520 403920]
$e newPath $emj17 FIXED [RL M9]
set emj23 [$e addPoint 257040 675000]
$e newPath $emj18 FIXED [RL M8]
set emj24 [$e addPoint 978480 136080]
$e newPath $emj19 FIXED [RL M9]
set emj25 [$e addPoint 771120 135000]
$e newPath $emj19 FIXED [RL M9]
set emj26 [$e addPoint 771120 403920]
$e newPath $emj22 FIXED [RL M8]
set emj27 [$e addPoint 771120 403920]
$e newPath $emj22 FIXED [RL M8]
set emj28 [$e addTechVia [V {VIA89}]]
$e newPath $emj23 FIXED [RL M9]
set emj29 [$e addPoint 257040 676080]
$e newPath $emj24 FIXED [RL M8]
set emj30 [$e addPoint 1285200 136080]
$e newPath $emj24 FIXED [RL M8]
set emj31 [$e addTechVia [V {VIA89}]]
$e newPath $emj25 FIXED [RL M9]
set emj32 [$e addPoint 771120 25830]
$e newPath $emj26 FIXED [RL M9]
set emch33 [$e addTechVia [V {VIA89}]]
$e newPath $emj26 FIXED [RL M9]
set emj33 [$e addPoint 771120 405000]
$e newPath $emj27 FIXED [RL M8]
set emj34 [$e addPoint 965520 403920]
$e newPath $emj28 FIXED [RL M9]
set emj35 [$e addPoint 317520 407340]
$e newPath $emj29 FIXED [RL M9]
set emj36 [$e addTechVia [V {VIA89}]]
$e newPath $emj29 FIXED [RL M9]
set emj37 [$e addPoint 257040 943920]
$e newPath $emj30 FIXED [RL M8]
set emj38 [$e addPoint 1388880 136080]
$e newPath $emj30 FIXED [RL M8]
set emj39 [$e addTechVia [V {VIA89}]]
$e newPath $emj31 FIXED [RL M9]
set emj40 [$e addPoint 978480 136170]
$e newPath $emj32 FIXED [RL M9]
set emj41 [$e addPoint 771120 23760]
$e newPath $emj32 FIXED [RL M9]
set emj42 [$e addPoint 771120 25696]
$e newPath $emj33 FIXED [RL M9]
set emj43 [$e addPoint 771120 675000]
$e newPath $emj34 FIXED [RL M8]
set emj44 [$e addPoint 1285200 403920]
$e newPath $emj34 FIXED [RL M8]
set emj45 [$e addTechVia [V {VIA89}]]
$e newPath $emj36 FIXED [RL M8]
set emj46 [$e addPoint 85472 676080]
$e newPath $emj36 FIXED [RL M8]
set emj47 [$e addPoint 317520 676080]
$e newPath $emj37 FIXED [RL M9]
set emj48 [$e addTechVia [V {VIA89}]]
$e newPath $emj37 FIXED [RL M9]
set emj49 [$e addPoint 257040 945000]
$e newPath $emj38 FIXED [RL M8]
set emj50 [$e addPoint 1390560 136080]
$e newPath $emj38 FIXED [RL M8]
set emj51 [$e addTechVia [V {VIA89}]]
$e newPath $emj39 FIXED [RL M9]
set emj52 [$e addPoint 1285200 135000]
$e newPath $emj39 FIXED [RL M9]
set emj53 [$e addPoint 1285200 403920]
$e newPath $emj41 FIXED [RL M9]
set emj54 [$e addTechVia [V {VIA89}]]
$e newPath $emj41 FIXED [RL M9]
set emj55 [$e addPoint 771120 15056]
$e newPath $emj41 FIXED [RL M9]
set emch57 [$e addPoint 771120 25696]
$e newPath $emj43 FIXED [RL M9]
set emj56 [$e addPoint 771120 676080]
$e newPath $emj44 FIXED [RL M8]
set emj57 [$e addPoint 1388880 403920]
$e newPath $emj44 FIXED [RL M8]
set emch60 [$e addTechVia [V {VIA89}]]
$e newPath $emj45 FIXED [RL M9]
set emj58 [$e addPoint 965520 407340]
$e newPath $emj46 FIXED [RL M8]
set emj59 [$e addPoint 84240 676080]
$e newPath $emj47 FIXED [RL M8]
set emj60 [$e addPoint 369360 676080]
$e newPath $emj47 FIXED [RL M8]
set emj61 [$e addTechVia [V {VIA89}]]
$e newPath $emj48 FIXED [RL M8]
set emj62 [$e addPoint 85472 943920]
$e newPath $emj48 FIXED [RL M8]
set emj63 [$e addPoint 317520 943920]
$e newPath $emj49 FIXED [RL M9]
set emj64 [$e addPoint 257040 1215000]
$e newPath $emj50 FIXED [RL M8]
set emj65 [$e addPoint 1466640 136080]
$e newPath $emj51 FIXED [RL M9]
set emj66 [$e addPoint 1388880 132660]
$e newPath $emj51 FIXED [RL M9]
set emj67 [$e addPoint 1388880 136170]
$e newPath $emj52 FIXED [RL M9]
set emj68 [$e addPoint 1285200 15056]
$e newPath $emj53 FIXED [RL M9]
set emj69 [$e addPoint 1285200 405000]
$e newPath $emj56 FIXED [RL M9]
set emj70 [$e addTechVia [V {VIA89}]]
$e newPath $emj56 FIXED [RL M9]
set emj71 [$e addPoint 771120 943920]
$e newPath $emj57 FIXED [RL M8]
set emj72 [$e addPoint 1390560 403920]
$e newPath $emj57 FIXED [RL M8]
set emj73 [$e addTechVia [V {VIA89}]]
$e newPath $emj59 FIXED [RL M8]
set emj74 [$e addPoint 83472 676080]
$e newPath $emj59 FIXED [RL M8]
set emj75 [$e addTechVia [V {VIA89}]]
$e newPath $emj60 FIXED [RL M8]
set emj76 [$e addPoint 370912 676080]
$e newPath $emj60 FIXED [RL M8]
set emj77 [$e addTechVia [V {VIA89}]]
$e newPath $emj61 FIXED [RL M9]
set emj78 [$e addPoint 317520 672660]
$e newPath $emj62 FIXED [RL M8]
set emj79 [$e addPoint 84240 943920]
$e newPath $emj63 FIXED [RL M8]
set emj80 [$e addPoint 771120 943920]
$e newPath $emj63 FIXED [RL M8]
set emj81 [$e addTechVia [V {VIA89}]]
$e newPath $emj64 FIXED [RL M9]
set emj82 [$e addPoint 257040 1216080]
$e newPath $emj65 FIXED [RL M8]
set emj83 [$e addPoint 1466976 136080]
$e newPath $emj65 FIXED [RL M8]
set emj84 [$e addTechVia [V {VIA89}]]
$e newPath $emj69 FIXED [RL M9]
set emj85 [$e addPoint 1285200 675000]
$e newPath $emj70 FIXED [RL M8]
set emch89 [$e addPoint 370912 676080]
$e newPath $emj70 FIXED [RL M8]
set emj86 [$e addPoint 965520 676080]
$e newPath $emj71 FIXED [RL M9]
set emch91 [$e addTechVia [V {VIA89}]]
$e newPath $emj71 FIXED [RL M9]
set emj87 [$e addPoint 771120 945000]
$e newPath $emj71 FIXED [RL M9]
set emj88 [$e addPoint 771120 1094220]
$e newPath $emj72 FIXED [RL M8]
set emj89 [$e addPoint 1475280 403920]
$e newPath $emj73 FIXED [RL M9]
set emj90 [$e addPoint 1388880 404010]
$e newPath $emj73 FIXED [RL M9]
set emj91 [$e addPoint 1388880 407340]
$e newPath $emj75 FIXED [RL M9]
set emj92 [$e addPoint 84240 676170]
$e newPath $emj77 FIXED [RL M9]
set emj93 [$e addPoint 369360 676170]
$e newPath $emj79 FIXED [RL M8]
set emj94 [$e addPoint 83472 943920]
$e newPath $emj79 FIXED [RL M8]
set emj95 [$e addTechVia [V {VIA89}]]
$e newPath $emj80 FIXED [RL M8]
set emj96 [$e addPoint 978144 943920]
$e newPath $emj81 FIXED [RL M9]
set emj97 [$e addPoint 317520 947340]
$e newPath $emj82 FIXED [RL M9]
set emj98 [$e addTechVia [V {VIA89}]]
$e newPath $emj82 FIXED [RL M9]
set emj99 [$e addPoint 257040 1374560]
$e newPath $emj83 FIXED [RL M8]
set emj100 [$e addPoint 1790640 136080]
$e newPath $emj84 FIXED [RL M9]
set emj101 [$e addPoint 1466640 136170]
$e newPath $emj85 FIXED [RL M9]
set emj102 [$e addPoint 1285200 676080]
$e newPath $emj86 FIXED [RL M8]
set emj103 [$e addPoint 978144 676080]
$e newPath $emj86 FIXED [RL M8]
set emj104 [$e addTechVia [V {VIA89}]]
$e newPath $emj87 FIXED [RL M9]
set emch110 [$e addPoint 771120 1094220]
$e newPath $emj88 FIXED [RL M9]
set emj105 [$e addPoint 771120 1098450]
$e newPath $emj89 FIXED [RL M8]
set emj106 [$e addPoint 1799280 403920]
$e newPath $emj89 FIXED [RL M8]
set emj107 [$e addTechVia [V {VIA89}]]
$e newPath $emj95 FIXED [RL M9]
set emj108 [$e addPoint 84240 944010]
$e newPath $emj96 FIXED [RL M8]
set emj109 [$e addPoint 978480 943920]
$e newPath $emj98 FIXED [RL M8]
set emj110 [$e addPoint 83472 1216080]
$e newPath $emj98 FIXED [RL M8]
set emj111 [$e addPoint 317520 1216080]
$e newPath $emj99 FIXED [RL M9]
set emj112 [$e addPoint 257040 1374750]
$e newPath $emj99 FIXED [RL M9]
set emj113 [$e addPoint 257040 1375920]
$e newPath $emj100 FIXED [RL M8]
set emj114 [$e addPoint 1799280 136080]
$e newPath $emj100 FIXED [RL M8]
set emj115 [$e addTechVia [V {VIA89}]]
$e newPath $emj102 FIXED [RL M9]
set emj116 [$e addTechVia [V {VIA89}]]
$e newPath $emj102 FIXED [RL M9]
set emj117 [$e addPoint 1285200 943920]
$e newPath $emj103 FIXED [RL M8]
set emj118 [$e addPoint 978480 676080]
$e newPath $emj104 FIXED [RL M9]
set emj119 [$e addPoint 965520 672660]
$e newPath $emj105 FIXED [RL M9]
set emj120 [$e addPoint 771120 1098464]
$e newPath $emj105 FIXED [RL M9]
set emj121 [$e addPoint 771120 1099440]
$e newPath $emj106 FIXED [RL M8]
set emj122 [$e addPoint 2309040 403920]
$e newPath $emj106 FIXED [RL M8]
set emj123 [$e addTechVia [V {VIA89}]]
$e newPath $emj107 FIXED [RL M9]
set emj124 [$e addPoint 1475280 407340]
$e newPath $emj109 FIXED [RL M8]
set emj125 [$e addPoint 1250640 943920]
$e newPath $emj109 FIXED [RL M8]
set emj126 [$e addTechVia [V {VIA89}]]
$e newPath $emj111 FIXED [RL M8]
set emj127 [$e addPoint 762480 1216080]
$e newPath $emj111 FIXED [RL M8]
set emj128 [$e addTechVia [V {VIA89}]]
$e newPath $emj112 FIXED [RL M9]
set emch135 [$e addPoint 257040 1375920]
$e newPath $emj113 FIXED [RL M9]
set emj129 [$e addTechVia [V {VIA89}]]
$e newPath $emj113 FIXED [RL M9]
set emj130 [$e addPoint 257040 1483920]
$e newPath $emj114 FIXED [RL M8]
set emj131 [$e addPoint 2309040 136080]
$e newPath $emj114 FIXED [RL M8]
set emj132 [$e addTechVia [V {VIA89}]]
$e newPath $emj115 FIXED [RL M9]
set emj133 [$e addPoint 1790640 3060]
$e newPath $emj116 FIXED [RL M8]
set emch141 [$e addPoint 978480 676080]
$e newPath $emj116 FIXED [RL M8]
set emj134 [$e addPoint 1298160 676080]
$e newPath $emj117 FIXED [RL M9]
set emj135 [$e addTechVia [V {VIA89}]]
$e newPath $emj117 FIXED [RL M9]
set emj136 [$e addPoint 1285200 945000]
$e newPath $emj118 FIXED [RL M8]
set emj137 [$e addTechVia [V {VIA89}]]
$e newPath $emj120 FIXED [RL M9]
set emch146 [$e addPoint 771120 1099440]
$e newPath $emj121 FIXED [RL M9]
set emj138 [$e addTechVia [V {VIA89}]]
$e newPath $emj121 FIXED [RL M9]
set emj139 [$e addPoint 771120 1215000]
$e newPath $emj122 FIXED [RL M8]
set emj140 [$e addPoint 2425680 403920]
$e newPath $emj122 FIXED [RL M8]
set emj141 [$e addTechVia [V {VIA89}]]
$e newPath $emj123 FIXED [RL M9]
set emch151 [$e addPoint 1799280 136080]
$e newPath $emj123 FIXED [RL M9]
set emj142 [$e addPoint 1799280 405000]
$e newPath $emj125 FIXED [RL M8]
set emch153 [$e addPoint 1285200 943920]
$e newPath $emj125 FIXED [RL M8]
set emj143 [$e addTechVia [V {VIA89}]]
$e newPath $emj126 FIXED [RL M9]
set emj144 [$e addPoint 978480 944010]
$e newPath $emj127 FIXED [RL M8]
set emj145 [$e addPoint 771120 1216080]
$e newPath $emj127 FIXED [RL M8]
set emj146 [$e addTechVia [V {VIA89}]]
$e newPath $emj128 FIXED [RL M9]
set emj147 [$e addPoint 317520 1212660]
$e newPath $emj130 FIXED [RL M9]
set emj148 [$e addTechVia [V {VIA89}]]
$e newPath $emj130 FIXED [RL M9]
set emj149 [$e addPoint 257040 1487295]
$e newPath $emj131 FIXED [RL M8]
set emj150 [$e addPoint 2425680 136080]
$e newPath $emj131 FIXED [RL M8]
set emj151 [$e addTechVia [V {VIA89}]]
$e newPath $emj132 FIXED [RL M9]
set emj152 [$e addPoint 1799280 135000]
$e newPath $emj134 FIXED [RL M8]
set emj153 [$e addPoint 1799280 676080]
$e newPath $emj134 FIXED [RL M8]
set emj154 [$e addTechVia [V {VIA89}]]
$e newPath $emj135 FIXED [RL M8]
set emj155 [$e addPoint 1626480 943920]
$e newPath $emj136 FIXED [RL M9]
set emj156 [$e addPoint 1285200 1072530]
$e newPath $emj137 FIXED [RL M9]
set emj157 [$e addPoint 978480 676170]
$e newPath $emj139 FIXED [RL M9]
set emj158 [$e addPoint 771120 1216080]
$e newPath $emj140 FIXED [RL M8]
set emj159 [$e addPoint 2823120 403920]
$e newPath $emj140 FIXED [RL M8]
set emj160 [$e addTechVia [V {VIA89}]]
$e newPath $emj141 FIXED [RL M9]
set emch172 [$e addPoint 2309040 136080]
$e newPath $emj141 FIXED [RL M9]
set emj161 [$e addPoint 2309040 405000]
$e newPath $emj142 FIXED [RL M9]
set emj162 [$e addPoint 1799280 675000]
$e newPath $emj143 FIXED [RL M9]
set emj163 [$e addPoint 1250640 955980]
$e newPath $emj145 FIXED [RL M8]
set emj164 [$e addPoint 1250640 1216080]
$e newPath $emj145 FIXED [RL M8]
set emch177 [$e addTechVia [V {VIA89}]]
$e newPath $emj146 FIXED [RL M9]
set emj165 [$e addPoint 762480 1126260]
$e newPath $emj148 FIXED [RL M8]
set emj166 [$e addPoint 83472 1483920]
$e newPath $emj148 FIXED [RL M8]
set emj167 [$e addPoint 386640 1483920]
$e newPath $emj149 FIXED [RL M9]
set emj168 [$e addPoint 257040 1487340]
$e newPath $emj149 FIXED [RL M9]
set emj169 [$e addPoint 257040 1488240]
$e newPath $emj150 FIXED [RL M8]
set emj170 [$e addPoint 2426272 136080]
$e newPath $emj150 FIXED [RL M8]
set emj171 [$e addTechVia [V {VIA89}]]
$e newPath $emj151 FIXED [RL M9]
set emj172 [$e addPoint 2309040 135000]
$e newPath $emj152 FIXED [RL M9]
set emj173 [$e addPoint 1799280 15056]
$e newPath $emj153 FIXED [RL M8]
set emj174 [$e addPoint 1816560 676080]
$e newPath $emj153 FIXED [RL M8]
set emj175 [$e addTechVia [V {VIA89}]]
$e newPath $emj154 FIXED [RL M9]
set emj176 [$e addPoint 1298160 754740]
$e newPath $emj155 FIXED [RL M8]
set emj177 [$e addPoint 1626976 943920]
$e newPath $emj155 FIXED [RL M8]
set emj178 [$e addTechVia [V {VIA89}]]
$e newPath $emj156 FIXED [RL M9]
set emj179 [$e addPoint 1285200 1072544]
$e newPath $emj156 FIXED [RL M9]
set emj180 [$e addPoint 1285200 1073520]
$e newPath $emj158 FIXED [RL M9]
set emj181 [$e addPoint 771120 1483920]
$e newPath $emj159 FIXED [RL M8]
set emj182 [$e addPoint 2831760 403920]
$e newPath $emj159 FIXED [RL M8]
set emj183 [$e addTechVia [V {VIA89}]]
$e newPath $emj160 FIXED [RL M9]
set emj184 [$e addPoint 2425680 407340]
$e newPath $emj161 FIXED [RL M9]
set emj185 [$e addPoint 2309040 675000]
$e newPath $emj162 FIXED [RL M9]
set emch199 [$e addPoint 1799280 676080]
$e newPath $emj164 FIXED [RL M8]
set emj186 [$e addPoint 1285200 1216080]
$e newPath $emj164 FIXED [RL M8]
set emj187 [$e addTechVia [V {VIA89}]]
$e newPath $emj167 FIXED [RL M8]
set emj188 [$e addPoint 388192 1483920]
$e newPath $emj167 FIXED [RL M8]
set emj189 [$e addTechVia [V {VIA89}]]
$e newPath $emj168 FIXED [RL M9]
set emch204 [$e addPoint 257040 1488240]
$e newPath $emj169 FIXED [RL M9]
set emj190 [$e addTechVia [V {VIA89}]]
$e newPath $emj169 FIXED [RL M9]
set emj191 [$e addPoint 257040 1755000]
$e newPath $emj170 FIXED [RL M8]
set emj192 [$e addPoint 2503440 136080]
$e newPath $emj171 FIXED [RL M9]
set emj193 [$e addPoint 2425680 132660]
$e newPath $emj171 FIXED [RL M9]
set emj194 [$e addPoint 2425680 136170]
$e newPath $emj172 FIXED [RL M9]
set emj195 [$e addPoint 2309040 15056]
$e newPath $emj174 FIXED [RL M8]
set emj196 [$e addPoint 2309040 676080]
$e newPath $emj174 FIXED [RL M8]
set emj197 [$e addTechVia [V {VIA89}]]
$e newPath $emj175 FIXED [RL M9]
set emj198 [$e addPoint 1799280 779168]
$e newPath $emj177 FIXED [RL M8]
set emj199 [$e addPoint 1790640 943920]
$e newPath $emj178 FIXED [RL M9]
set emj200 [$e addPoint 1626480 944010]
$e newPath $emj179 FIXED [RL M9]
set emch216 [$e addPoint 1285200 1073520]
$e newPath $emj180 FIXED [RL M9]
set emj201 [$e addTechVia [V {VIA89}]]
$e newPath $emj180 FIXED [RL M9]
set emj202 [$e addPoint 1285200 1215000]
$e newPath $emj181 FIXED [RL M9]
set emj203 [$e addTechVia [V {VIA89}]]
$e newPath $emj181 FIXED [RL M9]
set emj204 [$e addPoint 771120 1485000]
$e newPath $emj181 FIXED [RL M9]
set emj205 [$e addPoint 771120 1782900]
$e newPath $emj182 FIXED [RL M8]
set emj206 [$e addPoint 3337200 403920]
$e newPath $emj182 FIXED [RL M8]
set emj207 [$e addTechVia [V {VIA89}]]
$e newPath $emj183 FIXED [RL M9]
set emj208 [$e addPoint 2823120 136080]
$e newPath $emj183 FIXED [RL M9]
set emj209 [$e addPoint 2823120 405000]
$e newPath $emj185 FIXED [RL M9]
set emj210 [$e addPoint 2309040 676080]
$e newPath $emj186 FIXED [RL M8]
set emj211 [$e addPoint 1799280 1216080]
$e newPath $emj186 FIXED [RL M8]
set emj212 [$e addTechVia [V {VIA89}]]
$e newPath $emj187 FIXED [RL M9]
set emj213 [$e addPoint 1250640 1224900]
$e newPath $emj188 FIXED [RL M8]
set emch230 [$e addPoint 771120 1483920]
$e newPath $emj189 FIXED [RL M9]
set emj214 [$e addPoint 386640 1484010]
$e newPath $emj191 FIXED [RL M9]
set emj215 [$e addPoint 257040 1756080]
$e newPath $emj192 FIXED [RL M8]
set emj216 [$e addPoint 2504352 136080]
$e newPath $emj192 FIXED [RL M8]
set emj217 [$e addTechVia [V {VIA89}]]
$e newPath $emj196 FIXED [RL M8]
set emj218 [$e addPoint 2326320 676080]
$e newPath $emj196 FIXED [RL M8]
set emch236 [$e addTechVia [V {VIA89}]]
$e newPath $emj197 FIXED [RL M9]
set emj219 [$e addPoint 1816560 774540]
$e newPath $emj198 FIXED [RL M9]
set emj220 [$e addPoint 1799280 779310]
$e newPath $emj198 FIXED [RL M9]
set emj221 [$e addPoint 1799280 779760]
$e newPath $emj199 FIXED [RL M8]
set emj222 [$e addPoint 1799280 943920]
$e newPath $emj199 FIXED [RL M8]
set emj223 [$e addTechVia [V {VIA89}]]
$e newPath $emj202 FIXED [RL M9]
set emch242 [$e addPoint 1285200 1216080]
$e newPath $emj203 FIXED [RL M8]
set emj224 [$e addPoint 1250640 1483920]
$e newPath $emj204 FIXED [RL M9]
set emj225 [$e addPoint 771120 1755000]
$e newPath $emj205 FIXED [RL M9]
set emj226 [$e addPoint 771120 1756080]
$e newPath $emj205 FIXED [RL M9]
set emj227 [$e addPoint 771120 1788896]
$e newPath $emj206 FIXED [RL M8]
set emj228 [$e addPoint 3341520 403920]
$e newPath $emj206 FIXED [RL M8]
set emj229 [$e addTechVia [V {VIA89}]]
$e newPath $emj207 FIXED [RL M9]
set emj230 [$e addPoint 2831760 428940]
$e newPath $emj208 FIXED [RL M9]
set emj231 [$e addTechVia [V {VIA89}]]
$e newPath $emj208 FIXED [RL M9]
set emj232 [$e addPoint 2823120 135000]
$e newPath $emj209 FIXED [RL M9]
set emj233 [$e addPoint 2823120 589088]
$e newPath $emj210 FIXED [RL M9]
set emj234 [$e addPoint 2309040 779168]
$e newPath $emj211 FIXED [RL M8]
set emj235 [$e addPoint 2309040 1216080]
$e newPath $emj211 FIXED [RL M8]
set emj236 [$e addTechVia [V {VIA89}]]
$e newPath $emj212 FIXED [RL M9]
set emj237 [$e addPoint 1285200 1374560]
$e newPath $emj215 FIXED [RL M9]
set emj238 [$e addTechVia [V {VIA89}]]
$e newPath $emj215 FIXED [RL M9]
set emj239 [$e addPoint 257040 1790640]
$e newPath $emj216 FIXED [RL M8]
set emch259 [$e addPoint 2823120 136080]
$e newPath $emj217 FIXED [RL M9]
set emj240 [$e addPoint 2503440 136170]
$e newPath $emj218 FIXED [RL M8]
set emj241 [$e addPoint 2542320 676080]
$e newPath $emj218 FIXED [RL M8]
set emj242 [$e addTechVia [V {VIA89}]]
$e newPath $emj220 FIXED [RL M9]
set emch263 [$e addPoint 1799280 779760]
$e newPath $emj221 FIXED [RL M9]
set emj243 [$e addTechVia [V {VIA89}]]
$e newPath $emj221 FIXED [RL M9]
set emj244 [$e addPoint 1799280 943920]
$e newPath $emj222 FIXED [RL M8]
set emj245 [$e addPoint 2309040 943920]
$e newPath $emj222 FIXED [RL M8]
set emch267 [$e addTechVia [V {VIA89}]]
$e newPath $emj223 FIXED [RL M9]
set emj246 [$e addPoint 1790640 832500]
$e newPath $emj224 FIXED [RL M8]
set emj247 [$e addPoint 1285200 1483920]
$e newPath $emj224 FIXED [RL M8]
set emj248 [$e addTechVia [V {VIA89}]]
$e newPath $emj225 FIXED [RL M9]
set emch271 [$e addPoint 771120 1756080]
$e newPath $emj226 FIXED [RL M9]
set emj249 [$e addTechVia [V {VIA89}]]
$e newPath $emj227 FIXED [RL M9]
set emj250 [$e addPoint 771120 1789110]
$e newPath $emj227 FIXED [RL M9]
set emj251 [$e addPoint 771120 1790640]
$e newPath $emj228 FIXED [RL M8]
set emj252 [$e addPoint 3834000 403920]
$e newPath $emj228 FIXED [RL M8]
set emj253 [$e addTechVia [V {VIA89}]]
$e newPath $emj229 FIXED [RL M9]
set emj254 [$e addPoint 3337200 136080]
$e newPath $emj229 FIXED [RL M9]
set emj255 [$e addPoint 3337200 405000]
$e newPath $emj231 FIXED [RL M8]
set emj256 [$e addPoint 2883600 136080]
$e newPath $emj232 FIXED [RL M9]
set emj257 [$e addPoint 2823120 15056]
$e newPath $emj233 FIXED [RL M9]
set emj258 [$e addPoint 2823120 589230]
$e newPath $emj233 FIXED [RL M9]
set emj259 [$e addPoint 2823120 589680]
$e newPath $emj234 FIXED [RL M9]
set emj260 [$e addPoint 2309040 779310]
$e newPath $emj234 FIXED [RL M9]
set emj261 [$e addPoint 2309040 779760]
$e newPath $emj235 FIXED [RL M8]
set emj262 [$e addPoint 2317680 1216080]
$e newPath $emj235 FIXED [RL M8]
set emj263 [$e addTechVia [V {VIA89}]]
$e newPath $emj236 FIXED [RL M9]
set emj264 [$e addPoint 1799280 1215000]
$e newPath $emj236 FIXED [RL M9]
set emj265 [$e addPoint 1799280 1358640]
$e newPath $emj236 FIXED [RL M9]
set emj266 [$e addPoint 1799280 1362060]
$e newPath $emj237 FIXED [RL M9]
set emj267 [$e addPoint 1285200 1374750]
$e newPath $emj237 FIXED [RL M9]
set emj268 [$e addPoint 1285200 1375920]
$e newPath $emj238 FIXED [RL M8]
set emj269 [$e addPoint 83472 1756080]
$e newPath $emj238 FIXED [RL M8]
set emj270 [$e addPoint 261360 1756080]
$e newPath $emj239 FIXED [RL M9]
set emj271 [$e addTechVia [V {VIA89}]]
$e newPath $emj239 FIXED [RL M9]
set emj272 [$e addPoint 257040 1791136]
$e newPath $emj239 FIXED [RL M9]
set emj273 [$e addPoint 257040 1791270]
$e newPath $emj241 FIXED [RL M8]
set emj274 [$e addPoint 2543264 676080]
$e newPath $emj241 FIXED [RL M8]
set emj275 [$e addTechVia [V {VIA89}]]
$e newPath $emj242 FIXED [RL M9]
set emj276 [$e addPoint 2326320 774540]
$e newPath $emj244 FIXED [RL M9]
set emj277 [$e addPoint 1799280 945000]
$e newPath $emj245 FIXED [RL M8]
set emj278 [$e addPoint 2326320 943920]
$e newPath $emj245 FIXED [RL M8]
set emj279 [$e addTechVia [V {VIA89}]]
$e newPath $emj247 FIXED [RL M8]
set emj280 [$e addPoint 1777680 1483920]
$e newPath $emj247 FIXED [RL M8]
set emj281 [$e addTechVia [V {VIA89}]]
$e newPath $emj248 FIXED [RL M9]
set emj282 [$e addPoint 1250640 1495980]
$e newPath $emj249 FIXED [RL M8]
set emch306 [$e addPoint 261360 1756080]
$e newPath $emj249 FIXED [RL M8]
set emj283 [$e addPoint 775440 1756080]
$e newPath $emj250 FIXED [RL M9]
set emch308 [$e addPoint 771120 1790640]
$e newPath $emj251 FIXED [RL M9]
set emj284 [$e addTechVia [V {VIA89}]]
$e newPath $emj251 FIXED [RL M9]
set emj285 [$e addPoint 771120 2023920]
$e newPath $emj252 FIXED [RL M8]
set emj286 [$e addPoint 3851280 403920]
$e newPath $emj252 FIXED [RL M8]
set emj287 [$e addTechVia [V {VIA89}]]
$e newPath $emj253 FIXED [RL M9]
set emj288 [$e addPoint 3341520 409140]
$e newPath $emj254 FIXED [RL M9]
set emj289 [$e addTechVia [V {VIA89}]]
$e newPath $emj254 FIXED [RL M9]
set emj290 [$e addPoint 3337200 135000]
$e newPath $emj255 FIXED [RL M9]
set emj291 [$e addPoint 3337200 563760]
$e newPath $emj256 FIXED [RL M8]
set emj292 [$e addPoint 2934496 136080]
$e newPath $emj256 FIXED [RL M8]
set emj293 [$e addTechVia [V {VIA89}]]
$e newPath $emj258 FIXED [RL M9]
set emch319 [$e addPoint 2823120 589680]
$e newPath $emj259 FIXED [RL M9]
set emj294 [$e addTechVia [V {VIA89}]]
$e newPath $emj259 FIXED [RL M9]
set emj295 [$e addPoint 2823120 671760]
$e newPath $emj260 FIXED [RL M9]
set emch322 [$e addPoint 2309040 779760]
$e newPath $emj261 FIXED [RL M9]
set emj296 [$e addTechVia [V {VIA89}]]
$e newPath $emj261 FIXED [RL M9]
set emj297 [$e addPoint 2309040 827280]
$e newPath $emj262 FIXED [RL M8]
set emj298 [$e addPoint 2823120 1216080]
$e newPath $emj262 FIXED [RL M8]
set emj299 [$e addTechVia [V {VIA89}]]
$e newPath $emj263 FIXED [RL M9]
set emj300 [$e addPoint 2309040 1215000]
$e newPath $emj263 FIXED [RL M9]
set emj301 [$e addPoint 2309040 1326544]
$e newPath $emj264 FIXED [RL M9]
set emch329 [$e addPoint 1799280 945000]
$e newPath $emj265 FIXED [RL M9]
set emj302 [$e addTechVia [V {VIA89}]]
$e newPath $emj265 FIXED [RL M9]
set emj303 [$e addPoint 1799280 1360560]
$e newPath $emj265 FIXED [RL M9]
set emj304 [$e addPoint 1799280 1360710]
$e newPath $emj266 FIXED [RL M9]
set emch333 [$e addPoint 1799280 1360710]
$e newPath $emj266 FIXED [RL M9]
set emj305 [$e addPoint 1799280 1483920]
$e newPath $emj267 FIXED [RL M9]
set emch335 [$e addPoint 1285200 1375920]
$e newPath $emj268 FIXED [RL M9]
set emj306 [$e addTechVia [V {VIA89}]]
$e newPath $emj268 FIXED [RL M9]
set emch337 [$e addPoint 1285200 1483920]
$e newPath $emj270 FIXED [RL M8]
set emj307 [$e addTechVia [V {VIA89}]]
$e newPath $emj272 FIXED [RL M9]
set emch339 [$e addPoint 257040 1791270]
$e newPath $emj273 FIXED [RL M9]
set emj308 [$e addPoint 257040 2023920]
$e newPath $emj274 FIXED [RL M8]
set emj309 [$e addPoint 2823120 676080]
$e newPath $emj275 FIXED [RL M9]
set emj310 [$e addPoint 2542320 676170]
$e newPath $emj278 FIXED [RL M8]
set emj311 [$e addPoint 2823120 943920]
$e newPath $emj278 FIXED [RL M8]
set emj312 [$e addTechVia [V {VIA89}]]
$e newPath $emj279 FIXED [RL M9]
set emj313 [$e addPoint 2309040 828450]
$e newPath $emj279 FIXED [RL M9]
set emj314 [$e addPoint 2309040 945000]
$e newPath $emj280 FIXED [RL M8]
set emj315 [$e addPoint 1799280 1483920]
$e newPath $emj280 FIXED [RL M8]
set emj316 [$e addTechVia [V {VIA89}]]
$e newPath $emj281 FIXED [RL M9]
set emj317 [$e addPoint 1285200 1485000]
$e newPath $emj283 FIXED [RL M8]
set emj318 [$e addPoint 1285200 1756080]
$e newPath $emj283 FIXED [RL M8]
set emj319 [$e addTechVia [V {VIA89}]]
$e newPath $emj285 FIXED [RL M9]
set emj320 [$e addTechVia [V {VIA89}]]
$e newPath $emj285 FIXED [RL M9]
set emj321 [$e addPoint 771120 2025000]
$e newPath $emj286 FIXED [RL M8]
set emj322 [$e addPoint 4365360 403920]
$e newPath $emj286 FIXED [RL M8]
set emj323 [$e addTechVia [V {VIA89}]]
$e newPath $emj287 FIXED [RL M9]
set emj324 [$e addPoint 3834000 409140]
$e newPath $emj289 FIXED [RL M8]
set emj325 [$e addPoint 3332880 136080]
$e newPath $emj289 FIXED [RL M8]
set emj326 [$e addPoint 3717024 136080]
$e newPath $emj290 FIXED [RL M9]
set emj327 [$e addPoint 3337200 103590]
$e newPath $emj291 FIXED [RL M9]
set emj328 [$e addTechVia [V {VIA89}]]
$e newPath $emj291 FIXED [RL M9]
set emj329 [$e addPoint 3337200 565088]
$e newPath $emj291 FIXED [RL M9]
set emj330 [$e addPoint 3337200 565290]
$e newPath $emj292 FIXED [RL M8]
set emj331 [$e addPoint 2935440 136080]
$e newPath $emj293 FIXED [RL M9]
set emj332 [$e addPoint 2883600 132660]
$e newPath $emj295 FIXED [RL M9]
set emj333 [$e addTechVia [V {VIA89}]]
$e newPath $emj295 FIXED [RL M9]
set emj334 [$e addPoint 2823120 672660]
$e newPath $emj295 FIXED [RL M9]
set emj335 [$e addPoint 2823120 672705]
$e newPath $emj297 FIXED [RL M9]
set emj336 [$e addTechVia [V {VIA89}]]
$e newPath $emj297 FIXED [RL M9]
set emj337 [$e addPoint 2309040 828448]
$e newPath $emj297 FIXED [RL M9]
set emch370 [$e addPoint 2309040 828450]
$e newPath $emj298 FIXED [RL M8]
set emj338 [$e addPoint 3337200 1216080]
$e newPath $emj298 FIXED [RL M8]
set emj339 [$e addTechVia [V {VIA89}]]
$e newPath $emj299 FIXED [RL M9]
set emj340 [$e addPoint 2317680 1247220]
$e newPath $emj300 FIXED [RL M9]
set emch374 [$e addPoint 2309040 945000]
$e newPath $emj301 FIXED [RL M9]
set emj341 [$e addPoint 2309040 1326690]
$e newPath $emj301 FIXED [RL M9]
set emj342 [$e addPoint 2309040 1328400]
$e newPath $emj303 FIXED [RL M9]
set emch377 [$e addPoint 1799280 1360710]
$e newPath $emj305 FIXED [RL M9]
set emch378 [$e addTechVia [V {VIA89}]]
$e newPath $emj305 FIXED [RL M9]
set emj343 [$e addPoint 1799280 1485000]
$e newPath $emj307 FIXED [RL M9]
set emj344 [$e addPoint 261360 1785420]
$e newPath $emj308 FIXED [RL M9]
set emj345 [$e addTechVia [V {VIA89}]]
$e newPath $emj308 FIXED [RL M9]
set emj346 [$e addPoint 257040 2025000]
$e newPath $emj309 FIXED [RL M8]
set emj347 [$e addPoint 3337200 676080]
$e newPath $emj309 FIXED [RL M8]
set emj348 [$e addTechVia [V {VIA89}]]
$e newPath $emj311 FIXED [RL M8]
set emj349 [$e addPoint 3281040 943920]
$e newPath $emj311 FIXED [RL M8]
set emj350 [$e addTechVia [V {VIA89}]]
$e newPath $emj312 FIXED [RL M9]
set emj351 [$e addPoint 2326320 845460]
$e newPath $emj313 FIXED [RL M9]
set emch388 [$e addPoint 2309040 828448]
$e newPath $emj315 FIXED [RL M8]
set emj352 [$e addPoint 2151968 1483920]
$e newPath $emj316 FIXED [RL M9]
set emj353 [$e addPoint 1777680 1489140]
$e newPath $emj317 FIXED [RL M9]
set emj354 [$e addPoint 1285200 1755000]
$e newPath $emj318 FIXED [RL M8]
set emj355 [$e addPoint 1293840 1756080]
$e newPath $emj318 FIXED [RL M8]
set emj356 [$e addTechVia [V {VIA89}]]
$e newPath $emj319 FIXED [RL M9]
set emj357 [$e addPoint 775440 1782900]
$e newPath $emj320 FIXED [RL M8]
set emch395 [$e addPoint 257040 2023920]
$e newPath $emj320 FIXED [RL M8]
set emj358 [$e addPoint 822960 2023920]
$e newPath $emj321 FIXED [RL M9]
set emj359 [$e addPoint 771120 2295000]
$e newPath $emj322 FIXED [RL M8]
set emj360 [$e addPoint 4879440 403920]
$e newPath $emj322 FIXED [RL M8]
set emj361 [$e addTechVia [V {VIA89}]]
$e newPath $emj323 FIXED [RL M9]
set emj362 [$e addPoint 3851280 136080]
$e newPath $emj323 FIXED [RL M9]
set emj363 [$e addPoint 3851280 405000]
$e newPath $emj325 FIXED [RL M8]
set emch402 [$e addPoint 2935440 136080]
$e newPath $emj325 FIXED [RL M8]
set emj364 [$e addTechVia [V {VIA89}]]
$e newPath $emj326 FIXED [RL M8]
set emj365 [$e addPoint 3717360 136080]
$e newPath $emj327 FIXED [RL M9]
set emj366 [$e addPoint 3337200 101520]
$e newPath $emj327 FIXED [RL M9]
set emj367 [$e addPoint 3337200 103456]
$e newPath $emj329 FIXED [RL M9]
set emch407 [$e addPoint 3337200 565290]
$e newPath $emj330 FIXED [RL M9]
set emj368 [$e addPoint 3337200 671760]
$e newPath $emj331 FIXED [RL M8]
set emj369 [$e addTechVia [V {VIA89}]]
$e newPath $emj334 FIXED [RL M9]
set emch410 [$e addPoint 2823120 672705]
$e newPath $emj335 FIXED [RL M9]
set emch411 [$e addPoint 2823120 676080]
$e newPath $emj338 FIXED [RL M8]
set emj370 [$e addPoint 3341520 1216080]
$e newPath $emj338 FIXED [RL M8]
set emj371 [$e addTechVia [V {VIA89}]]
$e newPath $emj339 FIXED [RL M9]
set emj372 [$e addPoint 2823120 1212705]
$e newPath $emj339 FIXED [RL M9]
set emj373 [$e addPoint 2823120 1319760]
$e newPath $emj341 FIXED [RL M9]
set emch416 [$e addPoint 2309040 1328400]
$e newPath $emj342 FIXED [RL M9]
set emj374 [$e addTechVia [V {VIA89}]]
$e newPath $emj342 FIXED [RL M9]
set emj375 [$e addPoint 2309040 1483920]
$e newPath $emj343 FIXED [RL M9]
set emj376 [$e addPoint 1799280 1755000]
$e newPath $emj345 FIXED [RL M8]
set emj377 [$e addPoint 239760 2023920]
$e newPath $emj346 FIXED [RL M9]
set emj378 [$e addPoint 257040 2295000]
$e newPath $emj347 FIXED [RL M8]
set emj379 [$e addPoint 3829680 676080]
$e newPath $emj347 FIXED [RL M8]
set emj380 [$e addTechVia [V {VIA89}]]
$e newPath $emj348 FIXED [RL M9]
set emj381 [$e addPoint 2823120 922320]
$e newPath $emj349 FIXED [RL M8]
set emj382 [$e addPoint 3282592 943920]
$e newPath $emj349 FIXED [RL M8]
set emj383 [$e addTechVia [V {VIA89}]]
$e newPath $emj350 FIXED [RL M9]
set emj384 [$e addPoint 2823120 930060]
$e newPath $emj350 FIXED [RL M9]
set emj385 [$e addPoint 2823120 945000]
$e newPath $emj352 FIXED [RL M8]
set emj386 [$e addPoint 2153520 1483920]
$e newPath $emj354 FIXED [RL M9]
set emch430 [$e addPoint 1285200 1756080]
$e newPath $emj355 FIXED [RL M8]
set emj387 [$e addPoint 1682640 1756080]
$e newPath $emj355 FIXED [RL M8]
set emj388 [$e addTechVia [V {VIA89}]]
$e newPath $emj356 FIXED [RL M9]
set emj389 [$e addPoint 1285200 1790640]
$e newPath $emj358 FIXED [RL M8]
set emj390 [$e addPoint 1267920 2023920]
$e newPath $emj358 FIXED [RL M8]
set emj391 [$e addTechVia [V {VIA89}]]
$e newPath $emj359 FIXED [RL M9]
set emj392 [$e addPoint 771120 2296080]
$e newPath $emj360 FIXED [RL M8]
set emj393 [$e addPoint 5393520 403920]
$e newPath $emj360 FIXED [RL M8]
set emj394 [$e addTechVia [V {VIA89}]]
$e newPath $emj361 FIXED [RL M9]
set emj395 [$e addPoint 4365360 136080]
$e newPath $emj361 FIXED [RL M9]
set emj396 [$e addPoint 4365360 407295]
$e newPath $emj362 FIXED [RL M9]
set emj397 [$e addTechVia [V {VIA89}]]
$e newPath $emj362 FIXED [RL M9]
set emj398 [$e addPoint 3851280 132705]
$e newPath $emj363 FIXED [RL M9]
set emj399 [$e addPoint 3851280 675000]
$e newPath $emj364 FIXED [RL M9]
set emj400 [$e addPoint 3332880 109260]
$e newPath $emj365 FIXED [RL M8]
set emch445 [$e addPoint 3851280 136080]
$e newPath $emj365 FIXED [RL M8]
set emj401 [$e addTechVia [V {VIA89}]]
$e newPath $emj366 FIXED [RL M9]
set emj402 [$e addTechVia [V {VIA89}]]
$e newPath $emj366 FIXED [RL M9]
set emj403 [$e addPoint 3337200 15056]
$e newPath $emj366 FIXED [RL M9]
set emch449 [$e addPoint 3337200 103456]
$e newPath $emj368 FIXED [RL M9]
set emj404 [$e addTechVia [V {VIA89}]]
$e newPath $emj368 FIXED [RL M9]
set emj405 [$e addPoint 3337200 672660]
$e newPath $emj368 FIXED [RL M9]
set emj406 [$e addPoint 3337200 672705]
$e newPath $emj369 FIXED [RL M9]
set emj407 [$e addPoint 2935440 136170]
$e newPath $emj370 FIXED [RL M8]
set emj408 [$e addPoint 3851280 1216080]
$e newPath $emj370 FIXED [RL M8]
set emj409 [$e addTechVia [V {VIA89}]]
$e newPath $emj371 FIXED [RL M9]
set emj410 [$e addPoint 3337200 1215000]
$e newPath $emj371 FIXED [RL M9]
set emj411 [$e addPoint 3337200 1374560]
$e newPath $emj372 FIXED [RL M9]
set emj412 [$e addPoint 2823120 1211760]
$e newPath $emj372 FIXED [RL M9]
set emj413 [$e addPoint 2823120 1212660]
$e newPath $emj373 FIXED [RL M9]
set emj414 [$e addTechVia [V {VIA89}]]
$e newPath $emj373 FIXED [RL M9]
set emj415 [$e addPoint 2823120 1320544]
$e newPath $emj373 FIXED [RL M9]
set emj416 [$e addPoint 2823120 1320750]
$e newPath $emj375 FIXED [RL M9]
set emj417 [$e addTechVia [V {VIA89}]]
$e newPath $emj375 FIXED [RL M9]
set emj418 [$e addPoint 2309040 1485000]
$e newPath $emj376 FIXED [RL M9]
set emj419 [$e addPoint 1799280 1756080]
$e newPath $emj377 FIXED [RL M8]
set emj420 [$e addPoint 83472 2023920]
$e newPath $emj377 FIXED [RL M8]
set emj421 [$e addTechVia [V {VIA89}]]
$e newPath $emj378 FIXED [RL M9]
set emj422 [$e addPoint 257040 2296080]
$e newPath $emj379 FIXED [RL M8]
set emj423 [$e addPoint 3831984 676080]
$e newPath $emj379 FIXED [RL M8]
set emj424 [$e addTechVia [V {VIA89}]]
$e newPath $emj380 FIXED [RL M9]
set emch471 [$e addPoint 3337200 672705]
$e newPath $emj380 FIXED [RL M9]
set emj425 [$e addPoint 3337200 943920]
$e newPath $emj381 FIXED [RL M9]
set emj426 [$e addTechVia [V {VIA89}]]
$e newPath $emj381 FIXED [RL M9]
set emj427 [$e addPoint 2823120 923488]
$e newPath $emj381 FIXED [RL M9]
set emj428 [$e addPoint 2823120 923490]
$e newPath $emj382 FIXED [RL M8]
set emj429 [$e addPoint 3289680 943920]
$e newPath $emj383 FIXED [RL M9]
set emj430 [$e addPoint 3281040 944010]
$e newPath $emj384 FIXED [RL M9]
set emch478 [$e addPoint 2823120 923490]
$e newPath $emj385 FIXED [RL M9]
set emch479 [$e addPoint 2823120 1211760]
$e newPath $emj386 FIXED [RL M8]
set emch480 [$e addPoint 2309040 1483920]
$e newPath $emj386 FIXED [RL M8]
set emj431 [$e addTechVia [V {VIA89}]]
$e newPath $emj387 FIXED [RL M8]
set emj432 [$e addPoint 1682976 1756080]
$e newPath $emj387 FIXED [RL M8]
set emj433 [$e addTechVia [V {VIA89}]]
$e newPath $emj388 FIXED [RL M9]
set emj434 [$e addPoint 1293840 1790460]
$e newPath $emj389 FIXED [RL M9]
set emj435 [$e addTechVia [V {VIA89}]]
$e newPath $emj389 FIXED [RL M9]
set emj436 [$e addPoint 1285200 1791264]
$e newPath $emj389 FIXED [RL M9]
set emj437 [$e addPoint 1285200 1791270]
$e newPath $emj390 FIXED [RL M8]
set emj438 [$e addPoint 1285200 2023920]
$e newPath $emj390 FIXED [RL M8]
set emj439 [$e addTechVia [V {VIA89}]]
$e newPath $emj391 FIXED [RL M9]
set emj440 [$e addPoint 822960 2027340]
$e newPath $emj392 FIXED [RL M9]
set emj441 [$e addTechVia [V {VIA89}]]
$e newPath $emj392 FIXED [RL M9]
set emj442 [$e addPoint 771120 2563920]
$e newPath $emj393 FIXED [RL M8]
set emj443 [$e addPoint 5397840 403920]
$e newPath $emj393 FIXED [RL M8]
set emj444 [$e addTechVia [V {VIA89}]]
$e newPath $emj394 FIXED [RL M9]
set emj445 [$e addPoint 4879440 196560]
$e newPath $emj394 FIXED [RL M9]
set emj446 [$e addPoint 4879440 407295]
$e newPath $emj395 FIXED [RL M9]
set emj447 [$e addTechVia [V {VIA89}]]
$e newPath $emj395 FIXED [RL M9]
set emj448 [$e addPoint 4365360 135000]
$e newPath $emj396 FIXED [RL M9]
set emj449 [$e addPoint 4365360 407340]
$e newPath $emj396 FIXED [RL M9]
set emj450 [$e addPoint 4365360 408240]
$e newPath $emj397 FIXED [RL M8]
set emj451 [$e addPoint 4106160 136080]
$e newPath $emj398 FIXED [RL M9]
set emj452 [$e addPoint 3851280 131760]
$e newPath $emj398 FIXED [RL M9]
set emj453 [$e addPoint 3851280 132660]
$e newPath $emj399 FIXED [RL M9]
set emj454 [$e addPoint 3851280 676080]
$e newPath $emj401 FIXED [RL M9]
set emj455 [$e addPoint 3717360 136170]
$e newPath $emj405 FIXED [RL M9]
set emch506 [$e addPoint 3337200 672705]
$e newPath $emj408 FIXED [RL M8]
set emj456 [$e addPoint 3920400 1216080]
$e newPath $emj408 FIXED [RL M8]
set emj457 [$e addTechVia [V {VIA89}]]
$e newPath $emj409 FIXED [RL M9]
set emj458 [$e addPoint 3341520 1246680]
$e newPath $emj410 FIXED [RL M9]
set emj459 [$e addPoint 3337200 945000]
$e newPath $emj411 FIXED [RL M9]
set emj460 [$e addPoint 3337200 1374750]
$e newPath $emj411 FIXED [RL M9]
set emj461 [$e addPoint 3337200 1375920]
$e newPath $emj412 FIXED [RL M9]
set emj462 [$e addTechVia [V {VIA89}]]
$e newPath $emj412 FIXED [RL M9]
set emch514 [$e addPoint 2823120 1212660]
$e newPath $emj415 FIXED [RL M9]
set emch515 [$e addPoint 2823120 1320750]
$e newPath $emj416 FIXED [RL M9]
set emj463 [$e addPoint 2823120 1483920]
$e newPath $emj417 FIXED [RL M8]
set emj464 [$e addPoint 2313360 1483920]
$e newPath $emj418 FIXED [RL M9]
set emj465 [$e addPoint 2309040 1755000]
$e newPath $emj419 FIXED [RL M9]
set emj466 [$e addTechVia [V {VIA89}]]
$e newPath $emj419 FIXED [RL M9]
set emj467 [$e addPoint 1799280 2023920]
$e newPath $emj421 FIXED [RL M9]
set emj468 [$e addPoint 239760 2029140]
$e newPath $emj422 FIXED [RL M9]
set emj469 [$e addTechVia [V {VIA89}]]
$e newPath $emj422 FIXED [RL M9]
set emj470 [$e addPoint 257040 2563920]
$e newPath $emj423 FIXED [RL M8]
set emj471 [$e addPoint 3851280 676080]
$e newPath $emj424 FIXED [RL M9]
set emj472 [$e addPoint 3829680 676170]
$e newPath $emj425 FIXED [RL M9]
set emj473 [$e addTechVia [V {VIA89}]]
$e newPath $emj425 FIXED [RL M9]
set emch527 [$e addPoint 3337200 945000]
$e newPath $emj427 FIXED [RL M9]
set emch528 [$e addPoint 2823120 923490]
$e newPath $emj429 FIXED [RL M8]
set emch529 [$e addPoint 3337200 943920]
$e newPath $emj429 FIXED [RL M8]
set emj474 [$e addTechVia [V {VIA89}]]
$e newPath $emj431 FIXED [RL M9]
set emj475 [$e addPoint 2153520 1484010]
$e newPath $emj432 FIXED [RL M8]
set emj476 [$e addPoint 1691280 1756080]
$e newPath $emj433 FIXED [RL M9]
set emj477 [$e addPoint 1682640 1756170]
$e newPath $emj436 FIXED [RL M9]
set emch534 [$e addPoint 1285200 1791270]
$e newPath $emj437 FIXED [RL M9]
set emj478 [$e addPoint 1285200 2023920]
$e newPath $emj438 FIXED [RL M8]
set emj479 [$e addPoint 1799280 2023920]
$e newPath $emj438 FIXED [RL M8]
set emch537 [$e addTechVia [V {VIA89}]]
$e newPath $emj439 FIXED [RL M9]
set emj480 [$e addPoint 1267920 1808820]
$e newPath $emj441 FIXED [RL M8]
set emch539 [$e addPoint 257040 2296080]
$e newPath $emj441 FIXED [RL M8]
set emj481 [$e addPoint 822960 2296080]
$e newPath $emj442 FIXED [RL M9]
set emj482 [$e addTechVia [V {VIA89}]]
$e newPath $emj442 FIXED [RL M9]
set emj483 [$e addPoint 771120 2567295]
$e newPath $emj443 FIXED [RL M8]
set emj484 [$e addPoint 5682960 403920]
$e newPath $emj443 FIXED [RL M8]
set emj485 [$e addTechVia [V {VIA89}]]
$e newPath $emj444 FIXED [RL M9]
set emj486 [$e addPoint 5393520 136080]
$e newPath $emj444 FIXED [RL M9]
set emj487 [$e addPoint 5393520 405000]
$e newPath $emj445 FIXED [RL M9]
set emj488 [$e addTechVia [V {VIA89}]]
$e newPath $emj445 FIXED [RL M9]
set emj489 [$e addPoint 4879440 196064]
$e newPath $emj445 FIXED [RL M9]
set emj490 [$e addPoint 4879440 196110]
$e newPath $emj446 FIXED [RL M9]
set emj491 [$e addPoint 4879440 407340]
$e newPath $emj446 FIXED [RL M9]
set emj492 [$e addPoint 4879440 408240]
$e newPath $emj447 FIXED [RL M8]
set emj493 [$e addPoint 4361040 136080]
$e newPath $emj447 FIXED [RL M8]
set emj494 [$e addPoint 4514912 136080]
$e newPath $emj448 FIXED [RL M9]
set emj495 [$e addPoint 4365360 15056]
$e newPath $emj449 FIXED [RL M9]
set emch555 [$e addPoint 4365360 408240]
$e newPath $emj450 FIXED [RL M9]
set emj496 [$e addTechVia [V {VIA89}]]
$e newPath $emj450 FIXED [RL M9]
set emj497 [$e addPoint 4365360 671760]
$e newPath $emj451 FIXED [RL M8]
set emj498 [$e addPoint 4107808 136080]
$e newPath $emj451 FIXED [RL M8]
set emj499 [$e addTechVia [V {VIA89}]]
$e newPath $emj452 FIXED [RL M9]
set emj500 [$e addTechVia [V {VIA89}]]
$e newPath $emj452 FIXED [RL M9]
set emj501 [$e addPoint 3851280 15056]
$e newPath $emj452 FIXED [RL M9]
set emch562 [$e addPoint 3851280 132660]
$e newPath $emj454 FIXED [RL M9]
set emch563 [$e addTechVia [V {VIA89}]]
$e newPath $emj454 FIXED [RL M9]
set emj502 [$e addPoint 3851280 827280]
$e newPath $emj456 FIXED [RL M8]
set emj503 [$e addPoint 4365360 1216080]
$e newPath $emj456 FIXED [RL M8]
set emj504 [$e addTechVia [V {VIA89}]]
$e newPath $emj457 FIXED [RL M9]
set emj505 [$e addPoint 3851280 1215000]
$e newPath $emj457 FIXED [RL M9]
set emj506 [$e addPoint 3851280 1483920]
$e newPath $emj460 FIXED [RL M9]
set emch569 [$e addPoint 3337200 1375920]
$e newPath $emj461 FIXED [RL M9]
set emj507 [$e addTechVia [V {VIA89}]]
$e newPath $emj461 FIXED [RL M9]
set emj508 [$e addPoint 3337200 1483920]
$e newPath $emj463 FIXED [RL M9]
set emj509 [$e addTechVia [V {VIA89}]]
$e newPath $emj463 FIXED [RL M9]
set emj510 [$e addPoint 2823120 1485000]
$e newPath $emj464 FIXED [RL M8]
set emj511 [$e addPoint 2810160 1483920]
$e newPath $emj464 FIXED [RL M8]
set emj512 [$e addTechVia [V {VIA89}]]
$e newPath $emj465 FIXED [RL M9]
set emj513 [$e addPoint 2309040 1756080]
$e newPath $emj466 FIXED [RL M8]
set emch577 [$e addPoint 1691280 1756080]
$e newPath $emj466 FIXED [RL M8]
set emj514 [$e addPoint 2309040 1756080]
$e newPath $emj467 FIXED [RL M9]
set emch579 [$e addTechVia [V {VIA89}]]
$e newPath $emj467 FIXED [RL M9]
set emj515 [$e addPoint 1799280 2025000]
$e newPath $emj469 FIXED [RL M8]
set emj516 [$e addPoint 239760 2296080]
$e newPath $emj470 FIXED [RL M9]
set emj517 [$e addTechVia [V {VIA89}]]
$e newPath $emj470 FIXED [RL M9]
set emj518 [$e addPoint 257040 2567295]
$e newPath $emj471 FIXED [RL M8]
set emj519 [$e addPoint 3855600 676080]
$e newPath $emj473 FIXED [RL M8]
set emj520 [$e addPoint 3851280 943920]
$e newPath $emj474 FIXED [RL M9]
set emj521 [$e addPoint 3289680 949140]
$e newPath $emj476 FIXED [RL M8]
set emj522 [$e addTechVia [V {VIA89}]]
$e newPath $emj478 FIXED [RL M9]
set emj523 [$e addPoint 1285200 2025000]
$e newPath $emj479 FIXED [RL M8]
set emj524 [$e addPoint 1812240 2023920]
$e newPath $emj481 FIXED [RL M8]
set emj525 [$e addPoint 826656 2296080]
$e newPath $emj481 FIXED [RL M8]
set emj526 [$e addTechVia [V {VIA89}]]
$e newPath $emj482 FIXED [RL M8]
set emj527 [$e addPoint 586912 2563920]
$e newPath $emj482 FIXED [RL M8]
set emj528 [$e addPoint 956880 2563920]
$e newPath $emj483 FIXED [RL M9]
set emj529 [$e addPoint 771120 2567340]
$e newPath $emj483 FIXED [RL M9]
set emj530 [$e addPoint 771120 2568240]
$e newPath $emj484 FIXED [RL M8]
set emj531 [$e addPoint 5907600 403920]
$e newPath $emj484 FIXED [RL M8]
set emj532 [$e addTechVia [V {VIA89}]]
$e newPath $emj485 FIXED [RL M9]
set emj533 [$e addPoint 5397840 409140]
$e newPath $emj486 FIXED [RL M9]
set emj534 [$e addTechVia [V {VIA89}]]
$e newPath $emj486 FIXED [RL M9]
set emj535 [$e addPoint 5393520 14220]
$e newPath $emj486 FIXED [RL M9]
set emj536 [$e addPoint 5393520 135000]
$e newPath $emj487 FIXED [RL M9]
set emj537 [$e addPoint 5393520 675000]
$e newPath $emj489 FIXED [RL M9]
set emj538 [$e addPoint 4879440 136080]
$e newPath $emj489 FIXED [RL M9]
set emch604 [$e addPoint 4879440 196110]
$e newPath $emj491 FIXED [RL M9]
set emch605 [$e addPoint 4879440 408240]
$e newPath $emj492 FIXED [RL M9]
set emj539 [$e addTechVia [V {VIA89}]]
$e newPath $emj492 FIXED [RL M9]
set emj540 [$e addPoint 4879440 589088]
$e newPath $emj493 FIXED [RL M8]
set emch608 [$e addPoint 4107808 136080]
$e newPath $emj493 FIXED [RL M8]
set emj541 [$e addTechVia [V {VIA89}]]
$e newPath $emj494 FIXED [RL M8]
set emj542 [$e addPoint 4516560 136080]
$e newPath $emj497 FIXED [RL M9]
set emj543 [$e addTechVia [V {VIA89}]]
$e newPath $emj497 FIXED [RL M9]
set emj544 [$e addPoint 4365360 672660]
$e newPath $emj497 FIXED [RL M9]
set emj545 [$e addPoint 4365360 672705]
$e newPath $emj499 FIXED [RL M9]
set emj546 [$e addPoint 4106160 136170]
$e newPath $emj502 FIXED [RL M9]
set emj547 [$e addTechVia [V {VIA89}]]
$e newPath $emj502 FIXED [RL M9]
set emj548 [$e addPoint 3851280 828448]
$e newPath $emj502 FIXED [RL M9]
set emj549 [$e addPoint 3851280 828450]
$e newPath $emj503 FIXED [RL M8]
set emj550 [$e addPoint 4879440 1216080]
$e newPath $emj503 FIXED [RL M8]
set emj551 [$e addTechVia [V {VIA89}]]
$e newPath $emj504 FIXED [RL M9]
set emj552 [$e addPoint 3920400 1176300]
$e newPath $emj505 FIXED [RL M9]
set emj553 [$e addPoint 3851280 945000]
$e newPath $emj506 FIXED [RL M9]
set emj554 [$e addTechVia [V {VIA89}]]
$e newPath $emj506 FIXED [RL M9]
set emj555 [$e addPoint 3851280 1487295]
$e newPath $emj508 FIXED [RL M9]
set emj556 [$e addTechVia [V {VIA89}]]
$e newPath $emj508 FIXED [RL M9]
set emj557 [$e addPoint 3337200 1487295]
$e newPath $emj509 FIXED [RL M8]
set emch626 [$e addPoint 2810160 1483920]
$e newPath $emj509 FIXED [RL M8]
set emch627 [$e addPoint 3337200 1483920]
$e newPath $emj510 FIXED [RL M9]
set emj558 [$e addPoint 2823120 1755000]
$e newPath $emj511 FIXED [RL M8]
set emj559 [$e addTechVia [V {VIA89}]]
$e newPath $emj512 FIXED [RL M9]
set emj560 [$e addPoint 2313360 1487340]
$e newPath $emj513 FIXED [RL M9]
set emch631 [$e addTechVia [V {VIA89}]]
$e newPath $emj513 FIXED [RL M9]
set emj561 [$e addPoint 2309040 2023920]
$e newPath $emj514 FIXED [RL M8]
set emj562 [$e addPoint 2322000 1756080]
$e newPath $emj515 FIXED [RL M9]
set emj563 [$e addPoint 1799280 2295000]
$e newPath $emj516 FIXED [RL M8]
set emj564 [$e addPoint 196560 2296080]
$e newPath $emj516 FIXED [RL M8]
set emj565 [$e addTechVia [V {VIA89}]]
$e newPath $emj517 FIXED [RL M8]
set emj566 [$e addPoint 196560 2563920]
$e newPath $emj517 FIXED [RL M8]
set emj567 [$e addPoint 585360 2563920]
$e newPath $emj518 FIXED [RL M9]
set emj568 [$e addPoint 257040 2567340]
$e newPath $emj518 FIXED [RL M9]
set emj569 [$e addPoint 257040 2568240]
$e newPath $emj519 FIXED [RL M8]
set emj570 [$e addPoint 4106160 676080]
$e newPath $emj519 FIXED [RL M8]
set emj571 [$e addTechVia [V {VIA89}]]
$e newPath $emj520 FIXED [RL M8]
set emj572 [$e addPoint 3920400 943920]
$e newPath $emj520 FIXED [RL M8]
set emj573 [$e addTechVia [V {VIA89}]]
$e newPath $emj522 FIXED [RL M9]
set emj574 [$e addPoint 1691280 1752660]
$e newPath $emj523 FIXED [RL M9]
set emj575 [$e addPoint 1285200 2295000]
$e newPath $emj524 FIXED [RL M8]
set emj576 [$e addPoint 2151968 2023920]
$e newPath $emj524 FIXED [RL M8]
set emj577 [$e addTechVia [V {VIA89}]]
$e newPath $emj525 FIXED [RL M8]
set emj578 [$e addPoint 827280 2296080]
$e newPath $emj526 FIXED [RL M9]
set emj579 [$e addPoint 822960 2292660]
$e newPath $emj527 FIXED [RL M8]
set emch651 [$e addPoint 585360 2563920]
$e newPath $emj528 FIXED [RL M8]
set emj580 [$e addPoint 958560 2563920]
$e newPath $emj528 FIXED [RL M8]
set emj581 [$e addTechVia [V {VIA89}]]
$e newPath $emj529 FIXED [RL M9]
set emch654 [$e addPoint 771120 2568240]
$e newPath $emj530 FIXED [RL M9]
set emj582 [$e addTechVia [V {VIA89}]]
$e newPath $emj530 FIXED [RL M9]
set emj583 [$e addPoint 771120 2831760]
$e newPath $emj531 FIXED [RL M8]
set emj584 [$e addPoint 6417360 403920]
$e newPath $emj531 FIXED [RL M8]
set emj585 [$e addTechVia [V {VIA89}]]
$e newPath $emj532 FIXED [RL M9]
set emj586 [$e addPoint 5682960 425160]
$e newPath $emj534 FIXED [RL M8]
set emj587 [$e addPoint 5260512 136080]
$e newPath $emj534 FIXED [RL M8]
set emj588 [$e addPoint 5673376 136080]
$e newPath $emj535 FIXED [RL M9]
set emj589 [$e addPoint 5393520 15056]
$e newPath $emj536 FIXED [RL M9]
set emch663 [$e addPoint 5393520 15056]
$e newPath $emj537 FIXED [RL M9]
set emj590 [$e addPoint 5393520 676080]
$e newPath $emj538 FIXED [RL M9]
set emj591 [$e addTechVia [V {VIA89}]]
$e newPath $emj538 FIXED [RL M9]
set emj592 [$e addPoint 4879440 132705]
$e newPath $emj540 FIXED [RL M9]
set emj593 [$e addPoint 4879440 589230]
$e newPath $emj540 FIXED [RL M9]
set emj594 [$e addPoint 4879440 589680]
$e newPath $emj541 FIXED [RL M9]
set emj595 [$e addPoint 4361040 72180]
$e newPath $emj542 FIXED [RL M8]
set emch670 [$e addPoint 4879440 136080]
$e newPath $emj542 FIXED [RL M8]
set emj596 [$e addTechVia [V {VIA89}]]
$e newPath $emj544 FIXED [RL M9]
set emch672 [$e addPoint 4365360 672705]
$e newPath $emj545 FIXED [RL M9]
set emj597 [$e addPoint 4365360 676080]
$e newPath $emj548 FIXED [RL M9]
set emch674 [$e addPoint 3851280 828450]
$e newPath $emj549 FIXED [RL M9]
set emch675 [$e addPoint 3851280 943920]
$e newPath $emj550 FIXED [RL M8]
set emj598 [$e addPoint 5393520 1216080]
$e newPath $emj550 FIXED [RL M8]
set emj599 [$e addTechVia [V {VIA89}]]
$e newPath $emj551 FIXED [RL M9]
set emj600 [$e addPoint 4365360 1212705]
$e newPath $emj551 FIXED [RL M9]
set emj601 [$e addPoint 4365360 1483920]
$e newPath $emj553 FIXED [RL M9]
set emch680 [$e addPoint 3851280 943920]
$e newPath $emj554 FIXED [RL M8]
set emj602 [$e addPoint 3645600 1483920]
$e newPath $emj554 FIXED [RL M8]
set emj603 [$e addPoint 4106160 1483920]
$e newPath $emj555 FIXED [RL M9]
set emj604 [$e addPoint 3851280 1487340]
$e newPath $emj555 FIXED [RL M9]
set emj605 [$e addPoint 3851280 1488240]
$e newPath $emj556 FIXED [RL M8]
set emj606 [$e addPoint 3643920 1483920]
$e newPath $emj557 FIXED [RL M9]
set emj607 [$e addPoint 3337200 1487340]
$e newPath $emj557 FIXED [RL M9]
set emj608 [$e addPoint 3337200 1488240]
$e newPath $emj558 FIXED [RL M9]
set emj609 [$e addPoint 2823120 1756080]
$e newPath $emj559 FIXED [RL M9]
set emj610 [$e addPoint 2810160 1324980]
$e newPath $emj561 FIXED [RL M9]
set emj611 [$e addTechVia [V {VIA89}]]
$e newPath $emj561 FIXED [RL M9]
set emj612 [$e addPoint 2309040 2027295]
$e newPath $emj562 FIXED [RL M8]
set emj613 [$e addPoint 2372944 1756080]
$e newPath $emj562 FIXED [RL M8]
set emj614 [$e addTechVia [V {VIA89}]]
$e newPath $emj563 FIXED [RL M9]
set emj615 [$e addPoint 1799280 2296080]
$e newPath $emj564 FIXED [RL M8]
set emj616 [$e addPoint 195616 2296080]
$e newPath $emj564 FIXED [RL M8]
set emj617 [$e addTechVia [V {VIA89}]]
$e newPath $emj565 FIXED [RL M9]
set emj618 [$e addPoint 239760 2300220]
$e newPath $emj566 FIXED [RL M8]
set emj619 [$e addPoint 195616 2563920]
$e newPath $emj566 FIXED [RL M8]
set emj620 [$e addTechVia [V {VIA89}]]
$e newPath $emj567 FIXED [RL M8]
set emj621 [$e addTechVia [V {VIA89}]]
$e newPath $emj568 FIXED [RL M9]
set emch701 [$e addPoint 257040 2568240]
$e newPath $emj569 FIXED [RL M9]
set emj622 [$e addTechVia [V {VIA89}]]
$e newPath $emj569 FIXED [RL M9]
set emj623 [$e addPoint 257040 2835000]
$e newPath $emj570 FIXED [RL M8]
set emj624 [$e addPoint 4107808 676080]
$e newPath $emj570 FIXED [RL M8]
set emj625 [$e addTechVia [V {VIA89}]]
$e newPath $emj571 FIXED [RL M9]
set emj626 [$e addPoint 3855600 679500]
$e newPath $emj572 FIXED [RL M8]
set emj627 [$e addPoint 4106160 943920]
$e newPath $emj572 FIXED [RL M8]
set emj628 [$e addTechVia [V {VIA89}]]
$e newPath $emj575 FIXED [RL M9]
set emj629 [$e addPoint 1285200 2296080]
$e newPath $emj576 FIXED [RL M8]
set emj630 [$e addPoint 2153520 2023920]
$e newPath $emj577 FIXED [RL M9]
set emj631 [$e addPoint 1812240 2070540]
$e newPath $emj578 FIXED [RL M8]
set emj632 [$e addPoint 835920 2296080]
$e newPath $emj578 FIXED [RL M8]
set emj633 [$e addTechVia [V {VIA89}]]
$e newPath $emj580 FIXED [RL M8]
set emj634 [$e addPoint 1224720 2563920]
$e newPath $emj581 FIXED [RL M9]
set emj635 [$e addPoint 956880 2564010]
$e newPath $emj583 FIXED [RL M9]
set emj636 [$e addTechVia [V {VIA89}]]
$e newPath $emj583 FIXED [RL M9]
set emj637 [$e addPoint 771120 2832660]
$e newPath $emj583 FIXED [RL M9]
set emj638 [$e addPoint 771120 2832705]
$e newPath $emj584 FIXED [RL M8]
set emj639 [$e addPoint 6469200 403920]
$e newPath $emj584 FIXED [RL M8]
set emj640 [$e addTechVia [V {VIA89}]]
$e newPath $emj585 FIXED [RL M9]
set emj641 [$e addPoint 5907600 136080]
$e newPath $emj585 FIXED [RL M9]
set emj642 [$e addPoint 5907600 405000]
$e newPath $emj587 FIXED [RL M8]
set emj643 [$e addPoint 5259600 136080]
$e newPath $emj588 FIXED [RL M8]
set emj644 [$e addPoint 5674320 136080]
$e newPath $emj590 FIXED [RL M9]
set emj645 [$e addTechVia [V {VIA89}]]
$e newPath $emj590 FIXED [RL M9]
set emj646 [$e addPoint 5393520 943920]
$e newPath $emj591 FIXED [RL M8]
set emch727 [$e addPoint 5259600 136080]
$e newPath $emj592 FIXED [RL M9]
set emj647 [$e addPoint 4879440 131760]
$e newPath $emj592 FIXED [RL M9]
set emj648 [$e addPoint 4879440 132660]
$e newPath $emj593 FIXED [RL M9]
set emch730 [$e addPoint 4879440 589680]
$e newPath $emj594 FIXED [RL M9]
set emj649 [$e addTechVia [V {VIA89}]]
$e newPath $emj594 FIXED [RL M9]
set emj650 [$e addPoint 4879440 671760]
$e newPath $emj596 FIXED [RL M9]
set emj651 [$e addPoint 4516560 136170]
$e newPath $emj597 FIXED [RL M9]
set emj652 [$e addTechVia [V {VIA89}]]
$e newPath $emj597 FIXED [RL M9]
set emj653 [$e addPoint 4365360 943920]
$e newPath $emj598 FIXED [RL M8]
set emj654 [$e addPoint 5406480 1216080]
$e newPath $emj598 FIXED [RL M8]
set emj655 [$e addTechVia [V {VIA89}]]
$e newPath $emj599 FIXED [RL M9]
set emj656 [$e addPoint 4879440 1212705]
$e newPath $emj599 FIXED [RL M9]
set emj657 [$e addPoint 4879440 1374560]
$e newPath $emj600 FIXED [RL M9]
set emj658 [$e addPoint 4365360 1211760]
$e newPath $emj600 FIXED [RL M9]
set emj659 [$e addPoint 4365360 1212660]
$e newPath $emj601 FIXED [RL M9]
set emj660 [$e addTechVia [V {VIA89}]]
$e newPath $emj601 FIXED [RL M9]
set emj661 [$e addPoint 4365360 1487295]
$e newPath $emj602 FIXED [RL M8]
set emch744 [$e addPoint 3643920 1483920]
$e newPath $emj603 FIXED [RL M8]
set emj662 [$e addPoint 4107808 1483920]
$e newPath $emj603 FIXED [RL M8]
set emj663 [$e addTechVia [V {VIA89}]]
$e newPath $emj604 FIXED [RL M9]
set emch747 [$e addPoint 3851280 1488240]
$e newPath $emj605 FIXED [RL M9]
set emj664 [$e addTechVia [V {VIA89}]]
$e newPath $emj605 FIXED [RL M9]
set emj665 [$e addPoint 3851280 1755000]
$e newPath $emj606 FIXED [RL M8]
set emj666 [$e addTechVia [V {VIA89}]]
$e newPath $emj607 FIXED [RL M9]
set emch751 [$e addPoint 3337200 1488240]
$e newPath $emj608 FIXED [RL M9]
set emj667 [$e addTechVia [V {VIA89}]]
$e newPath $emj608 FIXED [RL M9]
set emj668 [$e addPoint 3337200 1755000]
$e newPath $emj609 FIXED [RL M9]
set emj669 [$e addTechVia [V {VIA89}]]
$e newPath $emj609 FIXED [RL M9]
set emj670 [$e addPoint 2823120 2023920]
$e newPath $emj611 FIXED [RL M8]
set emch756 [$e addPoint 2153520 2023920]
$e newPath $emj611 FIXED [RL M8]
set emj671 [$e addPoint 2823120 2023920]
$e newPath $emj612 FIXED [RL M9]
set emj672 [$e addPoint 2309040 2027340]
$e newPath $emj612 FIXED [RL M9]
set emj673 [$e addPoint 2309040 2028240]
$e newPath $emj613 FIXED [RL M8]
set emj674 [$e addPoint 2373840 1756080]
$e newPath $emj614 FIXED [RL M9]
set emj675 [$e addPoint 2322000 1759500]
$e newPath $emj615 FIXED [RL M9]
set emj676 [$e addTechVia [V {VIA89}]]
$e newPath $emj615 FIXED [RL M9]
set emj677 [$e addPoint 1799280 2563920]
$e newPath $emj616 FIXED [RL M8]
set emj678 [$e addPoint 83472 2296080]
$e newPath $emj617 FIXED [RL M9]
set emj679 [$e addPoint 196560 2296170]
$e newPath $emj619 FIXED [RL M8]
set emj680 [$e addPoint 83472 2563920]
$e newPath $emj620 FIXED [RL M9]
set emj681 [$e addPoint 196560 2564010]
$e newPath $emj621 FIXED [RL M9]
set emj682 [$e addPoint 585360 2564010]
$e newPath $emj623 FIXED [RL M9]
set emj683 [$e addPoint 257040 2836080]
$e newPath $emj624 FIXED [RL M8]
set emch770 [$e addPoint 4365360 676080]
$e newPath $emj625 FIXED [RL M9]
set emj684 [$e addPoint 4106160 676170]
$e newPath $emj627 FIXED [RL M8]
set emj685 [$e addPoint 4107808 943920]
$e newPath $emj627 FIXED [RL M8]
set emj686 [$e addTechVia [V {VIA89}]]
$e newPath $emj628 FIXED [RL M9]
set emj687 [$e addPoint 3920400 947340]
$e newPath $emj629 FIXED [RL M9]
set emj688 [$e addTechVia [V {VIA89}]]
$e newPath $emj629 FIXED [RL M9]
set emj689 [$e addPoint 1285200 2477520]
$e newPath $emj630 FIXED [RL M8]
set emj690 [$e addTechVia [V {VIA89}]]
$e newPath $emj632 FIXED [RL M8]
set emj691 [$e addPoint 837600 2296080]
$e newPath $emj632 FIXED [RL M8]
set emj692 [$e addTechVia [V {VIA89}]]
$e newPath $emj633 FIXED [RL M9]
set emj693 [$e addPoint 827280 2296170]
$e newPath $emj634 FIXED [RL M8]
set emj694 [$e addPoint 1285200 2563920]
$e newPath $emj634 FIXED [RL M8]
set emj695 [$e addTechVia [V {VIA89}]]
$e newPath $emj637 FIXED [RL M9]
set emch783 [$e addPoint 771120 2832705]
$e newPath $emj638 FIXED [RL M9]
set emj696 [$e addPoint 771120 2836080]
$e newPath $emj639 FIXED [RL M8]
set emj697 [$e addPoint 6892560 403920]
$e newPath $emj639 FIXED [RL M8]
set emj698 [$e addTechVia [V {VIA89}]]
$e newPath $emj640 FIXED [RL M9]
set emj699 [$e addPoint 6417360 136080]
$e newPath $emj640 FIXED [RL M9]
set emj700 [$e addPoint 6417360 405000]
$e newPath $emj641 FIXED [RL M9]
set emj701 [$e addTechVia [V {VIA89}]]
$e newPath $emj641 FIXED [RL M9]
set emj702 [$e addPoint 5907600 135000]
$e newPath $emj642 FIXED [RL M9]
set emj703 [$e addPoint 5907600 675000]
$e newPath $emj643 FIXED [RL M8]
set emj704 [$e addTechVia [V {VIA89}]]
$e newPath $emj644 FIXED [RL M8]
set emj705 [$e addPoint 5898960 136080]
$e newPath $emj644 FIXED [RL M8]
set emj706 [$e addTechVia [V {VIA89}]]
$e newPath $emj645 FIXED [RL M8]
set emj707 [$e addPoint 5282144 676080]
$e newPath $emj645 FIXED [RL M8]
set emj708 [$e addPoint 5397840 676080]
$e newPath $emj646 FIXED [RL M9]
set emj709 [$e addTechVia [V {VIA89}]]
$e newPath $emj646 FIXED [RL M9]
set emj710 [$e addPoint 5393520 947295]
$e newPath $emj647 FIXED [RL M9]
set emj711 [$e addTechVia [V {VIA89}]]
$e newPath $emj647 FIXED [RL M9]
set emj712 [$e addPoint 4879440 15056]
$e newPath $emj647 FIXED [RL M9]
set emch801 [$e addPoint 4879440 132660]
$e newPath $emj650 FIXED [RL M9]
set emj713 [$e addTechVia [V {VIA89}]]
$e newPath $emj650 FIXED [RL M9]
set emj714 [$e addPoint 4879440 672660]
$e newPath $emj650 FIXED [RL M9]
set emj715 [$e addPoint 4879440 672705]
$e newPath $emj652 FIXED [RL M8]
set emj716 [$e addPoint 4499280 676080]
$e newPath $emj653 FIXED [RL M9]
set emj717 [$e addTechVia [V {VIA89}]]
$e newPath $emj653 FIXED [RL M9]
set emj718 [$e addPoint 4365360 947295]
$e newPath $emj654 FIXED [RL M8]
set emj719 [$e addPoint 5907600 1216080]
$e newPath $emj654 FIXED [RL M8]
set emj720 [$e addTechVia [V {VIA89}]]
$e newPath $emj655 FIXED [RL M9]
set emj721 [$e addPoint 5393520 1215000]
$e newPath $emj655 FIXED [RL M9]
set emj722 [$e addPoint 5393520 1483920]
$e newPath $emj656 FIXED [RL M9]
set emj723 [$e addPoint 4879440 1211760]
$e newPath $emj656 FIXED [RL M9]
set emj724 [$e addPoint 4879440 1212660]
$e newPath $emj657 FIXED [RL M9]
set emj725 [$e addPoint 4879440 1374750]
$e newPath $emj657 FIXED [RL M9]
set emj726 [$e addPoint 4879440 1375920]
$e newPath $emj658 FIXED [RL M9]
set emj727 [$e addTechVia [V {VIA89}]]
$e newPath $emj658 FIXED [RL M9]
set emj728 [$e addPoint 4365360 948240]
$e newPath $emj658 FIXED [RL M9]
set emch818 [$e addPoint 4365360 1212660]
$e newPath $emj660 FIXED [RL M8]
set emch819 [$e addPoint 4107808 1483920]
$e newPath $emj660 FIXED [RL M8]
set emj729 [$e addPoint 4499280 1483920]
$e newPath $emj661 FIXED [RL M9]
set emj730 [$e addPoint 4365360 1487340]
$e newPath $emj661 FIXED [RL M9]
set emj731 [$e addPoint 4365360 1488240]
$e newPath $emj663 FIXED [RL M9]
set emj732 [$e addPoint 4106160 1484010]
$e newPath $emj665 FIXED [RL M9]
set emj733 [$e addPoint 3851280 1756080]
$e newPath $emj666 FIXED [RL M9]
set emj734 [$e addPoint 3643920 1484010]
$e newPath $emj668 FIXED [RL M9]
set emj735 [$e addPoint 3337200 1756080]
$e newPath $emj669 FIXED [RL M8]
set emj736 [$e addPoint 2400672 1756080]
$e newPath $emj669 FIXED [RL M8]
set emj737 [$e addPoint 3194640 1756080]
$e newPath $emj670 FIXED [RL M9]
set emch829 [$e addTechVia [V {VIA89}]]
$e newPath $emj670 FIXED [RL M9]
set emj738 [$e addPoint 2823120 2025000]
$e newPath $emj671 FIXED [RL M8]
set emj739 [$e addPoint 3194640 2023920]
$e newPath $emj672 FIXED [RL M9]
set emch832 [$e addPoint 2309040 2028240]
$e newPath $emj673 FIXED [RL M9]
set emj740 [$e addTechVia [V {VIA89}]]
$e newPath $emj673 FIXED [RL M9]
set emj741 [$e addPoint 2309040 2160032]
$e newPath $emj674 FIXED [RL M8]
set emj742 [$e addPoint 2399760 1756080]
$e newPath $emj674 FIXED [RL M8]
set emj743 [$e addTechVia [V {VIA89}]]
$e newPath $emj676 FIXED [RL M8]
set emj744 [$e addPoint 1786320 2296080]
$e newPath $emj676 FIXED [RL M8]
set emj745 [$e addPoint 2309040 2296080]
$e newPath $emj677 FIXED [RL M9]
set emj746 [$e addTechVia [V {VIA89}]]
$e newPath $emj677 FIXED [RL M9]
set emj747 [$e addPoint 1799280 2565000]
$e newPath $emj683 FIXED [RL M9]
set emj748 [$e addTechVia [V {VIA89}]]
$e newPath $emj683 FIXED [RL M9]
set emj749 [$e addPoint 257040 3103920]
$e newPath $emj685 FIXED [RL M8]
set emch843 [$e addPoint 4365360 943920]
$e newPath $emj686 FIXED [RL M9]
set emj750 [$e addPoint 4106160 944010]
$e newPath $emj688 FIXED [RL M8]
set emch845 [$e addPoint 837600 2296080]
$e newPath $emj688 FIXED [RL M8]
set emj751 [$e addPoint 1302480 2296080]
$e newPath $emj689 FIXED [RL M9]
set emj752 [$e addTechVia [V {VIA89}]]
$e newPath $emj689 FIXED [RL M9]
set emj753 [$e addPoint 1285200 2479230]
$e newPath $emj689 FIXED [RL M9]
set emj754 [$e addPoint 1285200 2479264]
$e newPath $emj690 FIXED [RL M9]
set emj755 [$e addPoint 2153520 2024010]
$e newPath $emj692 FIXED [RL M9]
set emj756 [$e addPoint 835920 2296170]
$e newPath $emj694 FIXED [RL M8]
set emj757 [$e addPoint 1682640 2563920]
$e newPath $emj694 FIXED [RL M8]
set emj758 [$e addTechVia [V {VIA89}]]
$e newPath $emj695 FIXED [RL M9]
set emj759 [$e addPoint 1224720 2576160]
$e newPath $emj696 FIXED [RL M9]
set emj760 [$e addTechVia [V {VIA89}]]
$e newPath $emj696 FIXED [RL M9]
set emj761 [$e addPoint 771120 3103920]
$e newPath $emj697 FIXED [RL M8]
set emj762 [$e addPoint 6931440 403920]
$e newPath $emj697 FIXED [RL M8]
set emj763 [$e addTechVia [V {VIA89}]]
$e newPath $emj698 FIXED [RL M9]
set emj764 [$e addPoint 6469200 409140]
$e newPath $emj699 FIXED [RL M9]
set emj765 [$e addTechVia [V {VIA89}]]
$e newPath $emj699 FIXED [RL M9]
set emj766 [$e addPoint 6417360 135000]
$e newPath $emj700 FIXED [RL M9]
set emj767 [$e addPoint 6417360 675000]
$e newPath $emj701 FIXED [RL M8]
set emch863 [$e addPoint 5898960 136080]
$e newPath $emj701 FIXED [RL M8]
set emch864 [$e addPoint 6417360 136080]
$e newPath $emj702 FIXED [RL M9]
set emj768 [$e addPoint 5907600 17190]
$e newPath $emj703 FIXED [RL M9]
set emj769 [$e addPoint 5907600 676080]
$e newPath $emj704 FIXED [RL M9]
set emj770 [$e addPoint 5259600 136170]
$e newPath $emj705 FIXED [RL M8]
set emj771 [$e addTechVia [V {VIA89}]]
$e newPath $emj706 FIXED [RL M9]
set emj772 [$e addPoint 5674320 136170]
$e newPath $emj707 FIXED [RL M8]
set emj773 [$e addPoint 5281200 676080]
$e newPath $emj708 FIXED [RL M8]
set emj774 [$e addPoint 5600880 676080]
$e newPath $emj708 FIXED [RL M8]
set emj775 [$e addTechVia [V {VIA89}]]
$e newPath $emj709 FIXED [RL M8]
set emj776 [$e addPoint 5282144 943920]
$e newPath $emj709 FIXED [RL M8]
set emj777 [$e addPoint 5793376 943920]
$e newPath $emj710 FIXED [RL M9]
set emj778 [$e addPoint 5393520 947340]
$e newPath $emj710 FIXED [RL M9]
set emj779 [$e addPoint 5393520 948240]
$e newPath $emj714 FIXED [RL M9]
set emch877 [$e addPoint 4879440 672705]
$e newPath $emj715 FIXED [RL M9]
set emj780 [$e addPoint 4879440 676080]
$e newPath $emj716 FIXED [RL M8]
set emj781 [$e addPoint 4499616 676080]
$e newPath $emj716 FIXED [RL M8]
set emj782 [$e addTechVia [V {VIA89}]]
$e newPath $emj717 FIXED [RL M8]
set emj783 [$e addPoint 4412880 943920]
$e newPath $emj718 FIXED [RL M9]
set emj784 [$e addPoint 4365360 947340]
$e newPath $emj718 FIXED [RL M9]
set emch883 [$e addPoint 4365360 948240]
$e newPath $emj719 FIXED [RL M8]
set emj785 [$e addPoint 6417360 1216080]
$e newPath $emj719 FIXED [RL M8]
set emj786 [$e addTechVia [V {VIA89}]]
$e newPath $emj720 FIXED [RL M9]
set emj787 [$e addPoint 5406480 1074420]
$e newPath $emj721 FIXED [RL M9]
set emch887 [$e addPoint 5393520 948240]
$e newPath $emj722 FIXED [RL M9]
set emj788 [$e addTechVia [V {VIA89}]]
$e newPath $emj722 FIXED [RL M9]
set emj789 [$e addPoint 5393520 1485000]
$e newPath $emj723 FIXED [RL M9]
set emj790 [$e addTechVia [V {VIA89}]]
$e newPath $emj723 FIXED [RL M9]
set emj791 [$e addPoint 4879440 982800]
$e newPath $emj723 FIXED [RL M9]
set emch892 [$e addPoint 4879440 1212660]
$e newPath $emj725 FIXED [RL M9]
set emch893 [$e addPoint 4879440 1375920]
$e newPath $emj726 FIXED [RL M9]
set emj792 [$e addTechVia [V {VIA89}]]
$e newPath $emj726 FIXED [RL M9]
set emj793 [$e addPoint 4879440 1483920]
$e newPath $emj728 FIXED [RL M9]
set emj794 [$e addTechVia [V {VIA89}]]
$e newPath $emj728 FIXED [RL M9]
set emch897 [$e addPoint 4365360 947340]
$e newPath $emj729 FIXED [RL M8]
set emj795 [$e addPoint 4499616 1483920]
$e newPath $emj729 FIXED [RL M8]
set emj796 [$e addTechVia [V {VIA89}]]
$e newPath $emj730 FIXED [RL M9]
set emch900 [$e addPoint 4365360 1488240]
$e newPath $emj731 FIXED [RL M9]
set emj797 [$e addTechVia [V {VIA89}]]
$e newPath $emj731 FIXED [RL M9]
set emj798 [$e addPoint 4365360 1751760]
$e newPath $emj733 FIXED [RL M9]
set emj799 [$e addTechVia [V {VIA89}]]
$e newPath $emj733 FIXED [RL M9]
set emj800 [$e addPoint 3851280 2023920]
$e newPath $emj735 FIXED [RL M9]
set emj801 [$e addTechVia [V {VIA89}]]
$e newPath $emj735 FIXED [RL M9]
set emj802 [$e addPoint 3337200 2023920]
$e newPath $emj736 FIXED [RL M8]
set emch907 [$e addPoint 2399760 1756080]
$e newPath $emj737 FIXED [RL M8]
set emj803 [$e addPoint 3198048 1756080]
$e newPath $emj737 FIXED [RL M8]
set emj804 [$e addTechVia [V {VIA89}]]
$e newPath $emj738 FIXED [RL M9]
set emj805 [$e addPoint 2823120 2295000]
$e newPath $emj739 FIXED [RL M8]
set emj806 [$e addPoint 3337200 2023920]
$e newPath $emj739 FIXED [RL M8]
set emj807 [$e addTechVia [V {VIA89}]]
$e newPath $emj741 FIXED [RL M9]
set emj808 [$e addPoint 2309040 2160090]
$e newPath $emj741 FIXED [RL M9]
set emj809 [$e addPoint 2309040 2162160]
$e newPath $emj742 FIXED [RL M8]
set emj810 [$e addTechVia [V {VIA89}]]
$e newPath $emj743 FIXED [RL M9]
set emj811 [$e addPoint 2373840 1756170]
$e newPath $emj744 FIXED [RL M8]
set emj812 [$e addPoint 1688736 2296080]
$e newPath $emj744 FIXED [RL M8]
set emj813 [$e addTechVia [V {VIA89}]]
$e newPath $emj745 FIXED [RL M8]
set emj814 [$e addPoint 2322000 2296080]
$e newPath $emj745 FIXED [RL M8]
set emj815 [$e addTechVia [V {VIA89}]]
$e newPath $emj746 FIXED [RL M8]
set emj816 [$e addPoint 1691280 2563920]
$e newPath $emj746 FIXED [RL M8]
set emj817 [$e addPoint 2309040 2563920]
$e newPath $emj747 FIXED [RL M9]
set emj818 [$e addPoint 1799280 2835000]
$e newPath $emj748 FIXED [RL M8]
set emj819 [$e addPoint 83472 2836080]
$e newPath $emj748 FIXED [RL M8]
set emj820 [$e addPoint 300240 2836080]
$e newPath $emj749 FIXED [RL M9]
set emj821 [$e addTechVia [V {VIA89}]]
$e newPath $emj749 FIXED [RL M9]
set emj822 [$e addPoint 257040 3107295]
$e newPath $emj751 FIXED [RL M8]
set emj823 [$e addPoint 1630800 2296080]
$e newPath $emj751 FIXED [RL M8]
set emj824 [$e addTechVia [V {VIA89}]]
$e newPath $emj753 FIXED [RL M9]
set emch930 [$e addPoint 1285200 2479264]
$e newPath $emj754 FIXED [RL M9]
set emch931 [$e addPoint 1285200 2563920]
$e newPath $emj757 FIXED [RL M8]
set emj825 [$e addPoint 1682976 2563920]
$e newPath $emj757 FIXED [RL M8]
set emj826 [$e addTechVia [V {VIA89}]]
$e newPath $emj758 FIXED [RL M9]
set emj827 [$e addPoint 1285200 2565000]
$e newPath $emj760 FIXED [RL M8]
set emj828 [$e addPoint 586912 2836080]
$e newPath $emj760 FIXED [RL M8]
set emj829 [$e addPoint 978144 2836080]
$e newPath $emj761 FIXED [RL M9]
set emj830 [$e addTechVia [V {VIA89}]]
$e newPath $emj761 FIXED [RL M9]
set emj831 [$e addPoint 771120 3107295]
$e newPath $emj762 FIXED [RL M8]
set emj832 [$e addPoint 7445520 403920]
$e newPath $emj762 FIXED [RL M8]
set emj833 [$e addTechVia [V {VIA89}]]
$e newPath $emj763 FIXED [RL M9]
set emj834 [$e addPoint 6892560 412380]
$e newPath $emj765 FIXED [RL M8]
set emj835 [$e addPoint 6469200 136080]
$e newPath $emj766 FIXED [RL M9]
set emj836 [$e addPoint 6417360 15056]
$e newPath $emj767 FIXED [RL M9]
set emj837 [$e addPoint 6417360 676080]
$e newPath $emj768 FIXED [RL M9]
set emj838 [$e addPoint 5907600 15120]
$e newPath $emj768 FIXED [RL M9]
set emj839 [$e addPoint 5907600 17056]
$e newPath $emj769 FIXED [RL M9]
set emj840 [$e addTechVia [V {VIA89}]]
$e newPath $emj769 FIXED [RL M9]
set emj841 [$e addPoint 5907600 679500]
$e newPath $emj771 FIXED [RL M9]
set emj842 [$e addPoint 5898960 20340]
$e newPath $emj773 FIXED [RL M8]
set emj843 [$e addPoint 4879440 676080]
$e newPath $emj773 FIXED [RL M8]
set emj844 [$e addTechVia [V {VIA89}]]
$e newPath $emj774 FIXED [RL M8]
set emj845 [$e addPoint 5601376 676080]
$e newPath $emj774 FIXED [RL M8]
set emj846 [$e addTechVia [V {VIA89}]]
$e newPath $emj775 FIXED [RL M9]
set emj847 [$e addPoint 5397840 714060]
$e newPath $emj776 FIXED [RL M8]
set emj848 [$e addPoint 5281200 943920]
$e newPath $emj777 FIXED [RL M8]
set emj849 [$e addPoint 5795280 943920]
$e newPath $emj778 FIXED [RL M9]
set emch957 [$e addPoint 5393520 948240]
$e newPath $emj779 FIXED [RL M9]
set emj850 [$e addTechVia [V {VIA89}]]
$e newPath $emj780 FIXED [RL M9]
set emch959 [$e addTechVia [V {VIA89}]]
$e newPath $emj780 FIXED [RL M9]
set emj851 [$e addPoint 4879440 943920]
$e newPath $emj781 FIXED [RL M8]
set emch961 [$e addPoint 4879440 676080]
$e newPath $emj782 FIXED [RL M9]
set emj852 [$e addPoint 4499280 676170]
$e newPath $emj783 FIXED [RL M8]
set emj853 [$e addPoint 4413216 943920]
$e newPath $emj783 FIXED [RL M8]
set emj854 [$e addTechVia [V {VIA89}]]
$e newPath $emj785 FIXED [RL M8]
set emj855 [$e addPoint 6421680 1216080]
$e newPath $emj785 FIXED [RL M8]
set emj856 [$e addTechVia [V {VIA89}]]
$e newPath $emj786 FIXED [RL M9]
set emj857 [$e addPoint 5907600 1212705]
$e newPath $emj786 FIXED [RL M9]
set emj858 [$e addPoint 5907600 1374560]
$e newPath $emj788 FIXED [RL M8]
set emj859 [$e addPoint 5289840 1483920]
$e newPath $emj788 FIXED [RL M8]
set emj860 [$e addPoint 5907600 1483920]
$e newPath $emj789 FIXED [RL M9]
set emj861 [$e addPoint 5393520 1755000]
$e newPath $emj791 FIXED [RL M9]
set emj862 [$e addTechVia [V {VIA89}]]
$e newPath $emj791 FIXED [RL M9]
set emj863 [$e addPoint 4879440 981792]
$e newPath $emj791 FIXED [RL M9]
set emj864 [$e addPoint 4879440 981810]
$e newPath $emj793 FIXED [RL M9]
set emj865 [$e addTechVia [V {VIA89}]]
$e newPath $emj793 FIXED [RL M9]
set emj866 [$e addPoint 4879440 1487295]
$e newPath $emj795 FIXED [RL M8]
set emch977 [$e addPoint 4879440 1483920]
$e newPath $emj796 FIXED [RL M9]
set emj867 [$e addPoint 4499280 1484010]
$e newPath $emj798 FIXED [RL M9]
set emj868 [$e addTechVia [V {VIA89}]]
$e newPath $emj798 FIXED [RL M9]
set emj869 [$e addPoint 4365360 1752660]
$e newPath $emj798 FIXED [RL M9]
set emj870 [$e addPoint 4365360 1752705]
$e newPath $emj799 FIXED [RL M8]
set emch982 [$e addPoint 3337200 1756080]
$e newPath $emj799 FIXED [RL M8]
set emj871 [$e addPoint 3920400 1756080]
$e newPath $emj800 FIXED [RL M9]
set emj872 [$e addTechVia [V {VIA89}]]
$e newPath $emj800 FIXED [RL M9]
set emj873 [$e addPoint 3851280 2025000]
$e newPath $emj801 FIXED [RL M8]
set emj874 [$e addPoint 3289680 1756080]
$e newPath $emj802 FIXED [RL M9]
set emch987 [$e addTechVia [V {VIA89}]]
$e newPath $emj802 FIXED [RL M9]
set emj875 [$e addPoint 3337200 2027295]
$e newPath $emj803 FIXED [RL M8]
set emj876 [$e addPoint 3198960 1756080]
$e newPath $emj804 FIXED [RL M9]
set emj877 [$e addPoint 3194640 1752660]
$e newPath $emj805 FIXED [RL M9]
set emj878 [$e addPoint 2823120 2296080]
$e newPath $emj806 FIXED [RL M8]
set emj879 [$e addPoint 3557520 2023920]
$e newPath $emj807 FIXED [RL M9]
set emj880 [$e addPoint 3194640 2027340]
$e newPath $emj808 FIXED [RL M9]
set emch994 [$e addPoint 2309040 2162160]
$e newPath $emj809 FIXED [RL M9]
set emj881 [$e addTechVia [V {VIA89}]]
$e newPath $emj809 FIXED [RL M9]
set emj882 [$e addPoint 2309040 2295000]
$e newPath $emj810 FIXED [RL M9]
set emj883 [$e addPoint 2399760 1756170]
$e newPath $emj812 FIXED [RL M8]
set emj884 [$e addPoint 1686960 2296080]
$e newPath $emj813 FIXED [RL M9]
set emj885 [$e addPoint 1786320 2249460]
$e newPath $emj814 FIXED [RL M8]
set emj886 [$e addPoint 2823120 2296080]
$e newPath $emj814 FIXED [RL M8]
set emj887 [$e addTechVia [V {VIA89}]]
$e newPath $emj815 FIXED [RL M9]
set emch1002 [$e addPoint 2309040 2295000]
$e newPath $emj815 FIXED [RL M9]
set emj888 [$e addPoint 2309040 2563920]
$e newPath $emj816 FIXED [RL M8]
set emch1004 [$e addPoint 1682976 2563920]
$e newPath $emj816 FIXED [RL M8]
set emj889 [$e addTechVia [V {VIA89}]]
$e newPath $emj817 FIXED [RL M8]
set emj890 [$e addPoint 2322000 2563920]
$e newPath $emj817 FIXED [RL M8]
set emch1007 [$e addTechVia [V {VIA89}]]
$e newPath $emj818 FIXED [RL M9]
set emj891 [$e addPoint 1799280 2836080]
$e newPath $emj820 FIXED [RL M8]
set emj892 [$e addPoint 585360 2836080]
$e newPath $emj820 FIXED [RL M8]
set emj893 [$e addTechVia [V {VIA89}]]
$e newPath $emj821 FIXED [RL M8]
set emj894 [$e addPoint 196560 3103920]
$e newPath $emj821 FIXED [RL M8]
set emch1012 [$e addPoint 771120 3103920]
$e newPath $emj822 FIXED [RL M9]
set emj895 [$e addPoint 257040 3107340]
$e newPath $emj822 FIXED [RL M9]
set emj896 [$e addPoint 257040 3108240]
$e newPath $emj823 FIXED [RL M8]
set emj897 [$e addPoint 1632480 2296080]
$e newPath $emj823 FIXED [RL M8]
set emj898 [$e addTechVia [V {VIA89}]]
$e newPath $emj824 FIXED [RL M9]
set emj899 [$e addPoint 1302480 2465460]
$e newPath $emj826 FIXED [RL M9]
set emj900 [$e addPoint 1682640 2564010]
$e newPath $emj827 FIXED [RL M9]
set emj901 [$e addPoint 1285200 2831760]
$e newPath $emj828 FIXED [RL M8]
set emch1020 [$e addPoint 585360 2836080]
$e newPath $emj829 FIXED [RL M8]
set emj902 [$e addPoint 978480 2836080]
$e newPath $emj830 FIXED [RL M8]
set emj903 [$e addPoint 1285200 3103920]
$e newPath $emj831 FIXED [RL M9]
set emj904 [$e addPoint 771120 3107340]
$e newPath $emj831 FIXED [RL M9]
set emj905 [$e addPoint 771120 3108240]
$e newPath $emj832 FIXED [RL M8]
set emj906 [$e addPoint 7959600 403920]
$e newPath $emj832 FIXED [RL M8]
set emj907 [$e addTechVia [V {VIA89}]]
$e newPath $emj833 FIXED [RL M9]
set emj908 [$e addPoint 6931440 136080]
$e newPath $emj833 FIXED [RL M9]
set emj909 [$e addPoint 6931440 405000]
$e newPath $emj835 FIXED [RL M8]
set emj910 [$e addPoint 6470880 136080]
$e newPath $emj835 FIXED [RL M8]
set emj911 [$e addTechVia [V {VIA89}]]
$e newPath $emj837 FIXED [RL M9]
set emj912 [$e addTechVia [V {VIA89}]]
$e newPath $emj837 FIXED [RL M9]
set emj913 [$e addPoint 6417360 679500]
$e newPath $emj838 FIXED [RL M9]
set emj914 [$e addTechVia [V {VIA89}]]
$e newPath $emj838 FIXED [RL M9]
set emj915 [$e addPoint 5907600 15056]
$e newPath $emj838 FIXED [RL M9]
set emch1035 [$e addPoint 5907600 17056]
$e newPath $emj840 FIXED [RL M8]
set emch1036 [$e addPoint 5601376 676080]
$e newPath $emj840 FIXED [RL M8]
set emch1037 [$e addPoint 6417360 676080]
$e newPath $emj841 FIXED [RL M9]
set emj916 [$e addPoint 5907600 680400]
$e newPath $emj844 FIXED [RL M9]
set emj917 [$e addPoint 5281200 676170]
$e newPath $emj846 FIXED [RL M9]
set emj918 [$e addPoint 5600880 676170]
$e newPath $emj848 FIXED [RL M8]
set emj919 [$e addPoint 4879440 943920]
$e newPath $emj848 FIXED [RL M8]
set emj920 [$e addTechVia [V {VIA89}]]
$e newPath $emj849 FIXED [RL M8]
set emj921 [$e addPoint 5907600 943920]
$e newPath $emj849 FIXED [RL M8]
set emj922 [$e addTechVia [V {VIA89}]]
$e newPath $emj851 FIXED [RL M9]
set emch1045 [$e addTechVia [V {VIA89}]]
$e newPath $emj851 FIXED [RL M9]
set emj923 [$e addPoint 4879440 947295]
$e newPath $emj853 FIXED [RL M8]
set emch1047 [$e addPoint 4879440 943920]
$e newPath $emj854 FIXED [RL M9]
set emj924 [$e addPoint 4412880 944010]
$e newPath $emj855 FIXED [RL M8]
set emj925 [$e addPoint 6577200 1216080]
$e newPath $emj855 FIXED [RL M8]
set emj926 [$e addTechVia [V {VIA89}]]
$e newPath $emj856 FIXED [RL M9]
set emj927 [$e addPoint 6417360 1215000]
$e newPath $emj856 FIXED [RL M9]
set emj928 [$e addPoint 6417360 1374560]
$e newPath $emj857 FIXED [RL M9]
set emj929 [$e addPoint 5907600 1211760]
$e newPath $emj857 FIXED [RL M9]
set emj930 [$e addPoint 5907600 1212660]
$e newPath $emj858 FIXED [RL M9]
set emj931 [$e addPoint 5907600 1374750]
$e newPath $emj858 FIXED [RL M9]
set emj932 [$e addPoint 5907600 1375920]
$e newPath $emj859 FIXED [RL M8]
set emch1057 [$e addPoint 4879440 1483920]
$e newPath $emj859 FIXED [RL M8]
set emj933 [$e addTechVia [V {VIA89}]]
$e newPath $emj860 FIXED [RL M8]
set emj934 [$e addPoint 6019920 1483920]
$e newPath $emj860 FIXED [RL M8]
set emj935 [$e addTechVia [V {VIA89}]]
$e newPath $emj861 FIXED [RL M9]
set emj936 [$e addPoint 5393520 1756080]
$e newPath $emj863 FIXED [RL M9]
set emj937 [$e addPoint 4879440 948240]
$e newPath $emj863 FIXED [RL M9]
set emch1063 [$e addPoint 4879440 981810]
$e newPath $emj866 FIXED [RL M9]
set emj938 [$e addPoint 4879440 1487340]
$e newPath $emj866 FIXED [RL M9]
set emj939 [$e addPoint 4879440 1488240]
$e newPath $emj869 FIXED [RL M9]
set emch1066 [$e addPoint 4365360 1752705]
$e newPath $emj870 FIXED [RL M9]
set emj940 [$e addPoint 4365360 1756080]
$e newPath $emj871 FIXED [RL M8]
set emj941 [$e addPoint 4106160 1756080]
$e newPath $emj871 FIXED [RL M8]
set emj942 [$e addTechVia [V {VIA89}]]
$e newPath $emj872 FIXED [RL M8]
set emj943 [$e addPoint 3559200 2023920]
$e newPath $emj872 FIXED [RL M8]
set emj944 [$e addPoint 3864240 2023920]
$e newPath $emj873 FIXED [RL M9]
set emj945 [$e addPoint 3851280 2160032]
$e newPath $emj874 FIXED [RL M8]
set emj946 [$e addPoint 3282592 1756080]
$e newPath $emj874 FIXED [RL M8]
set emj947 [$e addTechVia [V {VIA89}]]
$e newPath $emj875 FIXED [RL M9]
set emj948 [$e addPoint 3337200 2027340]
$e newPath $emj875 FIXED [RL M9]
set emj949 [$e addPoint 3337200 2028240]
$e newPath $emj876 FIXED [RL M8]
set emj950 [$e addPoint 3281040 1756080]
$e newPath $emj876 FIXED [RL M8]
set emj951 [$e addTechVia [V {VIA89}]]
$e newPath $emj878 FIXED [RL M9]
set emch1079 [$e addTechVia [V {VIA89}]]
$e newPath $emj878 FIXED [RL M9]
set emj952 [$e addPoint 2823120 2563920]
$e newPath $emj879 FIXED [RL M8]
set emch1081 [$e addPoint 3559200 2023920]
$e newPath $emj879 FIXED [RL M8]
set emj953 [$e addTechVia [V {VIA89}]]
$e newPath $emj884 FIXED [RL M8]
set emch1083 [$e addPoint 1632480 2296080]
$e newPath $emj884 FIXED [RL M8]
set emj954 [$e addTechVia [V {VIA89}]]
$e newPath $emj886 FIXED [RL M8]
set emj955 [$e addPoint 3194640 2296080]
$e newPath $emj887 FIXED [RL M9]
set emj956 [$e addPoint 2322000 2292660]
$e newPath $emj888 FIXED [RL M9]
set emj957 [$e addPoint 2309040 2565000]
$e newPath $emj889 FIXED [RL M9]
set emj958 [$e addPoint 1691280 2567340]
$e newPath $emj890 FIXED [RL M8]
set emj959 [$e addPoint 2399760 2563920]
$e newPath $emj890 FIXED [RL M8]
set emj960 [$e addTechVia [V {VIA89}]]
$e newPath $emj891 FIXED [RL M9]
set emj961 [$e addTechVia [V {VIA89}]]
$e newPath $emj891 FIXED [RL M9]
set emj962 [$e addPoint 1799280 2959440]
$e newPath $emj892 FIXED [RL M8]
set emj963 [$e addTechVia [V {VIA89}]]
$e newPath $emj893 FIXED [RL M9]
set emj964 [$e addPoint 300240 2832660]
$e newPath $emj894 FIXED [RL M8]
set emj965 [$e addPoint 195616 3103920]
$e newPath $emj894 FIXED [RL M8]
set emj966 [$e addTechVia [V {VIA89}]]
$e newPath $emj895 FIXED [RL M9]
set emch1097 [$e addPoint 257040 3108240]
$e newPath $emj896 FIXED [RL M9]
set emj967 [$e addTechVia [V {VIA89}]]
$e newPath $emj896 FIXED [RL M9]
set emj968 [$e addPoint 257040 3371760]
$e newPath $emj898 FIXED [RL M9]
set emj969 [$e addPoint 1630800 2296170]
$e newPath $emj901 FIXED [RL M9]
set emj970 [$e addTechVia [V {VIA89}]]
$e newPath $emj901 FIXED [RL M9]
set emj971 [$e addPoint 1285200 2832660]
$e newPath $emj901 FIXED [RL M9]
set emj972 [$e addPoint 1285200 2832705]
$e newPath $emj902 FIXED [RL M8]
set emj973 [$e addPoint 1285200 2836080]
$e newPath $emj902 FIXED [RL M8]
set emj974 [$e addTechVia [V {VIA89}]]
$e newPath $emj903 FIXED [RL M8]
set emj975 [$e addPoint 1367280 3103920]
$e newPath $emj903 FIXED [RL M8]
set emj976 [$e addTechVia [V {VIA89}]]
$e newPath $emj904 FIXED [RL M9]
set emch1108 [$e addPoint 771120 3108240]
$e newPath $emj905 FIXED [RL M9]
set emj977 [$e addTechVia [V {VIA89}]]
$e newPath $emj905 FIXED [RL M9]
set emj978 [$e addPoint 771120 3371760]
$e newPath $emj906 FIXED [RL M8]
set emj979 [$e addPoint 8176368 403920]
$e newPath $emj906 FIXED [RL M8]
set emj980 [$e addTechVia [V {VIA89}]]
$e newPath $emj907 FIXED [RL M9]
set emj981 [$e addPoint 7445520 136080]
$e newPath $emj907 FIXED [RL M9]
set emj982 [$e addPoint 7445520 407295]
$e newPath $emj908 FIXED [RL M9]
set emj983 [$e addTechVia [V {VIA89}]]
$e newPath $emj908 FIXED [RL M9]
set emj984 [$e addPoint 6931440 132705]
$e newPath $emj909 FIXED [RL M9]
set emj985 [$e addPoint 6931440 675000]
$e newPath $emj910 FIXED [RL M8]
set emj986 [$e addPoint 6845040 136080]
$e newPath $emj911 FIXED [RL M9]
set emj987 [$e addPoint 6469200 132660]
$e newPath $emj911 FIXED [RL M9]
set emj988 [$e addPoint 6469200 136170]
$e newPath $emj912 FIXED [RL M8]
set emj989 [$e addPoint 6469200 676080]
$e newPath $emj913 FIXED [RL M9]
set emj990 [$e addPoint 6417360 943920]
$e newPath $emj916 FIXED [RL M9]
set emj991 [$e addTechVia [V {VIA89}]]
$e newPath $emj916 FIXED [RL M9]
set emj992 [$e addPoint 5907600 681952]
$e newPath $emj916 FIXED [RL M9]
set emj993 [$e addPoint 5907600 682110]
$e newPath $emj920 FIXED [RL M9]
set emj994 [$e addPoint 5281200 944010]
$e newPath $emj921 FIXED [RL M8]
set emj995 [$e addPoint 6387120 943920]
$e newPath $emj921 FIXED [RL M8]
set emj996 [$e addTechVia [V {VIA89}]]
$e newPath $emj922 FIXED [RL M9]
set emj997 [$e addPoint 5795280 944010]
$e newPath $emj923 FIXED [RL M9]
set emj998 [$e addPoint 4879440 947340]
$e newPath $emj923 FIXED [RL M9]
set emch1131 [$e addPoint 4879440 948240]
$e newPath $emj925 FIXED [RL M8]
set emj999 [$e addPoint 6578848 1216080]
$e newPath $emj925 FIXED [RL M8]
set emj1000 [$e addTechVia [V {VIA89}]]
$e newPath $emj926 FIXED [RL M9]
set emj1001 [$e addPoint 6421680 1246680]
$e newPath $emj927 FIXED [RL M9]
set emj1002 [$e addPoint 6417360 945000]
$e newPath $emj928 FIXED [RL M9]
set emj1003 [$e addPoint 6417360 1374750]
$e newPath $emj928 FIXED [RL M9]
set emj1004 [$e addPoint 6417360 1375920]
$e newPath $emj929 FIXED [RL M9]
set emj1005 [$e addTechVia [V {VIA89}]]
$e newPath $emj929 FIXED [RL M9]
set emj1006 [$e addPoint 5907600 982800]
$e newPath $emj929 FIXED [RL M9]
set emch1140 [$e addPoint 5907600 1212660]
$e newPath $emj931 FIXED [RL M9]
set emch1141 [$e addPoint 5907600 1375920]
$e newPath $emj932 FIXED [RL M9]
set emj1007 [$e addTechVia [V {VIA89}]]
$e newPath $emj932 FIXED [RL M9]
set emch1143 [$e addPoint 5907600 1483920]
$e newPath $emj933 FIXED [RL M9]
set emj1008 [$e addPoint 5289840 1871820]
$e newPath $emj934 FIXED [RL M8]
set emj1009 [$e addPoint 6021472 1483920]
$e newPath $emj934 FIXED [RL M8]
set emj1010 [$e addTechVia [V {VIA89}]]
$e newPath $emj935 FIXED [RL M9]
set emj1011 [$e addPoint 5907600 1487295]
$e newPath $emj936 FIXED [RL M9]
set emj1012 [$e addTechVia [V {VIA89}]]
$e newPath $emj936 FIXED [RL M9]
set emj1013 [$e addPoint 5393520 2023920]
$e newPath $emj937 FIXED [RL M9]
set emj1014 [$e addTechVia [V {VIA89}]]
$e newPath $emj937 FIXED [RL M9]
set emch1151 [$e addPoint 4879440 947340]
$e newPath $emj938 FIXED [RL M9]
set emch1152 [$e addPoint 4879440 1488240]
$e newPath $emj939 FIXED [RL M9]
set emj1015 [$e addTechVia [V {VIA89}]]
$e newPath $emj939 FIXED [RL M9]
set emj1016 [$e addPoint 4879440 1751760]
$e newPath $emj940 FIXED [RL M9]
set emj1017 [$e addTechVia [V {VIA89}]]
$e newPath $emj940 FIXED [RL M9]
set emj1018 [$e addPoint 4365360 2023920]
$e newPath $emj941 FIXED [RL M8]
set emj1019 [$e addPoint 4107808 1756080]
$e newPath $emj941 FIXED [RL M8]
set emj1020 [$e addTechVia [V {VIA89}]]
$e newPath $emj942 FIXED [RL M9]
set emj1021 [$e addPoint 3920400 1752660]
$e newPath $emj944 FIXED [RL M8]
set emj1022 [$e addPoint 4365360 2023920]
$e newPath $emj944 FIXED [RL M8]
set emj1023 [$e addTechVia [V {VIA89}]]
$e newPath $emj945 FIXED [RL M9]
set emj1024 [$e addPoint 3851280 2160090]
$e newPath $emj945 FIXED [RL M9]
set emj1025 [$e addPoint 3851280 2162160]
$e newPath $emj946 FIXED [RL M8]
set emch1164 [$e addPoint 3281040 1756080]
$e newPath $emj947 FIXED [RL M9]
set emj1026 [$e addPoint 3289680 1759500]
$e newPath $emj948 FIXED [RL M9]
set emch1166 [$e addPoint 3337200 2028240]
$e newPath $emj949 FIXED [RL M9]
set emj1027 [$e addTechVia [V {VIA89}]]
$e newPath $emj949 FIXED [RL M9]
set emj1028 [$e addPoint 3337200 2160032]
$e newPath $emj950 FIXED [RL M8]
set emj1029 [$e addTechVia [V {VIA89}]]
$e newPath $emj951 FIXED [RL M9]
set emj1030 [$e addPoint 3198960 1756170]
$e newPath $emj952 FIXED [RL M9]
set emj1031 [$e addTechVia [V {VIA89}]]
$e newPath $emj952 FIXED [RL M9]
set emj1032 [$e addPoint 2823120 2565000]
$e newPath $emj953 FIXED [RL M9]
set emj1033 [$e addPoint 3557520 2024010]
$e newPath $emj954 FIXED [RL M9]
set emj1034 [$e addPoint 1686960 2296170]
$e newPath $emj955 FIXED [RL M8]
set emj1035 [$e addPoint 3198048 2296080]
$e newPath $emj955 FIXED [RL M8]
set emj1036 [$e addTechVia [V {VIA89}]]
$e newPath $emj957 FIXED [RL M9]
set emj1037 [$e addPoint 2309040 2667600]
$e newPath $emj959 FIXED [RL M8]
set emj1038 [$e addPoint 2400672 2563920]
$e newPath $emj959 FIXED [RL M8]
set emj1039 [$e addTechVia [V {VIA89}]]
$e newPath $emj960 FIXED [RL M9]
set emj1040 [$e addPoint 2322000 2567340]
$e newPath $emj961 FIXED [RL M8]
set emj1041 [$e addPoint 1786320 2836080]
$e newPath $emj961 FIXED [RL M8]
set emj1042 [$e addPoint 2151968 2836080]
$e newPath $emj962 FIXED [RL M9]
set emj1043 [$e addPoint 1799280 2959650]
$e newPath $emj962 FIXED [RL M9]
set emj1044 [$e addPoint 1799280 2961360]
$e newPath $emj963 FIXED [RL M9]
set emj1045 [$e addPoint 585360 2836170]
$e newPath $emj965 FIXED [RL M8]
set emj1046 [$e addPoint 83472 3103920]
$e newPath $emj966 FIXED [RL M9]
set emj1047 [$e addPoint 196560 3104010]
$e newPath $emj968 FIXED [RL M9]
set emj1048 [$e addTechVia [V {VIA89}]]
$e newPath $emj968 FIXED [RL M9]
set emj1049 [$e addPoint 257040 3372660]
$e newPath $emj968 FIXED [RL M9]
set emj1050 [$e addPoint 257040 3372705]
$e newPath $emj971 FIXED [RL M9]
set emch1191 [$e addPoint 1285200 2832705]
$e newPath $emj972 FIXED [RL M9]
set emj1051 [$e addPoint 1285200 2836080]
$e newPath $emj973 FIXED [RL M8]
set emch1193 [$e addPoint 1786320 2836080]
$e newPath $emj973 FIXED [RL M8]
set emch1194 [$e addTechVia [V {VIA89}]]
$e newPath $emj974 FIXED [RL M9]
set emj1052 [$e addPoint 978480 2836170]
$e newPath $emj975 FIXED [RL M8]
set emj1053 [$e addPoint 1368928 3103920]
$e newPath $emj975 FIXED [RL M8]
set emj1054 [$e addTechVia [V {VIA89}]]
$e newPath $emj976 FIXED [RL M9]
set emj1055 [$e addPoint 1285200 2945610]
$e newPath $emj976 FIXED [RL M9]
set emj1056 [$e addPoint 1285200 3107295]
$e newPath $emj978 FIXED [RL M9]
set emj1057 [$e addTechVia [V {VIA89}]]
$e newPath $emj978 FIXED [RL M9]
set emj1058 [$e addPoint 771120 3372660]
$e newPath $emj978 FIXED [RL M9]
set emj1059 [$e addPoint 771120 3372705]
$e newPath $emj980 FIXED [RL M9]
set emj1060 [$e addPoint 7959600 136080]
$e newPath $emj980 FIXED [RL M9]
set emj1061 [$e addPoint 7959600 407295]
$e newPath $emj981 FIXED [RL M9]
set emj1062 [$e addTechVia [V {VIA89}]]
$e newPath $emj981 FIXED [RL M9]
set emj1063 [$e addPoint 7445520 132705]
$e newPath $emj982 FIXED [RL M9]
set emj1064 [$e addPoint 7445520 407340]
$e newPath $emj982 FIXED [RL M9]
set emj1065 [$e addPoint 7445520 408240]
$e newPath $emj983 FIXED [RL M8]
set emj1066 [$e addPoint 6846688 136080]
$e newPath $emj983 FIXED [RL M8]
set emj1067 [$e addPoint 7238160 136080]
$e newPath $emj984 FIXED [RL M9]
set emj1068 [$e addPoint 6931440 131760]
$e newPath $emj984 FIXED [RL M9]
set emj1069 [$e addPoint 6931440 132660]
$e newPath $emj985 FIXED [RL M9]
set emj1070 [$e addPoint 6931440 676080]
$e newPath $emj986 FIXED [RL M8]
set emch1214 [$e addPoint 6846688 136080]
$e newPath $emj986 FIXED [RL M8]
set emj1071 [$e addTechVia [V {VIA89}]]
$e newPath $emj989 FIXED [RL M8]
set emj1072 [$e addPoint 6470880 676080]
$e newPath $emj989 FIXED [RL M8]
set emj1073 [$e addTechVia [V {VIA89}]]
$e newPath $emj990 FIXED [RL M9]
set emj1074 [$e addTechVia [V {VIA89}]]
$e newPath $emj990 FIXED [RL M9]
set emch1219 [$e addPoint 6417360 945000]
$e newPath $emj992 FIXED [RL M9]
set emch1220 [$e addPoint 5907600 682110]
$e newPath $emj993 FIXED [RL M9]
set emch1221 [$e addPoint 5907600 943920]
$e newPath $emj995 FIXED [RL M8]
set emch1222 [$e addPoint 6417360 943920]
$e newPath $emj995 FIXED [RL M8]
set emj1075 [$e addTechVia [V {VIA89}]]
$e newPath $emj996 FIXED [RL M9]
set emj1076 [$e addPoint 5907600 947295]
$e newPath $emj999 FIXED [RL M8]
set emj1077 [$e addPoint 6927120 1216080]
$e newPath $emj1000 FIXED [RL M9]
set emj1078 [$e addPoint 6577200 1216170]
$e newPath $emj1003 FIXED [RL M9]
set emch1227 [$e addPoint 6417360 1375920]
$e newPath $emj1004 FIXED [RL M9]
set emj1079 [$e addTechVia [V {VIA89}]]
$e newPath $emj1004 FIXED [RL M9]
set emj1080 [$e addPoint 6417360 1483920]
$e newPath $emj1006 FIXED [RL M9]
set emj1081 [$e addTechVia [V {VIA89}]]
$e newPath $emj1006 FIXED [RL M9]
set emj1082 [$e addPoint 5907600 981792]
$e newPath $emj1006 FIXED [RL M9]
set emj1083 [$e addPoint 5907600 981810]
$e newPath $emj1009 FIXED [RL M8]
set emj1084 [$e addPoint 6417360 1483920]
$e newPath $emj1010 FIXED [RL M9]
set emj1085 [$e addPoint 6019920 1484010]
$e newPath $emj1011 FIXED [RL M9]
set emj1086 [$e addPoint 5907600 1487340]
$e newPath $emj1011 FIXED [RL M9]
set emj1087 [$e addPoint 5907600 1488240]
$e newPath $emj1012 FIXED [RL M8]
set emj1088 [$e addPoint 5324400 1756080]
$e newPath $emj1012 FIXED [RL M8]
set emj1089 [$e addPoint 5907600 1756080]
$e newPath $emj1013 FIXED [RL M9]
set emj1090 [$e addTechVia [V {VIA89}]]
$e newPath $emj1013 FIXED [RL M9]
set emj1091 [$e addPoint 5393520 2025000]
$e newPath $emj1016 FIXED [RL M9]
set emj1092 [$e addTechVia [V {VIA89}]]
$e newPath $emj1016 FIXED [RL M9]
set emj1093 [$e addPoint 4879440 1752660]
$e newPath $emj1016 FIXED [RL M9]
set emj1094 [$e addPoint 4879440 1752705]
$e newPath $emj1017 FIXED [RL M8]
set emch1244 [$e addPoint 4107808 1756080]
$e newPath $emj1017 FIXED [RL M8]
set emj1095 [$e addPoint 4499280 1756080]
$e newPath $emj1018 FIXED [RL M9]
set emch1246 [$e addTechVia [V {VIA89}]]
$e newPath $emj1018 FIXED [RL M9]
set emj1096 [$e addPoint 4365360 2027295]
$e newPath $emj1020 FIXED [RL M9]
set emj1097 [$e addPoint 4106160 1756170]
$e newPath $emj1022 FIXED [RL M8]
set emj1098 [$e addPoint 4879440 2023920]
$e newPath $emj1023 FIXED [RL M9]
set emj1099 [$e addPoint 3864240 2070540]
$e newPath $emj1024 FIXED [RL M9]
set emch1251 [$e addPoint 3851280 2162160]
$e newPath $emj1025 FIXED [RL M9]
set emj1100 [$e addTechVia [V {VIA89}]]
$e newPath $emj1025 FIXED [RL M9]
set emj1101 [$e addPoint 3851280 2295000]
$e newPath $emj1028 FIXED [RL M9]
set emj1102 [$e addPoint 3337200 2160090]
$e newPath $emj1028 FIXED [RL M9]
set emj1103 [$e addPoint 3337200 2162160]
$e newPath $emj1029 FIXED [RL M9]
set emj1104 [$e addPoint 3281040 1756170]
$e newPath $emj1031 FIXED [RL M8]
set emch1257 [$e addPoint 2400672 2563920]
$e newPath $emj1031 FIXED [RL M8]
set emj1105 [$e addPoint 3194640 2563920]
$e newPath $emj1032 FIXED [RL M9]
set emj1106 [$e addPoint 2823120 2835000]
$e newPath $emj1035 FIXED [RL M8]
set emj1107 [$e addPoint 3198960 2296080]
$e newPath $emj1036 FIXED [RL M9]
set emj1108 [$e addPoint 3194640 2292660]
$e newPath $emj1037 FIXED [RL M9]
set emj1109 [$e addTechVia [V {VIA89}]]
$e newPath $emj1037 FIXED [RL M9]
set emj1110 [$e addPoint 2309040 2669310]
$e newPath $emj1037 FIXED [RL M9]
set emj1111 [$e addPoint 2309040 2669344]
$e newPath $emj1039 FIXED [RL M9]
set emj1112 [$e addPoint 2399760 2564010]
$e newPath $emj1041 FIXED [RL M8]
set emj1113 [$e addTechVia [V {VIA89}]]
$e newPath $emj1042 FIXED [RL M8]
set emj1114 [$e addPoint 2153520 2836080]
$e newPath $emj1043 FIXED [RL M9]
set emch1268 [$e addPoint 1799280 2961360]
$e newPath $emj1044 FIXED [RL M9]
set emj1115 [$e addTechVia [V {VIA89}]]
$e newPath $emj1044 FIXED [RL M9]
set emj1116 [$e addPoint 1799280 3103920]
$e newPath $emj1049 FIXED [RL M9]
set emch1271 [$e addPoint 257040 3372705]
$e newPath $emj1050 FIXED [RL M9]
set emj1117 [$e addPoint 257040 3376080]
$e newPath $emj1051 FIXED [RL M9]
set emj1118 [$e addPoint 1285200 2944080]
$e newPath $emj1053 FIXED [RL M8]
set emj1119 [$e addPoint 1691280 3103920]
$e newPath $emj1054 FIXED [RL M9]
set emj1120 [$e addPoint 1367280 3104010]
$e newPath $emj1055 FIXED [RL M9]
set emch1276 [$e addPoint 1285200 2944080]
$e newPath $emj1055 FIXED [RL M9]
set emj1121 [$e addPoint 1285200 2945440]
$e newPath $emj1056 FIXED [RL M9]
set emj1122 [$e addPoint 1285200 3107340]
$e newPath $emj1056 FIXED [RL M9]
set emj1123 [$e addPoint 1285200 3108240]
$e newPath $emj1058 FIXED [RL M9]
set emch1280 [$e addPoint 771120 3372705]
$e newPath $emj1059 FIXED [RL M9]
set emj1124 [$e addPoint 771120 3376080]
$e newPath $emj1060 FIXED [RL M9]
set emj1125 [$e addTechVia [V {VIA89}]]
$e newPath $emj1060 FIXED [RL M9]
set emj1126 [$e addPoint 7959600 132705]
$e newPath $emj1061 FIXED [RL M9]
set emj1127 [$e addPoint 7959600 407340]
$e newPath $emj1061 FIXED [RL M9]
set emj1128 [$e addPoint 7959600 408240]
$e newPath $emj1062 FIXED [RL M8]
set emj1129 [$e addPoint 7238496 136080]
$e newPath $emj1062 FIXED [RL M8]
set emj1130 [$e addPoint 7629728 136080]
$e newPath $emj1063 FIXED [RL M9]
set emj1131 [$e addPoint 7445520 131760]
$e newPath $emj1063 FIXED [RL M9]
set emj1132 [$e addPoint 7445520 132660]
$e newPath $emj1064 FIXED [RL M9]
set emch1290 [$e addPoint 7445520 408240]
$e newPath $emj1065 FIXED [RL M9]
set emj1133 [$e addTechVia [V {VIA89}]]
$e newPath $emj1065 FIXED [RL M9]
set emj1134 [$e addPoint 7445520 675000]
$e newPath $emj1067 FIXED [RL M8]
set emch1293 [$e addPoint 7238496 136080]
$e newPath $emj1067 FIXED [RL M8]
set emj1135 [$e addTechVia [V {VIA89}]]
$e newPath $emj1068 FIXED [RL M9]
set emj1136 [$e addTechVia [V {VIA89}]]
$e newPath $emj1068 FIXED [RL M9]
set emj1137 [$e addPoint 6931440 15056]
$e newPath $emj1068 FIXED [RL M9]
set emch1297 [$e addPoint 6931440 132660]
$e newPath $emj1070 FIXED [RL M9]
set emj1138 [$e addTechVia [V {VIA89}]]
$e newPath $emj1070 FIXED [RL M9]
set emj1139 [$e addPoint 6931440 943920]
$e newPath $emj1071 FIXED [RL M9]
set emj1140 [$e addPoint 6845040 136170]
$e newPath $emj1072 FIXED [RL M8]
set emj1141 [$e addPoint 6845040 676080]
$e newPath $emj1073 FIXED [RL M9]
set emj1142 [$e addPoint 6469200 676170]
$e newPath $emj1074 FIXED [RL M8]
set emj1143 [$e addPoint 6931440 943920]
$e newPath $emj1075 FIXED [RL M9]
set emj1144 [$e addPoint 6387120 832500]
$e newPath $emj1076 FIXED [RL M9]
set emj1145 [$e addPoint 5907600 947340]
$e newPath $emj1076 FIXED [RL M9]
set emj1146 [$e addPoint 5907600 948240]
$e newPath $emj1077 FIXED [RL M8]
set emj1147 [$e addPoint 6931440 1216080]
$e newPath $emj1077 FIXED [RL M8]
set emj1148 [$e addTechVia [V {VIA89}]]
$e newPath $emj1080 FIXED [RL M9]
set emch1309 [$e addTechVia [V {VIA89}]]
$e newPath $emj1080 FIXED [RL M9]
set emj1149 [$e addPoint 6417360 1487295]
$e newPath $emj1082 FIXED [RL M9]
set emch1311 [$e addPoint 5907600 948240]
$e newPath $emj1082 FIXED [RL M9]
set emch1312 [$e addPoint 5907600 981810]
$e newPath $emj1084 FIXED [RL M8]
set emj1150 [$e addPoint 6659280 1483920]
$e newPath $emj1086 FIXED [RL M9]
set emch1314 [$e addPoint 5907600 1488240]
$e newPath $emj1087 FIXED [RL M9]
set emj1151 [$e addTechVia [V {VIA89}]]
$e newPath $emj1087 FIXED [RL M9]
set emj1152 [$e addPoint 5907600 1751760]
$e newPath $emj1088 FIXED [RL M8]
set emj1153 [$e addPoint 4892400 1756080]
$e newPath $emj1088 FIXED [RL M8]
set emj1154 [$e addTechVia [V {VIA89}]]
$e newPath $emj1089 FIXED [RL M8]
set emj1155 [$e addPoint 5933520 1756080]
$e newPath $emj1089 FIXED [RL M8]
set emj1156 [$e addTechVia [V {VIA89}]]
$e newPath $emj1090 FIXED [RL M8]
set emj1157 [$e addPoint 5320080 2023920]
$e newPath $emj1090 FIXED [RL M8]
set emj1158 [$e addPoint 5673376 2023920]
$e newPath $emj1091 FIXED [RL M9]
set emj1159 [$e addPoint 5393520 2291760]
$e newPath $emj1093 FIXED [RL M9]
set emch1324 [$e addPoint 4879440 1752705]
$e newPath $emj1094 FIXED [RL M9]
set emj1160 [$e addPoint 4879440 1756080]
$e newPath $emj1095 FIXED [RL M8]
set emj1161 [$e addPoint 4499616 1756080]
$e newPath $emj1095 FIXED [RL M8]
set emj1162 [$e addTechVia [V {VIA89}]]
$e newPath $emj1096 FIXED [RL M9]
set emj1163 [$e addPoint 4365360 2027340]
$e newPath $emj1096 FIXED [RL M9]
set emj1164 [$e addPoint 4365360 2028240]
$e newPath $emj1098 FIXED [RL M8]
set emj1165 [$e addPoint 5281200 2023920]
$e newPath $emj1098 FIXED [RL M8]
set emj1166 [$e addTechVia [V {VIA89}]]
$e newPath $emj1101 FIXED [RL M9]
set emj1167 [$e addPoint 3851280 2296080]
$e newPath $emj1102 FIXED [RL M9]
set emch1333 [$e addPoint 3337200 2162160]
$e newPath $emj1103 FIXED [RL M9]
set emj1168 [$e addTechVia [V {VIA89}]]
$e newPath $emj1103 FIXED [RL M9]
set emj1169 [$e addPoint 3337200 2295000]
$e newPath $emj1105 FIXED [RL M8]
set emj1170 [$e addPoint 3198048 2563920]
$e newPath $emj1105 FIXED [RL M8]
set emj1171 [$e addTechVia [V {VIA89}]]
$e newPath $emj1106 FIXED [RL M9]
set emj1172 [$e addPoint 2823120 2836080]
$e newPath $emj1107 FIXED [RL M8]
set emj1173 [$e addPoint 3324240 2296080]
$e newPath $emj1107 FIXED [RL M8]
set emj1174 [$e addTechVia [V {VIA89}]]
$e newPath $emj1110 FIXED [RL M9]
set emch1341 [$e addPoint 2309040 2669344]
$e newPath $emj1111 FIXED [RL M9]
set emj1175 [$e addPoint 2309040 2831760]
$e newPath $emj1113 FIXED [RL M9]
set emj1176 [$e addPoint 1786320 2840580]
$e newPath $emj1114 FIXED [RL M8]
set emj1177 [$e addPoint 2309040 2836080]
$e newPath $emj1114 FIXED [RL M8]
set emj1178 [$e addTechVia [V {VIA89}]]
$e newPath $emj1116 FIXED [RL M9]
set emj1179 [$e addTechVia [V {VIA89}]]
$e newPath $emj1116 FIXED [RL M9]
set emj1180 [$e addPoint 1799280 3105000]
$e newPath $emj1117 FIXED [RL M9]
set emj1181 [$e addTechVia [V {VIA89}]]
$e newPath $emj1117 FIXED [RL M9]
set emj1182 [$e addPoint 257040 3643920]
$e newPath $emj1118 FIXED [RL M9]
set emj1183 [$e addTechVia [V {VIA89}]]
$e newPath $emj1118 FIXED [RL M9]
set emch1351 [$e addPoint 1285200 2945440]
$e newPath $emj1119 FIXED [RL M8]
set emch1352 [$e addPoint 1799280 3103920]
$e newPath $emj1119 FIXED [RL M8]
set emj1184 [$e addTechVia [V {VIA89}]]
$e newPath $emj1122 FIXED [RL M9]
set emch1354 [$e addPoint 1285200 3108240]
$e newPath $emj1123 FIXED [RL M9]
set emj1185 [$e addTechVia [V {VIA89}]]
$e newPath $emj1123 FIXED [RL M9]
set emj1186 [$e addPoint 1285200 3375000]
$e newPath $emj1124 FIXED [RL M9]
set emj1187 [$e addTechVia [V {VIA89}]]
$e newPath $emj1124 FIXED [RL M9]
set emj1188 [$e addPoint 771120 3643920]
$e newPath $emj1125 FIXED [RL M8]
set emj1189 [$e addPoint 7631280 136080]
$e newPath $emj1125 FIXED [RL M8]
set emj1190 [$e addPoint 8020080 136080]
$e newPath $emj1126 FIXED [RL M9]
set emj1191 [$e addPoint 7959600 131760]
$e newPath $emj1126 FIXED [RL M9]
set emj1192 [$e addPoint 7959600 132660]
$e newPath $emj1127 FIXED [RL M9]
set emch1363 [$e addPoint 7959600 408240]
$e newPath $emj1128 FIXED [RL M9]
set emj1193 [$e addTechVia [V {VIA89}]]
$e newPath $emj1128 FIXED [RL M9]
set emj1194 [$e addPoint 7959600 589088]
$e newPath $emj1130 FIXED [RL M8]
set emch1366 [$e addPoint 7631280 136080]
$e newPath $emj1131 FIXED [RL M9]
set emj1195 [$e addTechVia [V {VIA89}]]
$e newPath $emj1131 FIXED [RL M9]
set emj1196 [$e addPoint 7445520 15056]
$e newPath $emj1131 FIXED [RL M9]
set emch1369 [$e addPoint 7445520 132660]
$e newPath $emj1134 FIXED [RL M9]
set emj1197 [$e addPoint 7445520 676080]
$e newPath $emj1135 FIXED [RL M9]
set emj1198 [$e addPoint 7238160 136170]
$e newPath $emj1138 FIXED [RL M8]
set emj1199 [$e addPoint 6892560 676080]
$e newPath $emj1138 FIXED [RL M8]
set emj1200 [$e addPoint 7332496 676080]
$e newPath $emj1139 FIXED [RL M9]
set emch1374 [$e addTechVia [V {VIA89}]]
$e newPath $emj1139 FIXED [RL M9]
set emj1201 [$e addPoint 6931440 945000]
$e newPath $emj1141 FIXED [RL M8]
set emj1202 [$e addPoint 6846688 676080]
$e newPath $emj1141 FIXED [RL M8]
set emj1203 [$e addTechVia [V {VIA89}]]
$e newPath $emj1143 FIXED [RL M8]
set emj1204 [$e addPoint 7013520 943920]
$e newPath $emj1145 FIXED [RL M9]
set emch1379 [$e addPoint 5907600 948240]
$e newPath $emj1146 FIXED [RL M9]
set emj1205 [$e addTechVia [V {VIA89}]]
$e newPath $emj1147 FIXED [RL M8]
set emj1206 [$e addPoint 7445520 1216080]
$e newPath $emj1147 FIXED [RL M8]
set emj1207 [$e addTechVia [V {VIA89}]]
$e newPath $emj1148 FIXED [RL M9]
set emj1208 [$e addPoint 6927120 1189260]
$e newPath $emj1149 FIXED [RL M9]
set emj1209 [$e addPoint 6417360 1487340]
$e newPath $emj1149 FIXED [RL M9]
set emj1210 [$e addPoint 6417360 1488240]
$e newPath $emj1150 FIXED [RL M8]
set emj1211 [$e addPoint 6931440 1483920]
$e newPath $emj1150 FIXED [RL M8]
set emj1212 [$e addTechVia [V {VIA89}]]
$e newPath $emj1152 FIXED [RL M9]
set emj1213 [$e addTechVia [V {VIA89}]]
$e newPath $emj1152 FIXED [RL M9]
set emj1214 [$e addPoint 5907600 1752660]
$e newPath $emj1152 FIXED [RL M9]
set emj1215 [$e addPoint 5907600 1752705]
$e newPath $emj1153 FIXED [RL M8]
set emj1216 [$e addPoint 4890848 1756080]
$e newPath $emj1153 FIXED [RL M8]
set emj1217 [$e addTechVia [V {VIA89}]]
$e newPath $emj1154 FIXED [RL M9]
set emj1218 [$e addPoint 5324400 1877940]
$e newPath $emj1155 FIXED [RL M8]
set emj1219 [$e addPoint 5935072 1756080]
$e newPath $emj1155 FIXED [RL M8]
set emj1220 [$e addTechVia [V {VIA89}]]
$e newPath $emj1156 FIXED [RL M9]
set emch1396 [$e addPoint 5907600 1752705]
$e newPath $emj1156 FIXED [RL M9]
set emj1221 [$e addPoint 5907600 2023920]
$e newPath $emj1157 FIXED [RL M8]
set emj1222 [$e addPoint 5282144 2023920]
$e newPath $emj1157 FIXED [RL M8]
set emj1223 [$e addTechVia [V {VIA89}]]
$e newPath $emj1158 FIXED [RL M8]
set emj1224 [$e addPoint 5674320 2023920]
$e newPath $emj1159 FIXED [RL M9]
set emj1225 [$e addTechVia [V {VIA89}]]
$e newPath $emj1159 FIXED [RL M9]
set emj1226 [$e addPoint 5393520 2292660]
$e newPath $emj1159 FIXED [RL M9]
set emj1227 [$e addPoint 5393520 2292705]
$e newPath $emj1160 FIXED [RL M9]
set emj1228 [$e addTechVia [V {VIA89}]]
$e newPath $emj1160 FIXED [RL M9]
set emch1405 [$e addPoint 4879440 2023920]
$e newPath $emj1161 FIXED [RL M8]
set emch1406 [$e addPoint 4879440 1756080]
$e newPath $emj1162 FIXED [RL M9]
set emj1229 [$e addPoint 4499280 1756170]
$e newPath $emj1163 FIXED [RL M9]
set emch1408 [$e addPoint 4365360 2028240]
$e newPath $emj1164 FIXED [RL M9]
set emj1230 [$e addTechVia [V {VIA89}]]
$e newPath $emj1164 FIXED [RL M9]
set emj1231 [$e addPoint 4365360 2160032]
$e newPath $emj1165 FIXED [RL M8]
set emch1411 [$e addPoint 5282144 2023920]
$e newPath $emj1165 FIXED [RL M8]
set emj1232 [$e addTechVia [V {VIA89}]]
$e newPath $emj1166 FIXED [RL M9]
set emj1233 [$e addPoint 4879440 2027295]
$e newPath $emj1167 FIXED [RL M9]
set emj1234 [$e addTechVia [V {VIA89}]]
$e newPath $emj1167 FIXED [RL M9]
set emj1235 [$e addPoint 3851280 2563920]
$e newPath $emj1169 FIXED [RL M9]
set emj1236 [$e addPoint 3337200 2296080]
$e newPath $emj1170 FIXED [RL M8]
set emj1237 [$e addPoint 3198960 2563920]
$e newPath $emj1171 FIXED [RL M9]
set emj1238 [$e addPoint 3194640 2567340]
$e newPath $emj1172 FIXED [RL M9]
set emj1239 [$e addTechVia [V {VIA89}]]
$e newPath $emj1172 FIXED [RL M9]
set emj1240 [$e addPoint 2823120 3103920]
$e newPath $emj1173 FIXED [RL M8]
set emj1241 [$e addPoint 3337200 2296080]
$e newPath $emj1173 FIXED [RL M8]
set emj1242 [$e addTechVia [V {VIA89}]]
$e newPath $emj1174 FIXED [RL M9]
set emj1243 [$e addPoint 3198960 2296170]
$e newPath $emj1175 FIXED [RL M9]
set emj1244 [$e addTechVia [V {VIA89}]]
$e newPath $emj1175 FIXED [RL M9]
set emj1245 [$e addPoint 2309040 2832660]
$e newPath $emj1175 FIXED [RL M9]
set emj1246 [$e addPoint 2309040 2832705]
$e newPath $emj1177 FIXED [RL M8]
set emj1247 [$e addPoint 2801520 2836080]
$e newPath $emj1177 FIXED [RL M8]
set emj1248 [$e addTechVia [V {VIA89}]]
$e newPath $emj1178 FIXED [RL M9]
set emj1249 [$e addPoint 2153520 2836170]
$e newPath $emj1179 FIXED [RL M8]
set emj1250 [$e addPoint 2309040 3103920]
$e newPath $emj1180 FIXED [RL M9]
set emj1251 [$e addPoint 1799280 3375000]
$e newPath $emj1181 FIXED [RL M8]
set emj1252 [$e addPoint 196560 3376080]
$e newPath $emj1181 FIXED [RL M8]
set emj1253 [$e addPoint 692768 3376080]
$e newPath $emj1182 FIXED [RL M9]
set emj1254 [$e addTechVia [V {VIA89}]]
$e newPath $emj1182 FIXED [RL M9]
set emj1255 [$e addPoint 257040 3647295]
$e newPath $emj1184 FIXED [RL M9]
set emj1256 [$e addPoint 1691280 3107340]
$e newPath $emj1186 FIXED [RL M9]
set emj1257 [$e addPoint 1285200 3376080]
$e newPath $emj1187 FIXED [RL M8]
set emj1258 [$e addPoint 693360 3376080]
$e newPath $emj1187 FIXED [RL M8]
set emj1259 [$e addPoint 978144 3376080]
$e newPath $emj1188 FIXED [RL M9]
set emj1260 [$e addTechVia [V {VIA89}]]
$e newPath $emj1188 FIXED [RL M9]
set emj1261 [$e addPoint 771120 3647295]
$e newPath $emj1189 FIXED [RL M8]
set emj1262 [$e addTechVia [V {VIA89}]]
$e newPath $emj1190 FIXED [RL M8]
set emj1263 [$e addPoint 8021024 136080]
$e newPath $emj1190 FIXED [RL M8]
set emj1264 [$e addTechVia [V {VIA89}]]
$e newPath $emj1191 FIXED [RL M9]
set emj1265 [$e addTechVia [V {VIA89}]]
$e newPath $emj1191 FIXED [RL M9]
set emj1266 [$e addPoint 7959600 15056]
$e newPath $emj1191 FIXED [RL M9]
set emch1447 [$e addPoint 7959600 132660]
$e newPath $emj1194 FIXED [RL M9]
set emj1267 [$e addPoint 7959600 589230]
$e newPath $emj1194 FIXED [RL M9]
set emj1268 [$e addPoint 7959600 589680]
$e newPath $emj1197 FIXED [RL M9]
set emj1269 [$e addTechVia [V {VIA89}]]
$e newPath $emj1197 FIXED [RL M9]
set emj1270 [$e addPoint 7445520 943920]
$e newPath $emj1199 FIXED [RL M8]
set emch1452 [$e addPoint 6846688 676080]
$e newPath $emj1199 FIXED [RL M8]
set emj1271 [$e addTechVia [V {VIA89}]]
$e newPath $emj1200 FIXED [RL M8]
set emj1272 [$e addPoint 7333200 676080]
$e newPath $emj1201 FIXED [RL M9]
set emj1273 [$e addPoint 6931440 1134000]
$e newPath $emj1203 FIXED [RL M9]
set emj1274 [$e addPoint 6845040 676170]
$e newPath $emj1204 FIXED [RL M8]
set emj1275 [$e addPoint 7445520 943920]
$e newPath $emj1204 FIXED [RL M8]
set emj1276 [$e addTechVia [V {VIA89}]]
$e newPath $emj1206 FIXED [RL M8]
set emj1277 [$e addPoint 7959600 1216080]
$e newPath $emj1206 FIXED [RL M8]
set emj1278 [$e addTechVia [V {VIA89}]]
$e newPath $emj1207 FIXED [RL M9]
set emj1279 [$e addPoint 6931440 1215000]
$e newPath $emj1207 FIXED [RL M9]
set emj1280 [$e addPoint 6931440 1483920]
$e newPath $emj1209 FIXED [RL M9]
set emch1463 [$e addPoint 6417360 1488240]
$e newPath $emj1210 FIXED [RL M9]
set emj1281 [$e addTechVia [V {VIA89}]]
$e newPath $emj1210 FIXED [RL M9]
set emj1282 [$e addPoint 6417360 1755000]
$e newPath $emj1211 FIXED [RL M8]
set emj1283 [$e addPoint 7445520 1483920]
$e newPath $emj1211 FIXED [RL M8]
set emch1467 [$e addTechVia [V {VIA89}]]
$e newPath $emj1212 FIXED [RL M9]
set emj1284 [$e addPoint 6659280 1509120]
$e newPath $emj1214 FIXED [RL M9]
set emch1469 [$e addPoint 5907600 1752705]
$e newPath $emj1216 FIXED [RL M8]
set emch1470 [$e addPoint 4879440 1756080]
$e newPath $emj1217 FIXED [RL M9]
set emj1285 [$e addPoint 4892400 1756170]
$e newPath $emj1219 FIXED [RL M8]
set emj1286 [$e addPoint 6296400 1756080]
$e newPath $emj1220 FIXED [RL M9]
set emj1287 [$e addPoint 5933520 1756170]
$e newPath $emj1221 FIXED [RL M9]
set emj1288 [$e addTechVia [V {VIA89}]]
$e newPath $emj1221 FIXED [RL M9]
set emj1289 [$e addPoint 5907600 2027295]
$e newPath $emj1223 FIXED [RL M9]
set emj1290 [$e addPoint 5320080 2031840]
$e newPath $emj1224 FIXED [RL M8]
set emch1477 [$e addPoint 5907600 2023920]
$e newPath $emj1224 FIXED [RL M8]
set emj1291 [$e addTechVia [V {VIA89}]]
$e newPath $emj1226 FIXED [RL M9]
set emch1479 [$e addPoint 5393520 2292705]
$e newPath $emj1227 FIXED [RL M9]
set emj1292 [$e addPoint 5393520 2296080]
$e newPath $emj1231 FIXED [RL M9]
set emj1293 [$e addPoint 4365360 2160090]
$e newPath $emj1231 FIXED [RL M9]
set emj1294 [$e addPoint 4365360 2162160]
$e newPath $emj1232 FIXED [RL M9]
set emj1295 [$e addPoint 5281200 2024010]
$e newPath $emj1233 FIXED [RL M9]
set emj1296 [$e addPoint 4879440 2027340]
$e newPath $emj1233 FIXED [RL M9]
set emj1297 [$e addPoint 4879440 2028240]
$e newPath $emj1234 FIXED [RL M8]
set emj1298 [$e addPoint 3838320 2296080]
$e newPath $emj1234 FIXED [RL M8]
set emj1299 [$e addPoint 4106160 2296080]
$e newPath $emj1235 FIXED [RL M9]
set emj1300 [$e addTechVia [V {VIA89}]]
$e newPath $emj1235 FIXED [RL M9]
set emj1301 [$e addPoint 3851280 2565000]
$e newPath $emj1236 FIXED [RL M9]
set emch1490 [$e addTechVia [V {VIA89}]]
$e newPath $emj1236 FIXED [RL M9]
set emj1302 [$e addPoint 3337200 2563920]
$e newPath $emj1237 FIXED [RL M8]
set emj1303 [$e addPoint 3281040 2563920]
$e newPath $emj1237 FIXED [RL M8]
set emj1304 [$e addTechVia [V {VIA89}]]
$e newPath $emj1239 FIXED [RL M8]
set emch1494 [$e addPoint 2801520 2836080]
$e newPath $emj1239 FIXED [RL M8]
set emj1305 [$e addPoint 3337200 2836080]
$e newPath $emj1240 FIXED [RL M9]
set emj1306 [$e addTechVia [V {VIA89}]]
$e newPath $emj1240 FIXED [RL M9]
set emj1307 [$e addPoint 2823120 3105000]
$e newPath $emj1241 FIXED [RL M8]
set emch1498 [$e addPoint 3838320 2296080]
$e newPath $emj1242 FIXED [RL M9]
set emj1308 [$e addPoint 3324240 2249460]
$e newPath $emj1245 FIXED [RL M9]
set emch1500 [$e addPoint 2309040 2832705]
$e newPath $emj1246 FIXED [RL M9]
set emch1501 [$e addPoint 2309040 2836080]
$e newPath $emj1247 FIXED [RL M8]
set emj1309 [$e addTechVia [V {VIA89}]]
$e newPath $emj1248 FIXED [RL M9]
set emj1310 [$e addPoint 2309040 3103920]
$e newPath $emj1250 FIXED [RL M8]
set emj1311 [$e addPoint 2322000 3103920]
$e newPath $emj1250 FIXED [RL M8]
set emch1505 [$e addTechVia [V {VIA89}]]
$e newPath $emj1251 FIXED [RL M9]
set emj1312 [$e addPoint 1799280 3376080]
$e newPath $emj1252 FIXED [RL M8]
set emj1313 [$e addPoint 195616 3376080]
$e newPath $emj1252 FIXED [RL M8]
set emj1314 [$e addTechVia [V {VIA89}]]
$e newPath $emj1253 FIXED [RL M8]
set emch1509 [$e addPoint 693360 3376080]
$e newPath $emj1254 FIXED [RL M8]
set emj1315 [$e addPoint 83472 3643920]
$e newPath $emj1254 FIXED [RL M8]
set emch1511 [$e addPoint 771120 3643920]
$e newPath $emj1255 FIXED [RL M9]
set emj1316 [$e addPoint 257040 3647340]
$e newPath $emj1255 FIXED [RL M9]
set emj1317 [$e addPoint 257040 3648240]
$e newPath $emj1257 FIXED [RL M9]
set emj1318 [$e addTechVia [V {VIA89}]]
$e newPath $emj1257 FIXED [RL M9]
set emj1319 [$e addPoint 1285200 3643920]
$e newPath $emj1258 FIXED [RL M8]
set emj1320 [$e addTechVia [V {VIA89}]]
$e newPath $emj1259 FIXED [RL M8]
set emj1321 [$e addPoint 978480 3376080]
$e newPath $emj1260 FIXED [RL M8]
set emj1322 [$e addPoint 978144 3643920]
$e newPath $emj1261 FIXED [RL M9]
set emj1323 [$e addPoint 771120 3647340]
$e newPath $emj1261 FIXED [RL M9]
set emj1324 [$e addPoint 771120 3648240]
$e newPath $emj1262 FIXED [RL M9]
set emj1325 [$e addPoint 7631280 136170]
$e newPath $emj1263 FIXED [RL M8]
set emj1326 [$e addPoint 8176368 136080]
$e newPath $emj1264 FIXED [RL M9]
set emj1327 [$e addPoint 8020080 136170]
$e newPath $emj1267 FIXED [RL M9]
set emch1524 [$e addPoint 7959600 589680]
$e newPath $emj1268 FIXED [RL M9]
set emj1328 [$e addTechVia [V {VIA89}]]
$e newPath $emj1268 FIXED [RL M9]
set emj1329 [$e addPoint 7959600 671760]
$e newPath $emj1269 FIXED [RL M8]
set emch1527 [$e addPoint 7333200 676080]
$e newPath $emj1269 FIXED [RL M8]
set emj1330 [$e addPoint 7449840 676080]
$e newPath $emj1270 FIXED [RL M9]
set emch1529 [$e addTechVia [V {VIA89}]]
$e newPath $emj1270 FIXED [RL M9]
set emj1331 [$e addPoint 7445520 947295]
$e newPath $emj1271 FIXED [RL M9]
set emj1332 [$e addPoint 6892560 689940]
$e newPath $emj1272 FIXED [RL M8]
set emj1333 [$e addTechVia [V {VIA89}]]
$e newPath $emj1273 FIXED [RL M9]
set emj1334 [$e addTechVia [V {VIA89}]]
$e newPath $emj1273 FIXED [RL M9]
set emj1335 [$e addPoint 6931440 1135170]
$e newPath $emj1273 FIXED [RL M9]
set emj1336 [$e addPoint 6931440 1135200]
$e newPath $emj1275 FIXED [RL M8]
set emj1337 [$e addPoint 7531920 943920]
$e newPath $emj1276 FIXED [RL M9]
set emj1338 [$e addPoint 7013520 1043100]
$e newPath $emj1277 FIXED [RL M8]
set emj1339 [$e addPoint 8176368 1216080]
$e newPath $emj1277 FIXED [RL M8]
set emj1340 [$e addTechVia [V {VIA89}]]
$e newPath $emj1278 FIXED [RL M9]
set emj1341 [$e addPoint 7445520 1212705]
$e newPath $emj1278 FIXED [RL M9]
set emj1342 [$e addPoint 7445520 1483920]
$e newPath $emj1279 FIXED [RL M9]
set emj1343 [$e addPoint 6931440 1182510]
$e newPath $emj1280 FIXED [RL M9]
set emj1344 [$e addPoint 6931440 1485000]
$e newPath $emj1282 FIXED [RL M9]
set emj1345 [$e addPoint 6417360 1756080]
$e newPath $emj1283 FIXED [RL M8]
set emj1346 [$e addPoint 7629728 1483920]
$e newPath $emj1283 FIXED [RL M8]
set emch1546 [$e addTechVia [V {VIA89}]]
$e newPath $emj1286 FIXED [RL M8]
set emj1347 [$e addPoint 6417360 1756080]
$e newPath $emj1286 FIXED [RL M8]
set emj1348 [$e addTechVia [V {VIA89}]]
$e newPath $emj1288 FIXED [RL M8]
set emj1349 [$e addPoint 6417360 2023920]
$e newPath $emj1289 FIXED [RL M9]
set emj1350 [$e addPoint 5907600 2027340]
$e newPath $emj1289 FIXED [RL M9]
set emj1351 [$e addPoint 5907600 2028240]
$e newPath $emj1291 FIXED [RL M9]
set emj1352 [$e addPoint 5674320 2024010]
$e newPath $emj1292 FIXED [RL M9]
set emj1353 [$e addTechVia [V {VIA89}]]
$e newPath $emj1292 FIXED [RL M9]
set emj1354 [$e addPoint 5393520 2451600]
$e newPath $emj1293 FIXED [RL M9]
set emch1555 [$e addPoint 4365360 2162160]
$e newPath $emj1294 FIXED [RL M9]
set emj1355 [$e addTechVia [V {VIA89}]]
$e newPath $emj1294 FIXED [RL M9]
set emj1356 [$e addPoint 4365360 2291760]
$e newPath $emj1296 FIXED [RL M9]
set emch1558 [$e addPoint 4879440 2028240]
$e newPath $emj1297 FIXED [RL M9]
set emj1357 [$e addTechVia [V {VIA89}]]
$e newPath $emj1297 FIXED [RL M9]
set emj1358 [$e addPoint 4879440 2160032]
$e newPath $emj1298 FIXED [RL M8]
set emj1359 [$e addTechVia [V {VIA89}]]
$e newPath $emj1299 FIXED [RL M8]
set emj1360 [$e addPoint 4107808 2296080]
$e newPath $emj1299 FIXED [RL M8]
set emj1361 [$e addTechVia [V {VIA89}]]
$e newPath $emj1300 FIXED [RL M8]
set emj1362 [$e addPoint 3337200 2563920]
$e newPath $emj1300 FIXED [RL M8]
set emj1363 [$e addPoint 3920400 2563920]
$e newPath $emj1301 FIXED [RL M9]
set emj1364 [$e addPoint 3851280 2831760]
$e newPath $emj1302 FIXED [RL M9]
set emch1567 [$e addTechVia [V {VIA89}]]
$e newPath $emj1302 FIXED [RL M9]
set emj1365 [$e addPoint 3337200 2565000]
$e newPath $emj1303 FIXED [RL M8]
set emj1366 [$e addPoint 3282592 2563920]
$e newPath $emj1303 FIXED [RL M8]
set emj1367 [$e addTechVia [V {VIA89}]]
$e newPath $emj1304 FIXED [RL M9]
set emj1368 [$e addPoint 3198960 2564010]
$e newPath $emj1305 FIXED [RL M8]
set emj1369 [$e addPoint 3557520 2836080]
$e newPath $emj1305 FIXED [RL M8]
set emj1370 [$e addTechVia [V {VIA89}]]
$e newPath $emj1306 FIXED [RL M8]
set emj1371 [$e addPoint 2805840 3103920]
$e newPath $emj1306 FIXED [RL M8]
set emj1372 [$e addPoint 2956496 3103920]
$e newPath $emj1307 FIXED [RL M9]
set emj1373 [$e addPoint 2823120 3371760]
$e newPath $emj1309 FIXED [RL M9]
set emj1374 [$e addPoint 2801520 2970900]
$e newPath $emj1310 FIXED [RL M9]
set emj1375 [$e addPoint 2309040 3105000]
$e newPath $emj1311 FIXED [RL M8]
set emj1376 [$e addPoint 2533680 3103920]
$e newPath $emj1311 FIXED [RL M8]
set emj1377 [$e addTechVia [V {VIA89}]]
$e newPath $emj1312 FIXED [RL M9]
set emj1378 [$e addTechVia [V {VIA89}]]
$e newPath $emj1312 FIXED [RL M9]
set emj1379 [$e addPoint 1799280 3643920]
$e newPath $emj1313 FIXED [RL M8]
set emj1380 [$e addPoint 83472 3376080]
$e newPath $emj1314 FIXED [RL M9]
set emj1381 [$e addPoint 196560 3376170]
$e newPath $emj1316 FIXED [RL M9]
set emch1585 [$e addPoint 257040 3648240]
$e newPath $emj1317 FIXED [RL M9]
set emj1382 [$e addTechVia [V {VIA89}]]
$e newPath $emj1317 FIXED [RL M9]
set emj1383 [$e addPoint 257040 3730320]
$e newPath $emj1318 FIXED [RL M8]
set emj1384 [$e addPoint 1142640 3376080]
$e newPath $emj1318 FIXED [RL M8]
set emj1385 [$e addPoint 1682640 3376080]
$e newPath $emj1319 FIXED [RL M9]
set emj1386 [$e addTechVia [V {VIA89}]]
$e newPath $emj1319 FIXED [RL M9]
set emj1387 [$e addPoint 1285200 3645000]
$e newPath $emj1320 FIXED [RL M9]
set emj1388 [$e addPoint 693360 3376170]
$e newPath $emj1321 FIXED [RL M8]
set emch1593 [$e addPoint 1142640 3376080]
$e newPath $emj1321 FIXED [RL M8]
set emj1389 [$e addTechVia [V {VIA89}]]
$e newPath $emj1322 FIXED [RL M8]
set emj1390 [$e addPoint 978480 3643920]
$e newPath $emj1323 FIXED [RL M9]
set emch1596 [$e addPoint 771120 3648240]
$e newPath $emj1324 FIXED [RL M9]
set emj1391 [$e addTechVia [V {VIA89}]]
$e newPath $emj1324 FIXED [RL M9]
set emj1392 [$e addPoint 771120 3730320]
$e newPath $emj1329 FIXED [RL M9]
set emj1393 [$e addTechVia [V {VIA89}]]
$e newPath $emj1329 FIXED [RL M9]
set emj1394 [$e addPoint 7959600 672660]
$e newPath $emj1329 FIXED [RL M9]
set emj1395 [$e addPoint 7959600 672705]
$e newPath $emj1330 FIXED [RL M8]
set emj1396 [$e addPoint 7664288 676080]
$e newPath $emj1330 FIXED [RL M8]
set emj1397 [$e addTechVia [V {VIA89}]]
$e newPath $emj1331 FIXED [RL M9]
set emj1398 [$e addPoint 7445520 947340]
$e newPath $emj1331 FIXED [RL M9]
set emj1399 [$e addPoint 7445520 948240]
$e newPath $emj1333 FIXED [RL M9]
set emj1400 [$e addPoint 7333200 676170]
$e newPath $emj1335 FIXED [RL M9]
set emch1607 [$e addPoint 6931440 1135200]
$e newPath $emj1336 FIXED [RL M9]
set emj1401 [$e addPoint 6931440 1181520]
$e newPath $emj1337 FIXED [RL M8]
set emj1402 [$e addPoint 7532512 943920]
$e newPath $emj1337 FIXED [RL M8]
set emj1403 [$e addTechVia [V {VIA89}]]
$e newPath $emj1340 FIXED [RL M9]
set emj1404 [$e addPoint 7959600 1215000]
$e newPath $emj1340 FIXED [RL M9]
set emj1405 [$e addPoint 7959600 1362060]
$e newPath $emj1341 FIXED [RL M9]
set emj1406 [$e addPoint 7445520 1211760]
$e newPath $emj1341 FIXED [RL M9]
set emj1407 [$e addPoint 7445520 1212660]
$e newPath $emj1342 FIXED [RL M9]
set emj1408 [$e addPoint 7445520 1487295]
$e newPath $emj1343 FIXED [RL M9]
set emch1616 [$e addPoint 6931440 1181520]
$e newPath $emj1343 FIXED [RL M9]
set emj1409 [$e addPoint 6931440 1182304]
$e newPath $emj1344 FIXED [RL M9]
set emj1410 [$e addPoint 6931440 1755000]
$e newPath $emj1345 FIXED [RL M9]
set emch1619 [$e addTechVia [V {VIA89}]]
$e newPath $emj1345 FIXED [RL M9]
set emj1411 [$e addPoint 6417360 2023920]
$e newPath $emj1346 FIXED [RL M8]
set emj1412 [$e addPoint 7631280 1483920]
$e newPath $emj1347 FIXED [RL M8]
set emj1413 [$e addPoint 6577200 1756080]
$e newPath $emj1348 FIXED [RL M9]
set emj1414 [$e addPoint 6296400 1812600]
$e newPath $emj1349 FIXED [RL M8]
set emj1415 [$e addPoint 6659280 2023920]
$e newPath $emj1349 FIXED [RL M8]
set emch1625 [$e addTechVia [V {VIA89}]]
$e newPath $emj1350 FIXED [RL M9]
set emch1626 [$e addPoint 5907600 2028240]
$e newPath $emj1351 FIXED [RL M9]
set emj1416 [$e addTechVia [V {VIA89}]]
$e newPath $emj1351 FIXED [RL M9]
set emj1417 [$e addPoint 5907600 2160032]
$e newPath $emj1353 FIXED [RL M8]
set emj1418 [$e addPoint 5282144 2296080]
$e newPath $emj1353 FIXED [RL M8]
set emj1419 [$e addPoint 5673376 2296080]
$e newPath $emj1354 FIXED [RL M9]
set emj1420 [$e addTechVia [V {VIA89}]]
$e newPath $emj1354 FIXED [RL M9]
set emj1421 [$e addPoint 5393520 2453310]
$e newPath $emj1354 FIXED [RL M9]
set emj1422 [$e addPoint 5393520 2453344]
$e newPath $emj1356 FIXED [RL M9]
set emj1423 [$e addTechVia [V {VIA89}]]
$e newPath $emj1356 FIXED [RL M9]
set emj1424 [$e addPoint 4365360 2292660]
$e newPath $emj1356 FIXED [RL M9]
set emj1425 [$e addPoint 4365360 2292705]
$e newPath $emj1358 FIXED [RL M9]
set emj1426 [$e addPoint 4879440 2160090]
$e newPath $emj1358 FIXED [RL M9]
set emj1427 [$e addPoint 4879440 2162160]
$e newPath $emj1359 FIXED [RL M9]
set emj1428 [$e addPoint 3838320 2249460]
$e newPath $emj1360 FIXED [RL M8]
set emj1429 [$e addPoint 4365360 2296080]
$e newPath $emj1361 FIXED [RL M9]
set emj1430 [$e addPoint 4106160 2296170]
$e newPath $emj1362 FIXED [RL M8]
set emj1431 [$e addPoint 3289680 2563920]
$e newPath $emj1363 FIXED [RL M8]
set emj1432 [$e addPoint 4283280 2563920]
$e newPath $emj1363 FIXED [RL M8]
set emj1433 [$e addTechVia [V {VIA89}]]
$e newPath $emj1364 FIXED [RL M9]
set emj1434 [$e addTechVia [V {VIA89}]]
$e newPath $emj1364 FIXED [RL M9]
set emj1435 [$e addPoint 3851280 2832660]
$e newPath $emj1364 FIXED [RL M9]
set emj1436 [$e addPoint 3851280 2832705]
$e newPath $emj1365 FIXED [RL M9]
set emj1437 [$e addPoint 3337200 2831760]
$e newPath $emj1366 FIXED [RL M8]
set emch1649 [$e addPoint 3289680 2563920]
$e newPath $emj1367 FIXED [RL M9]
set emj1438 [$e addPoint 3281040 2564010]
$e newPath $emj1369 FIXED [RL M8]
set emj1439 [$e addPoint 3559200 2836080]
$e newPath $emj1369 FIXED [RL M8]
set emj1440 [$e addTechVia [V {VIA89}]]
$e newPath $emj1370 FIXED [RL M9]
set emj1441 [$e addPoint 3337200 2832705]
$e newPath $emj1370 FIXED [RL M9]
set emj1442 [$e addPoint 3337200 2944080]
$e newPath $emj1371 FIXED [RL M8]
set emj1443 [$e addPoint 2535264 3103920]
$e newPath $emj1371 FIXED [RL M8]
set emj1444 [$e addTechVia [V {VIA89}]]
$e newPath $emj1372 FIXED [RL M8]
set emj1445 [$e addPoint 2957040 3103920]
$e newPath $emj1373 FIXED [RL M9]
set emj1446 [$e addTechVia [V {VIA89}]]
$e newPath $emj1373 FIXED [RL M9]
set emj1447 [$e addPoint 2823120 3372660]
$e newPath $emj1373 FIXED [RL M9]
set emj1448 [$e addPoint 2823120 3372705]
$e newPath $emj1375 FIXED [RL M9]
set emj1449 [$e addPoint 2309040 3371760]
$e newPath $emj1376 FIXED [RL M8]
set emch1662 [$e addPoint 2535264 3103920]
$e newPath $emj1376 FIXED [RL M8]
set emj1450 [$e addTechVia [V {VIA89}]]
$e newPath $emj1377 FIXED [RL M9]
set emj1451 [$e addPoint 2322000 3107340]
$e newPath $emj1378 FIXED [RL M8]
set emj1452 [$e addPoint 1691280 3376080]
$e newPath $emj1378 FIXED [RL M8]
set emj1453 [$e addPoint 2151968 3376080]
$e newPath $emj1379 FIXED [RL M9]
set emj1454 [$e addTechVia [V {VIA89}]]
$e newPath $emj1379 FIXED [RL M9]
set emj1455 [$e addPoint 1799280 3647295]
$e newPath $emj1383 FIXED [RL M9]
set emj1456 [$e addTechVia [V {VIA89}]]
$e newPath $emj1383 FIXED [RL M9]
set emj1457 [$e addPoint 257040 3730912]
$e newPath $emj1383 FIXED [RL M9]
set emj1458 [$e addPoint 257040 3730950]
$e newPath $emj1384 FIXED [RL M8]
set emj1459 [$e addTechVia [V {VIA89}]]
$e newPath $emj1385 FIXED [RL M8]
set emj1460 [$e addPoint 1682976 3376080]
$e newPath $emj1385 FIXED [RL M8]
set emj1461 [$e addTechVia [V {VIA89}]]
$e newPath $emj1386 FIXED [RL M8]
set emch1675 [$e addPoint 978480 3643920]
$e newPath $emj1386 FIXED [RL M8]
set emj1462 [$e addPoint 1293840 3643920]
$e newPath $emj1387 FIXED [RL M9]
set emj1463 [$e addPoint 1285200 3730320]
$e newPath $emj1389 FIXED [RL M9]
set emj1464 [$e addPoint 978480 3376170]
$e newPath $emj1390 FIXED [RL M8]
set emj1465 [$e addTechVia [V {VIA89}]]
$e newPath $emj1392 FIXED [RL M9]
set emj1466 [$e addTechVia [V {VIA89}]]
$e newPath $emj1392 FIXED [RL M9]
set emj1467 [$e addPoint 771120 3730912]
$e newPath $emj1392 FIXED [RL M9]
set emj1468 [$e addPoint 771120 3730950]
$e newPath $emj1394 FIXED [RL M9]
set emch1683 [$e addPoint 7959600 672705]
$e newPath $emj1395 FIXED [RL M9]
set emj1469 [$e addPoint 7959600 676080]
$e newPath $emj1396 FIXED [RL M8]
set emj1470 [$e addPoint 7665840 676080]
$e newPath $emj1397 FIXED [RL M9]
set emj1471 [$e addPoint 7449840 688140]
$e newPath $emj1398 FIXED [RL M9]
set emch1687 [$e addPoint 7445520 948240]
$e newPath $emj1399 FIXED [RL M9]
set emj1472 [$e addTechVia [V {VIA89}]]
$e newPath $emj1399 FIXED [RL M9]
set emj1473 [$e addPoint 7445520 1046610]
$e newPath $emj1401 FIXED [RL M9]
set emj1474 [$e addTechVia [V {VIA89}]]
$e newPath $emj1401 FIXED [RL M9]
set emch1691 [$e addPoint 6931440 1182304]
$e newPath $emj1402 FIXED [RL M8]
set emj1475 [$e addPoint 7950960 943920]
$e newPath $emj1403 FIXED [RL M9]
set emj1476 [$e addPoint 7531920 944010]
$e newPath $emj1404 FIXED [RL M9]
set emj1477 [$e addPoint 7959600 945000]
$e newPath $emj1405 FIXED [RL M9]
set emj1478 [$e addPoint 7959600 1483920]
$e newPath $emj1406 FIXED [RL M9]
set emj1479 [$e addTechVia [V {VIA89}]]
$e newPath $emj1406 FIXED [RL M9]
set emj1480 [$e addPoint 7445520 1182510]
$e newPath $emj1406 FIXED [RL M9]
set emch1698 [$e addPoint 7445520 1212660]
$e newPath $emj1408 FIXED [RL M9]
set emj1481 [$e addPoint 7445520 1487340]
$e newPath $emj1408 FIXED [RL M9]
set emj1482 [$e addPoint 7445520 1488240]
$e newPath $emj1410 FIXED [RL M9]
set emj1483 [$e addPoint 6931440 1756080]
$e newPath $emj1411 FIXED [RL M9]
set emj1484 [$e addPoint 6417360 2027295]
$e newPath $emj1412 FIXED [RL M8]
set emj1485 [$e addPoint 7959600 1483920]
$e newPath $emj1412 FIXED [RL M8]
set emj1486 [$e addTechVia [V {VIA89}]]
$e newPath $emj1413 FIXED [RL M8]
set emj1487 [$e addPoint 6578848 1756080]
$e newPath $emj1413 FIXED [RL M8]
set emj1488 [$e addTechVia [V {VIA89}]]
$e newPath $emj1415 FIXED [RL M8]
set emj1489 [$e addPoint 6931440 2023920]
$e newPath $emj1415 FIXED [RL M8]
set emj1490 [$e addTechVia [V {VIA89}]]
$e newPath $emj1417 FIXED [RL M9]
set emj1491 [$e addPoint 5907600 2160090]
$e newPath $emj1417 FIXED [RL M9]
set emj1492 [$e addPoint 5907600 2162160]
$e newPath $emj1418 FIXED [RL M8]
set emj1493 [$e addPoint 5281200 2296080]
$e newPath $emj1419 FIXED [RL M8]
set emj1494 [$e addPoint 5674320 2296080]
$e newPath $emj1421 FIXED [RL M9]
set emch1713 [$e addPoint 5393520 2453344]
$e newPath $emj1422 FIXED [RL M9]
set emj1495 [$e addPoint 5393520 2563920]
$e newPath $emj1424 FIXED [RL M9]
set emch1715 [$e addPoint 4365360 2292705]
$e newPath $emj1425 FIXED [RL M9]
set emj1496 [$e addPoint 4365360 2296080]
$e newPath $emj1426 FIXED [RL M9]
set emch1717 [$e addPoint 4879440 2162160]
$e newPath $emj1427 FIXED [RL M9]
set emj1497 [$e addTechVia [V {VIA89}]]
$e newPath $emj1427 FIXED [RL M9]
set emj1498 [$e addPoint 4879440 2291760]
$e newPath $emj1429 FIXED [RL M8]
set emj1499 [$e addPoint 4879440 2296080]
$e newPath $emj1429 FIXED [RL M8]
set emch1721 [$e addTechVia [V {VIA89}]]
$e newPath $emj1431 FIXED [RL M8]
set emj1500 [$e addTechVia [V {VIA89}]]
$e newPath $emj1432 FIXED [RL M8]
set emj1501 [$e addPoint 4365360 2563920]
$e newPath $emj1432 FIXED [RL M8]
set emj1502 [$e addTechVia [V {VIA89}]]
$e newPath $emj1433 FIXED [RL M9]
set emj1503 [$e addPoint 3920400 2567340]
$e newPath $emj1435 FIXED [RL M9]
set emch1726 [$e addPoint 3851280 2832705]
$e newPath $emj1436 FIXED [RL M9]
set emj1504 [$e addPoint 3851280 2836080]
$e newPath $emj1437 FIXED [RL M9]
set emj1505 [$e addTechVia [V {VIA89}]]
$e newPath $emj1437 FIXED [RL M9]
set emj1506 [$e addPoint 3337200 2832660]
$e newPath $emj1437 FIXED [RL M9]
set emch1730 [$e addPoint 3337200 2832705]
$e newPath $emj1439 FIXED [RL M8]
set emj1507 [$e addPoint 3643920 2836080]
$e newPath $emj1440 FIXED [RL M9]
set emj1508 [$e addPoint 3557520 2836170]
$e newPath $emj1441 FIXED [RL M9]
set emch1733 [$e addPoint 3337200 2832660]
$e newPath $emj1442 FIXED [RL M9]
set emj1509 [$e addTechVia [V {VIA89}]]
$e newPath $emj1442 FIXED [RL M9]
set emj1510 [$e addPoint 3337200 2945440]
$e newPath $emj1442 FIXED [RL M9]
set emj1511 [$e addPoint 3337200 2945610]
$e newPath $emj1444 FIXED [RL M9]
set emj1512 [$e addPoint 2805840 3109140]
$e newPath $emj1445 FIXED [RL M8]
set emj1513 [$e addPoint 3289680 3103920]
$e newPath $emj1445 FIXED [RL M8]
set emj1514 [$e addTechVia [V {VIA89}]]
$e newPath $emj1447 FIXED [RL M9]
set emch1740 [$e addPoint 2823120 3372705]
$e newPath $emj1448 FIXED [RL M9]
set emj1515 [$e addPoint 2823120 3376080]
$e newPath $emj1449 FIXED [RL M9]
set emj1516 [$e addTechVia [V {VIA89}]]
$e newPath $emj1449 FIXED [RL M9]
set emj1517 [$e addPoint 2309040 3372660]
$e newPath $emj1449 FIXED [RL M9]
set emj1518 [$e addPoint 2309040 3372705]
$e newPath $emj1450 FIXED [RL M9]
set emj1519 [$e addPoint 2533680 3104010]
$e newPath $emj1452 FIXED [RL M8]
set emch1746 [$e addPoint 1682976 3376080]
$e newPath $emj1452 FIXED [RL M8]
set emj1520 [$e addTechVia [V {VIA89}]]
$e newPath $emj1453 FIXED [RL M8]
set emj1521 [$e addPoint 2153520 3376080]
$e newPath $emj1454 FIXED [RL M8]
set emch1749 [$e addPoint 1293840 3643920]
$e newPath $emj1454 FIXED [RL M8]
set emj1522 [$e addPoint 2309040 3643920]
$e newPath $emj1455 FIXED [RL M9]
set emj1523 [$e addPoint 1799280 3647340]
$e newPath $emj1455 FIXED [RL M9]
set emj1524 [$e addPoint 1799280 3648240]
$e newPath $emj1457 FIXED [RL M9]
set emch1753 [$e addPoint 257040 3730950]
$e newPath $emj1458 FIXED [RL M9]
set emj1525 [$e addPoint 257040 3911760]
$e newPath $emj1459 FIXED [RL M9]
set emj1526 [$e addPoint 1142640 3388140]
$e newPath $emj1461 FIXED [RL M9]
set emj1527 [$e addPoint 1682640 3376170]
$e newPath $emj1462 FIXED [RL M8]
set emj1528 [$e addTechVia [V {VIA89}]]
$e newPath $emj1463 FIXED [RL M9]
set emj1529 [$e addTechVia [V {VIA89}]]
$e newPath $emj1463 FIXED [RL M9]
set emj1530 [$e addPoint 1285200 3730912]
$e newPath $emj1463 FIXED [RL M9]
set emj1531 [$e addPoint 1285200 3730950]
$e newPath $emj1465 FIXED [RL M9]
set emj1532 [$e addPoint 978480 3644010]
$e newPath $emj1467 FIXED [RL M9]
set emch1762 [$e addPoint 771120 3730950]
$e newPath $emj1468 FIXED [RL M9]
set emj1533 [$e addPoint 771120 3911760]
$e newPath $emj1469 FIXED [RL M9]
set emj1534 [$e addTechVia [V {VIA89}]]
$e newPath $emj1469 FIXED [RL M9]
set emj1535 [$e addPoint 7959600 827280]
$e newPath $emj1470 FIXED [RL M8]
set emch1766 [$e addPoint 7959600 676080]
$e newPath $emj1470 FIXED [RL M8]
set emj1536 [$e addTechVia [V {VIA89}]]
$e newPath $emj1473 FIXED [RL M9]
set emj1537 [$e addPoint 7445520 1046624]
$e newPath $emj1473 FIXED [RL M9]
set emj1538 [$e addPoint 7445520 1047600]
$e newPath $emj1475 FIXED [RL M8]
set emj1539 [$e addPoint 7959600 943920]
$e newPath $emj1475 FIXED [RL M8]
set emj1540 [$e addTechVia [V {VIA89}]]
$e newPath $emj1477 FIXED [RL M9]
set emj1541 [$e addPoint 7959600 943920]
$e newPath $emj1478 FIXED [RL M9]
set emch1773 [$e addTechVia [V {VIA89}]]
$e newPath $emj1478 FIXED [RL M9]
set emj1542 [$e addPoint 7959600 1485000]
$e newPath $emj1480 FIXED [RL M9]
set emj1543 [$e addPoint 7445520 1181520]
$e newPath $emj1480 FIXED [RL M9]
set emj1544 [$e addPoint 7445520 1182304]
$e newPath $emj1481 FIXED [RL M9]
set emch1777 [$e addPoint 7445520 1488240]
$e newPath $emj1482 FIXED [RL M9]
set emj1545 [$e addTechVia [V {VIA89}]]
$e newPath $emj1482 FIXED [RL M9]
set emj1546 [$e addPoint 7445520 1751760]
$e newPath $emj1483 FIXED [RL M9]
set emj1547 [$e addTechVia [V {VIA89}]]
$e newPath $emj1483 FIXED [RL M9]
set emj1548 [$e addPoint 6931440 2023920]
$e newPath $emj1484 FIXED [RL M9]
set emj1549 [$e addPoint 6417360 2027340]
$e newPath $emj1484 FIXED [RL M9]
set emj1550 [$e addPoint 6417360 2028240]
$e newPath $emj1485 FIXED [RL M8]
set emj1551 [$e addPoint 7972560 1483920]
$e newPath $emj1486 FIXED [RL M9]
set emj1552 [$e addPoint 7631280 1484010]
$e newPath $emj1487 FIXED [RL M8]
set emj1553 [$e addPoint 6611744 1756080]
$e newPath $emj1488 FIXED [RL M9]
set emj1554 [$e addPoint 6577200 1756170]
$e newPath $emj1489 FIXED [RL M8]
set emj1555 [$e addPoint 7445520 2023920]
$e newPath $emj1489 FIXED [RL M8]
set emch1789 [$e addTechVia [V {VIA89}]]
$e newPath $emj1490 FIXED [RL M9]
set emj1556 [$e addPoint 6659280 2049120]
$e newPath $emj1491 FIXED [RL M9]
set emch1791 [$e addPoint 5907600 2162160]
$e newPath $emj1492 FIXED [RL M9]
set emj1557 [$e addTechVia [V {VIA89}]]
$e newPath $emj1492 FIXED [RL M9]
set emj1558 [$e addPoint 5907600 2291760]
$e newPath $emj1493 FIXED [RL M8]
set emch1794 [$e addPoint 4879440 2296080]
$e newPath $emj1493 FIXED [RL M8]
set emj1559 [$e addTechVia [V {VIA89}]]
$e newPath $emj1494 FIXED [RL M8]
set emj1560 [$e addPoint 5907600 2296080]
$e newPath $emj1494 FIXED [RL M8]
set emj1561 [$e addTechVia [V {VIA89}]]
$e newPath $emj1495 FIXED [RL M9]
set emj1562 [$e addTechVia [V {VIA89}]]
$e newPath $emj1495 FIXED [RL M9]
set emj1563 [$e addPoint 5393520 2565000]
$e newPath $emj1496 FIXED [RL M9]
set emj1564 [$e addPoint 4365360 2563920]
$e newPath $emj1498 FIXED [RL M9]
set emj1565 [$e addTechVia [V {VIA89}]]
$e newPath $emj1498 FIXED [RL M9]
set emj1566 [$e addPoint 4879440 2292660]
$e newPath $emj1498 FIXED [RL M9]
set emj1567 [$e addPoint 4879440 2292705]
$e newPath $emj1499 FIXED [RL M8]
set emj1568 [$e addTechVia [V {VIA89}]]
$e newPath $emj1500 FIXED [RL M9]
set emj1569 [$e addPoint 3289680 2569140]
$e newPath $emj1501 FIXED [RL M8]
set emj1570 [$e addPoint 4532192 2563920]
$e newPath $emj1501 FIXED [RL M8]
set emch1807 [$e addTechVia [V {VIA89}]]
$e newPath $emj1502 FIXED [RL M9]
set emj1571 [$e addPoint 4283280 2567340]
$e newPath $emj1504 FIXED [RL M9]
set emj1572 [$e addTechVia [V {VIA89}]]
$e newPath $emj1504 FIXED [RL M9]
set emj1573 [$e addPoint 3851280 3103920]
$e newPath $emj1507 FIXED [RL M8]
set emj1574 [$e addPoint 3645600 2836080]
$e newPath $emj1507 FIXED [RL M8]
set emj1575 [$e addTechVia [V {VIA89}]]
$e newPath $emj1510 FIXED [RL M9]
set emch1813 [$e addPoint 3337200 2945610]
$e newPath $emj1511 FIXED [RL M9]
set emj1576 [$e addPoint 3337200 3103920]
$e newPath $emj1513 FIXED [RL M8]
set emj1577 [$e addPoint 3337200 3103920]
$e newPath $emj1513 FIXED [RL M8]
set emj1578 [$e addTechVia [V {VIA89}]]
$e newPath $emj1514 FIXED [RL M9]
set emj1579 [$e addPoint 2957040 3104010]
$e newPath $emj1515 FIXED [RL M9]
set emj1580 [$e addTechVia [V {VIA89}]]
$e newPath $emj1515 FIXED [RL M9]
set emj1581 [$e addPoint 2823120 3643920]
$e newPath $emj1517 FIXED [RL M9]
set emch1820 [$e addPoint 2309040 3372705]
$e newPath $emj1518 FIXED [RL M9]
set emj1582 [$e addPoint 2309040 3376080]
$e newPath $emj1520 FIXED [RL M9]
set emj1583 [$e addPoint 1691280 3372660]
$e newPath $emj1521 FIXED [RL M8]
set emj1584 [$e addPoint 2309040 3376080]
$e newPath $emj1521 FIXED [RL M8]
set emj1585 [$e addTechVia [V {VIA89}]]
$e newPath $emj1522 FIXED [RL M8]
set emj1586 [$e addPoint 2542320 3643920]
$e newPath $emj1522 FIXED [RL M8]
set emj1587 [$e addTechVia [V {VIA89}]]
$e newPath $emj1523 FIXED [RL M9]
set emch1827 [$e addPoint 1799280 3648240]
$e newPath $emj1524 FIXED [RL M9]
set emj1588 [$e addTechVia [V {VIA89}]]
$e newPath $emj1524 FIXED [RL M9]
set emj1589 [$e addPoint 1799280 3730320]
$e newPath $emj1525 FIXED [RL M9]
set emj1590 [$e addTechVia [V {VIA89}]]
$e newPath $emj1525 FIXED [RL M9]
set emj1591 [$e addPoint 257040 3912660]
$e newPath $emj1525 FIXED [RL M9]
set emj1592 [$e addPoint 257040 3912705]
$e newPath $emj1528 FIXED [RL M9]
set emj1593 [$e addPoint 1293840 3668940]
$e newPath $emj1530 FIXED [RL M9]
set emch1834 [$e addPoint 1285200 3730950]
$e newPath $emj1531 FIXED [RL M9]
set emj1594 [$e addPoint 1285200 3911760]
$e newPath $emj1533 FIXED [RL M9]
set emj1595 [$e addTechVia [V {VIA89}]]
$e newPath $emj1533 FIXED [RL M9]
set emj1596 [$e addPoint 771120 3912660]
$e newPath $emj1533 FIXED [RL M9]
set emj1597 [$e addPoint 771120 3912705]
$e newPath $emj1534 FIXED [RL M8]
set emj1598 [$e addPoint 8176368 676080]
$e newPath $emj1535 FIXED [RL M9]
set emj1599 [$e addTechVia [V {VIA89}]]
$e newPath $emj1535 FIXED [RL M9]
set emj1600 [$e addPoint 7959600 828448]
$e newPath $emj1535 FIXED [RL M9]
set emj1601 [$e addPoint 7959600 828450]
$e newPath $emj1536 FIXED [RL M9]
set emj1602 [$e addPoint 7665840 676170]
$e newPath $emj1537 FIXED [RL M9]
set emch1844 [$e addPoint 7445520 1047600]
$e newPath $emj1538 FIXED [RL M9]
set emj1603 [$e addTechVia [V {VIA89}]]
$e newPath $emj1538 FIXED [RL M9]
set emch1846 [$e addPoint 7445520 1181520]
$e newPath $emj1539 FIXED [RL M8]
set emj1604 [$e addPoint 8176368 943920]
$e newPath $emj1539 FIXED [RL M8]
set emch1848 [$e addTechVia [V {VIA89}]]
$e newPath $emj1540 FIXED [RL M9]
set emj1605 [$e addPoint 7950960 832500]
$e newPath $emj1541 FIXED [RL M9]
set emch1850 [$e addPoint 7959600 828450]
$e newPath $emj1542 FIXED [RL M9]
set emj1606 [$e addPoint 7959600 1755000]
$e newPath $emj1543 FIXED [RL M9]
set emj1607 [$e addTechVia [V {VIA89}]]
$e newPath $emj1543 FIXED [RL M9]
set emch1853 [$e addPoint 7445520 1182304]
$e newPath $emj1546 FIXED [RL M9]
set emj1608 [$e addTechVia [V {VIA89}]]
$e newPath $emj1546 FIXED [RL M9]
set emj1609 [$e addPoint 7445520 1752660]
$e newPath $emj1546 FIXED [RL M9]
set emj1610 [$e addPoint 7445520 1752705]
$e newPath $emj1547 FIXED [RL M8]
set emj1611 [$e addPoint 6659280 1756080]
$e newPath $emj1547 FIXED [RL M8]
set emj1612 [$e addPoint 7445520 1756080]
$e newPath $emj1548 FIXED [RL M9]
set emj1613 [$e addPoint 6931440 2025000]
$e newPath $emj1549 FIXED [RL M9]
set emch1860 [$e addPoint 6417360 2028240]
$e newPath $emj1550 FIXED [RL M9]
set emj1614 [$e addTechVia [V {VIA89}]]
$e newPath $emj1550 FIXED [RL M9]
set emj1615 [$e addPoint 6417360 2160032]
$e newPath $emj1551 FIXED [RL M8]
set emj1616 [$e addPoint 8087968 1483920]
$e newPath $emj1551 FIXED [RL M8]
set emj1617 [$e addTechVia [V {VIA89}]]
$e newPath $emj1553 FIXED [RL M8]
set emj1618 [$e addPoint 6611760 1756080]
$e newPath $emj1555 FIXED [RL M8]
set emj1619 [$e addPoint 7629728 2023920]
$e newPath $emj1555 FIXED [RL M8]
set emj1620 [$e addTechVia [V {VIA89}]]
$e newPath $emj1558 FIXED [RL M9]
set emj1621 [$e addTechVia [V {VIA89}]]
$e newPath $emj1558 FIXED [RL M9]
set emj1622 [$e addPoint 5907600 2292660]
$e newPath $emj1558 FIXED [RL M9]
set emj1623 [$e addPoint 5907600 2292705]
$e newPath $emj1559 FIXED [RL M9]
set emj1624 [$e addPoint 5281200 2296170]
$e newPath $emj1560 FIXED [RL M8]
set emj1625 [$e addPoint 6404400 2296080]
$e newPath $emj1560 FIXED [RL M8]
set emj1626 [$e addTechVia [V {VIA89}]]
$e newPath $emj1561 FIXED [RL M9]
set emj1627 [$e addPoint 5674320 2296170]
$e newPath $emj1562 FIXED [RL M8]
set emj1628 [$e addPoint 4879440 2563920]
$e newPath $emj1562 FIXED [RL M8]
set emj1629 [$e addPoint 5432400 2563920]
$e newPath $emj1563 FIXED [RL M9]
set emj1630 [$e addPoint 5393520 2831760]
$e newPath $emj1564 FIXED [RL M9]
set emj1631 [$e addPoint 4365360 2565000]
$e newPath $emj1566 FIXED [RL M9]
set emch1879 [$e addPoint 4879440 2292705]
$e newPath $emj1567 FIXED [RL M9]
set emch1880 [$e addPoint 4879440 2296080]
$e newPath $emj1568 FIXED [RL M9]
set emj1632 [$e addPoint 4879440 2451600]
$e newPath $emj1570 FIXED [RL M8]
set emj1633 [$e addPoint 4533840 2563920]
$e newPath $emj1572 FIXED [RL M8]
set emch1883 [$e addPoint 3645600 2836080]
$e newPath $emj1572 FIXED [RL M8]
set emj1634 [$e addPoint 4106160 2836080]
$e newPath $emj1573 FIXED [RL M9]
set emj1635 [$e addTechVia [V {VIA89}]]
$e newPath $emj1573 FIXED [RL M9]
set emj1636 [$e addPoint 3851280 3105000]
$e newPath $emj1575 FIXED [RL M9]
set emj1637 [$e addPoint 3643920 2836170]
$e newPath $emj1576 FIXED [RL M9]
set emch1888 [$e addTechVia [V {VIA89}]]
$e newPath $emj1576 FIXED [RL M9]
set emj1638 [$e addPoint 3337200 3105000]
$e newPath $emj1577 FIXED [RL M8]
set emch1890 [$e addPoint 3851280 3103920]
$e newPath $emj1578 FIXED [RL M9]
set emj1639 [$e addPoint 3289680 3109140]
$e newPath $emj1580 FIXED [RL M8]
set emj1640 [$e addPoint 2543264 3376080]
$e newPath $emj1580 FIXED [RL M8]
set emj1641 [$e addPoint 2934496 3376080]
$e newPath $emj1581 FIXED [RL M9]
set emj1642 [$e addTechVia [V {VIA89}]]
$e newPath $emj1581 FIXED [RL M9]
set emj1643 [$e addPoint 2823120 3647295]
$e newPath $emj1582 FIXED [RL M9]
set emch1896 [$e addTechVia [V {VIA89}]]
$e newPath $emj1582 FIXED [RL M9]
set emch1897 [$e addPoint 2309040 3643920]
$e newPath $emj1584 FIXED [RL M8]
set emj1644 [$e addPoint 2542320 3376080]
$e newPath $emj1585 FIXED [RL M9]
set emj1645 [$e addPoint 2153520 3376170]
$e newPath $emj1586 FIXED [RL M8]
set emj1646 [$e addPoint 2543264 3643920]
$e newPath $emj1586 FIXED [RL M8]
set emj1647 [$e addTechVia [V {VIA89}]]
$e newPath $emj1587 FIXED [RL M9]
set emj1648 [$e addPoint 2309040 3647295]
$e newPath $emj1589 FIXED [RL M9]
set emj1649 [$e addTechVia [V {VIA89}]]
$e newPath $emj1589 FIXED [RL M9]
set emj1650 [$e addPoint 1799280 3730912]
$e newPath $emj1589 FIXED [RL M9]
set emj1651 [$e addPoint 1799280 3730950]
$e newPath $emj1591 FIXED [RL M9]
set emch1906 [$e addPoint 257040 3912705]
$e newPath $emj1592 FIXED [RL M9]
set emj1652 [$e addPoint 257040 3916080]
$e newPath $emj1594 FIXED [RL M9]
set emj1653 [$e addTechVia [V {VIA89}]]
$e newPath $emj1594 FIXED [RL M9]
set emj1654 [$e addPoint 1285200 3912660]
$e newPath $emj1594 FIXED [RL M9]
set emj1655 [$e addPoint 1285200 3912705]
$e newPath $emj1596 FIXED [RL M9]
set emch1911 [$e addPoint 771120 3912705]
$e newPath $emj1597 FIXED [RL M9]
set emj1656 [$e addPoint 771120 3916080]
$e newPath $emj1600 FIXED [RL M9]
set emch1913 [$e addPoint 7959600 828450]
$e newPath $emj1606 FIXED [RL M9]
set emj1657 [$e addPoint 7959600 1756080]
$e newPath $emj1609 FIXED [RL M9]
set emch1915 [$e addPoint 7445520 1752705]
$e newPath $emj1610 FIXED [RL M9]
set emj1658 [$e addPoint 7445520 1756080]
$e newPath $emj1611 FIXED [RL M8]
set emch1917 [$e addPoint 6611760 1756080]
$e newPath $emj1611 FIXED [RL M8]
set emj1659 [$e addTechVia [V {VIA89}]]
$e newPath $emj1612 FIXED [RL M8]
set emj1660 [$e addPoint 7531920 1756080]
$e newPath $emj1612 FIXED [RL M8]
set emch1920 [$e addTechVia [V {VIA89}]]
$e newPath $emj1613 FIXED [RL M9]
set emj1661 [$e addPoint 6931440 2295000]
$e newPath $emj1615 FIXED [RL M9]
set emj1662 [$e addPoint 6417360 2160090]
$e newPath $emj1615 FIXED [RL M9]
set emj1663 [$e addPoint 6417360 2162160]
$e newPath $emj1616 FIXED [RL M8]
set emj1664 [$e addPoint 8089200 1483920]
$e newPath $emj1617 FIXED [RL M9]
set emj1665 [$e addPoint 7972560 1543500]
$e newPath $emj1618 FIXED [RL M8]
set emj1666 [$e addTechVia [V {VIA89}]]
$e newPath $emj1619 FIXED [RL M8]
set emj1667 [$e addPoint 7631280 2023920]
$e newPath $emj1620 FIXED [RL M9]
set emj1668 [$e addPoint 7445520 1769040]
$e newPath $emj1620 FIXED [RL M9]
set emj1669 [$e addPoint 7445520 2027295]
$e newPath $emj1622 FIXED [RL M9]
set emch1930 [$e addPoint 5907600 2292705]
$e newPath $emj1623 FIXED [RL M9]
set emch1931 [$e addPoint 5907600 2296080]
$e newPath $emj1625 FIXED [RL M8]
set emj1670 [$e addPoint 6417360 2296080]
$e newPath $emj1625 FIXED [RL M8]
set emj1671 [$e addTechVia [V {VIA89}]]
$e newPath $emj1626 FIXED [RL M9]
set emj1672 [$e addPoint 5907600 2563920]
$e newPath $emj1628 FIXED [RL M8]
set emj1673 [$e addPoint 4793040 2563920]
$e newPath $emj1628 FIXED [RL M8]
set emj1674 [$e addTechVia [V {VIA89}]]
$e newPath $emj1629 FIXED [RL M8]
set emj1675 [$e addPoint 5673376 2563920]
$e newPath $emj1629 FIXED [RL M8]
set emj1676 [$e addTechVia [V {VIA89}]]
$e newPath $emj1630 FIXED [RL M9]
set emj1677 [$e addTechVia [V {VIA89}]]
$e newPath $emj1630 FIXED [RL M9]
set emj1678 [$e addPoint 5393520 2832660]
$e newPath $emj1630 FIXED [RL M9]
set emj1679 [$e addPoint 5393520 2832705]
$e newPath $emj1631 FIXED [RL M9]
set emj1680 [$e addPoint 4365360 2831760]
$e newPath $emj1632 FIXED [RL M9]
set emj1681 [$e addTechVia [V {VIA89}]]
$e newPath $emj1632 FIXED [RL M9]
set emj1682 [$e addPoint 4879440 2453310]
$e newPath $emj1632 FIXED [RL M9]
set emj1683 [$e addPoint 4879440 2453344]
$e newPath $emj1633 FIXED [RL M8]
set emch1946 [$e addPoint 4793040 2563920]
$e newPath $emj1633 FIXED [RL M8]
set emj1684 [$e addTechVia [V {VIA89}]]
$e newPath $emj1634 FIXED [RL M8]
set emj1685 [$e addPoint 4107808 2836080]
$e newPath $emj1634 FIXED [RL M8]
set emj1686 [$e addTechVia [V {VIA89}]]
$e newPath $emj1635 FIXED [RL M8]
set emj1687 [$e addPoint 3920400 3103920]
$e newPath $emj1636 FIXED [RL M9]
set emj1688 [$e addPoint 3851280 3375000]
$e newPath $emj1638 FIXED [RL M9]
set emj1689 [$e addPoint 3337200 3371760]
$e newPath $emj1640 FIXED [RL M8]
set emch1953 [$e addPoint 2542320 3376080]
$e newPath $emj1641 FIXED [RL M8]
set emj1690 [$e addPoint 2935440 3376080]
$e newPath $emj1642 FIXED [RL M8]
set emch1955 [$e addPoint 2543264 3643920]
$e newPath $emj1642 FIXED [RL M8]
set emj1691 [$e addPoint 2934496 3643920]
$e newPath $emj1643 FIXED [RL M9]
set emj1692 [$e addPoint 2823120 3647340]
$e newPath $emj1643 FIXED [RL M9]
set emj1693 [$e addPoint 2823120 3648240]
$e newPath $emj1644 FIXED [RL M8]
set emj1694 [$e addTechVia [V {VIA89}]]
$e newPath $emj1647 FIXED [RL M9]
set emj1695 [$e addPoint 2542320 3644010]
$e newPath $emj1648 FIXED [RL M9]
set emj1696 [$e addPoint 2309040 3647340]
$e newPath $emj1648 FIXED [RL M9]
set emj1697 [$e addPoint 2309040 3648240]
$e newPath $emj1650 FIXED [RL M9]
set emch1963 [$e addPoint 1799280 3730950]
$e newPath $emj1651 FIXED [RL M9]
set emj1698 [$e addPoint 1799280 3915000]
$e newPath $emj1652 FIXED [RL M9]
set emj1699 [$e addTechVia [V {VIA89}]]
$e newPath $emj1652 FIXED [RL M9]
set emj1700 [$e addPoint 257040 4183920]
$e newPath $emj1654 FIXED [RL M9]
set emch1967 [$e addPoint 1285200 3912705]
$e newPath $emj1655 FIXED [RL M9]
set emj1701 [$e addPoint 1285200 3916080]
$e newPath $emj1656 FIXED [RL M9]
set emj1702 [$e addTechVia [V {VIA89}]]
$e newPath $emj1656 FIXED [RL M9]
set emj1703 [$e addPoint 771120 4183920]
$e newPath $emj1657 FIXED [RL M9]
set emj1704 [$e addTechVia [V {VIA89}]]
$e newPath $emj1657 FIXED [RL M9]
set emj1705 [$e addPoint 7959600 2023920]
$e newPath $emj1658 FIXED [RL M9]
set emj1706 [$e addPoint 7445520 1767264]
$e newPath $emj1659 FIXED [RL M9]
set emj1707 [$e addPoint 6659280 1778580]
$e newPath $emj1660 FIXED [RL M8]
set emj1708 [$e addPoint 7532512 1756080]
$e newPath $emj1660 FIXED [RL M8]
set emj1709 [$e addTechVia [V {VIA89}]]
$e newPath $emj1661 FIXED [RL M9]
set emj1710 [$e addPoint 6931440 2296080]
$e newPath $emj1662 FIXED [RL M9]
set emch1978 [$e addPoint 6417360 2162160]
$e newPath $emj1663 FIXED [RL M9]
set emj1711 [$e addTechVia [V {VIA89}]]
$e newPath $emj1663 FIXED [RL M9]
set emj1712 [$e addPoint 6417360 2295000]
$e newPath $emj1664 FIXED [RL M8]
set emj1713 [$e addPoint 8176368 1483920]
$e newPath $emj1664 FIXED [RL M8]
set emj1714 [$e addTechVia [V {VIA89}]]
$e newPath $emj1666 FIXED [RL M9]
set emj1715 [$e addPoint 6611760 1756170]
$e newPath $emj1667 FIXED [RL M8]
set emj1716 [$e addPoint 7959600 2023920]
$e newPath $emj1667 FIXED [RL M8]
set emj1717 [$e addTechVia [V {VIA89}]]
$e newPath $emj1668 FIXED [RL M9]
set emj1718 [$e addTechVia [V {VIA89}]]
$e newPath $emj1668 FIXED [RL M9]
set emch1987 [$e addPoint 7445520 1767264]
$e newPath $emj1668 FIXED [RL M9]
set emj1719 [$e addPoint 7445520 1767330]
$e newPath $emj1669 FIXED [RL M9]
set emj1720 [$e addPoint 7445520 2027340]
$e newPath $emj1669 FIXED [RL M9]
set emj1721 [$e addPoint 7445520 2028240]
$e newPath $emj1670 FIXED [RL M8]
set emj1722 [$e addPoint 6623072 2296080]
$e newPath $emj1670 FIXED [RL M8]
set emj1723 [$e addTechVia [V {VIA89}]]
$e newPath $emj1671 FIXED [RL M9]
set emj1724 [$e addPoint 6404400 2249460]
$e newPath $emj1672 FIXED [RL M9]
set emj1725 [$e addTechVia [V {VIA89}]]
$e newPath $emj1672 FIXED [RL M9]
set emj1726 [$e addPoint 5907600 2567295]
$e newPath $emj1673 FIXED [RL M8]
set emj1727 [$e addTechVia [V {VIA89}]]
$e newPath $emj1674 FIXED [RL M9]
set emch1997 [$e addPoint 4879440 2453344]
$e newPath $emj1674 FIXED [RL M9]
set emj1728 [$e addPoint 4879440 2565000]
$e newPath $emj1675 FIXED [RL M8]
set emj1729 [$e addPoint 5674320 2563920]
$e newPath $emj1676 FIXED [RL M9]
set emj1730 [$e addPoint 5432400 2567340]
$e newPath $emj1678 FIXED [RL M9]
set emch2001 [$e addPoint 5393520 2832705]
$e newPath $emj1679 FIXED [RL M9]
set emj1731 [$e addPoint 5393520 2836080]
$e newPath $emj1680 FIXED [RL M9]
set emj1732 [$e addTechVia [V {VIA89}]]
$e newPath $emj1680 FIXED [RL M9]
set emj1733 [$e addPoint 4365360 2832660]
$e newPath $emj1680 FIXED [RL M9]
set emj1734 [$e addPoint 4365360 2832705]
$e newPath $emj1682 FIXED [RL M9]
set emch2006 [$e addPoint 4879440 2453344]
$e newPath $emj1684 FIXED [RL M9]
set emj1735 [$e addPoint 4533840 2564010]
$e newPath $emj1685 FIXED [RL M8]
set emj1736 [$e addPoint 4365360 2836080]
$e newPath $emj1686 FIXED [RL M9]
set emj1737 [$e addPoint 4106160 2836170]
$e newPath $emj1687 FIXED [RL M8]
set emj1738 [$e addPoint 4365360 3103920]
$e newPath $emj1687 FIXED [RL M8]
set emj1739 [$e addTechVia [V {VIA89}]]
$e newPath $emj1688 FIXED [RL M9]
set emj1740 [$e addPoint 3851280 3376080]
$e newPath $emj1689 FIXED [RL M9]
set emj1741 [$e addTechVia [V {VIA89}]]
$e newPath $emj1689 FIXED [RL M9]
set emj1742 [$e addPoint 3337200 3372660]
$e newPath $emj1689 FIXED [RL M9]
set emj1743 [$e addPoint 3337200 3372705]
$e newPath $emj1690 FIXED [RL M8]
set emj1744 [$e addPoint 3324240 3376080]
$e newPath $emj1690 FIXED [RL M8]
set emj1745 [$e addTechVia [V {VIA89}]]
$e newPath $emj1691 FIXED [RL M8]
set emj1746 [$e addPoint 2935440 3643920]
$e newPath $emj1692 FIXED [RL M9]
set emch2019 [$e addPoint 2823120 3648240]
$e newPath $emj1693 FIXED [RL M9]
set emj1747 [$e addTechVia [V {VIA89}]]
$e newPath $emj1693 FIXED [RL M9]
set emj1748 [$e addPoint 2823120 3915000]
$e newPath $emj1694 FIXED [RL M9]
set emj1749 [$e addPoint 2542320 3376170]
$e newPath $emj1696 FIXED [RL M9]
set emch2023 [$e addPoint 2309040 3648240]
$e newPath $emj1697 FIXED [RL M9]
set emj1750 [$e addTechVia [V {VIA89}]]
$e newPath $emj1697 FIXED [RL M9]
set emj1751 [$e addPoint 2309040 3730320]
$e newPath $emj1698 FIXED [RL M9]
set emj1752 [$e addPoint 1799280 3916080]
$e newPath $emj1699 FIXED [RL M8]
set emj1753 [$e addPoint 83472 3916080]
$e newPath $emj1699 FIXED [RL M8]
set emch2028 [$e addPoint 771120 3916080]
$e newPath $emj1700 FIXED [RL M9]
set emj1754 [$e addTechVia [V {VIA89}]]
$e newPath $emj1700 FIXED [RL M9]
set emj1755 [$e addPoint 257040 4187295]
$e newPath $emj1701 FIXED [RL M9]
set emj1756 [$e addTechVia [V {VIA89}]]
$e newPath $emj1701 FIXED [RL M9]
set emj1757 [$e addPoint 1285200 4183920]
$e newPath $emj1702 FIXED [RL M8]
set emch2033 [$e addPoint 1285200 3916080]
$e newPath $emj1703 FIXED [RL M9]
set emj1758 [$e addTechVia [V {VIA89}]]
$e newPath $emj1703 FIXED [RL M9]
set emj1759 [$e addPoint 771120 4187295]
$e newPath $emj1704 FIXED [RL M8]
set emch2036 [$e addPoint 7532512 1756080]
$e newPath $emj1704 FIXED [RL M8]
set emj1760 [$e addPoint 8171280 1756080]
$e newPath $emj1705 FIXED [RL M9]
set emch2038 [$e addTechVia [V {VIA89}]]
$e newPath $emj1705 FIXED [RL M9]
set emj1761 [$e addPoint 7959600 2025000]
$e newPath $emj1706 FIXED [RL M9]
set emch2040 [$e addPoint 7445520 1767330]
$e newPath $emj1709 FIXED [RL M9]
set emj1762 [$e addPoint 7531920 1756170]
$e newPath $emj1710 FIXED [RL M9]
set emj1763 [$e addTechVia [V {VIA89}]]
$e newPath $emj1710 FIXED [RL M9]
set emj1764 [$e addPoint 6931440 2563920]
$e newPath $emj1712 FIXED [RL M9]
set emch2044 [$e addPoint 6417360 2296080]
$e newPath $emj1714 FIXED [RL M9]
set emj1765 [$e addPoint 8089200 1484010]
$e newPath $emj1716 FIXED [RL M8]
set emj1766 [$e addPoint 7972560 2023920]
$e newPath $emj1717 FIXED [RL M9]
set emj1767 [$e addPoint 7631280 2024010]
$e newPath $emj1720 FIXED [RL M9]
set emch2048 [$e addPoint 7445520 2028240]
$e newPath $emj1721 FIXED [RL M9]
set emj1768 [$e addTechVia [V {VIA89}]]
$e newPath $emj1721 FIXED [RL M9]
set emj1769 [$e addPoint 7445520 2160032]
$e newPath $emj1722 FIXED [RL M8]
set emj1770 [$e addPoint 6624720 2296080]
$e newPath $emj1723 FIXED [RL M9]
set emj1771 [$e addPoint 6417360 2563920]
$e newPath $emj1725 FIXED [RL M8]
set emch2053 [$e addPoint 5674320 2563920]
$e newPath $emj1725 FIXED [RL M8]
set emj1772 [$e addPoint 5942160 2563920]
$e newPath $emj1726 FIXED [RL M9]
set emj1773 [$e addPoint 5907600 2567340]
$e newPath $emj1726 FIXED [RL M9]
set emj1774 [$e addPoint 5907600 2568240]
$e newPath $emj1727 FIXED [RL M9]
set emj1775 [$e addPoint 4793040 2580840]
$e newPath $emj1728 FIXED [RL M9]
set emj1776 [$e addPoint 4879440 2831760]
$e newPath $emj1729 FIXED [RL M8]
set emj1777 [$e addTechVia [V {VIA89}]]
$e newPath $emj1731 FIXED [RL M9]
set emj1778 [$e addTechVia [V {VIA89}]]
$e newPath $emj1731 FIXED [RL M9]
set emj1779 [$e addPoint 5393520 3103920]
$e newPath $emj1733 FIXED [RL M9]
set emch2062 [$e addPoint 4365360 2832705]
$e newPath $emj1734 FIXED [RL M9]
set emj1780 [$e addPoint 4365360 2836080]
$e newPath $emj1736 FIXED [RL M8]
set emj1781 [$e addPoint 4499280 2836080]
$e newPath $emj1736 FIXED [RL M8]
set emch2065 [$e addTechVia [V {VIA89}]]
$e newPath $emj1738 FIXED [RL M8]
set emj1782 [$e addPoint 4879440 3103920]
$e newPath $emj1738 FIXED [RL M8]
set emj1783 [$e addTechVia [V {VIA89}]]
$e newPath $emj1739 FIXED [RL M9]
set emj1784 [$e addPoint 3920400 3107340]
$e newPath $emj1740 FIXED [RL M9]
set emj1785 [$e addTechVia [V {VIA89}]]
$e newPath $emj1740 FIXED [RL M9]
set emj1786 [$e addPoint 3851280 3491552]
$e newPath $emj1742 FIXED [RL M9]
set emch2071 [$e addPoint 3337200 3372705]
$e newPath $emj1743 FIXED [RL M9]
set emj1787 [$e addPoint 3337200 3376080]
$e newPath $emj1744 FIXED [RL M8]
set emj1788 [$e addPoint 3325792 3376080]
$e newPath $emj1744 FIXED [RL M8]
set emj1789 [$e addTechVia [V {VIA89}]]
$e newPath $emj1745 FIXED [RL M9]
set emj1790 [$e addPoint 2935440 3376170]
$e newPath $emj1746 FIXED [RL M8]
set emj1791 [$e addPoint 3289680 3643920]
$e newPath $emj1746 FIXED [RL M8]
set emj1792 [$e addTechVia [V {VIA89}]]
$e newPath $emj1748 FIXED [RL M9]
set emj1793 [$e addPoint 2823120 3916080]
$e newPath $emj1751 FIXED [RL M9]
set emj1794 [$e addTechVia [V {VIA89}]]
$e newPath $emj1751 FIXED [RL M9]
set emj1795 [$e addPoint 2309040 3730912]
$e newPath $emj1751 FIXED [RL M9]
set emj1796 [$e addPoint 2309040 3730950]
$e newPath $emj1752 FIXED [RL M9]
set emj1797 [$e addTechVia [V {VIA89}]]
$e newPath $emj1752 FIXED [RL M9]
set emj1798 [$e addPoint 1799280 4183920]
$e newPath $emj1754 FIXED [RL M8]
set emj1799 [$e addPoint 196560 4183920]
$e newPath $emj1754 FIXED [RL M8]
set emj1800 [$e addPoint 585360 4183920]
$e newPath $emj1755 FIXED [RL M9]
set emj1801 [$e addPoint 257040 4187340]
$e newPath $emj1755 FIXED [RL M9]
set emj1802 [$e addPoint 257040 4188240]
$e newPath $emj1756 FIXED [RL M8]
set emch2088 [$e addPoint 1799280 3916080]
$e newPath $emj1757 FIXED [RL M9]
set emj1803 [$e addTechVia [V {VIA89}]]
$e newPath $emj1757 FIXED [RL M9]
set emj1804 [$e addPoint 1285200 4187295]
$e newPath $emj1758 FIXED [RL M8]
set emj1805 [$e addPoint 586912 4183920]
$e newPath $emj1758 FIXED [RL M8]
set emj1806 [$e addPoint 978144 4183920]
$e newPath $emj1759 FIXED [RL M9]
set emj1807 [$e addPoint 771120 4187340]
$e newPath $emj1759 FIXED [RL M9]
set emj1808 [$e addPoint 771120 4188240]
$e newPath $emj1760 FIXED [RL M8]
set emj1809 [$e addPoint 8174368 1756080]
$e newPath $emj1760 FIXED [RL M8]
set emj1810 [$e addTechVia [V {VIA89}]]
$e newPath $emj1761 FIXED [RL M9]
set emj1811 [$e addPoint 7959600 2295000]
$e newPath $emj1763 FIXED [RL M8]
set emj1812 [$e addPoint 6659280 2296080]
$e newPath $emj1763 FIXED [RL M8]
set emj1813 [$e addPoint 7445520 2296080]
$e newPath $emj1764 FIXED [RL M9]
set emj1814 [$e addTechVia [V {VIA89}]]
$e newPath $emj1764 FIXED [RL M9]
set emj1815 [$e addPoint 6931440 2565000]
$e newPath $emj1766 FIXED [RL M8]
set emj1816 [$e addPoint 8176368 2023920]
$e newPath $emj1766 FIXED [RL M8]
set emj1817 [$e addTechVia [V {VIA89}]]
$e newPath $emj1769 FIXED [RL M9]
set emj1818 [$e addPoint 7445520 2160090]
$e newPath $emj1769 FIXED [RL M9]
set emj1819 [$e addPoint 7445520 2162160]
$e newPath $emj1770 FIXED [RL M8]
set emch2106 [$e addPoint 6659280 2296080]
$e newPath $emj1770 FIXED [RL M8]
set emj1820 [$e addTechVia [V {VIA89}]]
$e newPath $emj1771 FIXED [RL M9]
set emj1821 [$e addTechVia [V {VIA89}]]
$e newPath $emj1771 FIXED [RL M9]
set emj1822 [$e addPoint 6417360 2565000]
$e newPath $emj1772 FIXED [RL M8]
set emj1823 [$e addPoint 5943712 2563920]
$e newPath $emj1772 FIXED [RL M8]
set emj1824 [$e addTechVia [V {VIA89}]]
$e newPath $emj1773 FIXED [RL M9]
set emch2112 [$e addPoint 5907600 2568240]
$e newPath $emj1774 FIXED [RL M9]
set emj1825 [$e addTechVia [V {VIA89}]]
$e newPath $emj1774 FIXED [RL M9]
set emj1826 [$e addPoint 5907600 2831760]
$e newPath $emj1776 FIXED [RL M9]
set emj1827 [$e addTechVia [V {VIA89}]]
$e newPath $emj1776 FIXED [RL M9]
set emj1828 [$e addPoint 4879440 2832660]
$e newPath $emj1776 FIXED [RL M9]
set emj1829 [$e addPoint 4879440 2832705]
$e newPath $emj1777 FIXED [RL M9]
set emj1830 [$e addPoint 5674320 2564010]
$e newPath $emj1778 FIXED [RL M8]
set emj1831 [$e addPoint 5282144 2836080]
$e newPath $emj1778 FIXED [RL M8]
set emj1832 [$e addPoint 5907600 2836080]
$e newPath $emj1779 FIXED [RL M9]
set emj1833 [$e addTechVia [V {VIA89}]]
$e newPath $emj1779 FIXED [RL M9]
set emj1834 [$e addPoint 5393520 3107295]
$e newPath $emj1780 FIXED [RL M9]
set emch2123 [$e addPoint 4365360 3103920]
$e newPath $emj1781 FIXED [RL M8]
set emj1835 [$e addPoint 4499616 2836080]
$e newPath $emj1781 FIXED [RL M8]
set emj1836 [$e addTechVia [V {VIA89}]]
$e newPath $emj1782 FIXED [RL M8]
set emch2126 [$e addPoint 5393520 3103920]
$e newPath $emj1782 FIXED [RL M8]
set emj1837 [$e addTechVia [V {VIA89}]]
$e newPath $emj1783 FIXED [RL M9]
set emj1838 [$e addPoint 4365360 3105000]
$e newPath $emj1783 FIXED [RL M9]
set emj1839 [$e addPoint 4365360 3189420]
$e newPath $emj1785 FIXED [RL M8]
set emj1840 [$e addPoint 3337200 3376080]
$e newPath $emj1785 FIXED [RL M8]
set emj1841 [$e addPoint 3920400 3376080]
$e newPath $emj1786 FIXED [RL M9]
set emj1842 [$e addPoint 3851280 3491730]
$e newPath $emj1786 FIXED [RL M9]
set emj1843 [$e addPoint 3851280 3492720]
$e newPath $emj1787 FIXED [RL M9]
set emch2134 [$e addTechVia [V {VIA89}]]
$e newPath $emj1787 FIXED [RL M9]
set emj1844 [$e addPoint 3337200 3643920]
$e newPath $emj1788 FIXED [RL M8]
set emch2136 [$e addPoint 3337200 3376080]
$e newPath $emj1789 FIXED [RL M9]
set emj1845 [$e addPoint 3324240 3376170]
$e newPath $emj1791 FIXED [RL M8]
set emj1846 [$e addPoint 3291232 3643920]
$e newPath $emj1791 FIXED [RL M8]
set emj1847 [$e addTechVia [V {VIA89}]]
$e newPath $emj1792 FIXED [RL M9]
set emj1848 [$e addPoint 2935440 3644010]
$e newPath $emj1793 FIXED [RL M9]
set emj1849 [$e addTechVia [V {VIA89}]]
$e newPath $emj1793 FIXED [RL M9]
set emj1850 [$e addPoint 2823120 4183920]
$e newPath $emj1795 FIXED [RL M9]
set emch2143 [$e addPoint 2309040 3730950]
$e newPath $emj1796 FIXED [RL M9]
set emj1851 [$e addPoint 2309040 3915000]
$e newPath $emj1797 FIXED [RL M8]
set emj1852 [$e addPoint 1807920 3916080]
$e newPath $emj1798 FIXED [RL M9]
set emj1853 [$e addTechVia [V {VIA89}]]
$e newPath $emj1798 FIXED [RL M9]
set emj1854 [$e addPoint 1799280 4187295]
$e newPath $emj1799 FIXED [RL M8]
set emj1855 [$e addPoint 195616 4183920]
$e newPath $emj1799 FIXED [RL M8]
set emj1856 [$e addTechVia [V {VIA89}]]
$e newPath $emj1800 FIXED [RL M8]
set emch2150 [$e addPoint 586912 4183920]
$e newPath $emj1800 FIXED [RL M8]
set emj1857 [$e addTechVia [V {VIA89}]]
$e newPath $emj1801 FIXED [RL M9]
set emch2152 [$e addPoint 257040 4188240]
$e newPath $emj1802 FIXED [RL M9]
set emj1858 [$e addTechVia [V {VIA89}]]
$e newPath $emj1802 FIXED [RL M9]
set emj1859 [$e addPoint 257040 4300592]
$e newPath $emj1803 FIXED [RL M8]
set emj1860 [$e addPoint 978480 4183920]
$e newPath $emj1803 FIXED [RL M8]
set emj1861 [$e addPoint 1367280 4183920]
$e newPath $emj1804 FIXED [RL M9]
set emj1862 [$e addPoint 1285200 4187340]
$e newPath $emj1804 FIXED [RL M9]
set emj1863 [$e addPoint 1285200 4188240]
$e newPath $emj1806 FIXED [RL M8]
set emch2159 [$e addPoint 978480 4183920]
$e newPath $emj1807 FIXED [RL M9]
set emch2160 [$e addPoint 771120 4188240]
$e newPath $emj1808 FIXED [RL M9]
set emj1864 [$e addTechVia [V {VIA89}]]
$e newPath $emj1808 FIXED [RL M9]
set emj1865 [$e addPoint 771120 4300592]
$e newPath $emj1809 FIXED [RL M8]
set emj1866 [$e addPoint 8175600 1756080]
$e newPath $emj1810 FIXED [RL M9]
set emj1867 [$e addPoint 8171280 1752660]
$e newPath $emj1811 FIXED [RL M9]
set emj1868 [$e addPoint 7959600 2296080]
$e newPath $emj1812 FIXED [RL M8]
set emj1869 [$e addTechVia [V {VIA89}]]
$e newPath $emj1813 FIXED [RL M8]
set emj1870 [$e addPoint 7946640 2296080]
$e newPath $emj1813 FIXED [RL M8]
set emj1871 [$e addTechVia [V {VIA89}]]
$e newPath $emj1814 FIXED [RL M8]
set emj1872 [$e addPoint 6633376 2563920]
$e newPath $emj1814 FIXED [RL M8]
set emj1873 [$e addPoint 6957360 2563920]
$e newPath $emj1815 FIXED [RL M9]
set emj1874 [$e addPoint 6931440 2831760]
$e newPath $emj1817 FIXED [RL M9]
set emj1875 [$e addPoint 7972560 2070540]
$e newPath $emj1818 FIXED [RL M9]
set emch2173 [$e addPoint 7445520 2162160]
$e newPath $emj1819 FIXED [RL M9]
set emj1876 [$e addTechVia [V {VIA89}]]
$e newPath $emj1819 FIXED [RL M9]
set emj1877 [$e addPoint 7445520 2291760]
$e newPath $emj1820 FIXED [RL M9]
set emj1878 [$e addPoint 6624720 2296170]
$e newPath $emj1821 FIXED [RL M8]
set emch2177 [$e addPoint 5943712 2563920]
$e newPath $emj1821 FIXED [RL M8]
set emj1879 [$e addPoint 6434640 2563920]
$e newPath $emj1822 FIXED [RL M9]
set emj1880 [$e addPoint 6417360 2667600]
$e newPath $emj1824 FIXED [RL M9]
set emj1881 [$e addPoint 5942160 2564010]
$e newPath $emj1826 FIXED [RL M9]
set emj1882 [$e addTechVia [V {VIA89}]]
$e newPath $emj1826 FIXED [RL M9]
set emj1883 [$e addPoint 5907600 2832660]
$e newPath $emj1826 FIXED [RL M9]
set emj1884 [$e addPoint 5907600 2832705]
$e newPath $emj1828 FIXED [RL M9]
set emch2184 [$e addPoint 4879440 2832705]
$e newPath $emj1829 FIXED [RL M9]
set emj1885 [$e addPoint 4879440 2836080]
$e newPath $emj1831 FIXED [RL M8]
set emj1886 [$e addPoint 5281200 2836080]
$e newPath $emj1832 FIXED [RL M8]
set emj1887 [$e addPoint 6019920 2836080]
$e newPath $emj1832 FIXED [RL M8]
set emj1888 [$e addTechVia [V {VIA89}]]
$e newPath $emj1833 FIXED [RL M8]
set emj1889 [$e addPoint 5907600 3103920]
$e newPath $emj1834 FIXED [RL M9]
set emj1890 [$e addPoint 5393520 3107340]
$e newPath $emj1834 FIXED [RL M9]
set emj1891 [$e addPoint 5393520 3108240]
$e newPath $emj1835 FIXED [RL M8]
set emj1892 [$e addPoint 4879440 2836080]
$e newPath $emj1836 FIXED [RL M9]
set emj1893 [$e addPoint 4499280 2836170]
$e newPath $emj1837 FIXED [RL M9]
set emj1894 [$e addPoint 4879440 2945610]
$e newPath $emj1837 FIXED [RL M9]
set emj1895 [$e addPoint 4879440 3107295]
$e newPath $emj1838 FIXED [RL M9]
set emch2196 [$e addPoint 4365360 3189420]
$e newPath $emj1839 FIXED [RL M9]
set emj1896 [$e addPoint 4365360 3375000]
$e newPath $emj1841 FIXED [RL M8]
set emj1897 [$e addPoint 3980880 3376080]
$e newPath $emj1841 FIXED [RL M8]
set emj1898 [$e addTechVia [V {VIA89}]]
$e newPath $emj1842 FIXED [RL M9]
set emch2200 [$e addPoint 3851280 3492720]
$e newPath $emj1843 FIXED [RL M9]
set emj1899 [$e addTechVia [V {VIA89}]]
$e newPath $emj1843 FIXED [RL M9]
set emj1900 [$e addPoint 3851280 3643920]
$e newPath $emj1844 FIXED [RL M9]
set emj1901 [$e addTechVia [V {VIA89}]]
$e newPath $emj1844 FIXED [RL M9]
set emj1902 [$e addPoint 3337200 3645000]
$e newPath $emj1846 FIXED [RL M8]
set emj1903 [$e addPoint 3298320 3643920]
$e newPath $emj1847 FIXED [RL M9]
set emj1904 [$e addPoint 3289680 3644010]
$e newPath $emj1849 FIXED [RL M8]
set emj1905 [$e addPoint 2309040 3916080]
$e newPath $emj1849 FIXED [RL M8]
set emj1906 [$e addPoint 2887920 3916080]
$e newPath $emj1850 FIXED [RL M9]
set emj1907 [$e addTechVia [V {VIA89}]]
$e newPath $emj1850 FIXED [RL M9]
set emj1908 [$e addPoint 2823120 4185000]
$e newPath $emj1851 FIXED [RL M9]
set emj1909 [$e addPoint 2309040 3916080]
$e newPath $emj1852 FIXED [RL M8]
set emj1910 [$e addPoint 2261520 3916080]
$e newPath $emj1852 FIXED [RL M8]
set emj1911 [$e addTechVia [V {VIA89}]]
$e newPath $emj1853 FIXED [RL M8]
set emj1912 [$e addPoint 1760736 4183920]
$e newPath $emj1853 FIXED [RL M8]
set emj1913 [$e addPoint 2183760 4183920]
$e newPath $emj1854 FIXED [RL M9]
set emj1914 [$e addPoint 1799280 4187340]
$e newPath $emj1854 FIXED [RL M9]
set emj1915 [$e addPoint 1799280 4188240]
$e newPath $emj1855 FIXED [RL M8]
set emj1916 [$e addPoint 83472 4183920]
$e newPath $emj1856 FIXED [RL M9]
set emj1917 [$e addPoint 196560 4184010]
$e newPath $emj1857 FIXED [RL M9]
set emj1918 [$e addPoint 585360 4184010]
$e newPath $emj1860 FIXED [RL M8]
set emj1919 [$e addTechVia [V {VIA89}]]
$e newPath $emj1861 FIXED [RL M8]
set emj1920 [$e addPoint 1368928 4183920]
$e newPath $emj1861 FIXED [RL M8]
set emj1921 [$e addTechVia [V {VIA89}]]
$e newPath $emj1862 FIXED [RL M9]
set emch2224 [$e addPoint 1285200 4188240]
$e newPath $emj1863 FIXED [RL M9]
set emj1922 [$e addTechVia [V {VIA89}]]
$e newPath $emj1863 FIXED [RL M9]
set emj1923 [$e addPoint 1285200 4300592]
$e newPath $emj1866 FIXED [RL M8]
set emj1924 [$e addPoint 8176368 1756080]
$e newPath $emj1866 FIXED [RL M8]
set emj1925 [$e addTechVia [V {VIA89}]]
$e newPath $emj1868 FIXED [RL M9]
set emj1926 [$e addTechVia [V {VIA89}]]
$e newPath $emj1868 FIXED [RL M9]
set emj1927 [$e addPoint 7959600 2563920]
$e newPath $emj1869 FIXED [RL M9]
set emj1928 [$e addPoint 6659280 2318580]
$e newPath $emj1870 FIXED [RL M8]
set emch2232 [$e addPoint 7959600 2296080]
$e newPath $emj1870 FIXED [RL M8]
set emj1929 [$e addTechVia [V {VIA89}]]
$e newPath $emj1871 FIXED [RL M9]
set emj1930 [$e addPoint 7445520 2292705]
$e newPath $emj1871 FIXED [RL M9]
set emj1931 [$e addPoint 7445520 2550960]
$e newPath $emj1872 FIXED [RL M8]
set emj1932 [$e addPoint 6633360 2563920]
$e newPath $emj1873 FIXED [RL M8]
set emj1933 [$e addPoint 7445520 2563920]
$e newPath $emj1873 FIXED [RL M8]
set emj1934 [$e addTechVia [V {VIA89}]]
$e newPath $emj1874 FIXED [RL M9]
set emj1935 [$e addTechVia [V {VIA89}]]
$e newPath $emj1874 FIXED [RL M9]
set emj1936 [$e addPoint 6931440 2832660]
$e newPath $emj1874 FIXED [RL M9]
set emj1937 [$e addPoint 6931440 2832705]
$e newPath $emj1877 FIXED [RL M9]
set emj1938 [$e addTechVia [V {VIA89}]]
$e newPath $emj1877 FIXED [RL M9]
set emj1939 [$e addPoint 7445520 2292660]
$e newPath $emj1877 FIXED [RL M9]
set emch2244 [$e addPoint 7445520 2292705]
$e newPath $emj1879 FIXED [RL M8]
set emch2245 [$e addPoint 6633360 2563920]
$e newPath $emj1879 FIXED [RL M8]
set emj1940 [$e addTechVia [V {VIA89}]]
$e newPath $emj1880 FIXED [RL M9]
set emj1941 [$e addTechVia [V {VIA89}]]
$e newPath $emj1880 FIXED [RL M9]
set emj1942 [$e addPoint 6417360 2669310]
$e newPath $emj1880 FIXED [RL M9]
set emj1943 [$e addPoint 6417360 2669344]
$e newPath $emj1883 FIXED [RL M9]
set emch2250 [$e addPoint 5907600 2832705]
$e newPath $emj1884 FIXED [RL M9]
set emch2251 [$e addPoint 5907600 2836080]
$e newPath $emj1885 FIXED [RL M9]
set emch2252 [$e addTechVia [V {VIA89}]]
$e newPath $emj1885 FIXED [RL M9]
set emj1944 [$e addPoint 4879440 2944080]
$e newPath $emj1886 FIXED [RL M8]
set emch2254 [$e addPoint 4879440 2836080]
$e newPath $emj1886 FIXED [RL M8]
set emj1945 [$e addTechVia [V {VIA89}]]
$e newPath $emj1887 FIXED [RL M8]
set emj1946 [$e addPoint 6021472 2836080]
$e newPath $emj1887 FIXED [RL M8]
set emj1947 [$e addTechVia [V {VIA89}]]
$e newPath $emj1888 FIXED [RL M9]
set emj1948 [$e addPoint 5907600 2986464]
$e newPath $emj1889 FIXED [RL M8]
set emj1949 [$e addPoint 6296400 3103920]
$e newPath $emj1889 FIXED [RL M8]
set emj1950 [$e addTechVia [V {VIA89}]]
$e newPath $emj1890 FIXED [RL M9]
set emch2261 [$e addPoint 5393520 3108240]
$e newPath $emj1891 FIXED [RL M9]
set emj1951 [$e addTechVia [V {VIA89}]]
$e newPath $emj1891 FIXED [RL M9]
set emj1952 [$e addPoint 5393520 3371760]
$e newPath $emj1894 FIXED [RL M9]
set emch2264 [$e addPoint 4879440 2944080]
$e newPath $emj1894 FIXED [RL M9]
set emj1953 [$e addPoint 4879440 2945440]
$e newPath $emj1895 FIXED [RL M9]
set emj1954 [$e addPoint 4879440 3107340]
$e newPath $emj1895 FIXED [RL M9]
set emj1955 [$e addPoint 4879440 3108240]
$e newPath $emj1896 FIXED [RL M9]
set emj1956 [$e addPoint 4365360 3376080]
$e newPath $emj1897 FIXED [RL M8]
set emj1957 [$e addPoint 3982560 3376080]
$e newPath $emj1897 FIXED [RL M8]
set emj1958 [$e addTechVia [V {VIA89}]]
$e newPath $emj1898 FIXED [RL M9]
set emj1959 [$e addPoint 3920400 3372660]
$e newPath $emj1900 FIXED [RL M9]
set emj1960 [$e addTechVia [V {VIA89}]]
$e newPath $emj1900 FIXED [RL M9]
set emj1961 [$e addPoint 3851280 3645000]
$e newPath $emj1901 FIXED [RL M8]
set emch2274 [$e addPoint 3298320 3643920]
$e newPath $emj1901 FIXED [RL M8]
set emch2275 [$e addPoint 3851280 3643920]
$e newPath $emj1902 FIXED [RL M9]
set emj1962 [$e addPoint 3337200 3911760]
$e newPath $emj1903 FIXED [RL M8]
set emj1963 [$e addTechVia [V {VIA89}]]
$e newPath $emj1905 FIXED [RL M8]
set emch2278 [$e addPoint 2261520 3916080]
$e newPath $emj1905 FIXED [RL M8]
set emch2279 [$e addTechVia [V {VIA89}]]
$e newPath $emj1906 FIXED [RL M8]
set emj1964 [$e addPoint 3337200 3916080]
$e newPath $emj1906 FIXED [RL M8]
set emj1965 [$e addTechVia [V {VIA89}]]
$e newPath $emj1907 FIXED [RL M8]
set emj1966 [$e addPoint 2543264 4183920]
$e newPath $emj1907 FIXED [RL M8]
set emj1967 [$e addPoint 2887920 4183920]
$e newPath $emj1908 FIXED [RL M9]
set emj1968 [$e addPoint 2823120 4300592]
$e newPath $emj1909 FIXED [RL M9]
set emj1969 [$e addPoint 2309040 4183920]
$e newPath $emj1910 FIXED [RL M8]
set emj1970 [$e addTechVia [V {VIA89}]]
$e newPath $emj1911 FIXED [RL M9]
set emj1971 [$e addPoint 1807920 3932460]
$e newPath $emj1912 FIXED [RL M8]
set emj1972 [$e addPoint 1760400 4183920]
$e newPath $emj1913 FIXED [RL M8]
set emj1973 [$e addPoint 2184352 4183920]
$e newPath $emj1913 FIXED [RL M8]
set emj1974 [$e addTechVia [V {VIA89}]]
$e newPath $emj1914 FIXED [RL M9]
set emch2291 [$e addPoint 1799280 4188240]
$e newPath $emj1915 FIXED [RL M9]
set emj1975 [$e addTechVia [V {VIA89}]]
$e newPath $emj1915 FIXED [RL M9]
set emj1976 [$e addPoint 1799280 4300592]
$e newPath $emj1919 FIXED [RL M9]
set emj1977 [$e addPoint 978480 4184010]
$e newPath $emj1920 FIXED [RL M8]
set emch2295 [$e addPoint 1760400 4183920]
$e newPath $emj1921 FIXED [RL M9]
set emj1978 [$e addPoint 1367280 4184010]
$e newPath $emj1925 FIXED [RL M9]
set emj1979 [$e addPoint 8175600 1756170]
$e newPath $emj1926 FIXED [RL M8]
set emj1980 [$e addPoint 8169968 2296080]
$e newPath $emj1927 FIXED [RL M9]
set emj1981 [$e addTechVia [V {VIA89}]]
$e newPath $emj1927 FIXED [RL M9]
set emj1982 [$e addPoint 7959600 2565000]
$e newPath $emj1929 FIXED [RL M9]
set emj1983 [$e addPoint 7946640 2249460]
$e newPath $emj1930 FIXED [RL M9]
set emch2302 [$e addPoint 7445520 2292660]
$e newPath $emj1931 FIXED [RL M9]
set emj1984 [$e addTechVia [V {VIA89}]]
$e newPath $emj1931 FIXED [RL M9]
set emj1985 [$e addPoint 7445520 2552736]
$e newPath $emj1931 FIXED [RL M9]
set emj1986 [$e addPoint 7445520 2553030]
$e newPath $emj1932 FIXED [RL M8]
set emj1987 [$e addTechVia [V {VIA89}]]
$e newPath $emj1933 FIXED [RL M8]
set emj1988 [$e addPoint 7531920 2563920]
$e newPath $emj1933 FIXED [RL M8]
set emj1989 [$e addTechVia [V {VIA89}]]
$e newPath $emj1934 FIXED [RL M9]
set emj1990 [$e addPoint 6957360 2832120]
$e newPath $emj1936 FIXED [RL M9]
set emch2310 [$e addPoint 6931440 2832705]
$e newPath $emj1937 FIXED [RL M9]
set emj1991 [$e addPoint 6931440 2836080]
$e newPath $emj1940 FIXED [RL M9]
set emj1992 [$e addPoint 6434640 2663640]
$e newPath $emj1942 FIXED [RL M9]
set emch2313 [$e addPoint 6417360 2669344]
$e newPath $emj1943 FIXED [RL M9]
set emj1993 [$e addPoint 6417360 2831760]
$e newPath $emj1944 FIXED [RL M9]
set emj1994 [$e addTechVia [V {VIA89}]]
$e newPath $emj1944 FIXED [RL M9]
set emch2316 [$e addPoint 4879440 2945440]
$e newPath $emj1945 FIXED [RL M9]
set emj1995 [$e addPoint 5281200 2836170]
$e newPath $emj1946 FIXED [RL M8]
set emj1996 [$e addPoint 6417360 2836080]
$e newPath $emj1947 FIXED [RL M9]
set emj1997 [$e addPoint 6019920 2836170]
$e newPath $emj1948 FIXED [RL M9]
set emj1998 [$e addPoint 5907600 2986650]
$e newPath $emj1948 FIXED [RL M9]
set emj1999 [$e addPoint 5907600 2987280]
$e newPath $emj1949 FIXED [RL M8]
set emj2000 [$e addPoint 6417360 3103920]
$e newPath $emj1949 FIXED [RL M8]
set emj2001 [$e addTechVia [V {VIA89}]]
$e newPath $emj1950 FIXED [RL M9]
set emch2324 [$e addPoint 5907600 2987280]
$e newPath $emj1950 FIXED [RL M9]
set emj2002 [$e addPoint 5907600 3107295]
$e newPath $emj1952 FIXED [RL M9]
set emj2003 [$e addTechVia [V {VIA89}]]
$e newPath $emj1952 FIXED [RL M9]
set emj2004 [$e addPoint 5393520 3372660]
$e newPath $emj1952 FIXED [RL M9]
set emj2005 [$e addPoint 5393520 3372705]
$e newPath $emj1954 FIXED [RL M9]
set emch2329 [$e addPoint 4879440 3108240]
$e newPath $emj1955 FIXED [RL M9]
set emj2006 [$e addTechVia [V {VIA89}]]
$e newPath $emj1955 FIXED [RL M9]
set emj2007 [$e addPoint 4879440 3337200]
$e newPath $emj1956 FIXED [RL M9]
set emj2008 [$e addTechVia [V {VIA89}]]
$e newPath $emj1956 FIXED [RL M9]
set emj2009 [$e addPoint 4365360 3540240]
$e newPath $emj1957 FIXED [RL M8]
set emch2334 [$e addPoint 4365360 3376080]
$e newPath $emj1958 FIXED [RL M9]
set emj2010 [$e addPoint 3980880 3376170]
$e newPath $emj1960 FIXED [RL M8]
set emj2011 [$e addPoint 3903120 3643920]
$e newPath $emj1961 FIXED [RL M9]
set emj2012 [$e addPoint 3851280 3793568]
$e newPath $emj1962 FIXED [RL M9]
set emj2013 [$e addTechVia [V {VIA89}]]
$e newPath $emj1962 FIXED [RL M9]
set emj2014 [$e addPoint 3337200 3912660]
$e newPath $emj1962 FIXED [RL M9]
set emj2015 [$e addPoint 3337200 3912705]
$e newPath $emj1963 FIXED [RL M9]
set emj2016 [$e addPoint 3298320 3652380]
$e newPath $emj1964 FIXED [RL M8]
set emj2017 [$e addPoint 3851280 3916080]
$e newPath $emj1964 FIXED [RL M8]
set emj2018 [$e addTechVia [V {VIA89}]]
$e newPath $emj1965 FIXED [RL M9]
set emj2019 [$e addPoint 2887920 3912660]
$e newPath $emj1966 FIXED [RL M8]
set emj2020 [$e addPoint 2542320 4183920]
$e newPath $emj1967 FIXED [RL M8]
set emj2021 [$e addPoint 2934496 4183920]
$e newPath $emj1967 FIXED [RL M8]
set emj2022 [$e addTechVia [V {VIA89}]]
$e newPath $emj1969 FIXED [RL M9]
set emj2023 [$e addTechVia [V {VIA89}]]
$e newPath $emj1969 FIXED [RL M9]
set emj2024 [$e addPoint 2309040 4187295]
$e newPath $emj1970 FIXED [RL M9]
set emj2025 [$e addPoint 2261520 3919500]
$e newPath $emj1972 FIXED [RL M8]
set emj2026 [$e addTechVia [V {VIA89}]]
$e newPath $emj1973 FIXED [RL M8]
set emch2352 [$e addPoint 2309040 4183920]
$e newPath $emj1974 FIXED [RL M9]
set emj2027 [$e addPoint 2183760 4184010]
$e newPath $emj1980 FIXED [RL M8]
set emj2028 [$e addPoint 8171280 2296080]
$e newPath $emj1981 FIXED [RL M8]
set emj2029 [$e addPoint 7812720 2563920]
$e newPath $emj1981 FIXED [RL M8]
set emj2030 [$e addPoint 8174368 2563920]
$e newPath $emj1982 FIXED [RL M9]
set emj2031 [$e addPoint 7959600 2835000]
$e newPath $emj1985 FIXED [RL M9]
set emch2358 [$e addPoint 7445520 2553030]
$e newPath $emj1986 FIXED [RL M9]
set emch2359 [$e addPoint 7445520 2563920]
$e newPath $emj1987 FIXED [RL M9]
set emj2032 [$e addPoint 6633360 2564010]
$e newPath $emj1988 FIXED [RL M8]
set emj2033 [$e addPoint 7532512 2563920]
$e newPath $emj1988 FIXED [RL M8]
set emj2034 [$e addTechVia [V {VIA89}]]
$e newPath $emj1989 FIXED [RL M9]
set emj2035 [$e addPoint 7445520 2567295]
$e newPath $emj1991 FIXED [RL M9]
set emj2036 [$e addTechVia [V {VIA89}]]
$e newPath $emj1991 FIXED [RL M9]
set emj2037 [$e addPoint 6931440 3103920]
$e newPath $emj1993 FIXED [RL M9]
set emj2038 [$e addTechVia [V {VIA89}]]
$e newPath $emj1993 FIXED [RL M9]
set emj2039 [$e addPoint 6417360 2832660]
$e newPath $emj1993 FIXED [RL M9]
set emj2040 [$e addPoint 6417360 2832705]
$e newPath $emj1996 FIXED [RL M8]
set emj2041 [$e addPoint 6845040 2836080]
$e newPath $emj1996 FIXED [RL M8]
set emj2042 [$e addTechVia [V {VIA89}]]
$e newPath $emj1998 FIXED [RL M9]
set emch2371 [$e addPoint 5907600 2987280]
$e newPath $emj1999 FIXED [RL M9]
set emj2043 [$e addTechVia [V {VIA89}]]
$e newPath $emj2000 FIXED [RL M8]
set emj2044 [$e addPoint 6931440 3103920]
$e newPath $emj2000 FIXED [RL M8]
set emj2045 [$e addTechVia [V {VIA89}]]
$e newPath $emj2001 FIXED [RL M9]
set emj2046 [$e addPoint 6296400 3163500]
$e newPath $emj2002 FIXED [RL M9]
set emj2047 [$e addPoint 5907600 3107340]
$e newPath $emj2002 FIXED [RL M9]
set emj2048 [$e addPoint 5907600 3108240]
$e newPath $emj2004 FIXED [RL M9]
set emch2378 [$e addPoint 5393520 3372705]
$e newPath $emj2005 FIXED [RL M9]
set emj2049 [$e addPoint 5393520 3376080]
$e newPath $emj2007 FIXED [RL M9]
set emj2050 [$e addTechVia [V {VIA89}]]
$e newPath $emj2007 FIXED [RL M9]
set emj2051 [$e addPoint 4879440 3338208]
$e newPath $emj2007 FIXED [RL M9]
set emj2052 [$e addPoint 4879440 3338370]
$e newPath $emj2008 FIXED [RL M8]
set emj2053 [$e addPoint 4369680 3376080]
$e newPath $emj2009 FIXED [RL M9]
set emj2054 [$e addTechVia [V {VIA89}]]
$e newPath $emj2009 FIXED [RL M9]
set emj2055 [$e addPoint 4365360 3540832]
$e newPath $emj2009 FIXED [RL M9]
set emj2056 [$e addPoint 4365360 3540870]
$e newPath $emj2011 FIXED [RL M8]
set emj2057 [$e addPoint 4106160 3643920]
$e newPath $emj2011 FIXED [RL M8]
set emj2058 [$e addTechVia [V {VIA89}]]
$e newPath $emj2012 FIXED [RL M9]
set emj2059 [$e addPoint 3851280 3793590]
$e newPath $emj2012 FIXED [RL M9]
set emj2060 [$e addPoint 3851280 3795120]
$e newPath $emj2014 FIXED [RL M9]
set emch2391 [$e addPoint 3337200 3912705]
$e newPath $emj2015 FIXED [RL M9]
set emch2392 [$e addPoint 3337200 3916080]
$e newPath $emj2017 FIXED [RL M8]
set emj2061 [$e addPoint 3872880 3916080]
$e newPath $emj2017 FIXED [RL M8]
set emj2062 [$e addTechVia [V {VIA89}]]
$e newPath $emj2018 FIXED [RL M9]
set emj2063 [$e addPoint 3337200 4123440]
$e newPath $emj2020 FIXED [RL M8]
set emch2396 [$e addPoint 2309040 4183920]
$e newPath $emj2020 FIXED [RL M8]
set emj2064 [$e addTechVia [V {VIA89}]]
$e newPath $emj2021 FIXED [RL M8]
set emj2065 [$e addPoint 2935440 4183920]
$e newPath $emj2022 FIXED [RL M9]
set emj2066 [$e addPoint 2887920 4187340]
$e newPath $emj2024 FIXED [RL M9]
set emj2067 [$e addPoint 2309040 4187340]
$e newPath $emj2024 FIXED [RL M9]
set emj2068 [$e addPoint 2309040 4188240]
$e newPath $emj2026 FIXED [RL M9]
set emj2069 [$e addPoint 1760400 4184010]
$e newPath $emj2028 FIXED [RL M8]
set emj2070 [$e addPoint 8176368 2296080]
$e newPath $emj2028 FIXED [RL M8]
set emj2071 [$e addTechVia [V {VIA89}]]
$e newPath $emj2029 FIXED [RL M8]
set emch2405 [$e addPoint 7532512 2563920]
$e newPath $emj2029 FIXED [RL M8]
set emj2072 [$e addTechVia [V {VIA89}]]
$e newPath $emj2030 FIXED [RL M8]
set emj2073 [$e addPoint 8175600 2563920]
$e newPath $emj2031 FIXED [RL M9]
set emj2074 [$e addPoint 7959600 2836080]
$e newPath $emj2034 FIXED [RL M9]
set emj2075 [$e addPoint 7531920 2564010]
$e newPath $emj2035 FIXED [RL M9]
set emj2076 [$e addPoint 7445520 2567340]
$e newPath $emj2035 FIXED [RL M9]
set emj2077 [$e addPoint 7445520 2568240]
$e newPath $emj2036 FIXED [RL M8]
set emj2078 [$e addPoint 6846688 2836080]
$e newPath $emj2036 FIXED [RL M8]
set emj2079 [$e addPoint 7445520 2836080]
$e newPath $emj2037 FIXED [RL M9]
set emch2414 [$e addTechVia [V {VIA89}]]
$e newPath $emj2037 FIXED [RL M9]
set emj2080 [$e addPoint 6931440 3105000]
$e newPath $emj2039 FIXED [RL M9]
set emch2416 [$e addPoint 6417360 2832705]
$e newPath $emj2040 FIXED [RL M9]
set emch2417 [$e addPoint 6417360 2836080]
$e newPath $emj2041 FIXED [RL M8]
set emch2418 [$e addPoint 6846688 2836080]
$e newPath $emj2041 FIXED [RL M8]
set emj2081 [$e addTechVia [V {VIA89}]]
$e newPath $emj2042 FIXED [RL M9]
set emj2082 [$e addPoint 6417360 2944080]
$e newPath $emj2044 FIXED [RL M8]
set emj2083 [$e addPoint 6935760 3103920]
$e newPath $emj2045 FIXED [RL M9]
set emj2084 [$e addPoint 6417360 2945610]
$e newPath $emj2045 FIXED [RL M9]
set emj2085 [$e addPoint 6417360 3105000]
$e newPath $emj2047 FIXED [RL M9]
set emch2424 [$e addPoint 5907600 3108240]
$e newPath $emj2048 FIXED [RL M9]
set emj2086 [$e addTechVia [V {VIA89}]]
$e newPath $emj2048 FIXED [RL M9]
set emj2087 [$e addPoint 5907600 3337200]
$e newPath $emj2049 FIXED [RL M9]
set emj2088 [$e addTechVia [V {VIA89}]]
$e newPath $emj2049 FIXED [RL M9]
set emj2089 [$e addPoint 5393520 3643920]
$e newPath $emj2051 FIXED [RL M9]
set emch2429 [$e addPoint 4879440 3338370]
$e newPath $emj2052 FIXED [RL M9]
set emj2090 [$e addPoint 4879440 3371760]
$e newPath $emj2053 FIXED [RL M8]
set emj2091 [$e addPoint 4499280 3376080]
$e newPath $emj2053 FIXED [RL M8]
set emj2092 [$e addTechVia [V {VIA89}]]
$e newPath $emj2055 FIXED [RL M9]
set emch2433 [$e addPoint 4365360 3540870]
$e newPath $emj2056 FIXED [RL M9]
set emj2093 [$e addPoint 4365360 3643920]
$e newPath $emj2057 FIXED [RL M8]
set emj2094 [$e addPoint 4107808 3643920]
$e newPath $emj2057 FIXED [RL M8]
set emj2095 [$e addTechVia [V {VIA89}]]
$e newPath $emj2058 FIXED [RL M9]
set emj2096 [$e addPoint 3903120 3647340]
$e newPath $emj2059 FIXED [RL M9]
set emch2438 [$e addPoint 3851280 3795120]
$e newPath $emj2060 FIXED [RL M9]
set emj2097 [$e addTechVia [V {VIA89}]]
$e newPath $emj2060 FIXED [RL M9]
set emj2098 [$e addPoint 3851280 3915000]
$e newPath $emj2061 FIXED [RL M8]
set emj2099 [$e addPoint 4205520 3916080]
$e newPath $emj2061 FIXED [RL M8]
set emj2100 [$e addTechVia [V {VIA89}]]
$e newPath $emj2062 FIXED [RL M9]
set emch2443 [$e addPoint 3851280 3915000]
$e newPath $emj2062 FIXED [RL M9]
set emj2101 [$e addPoint 3851280 4183920]
$e newPath $emj2063 FIXED [RL M9]
set emj2102 [$e addTechVia [V {VIA89}]]
$e newPath $emj2063 FIXED [RL M9]
set emj2103 [$e addPoint 3337200 4123936]
$e newPath $emj2063 FIXED [RL M9]
set emj2104 [$e addPoint 3337200 4124070]
$e newPath $emj2064 FIXED [RL M9]
set emj2105 [$e addPoint 2542320 4184010]
$e newPath $emj2065 FIXED [RL M8]
set emj2106 [$e addPoint 3337200 4183920]
$e newPath $emj2065 FIXED [RL M8]
set emj2107 [$e addTechVia [V {VIA89}]]
$e newPath $emj2067 FIXED [RL M9]
set emch2451 [$e addPoint 2309040 4188240]
$e newPath $emj2068 FIXED [RL M9]
set emj2108 [$e addTechVia [V {VIA89}]]
$e newPath $emj2068 FIXED [RL M9]
set emj2109 [$e addPoint 2309040 4300592]
$e newPath $emj2071 FIXED [RL M9]
set emj2110 [$e addPoint 8171280 2296170]
$e newPath $emj2072 FIXED [RL M9]
set emj2111 [$e addPoint 7812720 2667240]
$e newPath $emj2073 FIXED [RL M8]
set emj2112 [$e addPoint 8176368 2563920]
$e newPath $emj2073 FIXED [RL M8]
set emj2113 [$e addTechVia [V {VIA89}]]
$e newPath $emj2074 FIXED [RL M9]
set emj2114 [$e addTechVia [V {VIA89}]]
$e newPath $emj2074 FIXED [RL M9]
set emj2115 [$e addPoint 7959600 2957940]
$e newPath $emj2076 FIXED [RL M9]
set emch2460 [$e addPoint 7445520 2568240]
$e newPath $emj2077 FIXED [RL M9]
set emj2116 [$e addTechVia [V {VIA89}]]
$e newPath $emj2077 FIXED [RL M9]
set emj2117 [$e addPoint 7445520 2831760]
$e newPath $emj2079 FIXED [RL M8]
set emj2118 [$e addPoint 7629728 2836080]
$e newPath $emj2079 FIXED [RL M8]
set emj2119 [$e addTechVia [V {VIA89}]]
$e newPath $emj2080 FIXED [RL M9]
set emj2120 [$e addPoint 6931440 3371760]
$e newPath $emj2081 FIXED [RL M9]
set emj2121 [$e addPoint 6845040 2836170]
$e newPath $emj2082 FIXED [RL M9]
set emj2122 [$e addTechVia [V {VIA89}]]
$e newPath $emj2082 FIXED [RL M9]
set emj2123 [$e addPoint 6417360 2945440]
$e newPath $emj2082 FIXED [RL M9]
set emch2469 [$e addPoint 6417360 2945610]
$e newPath $emj2083 FIXED [RL M8]
set emj2124 [$e addPoint 7238160 3103920]
$e newPath $emj2083 FIXED [RL M8]
set emj2125 [$e addTechVia [V {VIA89}]]
$e newPath $emj2084 FIXED [RL M9]
set emch2472 [$e addPoint 6417360 2945440]
$e newPath $emj2085 FIXED [RL M9]
set emj2126 [$e addPoint 6417360 3371760]
$e newPath $emj2087 FIXED [RL M9]
set emj2127 [$e addTechVia [V {VIA89}]]
$e newPath $emj2087 FIXED [RL M9]
set emj2128 [$e addPoint 5907600 3338208]
$e newPath $emj2087 FIXED [RL M9]
set emj2129 [$e addPoint 5907600 3338370]
$e newPath $emj2088 FIXED [RL M8]
set emj2130 [$e addPoint 5282144 3376080]
$e newPath $emj2088 FIXED [RL M8]
set emj2131 [$e addPoint 5907600 3376080]
$e newPath $emj2089 FIXED [RL M9]
set emj2132 [$e addTechVia [V {VIA89}]]
$e newPath $emj2089 FIXED [RL M9]
set emj2133 [$e addPoint 5393520 3647295]
$e newPath $emj2090 FIXED [RL M9]
set emj2134 [$e addTechVia [V {VIA89}]]
$e newPath $emj2090 FIXED [RL M9]
set emj2135 [$e addPoint 4879440 3372660]
$e newPath $emj2090 FIXED [RL M9]
set emj2136 [$e addPoint 4879440 3372705]
$e newPath $emj2091 FIXED [RL M8]
set emj2137 [$e addPoint 4499616 3376080]
$e newPath $emj2091 FIXED [RL M8]
set emj2138 [$e addTechVia [V {VIA89}]]
$e newPath $emj2092 FIXED [RL M9]
set emj2139 [$e addPoint 4369680 3396780]
$e newPath $emj2093 FIXED [RL M9]
set emj2140 [$e addTechVia [V {VIA89}]]
$e newPath $emj2093 FIXED [RL M9]
set emj2141 [$e addPoint 4365360 3645000]
$e newPath $emj2094 FIXED [RL M8]
set emj2142 [$e addPoint 4348080 3643920]
$e newPath $emj2095 FIXED [RL M9]
set emj2143 [$e addPoint 4106160 3644010]
$e newPath $emj2099 FIXED [RL M8]
set emj2144 [$e addPoint 4365360 3916080]
$e newPath $emj2099 FIXED [RL M8]
set emj2145 [$e addTechVia [V {VIA89}]]
$e newPath $emj2100 FIXED [RL M9]
set emj2146 [$e addPoint 3872880 3912660]
$e newPath $emj2101 FIXED [RL M9]
set emj2147 [$e addTechVia [V {VIA89}]]
$e newPath $emj2101 FIXED [RL M9]
set emj2148 [$e addPoint 3851280 4187295]
$e newPath $emj2103 FIXED [RL M9]
set emch2496 [$e addPoint 3337200 4124070]
$e newPath $emj2104 FIXED [RL M9]
set emj2149 [$e addPoint 3337200 4183920]
$e newPath $emj2106 FIXED [RL M8]
set emj2150 [$e addPoint 3717024 4183920]
$e newPath $emj2106 FIXED [RL M8]
set emch2499 [$e addTechVia [V {VIA89}]]
$e newPath $emj2107 FIXED [RL M9]
set emj2151 [$e addPoint 2935440 4184010]
$e newPath $emj2113 FIXED [RL M9]
set emj2152 [$e addPoint 8175600 2564010]
$e newPath $emj2114 FIXED [RL M8]
set emj2153 [$e addPoint 7950960 2836080]
$e newPath $emj2114 FIXED [RL M8]
set emj2154 [$e addPoint 8087968 2836080]
$e newPath $emj2115 FIXED [RL M9]
set emj2155 [$e addPoint 7959600 3103920]
$e newPath $emj2117 FIXED [RL M9]
set emj2156 [$e addTechVia [V {VIA89}]]
$e newPath $emj2117 FIXED [RL M9]
set emj2157 [$e addPoint 7445520 2832660]
$e newPath $emj2117 FIXED [RL M9]
set emj2158 [$e addPoint 7445520 2832705]
$e newPath $emj2118 FIXED [RL M8]
set emj2159 [$e addPoint 7631280 2836080]
$e newPath $emj2119 FIXED [RL M9]
set emch2509 [$e addPoint 7445520 2832705]
$e newPath $emj2119 FIXED [RL M9]
set emj2160 [$e addPoint 7445520 3103920]
$e newPath $emj2120 FIXED [RL M9]
set emj2161 [$e addTechVia [V {VIA89}]]
$e newPath $emj2120 FIXED [RL M9]
set emj2162 [$e addPoint 6931440 3372660]
$e newPath $emj2120 FIXED [RL M9]
set emj2163 [$e addPoint 6931440 3372705]
$e newPath $emj2124 FIXED [RL M8]
set emj2164 [$e addPoint 7238496 3103920]
$e newPath $emj2124 FIXED [RL M8]
set emj2165 [$e addTechVia [V {VIA89}]]
$e newPath $emj2125 FIXED [RL M9]
set emj2166 [$e addPoint 6935760 3109140]
$e newPath $emj2126 FIXED [RL M9]
set emj2167 [$e addTechVia [V {VIA89}]]
$e newPath $emj2126 FIXED [RL M9]
set emj2168 [$e addPoint 6417360 3372660]
$e newPath $emj2126 FIXED [RL M9]
set emj2169 [$e addPoint 6417360 3372705]
$e newPath $emj2128 FIXED [RL M9]
set emch2520 [$e addPoint 5907600 3338370]
$e newPath $emj2129 FIXED [RL M9]
set emj2170 [$e addPoint 5907600 3371760]
$e newPath $emj2130 FIXED [RL M8]
set emj2171 [$e addPoint 5281200 3376080]
$e newPath $emj2131 FIXED [RL M8]
set emj2172 [$e addPoint 6417360 3376080]
$e newPath $emj2131 FIXED [RL M8]
set emj2173 [$e addTechVia [V {VIA89}]]
$e newPath $emj2132 FIXED [RL M8]
set emj2174 [$e addPoint 4879440 3643920]
$e newPath $emj2132 FIXED [RL M8]
set emj2175 [$e addPoint 5798688 3643920]
$e newPath $emj2133 FIXED [RL M9]
set emj2176 [$e addPoint 5393520 3647340]
$e newPath $emj2133 FIXED [RL M9]
set emj2177 [$e addPoint 5393520 3648240]
$e newPath $emj2135 FIXED [RL M9]
set emch2529 [$e addPoint 4879440 3372705]
$e newPath $emj2136 FIXED [RL M9]
set emj2178 [$e addPoint 4879440 3376080]
$e newPath $emj2137 FIXED [RL M8]
set emj2179 [$e addPoint 4879440 3376080]
$e newPath $emj2138 FIXED [RL M9]
set emj2180 [$e addPoint 4499280 3376170]
$e newPath $emj2140 FIXED [RL M8]
set emch2533 [$e addPoint 4348080 3643920]
$e newPath $emj2140 FIXED [RL M8]
set emj2181 [$e addPoint 4844880 3643920]
$e newPath $emj2141 FIXED [RL M9]
set emj2182 [$e addPoint 4365360 3915000]
$e newPath $emj2142 FIXED [RL M8]
set emj2183 [$e addTechVia [V {VIA89}]]
$e newPath $emj2144 FIXED [RL M8]
set emj2184 [$e addPoint 4879440 3916080]
$e newPath $emj2144 FIXED [RL M8]
set emj2185 [$e addTechVia [V {VIA89}]]
$e newPath $emj2145 FIXED [RL M9]
set emj2186 [$e addPoint 4205520 3912660]
$e newPath $emj2147 FIXED [RL M8]
set emj2187 [$e addPoint 3717360 4183920]
$e newPath $emj2147 FIXED [RL M8]
set emj2188 [$e addPoint 4106160 4183920]
$e newPath $emj2148 FIXED [RL M9]
set emj2189 [$e addPoint 3851280 4187340]
$e newPath $emj2148 FIXED [RL M9]
set emj2190 [$e addPoint 3851280 4188240]
$e newPath $emj2149 FIXED [RL M9]
set emj2191 [$e addPoint 3337200 4187295]
$e newPath $emj2150 FIXED [RL M8]
set emch2545 [$e addPoint 3717360 4183920]
$e newPath $emj2153 FIXED [RL M8]
set emch2546 [$e addPoint 7631280 2836080]
$e newPath $emj2153 FIXED [RL M8]
set emj2192 [$e addTechVia [V {VIA89}]]
$e newPath $emj2154 FIXED [RL M8]
set emj2193 [$e addPoint 8089200 2836080]
$e newPath $emj2155 FIXED [RL M9]
set emj2194 [$e addTechVia [V {VIA89}]]
$e newPath $emj2155 FIXED [RL M9]
set emj2195 [$e addPoint 7959600 3105000]
$e newPath $emj2157 FIXED [RL M9]
set emch2551 [$e addPoint 7445520 2832705]
$e newPath $emj2159 FIXED [RL M8]
set emj2196 [$e addTechVia [V {VIA89}]]
$e newPath $emj2160 FIXED [RL M9]
set emj2197 [$e addTechVia [V {VIA89}]]
$e newPath $emj2160 FIXED [RL M9]
set emj2198 [$e addPoint 7445520 3107295]
$e newPath $emj2162 FIXED [RL M9]
set emch2555 [$e addPoint 6931440 3372705]
$e newPath $emj2163 FIXED [RL M9]
set emj2199 [$e addPoint 6931440 3376080]
$e newPath $emj2164 FIXED [RL M8]
set emch2557 [$e addPoint 7445520 3103920]
$e newPath $emj2165 FIXED [RL M9]
set emj2200 [$e addPoint 7238160 3104010]
$e newPath $emj2168 FIXED [RL M9]
set emch2559 [$e addPoint 6417360 3372705]
$e newPath $emj2169 FIXED [RL M9]
set emj2201 [$e addPoint 6417360 3376080]
$e newPath $emj2170 FIXED [RL M9]
set emj2202 [$e addTechVia [V {VIA89}]]
$e newPath $emj2170 FIXED [RL M9]
set emj2203 [$e addPoint 5907600 3372660]
$e newPath $emj2170 FIXED [RL M9]
set emj2204 [$e addPoint 5907600 3372705]
$e newPath $emj2171 FIXED [RL M8]
set emch2564 [$e addPoint 4879440 3376080]
$e newPath $emj2171 FIXED [RL M8]
set emj2205 [$e addTechVia [V {VIA89}]]
$e newPath $emj2172 FIXED [RL M8]
set emj2206 [$e addPoint 6455904 3376080]
$e newPath $emj2172 FIXED [RL M8]
set emch2567 [$e addTechVia [V {VIA89}]]
$e newPath $emj2173 FIXED [RL M9]
set emch2568 [$e addPoint 5907600 3372705]
$e newPath $emj2173 FIXED [RL M9]
set emj2207 [$e addPoint 5907600 3491552]
$e newPath $emj2174 FIXED [RL M8]
set emch2570 [$e addPoint 4844880 3643920]
$e newPath $emj2174 FIXED [RL M8]
set emj2208 [$e addTechVia [V {VIA89}]]
$e newPath $emj2175 FIXED [RL M8]
set emj2209 [$e addPoint 5799600 3643920]
$e newPath $emj2176 FIXED [RL M9]
set emch2573 [$e addPoint 5393520 3648240]
$e newPath $emj2177 FIXED [RL M9]
set emj2210 [$e addTechVia [V {VIA89}]]
$e newPath $emj2177 FIXED [RL M9]
set emj2211 [$e addPoint 5393520 3730320]
$e newPath $emj2178 FIXED [RL M9]
set emch2576 [$e addTechVia [V {VIA89}]]
$e newPath $emj2178 FIXED [RL M9]
set emch2577 [$e addPoint 4879440 3643920]
$e newPath $emj2181 FIXED [RL M8]
set emj2212 [$e addTechVia [V {VIA89}]]
$e newPath $emj2182 FIXED [RL M9]
set emch2579 [$e addPoint 4365360 3916080]
$e newPath $emj2183 FIXED [RL M9]
set emj2213 [$e addPoint 4348080 3545460]
$e newPath $emj2184 FIXED [RL M8]
set emj2214 [$e addPoint 5393520 3916080]
$e newPath $emj2184 FIXED [RL M8]
set emj2215 [$e addTechVia [V {VIA89}]]
$e newPath $emj2185 FIXED [RL M9]
set emj2216 [$e addPoint 4365360 4183920]
$e newPath $emj2187 FIXED [RL M8]
set emj2217 [$e addTechVia [V {VIA89}]]
$e newPath $emj2188 FIXED [RL M8]
set emj2218 [$e addPoint 4107808 4183920]
$e newPath $emj2188 FIXED [RL M8]
set emj2219 [$e addTechVia [V {VIA89}]]
$e newPath $emj2189 FIXED [RL M9]
set emch2587 [$e addPoint 3851280 4188240]
$e newPath $emj2190 FIXED [RL M9]
set emj2220 [$e addTechVia [V {VIA89}]]
$e newPath $emj2190 FIXED [RL M9]
set emj2221 [$e addPoint 3851280 4300592]
$e newPath $emj2191 FIXED [RL M9]
set emj2222 [$e addPoint 3337200 4187340]
$e newPath $emj2191 FIXED [RL M9]
set emj2223 [$e addPoint 3337200 4188240]
$e newPath $emj2192 FIXED [RL M9]
set emj2224 [$e addPoint 7950960 2779020]
$e newPath $emj2193 FIXED [RL M8]
set emj2225 [$e addPoint 8176368 2836080]
$e newPath $emj2193 FIXED [RL M8]
set emj2226 [$e addTechVia [V {VIA89}]]
$e newPath $emj2194 FIXED [RL M8]
set emch2595 [$e addPoint 7445520 3103920]
$e newPath $emj2194 FIXED [RL M8]
set emj2227 [$e addPoint 8176368 3103920]
$e newPath $emj2195 FIXED [RL M9]
set emj2228 [$e addPoint 7959600 3375000]
$e newPath $emj2196 FIXED [RL M9]
set emj2229 [$e addPoint 7631280 2836170]
$e newPath $emj2198 FIXED [RL M9]
set emj2230 [$e addPoint 7445520 3107340]
$e newPath $emj2198 FIXED [RL M9]
set emj2231 [$e addPoint 7445520 3108240]
$e newPath $emj2199 FIXED [RL M9]
set emj2232 [$e addTechVia [V {VIA89}]]
$e newPath $emj2199 FIXED [RL M9]
set emj2233 [$e addPoint 6931440 3643920]
$e newPath $emj2201 FIXED [RL M9]
set emj2234 [$e addPoint 6417360 3540240]
$e newPath $emj2203 FIXED [RL M9]
set emch2604 [$e addPoint 5907600 3372705]
$e newPath $emj2205 FIXED [RL M9]
set emj2235 [$e addPoint 5281200 3376170]
$e newPath $emj2206 FIXED [RL M8]
set emj2236 [$e addPoint 6456240 3376080]
$e newPath $emj2207 FIXED [RL M9]
set emj2237 [$e addPoint 5907600 3491730]
$e newPath $emj2207 FIXED [RL M9]
set emj2238 [$e addPoint 5907600 3492720]
$e newPath $emj2208 FIXED [RL M9]
set emj2239 [$e addPoint 4879440 3645000]
$e newPath $emj2209 FIXED [RL M8]
set emj2240 [$e addPoint 5812560 3643920]
$e newPath $emj2209 FIXED [RL M8]
set emj2241 [$e addTechVia [V {VIA89}]]
$e newPath $emj2211 FIXED [RL M9]
set emj2242 [$e addTechVia [V {VIA89}]]
$e newPath $emj2211 FIXED [RL M9]
set emj2243 [$e addPoint 5393520 3730912]
$e newPath $emj2211 FIXED [RL M9]
set emj2244 [$e addPoint 5393520 3730950]
$e newPath $emj2212 FIXED [RL M9]
set emj2245 [$e addPoint 4844880 3655980]
$e newPath $emj2214 FIXED [RL M8]
set emj2246 [$e addPoint 5907600 3916080]
$e newPath $emj2214 FIXED [RL M8]
set emj2247 [$e addTechVia [V {VIA89}]]
$e newPath $emj2215 FIXED [RL M9]
set emj2248 [$e addPoint 4879440 3912705]
$e newPath $emj2215 FIXED [RL M9]
set emj2249 [$e addPoint 4879440 4123440]
$e newPath $emj2216 FIXED [RL M9]
set emj2250 [$e addTechVia [V {VIA89}]]
$e newPath $emj2216 FIXED [RL M9]
set emj2251 [$e addPoint 4365360 4185000]
$e newPath $emj2217 FIXED [RL M9]
set emj2252 [$e addPoint 3717360 4184010]
$e newPath $emj2218 FIXED [RL M8]
set emch2623 [$e addPoint 4365360 4183920]
$e newPath $emj2219 FIXED [RL M9]
set emj2253 [$e addPoint 4106160 4184010]
$e newPath $emj2222 FIXED [RL M9]
set emch2625 [$e addPoint 3337200 4188240]
$e newPath $emj2223 FIXED [RL M9]
set emj2254 [$e addTechVia [V {VIA89}]]
$e newPath $emj2223 FIXED [RL M9]
set emj2255 [$e addPoint 3337200 4300592]
$e newPath $emj2226 FIXED [RL M9]
set emj2256 [$e addPoint 8089200 2836170]
$e newPath $emj2228 FIXED [RL M9]
set emj2257 [$e addPoint 7959600 3376080]
$e newPath $emj2230 FIXED [RL M9]
set emch2630 [$e addPoint 7445520 3108240]
$e newPath $emj2231 FIXED [RL M9]
set emj2258 [$e addTechVia [V {VIA89}]]
$e newPath $emj2231 FIXED [RL M9]
set emj2259 [$e addPoint 7445520 3371760]
$e newPath $emj2232 FIXED [RL M8]
set emj2260 [$e addPoint 6846688 3376080]
$e newPath $emj2232 FIXED [RL M8]
set emj2261 [$e addPoint 7238160 3376080]
$e newPath $emj2233 FIXED [RL M9]
set emj2262 [$e addTechVia [V {VIA89}]]
$e newPath $emj2233 FIXED [RL M9]
set emj2263 [$e addPoint 6931440 3647295]
$e newPath $emj2234 FIXED [RL M9]
set emj2264 [$e addTechVia [V {VIA89}]]
$e newPath $emj2234 FIXED [RL M9]
set emj2265 [$e addPoint 6417360 3540832]
$e newPath $emj2234 FIXED [RL M9]
set emj2266 [$e addPoint 6417360 3540870]
$e newPath $emj2236 FIXED [RL M8]
set emj2267 [$e addPoint 6845040 3376080]
$e newPath $emj2236 FIXED [RL M8]
set emj2268 [$e addTechVia [V {VIA89}]]
$e newPath $emj2237 FIXED [RL M9]
set emch2642 [$e addPoint 5907600 3492720]
$e newPath $emj2238 FIXED [RL M9]
set emj2269 [$e addTechVia [V {VIA89}]]
$e newPath $emj2238 FIXED [RL M9]
set emj2270 [$e addPoint 5907600 3643920]
$e newPath $emj2239 FIXED [RL M9]
set emj2271 [$e addPoint 4879440 3730320]
$e newPath $emj2240 FIXED [RL M8]
set emj2272 [$e addPoint 5907600 3643920]
$e newPath $emj2240 FIXED [RL M8]
set emj2273 [$e addTechVia [V {VIA89}]]
$e newPath $emj2241 FIXED [RL M9]
set emj2274 [$e addPoint 5799600 3644010]
$e newPath $emj2243 FIXED [RL M9]
set emch2649 [$e addPoint 5393520 3730950]
$e newPath $emj2244 FIXED [RL M9]
set emj2275 [$e addPoint 5393520 3911760]
$e newPath $emj2246 FIXED [RL M8]
set emj2276 [$e addPoint 6140880 3916080]
$e newPath $emj2246 FIXED [RL M8]
set emj2277 [$e addTechVia [V {VIA89}]]
$e newPath $emj2247 FIXED [RL M9]
set emj2278 [$e addPoint 5393520 3912705]
$e newPath $emj2247 FIXED [RL M9]
set emj2279 [$e addPoint 5393520 4183920]
$e newPath $emj2248 FIXED [RL M9]
set emj2280 [$e addPoint 4879440 3911760]
$e newPath $emj2248 FIXED [RL M9]
set emj2281 [$e addPoint 4879440 3912660]
$e newPath $emj2249 FIXED [RL M9]
set emj2282 [$e addTechVia [V {VIA89}]]
$e newPath $emj2249 FIXED [RL M9]
set emj2283 [$e addPoint 4879440 4123936]
$e newPath $emj2249 FIXED [RL M9]
set emj2284 [$e addPoint 4879440 4124070]
$e newPath $emj2250 FIXED [RL M8]
set emj2285 [$e addPoint 4374000 4183920]
$e newPath $emj2251 FIXED [RL M9]
set emj2286 [$e addPoint 4365360 4298592]
$e newPath $emj2257 FIXED [RL M9]
set emj2287 [$e addTechVia [V {VIA89}]]
$e newPath $emj2257 FIXED [RL M9]
set emj2288 [$e addPoint 7959600 3491552]
$e newPath $emj2259 FIXED [RL M9]
set emj2289 [$e addTechVia [V {VIA89}]]
$e newPath $emj2259 FIXED [RL M9]
set emj2290 [$e addPoint 7445520 3372660]
$e newPath $emj2259 FIXED [RL M9]
set emj2291 [$e addPoint 7445520 3372705]
$e newPath $emj2260 FIXED [RL M8]
set emch2667 [$e addPoint 6845040 3376080]
$e newPath $emj2261 FIXED [RL M8]
set emj2292 [$e addPoint 7238496 3376080]
$e newPath $emj2261 FIXED [RL M8]
set emj2293 [$e addTechVia [V {VIA89}]]
$e newPath $emj2262 FIXED [RL M8]
set emj2294 [$e addPoint 6417360 3643920]
$e newPath $emj2262 FIXED [RL M8]
set emj2295 [$e addPoint 7151760 3643920]
$e newPath $emj2263 FIXED [RL M9]
set emj2296 [$e addPoint 6931440 3647340]
$e newPath $emj2263 FIXED [RL M9]
set emj2297 [$e addPoint 6931440 3648240]
$e newPath $emj2265 FIXED [RL M9]
set emch2674 [$e addPoint 6417360 3540870]
$e newPath $emj2266 FIXED [RL M9]
set emj2298 [$e addPoint 6417360 3643920]
$e newPath $emj2267 FIXED [RL M8]
set emj2299 [$e addTechVia [V {VIA89}]]
$e newPath $emj2268 FIXED [RL M9]
set emj2300 [$e addPoint 6456240 3376170]
$e newPath $emj2270 FIXED [RL M9]
set emch2678 [$e addTechVia [V {VIA89}]]
$e newPath $emj2270 FIXED [RL M9]
set emj2301 [$e addPoint 5907600 3645000]
$e newPath $emj2271 FIXED [RL M9]
set emj2302 [$e addTechVia [V {VIA89}]]
$e newPath $emj2271 FIXED [RL M9]
set emj2303 [$e addPoint 4879440 3730912]
$e newPath $emj2271 FIXED [RL M9]
set emj2304 [$e addPoint 4879440 3730950]
$e newPath $emj2272 FIXED [RL M8]
set emj2305 [$e addPoint 6127328 3643920]
$e newPath $emj2273 FIXED [RL M9]
set emj2306 [$e addPoint 5812560 3653460]
$e newPath $emj2275 FIXED [RL M9]
set emj2307 [$e addTechVia [V {VIA89}]]
$e newPath $emj2275 FIXED [RL M9]
set emj2308 [$e addPoint 5393520 3912660]
$e newPath $emj2275 FIXED [RL M9]
set emch2687 [$e addPoint 5393520 3912705]
$e newPath $emj2276 FIXED [RL M8]
set emj2309 [$e addPoint 6417360 3916080]
$e newPath $emj2276 FIXED [RL M8]
set emj2310 [$e addTechVia [V {VIA89}]]
$e newPath $emj2277 FIXED [RL M9]
set emj2311 [$e addPoint 5907600 3912705]
$e newPath $emj2277 FIXED [RL M9]
set emj2312 [$e addPoint 5907600 4183920]
$e newPath $emj2278 FIXED [RL M9]
set emch2692 [$e addPoint 5393520 3912660]
$e newPath $emj2279 FIXED [RL M9]
set emj2313 [$e addTechVia [V {VIA89}]]
$e newPath $emj2279 FIXED [RL M9]
set emj2314 [$e addPoint 5393520 4187295]
$e newPath $emj2280 FIXED [RL M9]
set emj2315 [$e addTechVia [V {VIA89}]]
$e newPath $emj2280 FIXED [RL M9]
set emch2696 [$e addPoint 4879440 3730950]
$e newPath $emj2280 FIXED [RL M9]
set emch2697 [$e addPoint 4879440 3912660]
$e newPath $emj2283 FIXED [RL M9]
set emch2698 [$e addPoint 4879440 4124070]
$e newPath $emj2284 FIXED [RL M9]
set emj2316 [$e addPoint 4879440 4183920]
$e newPath $emj2285 FIXED [RL M8]
set emj2317 [$e addPoint 4879440 4183920]
$e newPath $emj2285 FIXED [RL M8]
set emj2318 [$e addTechVia [V {VIA89}]]
$e newPath $emj2286 FIXED [RL M9]
set emj2319 [$e addPoint 4365360 4298850]
$e newPath $emj2286 FIXED [RL M9]
set emj2320 [$e addPoint 4365360 4300560]
$e newPath $emj2287 FIXED [RL M8]
set emj2321 [$e addPoint 7631280 3376080]
$e newPath $emj2287 FIXED [RL M8]
set emj2322 [$e addPoint 7968240 3376080]
$e newPath $emj2288 FIXED [RL M9]
set emj2323 [$e addPoint 7959600 3491730]
$e newPath $emj2288 FIXED [RL M9]
set emj2324 [$e addPoint 7959600 3492720]
$e newPath $emj2290 FIXED [RL M9]
set emch2708 [$e addPoint 7445520 3372705]
$e newPath $emj2291 FIXED [RL M9]
set emj2325 [$e addPoint 7445520 3376080]
$e newPath $emj2292 FIXED [RL M8]
set emj2326 [$e addPoint 7445520 3376080]
$e newPath $emj2293 FIXED [RL M9]
set emj2327 [$e addPoint 7238160 3376170]
$e newPath $emj2294 FIXED [RL M8]
set emj2328 [$e addPoint 6400080 3643920]
$e newPath $emj2294 FIXED [RL M8]
set emch2713 [$e addTechVia [V {VIA89}]]
$e newPath $emj2295 FIXED [RL M8]
set emj2329 [$e addPoint 7152096 3643920]
$e newPath $emj2295 FIXED [RL M8]
set emj2330 [$e addTechVia [V {VIA89}]]
$e newPath $emj2296 FIXED [RL M9]
set emch2716 [$e addPoint 6931440 3648240]
$e newPath $emj2297 FIXED [RL M9]
set emj2331 [$e addTechVia [V {VIA89}]]
$e newPath $emj2297 FIXED [RL M9]
set emj2332 [$e addPoint 6931440 3730320]
$e newPath $emj2298 FIXED [RL M9]
set emj2333 [$e addPoint 6417360 3645000]
$e newPath $emj2299 FIXED [RL M9]
set emj2334 [$e addPoint 6845040 3376170]
$e newPath $emj2301 FIXED [RL M9]
set emj2335 [$e addPoint 5907600 3911760]
$e newPath $emj2303 FIXED [RL M9]
set emch2722 [$e addPoint 4879440 3730950]
$e newPath $emj2305 FIXED [RL M8]
set emj2336 [$e addPoint 6127920 3643920]
$e newPath $emj2309 FIXED [RL M8]
set emj2337 [$e addPoint 6931440 3916080]
$e newPath $emj2309 FIXED [RL M8]
set emj2338 [$e addTechVia [V {VIA89}]]
$e newPath $emj2310 FIXED [RL M9]
set emj2339 [$e addPoint 6140880 3938580]
$e newPath $emj2311 FIXED [RL M9]
set emch2727 [$e addPoint 5907600 3911760]
$e newPath $emj2311 FIXED [RL M9]
set emj2340 [$e addPoint 5907600 3912660]
$e newPath $emj2312 FIXED [RL M9]
set emj2341 [$e addTechVia [V {VIA89}]]
$e newPath $emj2312 FIXED [RL M9]
set emj2342 [$e addPoint 5907600 4187295]
$e newPath $emj2313 FIXED [RL M8]
set emj2343 [$e addPoint 5282144 4183920]
$e newPath $emj2313 FIXED [RL M8]
set emj2344 [$e addPoint 5673376 4183920]
$e newPath $emj2314 FIXED [RL M9]
set emj2345 [$e addPoint 5393520 4187340]
$e newPath $emj2314 FIXED [RL M9]
set emj2346 [$e addPoint 5393520 4188240]
$e newPath $emj2316 FIXED [RL M9]
set emch2735 [$e addTechVia [V {VIA89}]]
$e newPath $emj2316 FIXED [RL M9]
set emj2347 [$e addPoint 4879440 4187295]
$e newPath $emj2317 FIXED [RL M8]
set emj2348 [$e addPoint 5281200 4183920]
$e newPath $emj2318 FIXED [RL M9]
set emj2349 [$e addPoint 4374000 4295340]
$e newPath $emj2319 FIXED [RL M9]
set emch2739 [$e addPoint 4365360 4300560]
$e newPath $emj2320 FIXED [RL M9]
set emj2350 [$e addTechVia [V {VIA89}]]
$e newPath $emj2320 FIXED [RL M9]
set emj2351 [$e addPoint 4365360 4300592]
$e newPath $emj2321 FIXED [RL M8]
set emj2352 [$e addPoint 7629728 3376080]
$e newPath $emj2321 FIXED [RL M8]
set emj2353 [$e addTechVia [V {VIA89}]]
$e newPath $emj2322 FIXED [RL M8]
set emj2354 [$e addPoint 8176368 3376080]
$e newPath $emj2322 FIXED [RL M8]
set emj2355 [$e addTechVia [V {VIA89}]]
$e newPath $emj2323 FIXED [RL M9]
set emch2746 [$e addPoint 7959600 3492720]
$e newPath $emj2324 FIXED [RL M9]
set emj2356 [$e addTechVia [V {VIA89}]]
$e newPath $emj2324 FIXED [RL M9]
set emj2357 [$e addPoint 7959600 3643920]
$e newPath $emj2325 FIXED [RL M9]
set emch2749 [$e addTechVia [V {VIA89}]]
$e newPath $emj2325 FIXED [RL M9]
set emj2358 [$e addPoint 7445520 3643920]
$e newPath $emj2326 FIXED [RL M8]
set emch2751 [$e addPoint 7629728 3376080]
$e newPath $emj2328 FIXED [RL M8]
set emch2752 [$e addPoint 6127920 3643920]
$e newPath $emj2328 FIXED [RL M8]
set emj2359 [$e addTechVia [V {VIA89}]]
$e newPath $emj2329 FIXED [RL M8]
set emj2360 [$e addPoint 7428240 3643920]
$e newPath $emj2330 FIXED [RL M9]
set emj2361 [$e addPoint 7151760 3644010]
$e newPath $emj2332 FIXED [RL M9]
set emj2362 [$e addTechVia [V {VIA89}]]
$e newPath $emj2332 FIXED [RL M9]
set emj2363 [$e addPoint 6931440 3730912]
$e newPath $emj2332 FIXED [RL M9]
set emj2364 [$e addPoint 6931440 3730950]
$e newPath $emj2333 FIXED [RL M9]
set emj2365 [$e addPoint 6417360 3915000]
$e newPath $emj2335 FIXED [RL M9]
set emj2366 [$e addTechVia [V {VIA89}]]
$e newPath $emj2335 FIXED [RL M9]
set emch2761 [$e addPoint 5907600 3912660]
$e newPath $emj2336 FIXED [RL M8]
set emj2367 [$e addTechVia [V {VIA89}]]
$e newPath $emj2337 FIXED [RL M8]
set emj2368 [$e addPoint 7445520 3916080]
$e newPath $emj2337 FIXED [RL M8]
set emj2369 [$e addTechVia [V {VIA89}]]
$e newPath $emj2338 FIXED [RL M9]
set emch2765 [$e addPoint 6417360 3915000]
$e newPath $emj2338 FIXED [RL M9]
set emj2370 [$e addPoint 6417360 4183920]
$e newPath $emj2341 FIXED [RL M8]
set emj2371 [$e addPoint 5674320 4183920]
$e newPath $emj2341 FIXED [RL M8]
set emj2372 [$e addPoint 6063120 4183920]
$e newPath $emj2342 FIXED [RL M9]
set emj2373 [$e addPoint 5907600 4187340]
$e newPath $emj2342 FIXED [RL M9]
set emj2374 [$e addPoint 5907600 4188240]
$e newPath $emj2343 FIXED [RL M8]
set emch2771 [$e addPoint 5281200 4183920]
$e newPath $emj2344 FIXED [RL M8]
set emch2772 [$e addPoint 5674320 4183920]
$e newPath $emj2345 FIXED [RL M9]
set emch2773 [$e addPoint 5393520 4188240]
$e newPath $emj2346 FIXED [RL M9]
set emj2375 [$e addTechVia [V {VIA89}]]
$e newPath $emj2346 FIXED [RL M9]
set emj2376 [$e addPoint 5393520 4300592]
$e newPath $emj2347 FIXED [RL M9]
set emj2377 [$e addPoint 4879440 4187340]
$e newPath $emj2347 FIXED [RL M9]
set emj2378 [$e addPoint 4879440 4188240]
$e newPath $emj2348 FIXED [RL M8]
set emj2379 [$e addTechVia [V {VIA89}]]
$e newPath $emj2353 FIXED [RL M9]
set emj2380 [$e addPoint 7631280 3376170]
$e newPath $emj2355 FIXED [RL M9]
set emj2381 [$e addPoint 7968240 3487500]
$e newPath $emj2357 FIXED [RL M9]
set emj2382 [$e addTechVia [V {VIA89}]]
$e newPath $emj2357 FIXED [RL M9]
set emj2383 [$e addPoint 7959600 3645000]
$e newPath $emj2358 FIXED [RL M9]
set emj2384 [$e addTechVia [V {VIA89}]]
$e newPath $emj2358 FIXED [RL M9]
set emj2385 [$e addPoint 7445520 3645000]
$e newPath $emj2359 FIXED [RL M9]
set emj2386 [$e addPoint 6400080 3545460]
$e newPath $emj2360 FIXED [RL M8]
set emch2786 [$e addPoint 7445520 3643920]
$e newPath $emj2360 FIXED [RL M8]
set emj2387 [$e addTechVia [V {VIA89}]]
$e newPath $emj2363 FIXED [RL M9]
set emch2788 [$e addPoint 6931440 3730950]
$e newPath $emj2364 FIXED [RL M9]
set emj2388 [$e addPoint 6931440 3911760]
$e newPath $emj2367 FIXED [RL M9]
set emj2389 [$e addPoint 6127920 3644010]
$e newPath $emj2368 FIXED [RL M8]
set emj2390 [$e addPoint 7458480 3916080]
$e newPath $emj2368 FIXED [RL M8]
set emj2391 [$e addTechVia [V {VIA89}]]
$e newPath $emj2369 FIXED [RL M9]
set emj2392 [$e addPoint 6931440 3912705]
$e newPath $emj2369 FIXED [RL M9]
set emj2393 [$e addPoint 6931440 4123440]
$e newPath $emj2370 FIXED [RL M9]
set emj2394 [$e addTechVia [V {VIA89}]]
$e newPath $emj2370 FIXED [RL M9]
set emj2395 [$e addPoint 6417360 4185000]
$e newPath $emj2371 FIXED [RL M8]
set emj2396 [$e addTechVia [V {VIA89}]]
$e newPath $emj2372 FIXED [RL M8]
set emj2397 [$e addPoint 6064672 4183920]
$e newPath $emj2372 FIXED [RL M8]
set emj2398 [$e addTechVia [V {VIA89}]]
$e newPath $emj2373 FIXED [RL M9]
set emch2800 [$e addPoint 5907600 4188240]
$e newPath $emj2374 FIXED [RL M9]
set emj2399 [$e addTechVia [V {VIA89}]]
$e newPath $emj2374 FIXED [RL M9]
set emj2400 [$e addPoint 5907600 4300592]
$e newPath $emj2377 FIXED [RL M9]
set emch2803 [$e addPoint 4879440 4188240]
$e newPath $emj2378 FIXED [RL M9]
set emj2401 [$e addTechVia [V {VIA89}]]
$e newPath $emj2378 FIXED [RL M9]
set emj2402 [$e addPoint 4879440 4300592]
$e newPath $emj2379 FIXED [RL M9]
set emj2403 [$e addPoint 5281200 4184010]
$e newPath $emj2382 FIXED [RL M8]
set emj2404 [$e addPoint 7631280 3643920]
$e newPath $emj2382 FIXED [RL M8]
set emj2405 [$e addPoint 7976880 3643920]
$e newPath $emj2383 FIXED [RL M9]
set emj2406 [$e addPoint 7959600 3738960]
$e newPath $emj2384 FIXED [RL M8]
set emj2407 [$e addPoint 7629728 3643920]
$e newPath $emj2385 FIXED [RL M9]
set emj2408 [$e addPoint 7445520 3915000]
$e newPath $emj2387 FIXED [RL M9]
set emj2409 [$e addPoint 7428240 3545460]
$e newPath $emj2388 FIXED [RL M9]
set emj2410 [$e addTechVia [V {VIA89}]]
$e newPath $emj2388 FIXED [RL M9]
set emj2411 [$e addPoint 6931440 3912660]
$e newPath $emj2388 FIXED [RL M9]
set emch2815 [$e addPoint 6931440 3912705]
$e newPath $emj2390 FIXED [RL M8]
set emj2412 [$e addPoint 7959600 3916080]
$e newPath $emj2390 FIXED [RL M8]
set emj2413 [$e addTechVia [V {VIA89}]]
$e newPath $emj2391 FIXED [RL M9]
set emch2818 [$e addPoint 7445520 3915000]
$e newPath $emj2391 FIXED [RL M9]
set emj2414 [$e addPoint 7445520 4183920]
$e newPath $emj2392 FIXED [RL M9]
set emch2820 [$e addPoint 6931440 3912660]
$e newPath $emj2393 FIXED [RL M9]
set emj2415 [$e addTechVia [V {VIA89}]]
$e newPath $emj2393 FIXED [RL M9]
set emj2416 [$e addPoint 6931440 4123936]
$e newPath $emj2393 FIXED [RL M9]
set emj2417 [$e addPoint 6931440 4124070]
$e newPath $emj2394 FIXED [RL M8]
set emch2824 [$e addPoint 6064672 4183920]
$e newPath $emj2394 FIXED [RL M8]
set emj2418 [$e addPoint 6421680 4183920]
$e newPath $emj2395 FIXED [RL M9]
set emj2419 [$e addPoint 6417360 4207904]
$e newPath $emj2396 FIXED [RL M9]
set emj2420 [$e addPoint 5674320 4184010]
$e newPath $emj2398 FIXED [RL M9]
set emj2421 [$e addPoint 6063120 4184010]
$e newPath $emj2404 FIXED [RL M8]
set emch2829 [$e addPoint 7629728 3643920]
$e newPath $emj2404 FIXED [RL M8]
set emj2422 [$e addTechVia [V {VIA89}]]
$e newPath $emj2405 FIXED [RL M8]
set emj2423 [$e addPoint 8176368 3643920]
$e newPath $emj2405 FIXED [RL M8]
set emj2424 [$e addTechVia [V {VIA89}]]
$e newPath $emj2406 FIXED [RL M9]
set emj2425 [$e addTechVia [V {VIA89}]]
$e newPath $emj2406 FIXED [RL M9]
set emj2426 [$e addPoint 7959600 3739552]
$e newPath $emj2406 FIXED [RL M9]
set emj2427 [$e addPoint 7959600 3739590]
$e newPath $emj2412 FIXED [RL M8]
set emj2428 [$e addPoint 7963920 3916080]
$e newPath $emj2412 FIXED [RL M8]
set emj2429 [$e addTechVia [V {VIA89}]]
$e newPath $emj2413 FIXED [RL M9]
set emj2430 [$e addPoint 7458480 4062600]
$e newPath $emj2414 FIXED [RL M9]
set emj2431 [$e addTechVia [V {VIA89}]]
$e newPath $emj2414 FIXED [RL M9]
set emj2432 [$e addPoint 7445520 4187295]
$e newPath $emj2416 FIXED [RL M9]
set emch2841 [$e addPoint 6931440 4124070]
$e newPath $emj2417 FIXED [RL M9]
set emj2433 [$e addPoint 6931440 4183920]
$e newPath $emj2418 FIXED [RL M8]
set emj2434 [$e addPoint 6931440 4183920]
$e newPath $emj2418 FIXED [RL M8]
set emj2435 [$e addTechVia [V {VIA89}]]
$e newPath $emj2419 FIXED [RL M9]
set emj2436 [$e addPoint 6417360 4208130]
$e newPath $emj2419 FIXED [RL M9]
set emj2437 [$e addPoint 6417360 4209840]
$e newPath $emj2422 FIXED [RL M9]
set emj2438 [$e addPoint 7631280 3644010]
$e newPath $emj2424 FIXED [RL M9]
set emj2439 [$e addPoint 7976880 3733740]
$e newPath $emj2426 FIXED [RL M9]
set emch2849 [$e addPoint 7959600 3739590]
$e newPath $emj2427 FIXED [RL M9]
set emj2440 [$e addPoint 7959600 3915000]
$e newPath $emj2428 FIXED [RL M8]
set emj2441 [$e addPoint 8176368 3916080]
$e newPath $emj2428 FIXED [RL M8]
set emj2442 [$e addTechVia [V {VIA89}]]
$e newPath $emj2429 FIXED [RL M9]
set emch2853 [$e addPoint 7959600 3915000]
$e newPath $emj2429 FIXED [RL M9]
set emj2443 [$e addPoint 7959600 4183920]
$e newPath $emj2431 FIXED [RL M8]
set emj2444 [$e addPoint 7238496 4183920]
$e newPath $emj2431 FIXED [RL M8]
set emj2445 [$e addPoint 7629728 4183920]
$e newPath $emj2432 FIXED [RL M9]
set emj2446 [$e addPoint 7445520 4187340]
$e newPath $emj2432 FIXED [RL M9]
set emj2447 [$e addPoint 7445520 4188240]
$e newPath $emj2433 FIXED [RL M9]
set emch2859 [$e addTechVia [V {VIA89}]]
$e newPath $emj2433 FIXED [RL M9]
set emj2448 [$e addPoint 6931440 4187295]
$e newPath $emj2434 FIXED [RL M8]
set emj2449 [$e addPoint 7238160 4183920]
$e newPath $emj2435 FIXED [RL M9]
set emj2450 [$e addPoint 6421680 4202100]
$e newPath $emj2436 FIXED [RL M9]
set emch2863 [$e addPoint 6417360 4209840]
$e newPath $emj2437 FIXED [RL M9]
set emj2451 [$e addTechVia [V {VIA89}]]
$e newPath $emj2437 FIXED [RL M9]
set emj2452 [$e addPoint 6417360 4300592]
$e newPath $emj2442 FIXED [RL M9]
set emj2453 [$e addPoint 7963920 3941100]
$e newPath $emj2443 FIXED [RL M9]
set emj2454 [$e addTechVia [V {VIA89}]]
$e newPath $emj2443 FIXED [RL M9]
set emj2455 [$e addPoint 7959600 4187295]
$e newPath $emj2444 FIXED [RL M8]
set emch2869 [$e addPoint 7238160 4183920]
$e newPath $emj2445 FIXED [RL M8]
set emj2456 [$e addPoint 7631280 4183920]
$e newPath $emj2446 FIXED [RL M9]
set emch2871 [$e addPoint 7445520 4188240]
$e newPath $emj2447 FIXED [RL M9]
set emj2457 [$e addTechVia [V {VIA89}]]
$e newPath $emj2447 FIXED [RL M9]
set emj2458 [$e addPoint 7445520 4300592]
$e newPath $emj2448 FIXED [RL M9]
set emj2459 [$e addPoint 6931440 4187340]
$e newPath $emj2448 FIXED [RL M9]
set emj2460 [$e addPoint 6931440 4188240]
$e newPath $emj2449 FIXED [RL M8]
set emj2461 [$e addTechVia [V {VIA89}]]
$e newPath $emj2454 FIXED [RL M8]
set emch2877 [$e addPoint 7631280 4183920]
$e newPath $emj2454 FIXED [RL M8]
set emj2462 [$e addPoint 8020080 4183920]
$e newPath $emj2455 FIXED [RL M9]
set emj2463 [$e addPoint 7959600 4187340]
$e newPath $emj2455 FIXED [RL M9]
set emj2464 [$e addPoint 7959600 4188240]
$e newPath $emj2456 FIXED [RL M8]
set emj2465 [$e addTechVia [V {VIA89}]]
$e newPath $emj2459 FIXED [RL M9]
set emch2882 [$e addPoint 6931440 4188240]
$e newPath $emj2460 FIXED [RL M9]
set emj2466 [$e addTechVia [V {VIA89}]]
$e newPath $emj2460 FIXED [RL M9]
set emj2467 [$e addPoint 6931440 4300592]
$e newPath $emj2461 FIXED [RL M9]
set emj2468 [$e addPoint 7238160 4184010]
$e newPath $emj2462 FIXED [RL M8]
set emj2469 [$e addPoint 8021024 4183920]
$e newPath $emj2462 FIXED [RL M8]
set emj2470 [$e addTechVia [V {VIA89}]]
$e newPath $emj2463 FIXED [RL M9]
set emch2888 [$e addPoint 7959600 4188240]
$e newPath $emj2464 FIXED [RL M9]
set emj2471 [$e addTechVia [V {VIA89}]]
$e newPath $emj2464 FIXED [RL M9]
set emj2472 [$e addPoint 7959600 4300592]
$e newPath $emj2465 FIXED [RL M9]
set emj2473 [$e addPoint 7631280 4184010]
$e newPath $emj2469 FIXED [RL M8]
set emj2474 [$e addPoint 8176368 4183920]
$e newPath $emj2470 FIXED [RL M9]
set emj2475 [$e addPoint 8020080 4184010]
$e newPath $emj14 FIXED [RL M9]
set jd1 [$e addTechVia [V {VIA89}]]
$e newPath $jd1 FIXED [RL M8]
$e addPoint 317720 132660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 317720 132740
set jd2 [$e addTechVia [V VIA67]]
$e newPath $jd2 FIXED
$e addPoint 317800 132740
set jd3 [$e addTechVia [V VIA56]]
$e newPath $jd3 FIXED
$e addPoint 317800 132836
set jd4 [$e addTechVia [V VIA45]]
$e newPath $jd4 FIXED
$e addPoint 317704 132836
set jd5 [$e addTechVia [V VIA34]]
$e newPath $jd5 FIXED
$e addPoint 317704 132660
set jd6 [$e addTechVia [V VIA23]]
$e newPath $jd6 FIXED
$e addPoint 317817 132660
set jd7 [$e addTechVia [V VIA12]]
$e newPath $jd7 FIXED
$e addITerm [IT M0_0 Y]
$e newPath $emj35 FIXED [RL M9]
set jd8 [$e addTechVia [V {VIA89}]]
$e newPath $jd8 FIXED [RL M8]
$e addPoint 317720 407340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 317720 407420
set jd9 [$e addTechVia [V VIA67]]
$e newPath $jd9 FIXED
$e addPoint 317800 407420
set jd10 [$e addTechVia [V VIA56]]
$e newPath $jd10 FIXED
$e addPoint 317800 407516
set jd11 [$e addTechVia [V VIA45]]
$e newPath $jd11 FIXED
$e addPoint 317704 407516
set jd12 [$e addTechVia [V VIA34]]
$e newPath $jd12 FIXED
$e addPoint 317704 407340
set jd13 [$e addTechVia [V VIA23]]
$e newPath $jd13 FIXED
$e addPoint 317817 407340
set jd14 [$e addTechVia [V VIA12]]
$e newPath $jd14 FIXED
$e addITerm [IT M0_1 Y]
$e newPath $emj78 FIXED [RL M9]
set jd15 [$e addTechVia [V {VIA89}]]
$e newPath $jd15 FIXED [RL M8]
$e addPoint 317720 672660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 317720 672740
set jd16 [$e addTechVia [V VIA67]]
$e newPath $jd16 FIXED
$e addPoint 317800 672740
set jd17 [$e addTechVia [V VIA56]]
$e newPath $jd17 FIXED
$e addPoint 317800 672836
set jd18 [$e addTechVia [V VIA45]]
$e newPath $jd18 FIXED
$e addPoint 317704 672836
set jd19 [$e addTechVia [V VIA34]]
$e newPath $jd19 FIXED
$e addPoint 317704 672660
set jd20 [$e addTechVia [V VIA23]]
$e newPath $jd20 FIXED
$e addPoint 317817 672660
set jd21 [$e addTechVia [V VIA12]]
$e newPath $jd21 FIXED
$e addITerm [IT M0_2 Y]
$e newPath $emj97 FIXED [RL M9]
set jd22 [$e addTechVia [V {VIA89}]]
$e newPath $jd22 FIXED [RL M8]
$e addPoint 317720 947340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 317720 947420
set jd23 [$e addTechVia [V VIA67]]
$e newPath $jd23 FIXED
$e addPoint 317800 947420
set jd24 [$e addTechVia [V VIA56]]
$e newPath $jd24 FIXED
$e addPoint 317800 947516
set jd25 [$e addTechVia [V VIA45]]
$e newPath $jd25 FIXED
$e addPoint 317704 947516
set jd26 [$e addTechVia [V VIA34]]
$e newPath $jd26 FIXED
$e addPoint 317704 947340
set jd27 [$e addTechVia [V VIA23]]
$e newPath $jd27 FIXED
$e addPoint 317817 947340
set jd28 [$e addTechVia [V VIA12]]
$e newPath $jd28 FIXED
$e addITerm [IT M0_3 Y]
$e newPath $emj147 FIXED [RL M9]
set jd29 [$e addTechVia [V {VIA89}]]
$e newPath $jd29 FIXED [RL M8]
$e addPoint 317720 1212660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 317720 1212740
set jd30 [$e addTechVia [V VIA67]]
$e newPath $jd30 FIXED
$e addPoint 317800 1212740
set jd31 [$e addTechVia [V VIA56]]
$e newPath $jd31 FIXED
$e addPoint 317800 1212836
set jd32 [$e addTechVia [V VIA45]]
$e newPath $jd32 FIXED
$e addPoint 317704 1212836
set jd33 [$e addTechVia [V VIA34]]
$e newPath $jd33 FIXED
$e addPoint 317704 1212660
set jd34 [$e addTechVia [V VIA23]]
$e newPath $jd34 FIXED
$e addPoint 317817 1212660
set jd35 [$e addTechVia [V VIA12]]
$e newPath $jd35 FIXED
$e addITerm [IT M0_4 Y]
$e newPath $emj168 FIXED [RL M9]
set jd36 [$e addTechVia [V {VIA89}]]
$e newPath $jd36 FIXED [RL M8]
$e addPoint 257240 1487340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 257240 1487420
set jd37 [$e addTechVia [V VIA67]]
$e newPath $jd37 FIXED
$e addPoint 257320 1487420
set jd38 [$e addTechVia [V VIA56]]
$e newPath $jd38 FIXED
$e addPoint 257320 1487516
set jd39 [$e addTechVia [V VIA45]]
$e newPath $jd39 FIXED
$e addPoint 257773 1487516
set jd40 [$e addTechVia [V VIA34]]
$e newPath $jd40 FIXED
$e addPoint 257773 1487340
set jd41 [$e addTechVia [V VIA23]]
$e newPath $jd41 FIXED
$e addPoint 257823 1487340
set jd42 [$e addTechVia [V VIA12]]
$e newPath $jd42 FIXED
$e addITerm [IT M0_5 Y]
$e newPath $emj344 FIXED [RL M9]
set jd43 [$e addTechVia [V {VIA89}]]
$e newPath $jd43 FIXED [RL M8]
$e addPoint 261160 1785420
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 261160 1785500
set jd44 [$e addTechVia [V VIA67]]
$e newPath $jd44 FIXED
$e addPoint 261080 1785500
set jd45 [$e addTechVia [V VIA56]]
$e newPath $jd45 FIXED
$e addPoint 261080 1785596
set jd46 [$e addTechVia [V VIA45]]
$e newPath $jd46 FIXED
$e addPoint 260465 1785596
set jd47 [$e addTechVia [V VIA34]]
$e newPath $jd47 FIXED
$e addPoint 260465 1785420
set jd48 [$e addTechVia [V VIA23]]
$e newPath $jd48 FIXED
$e addPoint 260415 1785420
set jd49 [$e addTechVia [V VIA12]]
$e newPath $jd49 FIXED
$e addITerm [IT M0_6 Y]
$e newPath $emj468 FIXED [RL M9]
set jd50 [$e addTechVia [V {VIA89}]]
$e newPath $jd50 FIXED [RL M8]
$e addPoint 239560 2029140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 239560 2029220
set jd51 [$e addTechVia [V VIA67]]
$e newPath $jd51 FIXED
$e addPoint 239480 2029220
set jd52 [$e addTechVia [V VIA56]]
$e newPath $jd52 FIXED
$e addPoint 239480 2029316
set jd53 [$e addTechVia [V VIA45]]
$e newPath $jd53 FIXED
$e addPoint 238541 2029316
set jd54 [$e addTechVia [V VIA34]]
$e newPath $jd54 FIXED
$e addPoint 238541 2029140
set jd55 [$e addTechVia [V VIA23]]
$e newPath $jd55 FIXED
$e addPoint 238491 2029140
set jd56 [$e addTechVia [V VIA12]]
$e newPath $jd56 FIXED
$e addITerm [IT M0_7 Y]
$e newPath $emj618 FIXED [RL M9]
set jd57 [$e addTechVia [V {VIA89}]]
$e newPath $jd57 FIXED [RL M8]
$e addPoint 239560 2300220
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 239560 2300300
set jd58 [$e addTechVia [V VIA67]]
$e newPath $jd58 FIXED
$e addPoint 239480 2300300
set jd59 [$e addTechVia [V VIA56]]
$e newPath $jd59 FIXED
$e addPoint 239480 2300396
set jd60 [$e addTechVia [V VIA45]]
$e newPath $jd60 FIXED
$e addPoint 238541 2300396
set jd61 [$e addTechVia [V VIA34]]
$e newPath $jd61 FIXED
$e addPoint 238541 2300220
set jd62 [$e addTechVia [V VIA23]]
$e newPath $jd62 FIXED
$e addPoint 238491 2300220
set jd63 [$e addTechVia [V VIA12]]
$e newPath $jd63 FIXED
$e addITerm [IT M0_8 Y]
$e newPath $emj568 FIXED [RL M9]
set jd64 [$e addTechVia [V {VIA89}]]
$e newPath $jd64 FIXED [RL M8]
$e addPoint 257240 2567340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 257240 2567420
set jd65 [$e addTechVia [V VIA67]]
$e newPath $jd65 FIXED
$e addPoint 257320 2567420
set jd66 [$e addTechVia [V VIA56]]
$e newPath $jd66 FIXED
$e addPoint 257320 2567516
set jd67 [$e addTechVia [V VIA45]]
$e newPath $jd67 FIXED
$e addPoint 257773 2567516
set jd68 [$e addTechVia [V VIA34]]
$e newPath $jd68 FIXED
$e addPoint 257773 2567340
set jd69 [$e addTechVia [V VIA23]]
$e newPath $jd69 FIXED
$e addPoint 257823 2567340
set jd70 [$e addTechVia [V VIA12]]
$e newPath $jd70 FIXED
$e addITerm [IT M0_9 Y]
$e newPath $emj964 FIXED [RL M9]
set jd71 [$e addTechVia [V {VIA89}]]
$e newPath $jd71 FIXED [RL M8]
$e addPoint 300040 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 300040 2832740
set jd72 [$e addTechVia [V VIA67]]
$e newPath $jd72 FIXED
$e addPoint 299960 2832740
set jd73 [$e addTechVia [V VIA56]]
$e newPath $jd73 FIXED
$e addPoint 299960 2832836
set jd74 [$e addTechVia [V VIA45]]
$e newPath $jd74 FIXED
$e addPoint 300056 2832836
set jd75 [$e addTechVia [V VIA34]]
$e newPath $jd75 FIXED
$e addPoint 300056 2832660
set jd76 [$e addTechVia [V VIA23]]
$e newPath $jd76 FIXED
$e addPoint 299835 2832660
set jd77 [$e addTechVia [V VIA12]]
$e newPath $jd77 FIXED
$e addITerm [IT M0_10 Y]
$e newPath $emj895 FIXED [RL M9]
set jd78 [$e addTechVia [V {VIA89}]]
$e newPath $jd78 FIXED [RL M8]
$e addPoint 257240 3107340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 257240 3107420
set jd79 [$e addTechVia [V VIA67]]
$e newPath $jd79 FIXED
$e addPoint 257320 3107420
set jd80 [$e addTechVia [V VIA56]]
$e newPath $jd80 FIXED
$e addPoint 257320 3107516
set jd81 [$e addTechVia [V VIA45]]
$e newPath $jd81 FIXED
$e addPoint 257773 3107516
set jd82 [$e addTechVia [V VIA34]]
$e newPath $jd82 FIXED
$e addPoint 257773 3107340
set jd83 [$e addTechVia [V VIA23]]
$e newPath $jd83 FIXED
$e addPoint 257823 3107340
set jd84 [$e addTechVia [V VIA12]]
$e newPath $jd84 FIXED
$e addITerm [IT M0_11 Y]
$e newPath $emj1049 FIXED [RL M9]
set jd85 [$e addTechVia [V {VIA89}]]
$e newPath $jd85 FIXED [RL M8]
$e addPoint 257240 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 257240 3372740
set jd86 [$e addTechVia [V VIA67]]
$e newPath $jd86 FIXED
$e addPoint 257320 3372740
set jd87 [$e addTechVia [V VIA56]]
$e newPath $jd87 FIXED
$e addPoint 257320 3372836
set jd88 [$e addTechVia [V VIA45]]
$e newPath $jd88 FIXED
$e addPoint 257773 3372836
set jd89 [$e addTechVia [V VIA34]]
$e newPath $jd89 FIXED
$e addPoint 257773 3372660
set jd90 [$e addTechVia [V VIA23]]
$e newPath $jd90 FIXED
$e addPoint 257823 3372660
set jd91 [$e addTechVia [V VIA12]]
$e newPath $jd91 FIXED
$e addITerm [IT M0_12 Y]
$e newPath $emj1316 FIXED [RL M9]
set jd92 [$e addTechVia [V {VIA89}]]
$e newPath $jd92 FIXED [RL M8]
$e addPoint 257240 3647340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 257240 3647420
set jd93 [$e addTechVia [V VIA67]]
$e newPath $jd93 FIXED
$e addPoint 257320 3647420
set jd94 [$e addTechVia [V VIA56]]
$e newPath $jd94 FIXED
$e addPoint 257320 3647516
set jd95 [$e addTechVia [V VIA45]]
$e newPath $jd95 FIXED
$e addPoint 257773 3647516
set jd96 [$e addTechVia [V VIA34]]
$e newPath $jd96 FIXED
$e addPoint 257773 3647340
set jd97 [$e addTechVia [V VIA23]]
$e newPath $jd97 FIXED
$e addPoint 257823 3647340
set jd98 [$e addTechVia [V VIA12]]
$e newPath $jd98 FIXED
$e addITerm [IT M0_13 Y]
$e newPath $emj1591 FIXED [RL M9]
set jd99 [$e addTechVia [V {VIA89}]]
$e newPath $jd99 FIXED [RL M8]
$e addPoint 257240 3912660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 257240 3912740
set jd100 [$e addTechVia [V VIA67]]
$e newPath $jd100 FIXED
$e addPoint 257320 3912740
set jd101 [$e addTechVia [V VIA56]]
$e newPath $jd101 FIXED
$e addPoint 257320 3912836
set jd102 [$e addTechVia [V VIA45]]
$e newPath $jd102 FIXED
$e addPoint 257773 3912836
set jd103 [$e addTechVia [V VIA34]]
$e newPath $jd103 FIXED
$e addPoint 257773 3912660
set jd104 [$e addTechVia [V VIA23]]
$e newPath $jd104 FIXED
$e addPoint 257823 3912660
set jd105 [$e addTechVia [V VIA12]]
$e newPath $jd105 FIXED
$e addITerm [IT M0_14 Y]
$e newPath $emj1801 FIXED [RL M9]
set jd106 [$e addTechVia [V {VIA89}]]
$e newPath $jd106 FIXED [RL M8]
$e addPoint 257240 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 257240 4187420
set jd107 [$e addTechVia [V VIA67]]
$e newPath $jd107 FIXED
$e addPoint 257320 4187420
set jd108 [$e addTechVia [V VIA56]]
$e newPath $jd108 FIXED
$e addPoint 257320 4187516
set jd109 [$e addTechVia [V VIA45]]
$e newPath $jd109 FIXED
$e addPoint 257773 4187516
set jd110 [$e addTechVia [V VIA34]]
$e newPath $jd110 FIXED
$e addPoint 257773 4187340
set jd111 [$e addTechVia [V VIA23]]
$e newPath $jd111 FIXED
$e addPoint 257823 4187340
set jd112 [$e addTechVia [V VIA12]]
$e newPath $jd112 FIXED
$e addITerm [IT M0_15 Y]
$e newPath $emj20 FIXED [RL M9]
set jd113 [$e addTechVia [V {VIA89}]]
$e newPath $jd113 FIXED [RL M8]
$e addPoint 762680 28980
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 762680 29060
set jd114 [$e addTechVia [V VIA67]]
$e newPath $jd114 FIXED
$e addPoint 762760 29060
set jd115 [$e addTechVia [V VIA56]]
$e newPath $jd115 FIXED
$e addPoint 762760 29156
set jd116 [$e addTechVia [V VIA45]]
$e newPath $jd116 FIXED
$e addPoint 762856 29156
set jd117 [$e addTechVia [V VIA34]]
$e newPath $jd117 FIXED
$e addPoint 762856 28980
set jd118 [$e addTechVia [V VIA23]]
$e newPath $jd118 FIXED
$e addPoint 762669 28980
set jd119 [$e addTechVia [V VIA12]]
$e newPath $jd119 FIXED
$e addITerm [IT M1_0 Y]
$e newPath $emj58 FIXED [RL M9]
set jd120 [$e addTechVia [V {VIA89}]]
$e newPath $jd120 FIXED [RL M8]
$e addPoint 965320 407340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 965320 407420
set jd121 [$e addTechVia [V VIA67]]
$e newPath $jd121 FIXED
$e addPoint 965240 407420
set jd122 [$e addTechVia [V VIA56]]
$e newPath $jd122 FIXED
$e addPoint 965240 407516
set jd123 [$e addTechVia [V VIA45]]
$e newPath $jd123 FIXED
$e addPoint 963977 407516
set jd124 [$e addTechVia [V VIA34]]
$e newPath $jd124 FIXED
$e addPoint 963977 407340
set jd125 [$e addTechVia [V VIA23]]
$e newPath $jd125 FIXED
$e addPoint 963927 407340
set jd126 [$e addTechVia [V VIA12]]
$e newPath $jd126 FIXED
$e addITerm [IT M1_1 Y]
$e newPath $emj119 FIXED [RL M9]
set jd127 [$e addTechVia [V {VIA89}]]
$e newPath $jd127 FIXED [RL M8]
$e addPoint 965320 672660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 965320 672740
set jd128 [$e addTechVia [V VIA67]]
$e newPath $jd128 FIXED
$e addPoint 965240 672740
set jd129 [$e addTechVia [V VIA56]]
$e newPath $jd129 FIXED
$e addPoint 965240 672836
set jd130 [$e addTechVia [V VIA45]]
$e newPath $jd130 FIXED
$e addPoint 963977 672836
set jd131 [$e addTechVia [V VIA34]]
$e newPath $jd131 FIXED
$e addPoint 963977 672660
set jd132 [$e addTechVia [V VIA23]]
$e newPath $jd132 FIXED
$e addPoint 963927 672660
set jd133 [$e addTechVia [V VIA12]]
$e newPath $jd133 FIXED
$e addITerm [IT M1_2 Y]
$e newPath $emj88 FIXED [RL M9]
set jd134 [$e addTechVia [V {VIA89}]]
$e newPath $jd134 FIXED [RL M8]
$e addPoint 771320 1094220
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 771320 1094300
set jd135 [$e addTechVia [V VIA67]]
$e newPath $jd135 FIXED
$e addPoint 771400 1094300
set jd136 [$e addTechVia [V VIA56]]
$e newPath $jd136 FIXED
$e addPoint 771400 1094396
set jd137 [$e addTechVia [V VIA45]]
$e newPath $jd137 FIXED
$e addPoint 771853 1094396
set jd138 [$e addTechVia [V VIA34]]
$e newPath $jd138 FIXED
$e addPoint 771853 1094220
set jd139 [$e addTechVia [V VIA23]]
$e newPath $jd139 FIXED
$e addPoint 771903 1094220
set jd140 [$e addTechVia [V VIA12]]
$e newPath $jd140 FIXED
$e addITerm [IT M1_3 Y]
$e newPath $emj165 FIXED [RL M9]
set jd141 [$e addTechVia [V {VIA89}]]
$e newPath $jd141 FIXED [RL M8]
$e addPoint 762680 1126260
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 762680 1126340
set jd142 [$e addTechVia [V VIA67]]
$e newPath $jd142 FIXED
$e addPoint 762760 1126340
set jd143 [$e addTechVia [V VIA56]]
$e newPath $jd143 FIXED
$e addPoint 762760 1126436
set jd144 [$e addTechVia [V VIA45]]
$e newPath $jd144 FIXED
$e addPoint 764185 1126436
set jd145 [$e addTechVia [V VIA34]]
$e newPath $jd145 FIXED
$e addPoint 764185 1126260
set jd146 [$e addTechVia [V VIA23]]
$e newPath $jd146 FIXED
$e addPoint 764235 1126260
set jd147 [$e addTechVia [V VIA12]]
$e newPath $jd147 FIXED
$e addITerm [IT M1_4 Y]
$e newPath $emj205 FIXED [RL M9]
set jd148 [$e addTechVia [V {VIA89}]]
$e newPath $jd148 FIXED [RL M8]
$e addPoint 771320 1782900
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 771320 1782980
set jd149 [$e addTechVia [V VIA67]]
$e newPath $jd149 FIXED
$e addPoint 771400 1782980
set jd150 [$e addTechVia [V VIA56]]
$e newPath $jd150 FIXED
$e addPoint 771400 1783076
set jd151 [$e addTechVia [V VIA45]]
$e newPath $jd151 FIXED
$e addPoint 771853 1783076
set jd152 [$e addTechVia [V VIA34]]
$e newPath $jd152 FIXED
$e addPoint 771853 1782900
set jd153 [$e addTechVia [V VIA23]]
$e newPath $jd153 FIXED
$e addPoint 771903 1782900
set jd154 [$e addTechVia [V VIA12]]
$e newPath $jd154 FIXED
$e addITerm [IT M1_5 Y]
$e newPath $emj357 FIXED [RL M9]
set jd155 [$e addTechVia [V {VIA89}]]
$e newPath $jd155 FIXED [RL M8]
$e addPoint 775240 1782900
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 775240 1782980
set jd156 [$e addTechVia [V VIA67]]
$e newPath $jd156 FIXED
$e addPoint 775160 1782980
set jd157 [$e addTechVia [V VIA56]]
$e newPath $jd157 FIXED
$e addPoint 775160 1783076
set jd158 [$e addTechVia [V VIA45]]
$e newPath $jd158 FIXED
$e addPoint 774383 1783076
set jd159 [$e addTechVia [V VIA34]]
$e newPath $jd159 FIXED
$e addPoint 774383 1782900
set jd160 [$e addTechVia [V VIA23]]
$e newPath $jd160 FIXED
$e addPoint 774333 1782900
set jd161 [$e addTechVia [V VIA12]]
$e newPath $jd161 FIXED
$e addITerm [IT M1_6 Y]
$e newPath $emj440 FIXED [RL M9]
set jd162 [$e addTechVia [V {VIA89}]]
$e newPath $jd162 FIXED [RL M8]
$e addPoint 822760 2027340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 822760 2027420
set jd163 [$e addTechVia [V VIA67]]
$e newPath $jd163 FIXED
$e addPoint 822680 2027420
set jd164 [$e addTechVia [V VIA56]]
$e newPath $jd164 FIXED
$e addPoint 822680 2027516
set jd165 [$e addTechVia [V VIA45]]
$e newPath $jd165 FIXED
$e addPoint 821957 2027516
set jd166 [$e addTechVia [V VIA34]]
$e newPath $jd166 FIXED
$e addPoint 821957 2027340
set jd167 [$e addTechVia [V VIA23]]
$e newPath $jd167 FIXED
$e addPoint 821907 2027340
set jd168 [$e addTechVia [V VIA12]]
$e newPath $jd168 FIXED
$e addITerm [IT M1_7 Y]
$e newPath $emj579 FIXED [RL M9]
set jd169 [$e addTechVia [V {VIA89}]]
$e newPath $jd169 FIXED [RL M8]
$e addPoint 822760 2292660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 822760 2292740
set jd170 [$e addTechVia [V VIA67]]
$e newPath $jd170 FIXED
$e addPoint 822680 2292740
set jd171 [$e addTechVia [V VIA56]]
$e newPath $jd171 FIXED
$e addPoint 822680 2292836
set jd172 [$e addTechVia [V VIA45]]
$e newPath $jd172 FIXED
$e addPoint 821957 2292836
set jd173 [$e addTechVia [V VIA34]]
$e newPath $jd173 FIXED
$e addPoint 821957 2292660
set jd174 [$e addTechVia [V VIA23]]
$e newPath $jd174 FIXED
$e addPoint 821907 2292660
set jd175 [$e addTechVia [V VIA12]]
$e newPath $jd175 FIXED
$e addITerm [IT M1_8 Y]
$e newPath $emj529 FIXED [RL M9]
set jd176 [$e addTechVia [V {VIA89}]]
$e newPath $jd176 FIXED [RL M8]
$e addPoint 771320 2567340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 771320 2567420
set jd177 [$e addTechVia [V VIA67]]
$e newPath $jd177 FIXED
$e addPoint 771400 2567420
set jd178 [$e addTechVia [V VIA56]]
$e newPath $jd178 FIXED
$e addPoint 771400 2567516
set jd179 [$e addTechVia [V VIA45]]
$e newPath $jd179 FIXED
$e addPoint 771853 2567516
set jd180 [$e addTechVia [V VIA34]]
$e newPath $jd180 FIXED
$e addPoint 771853 2567340
set jd181 [$e addTechVia [V VIA23]]
$e newPath $jd181 FIXED
$e addPoint 771903 2567340
set jd182 [$e addTechVia [V VIA12]]
$e newPath $jd182 FIXED
$e addITerm [IT M1_9 Y]
$e newPath $emj637 FIXED [RL M9]
set jd183 [$e addTechVia [V {VIA89}]]
$e newPath $jd183 FIXED [RL M8]
$e addPoint 771320 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 771320 2832740
set jd184 [$e addTechVia [V VIA67]]
$e newPath $jd184 FIXED
$e addPoint 771400 2832740
set jd185 [$e addTechVia [V VIA56]]
$e newPath $jd185 FIXED
$e addPoint 771400 2832836
set jd186 [$e addTechVia [V VIA45]]
$e newPath $jd186 FIXED
$e addPoint 771853 2832836
set jd187 [$e addTechVia [V VIA34]]
$e newPath $jd187 FIXED
$e addPoint 771853 2832660
set jd188 [$e addTechVia [V VIA23]]
$e newPath $jd188 FIXED
$e addPoint 771903 2832660
set jd189 [$e addTechVia [V VIA12]]
$e newPath $jd189 FIXED
$e addITerm [IT M1_10 Y]
$e newPath $emj904 FIXED [RL M9]
set jd190 [$e addTechVia [V {VIA89}]]
$e newPath $jd190 FIXED [RL M8]
$e addPoint 771320 3107340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 771320 3107420
set jd191 [$e addTechVia [V VIA67]]
$e newPath $jd191 FIXED
$e addPoint 771400 3107420
set jd192 [$e addTechVia [V VIA56]]
$e newPath $jd192 FIXED
$e addPoint 771400 3107516
set jd193 [$e addTechVia [V VIA45]]
$e newPath $jd193 FIXED
$e addPoint 771853 3107516
set jd194 [$e addTechVia [V VIA34]]
$e newPath $jd194 FIXED
$e addPoint 771853 3107340
set jd195 [$e addTechVia [V VIA23]]
$e newPath $jd195 FIXED
$e addPoint 771903 3107340
set jd196 [$e addTechVia [V VIA12]]
$e newPath $jd196 FIXED
$e addITerm [IT M1_11 Y]
$e newPath $emj1058 FIXED [RL M9]
set jd197 [$e addTechVia [V {VIA89}]]
$e newPath $jd197 FIXED [RL M8]
$e addPoint 771320 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 771320 3372740
set jd198 [$e addTechVia [V VIA67]]
$e newPath $jd198 FIXED
$e addPoint 771400 3372740
set jd199 [$e addTechVia [V VIA56]]
$e newPath $jd199 FIXED
$e addPoint 771400 3372836
set jd200 [$e addTechVia [V VIA45]]
$e newPath $jd200 FIXED
$e addPoint 771853 3372836
set jd201 [$e addTechVia [V VIA34]]
$e newPath $jd201 FIXED
$e addPoint 771853 3372660
set jd202 [$e addTechVia [V VIA23]]
$e newPath $jd202 FIXED
$e addPoint 771903 3372660
set jd203 [$e addTechVia [V VIA12]]
$e newPath $jd203 FIXED
$e addITerm [IT M1_12 Y]
$e newPath $emj1323 FIXED [RL M9]
set jd204 [$e addTechVia [V {VIA89}]]
$e newPath $jd204 FIXED [RL M8]
$e addPoint 771320 3647340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 771320 3647420
set jd205 [$e addTechVia [V VIA67]]
$e newPath $jd205 FIXED
$e addPoint 771400 3647420
set jd206 [$e addTechVia [V VIA56]]
$e newPath $jd206 FIXED
$e addPoint 771400 3647516
set jd207 [$e addTechVia [V VIA45]]
$e newPath $jd207 FIXED
$e addPoint 771853 3647516
set jd208 [$e addTechVia [V VIA34]]
$e newPath $jd208 FIXED
$e addPoint 771853 3647340
set jd209 [$e addTechVia [V VIA23]]
$e newPath $jd209 FIXED
$e addPoint 771903 3647340
set jd210 [$e addTechVia [V VIA12]]
$e newPath $jd210 FIXED
$e addITerm [IT M1_13 Y]
$e newPath $emj1596 FIXED [RL M9]
set jd211 [$e addTechVia [V {VIA89}]]
$e newPath $jd211 FIXED [RL M8]
$e addPoint 771320 3912660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 771320 3912740
set jd212 [$e addTechVia [V VIA67]]
$e newPath $jd212 FIXED
$e addPoint 771400 3912740
set jd213 [$e addTechVia [V VIA56]]
$e newPath $jd213 FIXED
$e addPoint 771400 3912836
set jd214 [$e addTechVia [V VIA45]]
$e newPath $jd214 FIXED
$e addPoint 771853 3912836
set jd215 [$e addTechVia [V VIA34]]
$e newPath $jd215 FIXED
$e addPoint 771853 3912660
set jd216 [$e addTechVia [V VIA23]]
$e newPath $jd216 FIXED
$e addPoint 771903 3912660
set jd217 [$e addTechVia [V VIA12]]
$e newPath $jd217 FIXED
$e addITerm [IT M1_14 Y]
$e newPath $emj1807 FIXED [RL M9]
set jd218 [$e addTechVia [V {VIA89}]]
$e newPath $jd218 FIXED [RL M8]
$e addPoint 771320 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 771320 4187420
set jd219 [$e addTechVia [V VIA67]]
$e newPath $jd219 FIXED
$e addPoint 771400 4187420
set jd220 [$e addTechVia [V VIA56]]
$e newPath $jd220 FIXED
$e addPoint 771400 4187516
set jd221 [$e addTechVia [V VIA45]]
$e newPath $jd221 FIXED
$e addPoint 771853 4187516
set jd222 [$e addTechVia [V VIA34]]
$e newPath $jd222 FIXED
$e addPoint 771853 4187340
set jd223 [$e addTechVia [V VIA23]]
$e newPath $jd223 FIXED
$e addPoint 771903 4187340
set jd224 [$e addTechVia [V VIA12]]
$e newPath $jd224 FIXED
$e addITerm [IT M1_15 Y]
$e newPath $emj66 FIXED [RL M9]
set jd225 [$e addTechVia [V {VIA89}]]
$e newPath $jd225 FIXED [RL M8]
$e addPoint 1388680 132660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1388680 132740
set jd226 [$e addTechVia [V VIA67]]
$e newPath $jd226 FIXED
$e addPoint 1388600 132740
set jd227 [$e addTechVia [V VIA56]]
$e newPath $jd227 FIXED
$e addPoint 1388600 132836
set jd228 [$e addTechVia [V VIA45]]
$e newPath $jd228 FIXED
$e addPoint 1388039 132836
set jd229 [$e addTechVia [V VIA34]]
$e newPath $jd229 FIXED
$e addPoint 1388039 132660
set jd230 [$e addTechVia [V VIA23]]
$e newPath $jd230 FIXED
$e addPoint 1387989 132660
set jd231 [$e addTechVia [V VIA12]]
$e newPath $jd231 FIXED
$e addITerm [IT M2_0 Y]
$e newPath $emj91 FIXED [RL M9]
set jd232 [$e addTechVia [V {VIA89}]]
$e newPath $jd232 FIXED [RL M8]
$e addPoint 1388680 407340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1388680 407420
set jd233 [$e addTechVia [V VIA67]]
$e newPath $jd233 FIXED
$e addPoint 1388600 407420
set jd234 [$e addTechVia [V VIA56]]
$e newPath $jd234 FIXED
$e addPoint 1388600 407516
set jd235 [$e addTechVia [V VIA45]]
$e newPath $jd235 FIXED
$e addPoint 1388039 407516
set jd236 [$e addTechVia [V VIA34]]
$e newPath $jd236 FIXED
$e addPoint 1388039 407340
set jd237 [$e addTechVia [V VIA23]]
$e newPath $jd237 FIXED
$e addPoint 1387989 407340
set jd238 [$e addTechVia [V VIA12]]
$e newPath $jd238 FIXED
$e addITerm [IT M2_1 Y]
$e newPath $emj176 FIXED [RL M9]
set jd239 [$e addTechVia [V {VIA89}]]
$e newPath $jd239 FIXED [RL M8]
$e addPoint 1298360 754740
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1298360 754820
set jd240 [$e addTechVia [V VIA67]]
$e newPath $jd240 FIXED
$e addPoint 1298440 754820
set jd241 [$e addTechVia [V VIA56]]
$e newPath $jd241 FIXED
$e addPoint 1298440 754916
set jd242 [$e addTechVia [V VIA45]]
$e newPath $jd242 FIXED
$e addPoint 1300189 754916
set jd243 [$e addTechVia [V VIA34]]
$e newPath $jd243 FIXED
$e addPoint 1300189 754740
set jd244 [$e addTechVia [V VIA23]]
$e newPath $jd244 FIXED
$e addPoint 1300239 754740
set jd245 [$e addTechVia [V VIA12]]
$e newPath $jd245 FIXED
$e addITerm [IT M2_2 Y]
$e newPath $emj163 FIXED [RL M9]
set jd246 [$e addTechVia [V {VIA89}]]
$e newPath $jd246 FIXED [RL M8]
$e addPoint 1250440 955980
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1250440 956060
set jd247 [$e addTechVia [V VIA67]]
$e newPath $jd247 FIXED
$e addPoint 1250360 956060
set jd248 [$e addTechVia [V VIA56]]
$e newPath $jd248 FIXED
$e addPoint 1250360 956156
set jd249 [$e addTechVia [V VIA45]]
$e newPath $jd249 FIXED
$e addPoint 1249313 956156
set jd250 [$e addTechVia [V VIA34]]
$e newPath $jd250 FIXED
$e addPoint 1249313 955980
set jd251 [$e addTechVia [V VIA23]]
$e newPath $jd251 FIXED
$e addPoint 1249263 955980
set jd252 [$e addTechVia [V VIA12]]
$e newPath $jd252 FIXED
$e addITerm [IT M2_3 Y]
$e newPath $emj213 FIXED [RL M9]
set jd253 [$e addTechVia [V {VIA89}]]
$e newPath $jd253 FIXED [RL M8]
$e addPoint 1250440 1224900
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1250440 1224980
set jd254 [$e addTechVia [V VIA67]]
$e newPath $jd254 FIXED
$e addPoint 1250360 1224980
set jd255 [$e addTechVia [V VIA56]]
$e newPath $jd255 FIXED
$e addPoint 1250360 1225076
set jd256 [$e addTechVia [V VIA45]]
$e newPath $jd256 FIXED
$e addPoint 1249313 1225076
set jd257 [$e addTechVia [V VIA34]]
$e newPath $jd257 FIXED
$e addPoint 1249313 1224900
set jd258 [$e addTechVia [V VIA23]]
$e newPath $jd258 FIXED
$e addPoint 1249263 1224900
set jd259 [$e addTechVia [V VIA12]]
$e newPath $jd259 FIXED
$e addITerm [IT M2_4 Y]
$e newPath $emj282 FIXED [RL M9]
set jd260 [$e addTechVia [V {VIA89}]]
$e newPath $jd260 FIXED [RL M8]
$e addPoint 1250440 1495980
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1250440 1496060
set jd261 [$e addTechVia [V VIA67]]
$e newPath $jd261 FIXED
$e addPoint 1250360 1496060
set jd262 [$e addTechVia [V VIA56]]
$e newPath $jd262 FIXED
$e addPoint 1250360 1496156
set jd263 [$e addTechVia [V VIA45]]
$e newPath $jd263 FIXED
$e addPoint 1249313 1496156
set jd264 [$e addTechVia [V VIA34]]
$e newPath $jd264 FIXED
$e addPoint 1249313 1495980
set jd265 [$e addTechVia [V VIA23]]
$e newPath $jd265 FIXED
$e addPoint 1249263 1495980
set jd266 [$e addTechVia [V VIA12]]
$e newPath $jd266 FIXED
$e addITerm [IT M2_5 Y]
$e newPath $emj434 FIXED [RL M9]
set jd267 [$e addTechVia [V {VIA89}]]
$e newPath $jd267 FIXED [RL M8]
$e addPoint 1293640 1790460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1293640 1790540
set jd268 [$e addTechVia [V VIA67]]
$e newPath $jd268 FIXED
$e addPoint 1293560 1790540
set jd269 [$e addTechVia [V VIA56]]
$e newPath $jd269 FIXED
$e addPoint 1293560 1790636
set jd270 [$e addTechVia [V VIA45]]
$e newPath $jd270 FIXED
$e addPoint 1292297 1790636
set jd271 [$e addTechVia [V VIA34]]
$e newPath $jd271 FIXED
$e addPoint 1292297 1790460
set jd272 [$e addTechVia [V VIA23]]
$e newPath $jd272 FIXED
$e addPoint 1292247 1790460
set jd273 [$e addTechVia [V VIA12]]
$e newPath $jd273 FIXED
$e addITerm [IT M2_6 Y]
$e newPath $emj480 FIXED [RL M9]
set jd274 [$e addTechVia [V {VIA89}]]
$e newPath $jd274 FIXED [RL M8]
$e addPoint 1267720 1808820
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1267720 1808900
set jd275 [$e addTechVia [V VIA67]]
$e newPath $jd275 FIXED
$e addPoint 1267640 1808900
set jd276 [$e addTechVia [V VIA56]]
$e newPath $jd276 FIXED
$e addPoint 1267640 1808996
set jd277 [$e addTechVia [V VIA45]]
$e newPath $jd277 FIXED
$e addPoint 1267187 1808996
set jd278 [$e addTechVia [V VIA34]]
$e newPath $jd278 FIXED
$e addPoint 1267187 1808820
set jd279 [$e addTechVia [V VIA23]]
$e newPath $jd279 FIXED
$e addPoint 1267137 1808820
set jd280 [$e addTechVia [V VIA12]]
$e newPath $jd280 FIXED
$e addITerm [IT M2_7 Y]
$e newPath $emj899 FIXED [RL M9]
set jd281 [$e addTechVia [V {VIA89}]]
$e newPath $jd281 FIXED [RL M8]
$e addPoint 1302280 2465460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1302280 2465540
set jd282 [$e addTechVia [V VIA67]]
$e newPath $jd282 FIXED
$e addPoint 1302200 2465540
set jd283 [$e addTechVia [V VIA56]]
$e newPath $jd283 FIXED
$e addPoint 1302200 2465636
set jd284 [$e addTechVia [V VIA45]]
$e newPath $jd284 FIXED
$e addPoint 1301045 2465636
set jd285 [$e addTechVia [V VIA34]]
$e newPath $jd285 FIXED
$e addPoint 1301045 2465460
set jd286 [$e addTechVia [V VIA23]]
$e newPath $jd286 FIXED
$e addPoint 1300995 2465460
set jd287 [$e addTechVia [V VIA12]]
$e newPath $jd287 FIXED
$e addITerm [IT M2_8 Y]
$e newPath $emj759 FIXED [RL M9]
set jd288 [$e addTechVia [V {VIA89}]]
$e newPath $jd288 FIXED [RL M8]
$e addPoint 1224520 2576160
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1224520 2576240
set jd289 [$e addTechVia [V VIA67]]
$e newPath $jd289 FIXED
$e addPoint 1224440 2576240
set jd290 [$e addTechVia [V VIA56]]
$e newPath $jd290 FIXED
$e addPoint 1224440 2576336
set jd291 [$e addTechVia [V VIA45]]
$e newPath $jd291 FIXED
$e addPoint 1223015 2576336
set jd292 [$e addTechVia [V VIA34]]
$e newPath $jd292 FIXED
$e addPoint 1223015 2576160
set jd293 [$e addTechVia [V VIA23]]
$e newPath $jd293 FIXED
$e addPoint 1222965 2576160
set jd294 [$e addTechVia [V VIA12]]
$e newPath $jd294 FIXED
$e addITerm [IT M2_9 Y]
$e newPath $emj971 FIXED [RL M9]
set jd295 [$e addTechVia [V {VIA89}]]
$e newPath $jd295 FIXED [RL M8]
$e addPoint 1285400 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1285400 2832740
set jd296 [$e addTechVia [V VIA67]]
$e newPath $jd296 FIXED
$e addPoint 1285480 2832740
set jd297 [$e addTechVia [V VIA56]]
$e newPath $jd297 FIXED
$e addPoint 1285480 2832836
set jd298 [$e addTechVia [V VIA45]]
$e newPath $jd298 FIXED
$e addPoint 1285933 2832836
set jd299 [$e addTechVia [V VIA34]]
$e newPath $jd299 FIXED
$e addPoint 1285933 2832660
set jd300 [$e addTechVia [V VIA23]]
$e newPath $jd300 FIXED
$e addPoint 1285983 2832660
set jd301 [$e addTechVia [V VIA12]]
$e newPath $jd301 FIXED
$e addITerm [IT M2_10 Y]
$e newPath $emj1122 FIXED [RL M9]
set jd302 [$e addTechVia [V {VIA89}]]
$e newPath $jd302 FIXED [RL M8]
$e addPoint 1285400 3107340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1285400 3107420
set jd303 [$e addTechVia [V VIA67]]
$e newPath $jd303 FIXED
$e addPoint 1285480 3107420
set jd304 [$e addTechVia [V VIA56]]
$e newPath $jd304 FIXED
$e addPoint 1285480 3107516
set jd305 [$e addTechVia [V VIA45]]
$e newPath $jd305 FIXED
$e addPoint 1285933 3107516
set jd306 [$e addTechVia [V VIA34]]
$e newPath $jd306 FIXED
$e addPoint 1285933 3107340
set jd307 [$e addTechVia [V VIA23]]
$e newPath $jd307 FIXED
$e addPoint 1285983 3107340
set jd308 [$e addTechVia [V VIA12]]
$e newPath $jd308 FIXED
$e addITerm [IT M2_11 Y]
$e newPath $emj1526 FIXED [RL M9]
set jd309 [$e addTechVia [V {VIA89}]]
$e newPath $jd309 FIXED [RL M8]
$e addPoint 1142840 3388140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1142840 3388220
set jd310 [$e addTechVia [V VIA67]]
$e newPath $jd310 FIXED
$e addPoint 1142920 3388220
set jd311 [$e addTechVia [V VIA56]]
$e newPath $jd311 FIXED
$e addPoint 1142920 3388316
set jd312 [$e addTechVia [V VIA45]]
$e newPath $jd312 FIXED
$e addPoint 1144453 3388316
set jd313 [$e addTechVia [V VIA34]]
$e newPath $jd313 FIXED
$e addPoint 1144453 3388140
set jd314 [$e addTechVia [V VIA23]]
$e newPath $jd314 FIXED
$e addPoint 1144503 3388140
set jd315 [$e addTechVia [V VIA12]]
$e newPath $jd315 FIXED
$e addITerm [IT M2_12 Y]
$e newPath $emj1593 FIXED [RL M9]
set jd316 [$e addTechVia [V {VIA89}]]
$e newPath $jd316 FIXED [RL M8]
$e addPoint 1294040 3668940
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1294040 3669020
set jd317 [$e addTechVia [V VIA67]]
$e newPath $jd317 FIXED
$e addPoint 1294120 3669020
set jd318 [$e addTechVia [V VIA56]]
$e newPath $jd318 FIXED
$e addPoint 1294120 3669116
set jd319 [$e addTechVia [V VIA45]]
$e newPath $jd319 FIXED
$e addPoint 1294024 3669116
set jd320 [$e addTechVia [V VIA34]]
$e newPath $jd320 FIXED
$e addPoint 1294024 3668940
set jd321 [$e addTechVia [V VIA23]]
$e newPath $jd321 FIXED
$e addPoint 1294191 3668940
set jd322 [$e addTechVia [V VIA12]]
$e newPath $jd322 FIXED
$e addITerm [IT M2_13 Y]
$e newPath $emj1654 FIXED [RL M9]
set jd323 [$e addTechVia [V {VIA89}]]
$e newPath $jd323 FIXED [RL M8]
$e addPoint 1285400 3912660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1285400 3912740
set jd324 [$e addTechVia [V VIA67]]
$e newPath $jd324 FIXED
$e addPoint 1285480 3912740
set jd325 [$e addTechVia [V VIA56]]
$e newPath $jd325 FIXED
$e addPoint 1285480 3912836
set jd326 [$e addTechVia [V VIA45]]
$e newPath $jd326 FIXED
$e addPoint 1285933 3912836
set jd327 [$e addTechVia [V VIA34]]
$e newPath $jd327 FIXED
$e addPoint 1285933 3912660
set jd328 [$e addTechVia [V VIA23]]
$e newPath $jd328 FIXED
$e addPoint 1285983 3912660
set jd329 [$e addTechVia [V VIA12]]
$e newPath $jd329 FIXED
$e addITerm [IT M2_14 Y]
$e newPath $emj1862 FIXED [RL M9]
set jd330 [$e addTechVia [V {VIA89}]]
$e newPath $jd330 FIXED [RL M8]
$e addPoint 1285400 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1285400 4187420
set jd331 [$e addTechVia [V VIA67]]
$e newPath $jd331 FIXED
$e addPoint 1285480 4187420
set jd332 [$e addTechVia [V VIA56]]
$e newPath $jd332 FIXED
$e addPoint 1285480 4187516
set jd333 [$e addTechVia [V VIA45]]
$e newPath $jd333 FIXED
$e addPoint 1285933 4187516
set jd334 [$e addTechVia [V VIA34]]
$e newPath $jd334 FIXED
$e addPoint 1285933 4187340
set jd335 [$e addTechVia [V VIA23]]
$e newPath $jd335 FIXED
$e addPoint 1285983 4187340
set jd336 [$e addTechVia [V VIA12]]
$e newPath $jd336 FIXED
$e addITerm [IT M2_15 Y]
$e newPath $emj133 FIXED [RL M9]
set jd337 [$e addTechVia [V {VIA89}]]
$e newPath $jd337 FIXED [RL M8]
$e addPoint 1790440 3060
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1790440 3140
set jd338 [$e addTechVia [V VIA67]]
$e newPath $jd338 FIXED
$e addPoint 1790360 3140
set jd339 [$e addTechVia [V VIA56]]
$e newPath $jd339 FIXED
$e addPoint 1790360 3236
set jd340 [$e addTechVia [V VIA45]]
$e newPath $jd340 FIXED
$e addPoint 1788611 3236
set jd341 [$e addTechVia [V VIA34]]
$e newPath $jd341 FIXED
$e addPoint 1788611 3060
set jd342 [$e addTechVia [V VIA23]]
$e newPath $jd342 FIXED
$e addPoint 1788561 3060
set jd343 [$e addTechVia [V VIA12]]
$e newPath $jd343 FIXED
$e addITerm [IT M3_0 Y]
$e newPath $emj124 FIXED [RL M9]
set jd344 [$e addTechVia [V {VIA89}]]
$e newPath $jd344 FIXED [RL M8]
$e addPoint 1475080 407340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1475080 407420
set jd345 [$e addTechVia [V VIA67]]
$e newPath $jd345 FIXED
$e addPoint 1475000 407420
set jd346 [$e addTechVia [V VIA56]]
$e newPath $jd346 FIXED
$e addPoint 1475000 407516
set jd347 [$e addTechVia [V VIA45]]
$e newPath $jd347 FIXED
$e addPoint 1474115 407516
set jd348 [$e addTechVia [V VIA34]]
$e newPath $jd348 FIXED
$e addPoint 1474115 407340
set jd349 [$e addTechVia [V VIA23]]
$e newPath $jd349 FIXED
$e addPoint 1474065 407340
set jd350 [$e addTechVia [V VIA12]]
$e newPath $jd350 FIXED
$e addITerm [IT M3_1 Y]
$e newPath $emj219 FIXED [RL M9]
set jd351 [$e addTechVia [V {VIA89}]]
$e newPath $jd351 FIXED [RL M8]
$e addPoint 1816760 774540
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1816760 774620
set jd352 [$e addTechVia [V VIA67]]
$e newPath $jd352 FIXED
$e addPoint 1816840 774620
set jd353 [$e addTechVia [V VIA56]]
$e newPath $jd353 FIXED
$e addPoint 1816840 774716
set jd354 [$e addTechVia [V VIA45]]
$e newPath $jd354 FIXED
$e addPoint 1817401 774716
set jd355 [$e addTechVia [V VIA34]]
$e newPath $jd355 FIXED
$e addPoint 1817401 774540
set jd356 [$e addTechVia [V VIA23]]
$e newPath $jd356 FIXED
$e addPoint 1817451 774540
set jd357 [$e addTechVia [V VIA12]]
$e newPath $jd357 FIXED
$e addITerm [IT M3_2 Y]
$e newPath $emj246 FIXED [RL M9]
set jd358 [$e addTechVia [V {VIA89}]]
$e newPath $jd358 FIXED [RL M8]
$e addPoint 1790440 832500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1790440 832580
set jd359 [$e addTechVia [V VIA67]]
$e newPath $jd359 FIXED
$e addPoint 1790360 832580
set jd360 [$e addTechVia [V VIA56]]
$e newPath $jd360 FIXED
$e addPoint 1790360 832676
set jd361 [$e addTechVia [V VIA45]]
$e newPath $jd361 FIXED
$e addPoint 1790456 832676
set jd362 [$e addTechVia [V VIA34]]
$e newPath $jd362 FIXED
$e addPoint 1790456 832500
set jd363 [$e addTechVia [V VIA23]]
$e newPath $jd363 FIXED
$e addPoint 1790289 832500
set jd364 [$e addTechVia [V VIA12]]
$e newPath $jd364 FIXED
$e addITerm [IT M3_3 Y]
$e newPath $emj266 FIXED [RL M9]
set jd365 [$e addTechVia [V {VIA89}]]
$e newPath $jd365 FIXED [RL M8]
$e addPoint 1799480 1362060
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1799480 1362140
set jd366 [$e addTechVia [V VIA67]]
$e newPath $jd366 FIXED
$e addPoint 1799560 1362140
set jd367 [$e addTechVia [V VIA56]]
$e newPath $jd367 FIXED
$e addPoint 1799560 1362236
set jd368 [$e addTechVia [V VIA45]]
$e newPath $jd368 FIXED
$e addPoint 1800013 1362236
set jd369 [$e addTechVia [V VIA34]]
$e newPath $jd369 FIXED
$e addPoint 1800013 1362060
set jd370 [$e addTechVia [V VIA23]]
$e newPath $jd370 FIXED
$e addPoint 1800063 1362060
set jd371 [$e addTechVia [V VIA12]]
$e newPath $jd371 FIXED
$e addITerm [IT M3_4 Y]
$e newPath $emj353 FIXED [RL M9]
set jd372 [$e addTechVia [V {VIA89}]]
$e newPath $jd372 FIXED [RL M8]
$e addPoint 1777480 1489140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1777480 1489220
set jd373 [$e addTechVia [V VIA67]]
$e newPath $jd373 FIXED
$e addPoint 1777400 1489220
set jd374 [$e addTechVia [V VIA56]]
$e newPath $jd374 FIXED
$e addPoint 1777400 1489316
set jd375 [$e addTechVia [V VIA45]]
$e newPath $jd375 FIXED
$e addPoint 1776461 1489316
set jd376 [$e addTechVia [V VIA34]]
$e newPath $jd376 FIXED
$e addPoint 1776461 1489140
set jd377 [$e addTechVia [V VIA23]]
$e newPath $jd377 FIXED
$e addPoint 1776411 1489140
set jd378 [$e addTechVia [V VIA12]]
$e newPath $jd378 FIXED
$e addITerm [IT M3_5 Y]
$e newPath $emj574 FIXED [RL M9]
set jd379 [$e addTechVia [V {VIA89}]]
$e newPath $jd379 FIXED [RL M8]
$e addPoint 1691080 1752660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1691080 1752740
set jd380 [$e addTechVia [V VIA67]]
$e newPath $jd380 FIXED
$e addPoint 1691000 1752740
set jd381 [$e addTechVia [V VIA56]]
$e newPath $jd381 FIXED
$e addPoint 1691000 1752836
set jd382 [$e addTechVia [V VIA45]]
$e newPath $jd382 FIXED
$e addPoint 1690115 1752836
set jd383 [$e addTechVia [V VIA34]]
$e newPath $jd383 FIXED
$e addPoint 1690115 1752660
set jd384 [$e addTechVia [V VIA23]]
$e newPath $jd384 FIXED
$e addPoint 1690065 1752660
set jd385 [$e addTechVia [V VIA12]]
$e newPath $jd385 FIXED
$e addITerm [IT M3_6 Y]
$e newPath $emj631 FIXED [RL M9]
set jd386 [$e addTechVia [V {VIA89}]]
$e newPath $jd386 FIXED [RL M8]
$e addPoint 1812040 2070540
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1812040 2070620
set jd387 [$e addTechVia [V VIA67]]
$e newPath $jd387 FIXED
$e addPoint 1811960 2070620
set jd388 [$e addTechVia [V VIA56]]
$e newPath $jd388 FIXED
$e addPoint 1811960 2070716
set jd389 [$e addTechVia [V VIA45]]
$e newPath $jd389 FIXED
$e addPoint 1812056 2070716
set jd390 [$e addTechVia [V VIA34]]
$e newPath $jd390 FIXED
$e addPoint 1812056 2070540
set jd391 [$e addTechVia [V VIA23]]
$e newPath $jd391 FIXED
$e addPoint 1811943 2070540
set jd392 [$e addTechVia [V VIA12]]
$e newPath $jd392 FIXED
$e addITerm [IT M3_7 Y]
$e newPath $emj885 FIXED [RL M9]
set jd393 [$e addTechVia [V {VIA89}]]
$e newPath $jd393 FIXED [RL M8]
$e addPoint 1786520 2249460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1786520 2249540
set jd394 [$e addTechVia [V VIA67]]
$e newPath $jd394 FIXED
$e addPoint 1786600 2249540
set jd395 [$e addTechVia [V VIA56]]
$e newPath $jd395 FIXED
$e addPoint 1786600 2249636
set jd396 [$e addTechVia [V VIA45]]
$e newPath $jd396 FIXED
$e addPoint 1788133 2249636
set jd397 [$e addTechVia [V VIA34]]
$e newPath $jd397 FIXED
$e addPoint 1788133 2249460
set jd398 [$e addTechVia [V VIA23]]
$e newPath $jd398 FIXED
$e addPoint 1788183 2249460
set jd399 [$e addTechVia [V VIA12]]
$e newPath $jd399 FIXED
$e addITerm [IT M3_8 Y]
$e newPath $emj958 FIXED [RL M9]
set jd400 [$e addTechVia [V {VIA89}]]
$e newPath $jd400 FIXED [RL M8]
$e addPoint 1691080 2567340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1691080 2567420
set jd401 [$e addTechVia [V VIA67]]
$e newPath $jd401 FIXED
$e addPoint 1691000 2567420
set jd402 [$e addTechVia [V VIA56]]
$e newPath $jd402 FIXED
$e addPoint 1691000 2567516
set jd403 [$e addTechVia [V VIA45]]
$e newPath $jd403 FIXED
$e addPoint 1690115 2567516
set jd404 [$e addTechVia [V VIA34]]
$e newPath $jd404 FIXED
$e addPoint 1690115 2567340
set jd405 [$e addTechVia [V VIA23]]
$e newPath $jd405 FIXED
$e addPoint 1690065 2567340
set jd406 [$e addTechVia [V VIA12]]
$e newPath $jd406 FIXED
$e addITerm [IT M3_9 Y]
$e newPath $emj1176 FIXED [RL M9]
set jd407 [$e addTechVia [V {VIA89}]]
$e newPath $jd407 FIXED [RL M8]
$e addPoint 1786120 2840580
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1786120 2840660
set jd408 [$e addTechVia [V VIA67]]
$e newPath $jd408 FIXED
$e addPoint 1786040 2840660
set jd409 [$e addTechVia [V VIA56]]
$e newPath $jd409 FIXED
$e addPoint 1786040 2840756
set jd410 [$e addTechVia [V VIA45]]
$e newPath $jd410 FIXED
$e addPoint 1785101 2840756
set jd411 [$e addTechVia [V VIA34]]
$e newPath $jd411 FIXED
$e addPoint 1785101 2840580
set jd412 [$e addTechVia [V VIA23]]
$e newPath $jd412 FIXED
$e addPoint 1785051 2840580
set jd413 [$e addTechVia [V VIA12]]
$e newPath $jd413 FIXED
$e addITerm [IT M3_10 Y]
$e newPath $emj1256 FIXED [RL M9]
set jd414 [$e addTechVia [V {VIA89}]]
$e newPath $jd414 FIXED [RL M8]
$e addPoint 1691080 3107340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1691080 3107420
set jd415 [$e addTechVia [V VIA67]]
$e newPath $jd415 FIXED
$e addPoint 1691000 3107420
set jd416 [$e addTechVia [V VIA56]]
$e newPath $jd416 FIXED
$e addPoint 1691000 3107516
set jd417 [$e addTechVia [V VIA45]]
$e newPath $jd417 FIXED
$e addPoint 1690115 3107516
set jd418 [$e addTechVia [V VIA34]]
$e newPath $jd418 FIXED
$e addPoint 1690115 3107340
set jd419 [$e addTechVia [V VIA23]]
$e newPath $jd419 FIXED
$e addPoint 1690065 3107340
set jd420 [$e addTechVia [V VIA12]]
$e newPath $jd420 FIXED
$e addITerm [IT M3_11 Y]
$e newPath $emj1583 FIXED [RL M9]
set jd421 [$e addTechVia [V {VIA89}]]
$e newPath $jd421 FIXED [RL M8]
$e addPoint 1691080 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1691080 3372740
set jd422 [$e addTechVia [V VIA67]]
$e newPath $jd422 FIXED
$e addPoint 1691000 3372740
set jd423 [$e addTechVia [V VIA56]]
$e newPath $jd423 FIXED
$e addPoint 1691000 3372836
set jd424 [$e addTechVia [V VIA45]]
$e newPath $jd424 FIXED
$e addPoint 1690115 3372836
set jd425 [$e addTechVia [V VIA34]]
$e newPath $jd425 FIXED
$e addPoint 1690115 3372660
set jd426 [$e addTechVia [V VIA23]]
$e newPath $jd426 FIXED
$e addPoint 1690065 3372660
set jd427 [$e addTechVia [V VIA12]]
$e newPath $jd427 FIXED
$e addITerm [IT M3_12 Y]
$e newPath $emj1523 FIXED [RL M9]
set jd428 [$e addTechVia [V {VIA89}]]
$e newPath $jd428 FIXED [RL M8]
$e addPoint 1799480 3647340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1799480 3647420
set jd429 [$e addTechVia [V VIA67]]
$e newPath $jd429 FIXED
$e addPoint 1799560 3647420
set jd430 [$e addTechVia [V VIA56]]
$e newPath $jd430 FIXED
$e addPoint 1799560 3647516
set jd431 [$e addTechVia [V VIA45]]
$e newPath $jd431 FIXED
$e addPoint 1800013 3647516
set jd432 [$e addTechVia [V VIA34]]
$e newPath $jd432 FIXED
$e addPoint 1800013 3647340
set jd433 [$e addTechVia [V VIA23]]
$e newPath $jd433 FIXED
$e addPoint 1800063 3647340
set jd434 [$e addTechVia [V VIA12]]
$e newPath $jd434 FIXED
$e addITerm [IT M3_13 Y]
$e newPath $emj1971 FIXED [RL M9]
set jd435 [$e addTechVia [V {VIA89}]]
$e newPath $jd435 FIXED [RL M8]
$e addPoint 1807720 3932460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1807720 3932540
set jd436 [$e addTechVia [V VIA67]]
$e newPath $jd436 FIXED
$e addPoint 1807640 3932540
set jd437 [$e addTechVia [V VIA56]]
$e newPath $jd437 FIXED
$e addPoint 1807640 3932636
set jd438 [$e addTechVia [V VIA45]]
$e newPath $jd438 FIXED
$e addPoint 1806269 3932636
set jd439 [$e addTechVia [V VIA34]]
$e newPath $jd439 FIXED
$e addPoint 1806269 3932460
set jd440 [$e addTechVia [V VIA23]]
$e newPath $jd440 FIXED
$e addPoint 1806219 3932460
set jd441 [$e addTechVia [V VIA12]]
$e newPath $jd441 FIXED
$e addITerm [IT M3_14 Y]
$e newPath $emj1914 FIXED [RL M9]
set jd442 [$e addTechVia [V {VIA89}]]
$e newPath $jd442 FIXED [RL M8]
$e addPoint 1799480 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1799480 4187420
set jd443 [$e addTechVia [V VIA67]]
$e newPath $jd443 FIXED
$e addPoint 1799560 4187420
set jd444 [$e addTechVia [V VIA56]]
$e newPath $jd444 FIXED
$e addPoint 1799560 4187516
set jd445 [$e addTechVia [V VIA45]]
$e newPath $jd445 FIXED
$e addPoint 1800013 4187516
set jd446 [$e addTechVia [V VIA34]]
$e newPath $jd446 FIXED
$e addPoint 1800013 4187340
set jd447 [$e addTechVia [V VIA23]]
$e newPath $jd447 FIXED
$e addPoint 1800063 4187340
set jd448 [$e addTechVia [V VIA12]]
$e newPath $jd448 FIXED
$e addITerm [IT M3_15 Y]
$e newPath $emj193 FIXED [RL M9]
set jd449 [$e addTechVia [V {VIA89}]]
$e newPath $jd449 FIXED [RL M8]
$e addPoint 2425480 132660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2425480 132740
set jd450 [$e addTechVia [V VIA67]]
$e newPath $jd450 FIXED
$e addPoint 2425400 132740
set jd451 [$e addTechVia [V VIA56]]
$e newPath $jd451 FIXED
$e addPoint 2425400 132836
set jd452 [$e addTechVia [V VIA45]]
$e newPath $jd452 FIXED
$e addPoint 2423867 132836
set jd453 [$e addTechVia [V VIA34]]
$e newPath $jd453 FIXED
$e addPoint 2423867 132660
set jd454 [$e addTechVia [V VIA23]]
$e newPath $jd454 FIXED
$e addPoint 2423817 132660
set jd455 [$e addTechVia [V VIA12]]
$e newPath $jd455 FIXED
$e addITerm [IT M4_0 Y]
$e newPath $emj184 FIXED [RL M9]
set jd456 [$e addTechVia [V {VIA89}]]
$e newPath $jd456 FIXED [RL M8]
$e addPoint 2425480 407340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2425480 407420
set jd457 [$e addTechVia [V VIA67]]
$e newPath $jd457 FIXED
$e addPoint 2425400 407420
set jd458 [$e addTechVia [V VIA56]]
$e newPath $jd458 FIXED
$e addPoint 2425400 407516
set jd459 [$e addTechVia [V VIA45]]
$e newPath $jd459 FIXED
$e addPoint 2423867 407516
set jd460 [$e addTechVia [V VIA34]]
$e newPath $jd460 FIXED
$e addPoint 2423867 407340
set jd461 [$e addTechVia [V VIA23]]
$e newPath $jd461 FIXED
$e addPoint 2423817 407340
set jd462 [$e addTechVia [V VIA12]]
$e newPath $jd462 FIXED
$e addITerm [IT M4_1 Y]
$e newPath $emj276 FIXED [RL M9]
set jd463 [$e addTechVia [V {VIA89}]]
$e newPath $jd463 FIXED [RL M8]
$e addPoint 2326520 774540
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2326520 774620
set jd464 [$e addTechVia [V VIA67]]
$e newPath $jd464 FIXED
$e addPoint 2326600 774620
set jd465 [$e addTechVia [V VIA56]]
$e newPath $jd465 FIXED
$e addPoint 2326600 774716
set jd466 [$e addTechVia [V VIA45]]
$e newPath $jd466 FIXED
$e addPoint 2327161 774716
set jd467 [$e addTechVia [V VIA34]]
$e newPath $jd467 FIXED
$e addPoint 2327161 774540
set jd468 [$e addTechVia [V VIA23]]
$e newPath $jd468 FIXED
$e addPoint 2327211 774540
set jd469 [$e addTechVia [V VIA12]]
$e newPath $jd469 FIXED
$e addITerm [IT M4_2 Y]
$e newPath $emj351 FIXED [RL M9]
set jd470 [$e addTechVia [V {VIA89}]]
$e newPath $jd470 FIXED [RL M8]
$e addPoint 2326520 845460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2326520 845540
set jd471 [$e addTechVia [V VIA67]]
$e newPath $jd471 FIXED
$e addPoint 2326600 845540
set jd472 [$e addTechVia [V VIA56]]
$e newPath $jd472 FIXED
$e addPoint 2326600 845636
set jd473 [$e addTechVia [V VIA45]]
$e newPath $jd473 FIXED
$e addPoint 2327161 845636
set jd474 [$e addTechVia [V VIA34]]
$e newPath $jd474 FIXED
$e addPoint 2327161 845460
set jd475 [$e addTechVia [V VIA23]]
$e newPath $jd475 FIXED
$e addPoint 2327211 845460
set jd476 [$e addTechVia [V VIA12]]
$e newPath $jd476 FIXED
$e addITerm [IT M4_3 Y]
$e newPath $emj340 FIXED [RL M9]
set jd477 [$e addTechVia [V {VIA89}]]
$e newPath $jd477 FIXED [RL M8]
$e addPoint 2317880 1247220
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2317880 1247300
set jd478 [$e addTechVia [V VIA67]]
$e newPath $jd478 FIXED
$e addPoint 2317960 1247300
set jd479 [$e addTechVia [V VIA56]]
$e newPath $jd479 FIXED
$e addPoint 2317960 1247396
set jd480 [$e addTechVia [V VIA45]]
$e newPath $jd480 FIXED
$e addPoint 2318575 1247396
set jd481 [$e addTechVia [V VIA34]]
$e newPath $jd481 FIXED
$e addPoint 2318575 1247220
set jd482 [$e addTechVia [V VIA23]]
$e newPath $jd482 FIXED
$e addPoint 2318625 1247220
set jd483 [$e addTechVia [V VIA12]]
$e newPath $jd483 FIXED
$e addITerm [IT M4_4 Y]
$e newPath $emj560 FIXED [RL M9]
set jd484 [$e addTechVia [V {VIA89}]]
$e newPath $jd484 FIXED [RL M8]
$e addPoint 2313160 1487340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2313160 1487420
set jd485 [$e addTechVia [V VIA67]]
$e newPath $jd485 FIXED
$e addPoint 2313080 1487420
set jd486 [$e addTechVia [V VIA56]]
$e newPath $jd486 FIXED
$e addPoint 2313080 1487516
set jd487 [$e addTechVia [V VIA45]]
$e newPath $jd487 FIXED
$e addPoint 2311871 1487516
set jd488 [$e addTechVia [V VIA34]]
$e newPath $jd488 FIXED
$e addPoint 2311871 1487340
set jd489 [$e addTechVia [V VIA23]]
$e newPath $jd489 FIXED
$e addPoint 2311821 1487340
set jd490 [$e addTechVia [V VIA12]]
$e newPath $jd490 FIXED
$e addITerm [IT M4_5 Y]
$e newPath $emj675 FIXED [RL M9]
set jd491 [$e addTechVia [V {VIA89}]]
$e newPath $jd491 FIXED [RL M8]
$e addPoint 2322200 1759500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2322200 1759580
set jd492 [$e addTechVia [V VIA67]]
$e newPath $jd492 FIXED
$e addPoint 2322280 1759580
set jd493 [$e addTechVia [V VIA56]]
$e newPath $jd493 FIXED
$e addPoint 2322280 1759676
set jd494 [$e addTechVia [V VIA45]]
$e newPath $jd494 FIXED
$e addPoint 2323273 1759676
set jd495 [$e addTechVia [V VIA34]]
$e newPath $jd495 FIXED
$e addPoint 2323273 1759500
set jd496 [$e addTechVia [V VIA23]]
$e newPath $jd496 FIXED
$e addPoint 2323323 1759500
set jd497 [$e addTechVia [V VIA12]]
$e newPath $jd497 FIXED
$e addITerm [IT M4_6 Y]
$e newPath $emj672 FIXED [RL M9]
set jd498 [$e addTechVia [V {VIA89}]]
$e newPath $jd498 FIXED [RL M8]
$e addPoint 2309240 2027340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2309240 2027420
set jd499 [$e addTechVia [V VIA67]]
$e newPath $jd499 FIXED
$e addPoint 2309320 2027420
set jd500 [$e addTechVia [V VIA56]]
$e newPath $jd500 FIXED
$e addPoint 2309320 2027516
set jd501 [$e addTechVia [V VIA45]]
$e newPath $jd501 FIXED
$e addPoint 2309773 2027516
set jd502 [$e addTechVia [V VIA34]]
$e newPath $jd502 FIXED
$e addPoint 2309773 2027340
set jd503 [$e addTechVia [V VIA23]]
$e newPath $jd503 FIXED
$e addPoint 2309823 2027340
set jd504 [$e addTechVia [V VIA12]]
$e newPath $jd504 FIXED
$e addITerm [IT M4_7 Y]
$e newPath $emj956 FIXED [RL M9]
set jd505 [$e addTechVia [V {VIA89}]]
$e newPath $jd505 FIXED [RL M8]
$e addPoint 2322200 2292660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2322200 2292740
set jd506 [$e addTechVia [V VIA67]]
$e newPath $jd506 FIXED
$e addPoint 2322280 2292740
set jd507 [$e addTechVia [V VIA56]]
$e newPath $jd507 FIXED
$e addPoint 2322280 2292836
set jd508 [$e addTechVia [V VIA45]]
$e newPath $jd508 FIXED
$e addPoint 2323759 2292836
set jd509 [$e addTechVia [V VIA34]]
$e newPath $jd509 FIXED
$e addPoint 2323759 2292660
set jd510 [$e addTechVia [V VIA23]]
$e newPath $jd510 FIXED
$e addPoint 2323809 2292660
set jd511 [$e addTechVia [V VIA12]]
$e newPath $jd511 FIXED
$e addITerm [IT M4_8 Y]
$e newPath $emj1040 FIXED [RL M9]
set jd512 [$e addTechVia [V {VIA89}]]
$e newPath $jd512 FIXED [RL M8]
$e addPoint 2322200 2567340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2322200 2567420
set jd513 [$e addTechVia [V VIA67]]
$e newPath $jd513 FIXED
$e addPoint 2322280 2567420
set jd514 [$e addTechVia [V VIA56]]
$e newPath $jd514 FIXED
$e addPoint 2322280 2567516
set jd515 [$e addTechVia [V VIA45]]
$e newPath $jd515 FIXED
$e addPoint 2323759 2567516
set jd516 [$e addTechVia [V VIA34]]
$e newPath $jd516 FIXED
$e addPoint 2323759 2567340
set jd517 [$e addTechVia [V VIA23]]
$e newPath $jd517 FIXED
$e addPoint 2323809 2567340
set jd518 [$e addTechVia [V VIA12]]
$e newPath $jd518 FIXED
$e addITerm [IT M4_9 Y]
$e newPath $emj1245 FIXED [RL M9]
set jd519 [$e addTechVia [V {VIA89}]]
$e newPath $jd519 FIXED [RL M8]
$e addPoint 2309240 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2309240 2832740
set jd520 [$e addTechVia [V VIA67]]
$e newPath $jd520 FIXED
$e addPoint 2309320 2832740
set jd521 [$e addTechVia [V VIA56]]
$e newPath $jd521 FIXED
$e addPoint 2309320 2832836
set jd522 [$e addTechVia [V VIA45]]
$e newPath $jd522 FIXED
$e addPoint 2309773 2832836
set jd523 [$e addTechVia [V VIA34]]
$e newPath $jd523 FIXED
$e addPoint 2309773 2832660
set jd524 [$e addTechVia [V VIA23]]
$e newPath $jd524 FIXED
$e addPoint 2309823 2832660
set jd525 [$e addTechVia [V VIA12]]
$e newPath $jd525 FIXED
$e addITerm [IT M4_10 Y]
$e newPath $emj1451 FIXED [RL M9]
set jd526 [$e addTechVia [V {VIA89}]]
$e newPath $jd526 FIXED [RL M8]
$e addPoint 2322200 3107340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2322200 3107420
set jd527 [$e addTechVia [V VIA67]]
$e newPath $jd527 FIXED
$e addPoint 2322280 3107420
set jd528 [$e addTechVia [V VIA56]]
$e newPath $jd528 FIXED
$e addPoint 2322280 3107516
set jd529 [$e addTechVia [V VIA45]]
$e newPath $jd529 FIXED
$e addPoint 2323759 3107516
set jd530 [$e addTechVia [V VIA34]]
$e newPath $jd530 FIXED
$e addPoint 2323759 3107340
set jd531 [$e addTechVia [V VIA23]]
$e newPath $jd531 FIXED
$e addPoint 2323809 3107340
set jd532 [$e addTechVia [V VIA12]]
$e newPath $jd532 FIXED
$e addITerm [IT M4_11 Y]
$e newPath $emj1517 FIXED [RL M9]
set jd533 [$e addTechVia [V {VIA89}]]
$e newPath $jd533 FIXED [RL M8]
$e addPoint 2309240 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2309240 3372740
set jd534 [$e addTechVia [V VIA67]]
$e newPath $jd534 FIXED
$e addPoint 2309320 3372740
set jd535 [$e addTechVia [V VIA56]]
$e newPath $jd535 FIXED
$e addPoint 2309320 3372836
set jd536 [$e addTechVia [V VIA45]]
$e newPath $jd536 FIXED
$e addPoint 2309773 3372836
set jd537 [$e addTechVia [V VIA34]]
$e newPath $jd537 FIXED
$e addPoint 2309773 3372660
set jd538 [$e addTechVia [V VIA23]]
$e newPath $jd538 FIXED
$e addPoint 2309823 3372660
set jd539 [$e addTechVia [V VIA12]]
$e newPath $jd539 FIXED
$e addITerm [IT M4_12 Y]
$e newPath $emj1696 FIXED [RL M9]
set jd540 [$e addTechVia [V {VIA89}]]
$e newPath $jd540 FIXED [RL M8]
$e addPoint 2309240 3647340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2309240 3647420
set jd541 [$e addTechVia [V VIA67]]
$e newPath $jd541 FIXED
$e addPoint 2309320 3647420
set jd542 [$e addTechVia [V VIA56]]
$e newPath $jd542 FIXED
$e addPoint 2309320 3647516
set jd543 [$e addTechVia [V VIA45]]
$e newPath $jd543 FIXED
$e addPoint 2309773 3647516
set jd544 [$e addTechVia [V VIA34]]
$e newPath $jd544 FIXED
$e addPoint 2309773 3647340
set jd545 [$e addTechVia [V VIA23]]
$e newPath $jd545 FIXED
$e addPoint 2309823 3647340
set jd546 [$e addTechVia [V VIA12]]
$e newPath $jd546 FIXED
$e addITerm [IT M4_13 Y]
$e newPath $emj2025 FIXED [RL M9]
set jd547 [$e addTechVia [V {VIA89}]]
$e newPath $jd547 FIXED [RL M8]
$e addPoint 2261320 3919500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2261320 3919580
set jd548 [$e addTechVia [V VIA67]]
$e newPath $jd548 FIXED
$e addPoint 2261240 3919580
set jd549 [$e addTechVia [V VIA56]]
$e newPath $jd549 FIXED
$e addPoint 2261240 3919676
set jd550 [$e addTechVia [V VIA45]]
$e newPath $jd550 FIXED
$e addPoint 2260085 3919676
set jd551 [$e addTechVia [V VIA34]]
$e newPath $jd551 FIXED
$e addPoint 2260085 3919500
set jd552 [$e addTechVia [V VIA23]]
$e newPath $jd552 FIXED
$e addPoint 2260035 3919500
set jd553 [$e addTechVia [V VIA12]]
$e newPath $jd553 FIXED
$e addITerm [IT M4_14 Y]
$e newPath $emj2067 FIXED [RL M9]
set jd554 [$e addTechVia [V {VIA89}]]
$e newPath $jd554 FIXED [RL M8]
$e addPoint 2309240 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2309240 4187420
set jd555 [$e addTechVia [V VIA67]]
$e newPath $jd555 FIXED
$e addPoint 2309320 4187420
set jd556 [$e addTechVia [V VIA56]]
$e newPath $jd556 FIXED
$e addPoint 2309320 4187516
set jd557 [$e addTechVia [V VIA45]]
$e newPath $jd557 FIXED
$e addPoint 2309773 4187516
set jd558 [$e addTechVia [V VIA34]]
$e newPath $jd558 FIXED
$e addPoint 2309773 4187340
set jd559 [$e addTechVia [V VIA23]]
$e newPath $jd559 FIXED
$e addPoint 2309823 4187340
set jd560 [$e addTechVia [V VIA12]]
$e newPath $jd560 FIXED
$e addITerm [IT M4_15 Y]
$e newPath $emj332 FIXED [RL M9]
set jd561 [$e addTechVia [V {VIA89}]]
$e newPath $jd561 FIXED [RL M8]
$e addPoint 2883800 132660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2883800 132740
set jd562 [$e addTechVia [V VIA67]]
$e newPath $jd562 FIXED
$e addPoint 2883880 132740
set jd563 [$e addTechVia [V VIA56]]
$e newPath $jd563 FIXED
$e addPoint 2883880 132836
set jd564 [$e addTechVia [V VIA45]]
$e newPath $jd564 FIXED
$e addPoint 2883784 132836
set jd565 [$e addTechVia [V VIA34]]
$e newPath $jd565 FIXED
$e addPoint 2883784 132660
set jd566 [$e addTechVia [V VIA23]]
$e newPath $jd566 FIXED
$e addPoint 2883897 132660
set jd567 [$e addTechVia [V VIA12]]
$e newPath $jd567 FIXED
$e addITerm [IT M5_0 Y]
$e newPath $emj230 FIXED [RL M9]
set jd568 [$e addTechVia [V {VIA89}]]
$e newPath $jd568 FIXED [RL M8]
$e addPoint 2831960 428940
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2831960 429020
set jd569 [$e addTechVia [V VIA67]]
$e newPath $jd569 FIXED
$e addPoint 2832040 429020
set jd570 [$e addTechVia [V VIA56]]
$e newPath $jd570 FIXED
$e addPoint 2832040 429116
set jd571 [$e addTechVia [V VIA45]]
$e newPath $jd571 FIXED
$e addPoint 2831944 429116
set jd572 [$e addTechVia [V VIA34]]
$e newPath $jd572 FIXED
$e addPoint 2831944 428940
set jd573 [$e addTechVia [V VIA23]]
$e newPath $jd573 FIXED
$e addPoint 2832111 428940
set jd574 [$e addTechVia [V VIA12]]
$e newPath $jd574 FIXED
$e addITerm [IT M5_1 Y]
$e newPath $emj334 FIXED [RL M9]
set jd575 [$e addTechVia [V {VIA89}]]
$e newPath $jd575 FIXED [RL M8]
$e addPoint 2823320 672660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2823320 672740
set jd576 [$e addTechVia [V VIA67]]
$e newPath $jd576 FIXED
$e addPoint 2823400 672740
set jd577 [$e addTechVia [V VIA56]]
$e newPath $jd577 FIXED
$e addPoint 2823400 672836
set jd578 [$e addTechVia [V VIA45]]
$e newPath $jd578 FIXED
$e addPoint 2823853 672836
set jd579 [$e addTechVia [V VIA34]]
$e newPath $jd579 FIXED
$e addPoint 2823853 672660
set jd580 [$e addTechVia [V VIA23]]
$e newPath $jd580 FIXED
$e addPoint 2823903 672660
set jd581 [$e addTechVia [V VIA12]]
$e newPath $jd581 FIXED
$e addITerm [IT M5_2 Y]
$e newPath $emj384 FIXED [RL M9]
set jd582 [$e addTechVia [V {VIA89}]]
$e newPath $jd582 FIXED [RL M8]
$e addPoint 2822920 930060
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2822920 930140
set jd583 [$e addTechVia [V VIA67]]
$e newPath $jd583 FIXED
$e addPoint 2822840 930140
set jd584 [$e addTechVia [V VIA56]]
$e newPath $jd584 FIXED
$e addPoint 2822840 930236
set jd585 [$e addTechVia [V VIA45]]
$e newPath $jd585 FIXED
$e addPoint 2822549 930236
set jd586 [$e addTechVia [V VIA34]]
$e newPath $jd586 FIXED
$e addPoint 2822549 930060
set jd587 [$e addTechVia [V VIA23]]
$e newPath $jd587 FIXED
$e addPoint 2822499 930060
set jd588 [$e addTechVia [V VIA12]]
$e newPath $jd588 FIXED
$e addITerm [IT M5_3 Y]
$e newPath $emj413 FIXED [RL M9]
set jd589 [$e addTechVia [V {VIA89}]]
$e newPath $jd589 FIXED [RL M8]
$e addPoint 2823320 1212660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2823320 1212740
set jd590 [$e addTechVia [V VIA67]]
$e newPath $jd590 FIXED
$e addPoint 2823400 1212740
set jd591 [$e addTechVia [V VIA56]]
$e newPath $jd591 FIXED
$e addPoint 2823400 1212836
set jd592 [$e addTechVia [V VIA45]]
$e newPath $jd592 FIXED
$e addPoint 2823853 1212836
set jd593 [$e addTechVia [V VIA34]]
$e newPath $jd593 FIXED
$e addPoint 2823853 1212660
set jd594 [$e addTechVia [V VIA23]]
$e newPath $jd594 FIXED
$e addPoint 2823903 1212660
set jd595 [$e addTechVia [V VIA12]]
$e newPath $jd595 FIXED
$e addITerm [IT M5_4 Y]
$e newPath $emj610 FIXED [RL M9]
set jd596 [$e addTechVia [V {VIA89}]]
$e newPath $jd596 FIXED [RL M8]
$e addPoint 2809960 1324980
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2809960 1325060
set jd597 [$e addTechVia [V VIA67]]
$e newPath $jd597 FIXED
$e addPoint 2809880 1325060
set jd598 [$e addTechVia [V VIA56]]
$e newPath $jd598 FIXED
$e addPoint 2809880 1325156
set jd599 [$e addTechVia [V VIA45]]
$e newPath $jd599 FIXED
$e addPoint 2809784 1325156
set jd600 [$e addTechVia [V VIA34]]
$e newPath $jd600 FIXED
$e addPoint 2809784 1324980
set jd601 [$e addTechVia [V VIA23]]
$e newPath $jd601 FIXED
$e addPoint 2809971 1324980
set jd602 [$e addTechVia [V VIA12]]
$e newPath $jd602 FIXED
$e addITerm [IT M5_5 Y]
$e newPath $emj877 FIXED [RL M9]
set jd603 [$e addTechVia [V {VIA89}]]
$e newPath $jd603 FIXED [RL M8]
$e addPoint 3194440 1752660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3194440 1752740
set jd604 [$e addTechVia [V VIA67]]
$e newPath $jd604 FIXED
$e addPoint 3194360 1752740
set jd605 [$e addTechVia [V VIA56]]
$e newPath $jd605 FIXED
$e addPoint 3194360 1752836
set jd606 [$e addTechVia [V VIA45]]
$e newPath $jd606 FIXED
$e addPoint 3193961 1752836
set jd607 [$e addTechVia [V VIA34]]
$e newPath $jd607 FIXED
$e addPoint 3193961 1752660
set jd608 [$e addTechVia [V VIA23]]
$e newPath $jd608 FIXED
$e addPoint 3193911 1752660
set jd609 [$e addTechVia [V VIA12]]
$e newPath $jd609 FIXED
$e addITerm [IT M5_6 Y]
$e newPath $emj880 FIXED [RL M9]
set jd610 [$e addTechVia [V {VIA89}]]
$e newPath $jd610 FIXED [RL M8]
$e addPoint 3194440 2027340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3194440 2027420
set jd611 [$e addTechVia [V VIA67]]
$e newPath $jd611 FIXED
$e addPoint 3194360 2027420
set jd612 [$e addTechVia [V VIA56]]
$e newPath $jd612 FIXED
$e addPoint 3194360 2027516
set jd613 [$e addTechVia [V VIA45]]
$e newPath $jd613 FIXED
$e addPoint 3193961 2027516
set jd614 [$e addTechVia [V VIA34]]
$e newPath $jd614 FIXED
$e addPoint 3193961 2027340
set jd615 [$e addTechVia [V VIA23]]
$e newPath $jd615 FIXED
$e addPoint 3193911 2027340
set jd616 [$e addTechVia [V VIA12]]
$e newPath $jd616 FIXED
$e addITerm [IT M5_7 Y]
$e newPath $emj1108 FIXED [RL M9]
set jd617 [$e addTechVia [V {VIA89}]]
$e newPath $jd617 FIXED [RL M8]
$e addPoint 3194440 2292660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3194440 2292740
set jd618 [$e addTechVia [V VIA67]]
$e newPath $jd618 FIXED
$e addPoint 3194360 2292740
set jd619 [$e addTechVia [V VIA56]]
$e newPath $jd619 FIXED
$e addPoint 3194360 2292836
set jd620 [$e addTechVia [V VIA45]]
$e newPath $jd620 FIXED
$e addPoint 3193961 2292836
set jd621 [$e addTechVia [V VIA34]]
$e newPath $jd621 FIXED
$e addPoint 3193961 2292660
set jd622 [$e addTechVia [V VIA23]]
$e newPath $jd622 FIXED
$e addPoint 3193911 2292660
set jd623 [$e addTechVia [V VIA12]]
$e newPath $jd623 FIXED
$e addITerm [IT M5_8 Y]
$e newPath $emj1238 FIXED [RL M9]
set jd624 [$e addTechVia [V {VIA89}]]
$e newPath $jd624 FIXED [RL M8]
$e addPoint 3194440 2567340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3194440 2567420
set jd625 [$e addTechVia [V VIA67]]
$e newPath $jd625 FIXED
$e addPoint 3194360 2567420
set jd626 [$e addTechVia [V VIA56]]
$e newPath $jd626 FIXED
$e addPoint 3194360 2567516
set jd627 [$e addTechVia [V VIA45]]
$e newPath $jd627 FIXED
$e addPoint 3193961 2567516
set jd628 [$e addTechVia [V VIA34]]
$e newPath $jd628 FIXED
$e addPoint 3193961 2567340
set jd629 [$e addTechVia [V VIA23]]
$e newPath $jd629 FIXED
$e addPoint 3193911 2567340
set jd630 [$e addTechVia [V VIA12]]
$e newPath $jd630 FIXED
$e addITerm [IT M5_9 Y]
$e newPath $emj1374 FIXED [RL M9]
set jd631 [$e addTechVia [V {VIA89}]]
$e newPath $jd631 FIXED [RL M8]
$e addPoint 2801320 2970900
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2801320 2970980
set jd632 [$e addTechVia [V VIA67]]
$e newPath $jd632 FIXED
$e addPoint 2801240 2970980
set jd633 [$e addTechVia [V VIA56]]
$e newPath $jd633 FIXED
$e addPoint 2801240 2971076
set jd634 [$e addTechVia [V VIA45]]
$e newPath $jd634 FIXED
$e addPoint 2799977 2971076
set jd635 [$e addTechVia [V VIA34]]
$e newPath $jd635 FIXED
$e addPoint 2799977 2970900
set jd636 [$e addTechVia [V VIA23]]
$e newPath $jd636 FIXED
$e addPoint 2799927 2970900
set jd637 [$e addTechVia [V VIA12]]
$e newPath $jd637 FIXED
$e addITerm [IT M5_10 Y]
$e newPath $emj1512 FIXED [RL M9]
set jd638 [$e addTechVia [V {VIA89}]]
$e newPath $jd638 FIXED [RL M8]
$e addPoint 2805640 3109140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2805640 3109220
set jd639 [$e addTechVia [V VIA67]]
$e newPath $jd639 FIXED
$e addPoint 2805560 3109220
set jd640 [$e addTechVia [V VIA56]]
$e newPath $jd640 FIXED
$e addPoint 2805560 3109316
set jd641 [$e addTechVia [V VIA45]]
$e newPath $jd641 FIXED
$e addPoint 2804621 3109316
set jd642 [$e addTechVia [V VIA34]]
$e newPath $jd642 FIXED
$e addPoint 2804621 3109140
set jd643 [$e addTechVia [V VIA23]]
$e newPath $jd643 FIXED
$e addPoint 2804571 3109140
set jd644 [$e addTechVia [V VIA12]]
$e newPath $jd644 FIXED
$e addITerm [IT M5_11 Y]
$e newPath $emj1447 FIXED [RL M9]
set jd645 [$e addTechVia [V {VIA89}]]
$e newPath $jd645 FIXED [RL M8]
$e addPoint 2823320 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2823320 3372740
set jd646 [$e addTechVia [V VIA67]]
$e newPath $jd646 FIXED
$e addPoint 2823400 3372740
set jd647 [$e addTechVia [V VIA56]]
$e newPath $jd647 FIXED
$e addPoint 2823400 3372836
set jd648 [$e addTechVia [V VIA45]]
$e newPath $jd648 FIXED
$e addPoint 2823853 3372836
set jd649 [$e addTechVia [V VIA34]]
$e newPath $jd649 FIXED
$e addPoint 2823853 3372660
set jd650 [$e addTechVia [V VIA23]]
$e newPath $jd650 FIXED
$e addPoint 2823903 3372660
set jd651 [$e addTechVia [V VIA12]]
$e newPath $jd651 FIXED
$e addITerm [IT M5_12 Y]
$e newPath $emj1692 FIXED [RL M9]
set jd652 [$e addTechVia [V {VIA89}]]
$e newPath $jd652 FIXED [RL M8]
$e addPoint 2823320 3647340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2823320 3647420
set jd653 [$e addTechVia [V VIA67]]
$e newPath $jd653 FIXED
$e addPoint 2823400 3647420
set jd654 [$e addTechVia [V VIA56]]
$e newPath $jd654 FIXED
$e addPoint 2823400 3647516
set jd655 [$e addTechVia [V VIA45]]
$e newPath $jd655 FIXED
$e addPoint 2823853 3647516
set jd656 [$e addTechVia [V VIA34]]
$e newPath $jd656 FIXED
$e addPoint 2823853 3647340
set jd657 [$e addTechVia [V VIA23]]
$e newPath $jd657 FIXED
$e addPoint 2823903 3647340
set jd658 [$e addTechVia [V VIA12]]
$e newPath $jd658 FIXED
$e addITerm [IT M5_13 Y]
$e newPath $emj2019 FIXED [RL M9]
set jd659 [$e addTechVia [V {VIA89}]]
$e newPath $jd659 FIXED [RL M8]
$e addPoint 2887720 3912660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2887720 3912740
set jd660 [$e addTechVia [V VIA67]]
$e newPath $jd660 FIXED
$e addPoint 2887640 3912740
set jd661 [$e addTechVia [V VIA56]]
$e newPath $jd661 FIXED
$e addPoint 2887640 3912836
set jd662 [$e addTechVia [V VIA45]]
$e newPath $jd662 FIXED
$e addPoint 2887843 3912836
set jd663 [$e addTechVia [V VIA34]]
$e newPath $jd663 FIXED
$e addPoint 2887843 3912660
set jd664 [$e addTechVia [V VIA23]]
$e newPath $jd664 FIXED
$e addPoint 2887893 3912660
set jd665 [$e addTechVia [V VIA12]]
$e newPath $jd665 FIXED
$e addITerm [IT M5_14 Y]
$e newPath $emj2066 FIXED [RL M9]
set jd666 [$e addTechVia [V {VIA89}]]
$e newPath $jd666 FIXED [RL M8]
$e addPoint 2887720 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2887720 4187420
set jd667 [$e addTechVia [V VIA67]]
$e newPath $jd667 FIXED
$e addPoint 2887640 4187420
set jd668 [$e addTechVia [V VIA56]]
$e newPath $jd668 FIXED
$e addPoint 2887640 4187516
set jd669 [$e addTechVia [V VIA45]]
$e newPath $jd669 FIXED
$e addPoint 2887843 4187516
set jd670 [$e addTechVia [V VIA34]]
$e newPath $jd670 FIXED
$e addPoint 2887843 4187340
set jd671 [$e addTechVia [V VIA23]]
$e newPath $jd671 FIXED
$e addPoint 2887893 4187340
set jd672 [$e addTechVia [V VIA12]]
$e newPath $jd672 FIXED
$e addITerm [IT M5_15 Y]
$e newPath $emj400 FIXED [RL M9]
set jd673 [$e addTechVia [V {VIA89}]]
$e newPath $jd673 FIXED [RL M8]
$e addPoint 3332680 109260
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3332680 109340
set jd674 [$e addTechVia [V VIA67]]
$e newPath $jd674 FIXED
$e addPoint 3332600 109340
set jd675 [$e addTechVia [V VIA56]]
$e newPath $jd675 FIXED
$e addPoint 3332600 109436
set jd676 [$e addTechVia [V VIA45]]
$e newPath $jd676 FIXED
$e addPoint 3330797 109436
set jd677 [$e addTechVia [V VIA34]]
$e newPath $jd677 FIXED
$e addPoint 3330797 109260
set jd678 [$e addTechVia [V VIA23]]
$e newPath $jd678 FIXED
$e addPoint 3330747 109260
set jd679 [$e addTechVia [V VIA12]]
$e newPath $jd679 FIXED
$e addITerm [IT M6_0 Y]
$e newPath $emj288 FIXED [RL M9]
set jd680 [$e addTechVia [V {VIA89}]]
$e newPath $jd680 FIXED [RL M8]
$e addPoint 3341320 409140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3341320 409220
set jd681 [$e addTechVia [V VIA67]]
$e newPath $jd681 FIXED
$e addPoint 3341240 409220
set jd682 [$e addTechVia [V VIA56]]
$e newPath $jd682 FIXED
$e addPoint 3341240 409316
set jd683 [$e addTechVia [V VIA45]]
$e newPath $jd683 FIXED
$e addPoint 3341057 409316
set jd684 [$e addTechVia [V VIA34]]
$e newPath $jd684 FIXED
$e addPoint 3341057 409140
set jd685 [$e addTechVia [V VIA23]]
$e newPath $jd685 FIXED
$e addPoint 3341007 409140
set jd686 [$e addTechVia [V VIA12]]
$e newPath $jd686 FIXED
$e addITerm [IT M6_1 Y]
$e newPath $emj405 FIXED [RL M9]
set jd687 [$e addTechVia [V {VIA89}]]
$e newPath $jd687 FIXED [RL M8]
$e addPoint 3337400 672660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337400 672740
set jd688 [$e addTechVia [V VIA67]]
$e newPath $jd688 FIXED
$e addPoint 3337480 672740
set jd689 [$e addTechVia [V VIA56]]
$e newPath $jd689 FIXED
$e addPoint 3337480 672836
set jd690 [$e addTechVia [V VIA45]]
$e newPath $jd690 FIXED
$e addPoint 3337933 672836
set jd691 [$e addTechVia [V VIA34]]
$e newPath $jd691 FIXED
$e addPoint 3337933 672660
set jd692 [$e addTechVia [V VIA23]]
$e newPath $jd692 FIXED
$e addPoint 3337983 672660
set jd693 [$e addTechVia [V VIA12]]
$e newPath $jd693 FIXED
$e addITerm [IT M6_2 Y]
$e newPath $emj521 FIXED [RL M9]
set jd694 [$e addTechVia [V {VIA89}]]
$e newPath $jd694 FIXED [RL M8]
$e addPoint 3289480 949140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3289480 949220
set jd695 [$e addTechVia [V VIA67]]
$e newPath $jd695 FIXED
$e addPoint 3289400 949220
set jd696 [$e addTechVia [V VIA56]]
$e newPath $jd696 FIXED
$e addPoint 3289400 949316
set jd697 [$e addTechVia [V VIA45]]
$e newPath $jd697 FIXED
$e addPoint 3288245 949316
set jd698 [$e addTechVia [V VIA34]]
$e newPath $jd698 FIXED
$e addPoint 3288245 949140
set jd699 [$e addTechVia [V VIA23]]
$e newPath $jd699 FIXED
$e addPoint 3288195 949140
set jd700 [$e addTechVia [V VIA12]]
$e newPath $jd700 FIXED
$e addITerm [IT M6_3 Y]
$e newPath $emj458 FIXED [RL M9]
set jd701 [$e addTechVia [V {VIA89}]]
$e newPath $jd701 FIXED [RL M8]
$e addPoint 3341720 1246680
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3341720 1246760
set jd702 [$e addTechVia [V VIA67]]
$e newPath $jd702 FIXED
$e addPoint 3341800 1246760
set jd703 [$e addTechVia [V VIA56]]
$e newPath $jd703 FIXED
$e addPoint 3341800 1246856
set jd704 [$e addTechVia [V VIA45]]
$e newPath $jd704 FIXED
$e addPoint 3343495 1246856
set jd705 [$e addTechVia [V VIA34]]
$e newPath $jd705 FIXED
$e addPoint 3343495 1246680
set jd706 [$e addTechVia [V VIA23]]
$e newPath $jd706 FIXED
$e addPoint 3343545 1246680
set jd707 [$e addTechVia [V VIA12]]
$e newPath $jd707 FIXED
$e addITerm [IT M6_4 Y]
$e newPath $emj607 FIXED [RL M9]
set jd708 [$e addTechVia [V {VIA89}]]
$e newPath $jd708 FIXED [RL M8]
$e addPoint 3337400 1487340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337400 1487420
set jd709 [$e addTechVia [V VIA67]]
$e newPath $jd709 FIXED
$e addPoint 3337480 1487420
set jd710 [$e addTechVia [V VIA56]]
$e newPath $jd710 FIXED
$e addPoint 3337480 1487516
set jd711 [$e addTechVia [V VIA45]]
$e newPath $jd711 FIXED
$e addPoint 3337933 1487516
set jd712 [$e addTechVia [V VIA34]]
$e newPath $jd712 FIXED
$e addPoint 3337933 1487340
set jd713 [$e addTechVia [V VIA23]]
$e newPath $jd713 FIXED
$e addPoint 3337983 1487340
set jd714 [$e addTechVia [V VIA12]]
$e newPath $jd714 FIXED
$e addITerm [IT M6_5 Y]
$e newPath $emj1026 FIXED [RL M9]
set jd715 [$e addTechVia [V {VIA89}]]
$e newPath $jd715 FIXED [RL M8]
$e addPoint 3289480 1759500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3289480 1759580
set jd716 [$e addTechVia [V VIA67]]
$e newPath $jd716 FIXED
$e addPoint 3289400 1759580
set jd717 [$e addTechVia [V VIA56]]
$e newPath $jd717 FIXED
$e addPoint 3289400 1759676
set jd718 [$e addTechVia [V VIA45]]
$e newPath $jd718 FIXED
$e addPoint 3288245 1759676
set jd719 [$e addTechVia [V VIA34]]
$e newPath $jd719 FIXED
$e addPoint 3288245 1759500
set jd720 [$e addTechVia [V VIA23]]
$e newPath $jd720 FIXED
$e addPoint 3288195 1759500
set jd721 [$e addTechVia [V VIA12]]
$e newPath $jd721 FIXED
$e addITerm [IT M6_6 Y]
$e newPath $emj948 FIXED [RL M9]
set jd722 [$e addTechVia [V {VIA89}]]
$e newPath $jd722 FIXED [RL M8]
$e addPoint 3337400 2027340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337400 2027420
set jd723 [$e addTechVia [V VIA67]]
$e newPath $jd723 FIXED
$e addPoint 3337480 2027420
set jd724 [$e addTechVia [V VIA56]]
$e newPath $jd724 FIXED
$e addPoint 3337480 2027516
set jd725 [$e addTechVia [V VIA45]]
$e newPath $jd725 FIXED
$e addPoint 3337933 2027516
set jd726 [$e addTechVia [V VIA34]]
$e newPath $jd726 FIXED
$e addPoint 3337933 2027340
set jd727 [$e addTechVia [V VIA23]]
$e newPath $jd727 FIXED
$e addPoint 3337983 2027340
set jd728 [$e addTechVia [V VIA12]]
$e newPath $jd728 FIXED
$e addITerm [IT M6_7 Y]
$e newPath $emj1308 FIXED [RL M9]
set jd729 [$e addTechVia [V {VIA89}]]
$e newPath $jd729 FIXED [RL M8]
$e addPoint 3324440 2249460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3324440 2249540
set jd730 [$e addTechVia [V VIA67]]
$e newPath $jd730 FIXED
$e addPoint 3324520 2249540
set jd731 [$e addTechVia [V VIA56]]
$e newPath $jd731 FIXED
$e addPoint 3324520 2249636
set jd732 [$e addTechVia [V VIA45]]
$e newPath $jd732 FIXED
$e addPoint 3326053 2249636
set jd733 [$e addTechVia [V VIA34]]
$e newPath $jd733 FIXED
$e addPoint 3326053 2249460
set jd734 [$e addTechVia [V VIA23]]
$e newPath $jd734 FIXED
$e addPoint 3326103 2249460
set jd735 [$e addTechVia [V VIA12]]
$e newPath $jd735 FIXED
$e addITerm [IT M6_8 Y]
$e newPath $emj1569 FIXED [RL M9]
set jd736 [$e addTechVia [V {VIA89}]]
$e newPath $jd736 FIXED [RL M8]
$e addPoint 3289480 2569140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3289480 2569220
set jd737 [$e addTechVia [V VIA67]]
$e newPath $jd737 FIXED
$e addPoint 3289400 2569220
set jd738 [$e addTechVia [V VIA56]]
$e newPath $jd738 FIXED
$e addPoint 3289400 2569316
set jd739 [$e addTechVia [V VIA45]]
$e newPath $jd739 FIXED
$e addPoint 3288245 2569316
set jd740 [$e addTechVia [V VIA34]]
$e newPath $jd740 FIXED
$e addPoint 3288245 2569140
set jd741 [$e addTechVia [V VIA23]]
$e newPath $jd741 FIXED
$e addPoint 3288195 2569140
set jd742 [$e addTechVia [V VIA12]]
$e newPath $jd742 FIXED
$e addITerm [IT M6_9 Y]
$e newPath $emj1506 FIXED [RL M9]
set jd743 [$e addTechVia [V {VIA89}]]
$e newPath $jd743 FIXED [RL M8]
$e addPoint 3337400 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337400 2832740
set jd744 [$e addTechVia [V VIA67]]
$e newPath $jd744 FIXED
$e addPoint 3337480 2832740
set jd745 [$e addTechVia [V VIA56]]
$e newPath $jd745 FIXED
$e addPoint 3337480 2832836
set jd746 [$e addTechVia [V VIA45]]
$e newPath $jd746 FIXED
$e addPoint 3337933 2832836
set jd747 [$e addTechVia [V VIA34]]
$e newPath $jd747 FIXED
$e addPoint 3337933 2832660
set jd748 [$e addTechVia [V VIA23]]
$e newPath $jd748 FIXED
$e addPoint 3337983 2832660
set jd749 [$e addTechVia [V VIA12]]
$e newPath $jd749 FIXED
$e addITerm [IT M6_10 Y]
$e newPath $emj1639 FIXED [RL M9]
set jd750 [$e addTechVia [V {VIA89}]]
$e newPath $jd750 FIXED [RL M8]
$e addPoint 3289480 3109140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3289480 3109220
set jd751 [$e addTechVia [V VIA67]]
$e newPath $jd751 FIXED
$e addPoint 3289400 3109220
set jd752 [$e addTechVia [V VIA56]]
$e newPath $jd752 FIXED
$e addPoint 3289400 3109316
set jd753 [$e addTechVia [V VIA45]]
$e newPath $jd753 FIXED
$e addPoint 3288245 3109316
set jd754 [$e addTechVia [V VIA34]]
$e newPath $jd754 FIXED
$e addPoint 3288245 3109140
set jd755 [$e addTechVia [V VIA23]]
$e newPath $jd755 FIXED
$e addPoint 3288195 3109140
set jd756 [$e addTechVia [V VIA12]]
$e newPath $jd756 FIXED
$e addITerm [IT M6_11 Y]
$e newPath $emj1742 FIXED [RL M9]
set jd757 [$e addTechVia [V {VIA89}]]
$e newPath $jd757 FIXED [RL M8]
$e addPoint 3337400 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337400 3372740
set jd758 [$e addTechVia [V VIA67]]
$e newPath $jd758 FIXED
$e addPoint 3337480 3372740
set jd759 [$e addTechVia [V VIA56]]
$e newPath $jd759 FIXED
$e addPoint 3337480 3372836
set jd760 [$e addTechVia [V VIA45]]
$e newPath $jd760 FIXED
$e addPoint 3337933 3372836
set jd761 [$e addTechVia [V VIA34]]
$e newPath $jd761 FIXED
$e addPoint 3337933 3372660
set jd762 [$e addTechVia [V VIA23]]
$e newPath $jd762 FIXED
$e addPoint 3337983 3372660
set jd763 [$e addTechVia [V VIA12]]
$e newPath $jd763 FIXED
$e addITerm [IT M6_12 Y]
$e newPath $emj2016 FIXED [RL M9]
set jd764 [$e addTechVia [V {VIA89}]]
$e newPath $jd764 FIXED [RL M8]
$e addPoint 3298120 3652380
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3298120 3652460
set jd765 [$e addTechVia [V VIA67]]
$e newPath $jd765 FIXED
$e addPoint 3298040 3652460
set jd766 [$e addTechVia [V VIA56]]
$e newPath $jd766 FIXED
$e addPoint 3298040 3652556
set jd767 [$e addTechVia [V VIA45]]
$e newPath $jd767 FIXED
$e addPoint 3296669 3652556
set jd768 [$e addTechVia [V VIA34]]
$e newPath $jd768 FIXED
$e addPoint 3296669 3652380
set jd769 [$e addTechVia [V VIA23]]
$e newPath $jd769 FIXED
$e addPoint 3296619 3652380
set jd770 [$e addTechVia [V VIA12]]
$e newPath $jd770 FIXED
$e addITerm [IT M6_13 Y]
$e newPath $emj2014 FIXED [RL M9]
set jd771 [$e addTechVia [V {VIA89}]]
$e newPath $jd771 FIXED [RL M8]
$e addPoint 3337400 3912660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337400 3912740
set jd772 [$e addTechVia [V VIA67]]
$e newPath $jd772 FIXED
$e addPoint 3337480 3912740
set jd773 [$e addTechVia [V VIA56]]
$e newPath $jd773 FIXED
$e addPoint 3337480 3912836
set jd774 [$e addTechVia [V VIA45]]
$e newPath $jd774 FIXED
$e addPoint 3337933 3912836
set jd775 [$e addTechVia [V VIA34]]
$e newPath $jd775 FIXED
$e addPoint 3337933 3912660
set jd776 [$e addTechVia [V VIA23]]
$e newPath $jd776 FIXED
$e addPoint 3337983 3912660
set jd777 [$e addTechVia [V VIA12]]
$e newPath $jd777 FIXED
$e addITerm [IT M6_14 Y]
$e newPath $emj2222 FIXED [RL M9]
set jd778 [$e addTechVia [V {VIA89}]]
$e newPath $jd778 FIXED [RL M8]
$e addPoint 3337400 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337400 4187420
set jd779 [$e addTechVia [V VIA67]]
$e newPath $jd779 FIXED
$e addPoint 3337480 4187420
set jd780 [$e addTechVia [V VIA56]]
$e newPath $jd780 FIXED
$e addPoint 3337480 4187516
set jd781 [$e addTechVia [V VIA45]]
$e newPath $jd781 FIXED
$e addPoint 3337933 4187516
set jd782 [$e addTechVia [V VIA34]]
$e newPath $jd782 FIXED
$e addPoint 3337933 4187340
set jd783 [$e addTechVia [V VIA23]]
$e newPath $jd783 FIXED
$e addPoint 3337983 4187340
set jd784 [$e addTechVia [V VIA12]]
$e newPath $jd784 FIXED
$e addITerm [IT M6_15 Y]
$e newPath $emj453 FIXED [RL M9]
set jd785 [$e addTechVia [V {VIA89}]]
$e newPath $jd785 FIXED [RL M8]
$e addPoint 3851480 132660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3851480 132740
set jd786 [$e addTechVia [V VIA67]]
$e newPath $jd786 FIXED
$e addPoint 3851560 132740
set jd787 [$e addTechVia [V VIA56]]
$e newPath $jd787 FIXED
$e addPoint 3851560 132836
set jd788 [$e addTechVia [V VIA45]]
$e newPath $jd788 FIXED
$e addPoint 3852013 132836
set jd789 [$e addTechVia [V VIA34]]
$e newPath $jd789 FIXED
$e addPoint 3852013 132660
set jd790 [$e addTechVia [V VIA23]]
$e newPath $jd790 FIXED
$e addPoint 3852063 132660
set jd791 [$e addTechVia [V VIA12]]
$e newPath $jd791 FIXED
$e addITerm [IT M7_0 Y]
$e newPath $emj324 FIXED [RL M9]
set jd792 [$e addTechVia [V {VIA89}]]
$e newPath $jd792 FIXED [RL M8]
$e addPoint 3833800 409140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3833800 409220
set jd793 [$e addTechVia [V VIA67]]
$e newPath $jd793 FIXED
$e addPoint 3833720 409220
set jd794 [$e addTechVia [V VIA56]]
$e newPath $jd794 FIXED
$e addPoint 3833720 409316
set jd795 [$e addTechVia [V VIA45]]
$e newPath $jd795 FIXED
$e addPoint 3832781 409316
set jd796 [$e addTechVia [V VIA34]]
$e newPath $jd796 FIXED
$e addPoint 3832781 409140
set jd797 [$e addTechVia [V VIA23]]
$e newPath $jd797 FIXED
$e addPoint 3832731 409140
set jd798 [$e addTechVia [V VIA12]]
$e newPath $jd798 FIXED
$e addITerm [IT M7_1 Y]
$e newPath $emj626 FIXED [RL M9]
set jd799 [$e addTechVia [V {VIA89}]]
$e newPath $jd799 FIXED [RL M8]
$e addPoint 3855400 679500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3855400 679580
set jd800 [$e addTechVia [V VIA67]]
$e newPath $jd800 FIXED
$e addPoint 3855320 679580
set jd801 [$e addTechVia [V VIA56]]
$e newPath $jd801 FIXED
$e addPoint 3855320 679676
set jd802 [$e addTechVia [V VIA45]]
$e newPath $jd802 FIXED
$e addPoint 3854705 679676
set jd803 [$e addTechVia [V VIA34]]
$e newPath $jd803 FIXED
$e addPoint 3854705 679500
set jd804 [$e addTechVia [V VIA23]]
$e newPath $jd804 FIXED
$e addPoint 3854655 679500
set jd805 [$e addTechVia [V VIA12]]
$e newPath $jd805 FIXED
$e addITerm [IT M7_2 Y]
$e newPath $emj687 FIXED [RL M9]
set jd806 [$e addTechVia [V {VIA89}]]
$e newPath $jd806 FIXED [RL M8]
$e addPoint 3920200 947340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3920200 947420
set jd807 [$e addTechVia [V VIA67]]
$e newPath $jd807 FIXED
$e addPoint 3920120 947420
set jd808 [$e addTechVia [V VIA56]]
$e newPath $jd808 FIXED
$e addPoint 3920120 947516
set jd809 [$e addTechVia [V VIA45]]
$e newPath $jd809 FIXED
$e addPoint 3920216 947516
set jd810 [$e addTechVia [V VIA34]]
$e newPath $jd810 FIXED
$e addPoint 3920216 947340
set jd811 [$e addTechVia [V VIA23]]
$e newPath $jd811 FIXED
$e addPoint 3920049 947340
set jd812 [$e addTechVia [V VIA12]]
$e newPath $jd812 FIXED
$e addITerm [IT M7_3 Y]
$e newPath $emj552 FIXED [RL M9]
set jd813 [$e addTechVia [V {VIA89}]]
$e newPath $jd813 FIXED [RL M8]
$e addPoint 3920200 1176300
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3920200 1176380
set jd814 [$e addTechVia [V VIA67]]
$e newPath $jd814 FIXED
$e addPoint 3920120 1176380
set jd815 [$e addTechVia [V VIA56]]
$e newPath $jd815 FIXED
$e addPoint 3920120 1176476
set jd816 [$e addTechVia [V VIA45]]
$e newPath $jd816 FIXED
$e addPoint 3919667 1176476
set jd817 [$e addTechVia [V VIA34]]
$e newPath $jd817 FIXED
$e addPoint 3919667 1176300
set jd818 [$e addTechVia [V VIA23]]
$e newPath $jd818 FIXED
$e addPoint 3919617 1176300
set jd819 [$e addTechVia [V VIA12]]
$e newPath $jd819 FIXED
$e addITerm [IT M7_4 Y]
$e newPath $emj604 FIXED [RL M9]
set jd820 [$e addTechVia [V {VIA89}]]
$e newPath $jd820 FIXED [RL M8]
$e addPoint 3851480 1487340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3851480 1487420
set jd821 [$e addTechVia [V VIA67]]
$e newPath $jd821 FIXED
$e addPoint 3851560 1487420
set jd822 [$e addTechVia [V VIA56]]
$e newPath $jd822 FIXED
$e addPoint 3851560 1487516
set jd823 [$e addTechVia [V VIA45]]
$e newPath $jd823 FIXED
$e addPoint 3852013 1487516
set jd824 [$e addTechVia [V VIA34]]
$e newPath $jd824 FIXED
$e addPoint 3852013 1487340
set jd825 [$e addTechVia [V VIA23]]
$e newPath $jd825 FIXED
$e addPoint 3852063 1487340
set jd826 [$e addTechVia [V VIA12]]
$e newPath $jd826 FIXED
$e addITerm [IT M7_5 Y]
$e newPath $emj1021 FIXED [RL M9]
set jd827 [$e addTechVia [V {VIA89}]]
$e newPath $jd827 FIXED [RL M8]
$e addPoint 3920200 1752660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3920200 1752740
set jd828 [$e addTechVia [V VIA67]]
$e newPath $jd828 FIXED
$e addPoint 3920120 1752740
set jd829 [$e addTechVia [V VIA56]]
$e newPath $jd829 FIXED
$e addPoint 3920120 1752836
set jd830 [$e addTechVia [V VIA45]]
$e newPath $jd830 FIXED
$e addPoint 3920216 1752836
set jd831 [$e addTechVia [V VIA34]]
$e newPath $jd831 FIXED
$e addPoint 3920216 1752660
set jd832 [$e addTechVia [V VIA23]]
$e newPath $jd832 FIXED
$e addPoint 3920049 1752660
set jd833 [$e addTechVia [V VIA12]]
$e newPath $jd833 FIXED
$e addITerm [IT M7_6 Y]
$e newPath $emj1099 FIXED [RL M9]
set jd834 [$e addTechVia [V {VIA89}]]
$e newPath $jd834 FIXED [RL M8]
$e addPoint 3864040 2070540
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3864040 2070620
set jd835 [$e addTechVia [V VIA67]]
$e newPath $jd835 FIXED
$e addPoint 3863960 2070620
set jd836 [$e addTechVia [V VIA56]]
$e newPath $jd836 FIXED
$e addPoint 3863960 2070716
set jd837 [$e addTechVia [V VIA45]]
$e newPath $jd837 FIXED
$e addPoint 3864056 2070716
set jd838 [$e addTechVia [V VIA34]]
$e newPath $jd838 FIXED
$e addPoint 3864056 2070540
set jd839 [$e addTechVia [V VIA23]]
$e newPath $jd839 FIXED
$e addPoint 3863943 2070540
set jd840 [$e addTechVia [V VIA12]]
$e newPath $jd840 FIXED
$e addITerm [IT M7_7 Y]
$e newPath $emj1428 FIXED [RL M9]
set jd841 [$e addTechVia [V {VIA89}]]
$e newPath $jd841 FIXED [RL M8]
$e addPoint 3838520 2249460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3838520 2249540
set jd842 [$e addTechVia [V VIA67]]
$e newPath $jd842 FIXED
$e addPoint 3838600 2249540
set jd843 [$e addTechVia [V VIA56]]
$e newPath $jd843 FIXED
$e addPoint 3838600 2249636
set jd844 [$e addTechVia [V VIA45]]
$e newPath $jd844 FIXED
$e addPoint 3840133 2249636
set jd845 [$e addTechVia [V VIA34]]
$e newPath $jd845 FIXED
$e addPoint 3840133 2249460
set jd846 [$e addTechVia [V VIA23]]
$e newPath $jd846 FIXED
$e addPoint 3840183 2249460
set jd847 [$e addTechVia [V VIA12]]
$e newPath $jd847 FIXED
$e addITerm [IT M7_8 Y]
$e newPath $emj1503 FIXED [RL M9]
set jd848 [$e addTechVia [V {VIA89}]]
$e newPath $jd848 FIXED [RL M8]
$e addPoint 3920200 2567340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3920200 2567420
set jd849 [$e addTechVia [V VIA67]]
$e newPath $jd849 FIXED
$e addPoint 3920120 2567420
set jd850 [$e addTechVia [V VIA56]]
$e newPath $jd850 FIXED
$e addPoint 3920120 2567516
set jd851 [$e addTechVia [V VIA45]]
$e newPath $jd851 FIXED
$e addPoint 3920216 2567516
set jd852 [$e addTechVia [V VIA34]]
$e newPath $jd852 FIXED
$e addPoint 3920216 2567340
set jd853 [$e addTechVia [V VIA23]]
$e newPath $jd853 FIXED
$e addPoint 3920049 2567340
set jd854 [$e addTechVia [V VIA12]]
$e newPath $jd854 FIXED
$e addITerm [IT M7_9 Y]
$e newPath $emj1435 FIXED [RL M9]
set jd855 [$e addTechVia [V {VIA89}]]
$e newPath $jd855 FIXED [RL M8]
$e addPoint 3851480 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3851480 2832740
set jd856 [$e addTechVia [V VIA67]]
$e newPath $jd856 FIXED
$e addPoint 3851560 2832740
set jd857 [$e addTechVia [V VIA56]]
$e newPath $jd857 FIXED
$e addPoint 3851560 2832836
set jd858 [$e addTechVia [V VIA45]]
$e newPath $jd858 FIXED
$e addPoint 3852013 2832836
set jd859 [$e addTechVia [V VIA34]]
$e newPath $jd859 FIXED
$e addPoint 3852013 2832660
set jd860 [$e addTechVia [V VIA23]]
$e newPath $jd860 FIXED
$e addPoint 3852063 2832660
set jd861 [$e addTechVia [V VIA12]]
$e newPath $jd861 FIXED
$e addITerm [IT M7_10 Y]
$e newPath $emj1784 FIXED [RL M9]
set jd862 [$e addTechVia [V {VIA89}]]
$e newPath $jd862 FIXED [RL M8]
$e addPoint 3920200 3107340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3920200 3107420
set jd863 [$e addTechVia [V VIA67]]
$e newPath $jd863 FIXED
$e addPoint 3920120 3107420
set jd864 [$e addTechVia [V VIA56]]
$e newPath $jd864 FIXED
$e addPoint 3920120 3107516
set jd865 [$e addTechVia [V VIA45]]
$e newPath $jd865 FIXED
$e addPoint 3920216 3107516
set jd866 [$e addTechVia [V VIA34]]
$e newPath $jd866 FIXED
$e addPoint 3920216 3107340
set jd867 [$e addTechVia [V VIA23]]
$e newPath $jd867 FIXED
$e addPoint 3920049 3107340
set jd868 [$e addTechVia [V VIA12]]
$e newPath $jd868 FIXED
$e addITerm [IT M7_11 Y]
$e newPath $emj1959 FIXED [RL M9]
set jd869 [$e addTechVia [V {VIA89}]]
$e newPath $jd869 FIXED [RL M8]
$e addPoint 3920200 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3920200 3372740
set jd870 [$e addTechVia [V VIA67]]
$e newPath $jd870 FIXED
$e addPoint 3920120 3372740
set jd871 [$e addTechVia [V VIA56]]
$e newPath $jd871 FIXED
$e addPoint 3920120 3372836
set jd872 [$e addTechVia [V VIA45]]
$e newPath $jd872 FIXED
$e addPoint 3920216 3372836
set jd873 [$e addTechVia [V VIA34]]
$e newPath $jd873 FIXED
$e addPoint 3920216 3372660
set jd874 [$e addTechVia [V VIA23]]
$e newPath $jd874 FIXED
$e addPoint 3920049 3372660
set jd875 [$e addTechVia [V VIA12]]
$e newPath $jd875 FIXED
$e addITerm [IT M7_12 Y]
$e newPath $emj2096 FIXED [RL M9]
set jd876 [$e addTechVia [V {VIA89}]]
$e newPath $jd876 FIXED [RL M8]
$e addPoint 3902920 3647340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3902920 3647420
set jd877 [$e addTechVia [V VIA67]]
$e newPath $jd877 FIXED
$e addPoint 3902840 3647420
set jd878 [$e addTechVia [V VIA56]]
$e newPath $jd878 FIXED
$e addPoint 3902840 3647516
set jd879 [$e addTechVia [V VIA45]]
$e newPath $jd879 FIXED
$e addPoint 3902117 3647516
set jd880 [$e addTechVia [V VIA34]]
$e newPath $jd880 FIXED
$e addPoint 3902117 3647340
set jd881 [$e addTechVia [V VIA23]]
$e newPath $jd881 FIXED
$e addPoint 3902067 3647340
set jd882 [$e addTechVia [V VIA12]]
$e newPath $jd882 FIXED
$e addITerm [IT M7_13 Y]
$e newPath $emj2146 FIXED [RL M9]
set jd883 [$e addTechVia [V {VIA89}]]
$e newPath $jd883 FIXED [RL M8]
$e addPoint 3873080 3912660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3873080 3912740
set jd884 [$e addTechVia [V VIA67]]
$e newPath $jd884 FIXED
$e addPoint 3873160 3912740
set jd885 [$e addTechVia [V VIA56]]
$e newPath $jd885 FIXED
$e addPoint 3873160 3912836
set jd886 [$e addTechVia [V VIA45]]
$e newPath $jd886 FIXED
$e addPoint 3873991 3912836
set jd887 [$e addTechVia [V VIA34]]
$e newPath $jd887 FIXED
$e addPoint 3873991 3912660
set jd888 [$e addTechVia [V VIA23]]
$e newPath $jd888 FIXED
$e addPoint 3874041 3912660
set jd889 [$e addTechVia [V VIA12]]
$e newPath $jd889 FIXED
$e addITerm [IT M7_14 Y]
$e newPath $emj2189 FIXED [RL M9]
set jd890 [$e addTechVia [V {VIA89}]]
$e newPath $jd890 FIXED [RL M8]
$e addPoint 3851480 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3851480 4187420
set jd891 [$e addTechVia [V VIA67]]
$e newPath $jd891 FIXED
$e addPoint 3851560 4187420
set jd892 [$e addTechVia [V VIA56]]
$e newPath $jd892 FIXED
$e addPoint 3851560 4187516
set jd893 [$e addTechVia [V VIA45]]
$e newPath $jd893 FIXED
$e addPoint 3852013 4187516
set jd894 [$e addTechVia [V VIA34]]
$e newPath $jd894 FIXED
$e addPoint 3852013 4187340
set jd895 [$e addTechVia [V VIA23]]
$e newPath $jd895 FIXED
$e addPoint 3852063 4187340
set jd896 [$e addTechVia [V VIA12]]
$e newPath $jd896 FIXED
$e addITerm [IT M7_15 Y]
$e newPath $emj595 FIXED [RL M9]
set jd897 [$e addTechVia [V {VIA89}]]
$e newPath $jd897 FIXED [RL M8]
$e addPoint 4360840 72180
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4360840 72260
set jd898 [$e addTechVia [V VIA67]]
$e newPath $jd898 FIXED
$e addPoint 4360760 72260
set jd899 [$e addTechVia [V VIA56]]
$e newPath $jd899 FIXED
$e addPoint 4360760 72356
set jd900 [$e addTechVia [V VIA45]]
$e newPath $jd900 FIXED
$e addPoint 4360856 72356
set jd901 [$e addTechVia [V VIA34]]
$e newPath $jd901 FIXED
$e addPoint 4360856 72180
set jd902 [$e addTechVia [V VIA23]]
$e newPath $jd902 FIXED
$e addPoint 4360743 72180
set jd903 [$e addTechVia [V VIA12]]
$e newPath $jd903 FIXED
$e addITerm [IT M8_0 Y]
$e newPath $emj449 FIXED [RL M9]
set jd904 [$e addTechVia [V {VIA89}]]
$e newPath $jd904 FIXED [RL M8]
$e addPoint 4365560 407340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365560 407420
set jd905 [$e addTechVia [V VIA67]]
$e newPath $jd905 FIXED
$e addPoint 4365640 407420
set jd906 [$e addTechVia [V VIA56]]
$e newPath $jd906 FIXED
$e addPoint 4365640 407516
set jd907 [$e addTechVia [V VIA45]]
$e newPath $jd907 FIXED
$e addPoint 4366093 407516
set jd908 [$e addTechVia [V VIA34]]
$e newPath $jd908 FIXED
$e addPoint 4366093 407340
set jd909 [$e addTechVia [V VIA23]]
$e newPath $jd909 FIXED
$e addPoint 4366143 407340
set jd910 [$e addTechVia [V VIA12]]
$e newPath $jd910 FIXED
$e addITerm [IT M8_1 Y]
$e newPath $emj544 FIXED [RL M9]
set jd911 [$e addTechVia [V {VIA89}]]
$e newPath $jd911 FIXED [RL M8]
$e addPoint 4365560 672660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365560 672740
set jd912 [$e addTechVia [V VIA67]]
$e newPath $jd912 FIXED
$e addPoint 4365640 672740
set jd913 [$e addTechVia [V VIA56]]
$e newPath $jd913 FIXED
$e addPoint 4365640 672836
set jd914 [$e addTechVia [V VIA45]]
$e newPath $jd914 FIXED
$e addPoint 4366093 672836
set jd915 [$e addTechVia [V VIA34]]
$e newPath $jd915 FIXED
$e addPoint 4366093 672660
set jd916 [$e addTechVia [V VIA23]]
$e newPath $jd916 FIXED
$e addPoint 4366143 672660
set jd917 [$e addTechVia [V VIA12]]
$e newPath $jd917 FIXED
$e addITerm [IT M8_2 Y]
$e newPath $emj784 FIXED [RL M9]
set jd918 [$e addTechVia [V {VIA89}]]
$e newPath $jd918 FIXED [RL M8]
$e addPoint 4365560 947340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365560 947420
set jd919 [$e addTechVia [V VIA67]]
$e newPath $jd919 FIXED
$e addPoint 4365640 947420
set jd920 [$e addTechVia [V VIA56]]
$e newPath $jd920 FIXED
$e addPoint 4365640 947516
set jd921 [$e addTechVia [V VIA45]]
$e newPath $jd921 FIXED
$e addPoint 4366093 947516
set jd922 [$e addTechVia [V VIA34]]
$e newPath $jd922 FIXED
$e addPoint 4366093 947340
set jd923 [$e addTechVia [V VIA23]]
$e newPath $jd923 FIXED
$e addPoint 4366143 947340
set jd924 [$e addTechVia [V VIA12]]
$e newPath $jd924 FIXED
$e addITerm [IT M8_3 Y]
$e newPath $emj659 FIXED [RL M9]
set jd925 [$e addTechVia [V {VIA89}]]
$e newPath $jd925 FIXED [RL M8]
$e addPoint 4365560 1212660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365560 1212740
set jd926 [$e addTechVia [V VIA67]]
$e newPath $jd926 FIXED
$e addPoint 4365640 1212740
set jd927 [$e addTechVia [V VIA56]]
$e newPath $jd927 FIXED
$e addPoint 4365640 1212836
set jd928 [$e addTechVia [V VIA45]]
$e newPath $jd928 FIXED
$e addPoint 4366093 1212836
set jd929 [$e addTechVia [V VIA34]]
$e newPath $jd929 FIXED
$e addPoint 4366093 1212660
set jd930 [$e addTechVia [V VIA23]]
$e newPath $jd930 FIXED
$e addPoint 4366143 1212660
set jd931 [$e addTechVia [V VIA12]]
$e newPath $jd931 FIXED
$e addITerm [IT M8_4 Y]
$e newPath $emj730 FIXED [RL M9]
set jd932 [$e addTechVia [V {VIA89}]]
$e newPath $jd932 FIXED [RL M8]
$e addPoint 4365560 1487340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365560 1487420
set jd933 [$e addTechVia [V VIA67]]
$e newPath $jd933 FIXED
$e addPoint 4365640 1487420
set jd934 [$e addTechVia [V VIA56]]
$e newPath $jd934 FIXED
$e addPoint 4365640 1487516
set jd935 [$e addTechVia [V VIA45]]
$e newPath $jd935 FIXED
$e addPoint 4366093 1487516
set jd936 [$e addTechVia [V VIA34]]
$e newPath $jd936 FIXED
$e addPoint 4366093 1487340
set jd937 [$e addTechVia [V VIA23]]
$e newPath $jd937 FIXED
$e addPoint 4366143 1487340
set jd938 [$e addTechVia [V VIA12]]
$e newPath $jd938 FIXED
$e addITerm [IT M8_5 Y]
$e newPath $emj869 FIXED [RL M9]
set jd939 [$e addTechVia [V {VIA89}]]
$e newPath $jd939 FIXED [RL M8]
$e addPoint 4365560 1752660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365560 1752740
set jd940 [$e addTechVia [V VIA67]]
$e newPath $jd940 FIXED
$e addPoint 4365640 1752740
set jd941 [$e addTechVia [V VIA56]]
$e newPath $jd941 FIXED
$e addPoint 4365640 1752836
set jd942 [$e addTechVia [V VIA45]]
$e newPath $jd942 FIXED
$e addPoint 4366093 1752836
set jd943 [$e addTechVia [V VIA34]]
$e newPath $jd943 FIXED
$e addPoint 4366093 1752660
set jd944 [$e addTechVia [V VIA23]]
$e newPath $jd944 FIXED
$e addPoint 4366143 1752660
set jd945 [$e addTechVia [V VIA12]]
$e newPath $jd945 FIXED
$e addITerm [IT M8_6 Y]
$e newPath $emj1163 FIXED [RL M9]
set jd946 [$e addTechVia [V {VIA89}]]
$e newPath $jd946 FIXED [RL M8]
$e addPoint 4365560 2027340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365560 2027420
set jd947 [$e addTechVia [V VIA67]]
$e newPath $jd947 FIXED
$e addPoint 4365640 2027420
set jd948 [$e addTechVia [V VIA56]]
$e newPath $jd948 FIXED
$e addPoint 4365640 2027516
set jd949 [$e addTechVia [V VIA45]]
$e newPath $jd949 FIXED
$e addPoint 4366093 2027516
set jd950 [$e addTechVia [V VIA34]]
$e newPath $jd950 FIXED
$e addPoint 4366093 2027340
set jd951 [$e addTechVia [V VIA23]]
$e newPath $jd951 FIXED
$e addPoint 4366143 2027340
set jd952 [$e addTechVia [V VIA12]]
$e newPath $jd952 FIXED
$e addITerm [IT M8_7 Y]
$e newPath $emj1424 FIXED [RL M9]
set jd953 [$e addTechVia [V {VIA89}]]
$e newPath $jd953 FIXED [RL M8]
$e addPoint 4365560 2292660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365560 2292740
set jd954 [$e addTechVia [V VIA67]]
$e newPath $jd954 FIXED
$e addPoint 4365640 2292740
set jd955 [$e addTechVia [V VIA56]]
$e newPath $jd955 FIXED
$e addPoint 4365640 2292836
set jd956 [$e addTechVia [V VIA45]]
$e newPath $jd956 FIXED
$e addPoint 4366093 2292836
set jd957 [$e addTechVia [V VIA34]]
$e newPath $jd957 FIXED
$e addPoint 4366093 2292660
set jd958 [$e addTechVia [V VIA23]]
$e newPath $jd958 FIXED
$e addPoint 4366143 2292660
set jd959 [$e addTechVia [V VIA12]]
$e newPath $jd959 FIXED
$e addITerm [IT M8_8 Y]
$e newPath $emj1571 FIXED [RL M9]
set jd960 [$e addTechVia [V {VIA89}]]
$e newPath $jd960 FIXED [RL M8]
$e addPoint 4283080 2567340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4283080 2567420
set jd961 [$e addTechVia [V VIA67]]
$e newPath $jd961 FIXED
$e addPoint 4283000 2567420
set jd962 [$e addTechVia [V VIA56]]
$e newPath $jd962 FIXED
$e addPoint 4283000 2567516
set jd963 [$e addTechVia [V VIA45]]
$e newPath $jd963 FIXED
$e addPoint 4282169 2567516
set jd964 [$e addTechVia [V VIA34]]
$e newPath $jd964 FIXED
$e addPoint 4282169 2567340
set jd965 [$e addTechVia [V VIA23]]
$e newPath $jd965 FIXED
$e addPoint 4282119 2567340
set jd966 [$e addTechVia [V VIA12]]
$e newPath $jd966 FIXED
$e addITerm [IT M8_9 Y]
$e newPath $emj1733 FIXED [RL M9]
set jd967 [$e addTechVia [V {VIA89}]]
$e newPath $jd967 FIXED [RL M8]
$e addPoint 4365560 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365560 2832740
set jd968 [$e addTechVia [V VIA67]]
$e newPath $jd968 FIXED
$e addPoint 4365640 2832740
set jd969 [$e addTechVia [V VIA56]]
$e newPath $jd969 FIXED
$e addPoint 4365640 2832836
set jd970 [$e addTechVia [V VIA45]]
$e newPath $jd970 FIXED
$e addPoint 4366093 2832836
set jd971 [$e addTechVia [V VIA34]]
$e newPath $jd971 FIXED
$e addPoint 4366093 2832660
set jd972 [$e addTechVia [V VIA23]]
$e newPath $jd972 FIXED
$e addPoint 4366143 2832660
set jd973 [$e addTechVia [V VIA12]]
$e newPath $jd973 FIXED
$e addITerm [IT M8_10 Y]
$e newPath $emj1839 FIXED [RL M9]
set jd974 [$e addTechVia [V {VIA89}]]
$e newPath $jd974 FIXED [RL M8]
$e addPoint 4365560 3189420
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365560 3189500
set jd975 [$e addTechVia [V VIA67]]
$e newPath $jd975 FIXED
$e addPoint 4365640 3189500
set jd976 [$e addTechVia [V VIA56]]
$e newPath $jd976 FIXED
$e addPoint 4365640 3189596
set jd977 [$e addTechVia [V VIA45]]
$e newPath $jd977 FIXED
$e addPoint 4366093 3189596
set jd978 [$e addTechVia [V VIA34]]
$e newPath $jd978 FIXED
$e addPoint 4366093 3189420
set jd979 [$e addTechVia [V VIA23]]
$e newPath $jd979 FIXED
$e addPoint 4366143 3189420
set jd980 [$e addTechVia [V VIA12]]
$e newPath $jd980 FIXED
$e addITerm [IT M8_11 Y]
$e newPath $emj2139 FIXED [RL M9]
set jd981 [$e addTechVia [V {VIA89}]]
$e newPath $jd981 FIXED [RL M8]
$e addPoint 4369880 3396780
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4369880 3396860
set jd982 [$e addTechVia [V VIA67]]
$e newPath $jd982 FIXED
$e addPoint 4369960 3396860
set jd983 [$e addTechVia [V VIA56]]
$e newPath $jd983 FIXED
$e addPoint 4369960 3396956
set jd984 [$e addTechVia [V VIA45]]
$e newPath $jd984 FIXED
$e addPoint 4371763 3396956
set jd985 [$e addTechVia [V VIA34]]
$e newPath $jd985 FIXED
$e addPoint 4371763 3396780
set jd986 [$e addTechVia [V VIA23]]
$e newPath $jd986 FIXED
$e addPoint 4371813 3396780
set jd987 [$e addTechVia [V VIA12]]
$e newPath $jd987 FIXED
$e addITerm [IT M8_12 Y]
$e newPath $emj2213 FIXED [RL M9]
set jd988 [$e addTechVia [V {VIA89}]]
$e newPath $jd988 FIXED [RL M8]
$e addPoint 4348280 3545460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4348280 3545540
set jd989 [$e addTechVia [V VIA67]]
$e newPath $jd989 FIXED
$e addPoint 4348360 3545540
set jd990 [$e addTechVia [V VIA56]]
$e newPath $jd990 FIXED
$e addPoint 4348360 3545636
set jd991 [$e addTechVia [V VIA45]]
$e newPath $jd991 FIXED
$e addPoint 4348705 3545636
set jd992 [$e addTechVia [V VIA34]]
$e newPath $jd992 FIXED
$e addPoint 4348705 3545460
set jd993 [$e addTechVia [V VIA23]]
$e newPath $jd993 FIXED
$e addPoint 4348755 3545460
set jd994 [$e addTechVia [V VIA12]]
$e newPath $jd994 FIXED
$e addITerm [IT M8_13 Y]
$e newPath $emj2186 FIXED [RL M9]
set jd995 [$e addTechVia [V {VIA89}]]
$e newPath $jd995 FIXED [RL M8]
$e addPoint 4205320 3912660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4205320 3912740
set jd996 [$e addTechVia [V VIA67]]
$e newPath $jd996 FIXED
$e addPoint 4205240 3912740
set jd997 [$e addTechVia [V VIA56]]
$e newPath $jd997 FIXED
$e addPoint 4205240 3912836
set jd998 [$e addTechVia [V VIA45]]
$e newPath $jd998 FIXED
$e addPoint 4204193 3912836
set jd999 [$e addTechVia [V VIA34]]
$e newPath $jd999 FIXED
$e addPoint 4204193 3912660
set jd1000 [$e addTechVia [V VIA23]]
$e newPath $jd1000 FIXED
$e addPoint 4204143 3912660
set jd1001 [$e addTechVia [V VIA12]]
$e newPath $jd1001 FIXED
$e addITerm [IT M8_14 Y]
$e newPath $emj2349 FIXED [RL M9]
set jd1002 [$e addTechVia [V {VIA89}]]
$e newPath $jd1002 FIXED [RL M8]
$e addPoint 4374200 4295340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4374200 4295420
set jd1003 [$e addTechVia [V VIA67]]
$e newPath $jd1003 FIXED
$e addPoint 4374280 4295420
set jd1004 [$e addTechVia [V VIA56]]
$e newPath $jd1004 FIXED
$e addPoint 4374280 4295516
set jd1005 [$e addTechVia [V VIA45]]
$e newPath $jd1005 FIXED
$e addPoint 4375705 4295516
set jd1006 [$e addTechVia [V VIA34]]
$e newPath $jd1006 FIXED
$e addPoint 4375705 4295340
set jd1007 [$e addTechVia [V VIA23]]
$e newPath $jd1007 FIXED
$e addPoint 4375755 4295340
set jd1008 [$e addTechVia [V VIA12]]
$e newPath $jd1008 FIXED
$e addITerm [IT M8_15 Y]
$e newPath $emj648 FIXED [RL M9]
set jd1009 [$e addTechVia [V {VIA89}]]
$e newPath $jd1009 FIXED [RL M8]
$e addPoint 4879640 132660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 132740
set jd1010 [$e addTechVia [V VIA67]]
$e newPath $jd1010 FIXED
$e addPoint 4879720 132740
set jd1011 [$e addTechVia [V VIA56]]
$e newPath $jd1011 FIXED
$e addPoint 4879720 132836
set jd1012 [$e addTechVia [V VIA45]]
$e newPath $jd1012 FIXED
$e addPoint 4880173 132836
set jd1013 [$e addTechVia [V VIA34]]
$e newPath $jd1013 FIXED
$e addPoint 4880173 132660
set jd1014 [$e addTechVia [V VIA23]]
$e newPath $jd1014 FIXED
$e addPoint 4880223 132660
set jd1015 [$e addTechVia [V VIA12]]
$e newPath $jd1015 FIXED
$e addITerm [IT M9_0 Y]
$e newPath $emj491 FIXED [RL M9]
set jd1016 [$e addTechVia [V {VIA89}]]
$e newPath $jd1016 FIXED [RL M8]
$e addPoint 4879640 407340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 407420
set jd1017 [$e addTechVia [V VIA67]]
$e newPath $jd1017 FIXED
$e addPoint 4879720 407420
set jd1018 [$e addTechVia [V VIA56]]
$e newPath $jd1018 FIXED
$e addPoint 4879720 407516
set jd1019 [$e addTechVia [V VIA45]]
$e newPath $jd1019 FIXED
$e addPoint 4880173 407516
set jd1020 [$e addTechVia [V VIA34]]
$e newPath $jd1020 FIXED
$e addPoint 4880173 407340
set jd1021 [$e addTechVia [V VIA23]]
$e newPath $jd1021 FIXED
$e addPoint 4880223 407340
set jd1022 [$e addTechVia [V VIA12]]
$e newPath $jd1022 FIXED
$e addITerm [IT M9_1 Y]
$e newPath $emj714 FIXED [RL M9]
set jd1023 [$e addTechVia [V {VIA89}]]
$e newPath $jd1023 FIXED [RL M8]
$e addPoint 4879640 672660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 672740
set jd1024 [$e addTechVia [V VIA67]]
$e newPath $jd1024 FIXED
$e addPoint 4879720 672740
set jd1025 [$e addTechVia [V VIA56]]
$e newPath $jd1025 FIXED
$e addPoint 4879720 672836
set jd1026 [$e addTechVia [V VIA45]]
$e newPath $jd1026 FIXED
$e addPoint 4880173 672836
set jd1027 [$e addTechVia [V VIA34]]
$e newPath $jd1027 FIXED
$e addPoint 4880173 672660
set jd1028 [$e addTechVia [V VIA23]]
$e newPath $jd1028 FIXED
$e addPoint 4880223 672660
set jd1029 [$e addTechVia [V VIA12]]
$e newPath $jd1029 FIXED
$e addITerm [IT M9_2 Y]
$e newPath $emj998 FIXED [RL M9]
set jd1030 [$e addTechVia [V {VIA89}]]
$e newPath $jd1030 FIXED [RL M8]
$e addPoint 4879640 947340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 947420
set jd1031 [$e addTechVia [V VIA67]]
$e newPath $jd1031 FIXED
$e addPoint 4879720 947420
set jd1032 [$e addTechVia [V VIA56]]
$e newPath $jd1032 FIXED
$e addPoint 4879720 947516
set jd1033 [$e addTechVia [V VIA45]]
$e newPath $jd1033 FIXED
$e addPoint 4880173 947516
set jd1034 [$e addTechVia [V VIA34]]
$e newPath $jd1034 FIXED
$e addPoint 4880173 947340
set jd1035 [$e addTechVia [V VIA23]]
$e newPath $jd1035 FIXED
$e addPoint 4880223 947340
set jd1036 [$e addTechVia [V VIA12]]
$e newPath $jd1036 FIXED
$e addITerm [IT M9_3 Y]
$e newPath $emj724 FIXED [RL M9]
set jd1037 [$e addTechVia [V {VIA89}]]
$e newPath $jd1037 FIXED [RL M8]
$e addPoint 4879640 1212660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 1212740
set jd1038 [$e addTechVia [V VIA67]]
$e newPath $jd1038 FIXED
$e addPoint 4879720 1212740
set jd1039 [$e addTechVia [V VIA56]]
$e newPath $jd1039 FIXED
$e addPoint 4879720 1212836
set jd1040 [$e addTechVia [V VIA45]]
$e newPath $jd1040 FIXED
$e addPoint 4880173 1212836
set jd1041 [$e addTechVia [V VIA34]]
$e newPath $jd1041 FIXED
$e addPoint 4880173 1212660
set jd1042 [$e addTechVia [V VIA23]]
$e newPath $jd1042 FIXED
$e addPoint 4880223 1212660
set jd1043 [$e addTechVia [V VIA12]]
$e newPath $jd1043 FIXED
$e addITerm [IT M9_4 Y]
$e newPath $emj938 FIXED [RL M9]
set jd1044 [$e addTechVia [V {VIA89}]]
$e newPath $jd1044 FIXED [RL M8]
$e addPoint 4879640 1487340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 1487420
set jd1045 [$e addTechVia [V VIA67]]
$e newPath $jd1045 FIXED
$e addPoint 4879720 1487420
set jd1046 [$e addTechVia [V VIA56]]
$e newPath $jd1046 FIXED
$e addPoint 4879720 1487516
set jd1047 [$e addTechVia [V VIA45]]
$e newPath $jd1047 FIXED
$e addPoint 4880173 1487516
set jd1048 [$e addTechVia [V VIA34]]
$e newPath $jd1048 FIXED
$e addPoint 4880173 1487340
set jd1049 [$e addTechVia [V VIA23]]
$e newPath $jd1049 FIXED
$e addPoint 4880223 1487340
set jd1050 [$e addTechVia [V VIA12]]
$e newPath $jd1050 FIXED
$e addITerm [IT M9_5 Y]
$e newPath $emj1093 FIXED [RL M9]
set jd1051 [$e addTechVia [V {VIA89}]]
$e newPath $jd1051 FIXED [RL M8]
$e addPoint 4879640 1752660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 1752740
set jd1052 [$e addTechVia [V VIA67]]
$e newPath $jd1052 FIXED
$e addPoint 4879720 1752740
set jd1053 [$e addTechVia [V VIA56]]
$e newPath $jd1053 FIXED
$e addPoint 4879720 1752836
set jd1054 [$e addTechVia [V VIA45]]
$e newPath $jd1054 FIXED
$e addPoint 4880173 1752836
set jd1055 [$e addTechVia [V VIA34]]
$e newPath $jd1055 FIXED
$e addPoint 4880173 1752660
set jd1056 [$e addTechVia [V VIA23]]
$e newPath $jd1056 FIXED
$e addPoint 4880223 1752660
set jd1057 [$e addTechVia [V VIA12]]
$e newPath $jd1057 FIXED
$e addITerm [IT M9_6 Y]
$e newPath $emj1296 FIXED [RL M9]
set jd1058 [$e addTechVia [V {VIA89}]]
$e newPath $jd1058 FIXED [RL M8]
$e addPoint 4879640 2027340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 2027420
set jd1059 [$e addTechVia [V VIA67]]
$e newPath $jd1059 FIXED
$e addPoint 4879720 2027420
set jd1060 [$e addTechVia [V VIA56]]
$e newPath $jd1060 FIXED
$e addPoint 4879720 2027516
set jd1061 [$e addTechVia [V VIA45]]
$e newPath $jd1061 FIXED
$e addPoint 4880173 2027516
set jd1062 [$e addTechVia [V VIA34]]
$e newPath $jd1062 FIXED
$e addPoint 4880173 2027340
set jd1063 [$e addTechVia [V VIA23]]
$e newPath $jd1063 FIXED
$e addPoint 4880223 2027340
set jd1064 [$e addTechVia [V VIA12]]
$e newPath $jd1064 FIXED
$e addITerm [IT M9_7 Y]
$e newPath $emj1566 FIXED [RL M9]
set jd1065 [$e addTechVia [V {VIA89}]]
$e newPath $jd1065 FIXED [RL M8]
$e addPoint 4879640 2292660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 2292740
set jd1066 [$e addTechVia [V VIA67]]
$e newPath $jd1066 FIXED
$e addPoint 4879720 2292740
set jd1067 [$e addTechVia [V VIA56]]
$e newPath $jd1067 FIXED
$e addPoint 4879720 2292836
set jd1068 [$e addTechVia [V VIA45]]
$e newPath $jd1068 FIXED
$e addPoint 4880173 2292836
set jd1069 [$e addTechVia [V VIA34]]
$e newPath $jd1069 FIXED
$e addPoint 4880173 2292660
set jd1070 [$e addTechVia [V VIA23]]
$e newPath $jd1070 FIXED
$e addPoint 4880223 2292660
set jd1071 [$e addTechVia [V VIA12]]
$e newPath $jd1071 FIXED
$e addITerm [IT M9_8 Y]
$e newPath $emj1775 FIXED [RL M9]
set jd1072 [$e addTechVia [V {VIA89}]]
$e newPath $jd1072 FIXED [RL M8]
$e addPoint 4792840 2580840
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4792840 2580920
set jd1073 [$e addTechVia [V VIA67]]
$e newPath $jd1073 FIXED
$e addPoint 4792760 2580920
set jd1074 [$e addTechVia [V VIA56]]
$e newPath $jd1074 FIXED
$e addPoint 4792760 2581016
set jd1075 [$e addTechVia [V VIA45]]
$e newPath $jd1075 FIXED
$e addPoint 4791659 2581016
set jd1076 [$e addTechVia [V VIA34]]
$e newPath $jd1076 FIXED
$e addPoint 4791659 2580840
set jd1077 [$e addTechVia [V VIA23]]
$e newPath $jd1077 FIXED
$e addPoint 4791609 2580840
set jd1078 [$e addTechVia [V VIA12]]
$e newPath $jd1078 FIXED
$e addITerm [IT M9_9 Y]
$e newPath $emj1828 FIXED [RL M9]
set jd1079 [$e addTechVia [V {VIA89}]]
$e newPath $jd1079 FIXED [RL M8]
$e addPoint 4879640 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 2832740
set jd1080 [$e addTechVia [V VIA67]]
$e newPath $jd1080 FIXED
$e addPoint 4879720 2832740
set jd1081 [$e addTechVia [V VIA56]]
$e newPath $jd1081 FIXED
$e addPoint 4879720 2832836
set jd1082 [$e addTechVia [V VIA45]]
$e newPath $jd1082 FIXED
$e addPoint 4880173 2832836
set jd1083 [$e addTechVia [V VIA34]]
$e newPath $jd1083 FIXED
$e addPoint 4880173 2832660
set jd1084 [$e addTechVia [V VIA23]]
$e newPath $jd1084 FIXED
$e addPoint 4880223 2832660
set jd1085 [$e addTechVia [V VIA12]]
$e newPath $jd1085 FIXED
$e addITerm [IT M9_10 Y]
$e newPath $emj1954 FIXED [RL M9]
set jd1086 [$e addTechVia [V {VIA89}]]
$e newPath $jd1086 FIXED [RL M8]
$e addPoint 4879640 3107340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 3107420
set jd1087 [$e addTechVia [V VIA67]]
$e newPath $jd1087 FIXED
$e addPoint 4879720 3107420
set jd1088 [$e addTechVia [V VIA56]]
$e newPath $jd1088 FIXED
$e addPoint 4879720 3107516
set jd1089 [$e addTechVia [V VIA45]]
$e newPath $jd1089 FIXED
$e addPoint 4880173 3107516
set jd1090 [$e addTechVia [V VIA34]]
$e newPath $jd1090 FIXED
$e addPoint 4880173 3107340
set jd1091 [$e addTechVia [V VIA23]]
$e newPath $jd1091 FIXED
$e addPoint 4880223 3107340
set jd1092 [$e addTechVia [V VIA12]]
$e newPath $jd1092 FIXED
$e addITerm [IT M9_11 Y]
$e newPath $emj2135 FIXED [RL M9]
set jd1093 [$e addTechVia [V {VIA89}]]
$e newPath $jd1093 FIXED [RL M8]
$e addPoint 4879640 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 3372740
set jd1094 [$e addTechVia [V VIA67]]
$e newPath $jd1094 FIXED
$e addPoint 4879720 3372740
set jd1095 [$e addTechVia [V VIA56]]
$e newPath $jd1095 FIXED
$e addPoint 4879720 3372836
set jd1096 [$e addTechVia [V VIA45]]
$e newPath $jd1096 FIXED
$e addPoint 4880173 3372836
set jd1097 [$e addTechVia [V VIA34]]
$e newPath $jd1097 FIXED
$e addPoint 4880173 3372660
set jd1098 [$e addTechVia [V VIA23]]
$e newPath $jd1098 FIXED
$e addPoint 4880223 3372660
set jd1099 [$e addTechVia [V VIA12]]
$e newPath $jd1099 FIXED
$e addITerm [IT M9_12 Y]
$e newPath $emj2245 FIXED [RL M9]
set jd1100 [$e addTechVia [V {VIA89}]]
$e newPath $jd1100 FIXED [RL M8]
$e addPoint 4844680 3655980
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4844680 3656060
set jd1101 [$e addTechVia [V VIA67]]
$e newPath $jd1101 FIXED
$e addPoint 4844600 3656060
set jd1102 [$e addTechVia [V VIA56]]
$e newPath $jd1102 FIXED
$e addPoint 4844600 3656156
set jd1103 [$e addTechVia [V VIA45]]
$e newPath $jd1103 FIXED
$e addPoint 4843553 3656156
set jd1104 [$e addTechVia [V VIA34]]
$e newPath $jd1104 FIXED
$e addPoint 4843553 3655980
set jd1105 [$e addTechVia [V VIA23]]
$e newPath $jd1105 FIXED
$e addPoint 4843503 3655980
set jd1106 [$e addTechVia [V VIA12]]
$e newPath $jd1106 FIXED
$e addITerm [IT M9_13 Y]
$e newPath $emj2281 FIXED [RL M9]
set jd1107 [$e addTechVia [V {VIA89}]]
$e newPath $jd1107 FIXED [RL M8]
$e addPoint 4879640 3912660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 3912740
set jd1108 [$e addTechVia [V VIA67]]
$e newPath $jd1108 FIXED
$e addPoint 4879720 3912740
set jd1109 [$e addTechVia [V VIA56]]
$e newPath $jd1109 FIXED
$e addPoint 4879720 3912836
set jd1110 [$e addTechVia [V VIA45]]
$e newPath $jd1110 FIXED
$e addPoint 4880173 3912836
set jd1111 [$e addTechVia [V VIA34]]
$e newPath $jd1111 FIXED
$e addPoint 4880173 3912660
set jd1112 [$e addTechVia [V VIA23]]
$e newPath $jd1112 FIXED
$e addPoint 4880223 3912660
set jd1113 [$e addTechVia [V VIA12]]
$e newPath $jd1113 FIXED
$e addITerm [IT M9_14 Y]
$e newPath $emj2377 FIXED [RL M9]
set jd1114 [$e addTechVia [V {VIA89}]]
$e newPath $jd1114 FIXED [RL M8]
$e addPoint 4879640 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879640 4187420
set jd1115 [$e addTechVia [V VIA67]]
$e newPath $jd1115 FIXED
$e addPoint 4879720 4187420
set jd1116 [$e addTechVia [V VIA56]]
$e newPath $jd1116 FIXED
$e addPoint 4879720 4187516
set jd1117 [$e addTechVia [V VIA45]]
$e newPath $jd1117 FIXED
$e addPoint 4880173 4187516
set jd1118 [$e addTechVia [V VIA34]]
$e newPath $jd1118 FIXED
$e addPoint 4880173 4187340
set jd1119 [$e addTechVia [V VIA23]]
$e newPath $jd1119 FIXED
$e addPoint 4880223 4187340
set jd1120 [$e addTechVia [V VIA12]]
$e newPath $jd1120 FIXED
$e addITerm [IT M9_15 Y]
$e newPath $emj535 FIXED [RL M9]
set jd1121 [$e addTechVia [V {VIA89}]]
$e newPath $jd1121 FIXED [RL M8]
$e addPoint 5393720 14220
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5393720 14300
set jd1122 [$e addTechVia [V VIA67]]
$e newPath $jd1122 FIXED
$e addPoint 5393800 14300
set jd1123 [$e addTechVia [V VIA56]]
$e newPath $jd1123 FIXED
$e addPoint 5393800 14396
set jd1124 [$e addTechVia [V VIA45]]
$e newPath $jd1124 FIXED
$e addPoint 5394253 14396
set jd1125 [$e addTechVia [V VIA34]]
$e newPath $jd1125 FIXED
$e addPoint 5394253 14220
set jd1126 [$e addTechVia [V VIA23]]
$e newPath $jd1126 FIXED
$e addPoint 5394303 14220
set jd1127 [$e addTechVia [V VIA12]]
$e newPath $jd1127 FIXED
$e addITerm [IT M10_0 Y]
$e newPath $emj533 FIXED [RL M9]
set jd1128 [$e addTechVia [V {VIA89}]]
$e newPath $jd1128 FIXED [RL M8]
$e addPoint 5397640 409140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5397640 409220
set jd1129 [$e addTechVia [V VIA67]]
$e newPath $jd1129 FIXED
$e addPoint 5397560 409220
set jd1130 [$e addTechVia [V VIA56]]
$e newPath $jd1130 FIXED
$e addPoint 5397560 409316
set jd1131 [$e addTechVia [V VIA45]]
$e newPath $jd1131 FIXED
$e addPoint 5397377 409316
set jd1132 [$e addTechVia [V VIA34]]
$e newPath $jd1132 FIXED
$e addPoint 5397377 409140
set jd1133 [$e addTechVia [V VIA23]]
$e newPath $jd1133 FIXED
$e addPoint 5397327 409140
set jd1134 [$e addTechVia [V VIA12]]
$e newPath $jd1134 FIXED
$e addITerm [IT M10_1 Y]
$e newPath $emj847 FIXED [RL M9]
set jd1135 [$e addTechVia [V {VIA89}]]
$e newPath $jd1135 FIXED [RL M8]
$e addPoint 5397640 714060
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5397640 714140
set jd1136 [$e addTechVia [V VIA67]]
$e newPath $jd1136 FIXED
$e addPoint 5397560 714140
set jd1137 [$e addTechVia [V VIA56]]
$e newPath $jd1137 FIXED
$e addPoint 5397560 714236
set jd1138 [$e addTechVia [V VIA45]]
$e newPath $jd1138 FIXED
$e addPoint 5397464 714236
set jd1139 [$e addTechVia [V VIA34]]
$e newPath $jd1139 FIXED
$e addPoint 5397464 714060
set jd1140 [$e addTechVia [V VIA23]]
$e newPath $jd1140 FIXED
$e addPoint 5397597 714060
set jd1141 [$e addTechVia [V VIA12]]
$e newPath $jd1141 FIXED
$e addITerm [IT M10_2 Y]
$e newPath $emj778 FIXED [RL M9]
set jd1142 [$e addTechVia [V {VIA89}]]
$e newPath $jd1142 FIXED [RL M8]
$e addPoint 5393720 947340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5393720 947420
set jd1143 [$e addTechVia [V VIA67]]
$e newPath $jd1143 FIXED
$e addPoint 5393800 947420
set jd1144 [$e addTechVia [V VIA56]]
$e newPath $jd1144 FIXED
$e addPoint 5393800 947516
set jd1145 [$e addTechVia [V VIA45]]
$e newPath $jd1145 FIXED
$e addPoint 5394253 947516
set jd1146 [$e addTechVia [V VIA34]]
$e newPath $jd1146 FIXED
$e addPoint 5394253 947340
set jd1147 [$e addTechVia [V VIA23]]
$e newPath $jd1147 FIXED
$e addPoint 5394303 947340
set jd1148 [$e addTechVia [V VIA12]]
$e newPath $jd1148 FIXED
$e addITerm [IT M10_3 Y]
$e newPath $emj787 FIXED [RL M9]
set jd1149 [$e addTechVia [V {VIA89}]]
$e newPath $jd1149 FIXED [RL M8]
$e addPoint 5406680 1074420
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5406680 1074500
set jd1150 [$e addTechVia [V VIA67]]
$e newPath $jd1150 FIXED
$e addPoint 5406760 1074500
set jd1151 [$e addTechVia [V VIA56]]
$e newPath $jd1151 FIXED
$e addPoint 5406760 1074596
set jd1152 [$e addTechVia [V VIA45]]
$e newPath $jd1152 FIXED
$e addPoint 5406557 1074596
set jd1153 [$e addTechVia [V VIA34]]
$e newPath $jd1153 FIXED
$e addPoint 5406557 1074420
set jd1154 [$e addTechVia [V VIA23]]
$e newPath $jd1154 FIXED
$e addPoint 5406507 1074420
set jd1155 [$e addTechVia [V VIA12]]
$e newPath $jd1155 FIXED
$e addITerm [IT M10_4 Y]
$e newPath $emj1008 FIXED [RL M9]
set jd1156 [$e addTechVia [V {VIA89}]]
$e newPath $jd1156 FIXED [RL M8]
$e addPoint 5290040 1871820
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5290040 1871900
set jd1157 [$e addTechVia [V VIA67]]
$e newPath $jd1157 FIXED
$e addPoint 5290120 1871900
set jd1158 [$e addTechVia [V VIA56]]
$e newPath $jd1158 FIXED
$e addPoint 5290120 1871996
set jd1159 [$e addTechVia [V VIA45]]
$e newPath $jd1159 FIXED
$e addPoint 5290735 1871996
set jd1160 [$e addTechVia [V VIA34]]
$e newPath $jd1160 FIXED
$e addPoint 5290735 1871820
set jd1161 [$e addTechVia [V VIA23]]
$e newPath $jd1161 FIXED
$e addPoint 5290785 1871820
set jd1162 [$e addTechVia [V VIA12]]
$e newPath $jd1162 FIXED
$e addITerm [IT M10_5 Y]
$e newPath $emj1218 FIXED [RL M9]
set jd1163 [$e addTechVia [V {VIA89}]]
$e newPath $jd1163 FIXED [RL M8]
$e addPoint 5324200 1877940
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5324200 1878020
set jd1164 [$e addTechVia [V VIA67]]
$e newPath $jd1164 FIXED
$e addPoint 5324120 1878020
set jd1165 [$e addTechVia [V VIA56]]
$e newPath $jd1165 FIXED
$e addPoint 5324120 1878116
set jd1166 [$e addTechVia [V VIA45]]
$e newPath $jd1166 FIXED
$e addPoint 5323343 1878116
set jd1167 [$e addTechVia [V VIA34]]
$e newPath $jd1167 FIXED
$e addPoint 5323343 1877940
set jd1168 [$e addTechVia [V VIA23]]
$e newPath $jd1168 FIXED
$e addPoint 5323293 1877940
set jd1169 [$e addTechVia [V VIA12]]
$e newPath $jd1169 FIXED
$e addITerm [IT M10_6 Y]
$e newPath $emj1290 FIXED [RL M9]
set jd1170 [$e addTechVia [V {VIA89}]]
$e newPath $jd1170 FIXED [RL M8]
$e addPoint 5319880 2031840
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5319880 2031920
set jd1171 [$e addTechVia [V VIA67]]
$e newPath $jd1171 FIXED
$e addPoint 5319800 2031920
set jd1172 [$e addTechVia [V VIA56]]
$e newPath $jd1172 FIXED
$e addPoint 5319800 2032016
set jd1173 [$e addTechVia [V VIA45]]
$e newPath $jd1173 FIXED
$e addPoint 5318645 2032016
set jd1174 [$e addTechVia [V VIA34]]
$e newPath $jd1174 FIXED
$e addPoint 5318645 2031840
set jd1175 [$e addTechVia [V VIA23]]
$e newPath $jd1175 FIXED
$e addPoint 5318595 2031840
set jd1176 [$e addTechVia [V VIA12]]
$e newPath $jd1176 FIXED
$e addITerm [IT M10_7 Y]
$e newPath $emj1226 FIXED [RL M9]
set jd1177 [$e addTechVia [V {VIA89}]]
$e newPath $jd1177 FIXED [RL M8]
$e addPoint 5393720 2292660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5393720 2292740
set jd1178 [$e addTechVia [V VIA67]]
$e newPath $jd1178 FIXED
$e addPoint 5393800 2292740
set jd1179 [$e addTechVia [V VIA56]]
$e newPath $jd1179 FIXED
$e addPoint 5393800 2292836
set jd1180 [$e addTechVia [V VIA45]]
$e newPath $jd1180 FIXED
$e addPoint 5394253 2292836
set jd1181 [$e addTechVia [V VIA34]]
$e newPath $jd1181 FIXED
$e addPoint 5394253 2292660
set jd1182 [$e addTechVia [V VIA23]]
$e newPath $jd1182 FIXED
$e addPoint 5394303 2292660
set jd1183 [$e addTechVia [V VIA12]]
$e newPath $jd1183 FIXED
$e addITerm [IT M10_8 Y]
$e newPath $emj1730 FIXED [RL M9]
set jd1184 [$e addTechVia [V {VIA89}]]
$e newPath $jd1184 FIXED [RL M8]
$e addPoint 5432200 2567340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5432200 2567420
set jd1185 [$e addTechVia [V VIA67]]
$e newPath $jd1185 FIXED
$e addPoint 5432120 2567420
set jd1186 [$e addTechVia [V VIA56]]
$e newPath $jd1186 FIXED
$e addPoint 5432120 2567516
set jd1187 [$e addTechVia [V VIA45]]
$e newPath $jd1187 FIXED
$e addPoint 5432269 2567516
set jd1188 [$e addTechVia [V VIA34]]
$e newPath $jd1188 FIXED
$e addPoint 5432269 2567340
set jd1189 [$e addTechVia [V VIA23]]
$e newPath $jd1189 FIXED
$e addPoint 5432319 2567340
set jd1190 [$e addTechVia [V VIA12]]
$e newPath $jd1190 FIXED
$e addITerm [IT M10_9 Y]
$e newPath $emj1678 FIXED [RL M9]
set jd1191 [$e addTechVia [V {VIA89}]]
$e newPath $jd1191 FIXED [RL M8]
$e addPoint 5393720 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5393720 2832740
set jd1192 [$e addTechVia [V VIA67]]
$e newPath $jd1192 FIXED
$e addPoint 5393800 2832740
set jd1193 [$e addTechVia [V VIA56]]
$e newPath $jd1193 FIXED
$e addPoint 5393800 2832836
set jd1194 [$e addTechVia [V VIA45]]
$e newPath $jd1194 FIXED
$e addPoint 5394253 2832836
set jd1195 [$e addTechVia [V VIA34]]
$e newPath $jd1195 FIXED
$e addPoint 5394253 2832660
set jd1196 [$e addTechVia [V VIA23]]
$e newPath $jd1196 FIXED
$e addPoint 5394303 2832660
set jd1197 [$e addTechVia [V VIA12]]
$e newPath $jd1197 FIXED
$e addITerm [IT M10_10 Y]
$e newPath $emj1890 FIXED [RL M9]
set jd1198 [$e addTechVia [V {VIA89}]]
$e newPath $jd1198 FIXED [RL M8]
$e addPoint 5393720 3107340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5393720 3107420
set jd1199 [$e addTechVia [V VIA67]]
$e newPath $jd1199 FIXED
$e addPoint 5393800 3107420
set jd1200 [$e addTechVia [V VIA56]]
$e newPath $jd1200 FIXED
$e addPoint 5393800 3107516
set jd1201 [$e addTechVia [V VIA45]]
$e newPath $jd1201 FIXED
$e addPoint 5394253 3107516
set jd1202 [$e addTechVia [V VIA34]]
$e newPath $jd1202 FIXED
$e addPoint 5394253 3107340
set jd1203 [$e addTechVia [V VIA23]]
$e newPath $jd1203 FIXED
$e addPoint 5394303 3107340
set jd1204 [$e addTechVia [V VIA12]]
$e newPath $jd1204 FIXED
$e addITerm [IT M10_11 Y]
$e newPath $emj2004 FIXED [RL M9]
set jd1205 [$e addTechVia [V {VIA89}]]
$e newPath $jd1205 FIXED [RL M8]
$e addPoint 5393720 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5393720 3372740
set jd1206 [$e addTechVia [V VIA67]]
$e newPath $jd1206 FIXED
$e addPoint 5393800 3372740
set jd1207 [$e addTechVia [V VIA56]]
$e newPath $jd1207 FIXED
$e addPoint 5393800 3372836
set jd1208 [$e addTechVia [V VIA45]]
$e newPath $jd1208 FIXED
$e addPoint 5394253 3372836
set jd1209 [$e addTechVia [V VIA34]]
$e newPath $jd1209 FIXED
$e addPoint 5394253 3372660
set jd1210 [$e addTechVia [V VIA23]]
$e newPath $jd1210 FIXED
$e addPoint 5394303 3372660
set jd1211 [$e addTechVia [V VIA12]]
$e newPath $jd1211 FIXED
$e addITerm [IT M10_12 Y]
$e newPath $emj2176 FIXED [RL M9]
set jd1212 [$e addTechVia [V {VIA89}]]
$e newPath $jd1212 FIXED [RL M8]
$e addPoint 5393720 3647340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5393720 3647420
set jd1213 [$e addTechVia [V VIA67]]
$e newPath $jd1213 FIXED
$e addPoint 5393800 3647420
set jd1214 [$e addTechVia [V VIA56]]
$e newPath $jd1214 FIXED
$e addPoint 5393800 3647516
set jd1215 [$e addTechVia [V VIA45]]
$e newPath $jd1215 FIXED
$e addPoint 5394253 3647516
set jd1216 [$e addTechVia [V VIA34]]
$e newPath $jd1216 FIXED
$e addPoint 5394253 3647340
set jd1217 [$e addTechVia [V VIA23]]
$e newPath $jd1217 FIXED
$e addPoint 5394303 3647340
set jd1218 [$e addTechVia [V VIA12]]
$e newPath $jd1218 FIXED
$e addITerm [IT M10_13 Y]
$e newPath $emj2308 FIXED [RL M9]
set jd1219 [$e addTechVia [V {VIA89}]]
$e newPath $jd1219 FIXED [RL M8]
$e addPoint 5393720 3912660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5393720 3912740
set jd1220 [$e addTechVia [V VIA67]]
$e newPath $jd1220 FIXED
$e addPoint 5393800 3912740
set jd1221 [$e addTechVia [V VIA56]]
$e newPath $jd1221 FIXED
$e addPoint 5393800 3912836
set jd1222 [$e addTechVia [V VIA45]]
$e newPath $jd1222 FIXED
$e addPoint 5394253 3912836
set jd1223 [$e addTechVia [V VIA34]]
$e newPath $jd1223 FIXED
$e addPoint 5394253 3912660
set jd1224 [$e addTechVia [V VIA23]]
$e newPath $jd1224 FIXED
$e addPoint 5394303 3912660
set jd1225 [$e addTechVia [V VIA12]]
$e newPath $jd1225 FIXED
$e addITerm [IT M10_14 Y]
$e newPath $emj2345 FIXED [RL M9]
set jd1226 [$e addTechVia [V {VIA89}]]
$e newPath $jd1226 FIXED [RL M8]
$e addPoint 5393720 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5393720 4187420
set jd1227 [$e addTechVia [V VIA67]]
$e newPath $jd1227 FIXED
$e addPoint 5393800 4187420
set jd1228 [$e addTechVia [V VIA56]]
$e newPath $jd1228 FIXED
$e addPoint 5393800 4187516
set jd1229 [$e addTechVia [V VIA45]]
$e newPath $jd1229 FIXED
$e addPoint 5394253 4187516
set jd1230 [$e addTechVia [V VIA34]]
$e newPath $jd1230 FIXED
$e addPoint 5394253 4187340
set jd1231 [$e addTechVia [V VIA23]]
$e newPath $jd1231 FIXED
$e addPoint 5394303 4187340
set jd1232 [$e addTechVia [V VIA12]]
$e newPath $jd1232 FIXED
$e addITerm [IT M10_15 Y]
$e newPath $emj842 FIXED [RL M9]
set jd1233 [$e addTechVia [V {VIA89}]]
$e newPath $jd1233 FIXED [RL M8]
$e addPoint 5898760 20340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5898760 20420
set jd1234 [$e addTechVia [V VIA67]]
$e newPath $jd1234 FIXED
$e addPoint 5898680 20420
set jd1235 [$e addTechVia [V VIA56]]
$e newPath $jd1235 FIXED
$e addPoint 5898680 20516
set jd1236 [$e addTechVia [V VIA45]]
$e newPath $jd1236 FIXED
$e addPoint 5898497 20516
set jd1237 [$e addTechVia [V VIA34]]
$e newPath $jd1237 FIXED
$e addPoint 5898497 20340
set jd1238 [$e addTechVia [V VIA23]]
$e newPath $jd1238 FIXED
$e addPoint 5898447 20340
set jd1239 [$e addTechVia [V VIA12]]
$e newPath $jd1239 FIXED
$e addITerm [IT M11_0 Y]
$e newPath $emj586 FIXED [RL M9]
set jd1240 [$e addTechVia [V {VIA89}]]
$e newPath $jd1240 FIXED [RL M8]
$e addPoint 5682760 425160
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5682760 425240
set jd1241 [$e addTechVia [V VIA67]]
$e newPath $jd1241 FIXED
$e addPoint 5682680 425240
set jd1242 [$e addTechVia [V VIA56]]
$e newPath $jd1242 FIXED
$e addPoint 5682680 425336
set jd1243 [$e addTechVia [V VIA45]]
$e newPath $jd1243 FIXED
$e addPoint 5681309 425336
set jd1244 [$e addTechVia [V VIA34]]
$e newPath $jd1244 FIXED
$e addPoint 5681309 425160
set jd1245 [$e addTechVia [V VIA23]]
$e newPath $jd1245 FIXED
$e addPoint 5681259 425160
set jd1246 [$e addTechVia [V VIA12]]
$e newPath $jd1246 FIXED
$e addITerm [IT M11_1 Y]
$e newPath $emj841 FIXED [RL M9]
set jd1247 [$e addTechVia [V {VIA89}]]
$e newPath $jd1247 FIXED [RL M8]
$e addPoint 5907800 679500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 679580
set jd1248 [$e addTechVia [V VIA67]]
$e newPath $jd1248 FIXED
$e addPoint 5907880 679580
set jd1249 [$e addTechVia [V VIA56]]
$e newPath $jd1249 FIXED
$e addPoint 5907880 679676
set jd1250 [$e addTechVia [V VIA45]]
$e newPath $jd1250 FIXED
$e addPoint 5908873 679676
set jd1251 [$e addTechVia [V VIA34]]
$e newPath $jd1251 FIXED
$e addPoint 5908873 679500
set jd1252 [$e addTechVia [V VIA23]]
$e newPath $jd1252 FIXED
$e addPoint 5908923 679500
set jd1253 [$e addTechVia [V VIA12]]
$e newPath $jd1253 FIXED
$e addITerm [IT M11_2 Y]
$e newPath $emj1145 FIXED [RL M9]
set jd1254 [$e addTechVia [V {VIA89}]]
$e newPath $jd1254 FIXED [RL M8]
$e addPoint 5907800 947340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 947420
set jd1255 [$e addTechVia [V VIA67]]
$e newPath $jd1255 FIXED
$e addPoint 5907880 947420
set jd1256 [$e addTechVia [V VIA56]]
$e newPath $jd1256 FIXED
$e addPoint 5907880 947516
set jd1257 [$e addTechVia [V VIA45]]
$e newPath $jd1257 FIXED
$e addPoint 5908333 947516
set jd1258 [$e addTechVia [V VIA34]]
$e newPath $jd1258 FIXED
$e addPoint 5908333 947340
set jd1259 [$e addTechVia [V VIA23]]
$e newPath $jd1259 FIXED
$e addPoint 5908383 947340
set jd1260 [$e addTechVia [V VIA12]]
$e newPath $jd1260 FIXED
$e addITerm [IT M11_3 Y]
$e newPath $emj930 FIXED [RL M9]
set jd1261 [$e addTechVia [V {VIA89}]]
$e newPath $jd1261 FIXED [RL M8]
$e addPoint 5907800 1212660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 1212740
set jd1262 [$e addTechVia [V VIA67]]
$e newPath $jd1262 FIXED
$e addPoint 5907880 1212740
set jd1263 [$e addTechVia [V VIA56]]
$e newPath $jd1263 FIXED
$e addPoint 5907880 1212836
set jd1264 [$e addTechVia [V VIA45]]
$e newPath $jd1264 FIXED
$e addPoint 5908333 1212836
set jd1265 [$e addTechVia [V VIA34]]
$e newPath $jd1265 FIXED
$e addPoint 5908333 1212660
set jd1266 [$e addTechVia [V VIA23]]
$e newPath $jd1266 FIXED
$e addPoint 5908383 1212660
set jd1267 [$e addTechVia [V VIA12]]
$e newPath $jd1267 FIXED
$e addITerm [IT M11_4 Y]
$e newPath $emj1086 FIXED [RL M9]
set jd1268 [$e addTechVia [V {VIA89}]]
$e newPath $jd1268 FIXED [RL M8]
$e addPoint 5907800 1487340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 1487420
set jd1269 [$e addTechVia [V VIA67]]
$e newPath $jd1269 FIXED
$e addPoint 5907880 1487420
set jd1270 [$e addTechVia [V VIA56]]
$e newPath $jd1270 FIXED
$e addPoint 5907880 1487516
set jd1271 [$e addTechVia [V VIA45]]
$e newPath $jd1271 FIXED
$e addPoint 5908333 1487516
set jd1272 [$e addTechVia [V VIA34]]
$e newPath $jd1272 FIXED
$e addPoint 5908333 1487340
set jd1273 [$e addTechVia [V VIA23]]
$e newPath $jd1273 FIXED
$e addPoint 5908383 1487340
set jd1274 [$e addTechVia [V VIA12]]
$e newPath $jd1274 FIXED
$e addITerm [IT M11_5 Y]
$e newPath $emj1214 FIXED [RL M9]
set jd1275 [$e addTechVia [V {VIA89}]]
$e newPath $jd1275 FIXED [RL M8]
$e addPoint 5907800 1752660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 1752740
set jd1276 [$e addTechVia [V VIA67]]
$e newPath $jd1276 FIXED
$e addPoint 5907880 1752740
set jd1277 [$e addTechVia [V VIA56]]
$e newPath $jd1277 FIXED
$e addPoint 5907880 1752836
set jd1278 [$e addTechVia [V VIA45]]
$e newPath $jd1278 FIXED
$e addPoint 5908333 1752836
set jd1279 [$e addTechVia [V VIA34]]
$e newPath $jd1279 FIXED
$e addPoint 5908333 1752660
set jd1280 [$e addTechVia [V VIA23]]
$e newPath $jd1280 FIXED
$e addPoint 5908383 1752660
set jd1281 [$e addTechVia [V VIA12]]
$e newPath $jd1281 FIXED
$e addITerm [IT M11_6 Y]
$e newPath $emj1350 FIXED [RL M9]
set jd1282 [$e addTechVia [V {VIA89}]]
$e newPath $jd1282 FIXED [RL M8]
$e addPoint 5907800 2027340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 2027420
set jd1283 [$e addTechVia [V VIA67]]
$e newPath $jd1283 FIXED
$e addPoint 5907880 2027420
set jd1284 [$e addTechVia [V VIA56]]
$e newPath $jd1284 FIXED
$e addPoint 5907880 2027516
set jd1285 [$e addTechVia [V VIA45]]
$e newPath $jd1285 FIXED
$e addPoint 5908333 2027516
set jd1286 [$e addTechVia [V VIA34]]
$e newPath $jd1286 FIXED
$e addPoint 5908333 2027340
set jd1287 [$e addTechVia [V VIA23]]
$e newPath $jd1287 FIXED
$e addPoint 5908383 2027340
set jd1288 [$e addTechVia [V VIA12]]
$e newPath $jd1288 FIXED
$e addITerm [IT M11_7 Y]
$e newPath $emj1622 FIXED [RL M9]
set jd1289 [$e addTechVia [V {VIA89}]]
$e newPath $jd1289 FIXED [RL M8]
$e addPoint 5907800 2292660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 2292740
set jd1290 [$e addTechVia [V VIA67]]
$e newPath $jd1290 FIXED
$e addPoint 5907880 2292740
set jd1291 [$e addTechVia [V VIA56]]
$e newPath $jd1291 FIXED
$e addPoint 5907880 2292836
set jd1292 [$e addTechVia [V VIA45]]
$e newPath $jd1292 FIXED
$e addPoint 5908333 2292836
set jd1293 [$e addTechVia [V VIA34]]
$e newPath $jd1293 FIXED
$e addPoint 5908333 2292660
set jd1294 [$e addTechVia [V VIA23]]
$e newPath $jd1294 FIXED
$e addPoint 5908383 2292660
set jd1295 [$e addTechVia [V VIA12]]
$e newPath $jd1295 FIXED
$e addITerm [IT M11_8 Y]
$e newPath $emj1773 FIXED [RL M9]
set jd1296 [$e addTechVia [V {VIA89}]]
$e newPath $jd1296 FIXED [RL M8]
$e addPoint 5907800 2567340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 2567420
set jd1297 [$e addTechVia [V VIA67]]
$e newPath $jd1297 FIXED
$e addPoint 5907880 2567420
set jd1298 [$e addTechVia [V VIA56]]
$e newPath $jd1298 FIXED
$e addPoint 5907880 2567516
set jd1299 [$e addTechVia [V VIA45]]
$e newPath $jd1299 FIXED
$e addPoint 5908333 2567516
set jd1300 [$e addTechVia [V VIA34]]
$e newPath $jd1300 FIXED
$e addPoint 5908333 2567340
set jd1301 [$e addTechVia [V VIA23]]
$e newPath $jd1301 FIXED
$e addPoint 5908383 2567340
set jd1302 [$e addTechVia [V VIA12]]
$e newPath $jd1302 FIXED
$e addITerm [IT M11_9 Y]
$e newPath $emj1883 FIXED [RL M9]
set jd1303 [$e addTechVia [V {VIA89}]]
$e newPath $jd1303 FIXED [RL M8]
$e addPoint 5907800 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 2832740
set jd1304 [$e addTechVia [V VIA67]]
$e newPath $jd1304 FIXED
$e addPoint 5907880 2832740
set jd1305 [$e addTechVia [V VIA56]]
$e newPath $jd1305 FIXED
$e addPoint 5907880 2832836
set jd1306 [$e addTechVia [V VIA45]]
$e newPath $jd1306 FIXED
$e addPoint 5908333 2832836
set jd1307 [$e addTechVia [V VIA34]]
$e newPath $jd1307 FIXED
$e addPoint 5908333 2832660
set jd1308 [$e addTechVia [V VIA23]]
$e newPath $jd1308 FIXED
$e addPoint 5908383 2832660
set jd1309 [$e addTechVia [V VIA12]]
$e newPath $jd1309 FIXED
$e addITerm [IT M11_10 Y]
$e newPath $emj2047 FIXED [RL M9]
set jd1310 [$e addTechVia [V {VIA89}]]
$e newPath $jd1310 FIXED [RL M8]
$e addPoint 5907800 3107340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 3107420
set jd1311 [$e addTechVia [V VIA67]]
$e newPath $jd1311 FIXED
$e addPoint 5907880 3107420
set jd1312 [$e addTechVia [V VIA56]]
$e newPath $jd1312 FIXED
$e addPoint 5907880 3107516
set jd1313 [$e addTechVia [V VIA45]]
$e newPath $jd1313 FIXED
$e addPoint 5908333 3107516
set jd1314 [$e addTechVia [V VIA34]]
$e newPath $jd1314 FIXED
$e addPoint 5908333 3107340
set jd1315 [$e addTechVia [V VIA23]]
$e newPath $jd1315 FIXED
$e addPoint 5908383 3107340
set jd1316 [$e addTechVia [V VIA12]]
$e newPath $jd1316 FIXED
$e addITerm [IT M11_11 Y]
$e newPath $emj2203 FIXED [RL M9]
set jd1317 [$e addTechVia [V {VIA89}]]
$e newPath $jd1317 FIXED [RL M8]
$e addPoint 5907800 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 3372740
set jd1318 [$e addTechVia [V VIA67]]
$e newPath $jd1318 FIXED
$e addPoint 5907880 3372740
set jd1319 [$e addTechVia [V VIA56]]
$e newPath $jd1319 FIXED
$e addPoint 5907880 3372836
set jd1320 [$e addTechVia [V VIA45]]
$e newPath $jd1320 FIXED
$e addPoint 5908333 3372836
set jd1321 [$e addTechVia [V VIA34]]
$e newPath $jd1321 FIXED
$e addPoint 5908333 3372660
set jd1322 [$e addTechVia [V VIA23]]
$e newPath $jd1322 FIXED
$e addPoint 5908383 3372660
set jd1323 [$e addTechVia [V VIA12]]
$e newPath $jd1323 FIXED
$e addITerm [IT M11_12 Y]
$e newPath $emj2306 FIXED [RL M9]
set jd1324 [$e addTechVia [V {VIA89}]]
$e newPath $jd1324 FIXED [RL M8]
$e addPoint 5812360 3653460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5812360 3653540
set jd1325 [$e addTechVia [V VIA67]]
$e newPath $jd1325 FIXED
$e addPoint 5812280 3653540
set jd1326 [$e addTechVia [V VIA56]]
$e newPath $jd1326 FIXED
$e addPoint 5812280 3653636
set jd1327 [$e addTechVia [V VIA45]]
$e newPath $jd1327 FIXED
$e addPoint 5810801 3653636
set jd1328 [$e addTechVia [V VIA34]]
$e newPath $jd1328 FIXED
$e addPoint 5810801 3653460
set jd1329 [$e addTechVia [V VIA23]]
$e newPath $jd1329 FIXED
$e addPoint 5810751 3653460
set jd1330 [$e addTechVia [V VIA12]]
$e newPath $jd1330 FIXED
$e addITerm [IT M11_13 Y]
$e newPath $emj2340 FIXED [RL M9]
set jd1331 [$e addTechVia [V {VIA89}]]
$e newPath $jd1331 FIXED [RL M8]
$e addPoint 5907800 3912660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 3912740
set jd1332 [$e addTechVia [V VIA67]]
$e newPath $jd1332 FIXED
$e addPoint 5907880 3912740
set jd1333 [$e addTechVia [V VIA56]]
$e newPath $jd1333 FIXED
$e addPoint 5907880 3912836
set jd1334 [$e addTechVia [V VIA45]]
$e newPath $jd1334 FIXED
$e addPoint 5908333 3912836
set jd1335 [$e addTechVia [V VIA34]]
$e newPath $jd1335 FIXED
$e addPoint 5908333 3912660
set jd1336 [$e addTechVia [V VIA23]]
$e newPath $jd1336 FIXED
$e addPoint 5908383 3912660
set jd1337 [$e addTechVia [V VIA12]]
$e newPath $jd1337 FIXED
$e addITerm [IT M11_14 Y]
$e newPath $emj2373 FIXED [RL M9]
set jd1338 [$e addTechVia [V {VIA89}]]
$e newPath $jd1338 FIXED [RL M8]
$e addPoint 5907800 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907800 4187420
set jd1339 [$e addTechVia [V VIA67]]
$e newPath $jd1339 FIXED
$e addPoint 5907880 4187420
set jd1340 [$e addTechVia [V VIA56]]
$e newPath $jd1340 FIXED
$e addPoint 5907880 4187516
set jd1341 [$e addTechVia [V VIA45]]
$e newPath $jd1341 FIXED
$e addPoint 5908333 4187516
set jd1342 [$e addTechVia [V VIA34]]
$e newPath $jd1342 FIXED
$e addPoint 5908333 4187340
set jd1343 [$e addTechVia [V VIA23]]
$e newPath $jd1343 FIXED
$e addPoint 5908383 4187340
set jd1344 [$e addTechVia [V VIA12]]
$e newPath $jd1344 FIXED
$e addITerm [IT M11_15 Y]
$e newPath $emj987 FIXED [RL M9]
set jd1345 [$e addTechVia [V {VIA89}]]
$e newPath $jd1345 FIXED [RL M8]
$e addPoint 6469000 132660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6469000 132740
set jd1346 [$e addTechVia [V VIA67]]
$e newPath $jd1346 FIXED
$e addPoint 6468920 132740
set jd1347 [$e addTechVia [V VIA56]]
$e newPath $jd1347 FIXED
$e addPoint 6468920 132836
set jd1348 [$e addTechVia [V VIA45]]
$e newPath $jd1348 FIXED
$e addPoint 6468197 132836
set jd1349 [$e addTechVia [V VIA34]]
$e newPath $jd1349 FIXED
$e addPoint 6468197 132660
set jd1350 [$e addTechVia [V VIA23]]
$e newPath $jd1350 FIXED
$e addPoint 6468147 132660
set jd1351 [$e addTechVia [V VIA12]]
$e newPath $jd1351 FIXED
$e addITerm [IT M12_0 Y]
$e newPath $emj764 FIXED [RL M9]
set jd1352 [$e addTechVia [V {VIA89}]]
$e newPath $jd1352 FIXED [RL M8]
$e addPoint 6469000 409140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6469000 409220
set jd1353 [$e addTechVia [V VIA67]]
$e newPath $jd1353 FIXED
$e addPoint 6468920 409220
set jd1354 [$e addTechVia [V VIA56]]
$e newPath $jd1354 FIXED
$e addPoint 6468920 409316
set jd1355 [$e addTechVia [V VIA45]]
$e newPath $jd1355 FIXED
$e addPoint 6467981 409316
set jd1356 [$e addTechVia [V VIA34]]
$e newPath $jd1356 FIXED
$e addPoint 6467981 409140
set jd1357 [$e addTechVia [V VIA23]]
$e newPath $jd1357 FIXED
$e addPoint 6467931 409140
set jd1358 [$e addTechVia [V VIA12]]
$e newPath $jd1358 FIXED
$e addITerm [IT M12_1 Y]
$e newPath $emj913 FIXED [RL M9]
set jd1359 [$e addTechVia [V {VIA89}]]
$e newPath $jd1359 FIXED [RL M8]
$e addPoint 6417560 679500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6417560 679580
set jd1360 [$e addTechVia [V VIA67]]
$e newPath $jd1360 FIXED
$e addPoint 6417640 679580
set jd1361 [$e addTechVia [V VIA56]]
$e newPath $jd1361 FIXED
$e addPoint 6417640 679676
set jd1362 [$e addTechVia [V VIA45]]
$e newPath $jd1362 FIXED
$e addPoint 6418633 679676
set jd1363 [$e addTechVia [V VIA34]]
$e newPath $jd1363 FIXED
$e addPoint 6418633 679500
set jd1364 [$e addTechVia [V VIA23]]
$e newPath $jd1364 FIXED
$e addPoint 6418683 679500
set jd1365 [$e addTechVia [V VIA12]]
$e newPath $jd1365 FIXED
$e addITerm [IT M12_2 Y]
$e newPath $emj1144 FIXED [RL M9]
set jd1366 [$e addTechVia [V {VIA89}]]
$e newPath $jd1366 FIXED [RL M8]
$e addPoint 6387320 832500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6387320 832580
set jd1367 [$e addTechVia [V VIA67]]
$e newPath $jd1367 FIXED
$e addPoint 6387400 832580
set jd1368 [$e addTechVia [V VIA56]]
$e newPath $jd1368 FIXED
$e addPoint 6387400 832676
set jd1369 [$e addTechVia [V VIA45]]
$e newPath $jd1369 FIXED
$e addPoint 6388069 832676
set jd1370 [$e addTechVia [V VIA34]]
$e newPath $jd1370 FIXED
$e addPoint 6388069 832500
set jd1371 [$e addTechVia [V VIA23]]
$e newPath $jd1371 FIXED
$e addPoint 6388119 832500
set jd1372 [$e addTechVia [V VIA12]]
$e newPath $jd1372 FIXED
$e addITerm [IT M12_3 Y]
$e newPath $emj1001 FIXED [RL M9]
set jd1373 [$e addTechVia [V {VIA89}]]
$e newPath $jd1373 FIXED [RL M8]
$e addPoint 6421880 1246680
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6421880 1246760
set jd1374 [$e addTechVia [V VIA67]]
$e newPath $jd1374 FIXED
$e addPoint 6421960 1246760
set jd1375 [$e addTechVia [V VIA56]]
$e newPath $jd1375 FIXED
$e addPoint 6421960 1246856
set jd1376 [$e addTechVia [V VIA45]]
$e newPath $jd1376 FIXED
$e addPoint 6423655 1246856
set jd1377 [$e addTechVia [V VIA34]]
$e newPath $jd1377 FIXED
$e addPoint 6423655 1246680
set jd1378 [$e addTechVia [V VIA23]]
$e newPath $jd1378 FIXED
$e addPoint 6423705 1246680
set jd1379 [$e addTechVia [V VIA12]]
$e newPath $jd1379 FIXED
$e addITerm [IT M12_4 Y]
$e newPath $emj1209 FIXED [RL M9]
set jd1380 [$e addTechVia [V {VIA89}]]
$e newPath $jd1380 FIXED [RL M8]
$e addPoint 6417560 1487340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6417560 1487420
set jd1381 [$e addTechVia [V VIA67]]
$e newPath $jd1381 FIXED
$e addPoint 6417640 1487420
set jd1382 [$e addTechVia [V VIA56]]
$e newPath $jd1382 FIXED
$e addPoint 6417640 1487516
set jd1383 [$e addTechVia [V VIA45]]
$e newPath $jd1383 FIXED
$e addPoint 6418093 1487516
set jd1384 [$e addTechVia [V VIA34]]
$e newPath $jd1384 FIXED
$e addPoint 6418093 1487340
set jd1385 [$e addTechVia [V VIA23]]
$e newPath $jd1385 FIXED
$e addPoint 6418143 1487340
set jd1386 [$e addTechVia [V VIA12]]
$e newPath $jd1386 FIXED
$e addITerm [IT M12_5 Y]
$e newPath $emj1414 FIXED [RL M9]
set jd1387 [$e addTechVia [V {VIA89}]]
$e newPath $jd1387 FIXED [RL M8]
$e addPoint 6296200 1812600
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6296200 1812680
set jd1388 [$e addTechVia [V VIA67]]
$e newPath $jd1388 FIXED
$e addPoint 6296120 1812680
set jd1389 [$e addTechVia [V VIA56]]
$e newPath $jd1389 FIXED
$e addPoint 6296120 1812776
set jd1390 [$e addTechVia [V VIA45]]
$e newPath $jd1390 FIXED
$e addPoint 6294911 1812776
set jd1391 [$e addTechVia [V VIA34]]
$e newPath $jd1391 FIXED
$e addPoint 6294911 1812600
set jd1392 [$e addTechVia [V VIA23]]
$e newPath $jd1392 FIXED
$e addPoint 6294861 1812600
set jd1393 [$e addTechVia [V VIA12]]
$e newPath $jd1393 FIXED
$e addITerm [IT M12_6 Y]
$e newPath $emj1549 FIXED [RL M9]
set jd1394 [$e addTechVia [V {VIA89}]]
$e newPath $jd1394 FIXED [RL M8]
$e addPoint 6417560 2027340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6417560 2027420
set jd1395 [$e addTechVia [V VIA67]]
$e newPath $jd1395 FIXED
$e addPoint 6417640 2027420
set jd1396 [$e addTechVia [V VIA56]]
$e newPath $jd1396 FIXED
$e addPoint 6417640 2027516
set jd1397 [$e addTechVia [V VIA45]]
$e newPath $jd1397 FIXED
$e addPoint 6418093 2027516
set jd1398 [$e addTechVia [V VIA34]]
$e newPath $jd1398 FIXED
$e addPoint 6418093 2027340
set jd1399 [$e addTechVia [V VIA23]]
$e newPath $jd1399 FIXED
$e addPoint 6418143 2027340
set jd1400 [$e addTechVia [V VIA12]]
$e newPath $jd1400 FIXED
$e addITerm [IT M12_7 Y]
$e newPath $emj1724 FIXED [RL M9]
set jd1401 [$e addTechVia [V {VIA89}]]
$e newPath $jd1401 FIXED [RL M8]
$e addPoint 6404600 2249460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6404600 2249540
set jd1402 [$e addTechVia [V VIA67]]
$e newPath $jd1402 FIXED
$e addPoint 6404680 2249540
set jd1403 [$e addTechVia [V VIA56]]
$e newPath $jd1403 FIXED
$e addPoint 6404680 2249636
set jd1404 [$e addTechVia [V VIA45]]
$e newPath $jd1404 FIXED
$e addPoint 6406213 2249636
set jd1405 [$e addTechVia [V VIA34]]
$e newPath $jd1405 FIXED
$e addPoint 6406213 2249460
set jd1406 [$e addTechVia [V VIA23]]
$e newPath $jd1406 FIXED
$e addPoint 6406263 2249460
set jd1407 [$e addTechVia [V VIA12]]
$e newPath $jd1407 FIXED
$e addITerm [IT M12_8 Y]
$e newPath $emj1992 FIXED [RL M9]
set jd1408 [$e addTechVia [V {VIA89}]]
$e newPath $jd1408 FIXED [RL M8]
$e addPoint 6434840 2663640
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6434840 2663720
set jd1409 [$e addTechVia [V VIA67]]
$e newPath $jd1409 FIXED
$e addPoint 6434920 2663720
set jd1410 [$e addTechVia [V VIA56]]
$e newPath $jd1410 FIXED
$e addPoint 6434920 2663816
set jd1411 [$e addTechVia [V VIA45]]
$e newPath $jd1411 FIXED
$e addPoint 6435481 2663816
set jd1412 [$e addTechVia [V VIA34]]
$e newPath $jd1412 FIXED
$e addPoint 6435481 2663640
set jd1413 [$e addTechVia [V VIA23]]
$e newPath $jd1413 FIXED
$e addPoint 6435531 2663640
set jd1414 [$e addTechVia [V VIA12]]
$e newPath $jd1414 FIXED
$e addITerm [IT M12_9 Y]
$e newPath $emj2039 FIXED [RL M9]
set jd1415 [$e addTechVia [V {VIA89}]]
$e newPath $jd1415 FIXED [RL M8]
$e addPoint 6417560 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6417560 2832740
set jd1416 [$e addTechVia [V VIA67]]
$e newPath $jd1416 FIXED
$e addPoint 6417640 2832740
set jd1417 [$e addTechVia [V VIA56]]
$e newPath $jd1417 FIXED
$e addPoint 6417640 2832836
set jd1418 [$e addTechVia [V VIA45]]
$e newPath $jd1418 FIXED
$e addPoint 6418093 2832836
set jd1419 [$e addTechVia [V VIA34]]
$e newPath $jd1419 FIXED
$e addPoint 6418093 2832660
set jd1420 [$e addTechVia [V VIA23]]
$e newPath $jd1420 FIXED
$e addPoint 6418143 2832660
set jd1421 [$e addTechVia [V VIA12]]
$e newPath $jd1421 FIXED
$e addITerm [IT M12_10 Y]
$e newPath $emj2046 FIXED [RL M9]
set jd1422 [$e addTechVia [V {VIA89}]]
$e newPath $jd1422 FIXED [RL M8]
$e addPoint 6296200 3163500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6296200 3163580
set jd1423 [$e addTechVia [V VIA67]]
$e newPath $jd1423 FIXED
$e addPoint 6296120 3163580
set jd1424 [$e addTechVia [V VIA56]]
$e newPath $jd1424 FIXED
$e addPoint 6296120 3163676
set jd1425 [$e addTechVia [V VIA45]]
$e newPath $jd1425 FIXED
$e addPoint 6294911 3163676
set jd1426 [$e addTechVia [V VIA34]]
$e newPath $jd1426 FIXED
$e addPoint 6294911 3163500
set jd1427 [$e addTechVia [V VIA23]]
$e newPath $jd1427 FIXED
$e addPoint 6294861 3163500
set jd1428 [$e addTechVia [V VIA12]]
$e newPath $jd1428 FIXED
$e addITerm [IT M12_11 Y]
$e newPath $emj2168 FIXED [RL M9]
set jd1429 [$e addTechVia [V {VIA89}]]
$e newPath $jd1429 FIXED [RL M8]
$e addPoint 6417560 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6417560 3372740
set jd1430 [$e addTechVia [V VIA67]]
$e newPath $jd1430 FIXED
$e addPoint 6417640 3372740
set jd1431 [$e addTechVia [V VIA56]]
$e newPath $jd1431 FIXED
$e addPoint 6417640 3372836
set jd1432 [$e addTechVia [V VIA45]]
$e newPath $jd1432 FIXED
$e addPoint 6418093 3372836
set jd1433 [$e addTechVia [V VIA34]]
$e newPath $jd1433 FIXED
$e addPoint 6418093 3372660
set jd1434 [$e addTechVia [V VIA23]]
$e newPath $jd1434 FIXED
$e addPoint 6418143 3372660
set jd1435 [$e addTechVia [V VIA12]]
$e newPath $jd1435 FIXED
$e addITerm [IT M12_12 Y]
$e newPath $emj2386 FIXED [RL M9]
set jd1436 [$e addTechVia [V {VIA89}]]
$e newPath $jd1436 FIXED [RL M8]
$e addPoint 6400280 3545460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6400280 3545540
set jd1437 [$e addTechVia [V VIA67]]
$e newPath $jd1437 FIXED
$e addPoint 6400360 3545540
set jd1438 [$e addTechVia [V VIA56]]
$e newPath $jd1438 FIXED
$e addPoint 6400360 3545636
set jd1439 [$e addTechVia [V VIA45]]
$e newPath $jd1439 FIXED
$e addPoint 6400705 3545636
set jd1440 [$e addTechVia [V VIA34]]
$e newPath $jd1440 FIXED
$e addPoint 6400705 3545460
set jd1441 [$e addTechVia [V VIA23]]
$e newPath $jd1441 FIXED
$e addPoint 6400755 3545460
set jd1442 [$e addTechVia [V VIA12]]
$e newPath $jd1442 FIXED
$e addITerm [IT M12_13 Y]
$e newPath $emj2339 FIXED [RL M9]
set jd1443 [$e addTechVia [V {VIA89}]]
$e newPath $jd1443 FIXED [RL M8]
$e addPoint 6140680 3938580
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6140680 3938660
set jd1444 [$e addTechVia [V VIA67]]
$e newPath $jd1444 FIXED
$e addPoint 6140600 3938660
set jd1445 [$e addTechVia [V VIA56]]
$e newPath $jd1445 FIXED
$e addPoint 6140600 3938756
set jd1446 [$e addTechVia [V VIA45]]
$e newPath $jd1446 FIXED
$e addPoint 6139283 3938756
set jd1447 [$e addTechVia [V VIA34]]
$e newPath $jd1447 FIXED
$e addPoint 6139283 3938580
set jd1448 [$e addTechVia [V VIA23]]
$e newPath $jd1448 FIXED
$e addPoint 6139233 3938580
set jd1449 [$e addTechVia [V VIA12]]
$e newPath $jd1449 FIXED
$e addITerm [IT M12_14 Y]
$e newPath $emj2450 FIXED [RL M9]
set jd1450 [$e addTechVia [V {VIA89}]]
$e newPath $jd1450 FIXED [RL M8]
$e addPoint 6421880 4202100
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6421880 4202180
set jd1451 [$e addTechVia [V VIA67]]
$e newPath $jd1451 FIXED
$e addPoint 6421960 4202180
set jd1452 [$e addTechVia [V VIA56]]
$e newPath $jd1452 FIXED
$e addPoint 6421960 4202276
set jd1453 [$e addTechVia [V VIA45]]
$e newPath $jd1453 FIXED
$e addPoint 6422737 4202276
set jd1454 [$e addTechVia [V VIA34]]
$e newPath $jd1454 FIXED
$e addPoint 6422737 4202100
set jd1455 [$e addTechVia [V VIA23]]
$e newPath $jd1455 FIXED
$e addPoint 6422787 4202100
set jd1456 [$e addTechVia [V VIA12]]
$e newPath $jd1456 FIXED
$e addITerm [IT M12_15 Y]
$e newPath $emj1069 FIXED [RL M9]
set jd1457 [$e addTechVia [V {VIA89}]]
$e newPath $jd1457 FIXED [RL M8]
$e addPoint 6931640 132660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6931640 132740
set jd1458 [$e addTechVia [V VIA67]]
$e newPath $jd1458 FIXED
$e addPoint 6931720 132740
set jd1459 [$e addTechVia [V VIA56]]
$e newPath $jd1459 FIXED
$e addPoint 6931720 132836
set jd1460 [$e addTechVia [V VIA45]]
$e newPath $jd1460 FIXED
$e addPoint 6932173 132836
set jd1461 [$e addTechVia [V VIA34]]
$e newPath $jd1461 FIXED
$e addPoint 6932173 132660
set jd1462 [$e addTechVia [V VIA23]]
$e newPath $jd1462 FIXED
$e addPoint 6932223 132660
set jd1463 [$e addTechVia [V VIA12]]
$e newPath $jd1463 FIXED
$e addITerm [IT M13_0 Y]
$e newPath $emj834 FIXED [RL M9]
set jd1464 [$e addTechVia [V {VIA89}]]
$e newPath $jd1464 FIXED [RL M8]
$e addPoint 6892360 412380
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6892360 412460
set jd1465 [$e addTechVia [V VIA67]]
$e newPath $jd1465 FIXED
$e addPoint 6892280 412460
set jd1466 [$e addTechVia [V VIA56]]
$e newPath $jd1466 FIXED
$e addPoint 6892280 412556
set jd1467 [$e addTechVia [V VIA45]]
$e newPath $jd1467 FIXED
$e addPoint 6890909 412556
set jd1468 [$e addTechVia [V VIA34]]
$e newPath $jd1468 FIXED
$e addPoint 6890909 412380
set jd1469 [$e addTechVia [V VIA23]]
$e newPath $jd1469 FIXED
$e addPoint 6890859 412380
set jd1470 [$e addTechVia [V VIA12]]
$e newPath $jd1470 FIXED
$e addITerm [IT M13_1 Y]
$e newPath $emj1332 FIXED [RL M9]
set jd1471 [$e addTechVia [V {VIA89}]]
$e newPath $jd1471 FIXED [RL M8]
$e addPoint 6892360 689940
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6892360 690020
set jd1472 [$e addTechVia [V VIA67]]
$e newPath $jd1472 FIXED
$e addPoint 6892280 690020
set jd1473 [$e addTechVia [V VIA56]]
$e newPath $jd1473 FIXED
$e addPoint 6892280 690116
set jd1474 [$e addTechVia [V VIA45]]
$e newPath $jd1474 FIXED
$e addPoint 6890909 690116
set jd1475 [$e addTechVia [V VIA34]]
$e newPath $jd1475 FIXED
$e addPoint 6890909 689940
set jd1476 [$e addTechVia [V VIA23]]
$e newPath $jd1476 FIXED
$e addPoint 6890859 689940
set jd1477 [$e addTechVia [V VIA12]]
$e newPath $jd1477 FIXED
$e addITerm [IT M13_2 Y]
$e newPath $emj1338 FIXED [RL M9]
set jd1478 [$e addTechVia [V {VIA89}]]
$e newPath $jd1478 FIXED [RL M8]
$e addPoint 7013720 1043100
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7013720 1043180
set jd1479 [$e addTechVia [V VIA67]]
$e newPath $jd1479 FIXED
$e addPoint 7013800 1043180
set jd1480 [$e addTechVia [V VIA56]]
$e newPath $jd1480 FIXED
$e addPoint 7013800 1043276
set jd1481 [$e addTechVia [V VIA45]]
$e newPath $jd1481 FIXED
$e addPoint 7014469 1043276
set jd1482 [$e addTechVia [V VIA34]]
$e newPath $jd1482 FIXED
$e addPoint 7014469 1043100
set jd1483 [$e addTechVia [V VIA23]]
$e newPath $jd1483 FIXED
$e addPoint 7014519 1043100
set jd1484 [$e addTechVia [V VIA12]]
$e newPath $jd1484 FIXED
$e addITerm [IT M13_3 Y]
$e newPath $emj1208 FIXED [RL M9]
set jd1485 [$e addTechVia [V {VIA89}]]
$e newPath $jd1485 FIXED [RL M8]
$e addPoint 6926920 1189260
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6926920 1189340
set jd1486 [$e addTechVia [V VIA67]]
$e newPath $jd1486 FIXED
$e addPoint 6926840 1189340
set jd1487 [$e addTechVia [V VIA56]]
$e newPath $jd1487 FIXED
$e addPoint 6926840 1189436
set jd1488 [$e addTechVia [V VIA45]]
$e newPath $jd1488 FIXED
$e addPoint 6925037 1189436
set jd1489 [$e addTechVia [V VIA34]]
$e newPath $jd1489 FIXED
$e addPoint 6925037 1189260
set jd1490 [$e addTechVia [V VIA23]]
$e newPath $jd1490 FIXED
$e addPoint 6924987 1189260
set jd1491 [$e addTechVia [V VIA12]]
$e newPath $jd1491 FIXED
$e addITerm [IT M13_4 Y]
$e newPath $emj1284 FIXED [RL M9]
set jd1492 [$e addTechVia [V {VIA89}]]
$e newPath $jd1492 FIXED [RL M8]
$e addPoint 6659080 1509120
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6659080 1509200
set jd1493 [$e addTechVia [V VIA67]]
$e newPath $jd1493 FIXED
$e addPoint 6659000 1509200
set jd1494 [$e addTechVia [V VIA56]]
$e newPath $jd1494 FIXED
$e addPoint 6659000 1509296
set jd1495 [$e addTechVia [V VIA45]]
$e newPath $jd1495 FIXED
$e addPoint 6657305 1509296
set jd1496 [$e addTechVia [V VIA34]]
$e newPath $jd1496 FIXED
$e addPoint 6657305 1509120
set jd1497 [$e addTechVia [V VIA23]]
$e newPath $jd1497 FIXED
$e addPoint 6657255 1509120
set jd1498 [$e addTechVia [V VIA12]]
$e newPath $jd1498 FIXED
$e addITerm [IT M13_5 Y]
$e newPath $emj1707 FIXED [RL M9]
set jd1499 [$e addTechVia [V {VIA89}]]
$e newPath $jd1499 FIXED [RL M8]
$e addPoint 6659080 1778580
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6659080 1778660
set jd1500 [$e addTechVia [V VIA67]]
$e newPath $jd1500 FIXED
$e addPoint 6659000 1778660
set jd1501 [$e addTechVia [V VIA56]]
$e newPath $jd1501 FIXED
$e addPoint 6659000 1778756
set jd1502 [$e addTechVia [V VIA45]]
$e newPath $jd1502 FIXED
$e addPoint 6657305 1778756
set jd1503 [$e addTechVia [V VIA34]]
$e newPath $jd1503 FIXED
$e addPoint 6657305 1778580
set jd1504 [$e addTechVia [V VIA23]]
$e newPath $jd1504 FIXED
$e addPoint 6657255 1778580
set jd1505 [$e addTechVia [V VIA12]]
$e newPath $jd1505 FIXED
$e addITerm [IT M13_6 Y]
$e newPath $emj1556 FIXED [RL M9]
set jd1506 [$e addTechVia [V {VIA89}]]
$e newPath $jd1506 FIXED [RL M8]
$e addPoint 6659080 2049120
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6659080 2049200
set jd1507 [$e addTechVia [V VIA67]]
$e newPath $jd1507 FIXED
$e addPoint 6659000 2049200
set jd1508 [$e addTechVia [V VIA56]]
$e newPath $jd1508 FIXED
$e addPoint 6659000 2049296
set jd1509 [$e addTechVia [V VIA45]]
$e newPath $jd1509 FIXED
$e addPoint 6657305 2049296
set jd1510 [$e addTechVia [V VIA34]]
$e newPath $jd1510 FIXED
$e addPoint 6657305 2049120
set jd1511 [$e addTechVia [V VIA23]]
$e newPath $jd1511 FIXED
$e addPoint 6657255 2049120
set jd1512 [$e addTechVia [V VIA12]]
$e newPath $jd1512 FIXED
$e addITerm [IT M13_7 Y]
$e newPath $emj1928 FIXED [RL M9]
set jd1513 [$e addTechVia [V {VIA89}]]
$e newPath $jd1513 FIXED [RL M8]
$e addPoint 6659080 2318580
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6659080 2318660
set jd1514 [$e addTechVia [V VIA67]]
$e newPath $jd1514 FIXED
$e addPoint 6659000 2318660
set jd1515 [$e addTechVia [V VIA56]]
$e newPath $jd1515 FIXED
$e addPoint 6659000 2318756
set jd1516 [$e addTechVia [V VIA45]]
$e newPath $jd1516 FIXED
$e addPoint 6657305 2318756
set jd1517 [$e addTechVia [V VIA34]]
$e newPath $jd1517 FIXED
$e addPoint 6657305 2318580
set jd1518 [$e addTechVia [V VIA23]]
$e newPath $jd1518 FIXED
$e addPoint 6657255 2318580
set jd1519 [$e addTechVia [V VIA12]]
$e newPath $jd1519 FIXED
$e addITerm [IT M13_8 Y]
$e newPath $emj1990 FIXED [RL M9]
set jd1520 [$e addTechVia [V {VIA89}]]
$e newPath $jd1520 FIXED [RL M8]
$e addPoint 6957160 2832120
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6957160 2832200
set jd1521 [$e addTechVia [V VIA67]]
$e newPath $jd1521 FIXED
$e addPoint 6957080 2832200
set jd1522 [$e addTechVia [V VIA56]]
$e newPath $jd1522 FIXED
$e addPoint 6957080 2832296
set jd1523 [$e addTechVia [V VIA45]]
$e newPath $jd1523 FIXED
$e addPoint 6955655 2832296
set jd1524 [$e addTechVia [V VIA34]]
$e newPath $jd1524 FIXED
$e addPoint 6955655 2832120
set jd1525 [$e addTechVia [V VIA23]]
$e newPath $jd1525 FIXED
$e addPoint 6955605 2832120
set jd1526 [$e addTechVia [V VIA12]]
$e newPath $jd1526 FIXED
$e addITerm [IT M13_9 Y]
$e newPath $emj1936 FIXED [RL M9]
set jd1527 [$e addTechVia [V {VIA89}]]
$e newPath $jd1527 FIXED [RL M8]
$e addPoint 6931640 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6931640 2832740
set jd1528 [$e addTechVia [V VIA67]]
$e newPath $jd1528 FIXED
$e addPoint 6931720 2832740
set jd1529 [$e addTechVia [V VIA56]]
$e newPath $jd1529 FIXED
$e addPoint 6931720 2832836
set jd1530 [$e addTechVia [V VIA45]]
$e newPath $jd1530 FIXED
$e addPoint 6932173 2832836
set jd1531 [$e addTechVia [V VIA34]]
$e newPath $jd1531 FIXED
$e addPoint 6932173 2832660
set jd1532 [$e addTechVia [V VIA23]]
$e newPath $jd1532 FIXED
$e addPoint 6932223 2832660
set jd1533 [$e addTechVia [V VIA12]]
$e newPath $jd1533 FIXED
$e addITerm [IT M13_10 Y]
$e newPath $emj2166 FIXED [RL M9]
set jd1534 [$e addTechVia [V {VIA89}]]
$e newPath $jd1534 FIXED [RL M8]
$e addPoint 6935560 3109140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6935560 3109220
set jd1535 [$e addTechVia [V VIA67]]
$e newPath $jd1535 FIXED
$e addPoint 6935480 3109220
set jd1536 [$e addTechVia [V VIA56]]
$e newPath $jd1536 FIXED
$e addPoint 6935480 3109316
set jd1537 [$e addTechVia [V VIA45]]
$e newPath $jd1537 FIXED
$e addPoint 6935297 3109316
set jd1538 [$e addTechVia [V VIA34]]
$e newPath $jd1538 FIXED
$e addPoint 6935297 3109140
set jd1539 [$e addTechVia [V VIA23]]
$e newPath $jd1539 FIXED
$e addPoint 6935247 3109140
set jd1540 [$e addTechVia [V VIA12]]
$e newPath $jd1540 FIXED
$e addITerm [IT M13_11 Y]
$e newPath $emj2162 FIXED [RL M9]
set jd1541 [$e addTechVia [V {VIA89}]]
$e newPath $jd1541 FIXED [RL M8]
$e addPoint 6931640 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6931640 3372740
set jd1542 [$e addTechVia [V VIA67]]
$e newPath $jd1542 FIXED
$e addPoint 6931720 3372740
set jd1543 [$e addTechVia [V VIA56]]
$e newPath $jd1543 FIXED
$e addPoint 6931720 3372836
set jd1544 [$e addTechVia [V VIA45]]
$e newPath $jd1544 FIXED
$e addPoint 6932173 3372836
set jd1545 [$e addTechVia [V VIA34]]
$e newPath $jd1545 FIXED
$e addPoint 6932173 3372660
set jd1546 [$e addTechVia [V VIA23]]
$e newPath $jd1546 FIXED
$e addPoint 6932223 3372660
set jd1547 [$e addTechVia [V VIA12]]
$e newPath $jd1547 FIXED
$e addITerm [IT M13_12 Y]
$e newPath $emj2296 FIXED [RL M9]
set jd1548 [$e addTechVia [V {VIA89}]]
$e newPath $jd1548 FIXED [RL M8]
$e addPoint 6931640 3647340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6931640 3647420
set jd1549 [$e addTechVia [V VIA67]]
$e newPath $jd1549 FIXED
$e addPoint 6931720 3647420
set jd1550 [$e addTechVia [V VIA56]]
$e newPath $jd1550 FIXED
$e addPoint 6931720 3647516
set jd1551 [$e addTechVia [V VIA45]]
$e newPath $jd1551 FIXED
$e addPoint 6932173 3647516
set jd1552 [$e addTechVia [V VIA34]]
$e newPath $jd1552 FIXED
$e addPoint 6932173 3647340
set jd1553 [$e addTechVia [V VIA23]]
$e newPath $jd1553 FIXED
$e addPoint 6932223 3647340
set jd1554 [$e addTechVia [V VIA12]]
$e newPath $jd1554 FIXED
$e addITerm [IT M13_13 Y]
$e newPath $emj2411 FIXED [RL M9]
set jd1555 [$e addTechVia [V {VIA89}]]
$e newPath $jd1555 FIXED [RL M8]
$e addPoint 6931640 3912660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6931640 3912740
set jd1556 [$e addTechVia [V VIA67]]
$e newPath $jd1556 FIXED
$e addPoint 6931720 3912740
set jd1557 [$e addTechVia [V VIA56]]
$e newPath $jd1557 FIXED
$e addPoint 6931720 3912836
set jd1558 [$e addTechVia [V VIA45]]
$e newPath $jd1558 FIXED
$e addPoint 6932173 3912836
set jd1559 [$e addTechVia [V VIA34]]
$e newPath $jd1559 FIXED
$e addPoint 6932173 3912660
set jd1560 [$e addTechVia [V VIA23]]
$e newPath $jd1560 FIXED
$e addPoint 6932223 3912660
set jd1561 [$e addTechVia [V VIA12]]
$e newPath $jd1561 FIXED
$e addITerm [IT M13_14 Y]
$e newPath $emj2459 FIXED [RL M9]
set jd1562 [$e addTechVia [V {VIA89}]]
$e newPath $jd1562 FIXED [RL M8]
$e addPoint 6931640 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6931640 4187420
set jd1563 [$e addTechVia [V VIA67]]
$e newPath $jd1563 FIXED
$e addPoint 6931720 4187420
set jd1564 [$e addTechVia [V VIA56]]
$e newPath $jd1564 FIXED
$e addPoint 6931720 4187516
set jd1565 [$e addTechVia [V VIA45]]
$e newPath $jd1565 FIXED
$e addPoint 6932173 4187516
set jd1566 [$e addTechVia [V VIA34]]
$e newPath $jd1566 FIXED
$e addPoint 6932173 4187340
set jd1567 [$e addTechVia [V VIA23]]
$e newPath $jd1567 FIXED
$e addPoint 6932223 4187340
set jd1568 [$e addTechVia [V VIA12]]
$e newPath $jd1568 FIXED
$e addITerm [IT M13_15 Y]
$e newPath $emj1132 FIXED [RL M9]
set jd1569 [$e addTechVia [V {VIA89}]]
$e newPath $jd1569 FIXED [RL M8]
$e addPoint 7445720 132660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 132740
set jd1570 [$e addTechVia [V VIA67]]
$e newPath $jd1570 FIXED
$e addPoint 7445800 132740
set jd1571 [$e addTechVia [V VIA56]]
$e newPath $jd1571 FIXED
$e addPoint 7445800 132836
set jd1572 [$e addTechVia [V VIA45]]
$e newPath $jd1572 FIXED
$e addPoint 7446253 132836
set jd1573 [$e addTechVia [V VIA34]]
$e newPath $jd1573 FIXED
$e addPoint 7446253 132660
set jd1574 [$e addTechVia [V VIA23]]
$e newPath $jd1574 FIXED
$e addPoint 7446303 132660
set jd1575 [$e addTechVia [V VIA12]]
$e newPath $jd1575 FIXED
$e addITerm [IT M14_0 Y]
$e newPath $emj1064 FIXED [RL M9]
set jd1576 [$e addTechVia [V {VIA89}]]
$e newPath $jd1576 FIXED [RL M8]
$e addPoint 7445720 407340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 407420
set jd1577 [$e addTechVia [V VIA67]]
$e newPath $jd1577 FIXED
$e addPoint 7445800 407420
set jd1578 [$e addTechVia [V VIA56]]
$e newPath $jd1578 FIXED
$e addPoint 7445800 407516
set jd1579 [$e addTechVia [V VIA45]]
$e newPath $jd1579 FIXED
$e addPoint 7446253 407516
set jd1580 [$e addTechVia [V VIA34]]
$e newPath $jd1580 FIXED
$e addPoint 7446253 407340
set jd1581 [$e addTechVia [V VIA23]]
$e newPath $jd1581 FIXED
$e addPoint 7446303 407340
set jd1582 [$e addTechVia [V VIA12]]
$e newPath $jd1582 FIXED
$e addITerm [IT M14_1 Y]
$e newPath $emj1471 FIXED [RL M9]
set jd1583 [$e addTechVia [V {VIA89}]]
$e newPath $jd1583 FIXED [RL M8]
$e addPoint 7449640 688140
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7449640 688220
set jd1584 [$e addTechVia [V VIA67]]
$e newPath $jd1584 FIXED
$e addPoint 7449560 688220
set jd1585 [$e addTechVia [V VIA56]]
$e newPath $jd1585 FIXED
$e addPoint 7449560 688316
set jd1586 [$e addTechVia [V VIA45]]
$e newPath $jd1586 FIXED
$e addPoint 7448459 688316
set jd1587 [$e addTechVia [V VIA34]]
$e newPath $jd1587 FIXED
$e addPoint 7448459 688140
set jd1588 [$e addTechVia [V VIA23]]
$e newPath $jd1588 FIXED
$e addPoint 7448409 688140
set jd1589 [$e addTechVia [V VIA12]]
$e newPath $jd1589 FIXED
$e addITerm [IT M14_2 Y]
$e newPath $emj1398 FIXED [RL M9]
set jd1590 [$e addTechVia [V {VIA89}]]
$e newPath $jd1590 FIXED [RL M8]
$e addPoint 7445720 947340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 947420
set jd1591 [$e addTechVia [V VIA67]]
$e newPath $jd1591 FIXED
$e addPoint 7445800 947420
set jd1592 [$e addTechVia [V VIA56]]
$e newPath $jd1592 FIXED
$e addPoint 7445800 947516
set jd1593 [$e addTechVia [V VIA45]]
$e newPath $jd1593 FIXED
$e addPoint 7446253 947516
set jd1594 [$e addTechVia [V VIA34]]
$e newPath $jd1594 FIXED
$e addPoint 7446253 947340
set jd1595 [$e addTechVia [V VIA23]]
$e newPath $jd1595 FIXED
$e addPoint 7446303 947340
set jd1596 [$e addTechVia [V VIA12]]
$e newPath $jd1596 FIXED
$e addITerm [IT M14_3 Y]
$e newPath $emj1407 FIXED [RL M9]
set jd1597 [$e addTechVia [V {VIA89}]]
$e newPath $jd1597 FIXED [RL M8]
$e addPoint 7445720 1212660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 1212740
set jd1598 [$e addTechVia [V VIA67]]
$e newPath $jd1598 FIXED
$e addPoint 7445800 1212740
set jd1599 [$e addTechVia [V VIA56]]
$e newPath $jd1599 FIXED
$e addPoint 7445800 1212836
set jd1600 [$e addTechVia [V VIA45]]
$e newPath $jd1600 FIXED
$e addPoint 7446253 1212836
set jd1601 [$e addTechVia [V VIA34]]
$e newPath $jd1601 FIXED
$e addPoint 7446253 1212660
set jd1602 [$e addTechVia [V VIA23]]
$e newPath $jd1602 FIXED
$e addPoint 7446303 1212660
set jd1603 [$e addTechVia [V VIA12]]
$e newPath $jd1603 FIXED
$e addITerm [IT M14_4 Y]
$e newPath $emj1481 FIXED [RL M9]
set jd1604 [$e addTechVia [V {VIA89}]]
$e newPath $jd1604 FIXED [RL M8]
$e addPoint 7445720 1487340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 1487420
set jd1605 [$e addTechVia [V VIA67]]
$e newPath $jd1605 FIXED
$e addPoint 7445800 1487420
set jd1606 [$e addTechVia [V VIA56]]
$e newPath $jd1606 FIXED
$e addPoint 7445800 1487516
set jd1607 [$e addTechVia [V VIA45]]
$e newPath $jd1607 FIXED
$e addPoint 7446253 1487516
set jd1608 [$e addTechVia [V VIA34]]
$e newPath $jd1608 FIXED
$e addPoint 7446253 1487340
set jd1609 [$e addTechVia [V VIA23]]
$e newPath $jd1609 FIXED
$e addPoint 7446303 1487340
set jd1610 [$e addTechVia [V VIA12]]
$e newPath $jd1610 FIXED
$e addITerm [IT M14_5 Y]
$e newPath $emj1609 FIXED [RL M9]
set jd1611 [$e addTechVia [V {VIA89}]]
$e newPath $jd1611 FIXED [RL M8]
$e addPoint 7445720 1752660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 1752740
set jd1612 [$e addTechVia [V VIA67]]
$e newPath $jd1612 FIXED
$e addPoint 7445800 1752740
set jd1613 [$e addTechVia [V VIA56]]
$e newPath $jd1613 FIXED
$e addPoint 7445800 1752836
set jd1614 [$e addTechVia [V VIA45]]
$e newPath $jd1614 FIXED
$e addPoint 7446253 1752836
set jd1615 [$e addTechVia [V VIA34]]
$e newPath $jd1615 FIXED
$e addPoint 7446253 1752660
set jd1616 [$e addTechVia [V VIA23]]
$e newPath $jd1616 FIXED
$e addPoint 7446303 1752660
set jd1617 [$e addTechVia [V VIA12]]
$e newPath $jd1617 FIXED
$e addITerm [IT M14_6 Y]
$e newPath $emj1720 FIXED [RL M9]
set jd1618 [$e addTechVia [V {VIA89}]]
$e newPath $jd1618 FIXED [RL M8]
$e addPoint 7445720 2027340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 2027420
set jd1619 [$e addTechVia [V VIA67]]
$e newPath $jd1619 FIXED
$e addPoint 7445800 2027420
set jd1620 [$e addTechVia [V VIA56]]
$e newPath $jd1620 FIXED
$e addPoint 7445800 2027516
set jd1621 [$e addTechVia [V VIA45]]
$e newPath $jd1621 FIXED
$e addPoint 7446253 2027516
set jd1622 [$e addTechVia [V VIA34]]
$e newPath $jd1622 FIXED
$e addPoint 7446253 2027340
set jd1623 [$e addTechVia [V VIA23]]
$e newPath $jd1623 FIXED
$e addPoint 7446303 2027340
set jd1624 [$e addTechVia [V VIA12]]
$e newPath $jd1624 FIXED
$e addITerm [IT M14_7 Y]
$e newPath $emj1939 FIXED [RL M9]
set jd1625 [$e addTechVia [V {VIA89}]]
$e newPath $jd1625 FIXED [RL M8]
$e addPoint 7445720 2292660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 2292740
set jd1626 [$e addTechVia [V VIA67]]
$e newPath $jd1626 FIXED
$e addPoint 7445800 2292740
set jd1627 [$e addTechVia [V VIA56]]
$e newPath $jd1627 FIXED
$e addPoint 7445800 2292836
set jd1628 [$e addTechVia [V VIA45]]
$e newPath $jd1628 FIXED
$e addPoint 7446253 2292836
set jd1629 [$e addTechVia [V VIA34]]
$e newPath $jd1629 FIXED
$e addPoint 7446253 2292660
set jd1630 [$e addTechVia [V VIA23]]
$e newPath $jd1630 FIXED
$e addPoint 7446303 2292660
set jd1631 [$e addTechVia [V VIA12]]
$e newPath $jd1631 FIXED
$e addITerm [IT M14_8 Y]
$e newPath $emj2076 FIXED [RL M9]
set jd1632 [$e addTechVia [V {VIA89}]]
$e newPath $jd1632 FIXED [RL M8]
$e addPoint 7445720 2567340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 2567420
set jd1633 [$e addTechVia [V VIA67]]
$e newPath $jd1633 FIXED
$e addPoint 7445800 2567420
set jd1634 [$e addTechVia [V VIA56]]
$e newPath $jd1634 FIXED
$e addPoint 7445800 2567516
set jd1635 [$e addTechVia [V VIA45]]
$e newPath $jd1635 FIXED
$e addPoint 7446253 2567516
set jd1636 [$e addTechVia [V VIA34]]
$e newPath $jd1636 FIXED
$e addPoint 7446253 2567340
set jd1637 [$e addTechVia [V VIA23]]
$e newPath $jd1637 FIXED
$e addPoint 7446303 2567340
set jd1638 [$e addTechVia [V VIA12]]
$e newPath $jd1638 FIXED
$e addITerm [IT M14_9 Y]
$e newPath $emj2157 FIXED [RL M9]
set jd1639 [$e addTechVia [V {VIA89}]]
$e newPath $jd1639 FIXED [RL M8]
$e addPoint 7445720 2832660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 2832740
set jd1640 [$e addTechVia [V VIA67]]
$e newPath $jd1640 FIXED
$e addPoint 7445800 2832740
set jd1641 [$e addTechVia [V VIA56]]
$e newPath $jd1641 FIXED
$e addPoint 7445800 2832836
set jd1642 [$e addTechVia [V VIA45]]
$e newPath $jd1642 FIXED
$e addPoint 7446253 2832836
set jd1643 [$e addTechVia [V VIA34]]
$e newPath $jd1643 FIXED
$e addPoint 7446253 2832660
set jd1644 [$e addTechVia [V VIA23]]
$e newPath $jd1644 FIXED
$e addPoint 7446303 2832660
set jd1645 [$e addTechVia [V VIA12]]
$e newPath $jd1645 FIXED
$e addITerm [IT M14_10 Y]
$e newPath $emj2230 FIXED [RL M9]
set jd1646 [$e addTechVia [V {VIA89}]]
$e newPath $jd1646 FIXED [RL M8]
$e addPoint 7445720 3107340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 3107420
set jd1647 [$e addTechVia [V VIA67]]
$e newPath $jd1647 FIXED
$e addPoint 7445800 3107420
set jd1648 [$e addTechVia [V VIA56]]
$e newPath $jd1648 FIXED
$e addPoint 7445800 3107516
set jd1649 [$e addTechVia [V VIA45]]
$e newPath $jd1649 FIXED
$e addPoint 7446253 3107516
set jd1650 [$e addTechVia [V VIA34]]
$e newPath $jd1650 FIXED
$e addPoint 7446253 3107340
set jd1651 [$e addTechVia [V VIA23]]
$e newPath $jd1651 FIXED
$e addPoint 7446303 3107340
set jd1652 [$e addTechVia [V VIA12]]
$e newPath $jd1652 FIXED
$e addITerm [IT M14_11 Y]
$e newPath $emj2290 FIXED [RL M9]
set jd1653 [$e addTechVia [V {VIA89}]]
$e newPath $jd1653 FIXED [RL M8]
$e addPoint 7445720 3372660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 3372740
set jd1654 [$e addTechVia [V VIA67]]
$e newPath $jd1654 FIXED
$e addPoint 7445800 3372740
set jd1655 [$e addTechVia [V VIA56]]
$e newPath $jd1655 FIXED
$e addPoint 7445800 3372836
set jd1656 [$e addTechVia [V VIA45]]
$e newPath $jd1656 FIXED
$e addPoint 7446253 3372836
set jd1657 [$e addTechVia [V VIA34]]
$e newPath $jd1657 FIXED
$e addPoint 7446253 3372660
set jd1658 [$e addTechVia [V VIA23]]
$e newPath $jd1658 FIXED
$e addPoint 7446303 3372660
set jd1659 [$e addTechVia [V VIA12]]
$e newPath $jd1659 FIXED
$e addITerm [IT M14_12 Y]
$e newPath $emj2409 FIXED [RL M9]
set jd1660 [$e addTechVia [V {VIA89}]]
$e newPath $jd1660 FIXED [RL M8]
$e addPoint 7428440 3545460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7428440 3545540
set jd1661 [$e addTechVia [V VIA67]]
$e newPath $jd1661 FIXED
$e addPoint 7428520 3545540
set jd1662 [$e addTechVia [V VIA56]]
$e newPath $jd1662 FIXED
$e addPoint 7428520 3545636
set jd1663 [$e addTechVia [V VIA45]]
$e newPath $jd1663 FIXED
$e addPoint 7428865 3545636
set jd1664 [$e addTechVia [V VIA34]]
$e newPath $jd1664 FIXED
$e addPoint 7428865 3545460
set jd1665 [$e addTechVia [V VIA23]]
$e newPath $jd1665 FIXED
$e addPoint 7428915 3545460
set jd1666 [$e addTechVia [V VIA12]]
$e newPath $jd1666 FIXED
$e addITerm [IT M14_13 Y]
$e newPath $emj2430 FIXED [RL M9]
set jd1667 [$e addTechVia [V {VIA89}]]
$e newPath $jd1667 FIXED [RL M8]
$e addPoint 7458680 4062600
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7458680 4062680
set jd1668 [$e addTechVia [V VIA67]]
$e newPath $jd1668 FIXED
$e addPoint 7458760 4062680
set jd1669 [$e addTechVia [V VIA56]]
$e newPath $jd1669 FIXED
$e addPoint 7458760 4062776
set jd1670 [$e addTechVia [V VIA45]]
$e newPath $jd1670 FIXED
$e addPoint 7459159 4062776
set jd1671 [$e addTechVia [V VIA34]]
$e newPath $jd1671 FIXED
$e addPoint 7459159 4062600
set jd1672 [$e addTechVia [V VIA23]]
$e newPath $jd1672 FIXED
$e addPoint 7459209 4062600
set jd1673 [$e addTechVia [V VIA12]]
$e newPath $jd1673 FIXED
$e addITerm [IT M14_14 Y]
$e newPath $emj2446 FIXED [RL M9]
set jd1674 [$e addTechVia [V {VIA89}]]
$e newPath $jd1674 FIXED [RL M8]
$e addPoint 7445720 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445720 4187420
set jd1675 [$e addTechVia [V VIA67]]
$e newPath $jd1675 FIXED
$e addPoint 7445800 4187420
set jd1676 [$e addTechVia [V VIA56]]
$e newPath $jd1676 FIXED
$e addPoint 7445800 4187516
set jd1677 [$e addTechVia [V VIA45]]
$e newPath $jd1677 FIXED
$e addPoint 7446253 4187516
set jd1678 [$e addTechVia [V VIA34]]
$e newPath $jd1678 FIXED
$e addPoint 7446253 4187340
set jd1679 [$e addTechVia [V VIA23]]
$e newPath $jd1679 FIXED
$e addPoint 7446303 4187340
set jd1680 [$e addTechVia [V VIA12]]
$e newPath $jd1680 FIXED
$e addITerm [IT M14_15 Y]
$e newPath $emj1192 FIXED [RL M9]
set jd1681 [$e addTechVia [V {VIA89}]]
$e newPath $jd1681 FIXED [RL M8]
$e addPoint 7959800 132660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7959800 132740
set jd1682 [$e addTechVia [V VIA67]]
$e newPath $jd1682 FIXED
$e addPoint 7959880 132740
set jd1683 [$e addTechVia [V VIA56]]
$e newPath $jd1683 FIXED
$e addPoint 7959880 132836
set jd1684 [$e addTechVia [V VIA45]]
$e newPath $jd1684 FIXED
$e addPoint 7960333 132836
set jd1685 [$e addTechVia [V VIA34]]
$e newPath $jd1685 FIXED
$e addPoint 7960333 132660
set jd1686 [$e addTechVia [V VIA23]]
$e newPath $jd1686 FIXED
$e addPoint 7960383 132660
set jd1687 [$e addTechVia [V VIA12]]
$e newPath $jd1687 FIXED
$e addITerm [IT M15_0 Y]
$e newPath $emj1127 FIXED [RL M9]
set jd1688 [$e addTechVia [V {VIA89}]]
$e newPath $jd1688 FIXED [RL M8]
$e addPoint 7959800 407340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7959800 407420
set jd1689 [$e addTechVia [V VIA67]]
$e newPath $jd1689 FIXED
$e addPoint 7959880 407420
set jd1690 [$e addTechVia [V VIA56]]
$e newPath $jd1690 FIXED
$e addPoint 7959880 407516
set jd1691 [$e addTechVia [V VIA45]]
$e newPath $jd1691 FIXED
$e addPoint 7960333 407516
set jd1692 [$e addTechVia [V VIA34]]
$e newPath $jd1692 FIXED
$e addPoint 7960333 407340
set jd1693 [$e addTechVia [V VIA23]]
$e newPath $jd1693 FIXED
$e addPoint 7960383 407340
set jd1694 [$e addTechVia [V VIA12]]
$e newPath $jd1694 FIXED
$e addITerm [IT M15_1 Y]
$e newPath $emj1394 FIXED [RL M9]
set jd1695 [$e addTechVia [V {VIA89}]]
$e newPath $jd1695 FIXED [RL M8]
$e addPoint 7959800 672660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7959800 672740
set jd1696 [$e addTechVia [V VIA67]]
$e newPath $jd1696 FIXED
$e addPoint 7959880 672740
set jd1697 [$e addTechVia [V VIA56]]
$e newPath $jd1697 FIXED
$e addPoint 7959880 672836
set jd1698 [$e addTechVia [V VIA45]]
$e newPath $jd1698 FIXED
$e addPoint 7960333 672836
set jd1699 [$e addTechVia [V VIA34]]
$e newPath $jd1699 FIXED
$e addPoint 7960333 672660
set jd1700 [$e addTechVia [V VIA23]]
$e newPath $jd1700 FIXED
$e addPoint 7960383 672660
set jd1701 [$e addTechVia [V VIA12]]
$e newPath $jd1701 FIXED
$e addITerm [IT M15_2 Y]
$e newPath $emj1605 FIXED [RL M9]
set jd1702 [$e addTechVia [V {VIA89}]]
$e newPath $jd1702 FIXED [RL M8]
$e addPoint 7950760 832500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7950760 832580
set jd1703 [$e addTechVia [V VIA67]]
$e newPath $jd1703 FIXED
$e addPoint 7950680 832580
set jd1704 [$e addTechVia [V VIA56]]
$e newPath $jd1704 FIXED
$e addPoint 7950680 832676
set jd1705 [$e addTechVia [V VIA45]]
$e newPath $jd1705 FIXED
$e addPoint 7950776 832676
set jd1706 [$e addTechVia [V VIA34]]
$e newPath $jd1706 FIXED
$e addPoint 7950776 832500
set jd1707 [$e addTechVia [V VIA23]]
$e newPath $jd1707 FIXED
$e addPoint 7950609 832500
set jd1708 [$e addTechVia [V VIA12]]
$e newPath $jd1708 FIXED
$e addITerm [IT M15_3 Y]
$e newPath $emj1405 FIXED [RL M9]
set jd1709 [$e addTechVia [V {VIA89}]]
$e newPath $jd1709 FIXED [RL M8]
$e addPoint 7959800 1362060
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7959800 1362140
set jd1710 [$e addTechVia [V VIA67]]
$e newPath $jd1710 FIXED
$e addPoint 7959880 1362140
set jd1711 [$e addTechVia [V VIA56]]
$e newPath $jd1711 FIXED
$e addPoint 7959880 1362236
set jd1712 [$e addTechVia [V VIA45]]
$e newPath $jd1712 FIXED
$e addPoint 7960333 1362236
set jd1713 [$e addTechVia [V VIA34]]
$e newPath $jd1713 FIXED
$e addPoint 7960333 1362060
set jd1714 [$e addTechVia [V VIA23]]
$e newPath $jd1714 FIXED
$e addPoint 7960383 1362060
set jd1715 [$e addTechVia [V VIA12]]
$e newPath $jd1715 FIXED
$e addITerm [IT M15_4 Y]
$e newPath $emj1665 FIXED [RL M9]
set jd1716 [$e addTechVia [V {VIA89}]]
$e newPath $jd1716 FIXED [RL M8]
$e addPoint 7972360 1543500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7972360 1543580
set jd1717 [$e addTechVia [V VIA67]]
$e newPath $jd1717 FIXED
$e addPoint 7972280 1543580
set jd1718 [$e addTechVia [V VIA56]]
$e newPath $jd1718 FIXED
$e addPoint 7972280 1543676
set jd1719 [$e addTechVia [V VIA45]]
$e newPath $jd1719 FIXED
$e addPoint 7970531 1543676
set jd1720 [$e addTechVia [V VIA34]]
$e newPath $jd1720 FIXED
$e addPoint 7970531 1543500
set jd1721 [$e addTechVia [V VIA23]]
$e newPath $jd1721 FIXED
$e addPoint 7970481 1543500
set jd1722 [$e addTechVia [V VIA12]]
$e newPath $jd1722 FIXED
$e addITerm [IT M15_5 Y]
$e newPath $emj1867 FIXED [RL M9]
set jd1723 [$e addTechVia [V {VIA89}]]
$e newPath $jd1723 FIXED [RL M8]
$e addPoint 8171080 1752660
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 8171080 1752740
set jd1724 [$e addTechVia [V VIA67]]
$e newPath $jd1724 FIXED
$e addPoint 8171000 1752740
set jd1725 [$e addTechVia [V VIA56]]
$e newPath $jd1725 FIXED
$e addPoint 8171000 1752836
set jd1726 [$e addTechVia [V VIA45]]
$e newPath $jd1726 FIXED
$e addPoint 8170439 1752836
set jd1727 [$e addTechVia [V VIA34]]
$e newPath $jd1727 FIXED
$e addPoint 8170439 1752660
set jd1728 [$e addTechVia [V VIA23]]
$e newPath $jd1728 FIXED
$e addPoint 8170389 1752660
set jd1729 [$e addTechVia [V VIA12]]
$e newPath $jd1729 FIXED
$e addITerm [IT M15_6 Y]
$e newPath $emj1875 FIXED [RL M9]
set jd1730 [$e addTechVia [V {VIA89}]]
$e newPath $jd1730 FIXED [RL M8]
$e addPoint 7972360 2070540
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7972360 2070620
set jd1731 [$e addTechVia [V VIA67]]
$e newPath $jd1731 FIXED
$e addPoint 7972280 2070620
set jd1732 [$e addTechVia [V VIA56]]
$e newPath $jd1732 FIXED
$e addPoint 7972280 2070716
set jd1733 [$e addTechVia [V VIA45]]
$e newPath $jd1733 FIXED
$e addPoint 7972376 2070716
set jd1734 [$e addTechVia [V VIA34]]
$e newPath $jd1734 FIXED
$e addPoint 7972376 2070540
set jd1735 [$e addTechVia [V VIA23]]
$e newPath $jd1735 FIXED
$e addPoint 7972263 2070540
set jd1736 [$e addTechVia [V VIA12]]
$e newPath $jd1736 FIXED
$e addITerm [IT M15_7 Y]
$e newPath $emj1983 FIXED [RL M9]
set jd1737 [$e addTechVia [V {VIA89}]]
$e newPath $jd1737 FIXED [RL M8]
$e addPoint 7946840 2249460
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7946840 2249540
set jd1738 [$e addTechVia [V VIA67]]
$e newPath $jd1738 FIXED
$e addPoint 7946920 2249540
set jd1739 [$e addTechVia [V VIA56]]
$e newPath $jd1739 FIXED
$e addPoint 7946920 2249636
set jd1740 [$e addTechVia [V VIA45]]
$e newPath $jd1740 FIXED
$e addPoint 7948453 2249636
set jd1741 [$e addTechVia [V VIA34]]
$e newPath $jd1741 FIXED
$e addPoint 7948453 2249460
set jd1742 [$e addTechVia [V VIA23]]
$e newPath $jd1742 FIXED
$e addPoint 7948503 2249460
set jd1743 [$e addTechVia [V VIA12]]
$e newPath $jd1743 FIXED
$e addITerm [IT M15_8 Y]
$e newPath $emj2111 FIXED [RL M9]
set jd1744 [$e addTechVia [V {VIA89}]]
$e newPath $jd1744 FIXED [RL M8]
$e addPoint 7812920 2667240
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7812920 2667320
set jd1745 [$e addTechVia [V VIA67]]
$e newPath $jd1745 FIXED
$e addPoint 7813000 2667320
set jd1746 [$e addTechVia [V VIA56]]
$e newPath $jd1746 FIXED
$e addPoint 7813000 2667416
set jd1747 [$e addTechVia [V VIA45]]
$e newPath $jd1747 FIXED
$e addPoint 7814533 2667416
set jd1748 [$e addTechVia [V VIA34]]
$e newPath $jd1748 FIXED
$e addPoint 7814533 2667240
set jd1749 [$e addTechVia [V VIA23]]
$e newPath $jd1749 FIXED
$e addPoint 7814583 2667240
set jd1750 [$e addTechVia [V VIA12]]
$e newPath $jd1750 FIXED
$e addITerm [IT M15_9 Y]
$e newPath $emj2224 FIXED [RL M9]
set jd1751 [$e addTechVia [V {VIA89}]]
$e newPath $jd1751 FIXED [RL M8]
$e addPoint 7950760 2779020
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7950760 2779100
set jd1752 [$e addTechVia [V VIA67]]
$e newPath $jd1752 FIXED
$e addPoint 7950680 2779100
set jd1753 [$e addTechVia [V VIA56]]
$e newPath $jd1753 FIXED
$e addPoint 7950680 2779196
set jd1754 [$e addTechVia [V VIA45]]
$e newPath $jd1754 FIXED
$e addPoint 7950335 2779196
set jd1755 [$e addTechVia [V VIA34]]
$e newPath $jd1755 FIXED
$e addPoint 7950335 2779020
set jd1756 [$e addTechVia [V VIA23]]
$e newPath $jd1756 FIXED
$e addPoint 7950285 2779020
set jd1757 [$e addTechVia [V VIA12]]
$e newPath $jd1757 FIXED
$e addITerm [IT M15_10 Y]
$e newPath $emj2115 FIXED [RL M9]
set jd1758 [$e addTechVia [V {VIA89}]]
$e newPath $jd1758 FIXED [RL M8]
$e addPoint 7959800 2957940
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7959800 2958020
set jd1759 [$e addTechVia [V VIA67]]
$e newPath $jd1759 FIXED
$e addPoint 7959880 2958020
set jd1760 [$e addTechVia [V VIA56]]
$e newPath $jd1760 FIXED
$e addPoint 7959880 2958116
set jd1761 [$e addTechVia [V VIA45]]
$e newPath $jd1761 FIXED
$e addPoint 7960333 2958116
set jd1762 [$e addTechVia [V VIA34]]
$e newPath $jd1762 FIXED
$e addPoint 7960333 2957940
set jd1763 [$e addTechVia [V VIA23]]
$e newPath $jd1763 FIXED
$e addPoint 7960383 2957940
set jd1764 [$e addTechVia [V VIA12]]
$e newPath $jd1764 FIXED
$e addITerm [IT M15_11 Y]
$e newPath $emj2381 FIXED [RL M9]
set jd1765 [$e addTechVia [V {VIA89}]]
$e newPath $jd1765 FIXED [RL M8]
$e addPoint 7968440 3487500
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7968440 3487580
set jd1766 [$e addTechVia [V VIA67]]
$e newPath $jd1766 FIXED
$e addPoint 7968520 3487580
set jd1767 [$e addTechVia [V VIA56]]
$e newPath $jd1767 FIXED
$e addPoint 7968520 3487676
set jd1768 [$e addTechVia [V VIA45]]
$e newPath $jd1768 FIXED
$e addPoint 7970107 3487676
set jd1769 [$e addTechVia [V VIA34]]
$e newPath $jd1769 FIXED
$e addPoint 7970107 3487500
set jd1770 [$e addTechVia [V VIA23]]
$e newPath $jd1770 FIXED
$e addPoint 7970157 3487500
set jd1771 [$e addTechVia [V VIA12]]
$e newPath $jd1771 FIXED
$e addITerm [IT M15_12 Y]
$e newPath $emj2439 FIXED [RL M9]
set jd1772 [$e addTechVia [V {VIA89}]]
$e newPath $jd1772 FIXED [RL M8]
$e addPoint 7976680 3733740
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7976680 3733820
set jd1773 [$e addTechVia [V VIA67]]
$e newPath $jd1773 FIXED
$e addPoint 7976600 3733820
set jd1774 [$e addTechVia [V VIA56]]
$e newPath $jd1774 FIXED
$e addPoint 7976600 3733916
set jd1775 [$e addTechVia [V VIA45]]
$e newPath $jd1775 FIXED
$e addPoint 7976039 3733916
set jd1776 [$e addTechVia [V VIA34]]
$e newPath $jd1776 FIXED
$e addPoint 7976039 3733740
set jd1777 [$e addTechVia [V VIA23]]
$e newPath $jd1777 FIXED
$e addPoint 7975989 3733740
set jd1778 [$e addTechVia [V VIA12]]
$e newPath $jd1778 FIXED
$e addITerm [IT M15_13 Y]
$e newPath $emj2453 FIXED [RL M9]
set jd1779 [$e addTechVia [V {VIA89}]]
$e newPath $jd1779 FIXED [RL M8]
$e addPoint 7964120 3941100
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7964120 3941180
set jd1780 [$e addTechVia [V VIA67]]
$e newPath $jd1780 FIXED
$e addPoint 7964200 3941180
set jd1781 [$e addTechVia [V VIA56]]
$e newPath $jd1781 FIXED
$e addPoint 7964200 3941276
set jd1782 [$e addTechVia [V VIA45]]
$e newPath $jd1782 FIXED
$e addPoint 7964869 3941276
set jd1783 [$e addTechVia [V VIA34]]
$e newPath $jd1783 FIXED
$e addPoint 7964869 3941100
set jd1784 [$e addTechVia [V VIA23]]
$e newPath $jd1784 FIXED
$e addPoint 7964919 3941100
set jd1785 [$e addTechVia [V VIA12]]
$e newPath $jd1785 FIXED
$e addITerm [IT M15_14 Y]
$e newPath $emj2463 FIXED [RL M9]
set jd1786 [$e addTechVia [V {VIA89}]]
$e newPath $jd1786 FIXED [RL M8]
$e addPoint 7959800 4187340
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7959800 4187420
set jd1787 [$e addTechVia [V VIA67]]
$e newPath $jd1787 FIXED
$e addPoint 7959880 4187420
set jd1788 [$e addTechVia [V VIA56]]
$e newPath $jd1788 FIXED
$e addPoint 7959880 4187516
set jd1789 [$e addTechVia [V VIA45]]
$e newPath $jd1789 FIXED
$e addPoint 7960333 4187516
set jd1790 [$e addTechVia [V VIA34]]
$e newPath $jd1790 FIXED
$e addPoint 7960333 4187340
set jd1791 [$e addTechVia [V VIA23]]
$e newPath $jd1791 FIXED
$e addPoint 7960383 4187340
set jd1792 [$e addTechVia [V VIA12]]
$e newPath $jd1792 FIXED
$e addITerm [IT M15_15 Y]
$e newPath $emj5 FIXED [RL M9]
set jd1793 [$e addTechVia [V {VIA89}]]
$e newPath $jd1793 FIXED [RL M8]
$e addPoint 84440 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 84440 136250
set jd1794 [$e addTechVia [V VIA67]]
$e newPath $jd1794 FIXED
$e addPoint 84520 136250
set jd1795 [$e addTechVia [V VIA56]]
$e newPath $jd1795 FIXED
$e addPoint 84520 136346
set jd1796 [$e addTechVia [V VIA45]]
$e newPath $jd1796 FIXED
$e addPoint 85243 136346
set jd1797 [$e addTechVia [V VIA34]]
$e newPath $jd1797 FIXED
$e addPoint 85243 136170
set jd1798 [$e addTechVia [V VIA23]]
$e newPath $jd1798 FIXED
$e addPoint 85293 136170
set jd1799 [$e addTechVia [V VIA12]]
$e newPath $jd1799 FIXED
$e addITerm [IT L_clk A]
$e newPath $emj32 FIXED [RL M9]
set jd1800 [$e addTechVia [V {VIA89}]]
$e newPath $jd1800 FIXED [RL M8]
$e addPoint 770920 25830
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 770920 25910
set jd1801 [$e addTechVia [V VIA67]]
$e newPath $jd1801 FIXED
$e addPoint 770840 25910
set jd1802 [$e addTechVia [V VIA56]]
$e newPath $jd1802 FIXED
$e addPoint 770840 26006
set jd1803 [$e addTechVia [V VIA45]]
$e newPath $jd1803 FIXED
$e addPoint 770744 26006
set jd1804 [$e addTechVia [V VIA34]]
$e newPath $jd1804 FIXED
$e addPoint 770744 25830
set jd1805 [$e addTechVia [V VIA23]]
$e newPath $jd1805 FIXED
$e addPoint 770931 25830
set jd1806 [$e addTechVia [V VIA12]]
$e newPath $jd1806 FIXED
$e addITerm [IT L_clk_t1 A]
$e newPath $emj546 FIXED [RL M9]
set jd1807 [$e addTechVia [V {VIA89}]]
$e newPath $jd1807 FIXED [RL M8]
$e addPoint 4106360 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4106360 136250
set jd1808 [$e addTechVia [V VIA67]]
$e newPath $jd1808 FIXED
$e addPoint 4106440 136250
set jd1809 [$e addTechVia [V VIA56]]
$e newPath $jd1809 FIXED
$e addPoint 4106440 136346
set jd1810 [$e addTechVia [V VIA45]]
$e newPath $jd1810 FIXED
$e addPoint 4107595 136346
set jd1811 [$e addTechVia [V VIA34]]
$e newPath $jd1811 FIXED
$e addPoint 4107595 136170
set jd1812 [$e addTechVia [V VIA23]]
$e newPath $jd1812 FIXED
$e addPoint 4107645 136170
set jd1813 [$e addTechVia [V VIA12]]
$e newPath $jd1813 FIXED
$e addITerm [IT L_clk_t10 A]
$e newPath $emj1554 FIXED [RL M9]
set jd1814 [$e addTechVia [V {VIA89}]]
$e newPath $jd1814 FIXED [RL M8]
$e addPoint 6577400 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6577400 1756250
set jd1815 [$e addTechVia [V VIA67]]
$e newPath $jd1815 FIXED
$e addPoint 6577480 1756250
set jd1816 [$e addTechVia [V VIA56]]
$e newPath $jd1816 FIXED
$e addPoint 6577480 1756346
set jd1817 [$e addTechVia [V VIA45]]
$e newPath $jd1817 FIXED
$e addPoint 6578635 1756346
set jd1818 [$e addTechVia [V VIA34]]
$e newPath $jd1818 FIXED
$e addPoint 6578635 1756170
set jd1819 [$e addTechVia [V VIA23]]
$e newPath $jd1819 FIXED
$e addPoint 6578685 1756170
set jd1820 [$e addTechVia [V VIA12]]
$e newPath $jd1820 FIXED
$e addITerm [IT L_clk_t100 A]
$e newPath $emj1715 FIXED [RL M9]
set jd1821 [$e addTechVia [V {VIA89}]]
$e newPath $jd1821 FIXED [RL M8]
$e addPoint 6611560 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6611560 1756250
set jd1822 [$e addTechVia [V VIA67]]
$e newPath $jd1822 FIXED
$e addPoint 6611480 1756250
set jd1823 [$e addTechVia [V VIA56]]
$e newPath $jd1823 FIXED
$e addPoint 6611480 1756346
set jd1824 [$e addTechVia [V VIA45]]
$e newPath $jd1824 FIXED
$e addPoint 6611384 1756346
set jd1825 [$e addTechVia [V VIA34]]
$e newPath $jd1825 FIXED
$e addPoint 6611384 1756170
set jd1826 [$e addTechVia [V VIA23]]
$e newPath $jd1826 FIXED
$e addPoint 6611571 1756170
set jd1827 [$e addTechVia [V VIA12]]
$e newPath $jd1827 FIXED
$e addITerm [IT L_clk_t101 A]
$e newPath $emj1719 FIXED [RL M9]
set jd1828 [$e addTechVia [V {VIA89}]]
$e newPath $jd1828 FIXED [RL M8]
$e addPoint 7445320 1767330
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445320 1767410
set jd1829 [$e addTechVia [V VIA67]]
$e newPath $jd1829 FIXED
$e addPoint 7445240 1767410
set jd1830 [$e addTechVia [V VIA56]]
$e newPath $jd1830 FIXED
$e addPoint 7445240 1767506
set jd1831 [$e addTechVia [V VIA45]]
$e newPath $jd1831 FIXED
$e addPoint 7445144 1767506
set jd1832 [$e addTechVia [V VIA34]]
$e newPath $jd1832 FIXED
$e addPoint 7445144 1767330
set jd1833 [$e addTechVia [V VIA23]]
$e newPath $jd1833 FIXED
$e addPoint 7445331 1767330
set jd1834 [$e addTechVia [V VIA12]]
$e newPath $jd1834 FIXED
$e addITerm [IT L_clk_t102 A]
$e newPath $emj1762 FIXED [RL M9]
set jd1835 [$e addTechVia [V {VIA89}]]
$e newPath $jd1835 FIXED [RL M8]
$e addPoint 7532120 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7532120 1756250
set jd1836 [$e addTechVia [V VIA67]]
$e newPath $jd1836 FIXED
$e addPoint 7532200 1756250
set jd1837 [$e addTechVia [V VIA56]]
$e newPath $jd1837 FIXED
$e addPoint 7532200 1756346
set jd1838 [$e addTechVia [V VIA45]]
$e newPath $jd1838 FIXED
$e addPoint 7532104 1756346
set jd1839 [$e addTechVia [V VIA34]]
$e newPath $jd1839 FIXED
$e addPoint 7532104 1756170
set jd1840 [$e addTechVia [V VIA23]]
$e newPath $jd1840 FIXED
$e addPoint 7532325 1756170
set jd1841 [$e addTechVia [V VIA12]]
$e newPath $jd1841 FIXED
$e addITerm [IT L_clk_t103 A]
$e newPath $emj1979 FIXED [RL M9]
set jd1842 [$e addTechVia [V {VIA89}]]
$e newPath $jd1842 FIXED [RL M8]
$e addPoint 8175400 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 8175400 1756250
set jd1843 [$e addTechVia [V VIA67]]
$e newPath $jd1843 FIXED
$e addPoint 8175320 1756250
set jd1844 [$e addTechVia [V VIA56]]
$e newPath $jd1844 FIXED
$e addPoint 8175320 1756346
set jd1845 [$e addTechVia [V VIA45]]
$e newPath $jd1845 FIXED
$e addPoint 8174219 1756346
set jd1846 [$e addTechVia [V VIA34]]
$e newPath $jd1846 FIXED
$e addPoint 8174219 1756170
set jd1847 [$e addTechVia [V VIA23]]
$e newPath $jd1847 FIXED
$e addPoint 8174169 1756170
set jd1848 [$e addTechVia [V VIA12]]
$e newPath $jd1848 FIXED
$e addITerm [IT L_clk_t104 A]
$e newPath $emj679 FIXED [RL M9]
set jd1849 [$e addTechVia [V {VIA89}]]
$e newPath $jd1849 FIXED [RL M8]
$e addPoint 196360 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 196360 2296250
set jd1850 [$e addTechVia [V VIA67]]
$e newPath $jd1850 FIXED
$e addPoint 196280 2296250
set jd1851 [$e addTechVia [V VIA56]]
$e newPath $jd1851 FIXED
$e addPoint 196280 2296346
set jd1852 [$e addTechVia [V VIA45]]
$e newPath $jd1852 FIXED
$e addPoint 195503 2296346
set jd1853 [$e addTechVia [V VIA34]]
$e newPath $jd1853 FIXED
$e addPoint 195503 2296170
set jd1854 [$e addTechVia [V VIA23]]
$e newPath $jd1854 FIXED
$e addPoint 195453 2296170
set jd1855 [$e addTechVia [V VIA12]]
$e newPath $jd1855 FIXED
$e addITerm [IT L_clk_t105 A]
$e newPath $emj693 FIXED [RL M9]
set jd1856 [$e addTechVia [V {VIA89}]]
$e newPath $jd1856 FIXED [RL M8]
$e addPoint 827080 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 827080 2296250
set jd1857 [$e addTechVia [V VIA67]]
$e newPath $jd1857 FIXED
$e addPoint 827000 2296250
set jd1858 [$e addTechVia [V VIA56]]
$e newPath $jd1858 FIXED
$e addPoint 827000 2296346
set jd1859 [$e addTechVia [V VIA45]]
$e newPath $jd1859 FIXED
$e addPoint 826493 2296346
set jd1860 [$e addTechVia [V VIA34]]
$e newPath $jd1860 FIXED
$e addPoint 826493 2296170
set jd1861 [$e addTechVia [V VIA23]]
$e newPath $jd1861 FIXED
$e addPoint 826443 2296170
set jd1862 [$e addTechVia [V VIA12]]
$e newPath $jd1862 FIXED
$e addITerm [IT L_clk_t106 A]
$e newPath $emj756 FIXED [RL M9]
set jd1863 [$e addTechVia [V {VIA89}]]
$e newPath $jd1863 FIXED [RL M8]
$e addPoint 836120 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 836120 2296250
set jd1864 [$e addTechVia [V VIA67]]
$e newPath $jd1864 FIXED
$e addPoint 836200 2296250
set jd1865 [$e addTechVia [V VIA56]]
$e newPath $jd1865 FIXED
$e addPoint 836200 2296346
set jd1866 [$e addTechVia [V VIA45]]
$e newPath $jd1866 FIXED
$e addPoint 837355 2296346
set jd1867 [$e addTechVia [V VIA34]]
$e newPath $jd1867 FIXED
$e addPoint 837355 2296170
set jd1868 [$e addTechVia [V VIA23]]
$e newPath $jd1868 FIXED
$e addPoint 837405 2296170
set jd1869 [$e addTechVia [V VIA12]]
$e newPath $jd1869 FIXED
$e addITerm [IT L_clk_t107 A]
$e newPath $emj969 FIXED [RL M9]
set jd1870 [$e addTechVia [V {VIA89}]]
$e newPath $jd1870 FIXED [RL M8]
$e addPoint 1631000 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1631000 2296250
set jd1871 [$e addTechVia [V VIA67]]
$e newPath $jd1871 FIXED
$e addPoint 1631080 2296250
set jd1872 [$e addTechVia [V VIA56]]
$e newPath $jd1872 FIXED
$e addPoint 1631080 2296346
set jd1873 [$e addTechVia [V VIA45]]
$e newPath $jd1873 FIXED
$e addPoint 1632235 2296346
set jd1874 [$e addTechVia [V VIA34]]
$e newPath $jd1874 FIXED
$e addPoint 1632235 2296170
set jd1875 [$e addTechVia [V VIA23]]
$e newPath $jd1875 FIXED
$e addPoint 1632285 2296170
set jd1876 [$e addTechVia [V VIA12]]
$e newPath $jd1876 FIXED
$e addITerm [IT L_clk_t108 A]
$e newPath $emj1034 FIXED [RL M9]
set jd1877 [$e addTechVia [V {VIA89}]]
$e newPath $jd1877 FIXED [RL M8]
$e addPoint 1687160 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1687160 2296250
set jd1878 [$e addTechVia [V VIA67]]
$e newPath $jd1878 FIXED
$e addPoint 1687240 2296250
set jd1879 [$e addTechVia [V VIA56]]
$e newPath $jd1879 FIXED
$e addPoint 1687240 2296346
set jd1880 [$e addTechVia [V VIA45]]
$e newPath $jd1880 FIXED
$e addPoint 1688503 2296346
set jd1881 [$e addTechVia [V VIA34]]
$e newPath $jd1881 FIXED
$e addPoint 1688503 2296170
set jd1882 [$e addTechVia [V VIA23]]
$e newPath $jd1882 FIXED
$e addPoint 1688553 2296170
set jd1883 [$e addTechVia [V VIA12]]
$e newPath $jd1883 FIXED
$e addITerm [IT L_clk_t109 A]
$e newPath $emj651 FIXED [RL M9]
set jd1884 [$e addTechVia [V {VIA89}]]
$e newPath $jd1884 FIXED [RL M8]
$e addPoint 4516360 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4516360 136250
set jd1885 [$e addTechVia [V VIA67]]
$e newPath $jd1885 FIXED
$e addPoint 4516280 136250
set jd1886 [$e addTechVia [V VIA56]]
$e newPath $jd1886 FIXED
$e addPoint 4516280 136346
set jd1887 [$e addTechVia [V VIA45]]
$e newPath $jd1887 FIXED
$e addPoint 4514747 136346
set jd1888 [$e addTechVia [V VIA34]]
$e newPath $jd1888 FIXED
$e addPoint 4514747 136170
set jd1889 [$e addTechVia [V VIA23]]
$e newPath $jd1889 FIXED
$e addPoint 4514697 136170
set jd1890 [$e addTechVia [V VIA12]]
$e newPath $jd1890 FIXED
$e addITerm [IT L_clk_t11 A]
$e newPath $emj755 FIXED [RL M9]
set jd1891 [$e addTechVia [V {VIA89}]]
$e newPath $jd1891 FIXED [RL M8]
$e addPoint 2153320 2024010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2153320 2024090
set jd1892 [$e addTechVia [V VIA67]]
$e newPath $jd1892 FIXED
$e addPoint 2153240 2024090
set jd1893 [$e addTechVia [V VIA56]]
$e newPath $jd1893 FIXED
$e addPoint 2153240 2024186
set jd1894 [$e addTechVia [V VIA45]]
$e newPath $jd1894 FIXED
$e addPoint 2151815 2024186
set jd1895 [$e addTechVia [V VIA34]]
$e newPath $jd1895 FIXED
$e addPoint 2151815 2024010
set jd1896 [$e addTechVia [V VIA23]]
$e newPath $jd1896 FIXED
$e addPoint 2151765 2024010
set jd1897 [$e addTechVia [V VIA12]]
$e newPath $jd1897 FIXED
$e addITerm [IT L_clk_t110 A]
$e newPath $emj808 FIXED [RL M9]
set jd1898 [$e addTechVia [V {VIA89}]]
$e newPath $jd1898 FIXED [RL M8]
$e addPoint 2308840 2160090
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2308840 2160170
set jd1899 [$e addTechVia [V VIA67]]
$e newPath $jd1899 FIXED
$e addPoint 2308760 2160170
set jd1900 [$e addTechVia [V VIA56]]
$e newPath $jd1900 FIXED
$e addPoint 2308760 2160266
set jd1901 [$e addTechVia [V VIA45]]
$e newPath $jd1901 FIXED
$e addPoint 2308664 2160266
set jd1902 [$e addTechVia [V VIA34]]
$e newPath $jd1902 FIXED
$e addPoint 2308664 2160090
set jd1903 [$e addTechVia [V VIA23]]
$e newPath $jd1903 FIXED
$e addPoint 2308851 2160090
set jd1904 [$e addTechVia [V VIA12]]
$e newPath $jd1904 FIXED
$e addITerm [IT L_clk_t111 A]
$e newPath $emj1243 FIXED [RL M9]
set jd1905 [$e addTechVia [V {VIA89}]]
$e newPath $jd1905 FIXED [RL M8]
$e addPoint 3198760 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3198760 2296250
set jd1906 [$e addTechVia [V VIA67]]
$e newPath $jd1906 FIXED
$e addPoint 3198680 2296250
set jd1907 [$e addTechVia [V VIA56]]
$e newPath $jd1907 FIXED
$e addPoint 3198680 2296346
set jd1908 [$e addTechVia [V VIA45]]
$e newPath $jd1908 FIXED
$e addPoint 3197903 2296346
set jd1909 [$e addTechVia [V VIA34]]
$e newPath $jd1909 FIXED
$e addPoint 3197903 2296170
set jd1910 [$e addTechVia [V VIA23]]
$e newPath $jd1910 FIXED
$e addPoint 3197853 2296170
set jd1911 [$e addTechVia [V VIA12]]
$e newPath $jd1911 FIXED
$e addITerm [IT L_clk_t112 A]
$e newPath $emj1102 FIXED [RL M9]
set jd1912 [$e addTechVia [V {VIA89}]]
$e newPath $jd1912 FIXED [RL M8]
$e addPoint 3337000 2160090
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337000 2160170
set jd1913 [$e addTechVia [V VIA67]]
$e newPath $jd1913 FIXED
$e addPoint 3336920 2160170
set jd1914 [$e addTechVia [V VIA56]]
$e newPath $jd1914 FIXED
$e addPoint 3336920 2160266
set jd1915 [$e addTechVia [V VIA45]]
$e newPath $jd1915 FIXED
$e addPoint 3336824 2160266
set jd1916 [$e addTechVia [V VIA34]]
$e newPath $jd1916 FIXED
$e addPoint 3336824 2160090
set jd1917 [$e addTechVia [V VIA23]]
$e newPath $jd1917 FIXED
$e addPoint 3337011 2160090
set jd1918 [$e addTechVia [V VIA12]]
$e newPath $jd1918 FIXED
$e addITerm [IT L_clk_t113 A]
$e newPath $emj1024 FIXED [RL M9]
set jd1919 [$e addTechVia [V {VIA89}]]
$e newPath $jd1919 FIXED [RL M8]
$e addPoint 3851080 2160090
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3851080 2160170
set jd1920 [$e addTechVia [V VIA67]]
$e newPath $jd1920 FIXED
$e addPoint 3851000 2160170
set jd1921 [$e addTechVia [V VIA56]]
$e newPath $jd1921 FIXED
$e addPoint 3851000 2160266
set jd1922 [$e addTechVia [V VIA45]]
$e newPath $jd1922 FIXED
$e addPoint 3850904 2160266
set jd1923 [$e addTechVia [V VIA34]]
$e newPath $jd1923 FIXED
$e addPoint 3850904 2160090
set jd1924 [$e addTechVia [V VIA23]]
$e newPath $jd1924 FIXED
$e addPoint 3851091 2160090
set jd1925 [$e addTechVia [V VIA12]]
$e newPath $jd1925 FIXED
$e addITerm [IT L_clk_t114 A]
$e newPath $emj1430 FIXED [RL M9]
set jd1926 [$e addTechVia [V {VIA89}]]
$e newPath $jd1926 FIXED [RL M8]
$e addPoint 4106360 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4106360 2296250
set jd1927 [$e addTechVia [V VIA67]]
$e newPath $jd1927 FIXED
$e addPoint 4106440 2296250
set jd1928 [$e addTechVia [V VIA56]]
$e newPath $jd1928 FIXED
$e addPoint 4106440 2296346
set jd1929 [$e addTechVia [V VIA45]]
$e newPath $jd1929 FIXED
$e addPoint 4107595 2296346
set jd1930 [$e addTechVia [V VIA34]]
$e newPath $jd1930 FIXED
$e addPoint 4107595 2296170
set jd1931 [$e addTechVia [V VIA23]]
$e newPath $jd1931 FIXED
$e addPoint 4107645 2296170
set jd1932 [$e addTechVia [V VIA12]]
$e newPath $jd1932 FIXED
$e addITerm [IT L_clk_t115 A]
$e newPath $emj1293 FIXED [RL M9]
set jd1933 [$e addTechVia [V {VIA89}]]
$e newPath $jd1933 FIXED [RL M8]
$e addPoint 4365160 2160090
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365160 2160170
set jd1934 [$e addTechVia [V VIA67]]
$e newPath $jd1934 FIXED
$e addPoint 4365080 2160170
set jd1935 [$e addTechVia [V VIA56]]
$e newPath $jd1935 FIXED
$e addPoint 4365080 2160266
set jd1936 [$e addTechVia [V VIA45]]
$e newPath $jd1936 FIXED
$e addPoint 4364984 2160266
set jd1937 [$e addTechVia [V VIA34]]
$e newPath $jd1937 FIXED
$e addPoint 4364984 2160090
set jd1938 [$e addTechVia [V VIA23]]
$e newPath $jd1938 FIXED
$e addPoint 4365171 2160090
set jd1939 [$e addTechVia [V VIA12]]
$e newPath $jd1939 FIXED
$e addITerm [IT L_clk_t116 A]
$e newPath $emj1426 FIXED [RL M9]
set jd1940 [$e addTechVia [V {VIA89}]]
$e newPath $jd1940 FIXED [RL M8]
$e addPoint 4879240 2160090
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879240 2160170
set jd1941 [$e addTechVia [V VIA67]]
$e newPath $jd1941 FIXED
$e addPoint 4879160 2160170
set jd1942 [$e addTechVia [V VIA56]]
$e newPath $jd1942 FIXED
$e addPoint 4879160 2160266
set jd1943 [$e addTechVia [V VIA45]]
$e newPath $jd1943 FIXED
$e addPoint 4879064 2160266
set jd1944 [$e addTechVia [V VIA34]]
$e newPath $jd1944 FIXED
$e addPoint 4879064 2160090
set jd1945 [$e addTechVia [V VIA23]]
$e newPath $jd1945 FIXED
$e addPoint 4879251 2160090
set jd1946 [$e addTechVia [V VIA12]]
$e newPath $jd1946 FIXED
$e addITerm [IT L_clk_t117 A]
$e newPath $emj1624 FIXED [RL M9]
set jd1947 [$e addTechVia [V {VIA89}]]
$e newPath $jd1947 FIXED [RL M8]
$e addPoint 5281400 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5281400 2296250
set jd1948 [$e addTechVia [V VIA67]]
$e newPath $jd1948 FIXED
$e addPoint 5281480 2296250
set jd1949 [$e addTechVia [V VIA56]]
$e newPath $jd1949 FIXED
$e addPoint 5281480 2296346
set jd1950 [$e addTechVia [V VIA45]]
$e newPath $jd1950 FIXED
$e addPoint 5281879 2296346
set jd1951 [$e addTechVia [V VIA34]]
$e newPath $jd1951 FIXED
$e addPoint 5281879 2296170
set jd1952 [$e addTechVia [V VIA23]]
$e newPath $jd1952 FIXED
$e addPoint 5281929 2296170
set jd1953 [$e addTechVia [V VIA12]]
$e newPath $jd1953 FIXED
$e addITerm [IT L_clk_t118 A]
$e newPath $emj1627 FIXED [RL M9]
set jd1954 [$e addTechVia [V {VIA89}]]
$e newPath $jd1954 FIXED [RL M8]
$e addPoint 5674120 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5674120 2296250
set jd1955 [$e addTechVia [V VIA67]]
$e newPath $jd1955 FIXED
$e addPoint 5674040 2296250
set jd1956 [$e addTechVia [V VIA56]]
$e newPath $jd1956 FIXED
$e addPoint 5674040 2296346
set jd1957 [$e addTechVia [V VIA45]]
$e newPath $jd1957 FIXED
$e addPoint 5673263 2296346
set jd1958 [$e addTechVia [V VIA34]]
$e newPath $jd1958 FIXED
$e addPoint 5673263 2296170
set jd1959 [$e addTechVia [V VIA23]]
$e newPath $jd1959 FIXED
$e addPoint 5673213 2296170
set jd1960 [$e addTechVia [V VIA12]]
$e newPath $jd1960 FIXED
$e addITerm [IT L_clk_t119 A]
$e newPath $emj490 FIXED [RL M9]
set jd1961 [$e addTechVia [V {VIA89}]]
$e newPath $jd1961 FIXED [RL M8]
$e addPoint 4879240 196110
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879240 196190
set jd1962 [$e addTechVia [V VIA67]]
$e newPath $jd1962 FIXED
$e addPoint 4879160 196190
set jd1963 [$e addTechVia [V VIA56]]
$e newPath $jd1963 FIXED
$e addPoint 4879160 196286
set jd1964 [$e addTechVia [V VIA45]]
$e newPath $jd1964 FIXED
$e addPoint 4879064 196286
set jd1965 [$e addTechVia [V VIA34]]
$e newPath $jd1965 FIXED
$e addPoint 4879064 196110
set jd1966 [$e addTechVia [V VIA23]]
$e newPath $jd1966 FIXED
$e addPoint 4879251 196110
set jd1967 [$e addTechVia [V VIA12]]
$e newPath $jd1967 FIXED
$e addITerm [IT L_clk_t12 A]
$e newPath $emj1491 FIXED [RL M9]
set jd1968 [$e addTechVia [V {VIA89}]]
$e newPath $jd1968 FIXED [RL M8]
$e addPoint 5907400 2160090
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907400 2160170
set jd1969 [$e addTechVia [V VIA67]]
$e newPath $jd1969 FIXED
$e addPoint 5907320 2160170
set jd1970 [$e addTechVia [V VIA56]]
$e newPath $jd1970 FIXED
$e addPoint 5907320 2160266
set jd1971 [$e addTechVia [V VIA45]]
$e newPath $jd1971 FIXED
$e addPoint 5907224 2160266
set jd1972 [$e addTechVia [V VIA34]]
$e newPath $jd1972 FIXED
$e addPoint 5907224 2160090
set jd1973 [$e addTechVia [V VIA23]]
$e newPath $jd1973 FIXED
$e addPoint 5907411 2160090
set jd1974 [$e addTechVia [V VIA12]]
$e newPath $jd1974 FIXED
$e addITerm [IT L_clk_t120 A]
$e newPath $emj1662 FIXED [RL M9]
set jd1975 [$e addTechVia [V {VIA89}]]
$e newPath $jd1975 FIXED [RL M8]
$e addPoint 6417160 2160090
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6417160 2160170
set jd1976 [$e addTechVia [V VIA67]]
$e newPath $jd1976 FIXED
$e addPoint 6417080 2160170
set jd1977 [$e addTechVia [V VIA56]]
$e newPath $jd1977 FIXED
$e addPoint 6417080 2160266
set jd1978 [$e addTechVia [V VIA45]]
$e newPath $jd1978 FIXED
$e addPoint 6416984 2160266
set jd1979 [$e addTechVia [V VIA34]]
$e newPath $jd1979 FIXED
$e addPoint 6416984 2160090
set jd1980 [$e addTechVia [V VIA23]]
$e newPath $jd1980 FIXED
$e addPoint 6417171 2160090
set jd1981 [$e addTechVia [V VIA12]]
$e newPath $jd1981 FIXED
$e addITerm [IT L_clk_t121 A]
$e newPath $emj1878 FIXED [RL M9]
set jd1982 [$e addTechVia [V {VIA89}]]
$e newPath $jd1982 FIXED [RL M8]
$e addPoint 6624520 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6624520 2296250
set jd1983 [$e addTechVia [V VIA67]]
$e newPath $jd1983 FIXED
$e addPoint 6624440 2296250
set jd1984 [$e addTechVia [V VIA56]]
$e newPath $jd1984 FIXED
$e addPoint 6624440 2296346
set jd1985 [$e addTechVia [V VIA45]]
$e newPath $jd1985 FIXED
$e addPoint 6622907 2296346
set jd1986 [$e addTechVia [V VIA34]]
$e newPath $jd1986 FIXED
$e addPoint 6622907 2296170
set jd1987 [$e addTechVia [V VIA23]]
$e newPath $jd1987 FIXED
$e addPoint 6622857 2296170
set jd1988 [$e addTechVia [V VIA12]]
$e newPath $jd1988 FIXED
$e addITerm [IT L_clk_t122 A]
$e newPath $emj1818 FIXED [RL M9]
set jd1989 [$e addTechVia [V {VIA89}]]
$e newPath $jd1989 FIXED [RL M8]
$e addPoint 7445320 2160090
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445320 2160170
set jd1990 [$e addTechVia [V VIA67]]
$e newPath $jd1990 FIXED
$e addPoint 7445240 2160170
set jd1991 [$e addTechVia [V VIA56]]
$e newPath $jd1991 FIXED
$e addPoint 7445240 2160266
set jd1992 [$e addTechVia [V VIA45]]
$e newPath $jd1992 FIXED
$e addPoint 7445144 2160266
set jd1993 [$e addTechVia [V VIA34]]
$e newPath $jd1993 FIXED
$e addPoint 7445144 2160090
set jd1994 [$e addTechVia [V VIA23]]
$e newPath $jd1994 FIXED
$e addPoint 7445331 2160090
set jd1995 [$e addTechVia [V VIA12]]
$e newPath $jd1995 FIXED
$e addITerm [IT L_clk_t123 A]
$e newPath $emj1767 FIXED [RL M9]
set jd1996 [$e addTechVia [V {VIA89}]]
$e newPath $jd1996 FIXED [RL M8]
$e addPoint 7631080 2024010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7631080 2024090
set jd1997 [$e addTechVia [V VIA67]]
$e newPath $jd1997 FIXED
$e addPoint 7631000 2024090
set jd1998 [$e addTechVia [V VIA56]]
$e newPath $jd1998 FIXED
$e addPoint 7631000 2024186
set jd1999 [$e addTechVia [V VIA45]]
$e newPath $jd1999 FIXED
$e addPoint 7629575 2024186
set jd2000 [$e addTechVia [V VIA34]]
$e newPath $jd2000 FIXED
$e addPoint 7629575 2024010
set jd2001 [$e addTechVia [V VIA23]]
$e newPath $jd2001 FIXED
$e addPoint 7629525 2024010
set jd2002 [$e addTechVia [V VIA12]]
$e newPath $jd2002 FIXED
$e addITerm [IT L_clk_t124 A]
$e newPath $emj2110 FIXED [RL M9]
set jd2003 [$e addTechVia [V {VIA89}]]
$e newPath $jd2003 FIXED [RL M8]
$e addPoint 8171080 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 8171080 2296250
set jd2004 [$e addTechVia [V VIA67]]
$e newPath $jd2004 FIXED
$e addPoint 8171000 2296250
set jd2005 [$e addTechVia [V VIA56]]
$e newPath $jd2005 FIXED
$e addPoint 8171000 2296346
set jd2006 [$e addTechVia [V VIA45]]
$e newPath $jd2006 FIXED
$e addPoint 8169845 2296346
set jd2007 [$e addTechVia [V VIA34]]
$e newPath $jd2007 FIXED
$e addPoint 8169845 2296170
set jd2008 [$e addTechVia [V VIA23]]
$e newPath $jd2008 FIXED
$e addPoint 8169795 2296170
set jd2009 [$e addTechVia [V VIA12]]
$e newPath $jd2009 FIXED
$e addITerm [IT L_clk_t125 A]
$e newPath $emj681 FIXED [RL M9]
set jd2010 [$e addTechVia [V {VIA89}]]
$e newPath $jd2010 FIXED [RL M8]
$e addPoint 196360 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 196360 2564090
set jd2011 [$e addTechVia [V VIA67]]
$e newPath $jd2011 FIXED
$e addPoint 196280 2564090
set jd2012 [$e addTechVia [V VIA56]]
$e newPath $jd2012 FIXED
$e addPoint 196280 2564186
set jd2013 [$e addTechVia [V VIA45]]
$e newPath $jd2013 FIXED
$e addPoint 195503 2564186
set jd2014 [$e addTechVia [V VIA34]]
$e newPath $jd2014 FIXED
$e addPoint 195503 2564010
set jd2015 [$e addTechVia [V VIA23]]
$e newPath $jd2015 FIXED
$e addPoint 195453 2564010
set jd2016 [$e addTechVia [V VIA12]]
$e newPath $jd2016 FIXED
$e addITerm [IT L_clk_t126 A]
$e newPath $emj682 FIXED [RL M9]
set jd2017 [$e addTechVia [V {VIA89}]]
$e newPath $jd2017 FIXED [RL M8]
$e addPoint 585560 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 585560 2564090
set jd2018 [$e addTechVia [V VIA67]]
$e newPath $jd2018 FIXED
$e addPoint 585640 2564090
set jd2019 [$e addTechVia [V VIA56]]
$e newPath $jd2019 FIXED
$e addPoint 585640 2564186
set jd2020 [$e addTechVia [V VIA45]]
$e newPath $jd2020 FIXED
$e addPoint 586687 2564186
set jd2021 [$e addTechVia [V VIA34]]
$e newPath $jd2021 FIXED
$e addPoint 586687 2564010
set jd2022 [$e addTechVia [V VIA23]]
$e newPath $jd2022 FIXED
$e addPoint 586737 2564010
set jd2023 [$e addTechVia [V VIA12]]
$e newPath $jd2023 FIXED
$e addITerm [IT L_clk_t127 A]
$e newPath $emj635 FIXED [RL M9]
set jd2024 [$e addTechVia [V {VIA89}]]
$e newPath $jd2024 FIXED [RL M8]
$e addPoint 957080 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 957080 2564090
set jd2025 [$e addTechVia [V VIA67]]
$e newPath $jd2025 FIXED
$e addPoint 957160 2564090
set jd2026 [$e addTechVia [V VIA56]]
$e newPath $jd2026 FIXED
$e addPoint 957160 2564186
set jd2027 [$e addTechVia [V VIA45]]
$e newPath $jd2027 FIXED
$e addPoint 958315 2564186
set jd2028 [$e addTechVia [V VIA34]]
$e newPath $jd2028 FIXED
$e addPoint 958315 2564010
set jd2029 [$e addTechVia [V VIA23]]
$e newPath $jd2029 FIXED
$e addPoint 958365 2564010
set jd2030 [$e addTechVia [V VIA12]]
$e newPath $jd2030 FIXED
$e addITerm [IT L_clk_t128 A]
$e newPath $emj753 FIXED [RL M9]
set jd2031 [$e addTechVia [V {VIA89}]]
$e newPath $jd2031 FIXED [RL M8]
$e addPoint 1285000 2479230
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1285000 2479310
set jd2032 [$e addTechVia [V VIA67]]
$e newPath $jd2032 FIXED
$e addPoint 1284920 2479310
set jd2033 [$e addTechVia [V VIA56]]
$e newPath $jd2033 FIXED
$e addPoint 1284920 2479406
set jd2034 [$e addTechVia [V VIA45]]
$e newPath $jd2034 FIXED
$e addPoint 1284824 2479406
set jd2035 [$e addTechVia [V VIA34]]
$e newPath $jd2035 FIXED
$e addPoint 1284824 2479230
set jd2036 [$e addTechVia [V VIA23]]
$e newPath $jd2036 FIXED
$e addPoint 1285011 2479230
set jd2037 [$e addTechVia [V VIA12]]
$e newPath $jd2037 FIXED
$e addITerm [IT L_clk_t129 A]
$e newPath $emj770 FIXED [RL M9]
set jd2038 [$e addTechVia [V {VIA89}]]
$e newPath $jd2038 FIXED [RL M8]
$e addPoint 5259800 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5259800 136250
set jd2039 [$e addTechVia [V VIA67]]
$e newPath $jd2039 FIXED
$e addPoint 5259880 136250
set jd2040 [$e addTechVia [V VIA56]]
$e newPath $jd2040 FIXED
$e addPoint 5259880 136346
set jd2041 [$e addTechVia [V VIA45]]
$e newPath $jd2041 FIXED
$e addPoint 5260279 136346
set jd2042 [$e addTechVia [V VIA34]]
$e newPath $jd2042 FIXED
$e addPoint 5260279 136170
set jd2043 [$e addTechVia [V VIA23]]
$e newPath $jd2043 FIXED
$e addPoint 5260329 136170
set jd2044 [$e addTechVia [V VIA12]]
$e newPath $jd2044 FIXED
$e addITerm [IT L_clk_t13 A]
$e newPath $emj900 FIXED [RL M9]
set jd2045 [$e addTechVia [V {VIA89}]]
$e newPath $jd2045 FIXED [RL M8]
$e addPoint 1682840 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1682840 2564090
set jd2046 [$e addTechVia [V VIA67]]
$e newPath $jd2046 FIXED
$e addPoint 1682920 2564090
set jd2047 [$e addTechVia [V VIA56]]
$e newPath $jd2047 FIXED
$e addPoint 1682920 2564186
set jd2048 [$e addTechVia [V VIA45]]
$e newPath $jd2048 FIXED
$e addPoint 1683016 2564186
set jd2049 [$e addTechVia [V VIA34]]
$e newPath $jd2049 FIXED
$e addPoint 1683016 2564010
set jd2050 [$e addTechVia [V VIA23]]
$e newPath $jd2050 FIXED
$e addPoint 1682775 2564010
set jd2051 [$e addTechVia [V VIA12]]
$e newPath $jd2051 FIXED
$e addITerm [IT L_clk_t130 A]
$e newPath $emj1110 FIXED [RL M9]
set jd2052 [$e addTechVia [V {VIA89}]]
$e newPath $jd2052 FIXED [RL M8]
$e addPoint 2308840 2669310
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2308840 2669390
set jd2053 [$e addTechVia [V VIA67]]
$e newPath $jd2053 FIXED
$e addPoint 2308760 2669390
set jd2054 [$e addTechVia [V VIA56]]
$e newPath $jd2054 FIXED
$e addPoint 2308760 2669486
set jd2055 [$e addTechVia [V VIA45]]
$e newPath $jd2055 FIXED
$e addPoint 2308664 2669486
set jd2056 [$e addTechVia [V VIA34]]
$e newPath $jd2056 FIXED
$e addPoint 2308664 2669310
set jd2057 [$e addTechVia [V VIA23]]
$e newPath $jd2057 FIXED
$e addPoint 2308851 2669310
set jd2058 [$e addTechVia [V VIA12]]
$e newPath $jd2058 FIXED
$e addITerm [IT L_clk_t131 A]
$e newPath $emj1112 FIXED [RL M9]
set jd2059 [$e addTechVia [V {VIA89}]]
$e newPath $jd2059 FIXED [RL M8]
$e addPoint 2399960 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2399960 2564090
set jd2060 [$e addTechVia [V VIA67]]
$e newPath $jd2060 FIXED
$e addPoint 2400040 2564090
set jd2061 [$e addTechVia [V VIA56]]
$e newPath $jd2061 FIXED
$e addPoint 2400040 2564186
set jd2062 [$e addTechVia [V VIA45]]
$e newPath $jd2062 FIXED
$e addPoint 2400439 2564186
set jd2063 [$e addTechVia [V VIA34]]
$e newPath $jd2063 FIXED
$e addPoint 2400439 2564010
set jd2064 [$e addTechVia [V VIA23]]
$e newPath $jd2064 FIXED
$e addPoint 2400489 2564010
set jd2065 [$e addTechVia [V VIA12]]
$e newPath $jd2065 FIXED
$e addITerm [IT L_clk_t132 A]
$e newPath $emj1368 FIXED [RL M9]
set jd2066 [$e addTechVia [V {VIA89}]]
$e newPath $jd2066 FIXED [RL M8]
$e addPoint 3198760 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3198760 2564090
set jd2067 [$e addTechVia [V VIA67]]
$e newPath $jd2067 FIXED
$e addPoint 3198680 2564090
set jd2068 [$e addTechVia [V VIA56]]
$e newPath $jd2068 FIXED
$e addPoint 3198680 2564186
set jd2069 [$e addTechVia [V VIA45]]
$e newPath $jd2069 FIXED
$e addPoint 3197903 2564186
set jd2070 [$e addTechVia [V VIA34]]
$e newPath $jd2070 FIXED
$e addPoint 3197903 2564010
set jd2071 [$e addTechVia [V VIA23]]
$e newPath $jd2071 FIXED
$e addPoint 3197853 2564010
set jd2072 [$e addTechVia [V VIA12]]
$e newPath $jd2072 FIXED
$e addITerm [IT L_clk_t133 A]
$e newPath $emj1438 FIXED [RL M9]
set jd2073 [$e addTechVia [V {VIA89}]]
$e newPath $jd2073 FIXED [RL M8]
$e addPoint 3281240 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3281240 2564090
set jd2074 [$e addTechVia [V VIA67]]
$e newPath $jd2074 FIXED
$e addPoint 3281320 2564090
set jd2075 [$e addTechVia [V VIA56]]
$e newPath $jd2075 FIXED
$e addPoint 3281320 2564186
set jd2076 [$e addTechVia [V VIA45]]
$e newPath $jd2076 FIXED
$e addPoint 3282367 2564186
set jd2077 [$e addTechVia [V VIA34]]
$e newPath $jd2077 FIXED
$e addPoint 3282367 2564010
set jd2078 [$e addTechVia [V VIA23]]
$e newPath $jd2078 FIXED
$e addPoint 3282417 2564010
set jd2079 [$e addTechVia [V VIA12]]
$e newPath $jd2079 FIXED
$e addITerm [IT L_clk_t134 A]
$e newPath $emj1508 FIXED [RL M9]
set jd2080 [$e addTechVia [V {VIA89}]]
$e newPath $jd2080 FIXED [RL M8]
$e addPoint 3557720 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3557720 2836250
set jd2081 [$e addTechVia [V VIA67]]
$e newPath $jd2081 FIXED
$e addPoint 3557800 2836250
set jd2082 [$e addTechVia [V VIA56]]
$e newPath $jd2082 FIXED
$e addPoint 3557800 2836346
set jd2083 [$e addTechVia [V VIA45]]
$e newPath $jd2083 FIXED
$e addPoint 3558955 2836346
set jd2084 [$e addTechVia [V VIA34]]
$e newPath $jd2084 FIXED
$e addPoint 3558955 2836170
set jd2085 [$e addTechVia [V VIA23]]
$e newPath $jd2085 FIXED
$e addPoint 3559005 2836170
set jd2086 [$e addTechVia [V VIA12]]
$e newPath $jd2086 FIXED
$e addITerm [IT L_clk_t135 A]
$e newPath $emj1430 FIXED [RL M9]
set jd2087 [$e addTechVia [V {VIA89}]]
$e newPath $jd2087 FIXED [RL M8]
$e addPoint 4106360 2296170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4106360 2296250
set jd2088 [$e addTechVia [V VIA67]]
$e newPath $jd2088 FIXED
$e addPoint 4106440 2296250
set jd2089 [$e addTechVia [V VIA56]]
$e newPath $jd2089 FIXED
$e addPoint 4106440 2296346
set jd2090 [$e addTechVia [V VIA45]]
$e newPath $jd2090 FIXED
$e addPoint 4108027 2296346
set jd2091 [$e addTechVia [V VIA34]]
$e newPath $jd2091 FIXED
$e addPoint 4108027 2296170
set jd2092 [$e addTechVia [V VIA23]]
$e newPath $jd2092 FIXED
$e addPoint 4108077 2296170
set jd2093 [$e addTechVia [V VIA12]]
$e newPath $jd2093 FIXED
$e addITerm [IT L_clk_t136 A]
$e newPath $emj1735 FIXED [RL M9]
set jd2094 [$e addTechVia [V {VIA89}]]
$e newPath $jd2094 FIXED [RL M8]
$e addPoint 4533640 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4533640 2564090
set jd2095 [$e addTechVia [V VIA67]]
$e newPath $jd2095 FIXED
$e addPoint 4533560 2564090
set jd2096 [$e addTechVia [V VIA56]]
$e newPath $jd2096 FIXED
$e addPoint 4533560 2564186
set jd2097 [$e addTechVia [V VIA45]]
$e newPath $jd2097 FIXED
$e addPoint 4532027 2564186
set jd2098 [$e addTechVia [V VIA34]]
$e newPath $jd2098 FIXED
$e addPoint 4532027 2564010
set jd2099 [$e addTechVia [V VIA23]]
$e newPath $jd2099 FIXED
$e addPoint 4531977 2564010
set jd2100 [$e addTechVia [V VIA12]]
$e newPath $jd2100 FIXED
$e addITerm [IT L_clk_t137 A]
$e newPath $emj1682 FIXED [RL M9]
set jd2101 [$e addTechVia [V {VIA89}]]
$e newPath $jd2101 FIXED [RL M8]
$e addPoint 4879240 2453310
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879240 2453390
set jd2102 [$e addTechVia [V VIA67]]
$e newPath $jd2102 FIXED
$e addPoint 4879160 2453390
set jd2103 [$e addTechVia [V VIA56]]
$e newPath $jd2103 FIXED
$e addPoint 4879160 2453486
set jd2104 [$e addTechVia [V VIA45]]
$e newPath $jd2104 FIXED
$e addPoint 4879064 2453486
set jd2105 [$e addTechVia [V VIA34]]
$e newPath $jd2105 FIXED
$e addPoint 4879064 2453310
set jd2106 [$e addTechVia [V VIA23]]
$e newPath $jd2106 FIXED
$e addPoint 4879251 2453310
set jd2107 [$e addTechVia [V VIA12]]
$e newPath $jd2107 FIXED
$e addITerm [IT L_clk_t138 A]
$e newPath $emj1421 FIXED [RL M9]
set jd2108 [$e addTechVia [V {VIA89}]]
$e newPath $jd2108 FIXED [RL M8]
$e addPoint 5393320 2453310
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5393320 2453390
set jd2109 [$e addTechVia [V VIA67]]
$e newPath $jd2109 FIXED
$e addPoint 5393240 2453390
set jd2110 [$e addTechVia [V VIA56]]
$e newPath $jd2110 FIXED
$e addPoint 5393240 2453486
set jd2111 [$e addTechVia [V VIA45]]
$e newPath $jd2111 FIXED
$e addPoint 5393144 2453486
set jd2112 [$e addTechVia [V VIA34]]
$e newPath $jd2112 FIXED
$e addPoint 5393144 2453310
set jd2113 [$e addTechVia [V VIA23]]
$e newPath $jd2113 FIXED
$e addPoint 5393331 2453310
set jd2114 [$e addTechVia [V VIA12]]
$e newPath $jd2114 FIXED
$e addITerm [IT L_clk_t139 A]
$e newPath $emj772 FIXED [RL M9]
set jd2115 [$e addTechVia [V {VIA89}]]
$e newPath $jd2115 FIXED [RL M8]
$e addPoint 5674120 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5674120 136250
set jd2116 [$e addTechVia [V VIA67]]
$e newPath $jd2116 FIXED
$e addPoint 5674040 136250
set jd2117 [$e addTechVia [V VIA56]]
$e newPath $jd2117 FIXED
$e addPoint 5674040 136346
set jd2118 [$e addTechVia [V VIA45]]
$e newPath $jd2118 FIXED
$e addPoint 5673263 136346
set jd2119 [$e addTechVia [V VIA34]]
$e newPath $jd2119 FIXED
$e addPoint 5673263 136170
set jd2120 [$e addTechVia [V VIA23]]
$e newPath $jd2120 FIXED
$e addPoint 5673213 136170
set jd2121 [$e addTechVia [V VIA12]]
$e newPath $jd2121 FIXED
$e addITerm [IT L_clk_t14 A]
$e newPath $emj1830 FIXED [RL M9]
set jd2122 [$e addTechVia [V {VIA89}]]
$e newPath $jd2122 FIXED [RL M8]
$e addPoint 5674120 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5674120 2564090
set jd2123 [$e addTechVia [V VIA67]]
$e newPath $jd2123 FIXED
$e addPoint 5674040 2564090
set jd2124 [$e addTechVia [V VIA56]]
$e newPath $jd2124 FIXED
$e addPoint 5674040 2564186
set jd2125 [$e addTechVia [V VIA45]]
$e newPath $jd2125 FIXED
$e addPoint 5673263 2564186
set jd2126 [$e addTechVia [V VIA34]]
$e newPath $jd2126 FIXED
$e addPoint 5673263 2564010
set jd2127 [$e addTechVia [V VIA23]]
$e newPath $jd2127 FIXED
$e addPoint 5673213 2564010
set jd2128 [$e addTechVia [V VIA12]]
$e newPath $jd2128 FIXED
$e addITerm [IT L_clk_t140 A]
$e newPath $emj1881 FIXED [RL M9]
set jd2129 [$e addTechVia [V {VIA89}]]
$e newPath $jd2129 FIXED [RL M8]
$e addPoint 5942360 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5942360 2564090
set jd2130 [$e addTechVia [V VIA67]]
$e newPath $jd2130 FIXED
$e addPoint 5942440 2564090
set jd2131 [$e addTechVia [V VIA56]]
$e newPath $jd2131 FIXED
$e addPoint 5942440 2564186
set jd2132 [$e addTechVia [V VIA45]]
$e newPath $jd2132 FIXED
$e addPoint 5943487 2564186
set jd2133 [$e addTechVia [V VIA34]]
$e newPath $jd2133 FIXED
$e addPoint 5943487 2564010
set jd2134 [$e addTechVia [V VIA23]]
$e newPath $jd2134 FIXED
$e addPoint 5943537 2564010
set jd2135 [$e addTechVia [V VIA12]]
$e newPath $jd2135 FIXED
$e addITerm [IT L_clk_t141 A]
$e newPath $emj1942 FIXED [RL M9]
set jd2136 [$e addTechVia [V {VIA89}]]
$e newPath $jd2136 FIXED [RL M8]
$e addPoint 6417160 2669310
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6417160 2669390
set jd2137 [$e addTechVia [V VIA67]]
$e newPath $jd2137 FIXED
$e addPoint 6417080 2669390
set jd2138 [$e addTechVia [V VIA56]]
$e newPath $jd2138 FIXED
$e addPoint 6417080 2669486
set jd2139 [$e addTechVia [V VIA45]]
$e newPath $jd2139 FIXED
$e addPoint 6416984 2669486
set jd2140 [$e addTechVia [V VIA34]]
$e newPath $jd2140 FIXED
$e addPoint 6416984 2669310
set jd2141 [$e addTechVia [V VIA23]]
$e newPath $jd2141 FIXED
$e addPoint 6417171 2669310
set jd2142 [$e addTechVia [V VIA12]]
$e newPath $jd2142 FIXED
$e addITerm [IT L_clk_t142 A]
$e newPath $emj2032 FIXED [RL M9]
set jd2143 [$e addTechVia [V {VIA89}]]
$e newPath $jd2143 FIXED [RL M8]
$e addPoint 6633160 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6633160 2564090
set jd2144 [$e addTechVia [V VIA67]]
$e newPath $jd2144 FIXED
$e addPoint 6633080 2564090
set jd2145 [$e addTechVia [V VIA56]]
$e newPath $jd2145 FIXED
$e addPoint 6633080 2564186
set jd2146 [$e addTechVia [V VIA45]]
$e newPath $jd2146 FIXED
$e addPoint 6632984 2564186
set jd2147 [$e addTechVia [V VIA34]]
$e newPath $jd2147 FIXED
$e addPoint 6632984 2564010
set jd2148 [$e addTechVia [V VIA23]]
$e newPath $jd2148 FIXED
$e addPoint 6633171 2564010
set jd2149 [$e addTechVia [V VIA12]]
$e newPath $jd2149 FIXED
$e addITerm [IT L_clk_t143 A]
$e newPath $emj1986 FIXED [RL M9]
set jd2150 [$e addTechVia [V {VIA89}]]
$e newPath $jd2150 FIXED [RL M8]
$e addPoint 7445320 2553030
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445320 2553110
set jd2151 [$e addTechVia [V VIA67]]
$e newPath $jd2151 FIXED
$e addPoint 7445240 2553110
set jd2152 [$e addTechVia [V VIA56]]
$e newPath $jd2152 FIXED
$e addPoint 7445240 2553206
set jd2153 [$e addTechVia [V VIA45]]
$e newPath $jd2153 FIXED
$e addPoint 7445144 2553206
set jd2154 [$e addTechVia [V VIA34]]
$e newPath $jd2154 FIXED
$e addPoint 7445144 2553030
set jd2155 [$e addTechVia [V VIA23]]
$e newPath $jd2155 FIXED
$e addPoint 7445331 2553030
set jd2156 [$e addTechVia [V VIA12]]
$e newPath $jd2156 FIXED
$e addITerm [IT L_clk_t144 A]
$e newPath $emj2075 FIXED [RL M9]
set jd2157 [$e addTechVia [V {VIA89}]]
$e newPath $jd2157 FIXED [RL M8]
$e addPoint 7532120 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7532120 2564090
set jd2158 [$e addTechVia [V VIA67]]
$e newPath $jd2158 FIXED
$e addPoint 7532200 2564090
set jd2159 [$e addTechVia [V VIA56]]
$e newPath $jd2159 FIXED
$e addPoint 7532200 2564186
set jd2160 [$e addTechVia [V VIA45]]
$e newPath $jd2160 FIXED
$e addPoint 7532104 2564186
set jd2161 [$e addTechVia [V VIA34]]
$e newPath $jd2161 FIXED
$e addPoint 7532104 2564010
set jd2162 [$e addTechVia [V VIA23]]
$e newPath $jd2162 FIXED
$e addPoint 7532325 2564010
set jd2163 [$e addTechVia [V VIA12]]
$e newPath $jd2163 FIXED
$e addITerm [IT L_clk_t145 A]
$e newPath $emj2152 FIXED [RL M9]
set jd2164 [$e addTechVia [V {VIA89}]]
$e newPath $jd2164 FIXED [RL M8]
$e addPoint 8175400 2564010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 8175400 2564090
set jd2165 [$e addTechVia [V VIA67]]
$e newPath $jd2165 FIXED
$e addPoint 8175320 2564090
set jd2166 [$e addTechVia [V VIA56]]
$e newPath $jd2166 FIXED
$e addPoint 8175320 2564186
set jd2167 [$e addTechVia [V VIA45]]
$e newPath $jd2167 FIXED
$e addPoint 8174219 2564186
set jd2168 [$e addTechVia [V VIA34]]
$e newPath $jd2168 FIXED
$e addPoint 8174219 2564010
set jd2169 [$e addTechVia [V VIA23]]
$e newPath $jd2169 FIXED
$e addPoint 8174169 2564010
set jd2170 [$e addTechVia [V VIA12]]
$e newPath $jd2170 FIXED
$e addITerm [IT L_clk_t146 A]
$e newPath $emj1047 FIXED [RL M9]
set jd2171 [$e addTechVia [V {VIA89}]]
$e newPath $jd2171 FIXED [RL M8]
$e addPoint 196360 3104010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 196360 3104090
set jd2172 [$e addTechVia [V VIA67]]
$e newPath $jd2172 FIXED
$e addPoint 196280 3104090
set jd2173 [$e addTechVia [V VIA56]]
$e newPath $jd2173 FIXED
$e addPoint 196280 3104186
set jd2174 [$e addTechVia [V VIA45]]
$e newPath $jd2174 FIXED
$e addPoint 195503 3104186
set jd2175 [$e addTechVia [V VIA34]]
$e newPath $jd2175 FIXED
$e addPoint 195503 3104010
set jd2176 [$e addTechVia [V VIA23]]
$e newPath $jd2176 FIXED
$e addPoint 195453 3104010
set jd2177 [$e addTechVia [V VIA12]]
$e newPath $jd2177 FIXED
$e addITerm [IT L_clk_t147 A]
$e newPath $emj1045 FIXED [RL M9]
set jd2178 [$e addTechVia [V {VIA89}]]
$e newPath $jd2178 FIXED [RL M8]
$e addPoint 585560 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 585560 2836250
set jd2179 [$e addTechVia [V VIA67]]
$e newPath $jd2179 FIXED
$e addPoint 585640 2836250
set jd2180 [$e addTechVia [V VIA56]]
$e newPath $jd2180 FIXED
$e addPoint 585640 2836346
set jd2181 [$e addTechVia [V VIA45]]
$e newPath $jd2181 FIXED
$e addPoint 586687 2836346
set jd2182 [$e addTechVia [V VIA34]]
$e newPath $jd2182 FIXED
$e addPoint 586687 2836170
set jd2183 [$e addTechVia [V VIA23]]
$e newPath $jd2183 FIXED
$e addPoint 586737 2836170
set jd2184 [$e addTechVia [V VIA12]]
$e newPath $jd2184 FIXED
$e addITerm [IT L_clk_t148 A]
$e newPath $emj1052 FIXED [RL M9]
set jd2185 [$e addTechVia [V {VIA89}]]
$e newPath $jd2185 FIXED [RL M8]
$e addPoint 978280 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 978280 2836250
set jd2186 [$e addTechVia [V VIA67]]
$e newPath $jd2186 FIXED
$e addPoint 978200 2836250
set jd2187 [$e addTechVia [V VIA56]]
$e newPath $jd2187 FIXED
$e addPoint 978200 2836346
set jd2188 [$e addTechVia [V VIA45]]
$e newPath $jd2188 FIXED
$e addPoint 978017 2836346
set jd2189 [$e addTechVia [V VIA34]]
$e newPath $jd2189 FIXED
$e addPoint 978017 2836170
set jd2190 [$e addTechVia [V VIA23]]
$e newPath $jd2190 FIXED
$e addPoint 977967 2836170
set jd2191 [$e addTechVia [V VIA12]]
$e newPath $jd2191 FIXED
$e addITerm [IT L_clk_t149 A]
$e newPath $emj768 FIXED [RL M9]
set jd2192 [$e addTechVia [V {VIA89}]]
$e newPath $jd2192 FIXED [RL M8]
$e addPoint 5907400 17190
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907400 17270
set jd2193 [$e addTechVia [V VIA67]]
$e newPath $jd2193 FIXED
$e addPoint 5907320 17270
set jd2194 [$e addTechVia [V VIA56]]
$e newPath $jd2194 FIXED
$e addPoint 5907320 17366
set jd2195 [$e addTechVia [V VIA45]]
$e newPath $jd2195 FIXED
$e addPoint 5907224 17366
set jd2196 [$e addTechVia [V VIA34]]
$e newPath $jd2196 FIXED
$e addPoint 5907224 17190
set jd2197 [$e addTechVia [V VIA23]]
$e newPath $jd2197 FIXED
$e addPoint 5907411 17190
set jd2198 [$e addTechVia [V VIA12]]
$e newPath $jd2198 FIXED
$e addITerm [IT L_clk_t15 A]
$e newPath $emj1055 FIXED [RL M9]
set jd2199 [$e addTechVia [V {VIA89}]]
$e newPath $jd2199 FIXED [RL M8]
$e addPoint 1285000 2945610
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1285000 2945690
set jd2200 [$e addTechVia [V VIA67]]
$e newPath $jd2200 FIXED
$e addPoint 1284920 2945690
set jd2201 [$e addTechVia [V VIA56]]
$e newPath $jd2201 FIXED
$e addPoint 1284920 2945786
set jd2202 [$e addTechVia [V VIA45]]
$e newPath $jd2202 FIXED
$e addPoint 1284824 2945786
set jd2203 [$e addTechVia [V VIA34]]
$e newPath $jd2203 FIXED
$e addPoint 1284824 2945610
set jd2204 [$e addTechVia [V VIA23]]
$e newPath $jd2204 FIXED
$e addPoint 1285011 2945610
set jd2205 [$e addTechVia [V VIA12]]
$e newPath $jd2205 FIXED
$e addITerm [IT L_clk_t150 A]
$e newPath $emj1043 FIXED [RL M9]
set jd2206 [$e addTechVia [V {VIA89}]]
$e newPath $jd2206 FIXED [RL M8]
$e addPoint 1799080 2959650
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1799080 2959730
set jd2207 [$e addTechVia [V VIA67]]
$e newPath $jd2207 FIXED
$e addPoint 1799000 2959730
set jd2208 [$e addTechVia [V VIA56]]
$e newPath $jd2208 FIXED
$e addPoint 1799000 2959826
set jd2209 [$e addTechVia [V VIA45]]
$e newPath $jd2209 FIXED
$e addPoint 1798904 2959826
set jd2210 [$e addTechVia [V VIA34]]
$e newPath $jd2210 FIXED
$e addPoint 1798904 2959650
set jd2211 [$e addTechVia [V VIA23]]
$e newPath $jd2211 FIXED
$e addPoint 1799091 2959650
set jd2212 [$e addTechVia [V VIA12]]
$e newPath $jd2212 FIXED
$e addITerm [IT L_clk_t151 A]
$e newPath $emj1249 FIXED [RL M9]
set jd2213 [$e addTechVia [V {VIA89}]]
$e newPath $jd2213 FIXED [RL M8]
$e addPoint 2153320 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2153320 2836250
set jd2214 [$e addTechVia [V VIA67]]
$e newPath $jd2214 FIXED
$e addPoint 2153240 2836250
set jd2215 [$e addTechVia [V VIA56]]
$e newPath $jd2215 FIXED
$e addPoint 2153240 2836346
set jd2216 [$e addTechVia [V VIA45]]
$e newPath $jd2216 FIXED
$e addPoint 2151815 2836346
set jd2217 [$e addTechVia [V VIA34]]
$e newPath $jd2217 FIXED
$e addPoint 2151815 2836170
set jd2218 [$e addTechVia [V VIA23]]
$e newPath $jd2218 FIXED
$e addPoint 2151765 2836170
set jd2219 [$e addTechVia [V VIA12]]
$e newPath $jd2219 FIXED
$e addITerm [IT L_clk_t152 A]
$e newPath $emj1519 FIXED [RL M9]
set jd2220 [$e addTechVia [V {VIA89}]]
$e newPath $jd2220 FIXED [RL M8]
$e addPoint 2533880 3104010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2533880 3104090
set jd2221 [$e addTechVia [V VIA67]]
$e newPath $jd2221 FIXED
$e addPoint 2533960 3104090
set jd2222 [$e addTechVia [V VIA56]]
$e newPath $jd2222 FIXED
$e addPoint 2533960 3104186
set jd2223 [$e addTechVia [V VIA45]]
$e newPath $jd2223 FIXED
$e addPoint 2535007 3104186
set jd2224 [$e addTechVia [V VIA34]]
$e newPath $jd2224 FIXED
$e addPoint 2535007 3104010
set jd2225 [$e addTechVia [V VIA23]]
$e newPath $jd2225 FIXED
$e addPoint 2535057 3104010
set jd2226 [$e addTechVia [V VIA12]]
$e newPath $jd2226 FIXED
$e addITerm [IT L_clk_t153 A]
$e newPath $emj1579 FIXED [RL M9]
set jd2227 [$e addTechVia [V {VIA89}]]
$e newPath $jd2227 FIXED [RL M8]
$e addPoint 2956840 3104010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2956840 3104090
set jd2228 [$e addTechVia [V VIA67]]
$e newPath $jd2228 FIXED
$e addPoint 2956760 3104090
set jd2229 [$e addTechVia [V VIA56]]
$e newPath $jd2229 FIXED
$e addPoint 2956760 3104186
set jd2230 [$e addTechVia [V VIA45]]
$e newPath $jd2230 FIXED
$e addPoint 2956361 3104186
set jd2231 [$e addTechVia [V VIA34]]
$e newPath $jd2231 FIXED
$e addPoint 2956361 3104010
set jd2232 [$e addTechVia [V VIA23]]
$e newPath $jd2232 FIXED
$e addPoint 2956311 3104010
set jd2233 [$e addTechVia [V VIA12]]
$e newPath $jd2233 FIXED
$e addITerm [IT L_clk_t154 A]
$e newPath $emj1511 FIXED [RL M9]
set jd2234 [$e addTechVia [V {VIA89}]]
$e newPath $jd2234 FIXED [RL M8]
$e addPoint 3337000 2945610
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337000 2945690
set jd2235 [$e addTechVia [V VIA67]]
$e newPath $jd2235 FIXED
$e addPoint 3336920 2945690
set jd2236 [$e addTechVia [V VIA56]]
$e newPath $jd2236 FIXED
$e addPoint 3336920 2945786
set jd2237 [$e addTechVia [V VIA45]]
$e newPath $jd2237 FIXED
$e addPoint 3336824 2945786
set jd2238 [$e addTechVia [V VIA34]]
$e newPath $jd2238 FIXED
$e addPoint 3336824 2945610
set jd2239 [$e addTechVia [V VIA23]]
$e newPath $jd2239 FIXED
$e addPoint 3337011 2945610
set jd2240 [$e addTechVia [V VIA12]]
$e newPath $jd2240 FIXED
$e addITerm [IT L_clk_t155 A]
$e newPath $emj1637 FIXED [RL M9]
set jd2241 [$e addTechVia [V {VIA89}]]
$e newPath $jd2241 FIXED [RL M8]
$e addPoint 3644120 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3644120 2836250
set jd2242 [$e addTechVia [V VIA67]]
$e newPath $jd2242 FIXED
$e addPoint 3644200 2836250
set jd2243 [$e addTechVia [V VIA56]]
$e newPath $jd2243 FIXED
$e addPoint 3644200 2836346
set jd2244 [$e addTechVia [V VIA45]]
$e newPath $jd2244 FIXED
$e addPoint 3645355 2836346
set jd2245 [$e addTechVia [V VIA34]]
$e newPath $jd2245 FIXED
$e addPoint 3645355 2836170
set jd2246 [$e addTechVia [V VIA23]]
$e newPath $jd2246 FIXED
$e addPoint 3645405 2836170
set jd2247 [$e addTechVia [V VIA12]]
$e newPath $jd2247 FIXED
$e addITerm [IT L_clk_t156 A]
$e newPath $emj1737 FIXED [RL M9]
set jd2248 [$e addTechVia [V {VIA89}]]
$e newPath $jd2248 FIXED [RL M8]
$e addPoint 4106360 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4106360 2836250
set jd2249 [$e addTechVia [V VIA67]]
$e newPath $jd2249 FIXED
$e addPoint 4106440 2836250
set jd2250 [$e addTechVia [V VIA56]]
$e newPath $jd2250 FIXED
$e addPoint 4106440 2836346
set jd2251 [$e addTechVia [V VIA45]]
$e newPath $jd2251 FIXED
$e addPoint 4107595 2836346
set jd2252 [$e addTechVia [V VIA34]]
$e newPath $jd2252 FIXED
$e addPoint 4107595 2836170
set jd2253 [$e addTechVia [V VIA23]]
$e newPath $jd2253 FIXED
$e addPoint 4107645 2836170
set jd2254 [$e addTechVia [V VIA12]]
$e newPath $jd2254 FIXED
$e addITerm [IT L_clk_t157 A]
$e newPath $emj1893 FIXED [RL M9]
set jd2255 [$e addTechVia [V {VIA89}]]
$e newPath $jd2255 FIXED [RL M8]
$e addPoint 4499480 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4499480 2836250
set jd2256 [$e addTechVia [V VIA67]]
$e newPath $jd2256 FIXED
$e addPoint 4499560 2836250
set jd2257 [$e addTechVia [V VIA56]]
$e newPath $jd2257 FIXED
$e addPoint 4499560 2836346
set jd2258 [$e addTechVia [V VIA45]]
$e newPath $jd2258 FIXED
$e addPoint 4499656 2836346
set jd2259 [$e addTechVia [V VIA34]]
$e newPath $jd2259 FIXED
$e addPoint 4499656 2836170
set jd2260 [$e addTechVia [V VIA23]]
$e newPath $jd2260 FIXED
$e addPoint 4499415 2836170
set jd2261 [$e addTechVia [V VIA12]]
$e newPath $jd2261 FIXED
$e addITerm [IT L_clk_t158 A]
$e newPath $emj1894 FIXED [RL M9]
set jd2262 [$e addTechVia [V {VIA89}]]
$e newPath $jd2262 FIXED [RL M8]
$e addPoint 4879240 2945610
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879240 2945690
set jd2263 [$e addTechVia [V VIA67]]
$e newPath $jd2263 FIXED
$e addPoint 4879160 2945690
set jd2264 [$e addTechVia [V VIA56]]
$e newPath $jd2264 FIXED
$e addPoint 4879160 2945786
set jd2265 [$e addTechVia [V VIA45]]
$e newPath $jd2265 FIXED
$e addPoint 4879064 2945786
set jd2266 [$e addTechVia [V VIA34]]
$e newPath $jd2266 FIXED
$e addPoint 4879064 2945610
set jd2267 [$e addTechVia [V VIA23]]
$e newPath $jd2267 FIXED
$e addPoint 4879251 2945610
set jd2268 [$e addTechVia [V VIA12]]
$e newPath $jd2268 FIXED
$e addITerm [IT L_clk_t159 A]
$e newPath $emj988 FIXED [RL M9]
set jd2269 [$e addTechVia [V {VIA89}]]
$e newPath $jd2269 FIXED [RL M8]
$e addPoint 6469400 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6469400 136250
set jd2270 [$e addTechVia [V VIA67]]
$e newPath $jd2270 FIXED
$e addPoint 6469480 136250
set jd2271 [$e addTechVia [V VIA56]]
$e newPath $jd2271 FIXED
$e addPoint 6469480 136346
set jd2272 [$e addTechVia [V VIA45]]
$e newPath $jd2272 FIXED
$e addPoint 6470635 136346
set jd2273 [$e addTechVia [V VIA34]]
$e newPath $jd2273 FIXED
$e addPoint 6470635 136170
set jd2274 [$e addTechVia [V VIA23]]
$e newPath $jd2274 FIXED
$e addPoint 6470685 136170
set jd2275 [$e addTechVia [V VIA12]]
$e newPath $jd2275 FIXED
$e addITerm [IT L_clk_t16 A]
$e newPath $emj1995 FIXED [RL M9]
set jd2276 [$e addTechVia [V {VIA89}]]
$e newPath $jd2276 FIXED [RL M8]
$e addPoint 5281400 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5281400 2836250
set jd2277 [$e addTechVia [V VIA67]]
$e newPath $jd2277 FIXED
$e addPoint 5281480 2836250
set jd2278 [$e addTechVia [V VIA56]]
$e newPath $jd2278 FIXED
$e addPoint 5281480 2836346
set jd2279 [$e addTechVia [V VIA45]]
$e newPath $jd2279 FIXED
$e addPoint 5281879 2836346
set jd2280 [$e addTechVia [V VIA34]]
$e newPath $jd2280 FIXED
$e addPoint 5281879 2836170
set jd2281 [$e addTechVia [V VIA23]]
$e newPath $jd2281 FIXED
$e addPoint 5281929 2836170
set jd2282 [$e addTechVia [V VIA12]]
$e newPath $jd2282 FIXED
$e addITerm [IT L_clk_t160 A]
$e newPath $emj1998 FIXED [RL M9]
set jd2283 [$e addTechVia [V {VIA89}]]
$e newPath $jd2283 FIXED [RL M8]
$e addPoint 5907400 2986650
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907400 2986730
set jd2284 [$e addTechVia [V VIA67]]
$e newPath $jd2284 FIXED
$e addPoint 5907320 2986730
set jd2285 [$e addTechVia [V VIA56]]
$e newPath $jd2285 FIXED
$e addPoint 5907320 2986826
set jd2286 [$e addTechVia [V VIA45]]
$e newPath $jd2286 FIXED
$e addPoint 5907224 2986826
set jd2287 [$e addTechVia [V VIA34]]
$e newPath $jd2287 FIXED
$e addPoint 5907224 2986650
set jd2288 [$e addTechVia [V VIA23]]
$e newPath $jd2288 FIXED
$e addPoint 5907411 2986650
set jd2289 [$e addTechVia [V VIA12]]
$e newPath $jd2289 FIXED
$e addITerm [IT L_clk_t161 A]
$e newPath $emj1997 FIXED [RL M9]
set jd2290 [$e addTechVia [V {VIA89}]]
$e newPath $jd2290 FIXED [RL M8]
$e addPoint 6020120 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6020120 2836250
set jd2291 [$e addTechVia [V VIA67]]
$e newPath $jd2291 FIXED
$e addPoint 6020200 2836250
set jd2292 [$e addTechVia [V VIA56]]
$e newPath $jd2292 FIXED
$e addPoint 6020200 2836346
set jd2293 [$e addTechVia [V VIA45]]
$e newPath $jd2293 FIXED
$e addPoint 6021247 2836346
set jd2294 [$e addTechVia [V VIA34]]
$e newPath $jd2294 FIXED
$e addPoint 6021247 2836170
set jd2295 [$e addTechVia [V VIA23]]
$e newPath $jd2295 FIXED
$e addPoint 6021297 2836170
set jd2296 [$e addTechVia [V VIA12]]
$e newPath $jd2296 FIXED
$e addITerm [IT L_clk_t162 A]
$e newPath $emj2084 FIXED [RL M9]
set jd2297 [$e addTechVia [V {VIA89}]]
$e newPath $jd2297 FIXED [RL M8]
$e addPoint 6417160 2945610
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6417160 2945690
set jd2298 [$e addTechVia [V VIA67]]
$e newPath $jd2298 FIXED
$e addPoint 6417080 2945690
set jd2299 [$e addTechVia [V VIA56]]
$e newPath $jd2299 FIXED
$e addPoint 6417080 2945786
set jd2300 [$e addTechVia [V VIA45]]
$e newPath $jd2300 FIXED
$e addPoint 6416984 2945786
set jd2301 [$e addTechVia [V VIA34]]
$e newPath $jd2301 FIXED
$e addPoint 6416984 2945610
set jd2302 [$e addTechVia [V VIA23]]
$e newPath $jd2302 FIXED
$e addPoint 6417171 2945610
set jd2303 [$e addTechVia [V VIA12]]
$e newPath $jd2303 FIXED
$e addITerm [IT L_clk_t163 A]
$e newPath $emj2121 FIXED [RL M9]
set jd2304 [$e addTechVia [V {VIA89}]]
$e newPath $jd2304 FIXED [RL M8]
$e addPoint 6845240 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6845240 2836250
set jd2305 [$e addTechVia [V VIA67]]
$e newPath $jd2305 FIXED
$e addPoint 6845320 2836250
set jd2306 [$e addTechVia [V VIA56]]
$e newPath $jd2306 FIXED
$e addPoint 6845320 2836346
set jd2307 [$e addTechVia [V VIA45]]
$e newPath $jd2307 FIXED
$e addPoint 6846475 2836346
set jd2308 [$e addTechVia [V VIA34]]
$e newPath $jd2308 FIXED
$e addPoint 6846475 2836170
set jd2309 [$e addTechVia [V VIA23]]
$e newPath $jd2309 FIXED
$e addPoint 6846525 2836170
set jd2310 [$e addTechVia [V VIA12]]
$e newPath $jd2310 FIXED
$e addITerm [IT L_clk_t164 A]
$e newPath $emj2200 FIXED [RL M9]
set jd2311 [$e addTechVia [V {VIA89}]]
$e newPath $jd2311 FIXED [RL M8]
$e addPoint 7238360 3104010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7238360 3104090
set jd2312 [$e addTechVia [V VIA67]]
$e newPath $jd2312 FIXED
$e addPoint 7238440 3104090
set jd2313 [$e addTechVia [V VIA56]]
$e newPath $jd2313 FIXED
$e addPoint 7238440 3104186
set jd2314 [$e addTechVia [V VIA45]]
$e newPath $jd2314 FIXED
$e addPoint 7238536 3104186
set jd2315 [$e addTechVia [V VIA34]]
$e newPath $jd2315 FIXED
$e addPoint 7238536 3104010
set jd2316 [$e addTechVia [V VIA23]]
$e newPath $jd2316 FIXED
$e addPoint 7238295 3104010
set jd2317 [$e addTechVia [V VIA12]]
$e newPath $jd2317 FIXED
$e addITerm [IT L_clk_t165 A]
$e newPath $emj2229 FIXED [RL M9]
set jd2318 [$e addTechVia [V {VIA89}]]
$e newPath $jd2318 FIXED [RL M8]
$e addPoint 7631080 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7631080 2836250
set jd2319 [$e addTechVia [V VIA67]]
$e newPath $jd2319 FIXED
$e addPoint 7631000 2836250
set jd2320 [$e addTechVia [V VIA56]]
$e newPath $jd2320 FIXED
$e addPoint 7631000 2836346
set jd2321 [$e addTechVia [V VIA45]]
$e newPath $jd2321 FIXED
$e addPoint 7629575 2836346
set jd2322 [$e addTechVia [V VIA34]]
$e newPath $jd2322 FIXED
$e addPoint 7629575 2836170
set jd2323 [$e addTechVia [V VIA23]]
$e newPath $jd2323 FIXED
$e addPoint 7629525 2836170
set jd2324 [$e addTechVia [V VIA12]]
$e newPath $jd2324 FIXED
$e addITerm [IT L_clk_t166 A]
$e newPath $emj2256 FIXED [RL M9]
set jd2325 [$e addTechVia [V {VIA89}]]
$e newPath $jd2325 FIXED [RL M8]
$e addPoint 8089000 2836170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 8089000 2836250
set jd2326 [$e addTechVia [V VIA67]]
$e newPath $jd2326 FIXED
$e addPoint 8088920 2836250
set jd2327 [$e addTechVia [V VIA56]]
$e newPath $jd2327 FIXED
$e addPoint 8088920 2836346
set jd2328 [$e addTechVia [V VIA45]]
$e newPath $jd2328 FIXED
$e addPoint 8087819 2836346
set jd2329 [$e addTechVia [V VIA34]]
$e newPath $jd2329 FIXED
$e addPoint 8087819 2836170
set jd2330 [$e addTechVia [V VIA23]]
$e newPath $jd2330 FIXED
$e addPoint 8087769 2836170
set jd2331 [$e addTechVia [V VIA12]]
$e newPath $jd2331 FIXED
$e addITerm [IT L_clk_t167 A]
$e newPath $emj1381 FIXED [RL M9]
set jd2332 [$e addTechVia [V {VIA89}]]
$e newPath $jd2332 FIXED [RL M8]
$e addPoint 196360 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 196360 3376250
set jd2333 [$e addTechVia [V VIA67]]
$e newPath $jd2333 FIXED
$e addPoint 196280 3376250
set jd2334 [$e addTechVia [V VIA56]]
$e newPath $jd2334 FIXED
$e addPoint 196280 3376346
set jd2335 [$e addTechVia [V VIA45]]
$e newPath $jd2335 FIXED
$e addPoint 195503 3376346
set jd2336 [$e addTechVia [V VIA34]]
$e newPath $jd2336 FIXED
$e addPoint 195503 3376170
set jd2337 [$e addTechVia [V VIA23]]
$e newPath $jd2337 FIXED
$e addPoint 195453 3376170
set jd2338 [$e addTechVia [V VIA12]]
$e newPath $jd2338 FIXED
$e addITerm [IT L_clk_t168 A]
$e newPath $emj1388 FIXED [RL M9]
set jd2339 [$e addTechVia [V {VIA89}]]
$e newPath $jd2339 FIXED [RL M8]
$e addPoint 693160 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 693160 3376250
set jd2340 [$e addTechVia [V VIA67]]
$e newPath $jd2340 FIXED
$e addPoint 693080 3376250
set jd2341 [$e addTechVia [V VIA56]]
$e newPath $jd2341 FIXED
$e addPoint 693080 3376346
set jd2342 [$e addTechVia [V VIA45]]
$e newPath $jd2342 FIXED
$e addPoint 692627 3376346
set jd2343 [$e addTechVia [V VIA34]]
$e newPath $jd2343 FIXED
$e addPoint 692627 3376170
set jd2344 [$e addTechVia [V VIA23]]
$e newPath $jd2344 FIXED
$e addPoint 692577 3376170
set jd2345 [$e addTechVia [V VIA12]]
$e newPath $jd2345 FIXED
$e addITerm [IT L_clk_t169 A]
$e newPath $emj1140 FIXED [RL M9]
set jd2346 [$e addTechVia [V {VIA89}]]
$e newPath $jd2346 FIXED [RL M8]
$e addPoint 6845240 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6845240 136250
set jd2347 [$e addTechVia [V VIA67]]
$e newPath $jd2347 FIXED
$e addPoint 6845320 136250
set jd2348 [$e addTechVia [V VIA56]]
$e newPath $jd2348 FIXED
$e addPoint 6845320 136346
set jd2349 [$e addTechVia [V VIA45]]
$e newPath $jd2349 FIXED
$e addPoint 6846475 136346
set jd2350 [$e addTechVia [V VIA34]]
$e newPath $jd2350 FIXED
$e addPoint 6846475 136170
set jd2351 [$e addTechVia [V VIA23]]
$e newPath $jd2351 FIXED
$e addPoint 6846525 136170
set jd2352 [$e addTechVia [V VIA12]]
$e newPath $jd2352 FIXED
$e addITerm [IT L_clk_t17 A]
$e newPath $emj1464 FIXED [RL M9]
set jd2353 [$e addTechVia [V {VIA89}]]
$e newPath $jd2353 FIXED [RL M8]
$e addPoint 978280 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 978280 3376250
set jd2354 [$e addTechVia [V VIA67]]
$e newPath $jd2354 FIXED
$e addPoint 978200 3376250
set jd2355 [$e addTechVia [V VIA56]]
$e newPath $jd2355 FIXED
$e addPoint 978200 3376346
set jd2356 [$e addTechVia [V VIA45]]
$e newPath $jd2356 FIXED
$e addPoint 978017 3376346
set jd2357 [$e addTechVia [V VIA34]]
$e newPath $jd2357 FIXED
$e addPoint 978017 3376170
set jd2358 [$e addTechVia [V VIA23]]
$e newPath $jd2358 FIXED
$e addPoint 977967 3376170
set jd2359 [$e addTechVia [V VIA12]]
$e newPath $jd2359 FIXED
$e addITerm [IT L_clk_t170 A]
$e newPath $emj1120 FIXED [RL M9]
set jd2360 [$e addTechVia [V {VIA89}]]
$e newPath $jd2360 FIXED [RL M8]
$e addPoint 1367480 3104010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1367480 3104090
set jd2361 [$e addTechVia [V VIA67]]
$e newPath $jd2361 FIXED
$e addPoint 1367560 3104090
set jd2362 [$e addTechVia [V VIA56]]
$e newPath $jd2362 FIXED
$e addPoint 1367560 3104186
set jd2363 [$e addTechVia [V VIA45]]
$e newPath $jd2363 FIXED
$e addPoint 1368715 3104186
set jd2364 [$e addTechVia [V VIA34]]
$e newPath $jd2364 FIXED
$e addPoint 1368715 3104010
set jd2365 [$e addTechVia [V VIA23]]
$e newPath $jd2365 FIXED
$e addPoint 1368765 3104010
set jd2366 [$e addTechVia [V VIA12]]
$e newPath $jd2366 FIXED
$e addITerm [IT L_clk_t171 A]
$e newPath $emj1527 FIXED [RL M9]
set jd2367 [$e addTechVia [V {VIA89}]]
$e newPath $jd2367 FIXED [RL M8]
$e addPoint 1682840 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1682840 3376250
set jd2368 [$e addTechVia [V VIA67]]
$e newPath $jd2368 FIXED
$e addPoint 1682920 3376250
set jd2369 [$e addTechVia [V VIA56]]
$e newPath $jd2369 FIXED
$e addPoint 1682920 3376346
set jd2370 [$e addTechVia [V VIA45]]
$e newPath $jd2370 FIXED
$e addPoint 1683016 3376346
set jd2371 [$e addTechVia [V VIA34]]
$e newPath $jd2371 FIXED
$e addPoint 1683016 3376170
set jd2372 [$e addTechVia [V VIA23]]
$e newPath $jd2372 FIXED
$e addPoint 1682775 3376170
set jd2373 [$e addTechVia [V VIA12]]
$e newPath $jd2373 FIXED
$e addITerm [IT L_clk_t172 A]
$e newPath $emj1645 FIXED [RL M9]
set jd2374 [$e addTechVia [V {VIA89}]]
$e newPath $jd2374 FIXED [RL M8]
$e addPoint 2153320 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2153320 3376250
set jd2375 [$e addTechVia [V VIA67]]
$e newPath $jd2375 FIXED
$e addPoint 2153240 3376250
set jd2376 [$e addTechVia [V VIA56]]
$e newPath $jd2376 FIXED
$e addPoint 2153240 3376346
set jd2377 [$e addTechVia [V VIA45]]
$e newPath $jd2377 FIXED
$e addPoint 2151815 3376346
set jd2378 [$e addTechVia [V VIA34]]
$e newPath $jd2378 FIXED
$e addPoint 2151815 3376170
set jd2379 [$e addTechVia [V VIA23]]
$e newPath $jd2379 FIXED
$e addPoint 2151765 3376170
set jd2380 [$e addTechVia [V VIA12]]
$e newPath $jd2380 FIXED
$e addITerm [IT L_clk_t173 A]
$e newPath $emj1749 FIXED [RL M9]
set jd2381 [$e addTechVia [V {VIA89}]]
$e newPath $jd2381 FIXED [RL M8]
$e addPoint 2542520 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2542520 3376250
set jd2382 [$e addTechVia [V VIA67]]
$e newPath $jd2382 FIXED
$e addPoint 2542600 3376250
set jd2383 [$e addTechVia [V VIA56]]
$e newPath $jd2383 FIXED
$e addPoint 2542600 3376346
set jd2384 [$e addTechVia [V VIA45]]
$e newPath $jd2384 FIXED
$e addPoint 2542999 3376346
set jd2385 [$e addTechVia [V VIA34]]
$e newPath $jd2385 FIXED
$e addPoint 2542999 3376170
set jd2386 [$e addTechVia [V VIA23]]
$e newPath $jd2386 FIXED
$e addPoint 2543049 3376170
set jd2387 [$e addTechVia [V VIA12]]
$e newPath $jd2387 FIXED
$e addITerm [IT L_clk_t174 A]
$e newPath $emj1790 FIXED [RL M9]
set jd2388 [$e addTechVia [V {VIA89}]]
$e newPath $jd2388 FIXED [RL M8]
$e addPoint 2935240 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2935240 3376250
set jd2389 [$e addTechVia [V VIA67]]
$e newPath $jd2389 FIXED
$e addPoint 2935160 3376250
set jd2390 [$e addTechVia [V VIA56]]
$e newPath $jd2390 FIXED
$e addPoint 2935160 3376346
set jd2391 [$e addTechVia [V VIA45]]
$e newPath $jd2391 FIXED
$e addPoint 2934383 3376346
set jd2392 [$e addTechVia [V VIA34]]
$e newPath $jd2392 FIXED
$e addPoint 2934383 3376170
set jd2393 [$e addTechVia [V VIA23]]
$e newPath $jd2393 FIXED
$e addPoint 2934333 3376170
set jd2394 [$e addTechVia [V VIA12]]
$e newPath $jd2394 FIXED
$e addITerm [IT L_clk_t175 A]
$e newPath $emj1845 FIXED [RL M9]
set jd2395 [$e addTechVia [V {VIA89}]]
$e newPath $jd2395 FIXED [RL M8]
$e addPoint 3324440 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3324440 3376250
set jd2396 [$e addTechVia [V VIA67]]
$e newPath $jd2396 FIXED
$e addPoint 3324520 3376250
set jd2397 [$e addTechVia [V VIA56]]
$e newPath $jd2397 FIXED
$e addPoint 3324520 3376346
set jd2398 [$e addTechVia [V VIA45]]
$e newPath $jd2398 FIXED
$e addPoint 3325567 3376346
set jd2399 [$e addTechVia [V VIA34]]
$e newPath $jd2399 FIXED
$e addPoint 3325567 3376170
set jd2400 [$e addTechVia [V VIA23]]
$e newPath $jd2400 FIXED
$e addPoint 3325617 3376170
set jd2401 [$e addTechVia [V VIA12]]
$e newPath $jd2401 FIXED
$e addITerm [IT L_clk_t176 A]
$e newPath $emj1842 FIXED [RL M9]
set jd2402 [$e addTechVia [V {VIA89}]]
$e newPath $jd2402 FIXED [RL M8]
$e addPoint 3851080 3491730
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3851080 3491810
set jd2403 [$e addTechVia [V VIA67]]
$e newPath $jd2403 FIXED
$e addPoint 3851000 3491810
set jd2404 [$e addTechVia [V VIA56]]
$e newPath $jd2404 FIXED
$e addPoint 3851000 3491906
set jd2405 [$e addTechVia [V VIA45]]
$e newPath $jd2405 FIXED
$e addPoint 3850904 3491906
set jd2406 [$e addTechVia [V VIA34]]
$e newPath $jd2406 FIXED
$e addPoint 3850904 3491730
set jd2407 [$e addTechVia [V VIA23]]
$e newPath $jd2407 FIXED
$e addPoint 3851091 3491730
set jd2408 [$e addTechVia [V VIA12]]
$e newPath $jd2408 FIXED
$e addITerm [IT L_clk_t177 A]
$e newPath $emj2010 FIXED [RL M9]
set jd2409 [$e addTechVia [V {VIA89}]]
$e newPath $jd2409 FIXED [RL M8]
$e addPoint 3981080 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3981080 3376250
set jd2410 [$e addTechVia [V VIA67]]
$e newPath $jd2410 FIXED
$e addPoint 3981160 3376250
set jd2411 [$e addTechVia [V VIA56]]
$e newPath $jd2411 FIXED
$e addPoint 3981160 3376346
set jd2412 [$e addTechVia [V VIA45]]
$e newPath $jd2412 FIXED
$e addPoint 3982315 3376346
set jd2413 [$e addTechVia [V VIA34]]
$e newPath $jd2413 FIXED
$e addPoint 3982315 3376170
set jd2414 [$e addTechVia [V VIA23]]
$e newPath $jd2414 FIXED
$e addPoint 3982365 3376170
set jd2415 [$e addTechVia [V VIA12]]
$e newPath $jd2415 FIXED
$e addITerm [IT L_clk_t178 A]
$e newPath $emj2180 FIXED [RL M9]
set jd2416 [$e addTechVia [V {VIA89}]]
$e newPath $jd2416 FIXED [RL M8]
$e addPoint 4499480 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4499480 3376250
set jd2417 [$e addTechVia [V VIA67]]
$e newPath $jd2417 FIXED
$e addPoint 4499560 3376250
set jd2418 [$e addTechVia [V VIA56]]
$e newPath $jd2418 FIXED
$e addPoint 4499560 3376346
set jd2419 [$e addTechVia [V VIA45]]
$e newPath $jd2419 FIXED
$e addPoint 4499656 3376346
set jd2420 [$e addTechVia [V VIA34]]
$e newPath $jd2420 FIXED
$e addPoint 4499656 3376170
set jd2421 [$e addTechVia [V VIA23]]
$e newPath $jd2421 FIXED
$e addPoint 4499415 3376170
set jd2422 [$e addTechVia [V VIA12]]
$e newPath $jd2422 FIXED
$e addITerm [IT L_clk_t179 A]
$e newPath $emj1198 FIXED [RL M9]
set jd2423 [$e addTechVia [V {VIA89}]]
$e newPath $jd2423 FIXED [RL M8]
$e addPoint 7238360 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7238360 136250
set jd2424 [$e addTechVia [V VIA67]]
$e newPath $jd2424 FIXED
$e addPoint 7238440 136250
set jd2425 [$e addTechVia [V VIA56]]
$e newPath $jd2425 FIXED
$e addPoint 7238440 136346
set jd2426 [$e addTechVia [V VIA45]]
$e newPath $jd2426 FIXED
$e addPoint 7238536 136346
set jd2427 [$e addTechVia [V VIA34]]
$e newPath $jd2427 FIXED
$e addPoint 7238536 136170
set jd2428 [$e addTechVia [V VIA23]]
$e newPath $jd2428 FIXED
$e addPoint 7238295 136170
set jd2429 [$e addTechVia [V VIA12]]
$e newPath $jd2429 FIXED
$e addITerm [IT L_clk_t18 A]
$e newPath $emj2052 FIXED [RL M9]
set jd2430 [$e addTechVia [V {VIA89}]]
$e newPath $jd2430 FIXED [RL M8]
$e addPoint 4879240 3338370
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879240 3338450
set jd2431 [$e addTechVia [V VIA67]]
$e newPath $jd2431 FIXED
$e addPoint 4879160 3338450
set jd2432 [$e addTechVia [V VIA56]]
$e newPath $jd2432 FIXED
$e addPoint 4879160 3338546
set jd2433 [$e addTechVia [V VIA45]]
$e newPath $jd2433 FIXED
$e addPoint 4879064 3338546
set jd2434 [$e addTechVia [V VIA34]]
$e newPath $jd2434 FIXED
$e addPoint 4879064 3338370
set jd2435 [$e addTechVia [V VIA23]]
$e newPath $jd2435 FIXED
$e addPoint 4879251 3338370
set jd2436 [$e addTechVia [V VIA12]]
$e newPath $jd2436 FIXED
$e addITerm [IT L_clk_t180 A]
$e newPath $emj2235 FIXED [RL M9]
set jd2437 [$e addTechVia [V {VIA89}]]
$e newPath $jd2437 FIXED [RL M8]
$e addPoint 5281400 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5281400 3376250
set jd2438 [$e addTechVia [V VIA67]]
$e newPath $jd2438 FIXED
$e addPoint 5281480 3376250
set jd2439 [$e addTechVia [V VIA56]]
$e newPath $jd2439 FIXED
$e addPoint 5281480 3376346
set jd2440 [$e addTechVia [V VIA45]]
$e newPath $jd2440 FIXED
$e addPoint 5281879 3376346
set jd2441 [$e addTechVia [V VIA34]]
$e newPath $jd2441 FIXED
$e addPoint 5281879 3376170
set jd2442 [$e addTechVia [V VIA23]]
$e newPath $jd2442 FIXED
$e addPoint 5281929 3376170
set jd2443 [$e addTechVia [V VIA12]]
$e newPath $jd2443 FIXED
$e addITerm [IT L_clk_t181 A]
$e newPath $emj2237 FIXED [RL M9]
set jd2444 [$e addTechVia [V {VIA89}]]
$e newPath $jd2444 FIXED [RL M8]
$e addPoint 5907400 3491730
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907400 3491810
set jd2445 [$e addTechVia [V VIA67]]
$e newPath $jd2445 FIXED
$e addPoint 5907320 3491810
set jd2446 [$e addTechVia [V VIA56]]
$e newPath $jd2446 FIXED
$e addPoint 5907320 3491906
set jd2447 [$e addTechVia [V VIA45]]
$e newPath $jd2447 FIXED
$e addPoint 5907224 3491906
set jd2448 [$e addTechVia [V VIA34]]
$e newPath $jd2448 FIXED
$e addPoint 5907224 3491730
set jd2449 [$e addTechVia [V VIA23]]
$e newPath $jd2449 FIXED
$e addPoint 5907411 3491730
set jd2450 [$e addTechVia [V VIA12]]
$e newPath $jd2450 FIXED
$e addITerm [IT L_clk_t182 A]
$e newPath $emj2129 FIXED [RL M9]
set jd2451 [$e addTechVia [V {VIA89}]]
$e newPath $jd2451 FIXED [RL M8]
$e addPoint 5907400 3338370
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907400 3338450
set jd2452 [$e addTechVia [V VIA67]]
$e newPath $jd2452 FIXED
$e addPoint 5907320 3338450
set jd2453 [$e addTechVia [V VIA56]]
$e newPath $jd2453 FIXED
$e addPoint 5907320 3338546
set jd2454 [$e addTechVia [V VIA45]]
$e newPath $jd2454 FIXED
$e addPoint 5907224 3338546
set jd2455 [$e addTechVia [V VIA34]]
$e newPath $jd2455 FIXED
$e addPoint 5907224 3338370
set jd2456 [$e addTechVia [V VIA23]]
$e newPath $jd2456 FIXED
$e addPoint 5907411 3338370
set jd2457 [$e addTechVia [V VIA12]]
$e newPath $jd2457 FIXED
$e addITerm [IT L_clk_t183 A]
$e newPath $emj2300 FIXED [RL M9]
set jd2458 [$e addTechVia [V {VIA89}]]
$e newPath $jd2458 FIXED [RL M8]
$e addPoint 6456040 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6456040 3376250
set jd2459 [$e addTechVia [V VIA67]]
$e newPath $jd2459 FIXED
$e addPoint 6455960 3376250
set jd2460 [$e addTechVia [V VIA56]]
$e newPath $jd2460 FIXED
$e addPoint 6455960 3376346
set jd2461 [$e addTechVia [V VIA45]]
$e newPath $jd2461 FIXED
$e addPoint 6455777 3376346
set jd2462 [$e addTechVia [V VIA34]]
$e newPath $jd2462 FIXED
$e addPoint 6455777 3376170
set jd2463 [$e addTechVia [V VIA23]]
$e newPath $jd2463 FIXED
$e addPoint 6455727 3376170
set jd2464 [$e addTechVia [V VIA12]]
$e newPath $jd2464 FIXED
$e addITerm [IT L_clk_t184 A]
$e newPath $emj2334 FIXED [RL M9]
set jd2465 [$e addTechVia [V {VIA89}]]
$e newPath $jd2465 FIXED [RL M8]
$e addPoint 6845240 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6845240 3376250
set jd2466 [$e addTechVia [V VIA67]]
$e newPath $jd2466 FIXED
$e addPoint 6845320 3376250
set jd2467 [$e addTechVia [V VIA56]]
$e newPath $jd2467 FIXED
$e addPoint 6845320 3376346
set jd2468 [$e addTechVia [V VIA45]]
$e newPath $jd2468 FIXED
$e addPoint 6846475 3376346
set jd2469 [$e addTechVia [V VIA34]]
$e newPath $jd2469 FIXED
$e addPoint 6846475 3376170
set jd2470 [$e addTechVia [V VIA23]]
$e newPath $jd2470 FIXED
$e addPoint 6846525 3376170
set jd2471 [$e addTechVia [V VIA12]]
$e newPath $jd2471 FIXED
$e addITerm [IT L_clk_t185 A]
$e newPath $emj2327 FIXED [RL M9]
set jd2472 [$e addTechVia [V {VIA89}]]
$e newPath $jd2472 FIXED [RL M8]
$e addPoint 7238360 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7238360 3376250
set jd2473 [$e addTechVia [V VIA67]]
$e newPath $jd2473 FIXED
$e addPoint 7238440 3376250
set jd2474 [$e addTechVia [V VIA56]]
$e newPath $jd2474 FIXED
$e addPoint 7238440 3376346
set jd2475 [$e addTechVia [V VIA45]]
$e newPath $jd2475 FIXED
$e addPoint 7238536 3376346
set jd2476 [$e addTechVia [V VIA34]]
$e newPath $jd2476 FIXED
$e addPoint 7238536 3376170
set jd2477 [$e addTechVia [V VIA23]]
$e newPath $jd2477 FIXED
$e addPoint 7238295 3376170
set jd2478 [$e addTechVia [V VIA12]]
$e newPath $jd2478 FIXED
$e addITerm [IT L_clk_t186 A]
$e newPath $emj2380 FIXED [RL M9]
set jd2479 [$e addTechVia [V {VIA89}]]
$e newPath $jd2479 FIXED [RL M8]
$e addPoint 7631080 3376170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7631080 3376250
set jd2480 [$e addTechVia [V VIA67]]
$e newPath $jd2480 FIXED
$e addPoint 7631000 3376250
set jd2481 [$e addTechVia [V VIA56]]
$e newPath $jd2481 FIXED
$e addPoint 7631000 3376346
set jd2482 [$e addTechVia [V VIA45]]
$e newPath $jd2482 FIXED
$e addPoint 7629575 3376346
set jd2483 [$e addTechVia [V VIA34]]
$e newPath $jd2483 FIXED
$e addPoint 7629575 3376170
set jd2484 [$e addTechVia [V VIA23]]
$e newPath $jd2484 FIXED
$e addPoint 7629525 3376170
set jd2485 [$e addTechVia [V VIA12]]
$e newPath $jd2485 FIXED
$e addITerm [IT L_clk_t187 A]
$e newPath $emj2323 FIXED [RL M9]
set jd2486 [$e addTechVia [V {VIA89}]]
$e newPath $jd2486 FIXED [RL M8]
$e addPoint 7959400 3491730
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7959400 3491810
set jd2487 [$e addTechVia [V VIA67]]
$e newPath $jd2487 FIXED
$e addPoint 7959320 3491810
set jd2488 [$e addTechVia [V VIA56]]
$e newPath $jd2488 FIXED
$e addPoint 7959320 3491906
set jd2489 [$e addTechVia [V VIA45]]
$e newPath $jd2489 FIXED
$e addPoint 7959224 3491906
set jd2490 [$e addTechVia [V VIA34]]
$e newPath $jd2490 FIXED
$e addPoint 7959224 3491730
set jd2491 [$e addTechVia [V VIA23]]
$e newPath $jd2491 FIXED
$e addPoint 7959411 3491730
set jd2492 [$e addTechVia [V VIA12]]
$e newPath $jd2492 FIXED
$e addITerm [IT L_clk_t188 A]
$e newPath $emj1458 FIXED [RL M9]
set jd2493 [$e addTechVia [V {VIA89}]]
$e newPath $jd2493 FIXED [RL M8]
$e addPoint 256840 3730950
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 256840 3731030
set jd2494 [$e addTechVia [V VIA67]]
$e newPath $jd2494 FIXED
$e addPoint 256760 3731030
set jd2495 [$e addTechVia [V VIA56]]
$e newPath $jd2495 FIXED
$e addPoint 256760 3731126
set jd2496 [$e addTechVia [V VIA45]]
$e newPath $jd2496 FIXED
$e addPoint 256664 3731126
set jd2497 [$e addTechVia [V VIA34]]
$e newPath $jd2497 FIXED
$e addPoint 256664 3730950
set jd2498 [$e addTechVia [V VIA23]]
$e newPath $jd2498 FIXED
$e addPoint 256851 3730950
set jd2499 [$e addTechVia [V VIA12]]
$e newPath $jd2499 FIXED
$e addITerm [IT L_clk_t189 A]
$e newPath $emj1325 FIXED [RL M9]
set jd2500 [$e addTechVia [V {VIA89}]]
$e newPath $jd2500 FIXED [RL M8]
$e addPoint 7631080 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7631080 136250
set jd2501 [$e addTechVia [V VIA67]]
$e newPath $jd2501 FIXED
$e addPoint 7631000 136250
set jd2502 [$e addTechVia [V VIA56]]
$e newPath $jd2502 FIXED
$e addPoint 7631000 136346
set jd2503 [$e addTechVia [V VIA45]]
$e newPath $jd2503 FIXED
$e addPoint 7629575 136346
set jd2504 [$e addTechVia [V VIA34]]
$e newPath $jd2504 FIXED
$e addPoint 7629575 136170
set jd2505 [$e addTechVia [V VIA23]]
$e newPath $jd2505 FIXED
$e addPoint 7629525 136170
set jd2506 [$e addTechVia [V VIA12]]
$e newPath $jd2506 FIXED
$e addITerm [IT L_clk_t19 A]
$e newPath $emj1468 FIXED [RL M9]
set jd2507 [$e addTechVia [V {VIA89}]]
$e newPath $jd2507 FIXED [RL M8]
$e addPoint 770920 3730950
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 770920 3731030
set jd2508 [$e addTechVia [V VIA67]]
$e newPath $jd2508 FIXED
$e addPoint 770840 3731030
set jd2509 [$e addTechVia [V VIA56]]
$e newPath $jd2509 FIXED
$e addPoint 770840 3731126
set jd2510 [$e addTechVia [V VIA45]]
$e newPath $jd2510 FIXED
$e addPoint 770744 3731126
set jd2511 [$e addTechVia [V VIA34]]
$e newPath $jd2511 FIXED
$e addPoint 770744 3730950
set jd2512 [$e addTechVia [V VIA23]]
$e newPath $jd2512 FIXED
$e addPoint 770931 3730950
set jd2513 [$e addTechVia [V VIA12]]
$e newPath $jd2513 FIXED
$e addITerm [IT L_clk_t190 A]
$e newPath $emj1532 FIXED [RL M9]
set jd2514 [$e addTechVia [V {VIA89}]]
$e newPath $jd2514 FIXED [RL M8]
$e addPoint 978280 3644010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 978280 3644090
set jd2515 [$e addTechVia [V VIA67]]
$e newPath $jd2515 FIXED
$e addPoint 978200 3644090
set jd2516 [$e addTechVia [V VIA56]]
$e newPath $jd2516 FIXED
$e addPoint 978200 3644186
set jd2517 [$e addTechVia [V VIA45]]
$e newPath $jd2517 FIXED
$e addPoint 978017 3644186
set jd2518 [$e addTechVia [V VIA34]]
$e newPath $jd2518 FIXED
$e addPoint 978017 3644010
set jd2519 [$e addTechVia [V VIA23]]
$e newPath $jd2519 FIXED
$e addPoint 977967 3644010
set jd2520 [$e addTechVia [V VIA12]]
$e newPath $jd2520 FIXED
$e addITerm [IT L_clk_t191 A]
$e newPath $emj1531 FIXED [RL M9]
set jd2521 [$e addTechVia [V {VIA89}]]
$e newPath $jd2521 FIXED [RL M8]
$e addPoint 1285000 3730950
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1285000 3731030
set jd2522 [$e addTechVia [V VIA67]]
$e newPath $jd2522 FIXED
$e addPoint 1284920 3731030
set jd2523 [$e addTechVia [V VIA56]]
$e newPath $jd2523 FIXED
$e addPoint 1284920 3731126
set jd2524 [$e addTechVia [V VIA45]]
$e newPath $jd2524 FIXED
$e addPoint 1284824 3731126
set jd2525 [$e addTechVia [V VIA34]]
$e newPath $jd2525 FIXED
$e addPoint 1284824 3730950
set jd2526 [$e addTechVia [V VIA23]]
$e newPath $jd2526 FIXED
$e addPoint 1285011 3730950
set jd2527 [$e addTechVia [V VIA12]]
$e newPath $jd2527 FIXED
$e addITerm [IT L_clk_t192 A]
$e newPath $emj1651 FIXED [RL M9]
set jd2528 [$e addTechVia [V {VIA89}]]
$e newPath $jd2528 FIXED [RL M8]
$e addPoint 1799080 3730950
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1799080 3731030
set jd2529 [$e addTechVia [V VIA67]]
$e newPath $jd2529 FIXED
$e addPoint 1799000 3731030
set jd2530 [$e addTechVia [V VIA56]]
$e newPath $jd2530 FIXED
$e addPoint 1799000 3731126
set jd2531 [$e addTechVia [V VIA45]]
$e newPath $jd2531 FIXED
$e addPoint 1798904 3731126
set jd2532 [$e addTechVia [V VIA34]]
$e newPath $jd2532 FIXED
$e addPoint 1798904 3730950
set jd2533 [$e addTechVia [V VIA23]]
$e newPath $jd2533 FIXED
$e addPoint 1799091 3730950
set jd2534 [$e addTechVia [V VIA12]]
$e newPath $jd2534 FIXED
$e addITerm [IT L_clk_t193 A]
$e newPath $emj1796 FIXED [RL M9]
set jd2535 [$e addTechVia [V {VIA89}]]
$e newPath $jd2535 FIXED [RL M8]
$e addPoint 2308840 3730950
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2308840 3731030
set jd2536 [$e addTechVia [V VIA67]]
$e newPath $jd2536 FIXED
$e addPoint 2308760 3731030
set jd2537 [$e addTechVia [V VIA56]]
$e newPath $jd2537 FIXED
$e addPoint 2308760 3731126
set jd2538 [$e addTechVia [V VIA45]]
$e newPath $jd2538 FIXED
$e addPoint 2308664 3731126
set jd2539 [$e addTechVia [V VIA34]]
$e newPath $jd2539 FIXED
$e addPoint 2308664 3730950
set jd2540 [$e addTechVia [V VIA23]]
$e newPath $jd2540 FIXED
$e addPoint 2308851 3730950
set jd2541 [$e addTechVia [V VIA12]]
$e newPath $jd2541 FIXED
$e addITerm [IT L_clk_t194 A]
$e newPath $emj1695 FIXED [RL M9]
set jd2542 [$e addTechVia [V {VIA89}]]
$e newPath $jd2542 FIXED [RL M8]
$e addPoint 2542520 3644010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2542520 3644090
set jd2543 [$e addTechVia [V VIA67]]
$e newPath $jd2543 FIXED
$e addPoint 2542600 3644090
set jd2544 [$e addTechVia [V VIA56]]
$e newPath $jd2544 FIXED
$e addPoint 2542600 3644186
set jd2545 [$e addTechVia [V VIA45]]
$e newPath $jd2545 FIXED
$e addPoint 2542999 3644186
set jd2546 [$e addTechVia [V VIA34]]
$e newPath $jd2546 FIXED
$e addPoint 2542999 3644010
set jd2547 [$e addTechVia [V VIA23]]
$e newPath $jd2547 FIXED
$e addPoint 2543049 3644010
set jd2548 [$e addTechVia [V VIA12]]
$e newPath $jd2548 FIXED
$e addITerm [IT L_clk_t195 A]
$e newPath $emj1848 FIXED [RL M9]
set jd2549 [$e addTechVia [V {VIA89}]]
$e newPath $jd2549 FIXED [RL M8]
$e addPoint 2935240 3644010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2935240 3644090
set jd2550 [$e addTechVia [V VIA67]]
$e newPath $jd2550 FIXED
$e addPoint 2935160 3644090
set jd2551 [$e addTechVia [V VIA56]]
$e newPath $jd2551 FIXED
$e addPoint 2935160 3644186
set jd2552 [$e addTechVia [V VIA45]]
$e newPath $jd2552 FIXED
$e addPoint 2934383 3644186
set jd2553 [$e addTechVia [V VIA34]]
$e newPath $jd2553 FIXED
$e addPoint 2934383 3644010
set jd2554 [$e addTechVia [V VIA23]]
$e newPath $jd2554 FIXED
$e addPoint 2934333 3644010
set jd2555 [$e addTechVia [V VIA12]]
$e newPath $jd2555 FIXED
$e addITerm [IT L_clk_t196 A]
$e newPath $emj1904 FIXED [RL M9]
set jd2556 [$e addTechVia [V {VIA89}]]
$e newPath $jd2556 FIXED [RL M8]
$e addPoint 3289880 3644010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3289880 3644090
set jd2557 [$e addTechVia [V VIA67]]
$e newPath $jd2557 FIXED
$e addPoint 3289960 3644090
set jd2558 [$e addTechVia [V VIA56]]
$e newPath $jd2558 FIXED
$e addPoint 3289960 3644186
set jd2559 [$e addTechVia [V VIA45]]
$e newPath $jd2559 FIXED
$e addPoint 3291007 3644186
set jd2560 [$e addTechVia [V VIA34]]
$e newPath $jd2560 FIXED
$e addPoint 3291007 3644010
set jd2561 [$e addTechVia [V VIA23]]
$e newPath $jd2561 FIXED
$e addPoint 3291057 3644010
set jd2562 [$e addTechVia [V VIA12]]
$e newPath $jd2562 FIXED
$e addITerm [IT L_clk_t197 A]
$e newPath $emj2059 FIXED [RL M9]
set jd2563 [$e addTechVia [V {VIA89}]]
$e newPath $jd2563 FIXED [RL M8]
$e addPoint 3851080 3793590
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3851080 3793670
set jd2564 [$e addTechVia [V VIA67]]
$e newPath $jd2564 FIXED
$e addPoint 3851000 3793670
set jd2565 [$e addTechVia [V VIA56]]
$e newPath $jd2565 FIXED
$e addPoint 3851000 3793766
set jd2566 [$e addTechVia [V VIA45]]
$e newPath $jd2566 FIXED
$e addPoint 3850904 3793766
set jd2567 [$e addTechVia [V VIA34]]
$e newPath $jd2567 FIXED
$e addPoint 3850904 3793590
set jd2568 [$e addTechVia [V VIA23]]
$e newPath $jd2568 FIXED
$e addPoint 3851091 3793590
set jd2569 [$e addTechVia [V VIA12]]
$e newPath $jd2569 FIXED
$e addITerm [IT L_clk_t198 A]
$e newPath $emj2143 FIXED [RL M9]
set jd2570 [$e addTechVia [V {VIA89}]]
$e newPath $jd2570 FIXED [RL M8]
$e addPoint 4106360 3644010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4106360 3644090
set jd2571 [$e addTechVia [V VIA67]]
$e newPath $jd2571 FIXED
$e addPoint 4106440 3644090
set jd2572 [$e addTechVia [V VIA56]]
$e newPath $jd2572 FIXED
$e addPoint 4106440 3644186
set jd2573 [$e addTechVia [V VIA45]]
$e newPath $jd2573 FIXED
$e addPoint 4107595 3644186
set jd2574 [$e addTechVia [V VIA34]]
$e newPath $jd2574 FIXED
$e addPoint 4107595 3644010
set jd2575 [$e addTechVia [V VIA23]]
$e newPath $jd2575 FIXED
$e addPoint 4107645 3644010
set jd2576 [$e addTechVia [V VIA12]]
$e newPath $jd2576 FIXED
$e addITerm [IT L_clk_t199 A]
$e newPath $emj40 FIXED [RL M9]
set jd2577 [$e addTechVia [V {VIA89}]]
$e newPath $jd2577 FIXED [RL M8]
$e addPoint 978280 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 978280 136250
set jd2578 [$e addTechVia [V VIA67]]
$e newPath $jd2578 FIXED
$e addPoint 978200 136250
set jd2579 [$e addTechVia [V VIA56]]
$e newPath $jd2579 FIXED
$e addPoint 978200 136346
set jd2580 [$e addTechVia [V VIA45]]
$e newPath $jd2580 FIXED
$e addPoint 978017 136346
set jd2581 [$e addTechVia [V VIA34]]
$e newPath $jd2581 FIXED
$e addPoint 978017 136170
set jd2582 [$e addTechVia [V VIA23]]
$e newPath $jd2582 FIXED
$e addPoint 977967 136170
set jd2583 [$e addTechVia [V VIA12]]
$e newPath $jd2583 FIXED
$e addITerm [IT L_clk_t2 A]
$e newPath $emj1327 FIXED [RL M9]
set jd2584 [$e addTechVia [V {VIA89}]]
$e newPath $jd2584 FIXED [RL M8]
$e addPoint 8020280 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 8020280 136250
set jd2585 [$e addTechVia [V VIA67]]
$e newPath $jd2585 FIXED
$e addPoint 8020360 136250
set jd2586 [$e addTechVia [V VIA56]]
$e newPath $jd2586 FIXED
$e addPoint 8020360 136346
set jd2587 [$e addTechVia [V VIA45]]
$e newPath $jd2587 FIXED
$e addPoint 8020759 136346
set jd2588 [$e addTechVia [V VIA34]]
$e newPath $jd2588 FIXED
$e addPoint 8020759 136170
set jd2589 [$e addTechVia [V VIA23]]
$e newPath $jd2589 FIXED
$e addPoint 8020809 136170
set jd2590 [$e addTechVia [V VIA12]]
$e newPath $jd2590 FIXED
$e addITerm [IT L_clk_t20 A]
$e newPath $emj2056 FIXED [RL M9]
set jd2591 [$e addTechVia [V {VIA89}]]
$e newPath $jd2591 FIXED [RL M8]
$e addPoint 4365160 3540870
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365160 3540950
set jd2592 [$e addTechVia [V VIA67]]
$e newPath $jd2592 FIXED
$e addPoint 4365080 3540950
set jd2593 [$e addTechVia [V VIA56]]
$e newPath $jd2593 FIXED
$e addPoint 4365080 3541046
set jd2594 [$e addTechVia [V VIA45]]
$e newPath $jd2594 FIXED
$e addPoint 4364984 3541046
set jd2595 [$e addTechVia [V VIA34]]
$e newPath $jd2595 FIXED
$e addPoint 4364984 3540870
set jd2596 [$e addTechVia [V VIA23]]
$e newPath $jd2596 FIXED
$e addPoint 4365171 3540870
set jd2597 [$e addTechVia [V VIA12]]
$e newPath $jd2597 FIXED
$e addITerm [IT L_clk_t200 A]
$e newPath $emj2304 FIXED [RL M9]
set jd2598 [$e addTechVia [V {VIA89}]]
$e newPath $jd2598 FIXED [RL M8]
$e addPoint 4879240 3730950
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879240 3731030
set jd2599 [$e addTechVia [V VIA67]]
$e newPath $jd2599 FIXED
$e addPoint 4879160 3731030
set jd2600 [$e addTechVia [V VIA56]]
$e newPath $jd2600 FIXED
$e addPoint 4879160 3731126
set jd2601 [$e addTechVia [V VIA45]]
$e newPath $jd2601 FIXED
$e addPoint 4879064 3731126
set jd2602 [$e addTechVia [V VIA34]]
$e newPath $jd2602 FIXED
$e addPoint 4879064 3730950
set jd2603 [$e addTechVia [V VIA23]]
$e newPath $jd2603 FIXED
$e addPoint 4879251 3730950
set jd2604 [$e addTechVia [V VIA12]]
$e newPath $jd2604 FIXED
$e addITerm [IT L_clk_t201 A]
$e newPath $emj2244 FIXED [RL M9]
set jd2605 [$e addTechVia [V {VIA89}]]
$e newPath $jd2605 FIXED [RL M8]
$e addPoint 5393320 3730950
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5393320 3731030
set jd2606 [$e addTechVia [V VIA67]]
$e newPath $jd2606 FIXED
$e addPoint 5393240 3731030
set jd2607 [$e addTechVia [V VIA56]]
$e newPath $jd2607 FIXED
$e addPoint 5393240 3731126
set jd2608 [$e addTechVia [V VIA45]]
$e newPath $jd2608 FIXED
$e addPoint 5393144 3731126
set jd2609 [$e addTechVia [V VIA34]]
$e newPath $jd2609 FIXED
$e addPoint 5393144 3730950
set jd2610 [$e addTechVia [V VIA23]]
$e newPath $jd2610 FIXED
$e addPoint 5393331 3730950
set jd2611 [$e addTechVia [V VIA12]]
$e newPath $jd2611 FIXED
$e addITerm [IT L_clk_t202 A]
$e newPath $emj2274 FIXED [RL M9]
set jd2612 [$e addTechVia [V {VIA89}]]
$e newPath $jd2612 FIXED [RL M8]
$e addPoint 5799400 3644010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5799400 3644090
set jd2613 [$e addTechVia [V VIA67]]
$e newPath $jd2613 FIXED
$e addPoint 5799320 3644090
set jd2614 [$e addTechVia [V VIA56]]
$e newPath $jd2614 FIXED
$e addPoint 5799320 3644186
set jd2615 [$e addTechVia [V VIA45]]
$e newPath $jd2615 FIXED
$e addPoint 5798543 3644186
set jd2616 [$e addTechVia [V VIA34]]
$e newPath $jd2616 FIXED
$e addPoint 5798543 3644010
set jd2617 [$e addTechVia [V VIA23]]
$e newPath $jd2617 FIXED
$e addPoint 5798493 3644010
set jd2618 [$e addTechVia [V VIA12]]
$e newPath $jd2618 FIXED
$e addITerm [IT L_clk_t203 A]
$e newPath $emj2389 FIXED [RL M9]
set jd2619 [$e addTechVia [V {VIA89}]]
$e newPath $jd2619 FIXED [RL M8]
$e addPoint 6127720 3644010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6127720 3644090
set jd2620 [$e addTechVia [V VIA67]]
$e newPath $jd2620 FIXED
$e addPoint 6127640 3644090
set jd2621 [$e addTechVia [V VIA56]]
$e newPath $jd2621 FIXED
$e addPoint 6127640 3644186
set jd2622 [$e addTechVia [V VIA45]]
$e newPath $jd2622 FIXED
$e addPoint 6127187 3644186
set jd2623 [$e addTechVia [V VIA34]]
$e newPath $jd2623 FIXED
$e addPoint 6127187 3644010
set jd2624 [$e addTechVia [V VIA23]]
$e newPath $jd2624 FIXED
$e addPoint 6127137 3644010
set jd2625 [$e addTechVia [V VIA12]]
$e newPath $jd2625 FIXED
$e addITerm [IT L_clk_t204 A]
$e newPath $emj2266 FIXED [RL M9]
set jd2626 [$e addTechVia [V {VIA89}]]
$e newPath $jd2626 FIXED [RL M8]
$e addPoint 6417160 3540870
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6417160 3540950
set jd2627 [$e addTechVia [V VIA67]]
$e newPath $jd2627 FIXED
$e addPoint 6417080 3540950
set jd2628 [$e addTechVia [V VIA56]]
$e newPath $jd2628 FIXED
$e addPoint 6417080 3541046
set jd2629 [$e addTechVia [V VIA45]]
$e newPath $jd2629 FIXED
$e addPoint 6416984 3541046
set jd2630 [$e addTechVia [V VIA34]]
$e newPath $jd2630 FIXED
$e addPoint 6416984 3540870
set jd2631 [$e addTechVia [V VIA23]]
$e newPath $jd2631 FIXED
$e addPoint 6417171 3540870
set jd2632 [$e addTechVia [V VIA12]]
$e newPath $jd2632 FIXED
$e addITerm [IT L_clk_t205 A]
$e newPath $emj2364 FIXED [RL M9]
set jd2633 [$e addTechVia [V {VIA89}]]
$e newPath $jd2633 FIXED [RL M8]
$e addPoint 6931240 3730950
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6931240 3731030
set jd2634 [$e addTechVia [V VIA67]]
$e newPath $jd2634 FIXED
$e addPoint 6931160 3731030
set jd2635 [$e addTechVia [V VIA56]]
$e newPath $jd2635 FIXED
$e addPoint 6931160 3731126
set jd2636 [$e addTechVia [V VIA45]]
$e newPath $jd2636 FIXED
$e addPoint 6931064 3731126
set jd2637 [$e addTechVia [V VIA34]]
$e newPath $jd2637 FIXED
$e addPoint 6931064 3730950
set jd2638 [$e addTechVia [V VIA23]]
$e newPath $jd2638 FIXED
$e addPoint 6931251 3730950
set jd2639 [$e addTechVia [V VIA12]]
$e newPath $jd2639 FIXED
$e addITerm [IT L_clk_t206 A]
$e newPath $emj2361 FIXED [RL M9]
set jd2640 [$e addTechVia [V {VIA89}]]
$e newPath $jd2640 FIXED [RL M8]
$e addPoint 7151960 3644010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7151960 3644090
set jd2641 [$e addTechVia [V VIA67]]
$e newPath $jd2641 FIXED
$e addPoint 7152040 3644090
set jd2642 [$e addTechVia [V VIA56]]
$e newPath $jd2642 FIXED
$e addPoint 7152040 3644186
set jd2643 [$e addTechVia [V VIA45]]
$e newPath $jd2643 FIXED
$e addPoint 7152136 3644186
set jd2644 [$e addTechVia [V VIA34]]
$e newPath $jd2644 FIXED
$e addPoint 7152136 3644010
set jd2645 [$e addTechVia [V VIA23]]
$e newPath $jd2645 FIXED
$e addPoint 7151895 3644010
set jd2646 [$e addTechVia [V VIA12]]
$e newPath $jd2646 FIXED
$e addITerm [IT L_clk_t207 A]
$e newPath $emj2438 FIXED [RL M9]
set jd2647 [$e addTechVia [V {VIA89}]]
$e newPath $jd2647 FIXED [RL M8]
$e addPoint 7631080 3644010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7631080 3644090
set jd2648 [$e addTechVia [V VIA67]]
$e newPath $jd2648 FIXED
$e addPoint 7631000 3644090
set jd2649 [$e addTechVia [V VIA56]]
$e newPath $jd2649 FIXED
$e addPoint 7631000 3644186
set jd2650 [$e addTechVia [V VIA45]]
$e newPath $jd2650 FIXED
$e addPoint 7629575 3644186
set jd2651 [$e addTechVia [V VIA34]]
$e newPath $jd2651 FIXED
$e addPoint 7629575 3644010
set jd2652 [$e addTechVia [V VIA23]]
$e newPath $jd2652 FIXED
$e addPoint 7629525 3644010
set jd2653 [$e addTechVia [V VIA12]]
$e newPath $jd2653 FIXED
$e addITerm [IT L_clk_t208 A]
$e newPath $emj2427 FIXED [RL M9]
set jd2654 [$e addTechVia [V {VIA89}]]
$e newPath $jd2654 FIXED [RL M8]
$e addPoint 7959400 3739590
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7959400 3739670
set jd2655 [$e addTechVia [V VIA67]]
$e newPath $jd2655 FIXED
$e addPoint 7959320 3739670
set jd2656 [$e addTechVia [V VIA56]]
$e newPath $jd2656 FIXED
$e addPoint 7959320 3739766
set jd2657 [$e addTechVia [V VIA45]]
$e newPath $jd2657 FIXED
$e addPoint 7959224 3739766
set jd2658 [$e addTechVia [V VIA34]]
$e newPath $jd2658 FIXED
$e addPoint 7959224 3739590
set jd2659 [$e addTechVia [V VIA23]]
$e newPath $jd2659 FIXED
$e addPoint 7959411 3739590
set jd2660 [$e addTechVia [V VIA12]]
$e newPath $jd2660 FIXED
$e addITerm [IT L_clk_t209 A]
$e newPath $emj92 FIXED [RL M9]
set jd2661 [$e addTechVia [V {VIA89}]]
$e newPath $jd2661 FIXED [RL M8]
$e addPoint 84440 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 84440 676250
set jd2662 [$e addTechVia [V VIA67]]
$e newPath $jd2662 FIXED
$e addPoint 84520 676250
set jd2663 [$e addTechVia [V VIA56]]
$e newPath $jd2663 FIXED
$e addPoint 84520 676346
set jd2664 [$e addTechVia [V VIA45]]
$e newPath $jd2664 FIXED
$e addPoint 85243 676346
set jd2665 [$e addTechVia [V VIA34]]
$e newPath $jd2665 FIXED
$e addPoint 85243 676170
set jd2666 [$e addTechVia [V VIA23]]
$e newPath $jd2666 FIXED
$e addPoint 85293 676170
set jd2667 [$e addTechVia [V VIA12]]
$e newPath $jd2667 FIXED
$e addITerm [IT L_clk_t21 A]
$e newPath $emj1917 FIXED [RL M9]
set jd2668 [$e addTechVia [V {VIA89}]]
$e newPath $jd2668 FIXED [RL M8]
$e addPoint 196360 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 196360 4184090
set jd2669 [$e addTechVia [V VIA67]]
$e newPath $jd2669 FIXED
$e addPoint 196280 4184090
set jd2670 [$e addTechVia [V VIA56]]
$e newPath $jd2670 FIXED
$e addPoint 196280 4184186
set jd2671 [$e addTechVia [V VIA45]]
$e newPath $jd2671 FIXED
$e addPoint 195503 4184186
set jd2672 [$e addTechVia [V VIA34]]
$e newPath $jd2672 FIXED
$e addPoint 195503 4184010
set jd2673 [$e addTechVia [V VIA23]]
$e newPath $jd2673 FIXED
$e addPoint 195453 4184010
set jd2674 [$e addTechVia [V VIA12]]
$e newPath $jd2674 FIXED
$e addITerm [IT L_clk_t210 A]
$e newPath $emj1918 FIXED [RL M9]
set jd2675 [$e addTechVia [V {VIA89}]]
$e newPath $jd2675 FIXED [RL M8]
$e addPoint 585560 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 585560 4184090
set jd2676 [$e addTechVia [V VIA67]]
$e newPath $jd2676 FIXED
$e addPoint 585640 4184090
set jd2677 [$e addTechVia [V VIA56]]
$e newPath $jd2677 FIXED
$e addPoint 585640 4184186
set jd2678 [$e addTechVia [V VIA45]]
$e newPath $jd2678 FIXED
$e addPoint 586687 4184186
set jd2679 [$e addTechVia [V VIA34]]
$e newPath $jd2679 FIXED
$e addPoint 586687 4184010
set jd2680 [$e addTechVia [V VIA23]]
$e newPath $jd2680 FIXED
$e addPoint 586737 4184010
set jd2681 [$e addTechVia [V VIA12]]
$e newPath $jd2681 FIXED
$e addITerm [IT L_clk_t211 A]
$e newPath $emj1977 FIXED [RL M9]
set jd2682 [$e addTechVia [V {VIA89}]]
$e newPath $jd2682 FIXED [RL M8]
$e addPoint 978280 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 978280 4184090
set jd2683 [$e addTechVia [V VIA67]]
$e newPath $jd2683 FIXED
$e addPoint 978200 4184090
set jd2684 [$e addTechVia [V VIA56]]
$e newPath $jd2684 FIXED
$e addPoint 978200 4184186
set jd2685 [$e addTechVia [V VIA45]]
$e newPath $jd2685 FIXED
$e addPoint 978017 4184186
set jd2686 [$e addTechVia [V VIA34]]
$e newPath $jd2686 FIXED
$e addPoint 978017 4184010
set jd2687 [$e addTechVia [V VIA23]]
$e newPath $jd2687 FIXED
$e addPoint 977967 4184010
set jd2688 [$e addTechVia [V VIA12]]
$e newPath $jd2688 FIXED
$e addITerm [IT L_clk_t212 A]
$e newPath $emj1978 FIXED [RL M9]
set jd2689 [$e addTechVia [V {VIA89}]]
$e newPath $jd2689 FIXED [RL M8]
$e addPoint 1367480 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1367480 4184090
set jd2690 [$e addTechVia [V VIA67]]
$e newPath $jd2690 FIXED
$e addPoint 1367560 4184090
set jd2691 [$e addTechVia [V VIA56]]
$e newPath $jd2691 FIXED
$e addPoint 1367560 4184186
set jd2692 [$e addTechVia [V VIA45]]
$e newPath $jd2692 FIXED
$e addPoint 1368715 4184186
set jd2693 [$e addTechVia [V VIA34]]
$e newPath $jd2693 FIXED
$e addPoint 1368715 4184010
set jd2694 [$e addTechVia [V VIA23]]
$e newPath $jd2694 FIXED
$e addPoint 1368765 4184010
set jd2695 [$e addTechVia [V VIA12]]
$e newPath $jd2695 FIXED
$e addITerm [IT L_clk_t213 A]
$e newPath $emj2069 FIXED [RL M9]
set jd2696 [$e addTechVia [V {VIA89}]]
$e newPath $jd2696 FIXED [RL M8]
$e addPoint 1760600 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1760600 4184090
set jd2697 [$e addTechVia [V VIA67]]
$e newPath $jd2697 FIXED
$e addPoint 1760680 4184090
set jd2698 [$e addTechVia [V VIA56]]
$e newPath $jd2698 FIXED
$e addPoint 1760680 4184186
set jd2699 [$e addTechVia [V VIA45]]
$e newPath $jd2699 FIXED
$e addPoint 1760776 4184186
set jd2700 [$e addTechVia [V VIA34]]
$e newPath $jd2700 FIXED
$e addPoint 1760776 4184010
set jd2701 [$e addTechVia [V VIA23]]
$e newPath $jd2701 FIXED
$e addPoint 1760535 4184010
set jd2702 [$e addTechVia [V VIA12]]
$e newPath $jd2702 FIXED
$e addITerm [IT L_clk_t214 A]
$e newPath $emj2027 FIXED [RL M9]
set jd2703 [$e addTechVia [V {VIA89}]]
$e newPath $jd2703 FIXED [RL M8]
$e addPoint 2183960 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2183960 4184090
set jd2704 [$e addTechVia [V VIA67]]
$e newPath $jd2704 FIXED
$e addPoint 2184040 4184090
set jd2705 [$e addTechVia [V VIA56]]
$e newPath $jd2705 FIXED
$e addPoint 2184040 4184186
set jd2706 [$e addTechVia [V VIA45]]
$e newPath $jd2706 FIXED
$e addPoint 2183944 4184186
set jd2707 [$e addTechVia [V VIA34]]
$e newPath $jd2707 FIXED
$e addPoint 2183944 4184010
set jd2708 [$e addTechVia [V VIA23]]
$e newPath $jd2708 FIXED
$e addPoint 2184165 4184010
set jd2709 [$e addTechVia [V VIA12]]
$e newPath $jd2709 FIXED
$e addITerm [IT L_clk_t215 A]
$e newPath $emj2105 FIXED [RL M9]
set jd2710 [$e addTechVia [V {VIA89}]]
$e newPath $jd2710 FIXED [RL M8]
$e addPoint 2542520 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2542520 4184090
set jd2711 [$e addTechVia [V VIA67]]
$e newPath $jd2711 FIXED
$e addPoint 2542600 4184090
set jd2712 [$e addTechVia [V VIA56]]
$e newPath $jd2712 FIXED
$e addPoint 2542600 4184186
set jd2713 [$e addTechVia [V VIA45]]
$e newPath $jd2713 FIXED
$e addPoint 2542999 4184186
set jd2714 [$e addTechVia [V VIA34]]
$e newPath $jd2714 FIXED
$e addPoint 2542999 4184010
set jd2715 [$e addTechVia [V VIA23]]
$e newPath $jd2715 FIXED
$e addPoint 2543049 4184010
set jd2716 [$e addTechVia [V VIA12]]
$e newPath $jd2716 FIXED
$e addITerm [IT L_clk_t216 A]
$e newPath $emj2151 FIXED [RL M9]
set jd2717 [$e addTechVia [V {VIA89}]]
$e newPath $jd2717 FIXED [RL M8]
$e addPoint 2935240 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2935240 4184090
set jd2718 [$e addTechVia [V VIA67]]
$e newPath $jd2718 FIXED
$e addPoint 2935160 4184090
set jd2719 [$e addTechVia [V VIA56]]
$e newPath $jd2719 FIXED
$e addPoint 2935160 4184186
set jd2720 [$e addTechVia [V VIA45]]
$e newPath $jd2720 FIXED
$e addPoint 2934383 4184186
set jd2721 [$e addTechVia [V VIA34]]
$e newPath $jd2721 FIXED
$e addPoint 2934383 4184010
set jd2722 [$e addTechVia [V VIA23]]
$e newPath $jd2722 FIXED
$e addPoint 2934333 4184010
set jd2723 [$e addTechVia [V VIA12]]
$e newPath $jd2723 FIXED
$e addITerm [IT L_clk_t217 A]
$e newPath $emj2104 FIXED [RL M9]
set jd2724 [$e addTechVia [V {VIA89}]]
$e newPath $jd2724 FIXED [RL M8]
$e addPoint 3337000 4124070
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337000 4124150
set jd2725 [$e addTechVia [V VIA67]]
$e newPath $jd2725 FIXED
$e addPoint 3336920 4124150
set jd2726 [$e addTechVia [V VIA56]]
$e newPath $jd2726 FIXED
$e addPoint 3336920 4124246
set jd2727 [$e addTechVia [V VIA45]]
$e newPath $jd2727 FIXED
$e addPoint 3336824 4124246
set jd2728 [$e addTechVia [V VIA34]]
$e newPath $jd2728 FIXED
$e addPoint 3336824 4124070
set jd2729 [$e addTechVia [V VIA23]]
$e newPath $jd2729 FIXED
$e addPoint 3337011 4124070
set jd2730 [$e addTechVia [V VIA12]]
$e newPath $jd2730 FIXED
$e addITerm [IT L_clk_t218 A]
$e newPath $emj2252 FIXED [RL M9]
set jd2731 [$e addTechVia [V {VIA89}]]
$e newPath $jd2731 FIXED [RL M8]
$e addPoint 3717160 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3717160 4184090
set jd2732 [$e addTechVia [V VIA67]]
$e newPath $jd2732 FIXED
$e addPoint 3717080 4184090
set jd2733 [$e addTechVia [V VIA56]]
$e newPath $jd2733 FIXED
$e addPoint 3717080 4184186
set jd2734 [$e addTechVia [V VIA45]]
$e newPath $jd2734 FIXED
$e addPoint 3716897 4184186
set jd2735 [$e addTechVia [V VIA34]]
$e newPath $jd2735 FIXED
$e addPoint 3716897 4184010
set jd2736 [$e addTechVia [V VIA23]]
$e newPath $jd2736 FIXED
$e addPoint 3716847 4184010
set jd2737 [$e addTechVia [V VIA12]]
$e newPath $jd2737 FIXED
$e addITerm [IT L_clk_t219 A]
$e newPath $emj93 FIXED [RL M9]
set jd2738 [$e addTechVia [V {VIA89}]]
$e newPath $jd2738 FIXED [RL M8]
$e addPoint 369560 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 369560 676250
set jd2739 [$e addTechVia [V VIA67]]
$e newPath $jd2739 FIXED
$e addPoint 369640 676250
set jd2740 [$e addTechVia [V VIA56]]
$e newPath $jd2740 FIXED
$e addPoint 369640 676346
set jd2741 [$e addTechVia [V VIA45]]
$e newPath $jd2741 FIXED
$e addPoint 370687 676346
set jd2742 [$e addTechVia [V VIA34]]
$e newPath $jd2742 FIXED
$e addPoint 370687 676170
set jd2743 [$e addTechVia [V VIA23]]
$e newPath $jd2743 FIXED
$e addPoint 370737 676170
set jd2744 [$e addTechVia [V VIA12]]
$e newPath $jd2744 FIXED
$e addITerm [IT L_clk_t22 A]
$e newPath $emj2253 FIXED [RL M9]
set jd2745 [$e addTechVia [V {VIA89}]]
$e newPath $jd2745 FIXED [RL M8]
$e addPoint 4106360 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4106360 4184090
set jd2746 [$e addTechVia [V VIA67]]
$e newPath $jd2746 FIXED
$e addPoint 4106440 4184090
set jd2747 [$e addTechVia [V VIA56]]
$e newPath $jd2747 FIXED
$e addPoint 4106440 4184186
set jd2748 [$e addTechVia [V VIA45]]
$e newPath $jd2748 FIXED
$e addPoint 4107595 4184186
set jd2749 [$e addTechVia [V VIA34]]
$e newPath $jd2749 FIXED
$e addPoint 4107595 4184010
set jd2750 [$e addTechVia [V VIA23]]
$e newPath $jd2750 FIXED
$e addPoint 4107645 4184010
set jd2751 [$e addTechVia [V VIA12]]
$e newPath $jd2751 FIXED
$e addITerm [IT L_clk_t220 A]
$e newPath $emj2319 FIXED [RL M9]
set jd2752 [$e addTechVia [V {VIA89}]]
$e newPath $jd2752 FIXED [RL M8]
$e addPoint 4365160 4298850
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4365160 4298930
set jd2753 [$e addTechVia [V VIA67]]
$e newPath $jd2753 FIXED
$e addPoint 4365080 4298930
set jd2754 [$e addTechVia [V VIA56]]
$e newPath $jd2754 FIXED
$e addPoint 4365080 4299026
set jd2755 [$e addTechVia [V VIA45]]
$e newPath $jd2755 FIXED
$e addPoint 4364984 4299026
set jd2756 [$e addTechVia [V VIA34]]
$e newPath $jd2756 FIXED
$e addPoint 4364984 4298850
set jd2757 [$e addTechVia [V VIA23]]
$e newPath $jd2757 FIXED
$e addPoint 4365171 4298850
set jd2758 [$e addTechVia [V VIA12]]
$e newPath $jd2758 FIXED
$e addITerm [IT L_clk_t221 A]
$e newPath $emj2284 FIXED [RL M9]
set jd2759 [$e addTechVia [V {VIA89}]]
$e newPath $jd2759 FIXED [RL M8]
$e addPoint 4879240 4124070
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879240 4124150
set jd2760 [$e addTechVia [V VIA67]]
$e newPath $jd2760 FIXED
$e addPoint 4879160 4124150
set jd2761 [$e addTechVia [V VIA56]]
$e newPath $jd2761 FIXED
$e addPoint 4879160 4124246
set jd2762 [$e addTechVia [V VIA45]]
$e newPath $jd2762 FIXED
$e addPoint 4879064 4124246
set jd2763 [$e addTechVia [V VIA34]]
$e newPath $jd2763 FIXED
$e addPoint 4879064 4124070
set jd2764 [$e addTechVia [V VIA23]]
$e newPath $jd2764 FIXED
$e addPoint 4879251 4124070
set jd2765 [$e addTechVia [V VIA12]]
$e newPath $jd2765 FIXED
$e addITerm [IT L_clk_t222 A]
$e newPath $emj2403 FIXED [RL M9]
set jd2766 [$e addTechVia [V {VIA89}]]
$e newPath $jd2766 FIXED [RL M8]
$e addPoint 5281400 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5281400 4184090
set jd2767 [$e addTechVia [V VIA67]]
$e newPath $jd2767 FIXED
$e addPoint 5281480 4184090
set jd2768 [$e addTechVia [V VIA56]]
$e newPath $jd2768 FIXED
$e addPoint 5281480 4184186
set jd2769 [$e addTechVia [V VIA45]]
$e newPath $jd2769 FIXED
$e addPoint 5281879 4184186
set jd2770 [$e addTechVia [V VIA34]]
$e newPath $jd2770 FIXED
$e addPoint 5281879 4184010
set jd2771 [$e addTechVia [V VIA23]]
$e newPath $jd2771 FIXED
$e addPoint 5281929 4184010
set jd2772 [$e addTechVia [V VIA12]]
$e newPath $jd2772 FIXED
$e addITerm [IT L_clk_t223 A]
$e newPath $emj2420 FIXED [RL M9]
set jd2773 [$e addTechVia [V {VIA89}]]
$e newPath $jd2773 FIXED [RL M8]
$e addPoint 5674120 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5674120 4184090
set jd2774 [$e addTechVia [V VIA67]]
$e newPath $jd2774 FIXED
$e addPoint 5674040 4184090
set jd2775 [$e addTechVia [V VIA56]]
$e newPath $jd2775 FIXED
$e addPoint 5674040 4184186
set jd2776 [$e addTechVia [V VIA45]]
$e newPath $jd2776 FIXED
$e addPoint 5673263 4184186
set jd2777 [$e addTechVia [V VIA34]]
$e newPath $jd2777 FIXED
$e addPoint 5673263 4184010
set jd2778 [$e addTechVia [V VIA23]]
$e newPath $jd2778 FIXED
$e addPoint 5673213 4184010
set jd2779 [$e addTechVia [V VIA12]]
$e newPath $jd2779 FIXED
$e addITerm [IT L_clk_t224 A]
$e newPath $emj2421 FIXED [RL M9]
set jd2780 [$e addTechVia [V {VIA89}]]
$e newPath $jd2780 FIXED [RL M8]
$e addPoint 6063320 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6063320 4184090
set jd2781 [$e addTechVia [V VIA67]]
$e newPath $jd2781 FIXED
$e addPoint 6063400 4184090
set jd2782 [$e addTechVia [V VIA56]]
$e newPath $jd2782 FIXED
$e addPoint 6063400 4184186
set jd2783 [$e addTechVia [V VIA45]]
$e newPath $jd2783 FIXED
$e addPoint 6064447 4184186
set jd2784 [$e addTechVia [V VIA34]]
$e newPath $jd2784 FIXED
$e addPoint 6064447 4184010
set jd2785 [$e addTechVia [V VIA23]]
$e newPath $jd2785 FIXED
$e addPoint 6064497 4184010
set jd2786 [$e addTechVia [V VIA12]]
$e newPath $jd2786 FIXED
$e addITerm [IT L_clk_t225 A]
$e newPath $emj2436 FIXED [RL M9]
set jd2787 [$e addTechVia [V {VIA89}]]
$e newPath $jd2787 FIXED [RL M8]
$e addPoint 6417160 4208130
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6417160 4208210
set jd2788 [$e addTechVia [V VIA67]]
$e newPath $jd2788 FIXED
$e addPoint 6417080 4208210
set jd2789 [$e addTechVia [V VIA56]]
$e newPath $jd2789 FIXED
$e addPoint 6417080 4208306
set jd2790 [$e addTechVia [V VIA45]]
$e newPath $jd2790 FIXED
$e addPoint 6416984 4208306
set jd2791 [$e addTechVia [V VIA34]]
$e newPath $jd2791 FIXED
$e addPoint 6416984 4208130
set jd2792 [$e addTechVia [V VIA23]]
$e newPath $jd2792 FIXED
$e addPoint 6417171 4208130
set jd2793 [$e addTechVia [V VIA12]]
$e newPath $jd2793 FIXED
$e addITerm [IT L_clk_t226 A]
$e newPath $emj2417 FIXED [RL M9]
set jd2794 [$e addTechVia [V {VIA89}]]
$e newPath $jd2794 FIXED [RL M8]
$e addPoint 6931240 4124070
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6931240 4124150
set jd2795 [$e addTechVia [V VIA67]]
$e newPath $jd2795 FIXED
$e addPoint 6931160 4124150
set jd2796 [$e addTechVia [V VIA56]]
$e newPath $jd2796 FIXED
$e addPoint 6931160 4124246
set jd2797 [$e addTechVia [V VIA45]]
$e newPath $jd2797 FIXED
$e addPoint 6931064 4124246
set jd2798 [$e addTechVia [V VIA34]]
$e newPath $jd2798 FIXED
$e addPoint 6931064 4124070
set jd2799 [$e addTechVia [V VIA23]]
$e newPath $jd2799 FIXED
$e addPoint 6931251 4124070
set jd2800 [$e addTechVia [V VIA12]]
$e newPath $jd2800 FIXED
$e addITerm [IT L_clk_t227 A]
$e newPath $emj2468 FIXED [RL M9]
set jd2801 [$e addTechVia [V {VIA89}]]
$e newPath $jd2801 FIXED [RL M8]
$e addPoint 7238360 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7238360 4184090
set jd2802 [$e addTechVia [V VIA67]]
$e newPath $jd2802 FIXED
$e addPoint 7238440 4184090
set jd2803 [$e addTechVia [V VIA56]]
$e newPath $jd2803 FIXED
$e addPoint 7238440 4184186
set jd2804 [$e addTechVia [V VIA45]]
$e newPath $jd2804 FIXED
$e addPoint 7238536 4184186
set jd2805 [$e addTechVia [V VIA34]]
$e newPath $jd2805 FIXED
$e addPoint 7238536 4184010
set jd2806 [$e addTechVia [V VIA23]]
$e newPath $jd2806 FIXED
$e addPoint 7238295 4184010
set jd2807 [$e addTechVia [V VIA12]]
$e newPath $jd2807 FIXED
$e addITerm [IT L_clk_t228 A]
$e newPath $emj2473 FIXED [RL M9]
set jd2808 [$e addTechVia [V {VIA89}]]
$e newPath $jd2808 FIXED [RL M8]
$e addPoint 7631080 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7631080 4184090
set jd2809 [$e addTechVia [V VIA67]]
$e newPath $jd2809 FIXED
$e addPoint 7631000 4184090
set jd2810 [$e addTechVia [V VIA56]]
$e newPath $jd2810 FIXED
$e addPoint 7631000 4184186
set jd2811 [$e addTechVia [V VIA45]]
$e newPath $jd2811 FIXED
$e addPoint 7629575 4184186
set jd2812 [$e addTechVia [V VIA34]]
$e newPath $jd2812 FIXED
$e addPoint 7629575 4184010
set jd2813 [$e addTechVia [V VIA23]]
$e newPath $jd2813 FIXED
$e addPoint 7629525 4184010
set jd2814 [$e addTechVia [V VIA12]]
$e newPath $jd2814 FIXED
$e addITerm [IT L_clk_t229 A]
$e newPath $emj157 FIXED [RL M9]
set jd2815 [$e addTechVia [V {VIA89}]]
$e newPath $jd2815 FIXED [RL M8]
$e addPoint 978280 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 978280 676250
set jd2816 [$e addTechVia [V VIA67]]
$e newPath $jd2816 FIXED
$e addPoint 978200 676250
set jd2817 [$e addTechVia [V VIA56]]
$e newPath $jd2817 FIXED
$e addPoint 978200 676346
set jd2818 [$e addTechVia [V VIA45]]
$e newPath $jd2818 FIXED
$e addPoint 978017 676346
set jd2819 [$e addTechVia [V VIA34]]
$e newPath $jd2819 FIXED
$e addPoint 978017 676170
set jd2820 [$e addTechVia [V VIA23]]
$e newPath $jd2820 FIXED
$e addPoint 977967 676170
set jd2821 [$e addTechVia [V VIA12]]
$e newPath $jd2821 FIXED
$e addITerm [IT L_clk_t23 A]
$e newPath $emj2475 FIXED [RL M9]
set jd2822 [$e addTechVia [V {VIA89}]]
$e newPath $jd2822 FIXED [RL M8]
$e addPoint 8020280 4184010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 8020280 4184090
set jd2823 [$e addTechVia [V VIA67]]
$e newPath $jd2823 FIXED
$e addPoint 8020360 4184090
set jd2824 [$e addTechVia [V VIA56]]
$e newPath $jd2824 FIXED
$e addPoint 8020360 4184186
set jd2825 [$e addTechVia [V VIA45]]
$e newPath $jd2825 FIXED
$e addPoint 8020759 4184186
set jd2826 [$e addTechVia [V VIA34]]
$e newPath $jd2826 FIXED
$e addPoint 8020759 4184010
set jd2827 [$e addTechVia [V VIA23]]
$e newPath $jd2827 FIXED
$e addPoint 8020809 4184010
set jd2828 [$e addTechVia [V VIA12]]
$e newPath $jd2828 FIXED
$e addITerm [IT L_clk_t230 A]
$e newPath $emj90 FIXED [RL M9]
set jd2829 [$e addTechVia [V {VIA89}]]
$e newPath $jd2829 FIXED [RL M8]
$e addPoint 1389080 404010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1389080 404090
set jd2830 [$e addTechVia [V VIA67]]
$e newPath $jd2830 FIXED
$e addPoint 1389160 404090
set jd2831 [$e addTechVia [V VIA56]]
$e newPath $jd2831 FIXED
$e addPoint 1389160 404186
set jd2832 [$e addTechVia [V VIA45]]
$e newPath $jd2832 FIXED
$e addPoint 1390315 404186
set jd2833 [$e addTechVia [V VIA34]]
$e newPath $jd2833 FIXED
$e addPoint 1390315 404010
set jd2834 [$e addTechVia [V VIA23]]
$e newPath $jd2834 FIXED
$e addPoint 1390365 404010
set jd2835 [$e addTechVia [V VIA12]]
$e newPath $jd2835 FIXED
$e addITerm [IT L_clk_t24 A]
$e newPath $emj220 FIXED [RL M9]
set jd2836 [$e addTechVia [V {VIA89}]]
$e newPath $jd2836 FIXED [RL M8]
$e addPoint 1799080 779310
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1799080 779390
set jd2837 [$e addTechVia [V VIA67]]
$e newPath $jd2837 FIXED
$e addPoint 1799000 779390
set jd2838 [$e addTechVia [V VIA56]]
$e newPath $jd2838 FIXED
$e addPoint 1799000 779486
set jd2839 [$e addTechVia [V VIA45]]
$e newPath $jd2839 FIXED
$e addPoint 1798904 779486
set jd2840 [$e addTechVia [V VIA34]]
$e newPath $jd2840 FIXED
$e addPoint 1798904 779310
set jd2841 [$e addTechVia [V VIA23]]
$e newPath $jd2841 FIXED
$e addPoint 1799091 779310
set jd2842 [$e addTechVia [V VIA12]]
$e newPath $jd2842 FIXED
$e addITerm [IT L_clk_t25 A]
$e newPath $emj260 FIXED [RL M9]
set jd2843 [$e addTechVia [V {VIA89}]]
$e newPath $jd2843 FIXED [RL M8]
$e addPoint 2308840 779310
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2308840 779390
set jd2844 [$e addTechVia [V VIA67]]
$e newPath $jd2844 FIXED
$e addPoint 2308760 779390
set jd2845 [$e addTechVia [V VIA56]]
$e newPath $jd2845 FIXED
$e addPoint 2308760 779486
set jd2846 [$e addTechVia [V VIA45]]
$e newPath $jd2846 FIXED
$e addPoint 2308664 779486
set jd2847 [$e addTechVia [V VIA34]]
$e newPath $jd2847 FIXED
$e addPoint 2308664 779310
set jd2848 [$e addTechVia [V VIA23]]
$e newPath $jd2848 FIXED
$e addPoint 2308851 779310
set jd2849 [$e addTechVia [V VIA12]]
$e newPath $jd2849 FIXED
$e addITerm [IT L_clk_t26 A]
$e newPath $emj310 FIXED [RL M9]
set jd2850 [$e addTechVia [V {VIA89}]]
$e newPath $jd2850 FIXED [RL M8]
$e addPoint 2542520 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2542520 676250
set jd2851 [$e addTechVia [V VIA67]]
$e newPath $jd2851 FIXED
$e addPoint 2542600 676250
set jd2852 [$e addTechVia [V VIA56]]
$e newPath $jd2852 FIXED
$e addPoint 2542600 676346
set jd2853 [$e addTechVia [V VIA45]]
$e newPath $jd2853 FIXED
$e addPoint 2542999 676346
set jd2854 [$e addTechVia [V VIA34]]
$e newPath $jd2854 FIXED
$e addPoint 2542999 676170
set jd2855 [$e addTechVia [V VIA23]]
$e newPath $jd2855 FIXED
$e addPoint 2543049 676170
set jd2856 [$e addTechVia [V VIA12]]
$e newPath $jd2856 FIXED
$e addITerm [IT L_clk_t27 A]
$e newPath $emj258 FIXED [RL M9]
set jd2857 [$e addTechVia [V {VIA89}]]
$e newPath $jd2857 FIXED [RL M8]
$e addPoint 2822920 589230
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2822920 589310
set jd2858 [$e addTechVia [V VIA67]]
$e newPath $jd2858 FIXED
$e addPoint 2822840 589310
set jd2859 [$e addTechVia [V VIA56]]
$e newPath $jd2859 FIXED
$e addPoint 2822840 589406
set jd2860 [$e addTechVia [V VIA45]]
$e newPath $jd2860 FIXED
$e addPoint 2822744 589406
set jd2861 [$e addTechVia [V VIA34]]
$e newPath $jd2861 FIXED
$e addPoint 2822744 589230
set jd2862 [$e addTechVia [V VIA23]]
$e newPath $jd2862 FIXED
$e addPoint 2822931 589230
set jd2863 [$e addTechVia [V VIA12]]
$e newPath $jd2863 FIXED
$e addITerm [IT L_clk_t28 A]
$e newPath $emj330 FIXED [RL M9]
set jd2864 [$e addTechVia [V {VIA89}]]
$e newPath $jd2864 FIXED [RL M8]
$e addPoint 3337000 565290
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337000 565370
set jd2865 [$e addTechVia [V VIA67]]
$e newPath $jd2865 FIXED
$e addPoint 3336920 565370
set jd2866 [$e addTechVia [V VIA56]]
$e newPath $jd2866 FIXED
$e addPoint 3336920 565466
set jd2867 [$e addTechVia [V VIA45]]
$e newPath $jd2867 FIXED
$e addPoint 3336824 565466
set jd2868 [$e addTechVia [V VIA34]]
$e newPath $jd2868 FIXED
$e addPoint 3336824 565290
set jd2869 [$e addTechVia [V VIA23]]
$e newPath $jd2869 FIXED
$e addPoint 3337011 565290
set jd2870 [$e addTechVia [V VIA12]]
$e newPath $jd2870 FIXED
$e addITerm [IT L_clk_t29 A]
$e newPath $emj67 FIXED [RL M9]
set jd2871 [$e addTechVia [V {VIA89}]]
$e newPath $jd2871 FIXED [RL M8]
$e addPoint 1389080 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1389080 136250
set jd2872 [$e addTechVia [V VIA67]]
$e newPath $jd2872 FIXED
$e addPoint 1389160 136250
set jd2873 [$e addTechVia [V VIA56]]
$e newPath $jd2873 FIXED
$e addPoint 1389160 136346
set jd2874 [$e addTechVia [V VIA45]]
$e newPath $jd2874 FIXED
$e addPoint 1390315 136346
set jd2875 [$e addTechVia [V VIA34]]
$e newPath $jd2875 FIXED
$e addPoint 1390315 136170
set jd2876 [$e addTechVia [V VIA23]]
$e newPath $jd2876 FIXED
$e addPoint 1390365 136170
set jd2877 [$e addTechVia [V VIA12]]
$e newPath $jd2877 FIXED
$e addITerm [IT L_clk_t3 A]
$e newPath $emj472 FIXED [RL M9]
set jd2878 [$e addTechVia [V {VIA89}]]
$e newPath $jd2878 FIXED [RL M8]
$e addPoint 3829880 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3829880 676250
set jd2879 [$e addTechVia [V VIA67]]
$e newPath $jd2879 FIXED
$e addPoint 3829960 676250
set jd2880 [$e addTechVia [V VIA56]]
$e newPath $jd2880 FIXED
$e addPoint 3829960 676346
set jd2881 [$e addTechVia [V VIA45]]
$e newPath $jd2881 FIXED
$e addPoint 3831763 676346
set jd2882 [$e addTechVia [V VIA34]]
$e newPath $jd2882 FIXED
$e addPoint 3831763 676170
set jd2883 [$e addTechVia [V VIA23]]
$e newPath $jd2883 FIXED
$e addPoint 3831813 676170
set jd2884 [$e addTechVia [V VIA12]]
$e newPath $jd2884 FIXED
$e addITerm [IT L_clk_t30 A]
$e newPath $emj684 FIXED [RL M9]
set jd2885 [$e addTechVia [V {VIA89}]]
$e newPath $jd2885 FIXED [RL M8]
$e addPoint 4106360 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4106360 676250
set jd2886 [$e addTechVia [V VIA67]]
$e newPath $jd2886 FIXED
$e addPoint 4106440 676250
set jd2887 [$e addTechVia [V VIA56]]
$e newPath $jd2887 FIXED
$e addPoint 4106440 676346
set jd2888 [$e addTechVia [V VIA45]]
$e newPath $jd2888 FIXED
$e addPoint 4107595 676346
set jd2889 [$e addTechVia [V VIA34]]
$e newPath $jd2889 FIXED
$e addPoint 4107595 676170
set jd2890 [$e addTechVia [V VIA23]]
$e newPath $jd2890 FIXED
$e addPoint 4107645 676170
set jd2891 [$e addTechVia [V VIA12]]
$e newPath $jd2891 FIXED
$e addITerm [IT L_clk_t31 A]
$e newPath $emj852 FIXED [RL M9]
set jd2892 [$e addTechVia [V {VIA89}]]
$e newPath $jd2892 FIXED [RL M8]
$e addPoint 4499480 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4499480 676250
set jd2893 [$e addTechVia [V VIA67]]
$e newPath $jd2893 FIXED
$e addPoint 4499560 676250
set jd2894 [$e addTechVia [V VIA56]]
$e newPath $jd2894 FIXED
$e addPoint 4499560 676346
set jd2895 [$e addTechVia [V VIA45]]
$e newPath $jd2895 FIXED
$e addPoint 4499656 676346
set jd2896 [$e addTechVia [V VIA34]]
$e newPath $jd2896 FIXED
$e addPoint 4499656 676170
set jd2897 [$e addTechVia [V VIA23]]
$e newPath $jd2897 FIXED
$e addPoint 4499415 676170
set jd2898 [$e addTechVia [V VIA12]]
$e newPath $jd2898 FIXED
$e addITerm [IT L_clk_t32 A]
$e newPath $emj593 FIXED [RL M9]
set jd2899 [$e addTechVia [V {VIA89}]]
$e newPath $jd2899 FIXED [RL M8]
$e addPoint 4879240 589230
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879240 589310
set jd2900 [$e addTechVia [V VIA67]]
$e newPath $jd2900 FIXED
$e addPoint 4879160 589310
set jd2901 [$e addTechVia [V VIA56]]
$e newPath $jd2901 FIXED
$e addPoint 4879160 589406
set jd2902 [$e addTechVia [V VIA45]]
$e newPath $jd2902 FIXED
$e addPoint 4879064 589406
set jd2903 [$e addTechVia [V VIA34]]
$e newPath $jd2903 FIXED
$e addPoint 4879064 589230
set jd2904 [$e addTechVia [V VIA23]]
$e newPath $jd2904 FIXED
$e addPoint 4879251 589230
set jd2905 [$e addTechVia [V VIA12]]
$e newPath $jd2905 FIXED
$e addITerm [IT L_clk_t33 A]
$e newPath $emj917 FIXED [RL M9]
set jd2906 [$e addTechVia [V {VIA89}]]
$e newPath $jd2906 FIXED [RL M8]
$e addPoint 5281400 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5281400 676250
set jd2907 [$e addTechVia [V VIA67]]
$e newPath $jd2907 FIXED
$e addPoint 5281480 676250
set jd2908 [$e addTechVia [V VIA56]]
$e newPath $jd2908 FIXED
$e addPoint 5281480 676346
set jd2909 [$e addTechVia [V VIA45]]
$e newPath $jd2909 FIXED
$e addPoint 5281879 676346
set jd2910 [$e addTechVia [V VIA34]]
$e newPath $jd2910 FIXED
$e addPoint 5281879 676170
set jd2911 [$e addTechVia [V VIA23]]
$e newPath $jd2911 FIXED
$e addPoint 5281929 676170
set jd2912 [$e addTechVia [V VIA12]]
$e newPath $jd2912 FIXED
$e addITerm [IT L_clk_t34 A]
$e newPath $emj918 FIXED [RL M9]
set jd2913 [$e addTechVia [V {VIA89}]]
$e newPath $jd2913 FIXED [RL M8]
$e addPoint 5601080 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5601080 676250
set jd2914 [$e addTechVia [V VIA67]]
$e newPath $jd2914 FIXED
$e addPoint 5601160 676250
set jd2915 [$e addTechVia [V VIA56]]
$e newPath $jd2915 FIXED
$e addPoint 5601160 676346
set jd2916 [$e addTechVia [V VIA45]]
$e newPath $jd2916 FIXED
$e addPoint 5601064 676346
set jd2917 [$e addTechVia [V VIA34]]
$e newPath $jd2917 FIXED
$e addPoint 5601064 676170
set jd2918 [$e addTechVia [V VIA23]]
$e newPath $jd2918 FIXED
$e addPoint 5601177 676170
set jd2919 [$e addTechVia [V VIA12]]
$e newPath $jd2919 FIXED
$e addITerm [IT L_clk_t35 A]
$e newPath $emj993 FIXED [RL M9]
set jd2920 [$e addTechVia [V {VIA89}]]
$e newPath $jd2920 FIXED [RL M8]
$e addPoint 5907400 682110
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907400 682190
set jd2921 [$e addTechVia [V VIA67]]
$e newPath $jd2921 FIXED
$e addPoint 5907320 682190
set jd2922 [$e addTechVia [V VIA56]]
$e newPath $jd2922 FIXED
$e addPoint 5907320 682286
set jd2923 [$e addTechVia [V VIA45]]
$e newPath $jd2923 FIXED
$e addPoint 5907224 682286
set jd2924 [$e addTechVia [V VIA34]]
$e newPath $jd2924 FIXED
$e addPoint 5907224 682110
set jd2925 [$e addTechVia [V VIA23]]
$e newPath $jd2925 FIXED
$e addPoint 5907411 682110
set jd2926 [$e addTechVia [V VIA12]]
$e newPath $jd2926 FIXED
$e addITerm [IT L_clk_t36 A]
$e newPath $emj1142 FIXED [RL M9]
set jd2927 [$e addTechVia [V {VIA89}]]
$e newPath $jd2927 FIXED [RL M8]
$e addPoint 6469400 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6469400 676250
set jd2928 [$e addTechVia [V VIA67]]
$e newPath $jd2928 FIXED
$e addPoint 6469480 676250
set jd2929 [$e addTechVia [V VIA56]]
$e newPath $jd2929 FIXED
$e addPoint 6469480 676346
set jd2930 [$e addTechVia [V VIA45]]
$e newPath $jd2930 FIXED
$e addPoint 6470635 676346
set jd2931 [$e addTechVia [V VIA34]]
$e newPath $jd2931 FIXED
$e addPoint 6470635 676170
set jd2932 [$e addTechVia [V VIA23]]
$e newPath $jd2932 FIXED
$e addPoint 6470685 676170
set jd2933 [$e addTechVia [V VIA12]]
$e newPath $jd2933 FIXED
$e addITerm [IT L_clk_t37 A]
$e newPath $emj1274 FIXED [RL M9]
set jd2934 [$e addTechVia [V {VIA89}]]
$e newPath $jd2934 FIXED [RL M8]
$e addPoint 6845240 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6845240 676250
set jd2935 [$e addTechVia [V VIA67]]
$e newPath $jd2935 FIXED
$e addPoint 6845320 676250
set jd2936 [$e addTechVia [V VIA56]]
$e newPath $jd2936 FIXED
$e addPoint 6845320 676346
set jd2937 [$e addTechVia [V VIA45]]
$e newPath $jd2937 FIXED
$e addPoint 6846475 676346
set jd2938 [$e addTechVia [V VIA34]]
$e newPath $jd2938 FIXED
$e addPoint 6846475 676170
set jd2939 [$e addTechVia [V VIA23]]
$e newPath $jd2939 FIXED
$e addPoint 6846525 676170
set jd2940 [$e addTechVia [V VIA12]]
$e newPath $jd2940 FIXED
$e addITerm [IT L_clk_t38 A]
$e newPath $emj1400 FIXED [RL M9]
set jd2941 [$e addTechVia [V {VIA89}]]
$e newPath $jd2941 FIXED [RL M8]
$e addPoint 7333000 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7333000 676250
set jd2942 [$e addTechVia [V VIA67]]
$e newPath $jd2942 FIXED
$e addPoint 7332920 676250
set jd2943 [$e addTechVia [V VIA56]]
$e newPath $jd2943 FIXED
$e addPoint 7332920 676346
set jd2944 [$e addTechVia [V VIA45]]
$e newPath $jd2944 FIXED
$e addPoint 7332359 676346
set jd2945 [$e addTechVia [V VIA34]]
$e newPath $jd2945 FIXED
$e addPoint 7332359 676170
set jd2946 [$e addTechVia [V VIA23]]
$e newPath $jd2946 FIXED
$e addPoint 7332309 676170
set jd2947 [$e addTechVia [V VIA12]]
$e newPath $jd2947 FIXED
$e addITerm [IT L_clk_t39 A]
$e newPath $emj101 FIXED [RL M9]
set jd2948 [$e addTechVia [V {VIA89}]]
$e newPath $jd2948 FIXED [RL M8]
$e addPoint 1466840 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1466840 136250
set jd2949 [$e addTechVia [V VIA67]]
$e newPath $jd2949 FIXED
$e addPoint 1466920 136250
set jd2950 [$e addTechVia [V VIA56]]
$e newPath $jd2950 FIXED
$e addPoint 1466920 136346
set jd2951 [$e addTechVia [V VIA45]]
$e newPath $jd2951 FIXED
$e addPoint 1467016 136346
set jd2952 [$e addTechVia [V VIA34]]
$e newPath $jd2952 FIXED
$e addPoint 1467016 136170
set jd2953 [$e addTechVia [V VIA23]]
$e newPath $jd2953 FIXED
$e addPoint 1466775 136170
set jd2954 [$e addTechVia [V VIA12]]
$e newPath $jd2954 FIXED
$e addITerm [IT L_clk_t4 A]
$e newPath $emj1602 FIXED [RL M9]
set jd2955 [$e addTechVia [V {VIA89}]]
$e newPath $jd2955 FIXED [RL M8]
$e addPoint 7665640 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7665640 676250
set jd2956 [$e addTechVia [V VIA67]]
$e newPath $jd2956 FIXED
$e addPoint 7665560 676250
set jd2957 [$e addTechVia [V VIA56]]
$e newPath $jd2957 FIXED
$e addPoint 7665560 676346
set jd2958 [$e addTechVia [V VIA45]]
$e newPath $jd2958 FIXED
$e addPoint 7664135 676346
set jd2959 [$e addTechVia [V VIA34]]
$e newPath $jd2959 FIXED
$e addPoint 7664135 676170
set jd2960 [$e addTechVia [V VIA23]]
$e newPath $jd2960 FIXED
$e addPoint 7664085 676170
set jd2961 [$e addTechVia [V VIA12]]
$e newPath $jd2961 FIXED
$e addITerm [IT L_clk_t40 A]
$e newPath $emj1267 FIXED [RL M9]
set jd2962 [$e addTechVia [V {VIA89}]]
$e newPath $jd2962 FIXED [RL M8]
$e addPoint 7959400 589230
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7959400 589310
set jd2963 [$e addTechVia [V VIA67]]
$e newPath $jd2963 FIXED
$e addPoint 7959320 589310
set jd2964 [$e addTechVia [V VIA56]]
$e newPath $jd2964 FIXED
$e addPoint 7959320 589406
set jd2965 [$e addTechVia [V VIA45]]
$e newPath $jd2965 FIXED
$e addPoint 7959224 589406
set jd2966 [$e addTechVia [V VIA34]]
$e newPath $jd2966 FIXED
$e addPoint 7959224 589230
set jd2967 [$e addTechVia [V VIA23]]
$e newPath $jd2967 FIXED
$e addPoint 7959411 589230
set jd2968 [$e addTechVia [V VIA12]]
$e newPath $jd2968 FIXED
$e addITerm [IT L_clk_t41 A]
$e newPath $emj108 FIXED [RL M9]
set jd2969 [$e addTechVia [V {VIA89}]]
$e newPath $jd2969 FIXED [RL M8]
$e addPoint 84440 944010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 84440 944090
set jd2970 [$e addTechVia [V VIA67]]
$e newPath $jd2970 FIXED
$e addPoint 84520 944090
set jd2971 [$e addTechVia [V VIA56]]
$e newPath $jd2971 FIXED
$e addPoint 84520 944186
set jd2972 [$e addTechVia [V VIA45]]
$e newPath $jd2972 FIXED
$e addPoint 85243 944186
set jd2973 [$e addTechVia [V VIA34]]
$e newPath $jd2973 FIXED
$e addPoint 85243 944010
set jd2974 [$e addTechVia [V VIA23]]
$e newPath $jd2974 FIXED
$e addPoint 85293 944010
set jd2975 [$e addTechVia [V VIA12]]
$e newPath $jd2975 FIXED
$e addITerm [IT L_clk_t42 A]
$e newPath $emj105 FIXED [RL M9]
set jd2976 [$e addTechVia [V {VIA89}]]
$e newPath $jd2976 FIXED [RL M8]
$e addPoint 770920 1098450
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 770920 1098530
set jd2977 [$e addTechVia [V VIA67]]
$e newPath $jd2977 FIXED
$e addPoint 770840 1098530
set jd2978 [$e addTechVia [V VIA56]]
$e newPath $jd2978 FIXED
$e addPoint 770840 1098626
set jd2979 [$e addTechVia [V VIA45]]
$e newPath $jd2979 FIXED
$e addPoint 770744 1098626
set jd2980 [$e addTechVia [V VIA34]]
$e newPath $jd2980 FIXED
$e addPoint 770744 1098450
set jd2981 [$e addTechVia [V VIA23]]
$e newPath $jd2981 FIXED
$e addPoint 770931 1098450
set jd2982 [$e addTechVia [V VIA12]]
$e newPath $jd2982 FIXED
$e addITerm [IT L_clk_t43 A]
$e newPath $emj144 FIXED [RL M9]
set jd2983 [$e addTechVia [V {VIA89}]]
$e newPath $jd2983 FIXED [RL M8]
$e addPoint 978280 944010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 978280 944090
set jd2984 [$e addTechVia [V VIA67]]
$e newPath $jd2984 FIXED
$e addPoint 978200 944090
set jd2985 [$e addTechVia [V VIA56]]
$e newPath $jd2985 FIXED
$e addPoint 978200 944186
set jd2986 [$e addTechVia [V VIA45]]
$e newPath $jd2986 FIXED
$e addPoint 978017 944186
set jd2987 [$e addTechVia [V VIA34]]
$e newPath $jd2987 FIXED
$e addPoint 978017 944010
set jd2988 [$e addTechVia [V VIA23]]
$e newPath $jd2988 FIXED
$e addPoint 977967 944010
set jd2989 [$e addTechVia [V VIA12]]
$e newPath $jd2989 FIXED
$e addITerm [IT L_clk_t44 A]
$e newPath $emj156 FIXED [RL M9]
set jd2990 [$e addTechVia [V {VIA89}]]
$e newPath $jd2990 FIXED [RL M8]
$e addPoint 1285000 1072530
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1285000 1072610
set jd2991 [$e addTechVia [V VIA67]]
$e newPath $jd2991 FIXED
$e addPoint 1284920 1072610
set jd2992 [$e addTechVia [V VIA56]]
$e newPath $jd2992 FIXED
$e addPoint 1284920 1072706
set jd2993 [$e addTechVia [V VIA45]]
$e newPath $jd2993 FIXED
$e addPoint 1284824 1072706
set jd2994 [$e addTechVia [V VIA34]]
$e newPath $jd2994 FIXED
$e addPoint 1284824 1072530
set jd2995 [$e addTechVia [V VIA23]]
$e newPath $jd2995 FIXED
$e addPoint 1285011 1072530
set jd2996 [$e addTechVia [V VIA12]]
$e newPath $jd2996 FIXED
$e addITerm [IT L_clk_t45 A]
$e newPath $emj200 FIXED [RL M9]
set jd2997 [$e addTechVia [V {VIA89}]]
$e newPath $jd2997 FIXED [RL M8]
$e addPoint 1626680 944010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1626680 944090
set jd2998 [$e addTechVia [V VIA67]]
$e newPath $jd2998 FIXED
$e addPoint 1626760 944090
set jd2999 [$e addTechVia [V VIA56]]
$e newPath $jd2999 FIXED
$e addPoint 1626760 944186
set jd3000 [$e addTechVia [V VIA45]]
$e newPath $jd3000 FIXED
$e addPoint 1626664 944186
set jd3001 [$e addTechVia [V VIA34]]
$e newPath $jd3001 FIXED
$e addPoint 1626664 944010
set jd3002 [$e addTechVia [V VIA23]]
$e newPath $jd3002 FIXED
$e addPoint 1626777 944010
set jd3003 [$e addTechVia [V VIA12]]
$e newPath $jd3003 FIXED
$e addITerm [IT L_clk_t46 A]
$e newPath $emj313 FIXED [RL M9]
set jd3004 [$e addTechVia [V {VIA89}]]
$e newPath $jd3004 FIXED [RL M8]
$e addPoint 2308840 828450
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2308840 828530
set jd3005 [$e addTechVia [V VIA67]]
$e newPath $jd3005 FIXED
$e addPoint 2308760 828530
set jd3006 [$e addTechVia [V VIA56]]
$e newPath $jd3006 FIXED
$e addPoint 2308760 828626
set jd3007 [$e addTechVia [V VIA45]]
$e newPath $jd3007 FIXED
$e addPoint 2308664 828626
set jd3008 [$e addTechVia [V VIA34]]
$e newPath $jd3008 FIXED
$e addPoint 2308664 828450
set jd3009 [$e addTechVia [V VIA23]]
$e newPath $jd3009 FIXED
$e addPoint 2308851 828450
set jd3010 [$e addTechVia [V VIA12]]
$e newPath $jd3010 FIXED
$e addITerm [IT L_clk_t47 A]
$e newPath $emj310 FIXED [RL M9]
set jd3011 [$e addTechVia [V {VIA89}]]
$e newPath $jd3011 FIXED [RL M8]
$e addPoint 2542520 676170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2542520 676250
set jd3012 [$e addTechVia [V VIA67]]
$e newPath $jd3012 FIXED
$e addPoint 2542600 676250
set jd3013 [$e addTechVia [V VIA56]]
$e newPath $jd3013 FIXED
$e addPoint 2542600 676346
set jd3014 [$e addTechVia [V VIA45]]
$e newPath $jd3014 FIXED
$e addPoint 2543431 676346
set jd3015 [$e addTechVia [V VIA34]]
$e newPath $jd3015 FIXED
$e addPoint 2543431 676170
set jd3016 [$e addTechVia [V VIA23]]
$e newPath $jd3016 FIXED
$e addPoint 2543481 676170
set jd3017 [$e addTechVia [V VIA12]]
$e newPath $jd3017 FIXED
$e addITerm [IT L_clk_t48 A]
$e newPath $emj428 FIXED [RL M9]
set jd3018 [$e addTechVia [V {VIA89}]]
$e newPath $jd3018 FIXED [RL M8]
$e addPoint 2822920 923490
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2822920 923570
set jd3019 [$e addTechVia [V VIA67]]
$e newPath $jd3019 FIXED
$e addPoint 2822840 923570
set jd3020 [$e addTechVia [V VIA56]]
$e newPath $jd3020 FIXED
$e addPoint 2822840 923666
set jd3021 [$e addTechVia [V VIA45]]
$e newPath $jd3021 FIXED
$e addPoint 2822744 923666
set jd3022 [$e addTechVia [V VIA34]]
$e newPath $jd3022 FIXED
$e addPoint 2822744 923490
set jd3023 [$e addTechVia [V VIA23]]
$e newPath $jd3023 FIXED
$e addPoint 2822931 923490
set jd3024 [$e addTechVia [V VIA12]]
$e newPath $jd3024 FIXED
$e addITerm [IT L_clk_t49 A]
$e newPath $emj194 FIXED [RL M9]
set jd3025 [$e addTechVia [V {VIA89}]]
$e newPath $jd3025 FIXED [RL M8]
$e addPoint 2425880 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2425880 136250
set jd3026 [$e addTechVia [V VIA67]]
$e newPath $jd3026 FIXED
$e addPoint 2425960 136250
set jd3027 [$e addTechVia [V VIA56]]
$e newPath $jd3027 FIXED
$e addPoint 2425960 136346
set jd3028 [$e addTechVia [V VIA45]]
$e newPath $jd3028 FIXED
$e addPoint 2425864 136346
set jd3029 [$e addTechVia [V VIA34]]
$e newPath $jd3029 FIXED
$e addPoint 2425864 136170
set jd3030 [$e addTechVia [V VIA23]]
$e newPath $jd3030 FIXED
$e addPoint 2426085 136170
set jd3031 [$e addTechVia [V VIA12]]
$e newPath $jd3031 FIXED
$e addITerm [IT L_clk_t5 A]
$e newPath $emj430 FIXED [RL M9]
set jd3032 [$e addTechVia [V {VIA89}]]
$e newPath $jd3032 FIXED [RL M8]
$e addPoint 3281240 944010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3281240 944090
set jd3033 [$e addTechVia [V VIA67]]
$e newPath $jd3033 FIXED
$e addPoint 3281320 944090
set jd3034 [$e addTechVia [V VIA56]]
$e newPath $jd3034 FIXED
$e addPoint 3281320 944186
set jd3035 [$e addTechVia [V VIA45]]
$e newPath $jd3035 FIXED
$e addPoint 3282367 944186
set jd3036 [$e addTechVia [V VIA34]]
$e newPath $jd3036 FIXED
$e addPoint 3282367 944010
set jd3037 [$e addTechVia [V VIA23]]
$e newPath $jd3037 FIXED
$e addPoint 3282417 944010
set jd3038 [$e addTechVia [V VIA12]]
$e newPath $jd3038 FIXED
$e addITerm [IT L_clk_t50 A]
$e newPath $emj549 FIXED [RL M9]
set jd3039 [$e addTechVia [V {VIA89}]]
$e newPath $jd3039 FIXED [RL M8]
$e addPoint 3851080 828450
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3851080 828530
set jd3040 [$e addTechVia [V VIA67]]
$e newPath $jd3040 FIXED
$e addPoint 3851000 828530
set jd3041 [$e addTechVia [V VIA56]]
$e newPath $jd3041 FIXED
$e addPoint 3851000 828626
set jd3042 [$e addTechVia [V VIA45]]
$e newPath $jd3042 FIXED
$e addPoint 3850904 828626
set jd3043 [$e addTechVia [V VIA34]]
$e newPath $jd3043 FIXED
$e addPoint 3850904 828450
set jd3044 [$e addTechVia [V VIA23]]
$e newPath $jd3044 FIXED
$e addPoint 3851091 828450
set jd3045 [$e addTechVia [V VIA12]]
$e newPath $jd3045 FIXED
$e addITerm [IT L_clk_t51 A]
$e newPath $emj750 FIXED [RL M9]
set jd3046 [$e addTechVia [V {VIA89}]]
$e newPath $jd3046 FIXED [RL M8]
$e addPoint 4106360 944010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4106360 944090
set jd3047 [$e addTechVia [V VIA67]]
$e newPath $jd3047 FIXED
$e addPoint 4106440 944090
set jd3048 [$e addTechVia [V VIA56]]
$e newPath $jd3048 FIXED
$e addPoint 4106440 944186
set jd3049 [$e addTechVia [V VIA45]]
$e newPath $jd3049 FIXED
$e addPoint 4107595 944186
set jd3050 [$e addTechVia [V VIA34]]
$e newPath $jd3050 FIXED
$e addPoint 4107595 944010
set jd3051 [$e addTechVia [V VIA23]]
$e newPath $jd3051 FIXED
$e addPoint 4107645 944010
set jd3052 [$e addTechVia [V VIA12]]
$e newPath $jd3052 FIXED
$e addITerm [IT L_clk_t52 A]
$e newPath $emj924 FIXED [RL M9]
set jd3053 [$e addTechVia [V {VIA89}]]
$e newPath $jd3053 FIXED [RL M8]
$e addPoint 4413080 944010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4413080 944090
set jd3054 [$e addTechVia [V VIA67]]
$e newPath $jd3054 FIXED
$e addPoint 4413160 944090
set jd3055 [$e addTechVia [V VIA56]]
$e newPath $jd3055 FIXED
$e addPoint 4413160 944186
set jd3056 [$e addTechVia [V VIA45]]
$e newPath $jd3056 FIXED
$e addPoint 4413256 944186
set jd3057 [$e addTechVia [V VIA34]]
$e newPath $jd3057 FIXED
$e addPoint 4413256 944010
set jd3058 [$e addTechVia [V VIA23]]
$e newPath $jd3058 FIXED
$e addPoint 4413015 944010
set jd3059 [$e addTechVia [V VIA12]]
$e newPath $jd3059 FIXED
$e addITerm [IT L_clk_t53 A]
$e newPath $emj864 FIXED [RL M9]
set jd3060 [$e addTechVia [V {VIA89}]]
$e newPath $jd3060 FIXED [RL M8]
$e addPoint 4879240 981810
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879240 981890
set jd3061 [$e addTechVia [V VIA67]]
$e newPath $jd3061 FIXED
$e addPoint 4879160 981890
set jd3062 [$e addTechVia [V VIA56]]
$e newPath $jd3062 FIXED
$e addPoint 4879160 981986
set jd3063 [$e addTechVia [V VIA45]]
$e newPath $jd3063 FIXED
$e addPoint 4879064 981986
set jd3064 [$e addTechVia [V VIA34]]
$e newPath $jd3064 FIXED
$e addPoint 4879064 981810
set jd3065 [$e addTechVia [V VIA23]]
$e newPath $jd3065 FIXED
$e addPoint 4879251 981810
set jd3066 [$e addTechVia [V VIA12]]
$e newPath $jd3066 FIXED
$e addITerm [IT L_clk_t54 A]
$e newPath $emj994 FIXED [RL M9]
set jd3067 [$e addTechVia [V {VIA89}]]
$e newPath $jd3067 FIXED [RL M8]
$e addPoint 5281400 944010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5281400 944090
set jd3068 [$e addTechVia [V VIA67]]
$e newPath $jd3068 FIXED
$e addPoint 5281480 944090
set jd3069 [$e addTechVia [V VIA56]]
$e newPath $jd3069 FIXED
$e addPoint 5281480 944186
set jd3070 [$e addTechVia [V VIA45]]
$e newPath $jd3070 FIXED
$e addPoint 5281879 944186
set jd3071 [$e addTechVia [V VIA34]]
$e newPath $jd3071 FIXED
$e addPoint 5281879 944010
set jd3072 [$e addTechVia [V VIA23]]
$e newPath $jd3072 FIXED
$e addPoint 5281929 944010
set jd3073 [$e addTechVia [V VIA12]]
$e newPath $jd3073 FIXED
$e addITerm [IT L_clk_t55 A]
$e newPath $emj997 FIXED [RL M9]
set jd3074 [$e addTechVia [V {VIA89}]]
$e newPath $jd3074 FIXED [RL M8]
$e addPoint 5795080 944010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5795080 944090
set jd3075 [$e addTechVia [V VIA67]]
$e newPath $jd3075 FIXED
$e addPoint 5795000 944090
set jd3076 [$e addTechVia [V VIA56]]
$e newPath $jd3076 FIXED
$e addPoint 5795000 944186
set jd3077 [$e addTechVia [V VIA45]]
$e newPath $jd3077 FIXED
$e addPoint 5793251 944186
set jd3078 [$e addTechVia [V VIA34]]
$e newPath $jd3078 FIXED
$e addPoint 5793251 944010
set jd3079 [$e addTechVia [V VIA23]]
$e newPath $jd3079 FIXED
$e addPoint 5793201 944010
set jd3080 [$e addTechVia [V VIA12]]
$e newPath $jd3080 FIXED
$e addITerm [IT L_clk_t56 A]
$e newPath $emj1083 FIXED [RL M9]
set jd3081 [$e addTechVia [V {VIA89}]]
$e newPath $jd3081 FIXED [RL M8]
$e addPoint 5907400 981810
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907400 981890
set jd3082 [$e addTechVia [V VIA67]]
$e newPath $jd3082 FIXED
$e addPoint 5907320 981890
set jd3083 [$e addTechVia [V VIA56]]
$e newPath $jd3083 FIXED
$e addPoint 5907320 981986
set jd3084 [$e addTechVia [V VIA45]]
$e newPath $jd3084 FIXED
$e addPoint 5907224 981986
set jd3085 [$e addTechVia [V VIA34]]
$e newPath $jd3085 FIXED
$e addPoint 5907224 981810
set jd3086 [$e addTechVia [V VIA23]]
$e newPath $jd3086 FIXED
$e addPoint 5907411 981810
set jd3087 [$e addTechVia [V VIA12]]
$e newPath $jd3087 FIXED
$e addITerm [IT L_clk_t57 A]
$e newPath $emj1078 FIXED [RL M9]
set jd3088 [$e addTechVia [V {VIA89}]]
$e newPath $jd3088 FIXED [RL M8]
$e addPoint 6577400 1216170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6577400 1216250
set jd3089 [$e addTechVia [V VIA67]]
$e newPath $jd3089 FIXED
$e addPoint 6577480 1216250
set jd3090 [$e addTechVia [V VIA56]]
$e newPath $jd3090 FIXED
$e addPoint 6577480 1216346
set jd3091 [$e addTechVia [V VIA45]]
$e newPath $jd3091 FIXED
$e addPoint 6578635 1216346
set jd3092 [$e addTechVia [V VIA34]]
$e newPath $jd3092 FIXED
$e addPoint 6578635 1216170
set jd3093 [$e addTechVia [V VIA23]]
$e newPath $jd3093 FIXED
$e addPoint 6578685 1216170
set jd3094 [$e addTechVia [V VIA12]]
$e newPath $jd3094 FIXED
$e addITerm [IT L_clk_t58 A]
$e newPath $emj1335 FIXED [RL M9]
set jd3095 [$e addTechVia [V {VIA89}]]
$e newPath $jd3095 FIXED [RL M8]
$e addPoint 6931240 1135170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6931240 1135250
set jd3096 [$e addTechVia [V VIA67]]
$e newPath $jd3096 FIXED
$e addPoint 6931160 1135250
set jd3097 [$e addTechVia [V VIA56]]
$e newPath $jd3097 FIXED
$e addPoint 6931160 1135346
set jd3098 [$e addTechVia [V VIA45]]
$e newPath $jd3098 FIXED
$e addPoint 6931064 1135346
set jd3099 [$e addTechVia [V VIA34]]
$e newPath $jd3099 FIXED
$e addPoint 6931064 1135170
set jd3100 [$e addTechVia [V VIA23]]
$e newPath $jd3100 FIXED
$e addPoint 6931251 1135170
set jd3101 [$e addTechVia [V VIA12]]
$e newPath $jd3101 FIXED
$e addITerm [IT L_clk_t59 A]
$e newPath $emj240 FIXED [RL M9]
set jd3102 [$e addTechVia [V {VIA89}]]
$e newPath $jd3102 FIXED [RL M8]
$e addPoint 2503640 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2503640 136250
set jd3103 [$e addTechVia [V VIA67]]
$e newPath $jd3103 FIXED
$e addPoint 2503720 136250
set jd3104 [$e addTechVia [V VIA56]]
$e newPath $jd3104 FIXED
$e addPoint 2503720 136346
set jd3105 [$e addTechVia [V VIA45]]
$e newPath $jd3105 FIXED
$e addPoint 2504119 136346
set jd3106 [$e addTechVia [V VIA34]]
$e newPath $jd3106 FIXED
$e addPoint 2504119 136170
set jd3107 [$e addTechVia [V VIA23]]
$e newPath $jd3107 FIXED
$e addPoint 2504169 136170
set jd3108 [$e addTechVia [V VIA12]]
$e newPath $jd3108 FIXED
$e addITerm [IT L_clk_t6 A]
$e newPath $emj1473 FIXED [RL M9]
set jd3109 [$e addTechVia [V {VIA89}]]
$e newPath $jd3109 FIXED [RL M8]
$e addPoint 7445320 1046610
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445320 1046690
set jd3110 [$e addTechVia [V VIA67]]
$e newPath $jd3110 FIXED
$e addPoint 7445240 1046690
set jd3111 [$e addTechVia [V VIA56]]
$e newPath $jd3111 FIXED
$e addPoint 7445240 1046786
set jd3112 [$e addTechVia [V VIA45]]
$e newPath $jd3112 FIXED
$e addPoint 7445144 1046786
set jd3113 [$e addTechVia [V VIA34]]
$e newPath $jd3113 FIXED
$e addPoint 7445144 1046610
set jd3114 [$e addTechVia [V VIA23]]
$e newPath $jd3114 FIXED
$e addPoint 7445331 1046610
set jd3115 [$e addTechVia [V VIA12]]
$e newPath $jd3115 FIXED
$e addITerm [IT L_clk_t60 A]
$e newPath $emj1476 FIXED [RL M9]
set jd3116 [$e addTechVia [V {VIA89}]]
$e newPath $jd3116 FIXED [RL M8]
$e addPoint 7532120 944010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7532120 944090
set jd3117 [$e addTechVia [V VIA67]]
$e newPath $jd3117 FIXED
$e addPoint 7532200 944090
set jd3118 [$e addTechVia [V VIA56]]
$e newPath $jd3118 FIXED
$e addPoint 7532200 944186
set jd3119 [$e addTechVia [V VIA45]]
$e newPath $jd3119 FIXED
$e addPoint 7532104 944186
set jd3120 [$e addTechVia [V VIA34]]
$e newPath $jd3120 FIXED
$e addPoint 7532104 944010
set jd3121 [$e addTechVia [V VIA23]]
$e newPath $jd3121 FIXED
$e addPoint 7532325 944010
set jd3122 [$e addTechVia [V VIA12]]
$e newPath $jd3122 FIXED
$e addITerm [IT L_clk_t61 A]
$e newPath $emj1601 FIXED [RL M9]
set jd3123 [$e addTechVia [V {VIA89}]]
$e newPath $jd3123 FIXED [RL M8]
$e addPoint 7959400 828450
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7959400 828530
set jd3124 [$e addTechVia [V VIA67]]
$e newPath $jd3124 FIXED
$e addPoint 7959320 828530
set jd3125 [$e addTechVia [V VIA56]]
$e newPath $jd3125 FIXED
$e addPoint 7959320 828626
set jd3126 [$e addTechVia [V VIA45]]
$e newPath $jd3126 FIXED
$e addPoint 7959224 828626
set jd3127 [$e addTechVia [V VIA34]]
$e newPath $jd3127 FIXED
$e addPoint 7959224 828450
set jd3128 [$e addTechVia [V VIA23]]
$e newPath $jd3128 FIXED
$e addPoint 7959411 828450
set jd3129 [$e addTechVia [V VIA12]]
$e newPath $jd3129 FIXED
$e addITerm [IT L_clk_t62 A]
$e newPath $emj112 FIXED [RL M9]
set jd3130 [$e addTechVia [V {VIA89}]]
$e newPath $jd3130 FIXED [RL M8]
$e addPoint 256840 1374750
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 256840 1374830
set jd3131 [$e addTechVia [V VIA67]]
$e newPath $jd3131 FIXED
$e addPoint 256760 1374830
set jd3132 [$e addTechVia [V VIA56]]
$e newPath $jd3132 FIXED
$e addPoint 256760 1374926
set jd3133 [$e addTechVia [V VIA45]]
$e newPath $jd3133 FIXED
$e addPoint 256664 1374926
set jd3134 [$e addTechVia [V VIA34]]
$e newPath $jd3134 FIXED
$e addPoint 256664 1374750
set jd3135 [$e addTechVia [V VIA23]]
$e newPath $jd3135 FIXED
$e addPoint 256851 1374750
set jd3136 [$e addTechVia [V VIA12]]
$e newPath $jd3136 FIXED
$e addITerm [IT L_clk_t63 A]
$e newPath $emj214 FIXED [RL M9]
set jd3137 [$e addTechVia [V {VIA89}]]
$e newPath $jd3137 FIXED [RL M8]
$e addPoint 386840 1484010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 386840 1484090
set jd3138 [$e addTechVia [V VIA67]]
$e newPath $jd3138 FIXED
$e addPoint 386920 1484090
set jd3139 [$e addTechVia [V VIA56]]
$e newPath $jd3139 FIXED
$e addPoint 386920 1484186
set jd3140 [$e addTechVia [V VIA45]]
$e newPath $jd3140 FIXED
$e addPoint 387967 1484186
set jd3141 [$e addTechVia [V VIA34]]
$e newPath $jd3141 FIXED
$e addPoint 387967 1484010
set jd3142 [$e addTechVia [V VIA23]]
$e newPath $jd3142 FIXED
$e addPoint 388017 1484010
set jd3143 [$e addTechVia [V VIA12]]
$e newPath $jd3143 FIXED
$e addITerm [IT L_clk_t64 A]
$e newPath $emj267 FIXED [RL M9]
set jd3144 [$e addTechVia [V {VIA89}]]
$e newPath $jd3144 FIXED [RL M8]
$e addPoint 1285000 1374750
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1285000 1374830
set jd3145 [$e addTechVia [V VIA67]]
$e newPath $jd3145 FIXED
$e addPoint 1284920 1374830
set jd3146 [$e addTechVia [V VIA56]]
$e newPath $jd3146 FIXED
$e addPoint 1284920 1374926
set jd3147 [$e addTechVia [V VIA45]]
$e newPath $jd3147 FIXED
$e addPoint 1284824 1374926
set jd3148 [$e addTechVia [V VIA34]]
$e newPath $jd3148 FIXED
$e addPoint 1284824 1374750
set jd3149 [$e addTechVia [V VIA23]]
$e newPath $jd3149 FIXED
$e addPoint 1285011 1374750
set jd3150 [$e addTechVia [V VIA12]]
$e newPath $jd3150 FIXED
$e addITerm [IT L_clk_t65 A]
$e newPath $emj267 FIXED [RL M9]
set jd3151 [$e addTechVia [V {VIA89}]]
$e newPath $jd3151 FIXED [RL M8]
$e addPoint 1285400 1374750
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1285400 1374830
set jd3152 [$e addTechVia [V VIA67]]
$e newPath $jd3152 FIXED
$e addPoint 1285480 1374830
set jd3153 [$e addTechVia [V VIA56]]
$e newPath $jd3153 FIXED
$e addPoint 1285480 1374926
set jd3154 [$e addTechVia [V VIA45]]
$e newPath $jd3154 FIXED
$e addPoint 1285576 1374926
set jd3155 [$e addTechVia [V VIA34]]
$e newPath $jd3155 FIXED
$e addPoint 1285576 1374750
set jd3156 [$e addTechVia [V VIA23]]
$e newPath $jd3156 FIXED
$e addPoint 1285443 1374750
set jd3157 [$e addTechVia [V VIA12]]
$e newPath $jd3157 FIXED
$e addITerm [IT L_clk_t66 A]
$e newPath $emj304 FIXED [RL M9]
set jd3158 [$e addTechVia [V {VIA89}]]
$e newPath $jd3158 FIXED [RL M8]
$e addPoint 1799080 1360710
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1799080 1360790
set jd3159 [$e addTechVia [V VIA67]]
$e newPath $jd3159 FIXED
$e addPoint 1799000 1360790
set jd3160 [$e addTechVia [V VIA56]]
$e newPath $jd3160 FIXED
$e addPoint 1799000 1360886
set jd3161 [$e addTechVia [V VIA45]]
$e newPath $jd3161 FIXED
$e addPoint 1798904 1360886
set jd3162 [$e addTechVia [V VIA34]]
$e newPath $jd3162 FIXED
$e addPoint 1798904 1360710
set jd3163 [$e addTechVia [V VIA23]]
$e newPath $jd3163 FIXED
$e addPoint 1799091 1360710
set jd3164 [$e addTechVia [V VIA12]]
$e newPath $jd3164 FIXED
$e addITerm [IT L_clk_t67 A]
$e newPath $emj475 FIXED [RL M9]
set jd3165 [$e addTechVia [V {VIA89}]]
$e newPath $jd3165 FIXED [RL M8]
$e addPoint 2153320 1484010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2153320 1484090
set jd3166 [$e addTechVia [V VIA67]]
$e newPath $jd3166 FIXED
$e addPoint 2153240 1484090
set jd3167 [$e addTechVia [V VIA56]]
$e newPath $jd3167 FIXED
$e addPoint 2153240 1484186
set jd3168 [$e addTechVia [V VIA45]]
$e newPath $jd3168 FIXED
$e addPoint 2151815 1484186
set jd3169 [$e addTechVia [V VIA34]]
$e newPath $jd3169 FIXED
$e addPoint 2151815 1484010
set jd3170 [$e addTechVia [V VIA23]]
$e newPath $jd3170 FIXED
$e addPoint 2151765 1484010
set jd3171 [$e addTechVia [V VIA12]]
$e newPath $jd3171 FIXED
$e addITerm [IT L_clk_t68 A]
$e newPath $emj341 FIXED [RL M9]
set jd3172 [$e addTechVia [V {VIA89}]]
$e newPath $jd3172 FIXED [RL M8]
$e addPoint 2308840 1326690
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2308840 1326770
set jd3173 [$e addTechVia [V VIA67]]
$e newPath $jd3173 FIXED
$e addPoint 2308760 1326770
set jd3174 [$e addTechVia [V VIA56]]
$e newPath $jd3174 FIXED
$e addPoint 2308760 1326866
set jd3175 [$e addTechVia [V VIA45]]
$e newPath $jd3175 FIXED
$e addPoint 2308664 1326866
set jd3176 [$e addTechVia [V VIA34]]
$e newPath $jd3176 FIXED
$e addPoint 2308664 1326690
set jd3177 [$e addTechVia [V VIA23]]
$e newPath $jd3177 FIXED
$e addPoint 2308851 1326690
set jd3178 [$e addTechVia [V VIA12]]
$e newPath $jd3178 FIXED
$e addITerm [IT L_clk_t69 A]
$e newPath $emj407 FIXED [RL M9]
set jd3179 [$e addTechVia [V {VIA89}]]
$e newPath $jd3179 FIXED [RL M8]
$e addPoint 2935240 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2935240 136250
set jd3180 [$e addTechVia [V VIA67]]
$e newPath $jd3180 FIXED
$e addPoint 2935160 136250
set jd3181 [$e addTechVia [V VIA56]]
$e newPath $jd3181 FIXED
$e addPoint 2935160 136346
set jd3182 [$e addTechVia [V VIA45]]
$e newPath $jd3182 FIXED
$e addPoint 2934383 136346
set jd3183 [$e addTechVia [V VIA34]]
$e newPath $jd3183 FIXED
$e addPoint 2934383 136170
set jd3184 [$e addTechVia [V VIA23]]
$e newPath $jd3184 FIXED
$e addPoint 2934333 136170
set jd3185 [$e addTechVia [V VIA12]]
$e newPath $jd3185 FIXED
$e addITerm [IT L_clk_t7 A]
$e newPath $emj416 FIXED [RL M9]
set jd3186 [$e addTechVia [V {VIA89}]]
$e newPath $jd3186 FIXED [RL M8]
$e addPoint 2822920 1320750
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2822920 1320830
set jd3187 [$e addTechVia [V VIA67]]
$e newPath $jd3187 FIXED
$e addPoint 2822840 1320830
set jd3188 [$e addTechVia [V VIA56]]
$e newPath $jd3188 FIXED
$e addPoint 2822840 1320926
set jd3189 [$e addTechVia [V VIA45]]
$e newPath $jd3189 FIXED
$e addPoint 2822744 1320926
set jd3190 [$e addTechVia [V VIA34]]
$e newPath $jd3190 FIXED
$e addPoint 2822744 1320750
set jd3191 [$e addTechVia [V VIA23]]
$e newPath $jd3191 FIXED
$e addPoint 2822931 1320750
set jd3192 [$e addTechVia [V VIA12]]
$e newPath $jd3192 FIXED
$e addITerm [IT L_clk_t70 A]
$e newPath $emj460 FIXED [RL M9]
set jd3193 [$e addTechVia [V {VIA89}]]
$e newPath $jd3193 FIXED [RL M8]
$e addPoint 3337000 1374750
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337000 1374830
set jd3194 [$e addTechVia [V VIA67]]
$e newPath $jd3194 FIXED
$e addPoint 3336920 1374830
set jd3195 [$e addTechVia [V VIA56]]
$e newPath $jd3195 FIXED
$e addPoint 3336920 1374926
set jd3196 [$e addTechVia [V VIA45]]
$e newPath $jd3196 FIXED
$e addPoint 3336824 1374926
set jd3197 [$e addTechVia [V VIA34]]
$e newPath $jd3197 FIXED
$e addPoint 3336824 1374750
set jd3198 [$e addTechVia [V VIA23]]
$e newPath $jd3198 FIXED
$e addPoint 3337011 1374750
set jd3199 [$e addTechVia [V VIA12]]
$e newPath $jd3199 FIXED
$e addITerm [IT L_clk_t71 A]
$e newPath $emj734 FIXED [RL M9]
set jd3200 [$e addTechVia [V {VIA89}]]
$e newPath $jd3200 FIXED [RL M8]
$e addPoint 3644120 1484010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3644120 1484090
set jd3201 [$e addTechVia [V VIA67]]
$e newPath $jd3201 FIXED
$e addPoint 3644200 1484090
set jd3202 [$e addTechVia [V VIA56]]
$e newPath $jd3202 FIXED
$e addPoint 3644200 1484186
set jd3203 [$e addTechVia [V VIA45]]
$e newPath $jd3203 FIXED
$e addPoint 3645355 1484186
set jd3204 [$e addTechVia [V VIA34]]
$e newPath $jd3204 FIXED
$e addPoint 3645355 1484010
set jd3205 [$e addTechVia [V VIA23]]
$e newPath $jd3205 FIXED
$e addPoint 3645405 1484010
set jd3206 [$e addTechVia [V VIA12]]
$e newPath $jd3206 FIXED
$e addITerm [IT L_clk_t72 A]
$e newPath $emj732 FIXED [RL M9]
set jd3207 [$e addTechVia [V {VIA89}]]
$e newPath $jd3207 FIXED [RL M8]
$e addPoint 4106360 1484010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4106360 1484090
set jd3208 [$e addTechVia [V VIA67]]
$e newPath $jd3208 FIXED
$e addPoint 4106440 1484090
set jd3209 [$e addTechVia [V VIA56]]
$e newPath $jd3209 FIXED
$e addPoint 4106440 1484186
set jd3210 [$e addTechVia [V VIA45]]
$e newPath $jd3210 FIXED
$e addPoint 4107595 1484186
set jd3211 [$e addTechVia [V VIA34]]
$e newPath $jd3211 FIXED
$e addPoint 4107595 1484010
set jd3212 [$e addTechVia [V VIA23]]
$e newPath $jd3212 FIXED
$e addPoint 4107645 1484010
set jd3213 [$e addTechVia [V VIA12]]
$e newPath $jd3213 FIXED
$e addITerm [IT L_clk_t73 A]
$e newPath $emj867 FIXED [RL M9]
set jd3214 [$e addTechVia [V {VIA89}]]
$e newPath $jd3214 FIXED [RL M8]
$e addPoint 4499480 1484010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4499480 1484090
set jd3215 [$e addTechVia [V VIA67]]
$e newPath $jd3215 FIXED
$e addPoint 4499560 1484090
set jd3216 [$e addTechVia [V VIA56]]
$e newPath $jd3216 FIXED
$e addPoint 4499560 1484186
set jd3217 [$e addTechVia [V VIA45]]
$e newPath $jd3217 FIXED
$e addPoint 4499656 1484186
set jd3218 [$e addTechVia [V VIA34]]
$e newPath $jd3218 FIXED
$e addPoint 4499656 1484010
set jd3219 [$e addTechVia [V VIA23]]
$e newPath $jd3219 FIXED
$e addPoint 4499415 1484010
set jd3220 [$e addTechVia [V VIA12]]
$e newPath $jd3220 FIXED
$e addITerm [IT L_clk_t74 A]
$e newPath $emj725 FIXED [RL M9]
set jd3221 [$e addTechVia [V {VIA89}]]
$e newPath $jd3221 FIXED [RL M8]
$e addPoint 4879240 1374750
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4879240 1374830
set jd3222 [$e addTechVia [V VIA67]]
$e newPath $jd3222 FIXED
$e addPoint 4879160 1374830
set jd3223 [$e addTechVia [V VIA56]]
$e newPath $jd3223 FIXED
$e addPoint 4879160 1374926
set jd3224 [$e addTechVia [V VIA45]]
$e newPath $jd3224 FIXED
$e addPoint 4879064 1374926
set jd3225 [$e addTechVia [V VIA34]]
$e newPath $jd3225 FIXED
$e addPoint 4879064 1374750
set jd3226 [$e addTechVia [V VIA23]]
$e newPath $jd3226 FIXED
$e addPoint 4879251 1374750
set jd3227 [$e addTechVia [V VIA12]]
$e newPath $jd3227 FIXED
$e addITerm [IT L_clk_t75 A]
$e newPath $emj994 FIXED [RL M9]
set jd3228 [$e addTechVia [V {VIA89}]]
$e newPath $jd3228 FIXED [RL M8]
$e addPoint 5281400 944010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5281400 944090
set jd3229 [$e addTechVia [V VIA67]]
$e newPath $jd3229 FIXED
$e addPoint 5281480 944090
set jd3230 [$e addTechVia [V VIA56]]
$e newPath $jd3230 FIXED
$e addPoint 5281480 944186
set jd3231 [$e addTechVia [V VIA45]]
$e newPath $jd3231 FIXED
$e addPoint 5282311 944186
set jd3232 [$e addTechVia [V VIA34]]
$e newPath $jd3232 FIXED
$e addPoint 5282311 944010
set jd3233 [$e addTechVia [V VIA23]]
$e newPath $jd3233 FIXED
$e addPoint 5282361 944010
set jd3234 [$e addTechVia [V VIA12]]
$e newPath $jd3234 FIXED
$e addITerm [IT L_clk_t76 A]
$e newPath $emj931 FIXED [RL M9]
set jd3235 [$e addTechVia [V {VIA89}]]
$e newPath $jd3235 FIXED [RL M8]
$e addPoint 5907400 1374750
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5907400 1374830
set jd3236 [$e addTechVia [V VIA67]]
$e newPath $jd3236 FIXED
$e addPoint 5907320 1374830
set jd3237 [$e addTechVia [V VIA56]]
$e newPath $jd3237 FIXED
$e addPoint 5907320 1374926
set jd3238 [$e addTechVia [V VIA45]]
$e newPath $jd3238 FIXED
$e addPoint 5907224 1374926
set jd3239 [$e addTechVia [V VIA34]]
$e newPath $jd3239 FIXED
$e addPoint 5907224 1374750
set jd3240 [$e addTechVia [V VIA23]]
$e newPath $jd3240 FIXED
$e addPoint 5907411 1374750
set jd3241 [$e addTechVia [V VIA12]]
$e newPath $jd3241 FIXED
$e addITerm [IT L_clk_t77 A]
$e newPath $emj1085 FIXED [RL M9]
set jd3242 [$e addTechVia [V {VIA89}]]
$e newPath $jd3242 FIXED [RL M8]
$e addPoint 6020120 1484010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6020120 1484090
set jd3243 [$e addTechVia [V VIA67]]
$e newPath $jd3243 FIXED
$e addPoint 6020200 1484090
set jd3244 [$e addTechVia [V VIA56]]
$e newPath $jd3244 FIXED
$e addPoint 6020200 1484186
set jd3245 [$e addTechVia [V VIA45]]
$e newPath $jd3245 FIXED
$e addPoint 6021247 1484186
set jd3246 [$e addTechVia [V VIA34]]
$e newPath $jd3246 FIXED
$e addPoint 6021247 1484010
set jd3247 [$e addTechVia [V VIA23]]
$e newPath $jd3247 FIXED
$e addPoint 6021297 1484010
set jd3248 [$e addTechVia [V VIA12]]
$e newPath $jd3248 FIXED
$e addITerm [IT L_clk_t78 A]
$e newPath $emj1003 FIXED [RL M9]
set jd3249 [$e addTechVia [V {VIA89}]]
$e newPath $jd3249 FIXED [RL M8]
$e addPoint 6417160 1374750
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6417160 1374830
set jd3250 [$e addTechVia [V VIA67]]
$e newPath $jd3250 FIXED
$e addPoint 6417080 1374830
set jd3251 [$e addTechVia [V VIA56]]
$e newPath $jd3251 FIXED
$e addPoint 6417080 1374926
set jd3252 [$e addTechVia [V VIA45]]
$e newPath $jd3252 FIXED
$e addPoint 6416984 1374926
set jd3253 [$e addTechVia [V VIA34]]
$e newPath $jd3253 FIXED
$e addPoint 6416984 1374750
set jd3254 [$e addTechVia [V VIA23]]
$e newPath $jd3254 FIXED
$e addPoint 6417171 1374750
set jd3255 [$e addTechVia [V VIA12]]
$e newPath $jd3255 FIXED
$e addITerm [IT L_clk_t79 A]
$e newPath $emj327 FIXED [RL M9]
set jd3256 [$e addTechVia [V {VIA89}]]
$e newPath $jd3256 FIXED [RL M8]
$e addPoint 3337000 103590
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3337000 103670
set jd3257 [$e addTechVia [V VIA67]]
$e newPath $jd3257 FIXED
$e addPoint 3336920 103670
set jd3258 [$e addTechVia [V VIA56]]
$e newPath $jd3258 FIXED
$e addPoint 3336920 103766
set jd3259 [$e addTechVia [V VIA45]]
$e newPath $jd3259 FIXED
$e addPoint 3336824 103766
set jd3260 [$e addTechVia [V VIA34]]
$e newPath $jd3260 FIXED
$e addPoint 3336824 103590
set jd3261 [$e addTechVia [V VIA23]]
$e newPath $jd3261 FIXED
$e addPoint 3337011 103590
set jd3262 [$e addTechVia [V VIA12]]
$e newPath $jd3262 FIXED
$e addITerm [IT L_clk_t8 A]
$e newPath $emj1343 FIXED [RL M9]
set jd3263 [$e addTechVia [V {VIA89}]]
$e newPath $jd3263 FIXED [RL M8]
$e addPoint 6931240 1182510
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 6931240 1182590
set jd3264 [$e addTechVia [V VIA67]]
$e newPath $jd3264 FIXED
$e addPoint 6931160 1182590
set jd3265 [$e addTechVia [V VIA56]]
$e newPath $jd3265 FIXED
$e addPoint 6931160 1182686
set jd3266 [$e addTechVia [V VIA45]]
$e newPath $jd3266 FIXED
$e addPoint 6931064 1182686
set jd3267 [$e addTechVia [V VIA34]]
$e newPath $jd3267 FIXED
$e addPoint 6931064 1182510
set jd3268 [$e addTechVia [V VIA23]]
$e newPath $jd3268 FIXED
$e addPoint 6931251 1182510
set jd3269 [$e addTechVia [V VIA12]]
$e newPath $jd3269 FIXED
$e addITerm [IT L_clk_t80 A]
$e newPath $emj1480 FIXED [RL M9]
set jd3270 [$e addTechVia [V {VIA89}]]
$e newPath $jd3270 FIXED [RL M8]
$e addPoint 7445320 1182510
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7445320 1182590
set jd3271 [$e addTechVia [V VIA67]]
$e newPath $jd3271 FIXED
$e addPoint 7445240 1182590
set jd3272 [$e addTechVia [V VIA56]]
$e newPath $jd3272 FIXED
$e addPoint 7445240 1182686
set jd3273 [$e addTechVia [V VIA45]]
$e newPath $jd3273 FIXED
$e addPoint 7445144 1182686
set jd3274 [$e addTechVia [V VIA34]]
$e newPath $jd3274 FIXED
$e addPoint 7445144 1182510
set jd3275 [$e addTechVia [V VIA23]]
$e newPath $jd3275 FIXED
$e addPoint 7445331 1182510
set jd3276 [$e addTechVia [V VIA12]]
$e newPath $jd3276 FIXED
$e addITerm [IT L_clk_t81 A]
$e newPath $emj1552 FIXED [RL M9]
set jd3277 [$e addTechVia [V {VIA89}]]
$e newPath $jd3277 FIXED [RL M8]
$e addPoint 7631080 1484010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 7631080 1484090
set jd3278 [$e addTechVia [V VIA67]]
$e newPath $jd3278 FIXED
$e addPoint 7631000 1484090
set jd3279 [$e addTechVia [V VIA56]]
$e newPath $jd3279 FIXED
$e addPoint 7631000 1484186
set jd3280 [$e addTechVia [V VIA45]]
$e newPath $jd3280 FIXED
$e addPoint 7629575 1484186
set jd3281 [$e addTechVia [V VIA34]]
$e newPath $jd3281 FIXED
$e addPoint 7629575 1484010
set jd3282 [$e addTechVia [V VIA23]]
$e newPath $jd3282 FIXED
$e addPoint 7629525 1484010
set jd3283 [$e addTechVia [V VIA12]]
$e newPath $jd3283 FIXED
$e addITerm [IT L_clk_t82 A]
$e newPath $emj1765 FIXED [RL M9]
set jd3284 [$e addTechVia [V {VIA89}]]
$e newPath $jd3284 FIXED [RL M8]
$e addPoint 8089000 1484010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 8089000 1484090
set jd3285 [$e addTechVia [V VIA67]]
$e newPath $jd3285 FIXED
$e addPoint 8088920 1484090
set jd3286 [$e addTechVia [V VIA56]]
$e newPath $jd3286 FIXED
$e addPoint 8088920 1484186
set jd3287 [$e addTechVia [V VIA45]]
$e newPath $jd3287 FIXED
$e addPoint 8087819 1484186
set jd3288 [$e addTechVia [V VIA34]]
$e newPath $jd3288 FIXED
$e addPoint 8087819 1484010
set jd3289 [$e addTechVia [V VIA23]]
$e newPath $jd3289 FIXED
$e addPoint 8087769 1484010
set jd3290 [$e addTechVia [V VIA12]]
$e newPath $jd3290 FIXED
$e addITerm [IT L_clk_t83 A]
$e newPath $emj273 FIXED [RL M9]
set jd3291 [$e addTechVia [V {VIA89}]]
$e newPath $jd3291 FIXED [RL M8]
$e addPoint 256840 1791270
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 256840 1791350
set jd3292 [$e addTechVia [V VIA67]]
$e newPath $jd3292 FIXED
$e addPoint 256760 1791350
set jd3293 [$e addTechVia [V VIA56]]
$e newPath $jd3293 FIXED
$e addPoint 256760 1791446
set jd3294 [$e addTechVia [V VIA45]]
$e newPath $jd3294 FIXED
$e addPoint 256664 1791446
set jd3295 [$e addTechVia [V VIA34]]
$e newPath $jd3295 FIXED
$e addPoint 256664 1791270
set jd3296 [$e addTechVia [V VIA23]]
$e newPath $jd3296 FIXED
$e addPoint 256851 1791270
set jd3297 [$e addTechVia [V VIA12]]
$e newPath $jd3297 FIXED
$e addITerm [IT L_clk_t84 A]
$e newPath $emj250 FIXED [RL M9]
set jd3298 [$e addTechVia [V {VIA89}]]
$e newPath $jd3298 FIXED [RL M8]
$e addPoint 770920 1789110
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 770920 1789190
set jd3299 [$e addTechVia [V VIA67]]
$e newPath $jd3299 FIXED
$e addPoint 770840 1789190
set jd3300 [$e addTechVia [V VIA56]]
$e newPath $jd3300 FIXED
$e addPoint 770840 1789286
set jd3301 [$e addTechVia [V VIA45]]
$e newPath $jd3301 FIXED
$e addPoint 770744 1789286
set jd3302 [$e addTechVia [V VIA34]]
$e newPath $jd3302 FIXED
$e addPoint 770744 1789110
set jd3303 [$e addTechVia [V VIA23]]
$e newPath $jd3303 FIXED
$e addPoint 770931 1789110
set jd3304 [$e addTechVia [V VIA12]]
$e newPath $jd3304 FIXED
$e addITerm [IT L_clk_t85 A]
$e newPath $emj250 FIXED [RL M9]
set jd3305 [$e addTechVia [V {VIA89}]]
$e newPath $jd3305 FIXED [RL M8]
$e addPoint 771320 1789110
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 771320 1789190
set jd3306 [$e addTechVia [V VIA67]]
$e newPath $jd3306 FIXED
$e addPoint 771400 1789190
set jd3307 [$e addTechVia [V VIA56]]
$e newPath $jd3307 FIXED
$e addPoint 771400 1789286
set jd3308 [$e addTechVia [V VIA45]]
$e newPath $jd3308 FIXED
$e addPoint 771496 1789286
set jd3309 [$e addTechVia [V VIA34]]
$e newPath $jd3309 FIXED
$e addPoint 771496 1789110
set jd3310 [$e addTechVia [V VIA23]]
$e newPath $jd3310 FIXED
$e addPoint 771363 1789110
set jd3311 [$e addTechVia [V VIA12]]
$e newPath $jd3311 FIXED
$e addITerm [IT L_clk_t86 A]
$e newPath $emj437 FIXED [RL M9]
set jd3312 [$e addTechVia [V {VIA89}]]
$e newPath $jd3312 FIXED [RL M8]
$e addPoint 1285000 1791270
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1285000 1791350
set jd3313 [$e addTechVia [V VIA67]]
$e newPath $jd3313 FIXED
$e addPoint 1284920 1791350
set jd3314 [$e addTechVia [V VIA56]]
$e newPath $jd3314 FIXED
$e addPoint 1284920 1791446
set jd3315 [$e addTechVia [V VIA45]]
$e newPath $jd3315 FIXED
$e addPoint 1284824 1791446
set jd3316 [$e addTechVia [V VIA34]]
$e newPath $jd3316 FIXED
$e addPoint 1284824 1791270
set jd3317 [$e addTechVia [V VIA23]]
$e newPath $jd3317 FIXED
$e addPoint 1285011 1791270
set jd3318 [$e addTechVia [V VIA12]]
$e newPath $jd3318 FIXED
$e addITerm [IT L_clk_t87 A]
$e newPath $emj477 FIXED [RL M9]
set jd3319 [$e addTechVia [V {VIA89}]]
$e newPath $jd3319 FIXED [RL M8]
$e addPoint 1682840 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 1682840 1756250
set jd3320 [$e addTechVia [V VIA67]]
$e newPath $jd3320 FIXED
$e addPoint 1682920 1756250
set jd3321 [$e addTechVia [V VIA56]]
$e newPath $jd3321 FIXED
$e addPoint 1682920 1756346
set jd3322 [$e addTechVia [V VIA45]]
$e newPath $jd3322 FIXED
$e addPoint 1683016 1756346
set jd3323 [$e addTechVia [V VIA34]]
$e newPath $jd3323 FIXED
$e addPoint 1683016 1756170
set jd3324 [$e addTechVia [V VIA23]]
$e newPath $jd3324 FIXED
$e addPoint 1682775 1756170
set jd3325 [$e addTechVia [V VIA12]]
$e newPath $jd3325 FIXED
$e addITerm [IT L_clk_t88 A]
$e newPath $emj811 FIXED [RL M9]
set jd3326 [$e addTechVia [V {VIA89}]]
$e newPath $jd3326 FIXED [RL M8]
$e addPoint 2373640 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2373640 1756250
set jd3327 [$e addTechVia [V VIA67]]
$e newPath $jd3327 FIXED
$e addPoint 2373560 1756250
set jd3328 [$e addTechVia [V VIA56]]
$e newPath $jd3328 FIXED
$e addPoint 2373560 1756346
set jd3329 [$e addTechVia [V VIA45]]
$e newPath $jd3329 FIXED
$e addPoint 2372783 1756346
set jd3330 [$e addTechVia [V VIA34]]
$e newPath $jd3330 FIXED
$e addPoint 2372783 1756170
set jd3331 [$e addTechVia [V VIA23]]
$e newPath $jd3331 FIXED
$e addPoint 2372733 1756170
set jd3332 [$e addTechVia [V VIA12]]
$e newPath $jd3332 FIXED
$e addITerm [IT L_clk_t89 A]
$e newPath $emj455 FIXED [RL M9]
set jd3333 [$e addTechVia [V {VIA89}]]
$e newPath $jd3333 FIXED [RL M8]
$e addPoint 3717160 136170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3717160 136250
set jd3334 [$e addTechVia [V VIA67]]
$e newPath $jd3334 FIXED
$e addPoint 3717080 136250
set jd3335 [$e addTechVia [V VIA56]]
$e newPath $jd3335 FIXED
$e addPoint 3717080 136346
set jd3336 [$e addTechVia [V VIA45]]
$e newPath $jd3336 FIXED
$e addPoint 3716897 136346
set jd3337 [$e addTechVia [V VIA34]]
$e newPath $jd3337 FIXED
$e addPoint 3716897 136170
set jd3338 [$e addTechVia [V VIA23]]
$e newPath $jd3338 FIXED
$e addPoint 3716847 136170
set jd3339 [$e addTechVia [V VIA12]]
$e newPath $jd3339 FIXED
$e addITerm [IT L_clk_t9 A]
$e newPath $emj883 FIXED [RL M9]
set jd3340 [$e addTechVia [V {VIA89}]]
$e newPath $jd3340 FIXED [RL M8]
$e addPoint 2399960 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 2399960 1756250
set jd3341 [$e addTechVia [V VIA67]]
$e newPath $jd3341 FIXED
$e addPoint 2400040 1756250
set jd3342 [$e addTechVia [V VIA56]]
$e newPath $jd3342 FIXED
$e addPoint 2400040 1756346
set jd3343 [$e addTechVia [V VIA45]]
$e newPath $jd3343 FIXED
$e addPoint 2400439 1756346
set jd3344 [$e addTechVia [V VIA34]]
$e newPath $jd3344 FIXED
$e addPoint 2400439 1756170
set jd3345 [$e addTechVia [V VIA23]]
$e newPath $jd3345 FIXED
$e addPoint 2400489 1756170
set jd3346 [$e addTechVia [V VIA12]]
$e newPath $jd3346 FIXED
$e addITerm [IT L_clk_t90 A]
$e newPath $emj1030 FIXED [RL M9]
set jd3347 [$e addTechVia [V {VIA89}]]
$e newPath $jd3347 FIXED [RL M8]
$e addPoint 3198760 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3198760 1756250
set jd3348 [$e addTechVia [V VIA67]]
$e newPath $jd3348 FIXED
$e addPoint 3198680 1756250
set jd3349 [$e addTechVia [V VIA56]]
$e newPath $jd3349 FIXED
$e addPoint 3198680 1756346
set jd3350 [$e addTechVia [V VIA45]]
$e newPath $jd3350 FIXED
$e addPoint 3197903 1756346
set jd3351 [$e addTechVia [V VIA34]]
$e newPath $jd3351 FIXED
$e addPoint 3197903 1756170
set jd3352 [$e addTechVia [V VIA23]]
$e newPath $jd3352 FIXED
$e addPoint 3197853 1756170
set jd3353 [$e addTechVia [V VIA12]]
$e newPath $jd3353 FIXED
$e addITerm [IT L_clk_t91 A]
$e newPath $emj1104 FIXED [RL M9]
set jd3354 [$e addTechVia [V {VIA89}]]
$e newPath $jd3354 FIXED [RL M8]
$e addPoint 3281240 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3281240 1756250
set jd3355 [$e addTechVia [V VIA67]]
$e newPath $jd3355 FIXED
$e addPoint 3281320 1756250
set jd3356 [$e addTechVia [V VIA56]]
$e newPath $jd3356 FIXED
$e addPoint 3281320 1756346
set jd3357 [$e addTechVia [V VIA45]]
$e newPath $jd3357 FIXED
$e addPoint 3282367 1756346
set jd3358 [$e addTechVia [V VIA34]]
$e newPath $jd3358 FIXED
$e addPoint 3282367 1756170
set jd3359 [$e addTechVia [V VIA23]]
$e newPath $jd3359 FIXED
$e addPoint 3282417 1756170
set jd3360 [$e addTechVia [V VIA12]]
$e newPath $jd3360 FIXED
$e addITerm [IT L_clk_t92 A]
$e newPath $emj1033 FIXED [RL M9]
set jd3361 [$e addTechVia [V {VIA89}]]
$e newPath $jd3361 FIXED [RL M8]
$e addPoint 3557720 2024010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 3557720 2024090
set jd3362 [$e addTechVia [V VIA67]]
$e newPath $jd3362 FIXED
$e addPoint 3557800 2024090
set jd3363 [$e addTechVia [V VIA56]]
$e newPath $jd3363 FIXED
$e addPoint 3557800 2024186
set jd3364 [$e addTechVia [V VIA45]]
$e newPath $jd3364 FIXED
$e addPoint 3558955 2024186
set jd3365 [$e addTechVia [V VIA34]]
$e newPath $jd3365 FIXED
$e addPoint 3558955 2024010
set jd3366 [$e addTechVia [V VIA23]]
$e newPath $jd3366 FIXED
$e addPoint 3559005 2024010
set jd3367 [$e addTechVia [V VIA12]]
$e newPath $jd3367 FIXED
$e addITerm [IT L_clk_t93 A]
$e newPath $emj1097 FIXED [RL M9]
set jd3368 [$e addTechVia [V {VIA89}]]
$e newPath $jd3368 FIXED [RL M8]
$e addPoint 4106360 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4106360 1756250
set jd3369 [$e addTechVia [V VIA67]]
$e newPath $jd3369 FIXED
$e addPoint 4106440 1756250
set jd3370 [$e addTechVia [V VIA56]]
$e newPath $jd3370 FIXED
$e addPoint 4106440 1756346
set jd3371 [$e addTechVia [V VIA45]]
$e newPath $jd3371 FIXED
$e addPoint 4107595 1756346
set jd3372 [$e addTechVia [V VIA34]]
$e newPath $jd3372 FIXED
$e addPoint 4107595 1756170
set jd3373 [$e addTechVia [V VIA23]]
$e newPath $jd3373 FIXED
$e addPoint 4107645 1756170
set jd3374 [$e addTechVia [V VIA12]]
$e newPath $jd3374 FIXED
$e addITerm [IT L_clk_t94 A]
$e newPath $emj1229 FIXED [RL M9]
set jd3375 [$e addTechVia [V {VIA89}]]
$e newPath $jd3375 FIXED [RL M8]
$e addPoint 4499480 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4499480 1756250
set jd3376 [$e addTechVia [V VIA67]]
$e newPath $jd3376 FIXED
$e addPoint 4499560 1756250
set jd3377 [$e addTechVia [V VIA56]]
$e newPath $jd3377 FIXED
$e addPoint 4499560 1756346
set jd3378 [$e addTechVia [V VIA45]]
$e newPath $jd3378 FIXED
$e addPoint 4499656 1756346
set jd3379 [$e addTechVia [V VIA34]]
$e newPath $jd3379 FIXED
$e addPoint 4499656 1756170
set jd3380 [$e addTechVia [V VIA23]]
$e newPath $jd3380 FIXED
$e addPoint 4499415 1756170
set jd3381 [$e addTechVia [V VIA12]]
$e newPath $jd3381 FIXED
$e addITerm [IT L_clk_t95 A]
$e newPath $emj1285 FIXED [RL M9]
set jd3382 [$e addTechVia [V {VIA89}]]
$e newPath $jd3382 FIXED [RL M8]
$e addPoint 4892200 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 4892200 1756250
set jd3383 [$e addTechVia [V VIA67]]
$e newPath $jd3383 FIXED
$e addPoint 4892120 1756250
set jd3384 [$e addTechVia [V VIA56]]
$e newPath $jd3384 FIXED
$e addPoint 4892120 1756346
set jd3385 [$e addTechVia [V VIA45]]
$e newPath $jd3385 FIXED
$e addPoint 4890695 1756346
set jd3386 [$e addTechVia [V VIA34]]
$e newPath $jd3386 FIXED
$e addPoint 4890695 1756170
set jd3387 [$e addTechVia [V VIA23]]
$e newPath $jd3387 FIXED
$e addPoint 4890645 1756170
set jd3388 [$e addTechVia [V VIA12]]
$e newPath $jd3388 FIXED
$e addITerm [IT L_clk_t96 A]
$e newPath $emj1295 FIXED [RL M9]
set jd3389 [$e addTechVia [V {VIA89}]]
$e newPath $jd3389 FIXED [RL M8]
$e addPoint 5281400 2024010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5281400 2024090
set jd3390 [$e addTechVia [V VIA67]]
$e newPath $jd3390 FIXED
$e addPoint 5281480 2024090
set jd3391 [$e addTechVia [V VIA56]]
$e newPath $jd3391 FIXED
$e addPoint 5281480 2024186
set jd3392 [$e addTechVia [V VIA45]]
$e newPath $jd3392 FIXED
$e addPoint 5281879 2024186
set jd3393 [$e addTechVia [V VIA34]]
$e newPath $jd3393 FIXED
$e addPoint 5281879 2024010
set jd3394 [$e addTechVia [V VIA23]]
$e newPath $jd3394 FIXED
$e addPoint 5281929 2024010
set jd3395 [$e addTechVia [V VIA12]]
$e newPath $jd3395 FIXED
$e addITerm [IT L_clk_t97 A]
$e newPath $emj1352 FIXED [RL M9]
set jd3396 [$e addTechVia [V {VIA89}]]
$e newPath $jd3396 FIXED [RL M8]
$e addPoint 5674120 2024010
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5674120 2024090
set jd3397 [$e addTechVia [V VIA67]]
$e newPath $jd3397 FIXED
$e addPoint 5674040 2024090
set jd3398 [$e addTechVia [V VIA56]]
$e newPath $jd3398 FIXED
$e addPoint 5674040 2024186
set jd3399 [$e addTechVia [V VIA45]]
$e newPath $jd3399 FIXED
$e addPoint 5673263 2024186
set jd3400 [$e addTechVia [V VIA34]]
$e newPath $jd3400 FIXED
$e addPoint 5673263 2024010
set jd3401 [$e addTechVia [V VIA23]]
$e newPath $jd3401 FIXED
$e addPoint 5673213 2024010
set jd3402 [$e addTechVia [V VIA12]]
$e newPath $jd3402 FIXED
$e addITerm [IT L_clk_t98 A]
$e newPath $emj1287 FIXED [RL M9]
set jd3403 [$e addTechVia [V {VIA89}]]
$e newPath $jd3403 FIXED [RL M8]
$e addPoint 5933720 1756170
set jv [$e addTechVia [V VIA78]]
$e newPath $jv FIXED
$e addPoint 5933720 1756250
set jd3404 [$e addTechVia [V VIA67]]
$e newPath $jd3404 FIXED
$e addPoint 5933800 1756250
set jd3405 [$e addTechVia [V VIA56]]
$e newPath $jd3405 FIXED
$e addPoint 5933800 1756346
set jd3406 [$e addTechVia [V VIA45]]
$e newPath $jd3406 FIXED
$e addPoint 5934847 1756346
set jd3407 [$e addTechVia [V VIA34]]
$e newPath $jd3407 FIXED
$e addPoint 5934847 1756170
set jd3408 [$e addTechVia [V VIA23]]
$e newPath $jd3408 FIXED
$e addPoint 5934897 1756170
set jd3409 [$e addTechVia [V VIA12]]
$e newPath $jd3409 FIXED
$e addITerm [IT L_clk_t99 A]
$e end
set ot_ndr $em_saved_ndr
puts "OT_ROUTED_CLOCK nets 1 pin_stairs 487 port_joins 0"
