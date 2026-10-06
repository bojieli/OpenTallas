# Sign-off form of io_ref_skew.sdc for the docker STA (no environment): every core port is intra-region (core clock region:
# ME spine, vector stream, memory port registers), OT_IO_SKEW 90 ps (65 measured region pair skew + 25), hold allowance 50.
set ::env(OT_IO_SKEW) 90
set ::env(OT_IO_HOLD_SKEW) 50
source /src/physical/qwen_core_ctx/io_ref_skew.sdc
