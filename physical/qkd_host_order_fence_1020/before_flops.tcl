# KV-HOST7: ORDER fence kits need the flop-first pin-hook wrapper so the band fence runs AFTER io_flop_at_pins (pin_hook_after_flops).
# ORFS here does not invoke POST_FLOORPLAN_TCL (Codex 05:10), so the n32a/b row hook never ran. No-op marker.
puts "ORDER_FENCE before-flops marker"
