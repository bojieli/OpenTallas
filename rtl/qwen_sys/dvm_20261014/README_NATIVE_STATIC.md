# Native static DVM entry points

The production die entry points are `qfd_xs_tap`, `qfd_xcol_e/w` and `qfd_xhead_e/w` in `ot_qfd_xslice_slots.sv`. Their tap and head instances explicitly select `STATIC_SCHEDULE=1` and `NATIVE_AFFINE=1` where applicable. The native `vm_nox_20261014/qfd_sp_vector_memory.sv` wrapper selects actual mapped SRAM macros by default and uses fixed service slots. Availability and faults do not postpone production execution.

The generic `ot_qwen_me_array_dvm_w12` composition and generic primitive defaults retain historical diagnostic profiles. They are arithmetic/timing test compositions, are not instantiated by the production die, and their default profile is not production qualification. Native generic-composition proofs must explicitly select `NATIVE_AFFINE=1` and `STATIC_SCHEDULE=1`. Historical dynamic profiles do not establish native production scheduling.

Published records under `results/rtl/qwen_vm_static_1014` and `results/rtl/qwen_dvm_native_affine_1014` pin the executed sources. They qualify the documented component boundaries only. Clock phases tied in functional simulation do not qualify physical phi-R delivery, die timing, whole-token execution, or throughput. The sequence-composition collective-return slots are external fixture inputs at the declared boundary.
