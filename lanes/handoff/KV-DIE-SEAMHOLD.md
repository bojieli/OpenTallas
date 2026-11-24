# KV-DIE-SEAMHOLD handoff (Opus 5.5, COORD split from KV-HUB-EPZO item 2, started 11-23 21:31 PST)
Job: dch / forwarded-clock landing-ring port->FF hold (hub_Eo ft16_i -182 post-CTS / -160 GRT; astk ep_zo -55..-99; s_d rings -26..-65).
Base: KV-ALLFIX A3g = plan b258e3e34f22 + asbuilt A3f e9d82a711970, rt 9b19260c1cde (confirmed by KV-ALLFIX 21:3x). epyc10 work dir /srv/opentallas-scratch2/claude/kv-die-seamhold.
## Census (21:4x)
- census.py over A3g (rt landing_contract.ring_input_ports): 93 types, 2534 forwarded rings, ALL write on the fall edge; contract 2462 rings at the -385 die default, 72 at -50 (io_cor, io_cor_v1, sys_SD_v1, hroot). Table: lanes/handoff/KV-DIE-SEAMHOLD-census.tsv (receiver, band, width, fall, contract, sender type:bus).
- Kit math (fall write): port slack = T/2 + c + d(port->D) - L(rx fclk) - hold - unc. With c = -385 the window is 31.5 + d, about 80 ps, so ANY fclk tree deeper than about 80 ps fails in the kit. This is the -385 default, never measured (FABLE-UNC-KV 02:20).
- Die eye = kit slack - c + m_FF, where m = min(data - fclk_out) at the sender port (FABLE-UNC-KV method, ringeye.tsv).
- hub_Eo ft16_i: sender kv3_hroot o_kvs_hroot_Q_o_ctl, m TT +39.1 (FF ~+31.7) -> die eye -160 + 385 + 31.7 = +257 at GRT.
- Senders of hub_Eo: hroot (measured), hg_v3 astk (UNMEASURED), hub_Ei ft (UNMEASURED); hub_Wo: hroot, hg_v3, hub_Wi.
## Structural form (ruling)
- No fclk depth cap (80 ps on 138-267-bit rings is not buildable and is not the cause). Source-synchronous alignment: per-receiver measured clock.ring_hold.sender_ps_types (rt supports it), = min m_FF over the receiver's senders - 20 margin, only when every sender is measured.
- Needs m on hg_v3 (o_astk_Q*), hub_Ei / hub_Wi ft outputs: rprobe.sh (fable-unc-kv/tools) on their 4_cts DBs.
## Full-cause scope (COORD 21:5x, FABLE-RC-KV 21:45 ACCEPT row form + 4 conditions)
- Measure m for EVERY sender type with a view; unmeasured rings keep -385 and are listed per type (coverage tsv).
- epyc11 L=/srv/opentallas-scratch2/claude/kv-die-seamhold: kits/<type> (staged copies: gen dir minus run/, + 4_cts.odb/.sdc), mjob.sh TYPE (rpff FF + rprobe TT -> m/<type>/{ff,tt,both}.tsv), drive.sh N (ot-run driver, log drive1.log), msum.py, tools/ (fable-unc-kv rprobe/rpff).
- localhost scratchpad seamhold/: census.py, pick.py (newest 4_cts per sender, proxy = strip __suffix), stage_<host>.sh, mkvalues.py (values.json, coverage.tsv, sender-obligation.json), ROWS_KV-DIE-SEAMHOLD.py (PLAN_IN PLAN_OUT, env SEAMHOLD_VALUES).
- First results FF/TT: hg_v3 -14.7/+15.9 (ft3_o, astk ep_zo -0.8 FF); hub_Ei -13.4/-0.8 (ft73_o).
- Inventory: 30 sender types with an 11-12+ CTS DB, 11 by proxy, 52 none (pv family, hg_v1 family, pc split copies, hub_Wi); older (10-31..11-12) inventory running.
## 22:5x state
- 31 sender kits measured on epyc11 (m/<type>/{ff,tt,both}.tsv + dp/duty.tsv). 51 sender types have no post-CTS view anywhere (inventory 10-31..now, 8 hosts).
- Duty: fclk_out is exported from the sender's LOCAL clk tap (OT_CLAND_EXPORT_REUSE fclk_out_ft3_o <- clk_t7), so per-port late-fall shift (15-27 ps) is subtracted, not chain-summed.
- Values: A strict (exact + split copy) 11 receivers / 290 rings; B (+family proxy, defect kits m<-100 excluded as proxies) 89/93 receivers, 2241 rings. Measured value below -385 = sender defect, kit keeps the default (hgi_v8, hub_C <- pv_v12).
- KVHEAD -50 entries contradicted: io_cor_v1 -> -157.7 (io_ft_v1 ft3_o), sys_SD_v1 -> -260.8 (io_ft_v1 ft0_o); row takes min(old,new).
- LATE-EXPORT defects (fam-late-export.tsv): pv_v12 (D28 SINKSPREAD kit 11-23 14:29) fclk_out insertion ~960 vs data 315 -> m -650 on 53 ring outs; io_ft_v1 ft0_o -211; phy_v1 ft0_o -157; hgi_v7 ft* -118..-129; pv_v6n 3. Sender-side structural fix needed (export tap = launch-flop leaf).
- Gates on epyc10 (sh_gate.sh): gate_strict4 / gate_fam4 (PRE vs A3g base delta + scoped strict bind hub_Eo/Wo + SDC min delta). Earlier strict/fam/2/3 runs killed (schema key in row, values updated).
- Hub files: lanes/handoff/KV-DIE-SEAMHOLD-{fam,strict}-*.
