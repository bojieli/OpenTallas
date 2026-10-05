# Written by tools/qwen_o4_floorplan.py: VM 8-skew-bank cut: physical/qwen_o4_w5/vm_skew_proposal.json coordinates (Codex proposal, unchanged)
set ot_block [ord::get_db_block]
set ot_lut [dict create]
foreach ot_inst [$ot_block getInsts] {
  if {[[$ot_inst getMaster] isBlock]} {
    dict set ot_lut [string map {"\\" ""} [$ot_inst getName]] [$ot_inst getName]
  }
}
proc ot_place {name x y orient} {
  global ot_lut
  if {![dict exists $ot_lut $name]} { error "ot_place: no macro instance $name" }
  place_macro -macro_name [dict get $ot_lut $name] -location [list $x $y] -orientation $orient
}

ot_place {u_vm.banks[0].slices[0].u_mem} 63.936 64.8 R0
ot_place {u_vm.banks[0].slices[1].u_mem} 63.936 112.32 R0
ot_place {u_vm.banks[0].slices[2].u_mem} 63.936 159.84 R0
ot_place {u_vm.banks[0].slices[3].u_mem} 63.936 207.36 R0
ot_place {u_vm.banks[1].slices[0].u_mem} 343.872 64.8 R0
ot_place {u_vm.banks[1].slices[1].u_mem} 343.872 112.32 R0
ot_place {u_vm.banks[1].slices[2].u_mem} 343.872 159.84 R0
ot_place {u_vm.banks[1].slices[3].u_mem} 343.872 207.36 R0
ot_place {u_vm.banks[2].slices[0].u_mem} 623.808 64.8 R0
ot_place {u_vm.banks[2].slices[1].u_mem} 623.808 112.32 R0
ot_place {u_vm.banks[2].slices[2].u_mem} 623.808 159.84 R0
ot_place {u_vm.banks[2].slices[3].u_mem} 623.808 207.36 R0
ot_place {u_vm.banks[3].slices[0].u_mem} 904.176 64.8 R0
ot_place {u_vm.banks[3].slices[1].u_mem} 904.176 112.32 R0
ot_place {u_vm.banks[3].slices[2].u_mem} 904.176 159.84 R0
ot_place {u_vm.banks[3].slices[3].u_mem} 904.176 207.36 R0
ot_place {u_vm.banks[4].slices[0].u_mem} 63.936 343.44 R0
ot_place {u_vm.banks[4].slices[1].u_mem} 63.936 390.96 R0
ot_place {u_vm.banks[4].slices[2].u_mem} 63.936 440.64 R0
ot_place {u_vm.banks[4].slices[3].u_mem} 63.936 488.16 R0
ot_place {u_vm.banks[5].slices[0].u_mem} 343.872 343.44 R0
ot_place {u_vm.banks[5].slices[1].u_mem} 343.872 390.96 R0
ot_place {u_vm.banks[5].slices[2].u_mem} 343.872 440.64 R0
ot_place {u_vm.banks[5].slices[3].u_mem} 343.872 488.16 R0
ot_place {u_vm.banks[6].slices[0].u_mem} 623.808 343.44 R0
ot_place {u_vm.banks[6].slices[1].u_mem} 623.808 390.96 R0
ot_place {u_vm.banks[6].slices[2].u_mem} 623.808 440.64 R0
ot_place {u_vm.banks[6].slices[3].u_mem} 623.808 488.16 R0
ot_place {u_vm.banks[7].slices[0].u_mem} 904.176 343.44 R0
ot_place {u_vm.banks[7].slices[1].u_mem} 904.176 390.96 R0
ot_place {u_vm.banks[7].slices[2].u_mem} 904.176 440.64 R0
ot_place {u_vm.banks[7].slices[3].u_mem} 904.176 488.16 R0
puts "ot_place: 32 macros placed"
