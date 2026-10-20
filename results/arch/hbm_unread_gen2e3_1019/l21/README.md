# GEN2e3 residual 878 unread bits -> hardware (l21, L2H-PAD, 10-19)

Input: GEN2e3 S1 die (pre_relay of branch claude/hd4g-gen2e3-1019 @9787e078a), strict replay with admitted manifest
e08e4c2f... left **878 unread bits / 361 nets / 171 classes** (`residual_bits.json`, bit-exact from die_port_bind).
No waiver; every bit is fixed in RTL (`tools/hbm_die_v16/d4g_layers/l21_obs_readback.py`, report `l21_report.json`):

- **876 observation-export bits are READ** by a host observation readback ring: 5 `ot_hbm_obs_leaf`
  (obs_C 95 b, obs_SW 208, obs_SE 182, obs_NE 182, obs_NW 209; LID 0..4 = ring position) and the host ingress becomes
  `ot_hbm_host_static_ingress_obs`: AXI-lite reads 0x000-0x3FF return obs words (idx = araddr[9:2] = {lid, page, word};
  page 0 live sample, page 1 sticky read-to-clear so 1-cycle done/fault pulses are never missed). Ring
  host_cp_ingress -> obs_C -> obs_SW -> obs_SE -> obs_NE -> obs_NW -> host_cp_ingress, {v, idx, d} packet, one read in
  flight; all other ingress behaviour unchanged (0xf30 status, writes, faults; other reads still ffffffff).
  Serial-domain sources (pgp_* SU programme slices, 70 b) take the leaf synchroniser flop (SYNC_MASK), as the fault leaves.
- **2 dead bits removed**: hb_ckgen pll_link / por_link (no link-domain consumer on this die) -> `hfd_ckgen_nolink`.

Results (die = GEN2e3 S1 + l21, contract sha in `contract_die_sha256.txt`, gz copy `pre_relay_l21.json.gz`):
- default strict bind: structural 0, unread 65,066 (= the reviewed manifest exactly) (`default_bind.log`);
- review transfer `unread_l21_transfer.py` (309 entries, 0 re-pointed, die_line recomputed) -> proposal
  **056f138ddbe6ff0f7c47f6292e638525ff6295f9df1c4c2e736e9c9a31b243cd** (`manifest_proposal_l21.json`);
- replay with it: **DIE_PORT_BIND PASS, unread_net_bits=0** (`strict_replay.log`); functional bind PASS (LAT warn as S1);
  CMC unchanged (2 pre-existing sfu_core_split3 hard-view markers).
- bench `tools/hbm_die_v16/obs_ring_bench.sh` (Verilator 5.050, fleet ot-epyc6): PASS 7,547 reads
  (`evidence/pass_obs_ring_m0.log`); leaf mutants LMUT 1 (no clear) / 2 (top bit dropped) / 3 (page swap) FAIL
  (`evidence/fail_witness_obs_lmut{1,2,3}.log`).

SAFE-DESIGN (leaf): 1 pins registered in+out, reset 2+1 ot_rst_relay landing PASS; 2 reach: hops get S4 relay stations
(reach 405) PASS; 3 fanout: one-hot selects replicated per page/clear (32 loads each, keep) PASS; 4 depth: <=32-term OR
(5 levels) per stage PASS; 5 storage: <=1,024 parallel-sampled flops/leaf (not runtime-indexed storage) PASS;
6 floorplan: soft die glue, GEN homes; 7 clock: stream domain, serial inputs synchronised; 8 schedule: no datapath cycle
changes, nothing gates execution (cycles_changed 0) PASS.
New masters needing synthesis in the next GEN pass: ot_hbm_obs_leaf (5 param sets), ot_hbm_host_static_ingress_obs,
hfd_ckgen_nolink. Host ABI change: reads 0x000-0x3FF now return observation words.

## Next GEN pass (GEN2e4)
After l20s in S1: `python3 $L/l21_obs_readback.py $A/net/c_l20s.json $A/net/pre_relay.json --report $A/net/l21.json`
(l20s writes c_l20s.json instead of pre_relay.json), then
`bash tools/hbm_die_v16/d4g_layers/l21_strict_replay.sh $A/net/pre_relay.json $A/pb0s results/arch/hbm_unread_gen2e3_1019/l21/review_l21_candidate.json results/arch/hbm_unread_gen2e3_1019/l21/manifest_proposal_l21.json 056f138d...`
-> strict PASS expected when the S1 contract is byte-identical (sha in contract_die_sha256.txt). The manifest is
die-identity pinned: later stages (post-landing / forest / l12) need the same transfer -> propose -> replay step.
Admission of digest 056f138d: LEAD2-HBM (exact transfer of admitted e08e4c2f; no new permission).
