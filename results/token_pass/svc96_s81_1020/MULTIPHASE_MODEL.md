# Opt-in B fallback: two four-row a_proj phases on 96 frames

This packet preserves the original 96-frame refusal. It separately tests an
unadopted compiler model; it does not waive the one-phase assertion or produce
a deployable programme.

`multiphase_model.py` invokes the actual `lower_xs.frame_programme` allocator,
with the existing four-row shape and 4,000 legaliser iterations, on all 112
chunks of the real L0 rank-0 fixture. Fleet unit
`oth-ubuntu-2548867-1792560072` returned exit 0: 448 rows covered exactly once,
112 real chunks, no return-plan faults. Maximum combined a_proj-only ROM fill
is 64 words per pair. This is an allocator/lowering result; it is not an RTL
measurement of the new two-phase sequence or a complete stage image.

The executable ownership model uses 80 wq_a frames and 16 wkv frames. Phase zero
places ranks 0–383 on all 96 frames; phase one places ranks 384–447 on those same
final 16 wkv frames. Each chunk has four rows and each frame handles one tensor.
The second phase involves slices u_s_6N, u_s_7S and u_s_7N. Every participating
slice has a contiguous rank range within each phase, so its prospective CAP
descriptor names actual produced rows. No sparse mask is needed. Descriptor
records are in `multiphase_model.json`; none is admitted to a current CAP.

The measured FSMALL work span is 361 cycles per phase. A conservative serial
schedule starts the new configuration one cycle after retirement and allows
the existing 52-edge CFG_LEAD: extra phase cost **414 cycles per occurrence**.
Across all 40 layers this adds **16,560 AR cycles**; six complete verification
positions contain 99,360 additional work cycles before pipeline overlap. The
current component composer gives 19,872 additional MTP critical-path cycles.
The physical stage reservation/wave model must be recomputed separately.

`price_multiphase.py` prices every a_proj occurrence, including contexts the
FSMALL by_old mapping leaves unchanged. It also prices G8/G4 service pass
deltas on every score/PV node. These are component sensitivities on the current
composer; they exclude the new stage count, expert topology and MU calendars.

| Scenario | AR tok/s | MTP tok/s |
|---|---:|---:|
| Current component composer | 834.0 | 2,649.1 |
| G8 + conservative second phase | 817.3 | 2,611.6 |
| G4 + conservative second phase | 803.3 | 2,592.1 |

Full-stage admission remains open. Actual tiny expert probes on this 96-frame
topology cost **112 words/expert on the worst pair and 9 cfg phases/expert**,
versus 72 words and 6 phases on the split112 A candidate. Isolated a_proj ROM
fit therefore does not establish an attractive full-stage chain.

The production implementation still needs these concrete changes and proofs:

1. Emit both a_proj phases in the complete dense/expert field, with stable
   global phase indices and valid idle-frame behaviour for the other 80 frames.
   Repack actual element/config/phase/stream images and check all memory depths.
2. Generalise `field.aproj_rank_rows` and the cfg image writer's `p == 0` rank
   remapping to a map for each a_proj phase. Preserve golden tensor row indices.
3. Give each phase its actual CAP descriptors, GO epoch and FIN lifetime;
   retire phase zero before descriptor/epoch reuse. Prove simultaneous frame
   traffic, physical arrival ages and all 448 capture writes with mutants.
4. Gather both captured ranges into the existing consumer order and price the
   last source-to-CAP-to-consumer age, not just the isolated frame work span.
5. Measure the smallest two-phase frame/CAP vehicle using the actual source,
   then recompile exact full-stage maps and both AR/MTP static MU calendars.

No new arithmetic datapath is proposed: each chunk retains the measured shape.
Sequencing, empty-frame behaviour, CAP/FIN and consumer transport remain real
RTL/protocol obligations. The 414-cycle model does not include unresolved new
physical landing or CAP retirement delays. A preserves the existing one-phase
contract and is the preferred qualification path while its geometry is viable.
