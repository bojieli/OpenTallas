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
