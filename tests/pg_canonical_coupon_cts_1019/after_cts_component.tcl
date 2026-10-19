# Loaded after all canonical fix hooks. Preserve their complete CTS/PG/RC work,
# then restore this diagnostic component's reviewed source-owned IO budgets.
rename clock_tree_synthesis coupon_original_cts_with_all_fixes
proc clock_tree_synthesis {args} {
 coupon_original_cts_with_all_fixes {*}$args
 source /src/tests/pg_canonical_coupon_1019/component_boundary.tcl
 puts "COUPON_SOURCE_BOUNDARY_AFTER_CANONICAL_CTS_HOOKS 100ps 80fF"
}
