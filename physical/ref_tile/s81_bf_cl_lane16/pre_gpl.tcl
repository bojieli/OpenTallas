# ref_tile PRE_GLOBAL_PLACE (pin flops, no hold stages): the spec's pin_hook_before_flops repo hooks, then
# every port's single launch / capture flop is fixed at its pin.  ORFS takes one hook per step.
source /src/physical/ref_tile_specs/s81_bf_native_1015/cl_lane16/group_bands.tcl
source /src/physical/qwen_die_masters/io_flop_at_pins.tcl
