# KV/HR parked on explicit Claude reset

No new jobs, merges or design changes after reset. No owned `codex-kvhr1030` containers remain on intel1/intel2; nothing was killed. Source/result branch is `codex/kv-hr-1030`, own worktree `/srv/opentallas-scratch/claude/wt/codex-kv-hr-1030`. Prior READY commits: `18f351724` RX candidate; `fd9e7ae2c` CDC placement; `8986e9b7e` RX placement; `8f685be49` pad diagnosis; `17f33dfe0` ownership reach; `182ae8e38` die_id source correction; `12c399275` proofs/initial failures; `f68332d96` zero-cycle M1 source; `60af377dc` rb_cap binding; `edf557c01` repair measurements; `38ecb0a19` native TAP-safe homes; `ab873a971` physical SRAM PG fix. No main merge or canonical pin adoption.

## PHY103: keep this exact clock tree

Own intel1 root: `/srv/opentallas-scratch2/claude/codex-kv-hr-1030/phy103_zero_cts1`.
Original one normal CTS checkpoint: `run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/4_cts.odb` and `.sdc`. ROOT authorized ONE exact normal CTS screen, no rebuild/clock variant/250 fit. It completed. Clock screen: 2062 arrivals, 15014 related pairs, TT setup/hold damage 42.35/50.25 ps, FF 39.88/49.06; no missing arrivals. Public means 155.741/126.099 ps are INFO. Existing typed `core.json.clock_contract.kind=hard_core_latency` and `boundary_guard_context.source_core_json=core.json`; current `vclk_ref.py` returns `bound-ff 202.500000 40.000000`. Fixed 250/202.5 IO references remain. Actual old load: 2061 FFs 977.211685 fF + M1 clock 9.3458 fF (same old M2 cap), total 986.557485 fF.

Original IO screen under fixed references: TT input +490.652/output +606.791; FF input +14.133, output -54.903. ROOT/FLOW approved one output hold repair: 279 true negative outputs, each existing INV+BUF2, no existing HB4. Exact NLDM driver-reload/slew model selected 488 HB4 (209 ports x2,70 x1), +49.80528 um², 0 FF/cycles. Modeled min FF margin 5.117 ps, TT remaining >=422.027 ps.

The ONE native apply completed but check_placement caught one TAP collision. **Original plan/TSV is known flawed**: geom.tsv omits TAP cells; the planner used row metadata but omitted explicit 1263 TAP obstacles. Preserve `output_hold1/4_cts_outputhold.odb`, `output_hold_apply.log` as FAIL. Do NOT replay the archived plan without correcting its TAP inventory. Only the already-created pad `phy_outhp_6_0__1260` was moved from (4.32,48.33,MX) to (10.152,48.6,R0), with both adjacent hops <=10 um. No second 488-cell apply.

**Valid current candidate:** `output_hold1_fixed/4_cts_outputhold.odb`, `.def`, `.sdc`, `after.v`. Also copied to normal results path as `4_cts_outputhold_candidate.odb`; original `4_cts.odb` untouched. Native placement PASS, PG 20480 terms/open0; old 9752 master/orient/home/public pin shapes/PG wires EXACT. Clock identity: 108 nets/2249 instance signatures, zero changes. Positive-buffer graph collapse PASS on 279 chains and all560 ABI ports (8489 old functional signal-pin cells; physical-only1263 TAPs separately covered by native guard). 488 positive HB4, no FF/cycle added. Original SRAM PG181/181 remains valid because all old macro/PG geometry identical.

Actual post image: local client `geom_phy103_outhold1/auto_geom.png`, SELF VIEWED. G1 pinmax12.59/0 unregistered, r2r159.56/0 bad, colV.394/H.557/V.394, only standing empty.5827 exception. No GRT has run.

Postplacement RC screen: TT **+155.659042**, 2590 timed endpoints/0 negative. FF **-8.295864**, five residual internal endpoints (output repair succeeded):

- `rs -> tx_v/RESETN`: -6.710340; TT recovery 691.325378.
- `rs -> fault/RESETN`: -6.499010; TT recovery 691.153015.
- `_155_[35] -> tx_flit[53]/D`: -8.295864; TT setup 234.416092.
- `rb_wp_g[8] -> M1 SRAM w_addr_in[8]`: -1.043013; TT setup 661.174561.
- `_155_[120] -> tx_flit[138]/D`: -.436595; TT setup 363.331024.

Last read-only pricing finished in `output_hold1_fixed/internal5_price.log`; no repair was launched. ROOT has NOT yet admitted GRT. Resume same tree with an approved ordinary DATA-only hold correction/joint MM flow for these five, then actual post geometry/PG/TTFF and ROOT GRT decision. No clock fit/reference change. Full actual GRT and routed RCX/SIGNED still required.

## CDC319: tiny four-cell candidate ready for ROOT LOOK

Own intel2 root `/srv/opentallas-scratch2/claude/codex-kv-hr-1030/cdc319_eco1`.
Original routed NOTSIGNED: DRC0, TT-31.79, FF-.11, DRV85/94; retained in sibling `cdc319/signoff`.
ECO1 localized86 reset ties, added19 DATA buffers +one id46 hold BUF and1 upsize. Fresh GRT0 exposed TT-53.845/FF+1.323 and1 slew/corner. ECO2 adds1 buffer/3 upsizes; actual fresh GRT0 TT+3.469003/FF+1.322997/DRV0. Full current old-CLOCK scene G2: 78208 pairs/11062 regs, TT56.02/57.59, FF49.93/50.37, no missing arrivals. All-clock original SPEF named append preserves native DATA; coupling of all newly globally routed DATA to old CLOCK remains unqualified.

ROOT accepted PREP exactly3 DATA LVT cells `{wire4506,place3260,place3259}` and one BUFx2 on true `id_q[50] -> ib[1][50]/D`. Read-only saved-GRT 3-LVT model: TT+7.906898, all11726 FF endpoints0 negative/global+1.322997. Target's TT setup409.836. Global+1.323 belongs id50 DATA, **not** first-listed asynchronous report group (that removal is+21.776). Next FF before new BUF is input i_d63 +3.886835. LEF routing/pins/footprint identical except intended VT master/implant layer names; 3/62599=.00479%, no global LVT resizer exposure. Cin delta +.19266/.23570 fF TT/FF; leak delta +19.886/+10.641 nW; same area for VT changes. New BUF actual area .0729 um².

**Valid actual PREP:** `eco3b/3_place.odb/.def/.v`; exactly3 changed masters and one added BUFx2 at (28.566,157.14), native check_placement PASS, all old homes exact, 731 CLOCK wires exact, PG125200/open0. G1 pin10.35/r2r397.49/clock36.34/col.20; standing fill/empty only. Actual PNG local `/srv/opentallas-scratch/claude/codex-kv-hr-1030-client/geom_cdceco3/auto_geom.png` SELF VIEWED. ROOT LOOK requested; ONE fresh GRT NOT RUN. No DRT. Do not expose LVT to global resizer; allowlist exactly3. Fresh all-corner RCX/clock/DRC/signoff mandatory before closure; tight prior margins are not coupling waivers.

Failed preparation evidence retained: prepare1 EST104 old GRT cache after master changes; prepare2 assumed literal buffer name though native appends numeric ID; prepare3 physical overlap (wrong .216 width assumption and orientation/location ordering). Failed `eco3/3_place.odb` retained. Valid prepare4 uses actual width .270, native row orientation then setLocation, saves to `eco3b`. No failed verdict overwritten.

## RX259: positive fresh GRT candidate, not signed/adopted

Own intel1 root `/srv/opentallas-scratch2/claude/codex-kv-hr-1030/rx259_eco1`. Original route DRC0/antenna0, TT-37.76, FF+9.48, DRV81/70 retained in sibling `rx259/signoff`.
ECO4 fresh GRT0 TT-77.0499/FF+10.4926; route-aware ECO5 adds24 DATA buffers/17 upsizes, then GRT TT-1.862. ECO7 three targeted RVT master upsizes gave GRT TT-.039524 (still FAIL). ECO8 adds shared `split19866` BUF2->BUF4; **actual `eco8_grt` GRT0, TT+.655920/FF+10.492579/DRV0**. All13999 FF/clock/pins fixed, ordinary DATA master-only steps DPL0 movement; no extra cycles. Thin TT/old CLOCK scene coupling still requires ROOT route decision and actual RCX. No DRT/SIGNED.

Canonical four-pin candidate remains HELD: parent ownership_valid source band to RX min1227.6um cannot use one existing u_bin with <=405um legs; needs +2 relays/replan under OWNER. Tokens priced valid-only +2 as boot enable +1.666ns and steady0, but fault isolation/paired reserved guard needs real contract. die_id comes from `io_pad_die_id[2:0]`, not local TIE; no static-strap exemption/falsepath invented. Parent owns die G0/clock/adoption.

## Other retained work / owner holds

- PHYpad B50 DRC50 rootcause NE94–99% hold+face crowding; HB100 structural contraction preserves logical gates but actual fresh GRT FF-35.55 remains FAIL. 913 additional input HB4 estimate only (+93.18um²/+13.675mmL1, max47.142um; cut x72 adds1314 crossings before old usage). No build approved.14 asynchronous reset negative endpoints need separate pricing if pursued. Modern m10b remains FLOW-owned long-running5862-violation DRT as last reported; never kill/restart it.
- Prompt emitted RTL method5 EQ40607/40607; valid shared macro-cut mutant4 rc1 with sole intended begin_fault unproven/40606 proven, receipt in38ec. No live proof jobs. Old BB SAT-method errors are not NEQ.
- Existing generic HR FACE contract OWNER questions remain in CODEX-LOG; no blanket +1 landing or invented waivers adopted.

Scripts here are archival evidence, with original client/remote paths above. No frozen-clock/data-RC method control repeats are needed: supported named same-dataset append is FLOW7720c6679, lifecycle integrated on main. This packet is results/source only, not physical closure or die adoption.
