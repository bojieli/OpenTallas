import sys
s=open(sys.argv[1]).read()
a='''set e [expr {[dict exists $ot_odd [get_full_name $i]] ? "fall" : "rise"}]; puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_$e] [get_property $q arrival_min_$e]\''''
assert s.count(a)==1
b='''set e [expr {[dict exists $ot_odd [get_full_name $i]] ? "fall" : "rise"}]; set g [expr {$e eq "fall" ? "rise" : "fall"}]; puts $fh "M [string range [get_full_name $i] 3 end] [get_property $q arrival_max_$g] [get_property $q arrival_min_$g]"; puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_$e] [get_property $q arrival_min_$e]\''''
s=s.replace(a,b)
s=s.replace('assert "ot_odd" in tail and \'"F \' in tail,','assert "ot_odd" in tail and \'"F \' in tail and \'"M \' in tail,')
open(sys.argv[2],"w").write("# DIE-QC-19 copy of die-qc11-1028/mk_clkfirst.py + node M rows (source-fall arrival at each clock cell output, polarity-resolved) for tap_fall_merge --tree\n"+s)
