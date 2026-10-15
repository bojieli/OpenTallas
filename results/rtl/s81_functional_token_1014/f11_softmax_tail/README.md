F11 softmax partial-vector implementation
=========================================
Compiler lowering now emits ceil(T/16) score vectors, pads inactive slots with
-Inf, and emits expected +0 probabilities for padding. The real flat and physical
hierarchical softmax lane paths retain the sentinel around the finite-domain
multiplier and mask exp output to +0 on the unchanged fixed pipeline timeline.
Exp's lower clamp would otherwise produce a nonzero padding probability. No
credit, ready, or issue feedback was added.

Actual synthesizable ot_s81_su_sml, real RTL floating-point primitives (no DPI),
replayed all 16 lane positions of a 133-position head at adjacent-vector rate:
144/144 outputs exact. Source-removed exp-mask mutant fails 11 padded positions.
Run/result are source-pinned in result.json. This proves the modified physical
lane, not continuous native token execution, SRAM connectivity, or timing closure.
The existing CLOSED sml views must be replaced with rtl_change successors.

su_service_bridge.py prepares standalone SE/SO jobs from actual service capture
and extracts actual SU VM output. Snapshot supplies constants only. The bridge
labels staged replay and host P-file conversion explicitly; actual native
FP32-to-BF16 P converter belongs to the SVC integration owner. CN/IK/CP and die
integration remain open.
