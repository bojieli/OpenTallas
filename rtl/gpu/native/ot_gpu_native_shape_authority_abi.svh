// Source-only shape join ABI, no numeric opcode changes.
`ifndef OT_GPU_NATIVE_SHAPE_AUTHORITY_ABI
`define OT_GPU_NATIVE_SHAPE_AUTHORITY_ABI
`define OT_NATIVE_SHAPE_DESCRIPTORS 116
`define OT_NATIVE_SHAPE_PROFILE_ROWS 10950
`define OT_NATIVE_SHAPE_BASE_ROWS 29696
`define OT_NATIVE_SHAPE_PROFILE_BITS 329
`define OT_NATIVE_SHAPE_BASE_BITS 17
`define OT_NATIVE_SHAPE_FACTORY_SERVICES 1
// I8: carrier type3 + independentlycaptured signed_i8 mask1. Never U8 alias.
`endif
