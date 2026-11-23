# FABLE-UNC-S81-SVC handoff (Fable; agent ad36422a39196fd09; started 11-23 ~01:45 PST)
Brief: localhost scratchpad fable_uncovered_brief.txt + rules.txt. Die S81, event J9 cut 18:00.
Deadlines (ASSEMBLY manifest): Wave A rows GATED 10:00-10:30; Wave B hard stop 12:30. Open items -> COORD 16:00.
Role (agreed with FIX-LEDGER 01:5x): independent cause reviewer + gap-filler for rc14-26 + x1 (SVC-HI4-SPLIT-F65F). Build a row only where no live builder.
Builders: SVC-R9 acbf5f53765607888 (rc14/20/19 ATT-ENG-ORDER, rc15 CUT-STATION, rc18 taps, rc22/23/26 probes, x1);
 FIX-S81-SVC-BCAST a8c9603916048346b (rc16); FIX-S81-SVC-LOSTART aa73a799dcaa5cd85 (rc25); FIX-S81-SVC-WESTRIP a3b5045d81be1bf87 (rc17/21/24).
Others: VIS-DIE-S81 a5cb7d854ffa9743b; ASSEMBLY adfaf0f3fdaedfc9f; FIX-LEDGER acd269758d3b62a53.
## Log
- 01:50 resumed after API 529 (nothing of mine existed on hub before). ACK sent to FIX-LEDGER.
- 02:0x SVC-R9 handed me rc14/15/19/20 to BUILD (it does x1 split rebase onto f65f; rebase bind launch ~04:30 on epyc7/8). FIX-LEDGER also gave me [hop-S81-svc]; FABLE-UNC-S81-DIE (aa0cf9d7ecf0a898a) gave me svc rc67 hop classes.
- CAUSE rc14/20 (traced in bound RTL out_r9 t4_att_part.sv): tile t = g_tr[t].eib(576b) -> 8 hcores .ib; hcores h[4j..4j+3] oy/oflt -> g_m[t].h4[j]; stage0/1 SRAM rd_data (1060b) -> all 4 tr. Generator packed macros by class in index order -> tr/h4 1.4-1.9 mm from tiles. Pins: hcore ib N, ld_* W, oy E; h4 iy W, oy E; tr w_g/qk_ib W, eib/col E.
- adv_hop_gap.py (rt/current tools/die_plan) does NOT resolve bit slices through concat assigns -> hcore->h4 over-counted ~8x. TODO patch (lane clone, push main).
- TOOL intel2 /srv/opentallas-scratch2/claude/fable-unc-s81-svc/att_order_row.py (local copy scratchpad unc_s81svc/). v1 992ab7fd26aa: t4_att + t5_att; ops atto_v1_ops.json 6ce5a039b98c; plan_r9h_atto_v1.json b70b2f541716. Sent to SVC-R9 03:5x for its rebase bind. PRE on r9h: pre_gate.sh via ot-run intel2 WAITING on disk floor (142<150 GB), log pre_t4.otrun.log (that run is the older t4-only plan, file since removed -> rerun on v1 plan when disk frees).
- NEXT: layouts t2_att, pvso t2, hi rs t1/t3/t6, pvso t1, lo x8 (LAYOUT dict); rc15 CUT-STATION analysis (Y_p endpoints); rc19 straps; SVC-SMS-ORDER (new class, sms/smh soft leaves <-> u_smd/u_smr/u_sml); hop tool slice patch; probe t4_att via SVC-R9 hi4 kit.
- Deadlines: Wave A 10:00-10:30, Wave B 12:30. Later types ride R5 composed gate as TOOL run after SPLIT-F65F, before YTRADE/ES1.
