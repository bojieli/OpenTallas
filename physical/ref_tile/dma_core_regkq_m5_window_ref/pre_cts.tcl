# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); cluster: balanced clock spine with child-insertion leaf targets (sourced FIRST, so the io_ref wrapper below wraps it)
source /src/physical/common_flow/clock_spine.tcl
source /src/physical/ref_tile/dma_core_regkq_m5_window_ref/spine_ins.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/p
  source /src/h
  source /src/y
  source /src/s
  source /src/i
  source /src/c
  source /src/a
  source /src/l
  source /src//
  source /src/q
  source /src/w
  source /src/e
  source /src/n
  source /src/_
  source /src/d
  source /src/i
  source /src/e
  source /src/_
  source /src/m
  source /src/a
  source /src/s
  source /src/t
  source /src/e
  source /src/r
  source /src/s
  source /src//
  source /src/s
  source /src/r
  source /src/a
  source /src/m
  source /src/_
  source /src/e
  source /src/d
  source /src/g
  source /src/e
  source /src/_
  source /src/g
  source /src/u
  source /src/a
  source /src/r
  source /src/d
  source /src/.
  source /src/t
  source /src/c
  source /src/l
}
