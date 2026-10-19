# GEN2e3 unread re-manifest (L2H-GEN2E, 10-19)

Die: GEN2e3 S1 strict die (`artifacts/hdie-d4/d4g_gen2e3/pb0/die.v` sha 1c169d9c..., contract pre_relay 71b97514...,
source 5b5d01284).  Default strict bind: structural 0, unread **65,944** (GEN2e2 70,320 minus 4,376 removed as hardware).
`tools/hbm_die_v16/unread_gen2e3_transfer.py`: exact fail-closed transfer of the GEN2e2 candidate (309 entries / 65,066 b,
itself the exact transfer of ROOT manifest 2beccb8e); 9 entries re-pointed (col_idx.rec -> idx256r; epcal/vmfc.ordinal ->
calendar_f20_role; same port/width/driver), die_line recomputed, four fixed held classes removed.
Review candidate sha 071a4cd8... -> proposal `manifest_proposal_gen2e3.json` sha
**e08e4c2f3027014c09e566be2f642b3e7dc9547b964e8dd24fa61fba6e7499fa** (die_port_bind --unread-proposal-out).
Replay with that digest: unread **878** (171 classes, `residual_878_classes.json`) -> strict FAIL kept (no waiver).
Residual = fault_cause / stat_cycles / bank_client / edge_index / block_ready / wq_done observation exports (codex
follow-up packets 9e7aa7207 cover 860 of them semantically, not reviewed) -> next: route them into the host status
collector or remove them in RTL, as for l20c/p/t/s.
CANDIDATE digest: admission by LEAD2-HBM (D1: Codex ROOT gating ended); not used to pass any gate here.
