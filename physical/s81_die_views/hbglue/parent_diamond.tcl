# Use the closure kit's diamond legalizer for the compact explicit parent fence.
rename detailed_placement ot_head_native_detailed_placement
proc detailed_placement {args} {
  return [ot_head_native_detailed_placement -use_diamond_legalizer {*}$args]
}
