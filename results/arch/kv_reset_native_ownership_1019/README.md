# GEN7 reset ownership and POR prerequisites

This is a read-only source/artifact audit, not a qualified reset schedule.
`prerequisites.json` pins the exact canonical bound netlist SHA
7006cbd0d11ffb755902c588eec474a1a7c27d7ad77212cebe3be1fcae5aae7e
and actual GEN7 relay table. `audit.py` derives every listed relay hop from
that netlist; it checks the SHA, unique reset drivers and acyclic paths.
No running case, reset source, counter, gate, health behavior or STATUS edge changes.

The central attention reset does not reset AHUB. Exact ownership is:

| Consumer | Reset producer | Root clock | Subsequent plain relay edges / clocks |
|---|---|---|---|
| ahub.rst_n | rly_rst_die_t8_42.b | n_clk_core_ES | 7 / n_clk_core_c |
| kvs_attn.rst_n | host.die_rst_n | n_clk_core_c via ck_rst | 11 / n_clk_core_c |
| seq__u_core.rst_n | host.die_rst_n | n_clk_core_c via ck_rst | 5 / n_clk_core_c |

AHUB root rly_rst_die_t8_42 is qkd_rst_region_pr. Its input has 47
ES-clock plain relay edges from host.die_rst_n, including five distribution
relays before the 42 named route stages. Its strapped dly is binary00100011
(35). The wrapper registers that strap before qkd_rst_region uses it; the
root's actual event equations and loaded phase still need a receipt. Its
output crosses into central-clock reset relays. Nominal equal frequency
is not a measured setup/hold or root-skew bound.

The canonical host is qkd_host_root_admission, with ck_rst central. The
predecessor raw-source reset-load manifest calls that host qkd_host_rt.
Its 18 proposed fault roots remain useful geometric provenance, but that
raw master name is not the canonical native host identity. All 42 actual
regional reset roots and their input chains are retained in the JSON.
The longest such input chain has82 plain edges. Different root-relative
registered depths cannot be treated as one release epoch.

Actual source at4db097403 gives AHUB two reset hierarchy levels. The
outer qkd_ahub_static_dw uses ot_rst_pipe REGIONS7/STAGES2. Its port
asynchronously clears only two synchronizer flops; plain regional flops
propagate assertion after two running edges and release after four.
u_rw.fault drives hf and is forced low while outer rr[0] is low. The
hub u_core has another ot_rst_pipe REGIONS4/STAGES2, whose rn[3] clears
its sticky fault. Thus the internal sticky source is two additional
running edges behind its outer reset port. ZH/reciprocal leaves and
unreset return pipelines are additional initialization obligations.
One cannot substitute immediate attention-local clear for any of these.
The source snapshots are preserved compressed with hashes in the JSON.

After the last possible AHUB hf high, the canonical transport table
requires34 plain edges before attention.ufh and37 before seq.hf see
low. These are transport ages; electrical crossing margins and loaded
clock phases remain open. A complete clear proof must establish the
last high after all local/child reset and stale return drains, hold the
final downstream sticky reset across that flush, and prove release
cannot resurrect a stale fault. No reset-at-functional-cutoff masking
is allowed; continuous health remains live.

The predecessor's final proposed fault sticky depth273 and skew64 are
conditional model values. There is no installed candidate clock/reset
tree, loaded reset STA, or exact cross-root assertion-skew receipt.
Consequently this audit leaves skew null, not64, and produces no numeric
host admission or STATUS schedule. Historical AHUB a7 already fails
native boundary clocks and the current source-specific successor is
still open; a positive data/setup result would not fill that gap.

A fixed schedule needs these source-bound times in one proven epoch:

1. Each root's POR assertion/release, host reset pulse arrival and local
   tree assertion/release, including all new branch and native phases.
2. Each real sticky/pulse source's last stale high after its own actual
   reset and every unreset feedback/return pipeline drain.
3. For every fault path i→j, last_high(i)+transport(i,j) precedes the
   chosen final sticky clear/release ordering, with measured margins.
4. Admission follows every required branch release/initialization and
   the above clear proof. The host calendar must price the resulting
   fixed guard; no conditional wait or new health mask.
5. STATUS follows the compiler-proven functional operation cutoff and
   the full join/UFH/AFR/TX/link/landing/consumer path with native phase.
   Later continuous faults retain the owner's conservative invalidation
   behavior. A standalone graph model does not establish that calendar.

Counter representability is a separate source obligation:

- qkd_rst_region ign is9 bits (max511), while dly and cnt are8 (max255).
- hold is8 bits, loaded using HOLD[7:0]-8'd1. Raising HOLD above256
  wraps; HOLD273 would load16, not272. A273-cycle hold requires at
  least9 state bits and corresponding arithmetic/source/bench proof.
- IGNORE gates the upstream input-chain flush at the regional root.
  The observed max82 input hops already fit255. New local depth273
  exceeding255 does not by itself imply IGNORE must become273: local
  POR flush, downstream clear and admission must be priced separately.
- If a final fixed guard G exceeds the existing counter range, its
  counter needs ceil(log2(G+1)) bits, with terminal-count convention
  checked against RTL. No larger counter or new guard is adopted here.

Audit invocation (metadata only, run locally):

    python3 audit.py --artifact-dir /home/ubuntu/artifacts/kv-reset-native-ownership-1019 --tools /home/ubuntu/wt/codex-kv-reset-native-ownership-1019/tools --table /home/ubuntu/artifacts/codex-kv-gen7/kv_table.gen7.json --out prerequisites.json

All own jobs are terminal. No physical gate, REVIEW or submit was launched.
