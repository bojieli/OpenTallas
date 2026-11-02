# Finite root OBS144 → physical OBS136 specialization

`rtl/hbm_accel/die_glue/ot_hbm_obs_leaf_fc136.sv` is an additive, default-off
master for the actual SOURCE13 root `u_u_obs_C`: old N144/LID0/SYNC_MASK0/MUT0.
The original OBS module, its global N32 default, every existing caller and all
selectors remain unchanged. LID/SYNC_MASK are accepted only at0; other profiles
fail elaboration. The proposal requires the separately owned four HFstatic
carrier projections and is not applied to the source root by this packet.

The new master has136 physical observation inputs and its own136-wide p1/p2
capture banks. **Only after those captures** does it reconstruct the old144
logical positions. Five32-bit debug words, padded width160, q/r pipeline,
indices, live/sticky selection, clear precedence, passthrough data and the
actual reset relay are preserved. This is not the old N144 master with eight
constant input ties, nor a generic N136 master that renumbers debug bits.

The exact original root concatenation independently gives these eight holes:

| Old logical OBS bits | Original source | Removed packed source bits |
|---|---|---|
| 16,17 | L125m_i_q | 3,4 |
| 29,30 | L117_i_q | 3,4 |
| 42,43 | L118_i_q, observed as[10:1] | 4,5 |
| 55,56 | L117m_i_q | 3,4 |

Retained physical order is ascending old logical order. Each captured vector p
expands as `{p[135:49],2'b00,p[48:38],2'b00,p[37:27],2'b00,p[26:16],2'b00,p[15:0]}`.
No vc2, host or other possible constant input is removed or qualified.
`generated/root_obs_fc136_PROPOSAL.sv` changes only the root OBS call. Its four
carrier ranges match the owner's independent projection: L117/L117m[8:0],
L118[8:1], L125m[4:0]. L118 fault scalar[0] stays outside the projection and is
unchanged. That proposal must never be applied to the old-width carriers alone.

Inputs and manifests are actual selected SOURCE13 bytes exported read-only by
the HBM owner from its preprocessed source: root9059dc334..., OBSb65259f93...,
reset helperae627fdff.... `derive.py` checks all three full SHA256 values before
derivation. The selected reset helper is the actual two-sync/one-tree-stage
`ot_rst_relay`, not an older proof fixture. Line directives are removed only
from generated proof/source views; the immutable input files remain intact.

Intel1 job `oth-ubuntu-1610218-1793627079`,2GB/1thread, admitted after126 seconds
and completed exit0. There was only one proof request; no Intel2/P&R job.

- Unbounded temporal induction passed at induction length3. All DUT initial
  state is unconstrained; only proof-monitor state initializes. The comparison
  becomes qualified after four consecutive genuine reset edges, then covers
  arbitrary retained136-bit inputs, all query fields, and subsequent resets.
- The miter compares all q/r outputs and instrumented state, including captured
  logical vectors, sticky/clear banks, query pipeline and reset output. The
  observation ports exist only in proof views, not the production master.
- Native lockstep passed3356 checked cycles: every retained input at its old
  word index, all256 query bytes, live/sticky/clear, nonmatching LID, q bubbles,
  passthrough data and warm resets. It compares outputs each cycle, so no added
  response edge is hidden by transaction-only checking.
- A wrong **retained** bit mutant maps captured p1[1] into logical bit0. Formal
  finds a counterexample and actual lockstep reports an r_d difference at cycle11.
  The mutant does not merely change a removed/assumed-zero bit.

The theorem is conditional projection equivalence: the original144-bit input
has the eight holes fixed at zero and all other inputs remain arbitrary. This
packet **does not prove the producer fields constant**. The HBM/FLOW owners
separately own their finite native producer lemmas and HFfc9 carrier proof;
those results are not replaced or relabeled here. Other OBS inputs remain
unqualified, and this does not close all R2 obligations or qualify physical use.

Model consequences are exact at source level: eight fewer physical inputs,
p1 and p2 each144→136 (16 fewer declared capture bits), old logical words and
indices unchanged, and zero added q/r cycles. Selected SYNC_MASK0 can let the
optimizer remove unused p2 state in both designs; mapped FF/area savings are
therefore left unclaimed until the actual master build. No clock, reset stage,
fault-scalar path, public query ABI, programme date or global selector changes.

Reproduce in this directory with `bash run.sh` through normal fleet admission.
The only data premise is the explicit eight-zero projection; the proof never
zeros all DUT initial registers or assumes a query/sticky invariant. Generated
views and expected-failure controls are reviewable beside the compact receipts.
