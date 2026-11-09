source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
E=/srv/opentallas-scratch2/claude/hbm-collect-1/n4c/eq
cd $E
for s in old new mut; do for dn in 0 1; do
  { echo "verilog_defines -DSYNTHESIS"
    for f in $E/$s/*.sv; do echo "read_verilog -defer -sv $f"; done
    echo "read_verilog -lib $E/bb.v"; echo "hierarchy -check -top ot_hnx_fused_tnode -chparam DELIVERED_RESET 1 -chparam DN_DEAD_MSB $dn"
    echo "proc; setattr -mod -unset keep_hierarchy *; flatten; hierarchy -top ot_hnx_fused_tnode; opt_clean; memory -nomap; memory_map; async2sync; opt_clean"
    echo "stat"
    if [ $s = old ]; then echo "rename ot_hnx_fused_tnode gold"; else echo "rename ot_hnx_fused_tnode gate"; fi
    echo "write_rtlil $E/${s}_${dn}.il"; } > elab_${s}_${dn}.ys
  yosys -q -l elab_${s}_${dn}.log -s elab_${s}_${dn}.ys || echo ELAB_FAIL $s $dn
done; done
for c in new_0 new_1 mut_1; do dn=${c#*_}
  printf 'read_rtlil %s\nread_rtlil %s\nequiv_make gold gate eq\nhierarchy -top eq\nequiv_simple -seq 8\nequiv_induct -seq 3\nequiv_status -assert\n' $E/old_$dn.il $E/$c.il > eq_$c.ys
  yosys -l eq_$c.log -s eq_$c.ys >/dev/null 2>&1 && echo "EQ $c PROVEN" || echo "EQ $c NOT_PROVEN"
  grep -E "are proven|unproven|ERROR" eq_$c.log | tail -n 2
done
grep -h -E "Number of cells|DFF" elab_old_1.log elab_new_1.log | head -n 8
