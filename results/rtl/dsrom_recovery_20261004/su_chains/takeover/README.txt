SU takeover: source-bound component measurements, NOT an adoption or token-rate result.

The norm successor preserves Claude's engine, original bench and driver byte-for-byte.
tools/dsrom_su_fusion_join.py binds the saved baseline case hash, chain identities,
geometry, exactness, source hashes and comparison coverage. Its 17 norm chains reuse
the existing full-shape DPI and N64 RTL records; no golden inference/regeneration ran.
The head comparison ends at normalised output: no head quant baseline is invented.

The opt-in tb_dsrom_su_norm_transport.sv adds real 23-stage output payload/index/valid
register paths; REGISTER_OUTPUT defaults to zero. One cached L20.attn.hc_pre_norm
was measured at N1024/D5120, with the unchanged golden chunk8 reduction, FP32 rounding,
BF16 rounding and quantiser contract. Its 5120 elements and 160 quantiser blocks pass.
All five output-vector identities have exactly 23 cycles from raw to consumer event.
The bench clock is 1.2 GHz; this functional simulation is not clock sign-off.

Actual boundary attribution (elapsed cycles; sum once along the chain):
                            baseline 0.9GHz        candidate 1.2GHz
hc_pre                      188 = 0.208889 us      56 = 0.046667 us
norm.sumsq                   75 = 0.083333 us      72 = 0.060000 us
norm.rsqrt                  145 = 0.161111 us      90 = 0.075000 us
norm.scale                   57 = 0.063333 us      24 = 0.020000 us
quant + final transport     210 = 0.233333 us      36 = 0.030000 us
component total             675 = 0.750000 us     278 = 0.231667 us

Gain-load accepts occur at cycles 6..10, go at 16, first/last lane input at 50/54,
mix last at 72, sum root at 144, scalar input at 153, rstd at 234, broadcast at 243,
raw scale last at 258, raw quant last at 271, actual consumer quant last at 294.
First gain acceptance to final output is 288 cycles = 0.240000 us, including the
existing pre-go schedule. The five gain beats were not hidden or removed. These are
cached operand availability assumptions, not measured ROM-to-gain loading service.
CDC is outside this component and must be charged on graph edges once by Maxwell.

The output-stage cost was priced before the bench build (transport_prebuild.json).
Source-counted x/gain registers, memory ports, fanout and selectors are estimates.
Physical area/corridor fit are unknown. An always-accepting bench endpoint does not
qualify finite consumer credits, actual VM publication/leases or full-token latency.
No ADOPT lever was written; shared composition.json/uarch_model.py/timing authority
remain with Maxwell. Reduction, broadcast, block quantisation, KV adjacent rotation,
and final VM/consumer publication remain exposed dependencies. HC pre's two lane-local
mix edges bypass intermediate VM; no reduction or cross-lane edge is reassociated.

HC-post NG256's first AGI128 attempt failed in a global host OOM, killing Verilator
1265147 at 44442220 kB anonymous RSS. Preserve hcpost_ng256_failed.log/kernel.log;
this is a resource/tool failure, not numerical failure or SS/FF verdict. One unchanged
source recovery on EPYC2 reuses the original generated objects and cached cases.
Its source-counted costs and admission basis are in hcpost_recovery.json. NG256 stays
unknown until its actual terminal. No reduced cases or P&R jobs are duplicated.

Consumer: Maxwell, tools/dsrom_1m_allmeasured.py. Machine-readable per-node times and
boundary events: norm_join.json and transport_result.json. Original cached operand
manifest is independently read from the completed source run. Three rejection checks
each for baseline join and registered transport are retained; failures are not erased.

Existing SwiGLU terminals joined without rerun: W1024 DPI and W64 RTL cover the
eight representative routed/shared chains plus existing stress. All source hashes
and the 1e00804b case-set hash match. Routed3456 elements: baseline swiglu+quant
347 slow cycles=0.385556us, candidate178 fast cycles=0.148333us. Shared576 elements:
242 slow=0.268889us versus170 fast=0.141667us. The baseline swiglu instruction
already includes route weight as E2; a separate graph route_w must not be added a
second time to this same-chain comparison. Candidate clock/area/corridor remain
unqualified; these component times are not composed rate or adoption.

Selected HC-post M5A4 existing routed lane has SS setup -52.47ps / FF hold +5.70ps
at833ps/SS60/FF25: REJECT_SS, regardless of the pending numerical recovery. Its
measured standard-cell area is5435.51um2/lane; 1024-lane replication is5.56596224mm2
ESTIMATE excluding outside-lane hub storage2,168,064bits plus90validbits, routing
and slot fit. Existing M6A5 lane closes SS+0.56/FF+4.47ps, but is a separately
labelled source/latency configuration without selected full-shape exact evidence.
It is not a rescue or substitute for M5A4. No new parameter/P&R run is launched.

NG256 SAME-SOURCE EPYC2 recovery is terminal: all40cases (8representative+32stress),
819200actual checkedwords, zero mismatches/faults, every case99cycles (first79/last98).
Source64b85a818 was clean and byte-identical to the failed AGI snapshot; PID1799575
and frontend1805547 are gone. Binarybe13059d, compiled30m06.168s; retained objects
and original cases reused, no reduced reruns/new parameters/P&R. The unwrapped
nohup launcher retained no exit-code file; the complete numeric JSON and all40PASS
rows are the terminal evidence, not a fabricated shell RC. SelectedM5A4 remains
REJECT_SS. Last-write baseline256slowcycles (0.284444us) versus99fastcycles
(0.082500us at proposed1.2GHz) is a publication-component comparison only. The
original final reducer result is339slowcycles,83afterpublication: required result/
busy/lease waits must remain priced, alongside nextHCmix sumsq branch. No actual
operational1.2GHz/full-token/composed gain claim follows from this functional run.

Physical-owner handoff after terminal: NO component is admitted until Maxwell
verifies>=1%composed gain with priced area, actual slot and finite corridor/supply.
The smallest existing SwiGLU complete quant block is ot_dsrom_su_swiglu W32,
LM5/LA4/ROUTED1/NIN33/NOUT23 in rtl/hdc/v41x/ot_dsrom_su_swiglu.sv,32replicas for
W1024. Slot isUNASSIGNED. NORM has inline lane generates, no independently bindable
physical leaf; factoring the retained-x/gain lane group/reducer/scalar boundary
needs model pricing before any new RTL. Current S81 serial su_s/su_n do not grant
fast-domain slots or 96/128times-wider operand faces. No new hardening is launched.
