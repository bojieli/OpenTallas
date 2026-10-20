# LH-RSTHOP (HBM d4g H.RST structural fallback, 10-19)

Problem: GEN2c case_a places 56.6k lane relay tiles in every channel; the reset forest's separate 32.4 um hbfd_rrl_hop
tiles find no legal home within the 405 um reach (forest_codex9d5a2c350 'no regional root home'; ofly 'no legal reset
relay within routed reach'). Diag: with relays blocking homes, 253 of 2,292 405-um bins with routable area have ZERO
legal hop homes.

Fix (coordinator 0jp A form: the relay rows carry the reset): `reset_forest_layer.py --host-hops prefer|fallback`
hosts a forest reach hop inside a placed lane relay station of the same clock domain. The station is remastered to
`hbfd_rly_<W>_<flow>_rf` (base) / `_rrf` (row-reset _rr driver) = unchanged station + one rfi->rfo flop
(rtl/hbm_accel/die_glue/ot_hbm_rly_rf.sv, hbfd_rrl_hop semantics: async assert, release 1 edge). Hosted edges keep the
conservative hop budget (reach - 2 radii - 2 GRID) on assumed i/o-face-middle pins. Splice: `added_inputs: [rfi]`
must be driven; die_case reset gate checks rfo (and _rrf rso) edges like forest drivers.

Bench: tb_rf_hop.sv (iverilog, ot-run) PASS one edge per hosted hop; mutant OT_HBM_RLY_RF_MUT_COMB fails
(fail_witness_mut_comb.log).

SAFE-DESIGN checklist for the _rf/_rrf masters (new tile variants of closed hbfd_rly kits):
1 pins: station pins unchanged (registered stage); rfi/rfo are a registered reset hop (rfo is a flop output) PASS
2 reach: every hosted edge <= hop budget (~320 um) on assumed pins, <= 405 with real pin offsets PASS (die gate re-checks)
3 fanout: rfo drives one forest stage or one leaf input PASS
4 depth: rfi -> async clear, flop -> rfo; no combinational in->out PASS
5 storage: one flop PASS
6 floorplan: same outline as the base kit (outline override in the post-chain) PASS; kit pins rfi on i face, rfo on o face (TODO kit)
7 clock: station's own regional clock, same domain enforced by the planner PASS
8 schedule: release ages counted by the planner (1 edge per hop, equal-age leaves) PASS
Kits: _rf/_rrf routed kits not built yet (die chain uses SYNTH views with the base outline); follow-up after the forest passes.
