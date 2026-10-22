# OBS/OBSX source port onto main

Base: a744c0689. This port stages real HOST CSR readers behind explicit, default-off flags. It does not merge the GEN9 branch or replace existing main source files with GEN9 copies.

With OT_KV_HOST_OBS=0, the actual HOST binding JSON for both MU=0 and MU=1 is byte-identical to main. The original main admission-root source is byte-identical. The complete static-die generator AST is identical after removing the one guarded OBSX block. All MU-root, OBS and OBSX generation checks pass against these main sources. The new composed static-generator pin is in main_port/check.json; the GEN9 79939e3d pin is not reused.

OBS uses the real AXI4-Lite window for 43 HOST observations (1335 bits plus 71 sticky fault bits). OBSX adds three die buses, totaling 41 bits, for dcal admission/ready/running/layer and D2D recovery cycles. It requires MU, HOST_OBS, STATIC_DIE, DCAL_BC and DCAL_BC4. HOST_MU=0 preserves the existing root. No source is converted into a tie or removed from its existing internal consumer.

The generated MU source is a new dependency. Its coordinator needs only a default POST_UID_SLOT=0 parameter forwarded to the existing child parameter; old callers retain zero. Main's newer context MU_HEAD and guard FIFO source are preserved. main_port/manifest.json pins all 96 elaboration and bench sources.

Fleet Verilator 5.050: the complete OBSX root elaborates at ENABLE_SERVICE=1, ENABLE_NATIVE=1, ENABLE_TOKEN=1, NL=2 with no errors. The actual main-source OBS bench passes (44 words, 6 captures); mutants 1-4 fail. The OBSX path bench passes (46 words, 12 captures); mutants 1-6 fail, including the sticky-pulse check. Each negative has a committed fail witness and regex in the manifest. Initial missing-file staging failures remain in fleet scratch; lint3 is the complete successful closure.

Physical adoption is HOLD for both OBS and OBSX. The benches use one ideal common edge. Equal relay counts do not prove multi-bit coherence, pulse capture, or physical atomic sampling across regional clocks. Every HOST observation and OBSX source/relay/receiver path still needs actual clock ownership and phase bounds, stable sampling aperture or atomic landing semantics, native timing, and census. The CSR's capture copies need the same qualification. No gate, strict die release, or production adoption follows from this source port.
