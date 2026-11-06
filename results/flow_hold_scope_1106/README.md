# FF hold-repair scope, private measured prototype

`OT_HOLD_REPAIR_SCOPE=reg2reg` is opt-in and applies only to a synchronized two-mode GRT hold repair. It temporarily excludes data input/output port hold from optimization, keeps internal paths active, then restores the complete original FF SDC with 17-digit round-trip precision in `finally`. TT setup is untouched. Current mode and original repair errors propagate. No sign-off threshold or final constraint changes; port debt remains visible and may still fail final qualification.

Qout vehicle: immutable copy of epyc5 `hbm-gaps-5-fix/ot_q2nf_qout_vA/4_cts.odb`, actual 109802-cell netlist. Private test on epyc2 `codex-hbm-holdscope-1105` used **placement RC**, TT RVT libraries in scene `tc`, FF RVT in scene `BC`; the inherited OpenSTA mode name `ss` means the TT setup shadow, not an SS corner. No SS library loaded.

Baseline FF: -213.449219 ps / 5863 endpoints; internal -11.961848 / 814. Scoped native repair inserted 814 buffers and reached internal 0 violations in 42 s (100 s including save/restore/statistics). Restored full FF: -213.449219 / 5049 parent IO endpoints; internal 0. This is optimization evidence, not a routed sign-off result. Original live job was untouched.

17-digit FF SDC before/after SHA256 both `fa3bdda9061de78b4095d821513031b1792f9e4c91bb4699a22892387a64388f`; TT SDC before/after both `bad19cc58ac22f221c7505cb8859ea886f622ac772b67d351fee9255cc8f5136`. Full snapshots retained on epyc2 under `codex-hbm-holdscope-1105/probe17/`; the first prototype with default four-digit serialization is retained separately and is superseded by this precision-safe result.

`run_test.sh REPO OUT` runs the actual shared helper in OpenROAD against two real ASAP7 flops with mixed original false paths, multicycle, max/min delay and path margin. It checks: IO paths excluded only during the body; internal path still present; exact original TT/FF SDC and numerical FF slack restored even on deliberate repair error; mode and error preserved; default bypass unchanged. Successful output ends `FLOW_SCOPE_PASS ...`.

Production helper keeps default all-path behavior unless explicitly enabled. Successful temporary SDC snapshots are removed to avoid storage growth; `OT_HOLD_SCOPE_KEEP_SDC=1` retains them for a requested diagnostic. A restoration mismatch retains both snapshots and aborts that repair session, never emits a qualified masked result.
