# Current native GAIN → NORMR command boundary

Current flattened s_0S_L0 source, same POST/gain/norm fixture and833ps component clocks. Actual GAIN480 at registered CV1567 then NORMR1576 (spacing9) passes all25 POST rowpairs,64 BF16 values and532 Q bits in HEAD-only and both-family modes, partial3f102d76, all VP/VNa/VNb/VS/VQ/cland faults0 and ready1. Eight driver gain writes end atGAIN+12. Spacings10,11,13 also pass.

The same compiled binary in a fresh control directory demonstrates spacing8 → VP scheduling fault1 despite eight gain writes and spacing7 → VP fault1/seven gain writes/numeric failures. Wrong released gain at safe spacing9 changes three numeric checks while all DUT faults remain0. These controls establish the actual local sequencer boundary and active operand dependency. Positive/control binaries are byte-identical.

The prior component used spacing81, so72 local idle edges are removable. This is not a measured global programme price. Inputs are the qualified local fixture, not real final-layer POST authority. The driver gain-write event is measured; internal VN gain-RF residency is not independently observed. The safe overlap is valid for this exact source/profile and must compose with per-leaf input/gain/tag leases and real issuer dates before programme adoption. No RTL, parameter, plan or source-default change.

Immutable evidence Intel1 codex-ds-norm-1101/native_gain_spacing_v1 unit1132167-1793574652 completed0 and native_gain_boundary_v1 unit1431086-1793575492 completed0. The latter's three DUT exits1 are required controls, retained here. No advancing jobs remain from these probes.
