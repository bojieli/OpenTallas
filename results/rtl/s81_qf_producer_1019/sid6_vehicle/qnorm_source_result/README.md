# Genuine raw-qnorm source component: bounded PASS

The actual historical XR→DL4→VP→VS QB9→VQ(AQ_XMEM2)→DL4up→RSTOP own-fragment
assembly→XS gather path consumes1280 original FP32 q_norm.scale values written
through320 real target5 commands. Twenty real QB8 commands cause the existing
quantizer to produce20 XQ beats. All1280 produced FP8 codes and40 scales match
independent golden models. All20 real gather dates are384+46b relative to the
first XR CTL pin sample; last1258.320 actual source SRAM write cycles and the
XS20-entry valid table plus actual source0 delivery are checked. No source fault is present.

Original job3714497 retained its numeric FAIL. Its scoreboard serializer used
bytes(int64_codes), producing8 bytes/code. Authoritative vs_gold uses an
explicit uint8 cast. Corrected model job3717067 enforces32 bytes/block and532
bits/packed beat. Source control, fixture, RTL and executable are unchanged;
scorefix job3718406 reuses the useful executable with exact hash receipt.
Correct-scoreboard baseline passes; corruption of a real raw input exponent
bit, a missing real SRAM row write and a foreign CTL slice destination each
causally fail. No final-Q or return payload is a stimulus, and expected
quantized words occur only in the scoreboard file.

The exact51-file historical source bundle is699572 bytes, ref ceaed19c4,
SHA-checked before compilation. Verilator5.050 produced164 modules/118 reported
C++ files,131MB generated source; build62.964s, reported allocation2314MB.
Admission was16GB/four threads, unpinned ot-epyc4; successful runtime0.257s/19MB.
Useful object directory quant_component_03/obj remains immutable. No full
six-frame/CAP vehicle was built. Initial setup attempts01/02 are retained
(serializer setup and nonconstant TB-only MUT parameter, before simulation).

Scope limits remain explicit. This proves genuine raw-input quantization and
gather delivery, not the upstream normalization producer. Physical native
phase/regional reset dates remain NULL. Last XS macro commit1260 is currently
a structural+valid-join date; actual macro write/read timestamp instrumentation
and all15 epoch retention/reload conditions remain to be checked. Scratch
608..927 occupies40960 existing bits and overlaps future SW600+ usage; whole
programme/MU/replay ownership is unproved. No production imagewriter/default,
GEN, physical view, QR/gather or token qualification changes. Original token
deadline remains unchanged, with no PASS inferred from this component.
