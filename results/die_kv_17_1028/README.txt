DIE-KV-17 2026-10-28 (KV die owner; successor of DIE-KV-16 7505ca76e0; branch claude/die-kv-17-1028).
Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-17-1028.  CHECKED-own = my run; nothing NUMBER-CHECKed independently.

(3) POWER of the 797,696 partition-entry pad FF (OWNER PG rule: measured activity, not flat 0.5)  [CHECKED-own]
  Method: OpenSTA 3.1 (ORFS asap7lock docker), ASAP7 RVT TT NLDM, 833 ps clock; a 64 x 16 ot_dp_dly chain mapped as
  bind_cells ot_dp_dly synthesises it (DFFHQNx1 + INVx1 per stage, no reset), padpower/pad_net.v.gz, pw.tcl, pw.log.
  Activity = MEASURED V input rate of the bank (pv2, 256 b) in the PG-ACTIVITY-KVHBM pv_pair active window
  (intel2 pg-act-kvhbm-1027/kv/act_pv_act.txt: u_s0.pv2 0.1405, u_s1.pv2 0.1435 toggles/cycle; pe2 0.096) -> 0.1435 on
  every pad stage (a pad chain repeats its input's toggles).  Per FF: 1.602 uW at 0.1435 (1.315 uW of it is the clock pin
  at activity 0; 2.316 uW at flat 0.5).  Clock-tree uplift from the same measured pv_pair routed core:
  (sequential 0.04504 + clock 0.03663) / sequential = x1.813.
  Pad power = 797,696 x 1.602 uW x 1.813 = 2.32 W (active-window activity; 1.90 W at zero data activity, i.e. the
  clock-only floor, since the chains are not clock-gated).
  KV die measured-activity basis (PG-ACTIVITY-KVHBM kv_types_meas_detail.json new_W x bound instances of bind5, 158
  partitions, phy_* excluded = off-chip PHY models): 187.85 W -> pads = 1.23 % (1.01 % clock-only floor).
  Note: higher than DIE-KV-16's ~0.9 % guess (the clock pin dominates).  PV partitions 52.5 mm2: +0.044 W/mm2 on the
  0.654 W/mm2 pv type (+6.7 %), still below the 1.050 W/mm2 PG window that passes (27.9 mV < 35).  Wire switching
  between abutted stages not included (data switching is 3 % of the pad power).  Denominator labels: hg/hgi/pv
  CHECKED (NUMBER-CHECK-3), the other types' 0.5498 ratio UNCHECKED-ESTIMATE.

(1)/(2) B48 whole-die token sim on bind5 (+ bind5m mutant): NOT LAUNCHED - BLOCKED at the boot image  [CHECKED-own]
  The token vehicle (tools/qwen_layerbench/kv_dieslice run_tok.sh, NATIVE_BOOT=1) needs a FULL native boot bundle
  (frames.hex / expect / epoch) and the pair image compiled on the bind.  img5 is component assets only
  (manifest status CURRENT_NATIVE_COMPONENT_ASSETS_NOT_FULL_BOOT_BUNDLE_OR_G5): no full bundle was ever compiled on
  the DIE-KV-13..16 binds.  Tried (boot5/):
  * boot_v36 run.sh on bind5 (KST 90,90,88,88,88,78,78): prep byte-identical to img5 prep_native2; pair image
    TXDP_K 030304aa = KV-16 [CHECKED]; the legacy asbuilt compile FAILS in mu_images: kv_frame_search no collision-free
    frame in 400 tries (run_legacy_tail.log).
  * native compile (kv_boot_v36 compile --mu --native-contract img5/native_contract.json --capability 1, bound padded
    ages): FAIL "T=7260: attention service needs 1697 edges, the link slot gives 1689" (native_compile.log).  The PV
    service at long context does not fit the pair calendar's fixed RESULT slot by 8 edges.  The prep (ages) is identical
    for bind4 and bind5, so this predates the V pads (DIE-KV-16 pads restore relative timing, 0 schedule edges); it comes
    from the DIE-KV-13..15 seams/PV schedule (seams 90/88/78 vs B48 68/66/67).
  * calendar D2D_ATTN_SERVICE_PAD / OT_KV_ATTN_SERVICE_PAD 8/16/32/64 does not close it (needs grow with the pad:
    1704/1697, 1720/1705, 1737/1721, 1759/1753) -> not a one-knob fix; it is the PV-service vs link-slot law in
    kv_static_programme.attention_calendar (r = max(P0,P1) incl. d_rl + pv_result_extra, service_end = tx_first - RX_CMD + 28).
  Vehicle source staged (veh5: stage_src.sh bind5, BOOT/HOSTSIDE_SOURCE_TREE = this worktree, 114 files, top sha
  9683dc86ace6, NATIVE_BOOT_SOURCES 5 files) - no build launched: the DUT's own dcal ROM and the bench far end both come
  from the pair image, so a ~250 GB build before the image compiles would be thrown away.

Bench coverage gap (owed to COORD 18:59): why the earlier KV token numbers did not see the 48-stage V spread
  - 4051.0 tok/s is the nativev7 COMPOSER (cycle model over component benches), not a simulation of a bound die.
  - PV pair bench drives the pair pins with the as-built V/command schedule; the vport bench (RT/DQ 128000 checks) is
    lockstep vport vs reference.  The die lanes vport -> bank (V), ctl -> bank (command), vport -> ctl (header) are in
    neither bench, so a per-bank V-D-H offset cannot appear in them.
  - The whole-die vehicle that contains those lanes (kv_dieslice) never reached its token phase on any bind: B33/B48 boot
    work 10-24..10-27 ended at BOOT PASS + native calendar (dcal) FAIL; TOK-QK KVL never reached FAR_LAYER_SUMMARY; and
    it was never run on the DIE-KV-14/15/16 binds (no full native image, above).
  - The static self-check that would have caught it (Codex kv_pv_pads_selfcheck V-D-H, d218a2b989) left with the withdrawn
    KV-P6-PV table; the DIE-KV-14d replacement was checked only by regen_constants kv_pv_trunk (command/flag law, no V term).
  Closed now: r8/kv_pv_v_pads.py check (per bank V-D-H = 0) on every KV bind + mutant bind5m caught (DIE-KV-16); the
  dynamic proof (token RESULT compare, bind5m must FAIL) waits for the image fix above.

(4) (b2) red_issue lane-group copies: NOT started (slice spent on (1)-(3)).
