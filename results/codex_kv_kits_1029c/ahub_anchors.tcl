# Actual-connectivity planned FF anchors; no net/master/RTL/pin changes.
set b [ord::get_db_block]
set u [[ord::get_db_tech] getDbUnitsPerMicron]
set oo {}
foreach r [$b getRows] {dict set oo [lindex [$r getOrigin] 1] [$r getOrient]}
set c [$b findInst {u_leaf.ap\[0\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[100\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[101\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[102\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[103\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[104\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[105\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[106\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[107\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[108\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[109\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[10\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[110\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[111\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[112\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[113\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[114\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[115\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[116\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[117\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[118\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[119\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[11\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[120\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[121\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[122\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[123\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[124\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[125\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[126\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[127\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[128\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[129\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[12\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[130\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[131\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[132\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[133\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[134\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[135\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[136\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[137\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[138\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[139\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[13\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[140\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[141\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[142\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[143\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[144\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[145\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[146\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[147\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[148\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[149\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[14\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[150\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[151\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[152\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[153\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[154\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[155\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[156\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[157\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[158\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[159\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[15\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[160\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[161\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[162\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[163\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[164\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[165\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[166\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[167\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[168\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[169\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[16\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[170\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[171\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[17\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[18\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[19\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[20\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[21\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[22\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[23\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[24\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[25\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[26\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[27\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[28\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[29\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[2\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[30\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[31\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[32\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[33\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[34\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[35\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[36\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[37\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[38\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[39\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[3\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[40\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[41\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[42\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[43\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[44\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[45\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[46\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[47\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[48\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[49\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[4\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[50\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[51\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[52\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[53\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[54\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[55\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[56\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[57\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[58\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[59\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[5\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[60\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[61\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[62\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[63\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[64\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[65\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[66\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[67\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[68\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[69\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[6\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[70\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[71\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[72\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[73\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[74\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[75\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[76\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[77\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[78\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[79\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[7\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[80\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[81\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[82\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[83\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[84\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[85\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[86\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[87\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[88\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[89\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[8\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[90\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[91\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[92\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[93\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[94\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[95\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[96\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[97\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[98\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[99\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.ap\[9\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[0\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[100\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[101\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[102\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[103\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[104\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[105\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[107\]$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[108\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[109\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[10\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[110\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[111\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[112\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[113\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[114\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[115\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[116\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[117\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[118\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[119\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[11\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[120\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[121\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[122\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[123\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[124\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[125\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[126\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[127\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[128\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[129\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[12\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[130\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[131\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[132\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[133\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[134\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[135\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[136\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[137\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[138\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[139\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[13\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[140\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[141\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[143\]$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[14\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[15\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[16\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[17\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[18\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[19\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[20\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[21\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[22\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[23\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[24\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[25\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[26\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[27\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[28\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[29\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[2\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[30\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[31\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[32\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[33\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[35\]$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[36\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[37\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[38\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[39\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[3\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[40\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[41\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[42\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[43\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[44\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[45\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[46\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[47\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[48\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[49\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[4\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[50\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[51\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[52\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[53\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[54\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[55\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[56\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[57\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[58\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[59\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[5\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[60\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[61\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[62\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[63\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[64\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[65\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[66\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[67\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[68\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[69\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[6\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[71\]$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[72\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[73\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[74\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[75\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[76\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[77\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[78\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[79\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[7\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[80\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[81\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[82\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[83\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[84\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[85\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[86\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[87\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[88\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[89\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[8\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[90\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[91\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[92\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[93\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[94\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[95\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[96\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[97\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[98\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[99\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.am\[9\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[0\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[10\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[11\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[12\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[13\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[2\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[3\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[4\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[5\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[6\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[7\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[8\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.T_p\[9\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[0\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[100\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[101\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[102\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[103\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[104\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[105\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[106\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[107\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[108\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[109\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[10\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[110\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[111\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[11\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[12\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[13\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[14\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[15\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[16\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[17\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[18\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[19\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[20\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[21\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[22\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[23\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[24\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[25\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[26\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[27\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[28\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[29\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[2\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[30\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[31\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[32\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[33\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[34\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[35\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[36\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[37\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[38\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[39\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[3\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[40\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[41\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[42\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[43\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[44\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[45\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[46\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[47\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[48\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[49\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[4\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[50\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[51\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[52\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[53\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[54\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[55\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[56\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[57\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[58\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[59\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[5\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[60\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[61\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[62\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[63\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[64\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[65\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[66\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[67\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[68\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[69\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[6\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[70\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[71\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[72\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[73\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[74\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[75\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[76\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[77\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[78\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[79\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[7\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[80\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[81\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[82\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[83\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[84\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[85\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[86\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[87\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[88\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[89\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[8\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[90\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[91\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[92\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[93\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[94\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[95\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[96\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[97\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[98\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[99\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_q\[9\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[0\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[10\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[11\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[12\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[13\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[14\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[15\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[2\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[3\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[4\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[5\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[6\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[7\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[8\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.cal_r_q\[9\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[0\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[10\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[11\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[12\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[13\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[14\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[15\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[2\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[3\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[4\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[5\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[6\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[7\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[8\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.epoch\[9\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fault$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.layer\[0\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.layer\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.layer\[2\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.layer\[3\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.layer\[4\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.layer\[5\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.start$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rr.s0$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rr.s1$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[0\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[100\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[101\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[102\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[103\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[104\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[105\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[106\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[107\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[108\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[109\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[10\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[110\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[111\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[112\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[113\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[114\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[115\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[116\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[117\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[118\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[119\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[11\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[120\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[121\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[122\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[123\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[124\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[125\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[126\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[127\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[128\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[129\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[12\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[130\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[131\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[132\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[133\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[134\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[135\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[136\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[137\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[138\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[139\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[13\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[140\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[141\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[142\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[143\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[144\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[14\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[15\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[16\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[17\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[18\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[19\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[20\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[21\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[22\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[23\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[24\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[25\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[26\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[27\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[28\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[29\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[2\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[30\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[31\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[32\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[33\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[34\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[35\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[36\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[37\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[38\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[39\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[3\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[40\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[41\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[42\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[43\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[44\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[45\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[46\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[47\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[48\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[49\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[4\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[50\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[51\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[52\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[53\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[54\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[55\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[56\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[57\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[58\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[59\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[5\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[60\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[61\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[62\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[63\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[64\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[65\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[66\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[67\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[68\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[69\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[6\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[70\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[71\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[72\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[73\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[74\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[75\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[76\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[77\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[78\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[79\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[7\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[80\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[81\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[82\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[83\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[84\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[85\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[86\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[87\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[88\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[89\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[8\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[90\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[91\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[92\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[93\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[94\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[95\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[96\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[97\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[98\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[99\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_rw.q\[9\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing fixed face flop"}
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.hh_b\[4\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(13.230000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(256.554000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.hh_b\[6\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(24.030000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(270.270000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.start_b$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(8.640000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(210.978000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.hh_b\[5\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(17.820000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(261.144000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.hh_b\[7\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(28.080000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(274.320000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.active$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(14.850000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(499.986000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.em_w$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(19.440000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(569.700000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.z_b\[1\]$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(5.670000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(207.900000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.z_b\[2\]$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(66.420000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(268.812000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.u_rr.rst_n\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(110.430000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.426000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.q_rr$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(58.320000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(456.624000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.k_b\[10\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(14.580000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(257.904000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.k_b\[11\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(29.700000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(273.024000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.k_b\[14\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(16.740000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(262.980000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.k_b\[9\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(229.770000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(192.456000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.z_b\[0\]$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(5.400000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(207.900000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[15\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(54.270000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(460.728000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[14\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(8.910000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(506.088000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[13\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(7.830000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(507.168000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[12\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(10.260000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(504.738000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[11\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(50.490000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(464.400000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[10\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(52.650000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(462.348000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[9\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(7.020000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(507.978000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[8\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(9.990000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(505.008000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[7\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(12.420000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(502.578000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[6\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(57.510000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(457.488000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[5\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(12.960000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(502.308000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[4\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(59.400000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(455.598000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[3\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(54.000000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(460.728000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[1\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(67.230000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(447.876000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.RECIP_RETURN_AGE\[2\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(13.500000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(501.498000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.first_r$_DFF_PN1_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(64.260000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(450.468000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.first_q$_DFF_PN1_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(15.390000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(368.064000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.q_rs\[0\]$_SDFF_PP0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(66.150000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(268.974000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.q_rs\[2\]$_SDFF_PN0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(47.520000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(249.858000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.q_rs\[3\]$_SDFF_PN0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(46.170000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(279.450000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.LMAX_IN_AGE\[43\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(5.130000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(402.246000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[2\]\[26\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(308.610000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(596.484000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[2\]\[27\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(311.040000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(593.946000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[2\]\[28\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(308.340000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(596.754000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[2\]\[29\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(311.850000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(593.136000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[2\]\[30\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(310.230000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(594.864000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[2\]\[31\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(310.500000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(594.702000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[3\]\[11\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(310.770000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(594.486000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[3\]\[14\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(309.150000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(595.782000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[3\]\[20\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(311.310000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(594.216000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[3\]\[21\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(309.960000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(594.756000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[3\]\[22\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(312.390000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(592.596000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[3\]\[26\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(311.580000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(593.946000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[3\]\[27\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(309.690000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(595.188000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[3\]\[28\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(309.420000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(595.728000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[3\]\[29\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(308.880000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(595.728000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[3\]\[30\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(310.500000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(593.622000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rz\[3\]\[31\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(312.660000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(592.326000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.LMAX_IN_AGE\[59\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(5.130000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(412.020000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.LMAX_IN_AGE\[58\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(5.130000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(414.018000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.LMAX_IN_AGE\[57\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(4.860000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(414.936000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.Z_START_AGE\[10\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(5.130000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(463.482000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[0\]\[52\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(228.150000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(179.172000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[0\]\[58\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(225.720000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.264000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[0\]\[8\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(228.690000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(179.172000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[1\]\[32\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(227.070000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.264000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[1\]\[42\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(225.450000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(179.172000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[1\]\[44\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(227.340000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(196.452000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[1\]\[46\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(223.020000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(196.452000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[1\]\[6\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(224.370000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(196.452000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[2\]\[38\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(223.560000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(179.172000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[3\]\[16\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(226.530000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(196.452000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[3\]\[20\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(228.960000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.264000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[3\]\[24\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(227.880000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(196.452000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[3\]\[56\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(229.500000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.264000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zseen\[3\]\[6\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(225.450000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.264000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.epoch\[11\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(11.880000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(589.572000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.epoch\[6\]$_DFFE_PN0P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(9.450000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(589.572000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zh_we\[314\]$_SDFF_PP0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(256.770000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(110.214000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zh_we\[315\]$_SDFF_PP0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(257.850000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(114.210000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zh_we\[318\]$_SDFF_PP0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(255.960000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(109.296000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zh_we\[319\]$_SDFF_PP0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(257.040000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(113.400000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zh_we\[366\]$_SDFF_PP0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(258.660000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(112.050000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zh_we\[367\]$_SDFF_PP0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(258.120000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(114.210000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.LMAX_ISSUE_AGE\[10\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(5.130000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(449.334000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.LMAX_ISSUE_AGE\[12\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(5.130000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(453.870000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.LMAX_ISSUE_AGE\[13\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(4.860000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(454.626000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.LMAX_ISSUE_AGE\[14\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(5.130000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(451.278000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.LMAX_ISSUE_AGE\[7\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(5.130000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(447.120000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.data_b\[100\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(21.060000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(352.134000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.data_b\[117\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(23.220000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(350.946000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.data_b\[121\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(17.280000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(352.134000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.data_b\[96\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(15.120000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(350.946000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.gz\[2\]$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(66.420000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(84.726000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.gz\[3\]$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(27.810000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(329.994000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.si_epoch\[52\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(6.750000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(588.546000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.si_epoch\[57\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(10.260000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(588.546000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.mo_h\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(15.390000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.426000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[0\]\[10\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(382.320000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.426000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[0\]\[12\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(380.700000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(193.104000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[0\]\[14\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(382.050000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.426000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[0\]\[15\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(381.240000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(193.644000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[0\]\[16\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(378.540000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(190.998000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[0\]\[17\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(380.160000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.426000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[0\]\[18\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(379.350000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(191.754000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[0\]\[30\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(383.130000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.426000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[0\]\[31\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(382.860000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.426000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[0\]\[7\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(379.080000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(191.646000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[0\]\[8\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(380.970000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(193.590000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[0\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(381.510000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(193.374000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[10\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(375.030000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(187.542000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[11\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(373.410000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(185.814000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[12\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(371.250000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(183.546000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[13\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(377.190000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(189.486000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[14\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(375.840000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(188.136000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[15\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(378.810000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(191.052000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[16\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(376.650000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(189.162000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[17\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(373.140000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(185.544000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[18\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(374.490000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(186.840000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[19\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(374.760000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(187.380000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(379.620000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(192.078000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[20\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(374.220000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(186.948000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[21\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(376.920000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(189.540000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[22\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(378.270000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(191.160000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[23\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(373.950000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(187.002000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[24\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(379.890000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(191.376000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[25\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(376.110000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(188.298000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[26\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(376.380000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(189.000000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[27\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(375.570000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(188.460000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[28\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(369.630000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(182.142000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[29\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(373.680000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(185.706000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[2\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(380.430000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(192.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[30\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(376.110000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(189.378000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[31\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(369.360000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(181.656000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[3\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(381.780000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(194.454000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[4\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(380.160000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(193.050000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[5\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(379.890000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(192.672000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[6\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(377.460000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(189.972000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[7\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(370.170000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(182.682000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[8\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(381.780000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(193.266000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[2\]\[9\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(375.300000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(187.596000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.rt_q\[3\]\[4\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(417.150000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(260.334000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_epoch\[15\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(42.120000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[0\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(59.670000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[101\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(342.630000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[107\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(322.110000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[109\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(316.980000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[111\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(379.080000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[112\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(379.890000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[113\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(381.510000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[114\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(381.240000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[115\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(380.160000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[119\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(315.360000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[11\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(94.770000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[120\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(316.440000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[127\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(321.570000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[12\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(103.140000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[13\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(103.680000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[14\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(104.220000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[15\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(119.070000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[16\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(119.340000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[18\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(118.530000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[19\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(116.640000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[20\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(116.910000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[22\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(121.230000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[23\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(123.930000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[26\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(133.920000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[27\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(135.540000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[2\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(65.880000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[30\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(142.830000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[32\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(150.390000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[33\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(153.360000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[34\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(156.600000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[35\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(157.680000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[36\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(159.840000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[37\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(161.730000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[39\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(167.130000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[3\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(67.500000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[40\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(171.990000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[42\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(177.930000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[43\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(180.090000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[46\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(186.840000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[48\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(202.230000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[50\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(204.660000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[51\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(206.280000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[52\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(208.980000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[53\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(210.330000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[54\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(214.650000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[55\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(217.080000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[56\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(219.510000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[58\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(223.560000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[5\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(72.360000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[61\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(233.550000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[62\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(235.710000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[64\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(243.270000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[65\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(246.240000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[66\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(250.020000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[67\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(252.450000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[68\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(254.340000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[6\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(72.630000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[70\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(259.470000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[71\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(262.170000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[73\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(268.380000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[75\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(278.910000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[76\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(283.230000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[77\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(285.120000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[78\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(286.470000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[79\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(288.090000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[80\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(290.520000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[81\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(294.300000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[82\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(297.270000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[83\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(300.780000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[85\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(305.100000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[86\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(307.800000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[88\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(311.850000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[91\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(318.060000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[95\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(323.730000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[96\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(334.530000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[97\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(334.800000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[98\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(331.830000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_rz\[9\]$_DFFE_PP_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(95.310000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(597.834000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_io.fr_valid$_DFF_PN0_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(352.350000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(512.352000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.mb_h\[0\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(17.550000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.426000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.u_rr.g_p\[0\].q\[1\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(109.620000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(195.426000 * $u)}] $ay
$c setPlacementStatus FIRM
set c [$b findInst {u_leaf.u_core.zroot_q\[142\]$_DFF_P_}]
if {$c eq "NULL"} {error "missing anchor flop"}
$c setPlacementStatus PLACED
set ay [expr {round(400.680000 * $u)}]
if {![dict exists $oo $ay]} {error "anchor is not on an actual row"}
$c setOrient [dict get $oo $ay]
$c setLocation [expr {round(179.334000 * $u)}] $ay
$c setPlacementStatus FIRM
