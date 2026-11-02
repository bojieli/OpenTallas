# Turn paired profile and unresolved upstream frame

ONE owned paired TT/FF B diagnostic completed on Intel1 unit1945396-1793628422, exit0,8GB2T normal admission. Exact completed legacy A receipts were reused. Both signed setup/hold results and every remaining negative are retained. No P&R, repair, source/kit adoption, gate-authority change, rejudge or SIGNED claim follows.

B used the exact old helper plus **only** the independently reviewed real-clock classification/propagation blocks from43e49c51f. Full43 contained an unrelated core_clock_band dispatch evolution; it was rejected before running. The private patch reverses byte-for-byte to the original A helper. B enables OT_POSTCTS_REAL_CLOCK_PROFILE=1; tolerance profile is OFF, raw20ps tolerance and old band policy are unchanged. Native SDC/Lib/config/RC/source hashes matched A, and the actual5GRT images were already personally VIEWED with identical ODB hashes before the earlier timing query. Fresh same global-route RC was estimated in each new B process.

| Measured field | Legacy A | Profile B |
|---|---:|---:|
| TT setup estimate | −340.16 | −202.66 |
| FF hold estimate | +10.01 | +10.01 |
| TT hold (information) | +12.59 | +12.59 |
| FF setup (information) | −117.99 | +0.74 |
| CLK-family pinreg meanTT /FF | 421.97 /327.65 | 421.97 /327.65 |

All5actual source-bearing clocks are propagated, sole source-less vclk remains ideal. Clock-family pinreg count1146 and its means are unchanged, as intended; forwarded-clock insertion is not mixed into that band census. Raw TT band FAIL20/FF PASS remain preserved. No40ps tolerance reclassification was applied.

The remaining TT worst is still the FSTART→ring path; its actual capture clock now contains its physical tree. Correcting ideal capture removed137.50ps of the old apparent deficit and moved the FF setup estimate by118.73ps, but does not prove the remaining−202.66 is a qualified physical DUT failure. Before DATA changes the actual upstream frame must be joined.

Receiver metadata has no hard-core early tap: core_latency/core_taps are empty and no core-tap overlay marker exists. Its primary clk has source early−40/late0; vclk is450TT/342FF. Incoming fclk_in_u1_i/d1_i are independent real833ps port clocks with source0. Edge metadata supplies period_mult1 and XY, not a measured external phase/arrival interval. Do not add a guessed450ps latency or subtract a measured mean from any SDC.

Exact immutable GEN source is prepared_l48z/source_plan.json SHA0c98a23000ade2c3fb13de073ca3f09eb8868b412e70921870abda21888bac12, with sidecardfe1fd228189319ff64e70436f884bc138ac0ba43b1632191c5e61c6ddbabb7c. Receiver is nst3_turn:

- u1 forwarded clock and FSTART come from **lk_WN1 /hd_serdes**, fclk_out_coll_o0 and cland_fstart_out_coll_o0 on coll_WN1_u__0.
- d1 counterparts come from **nst4 /hd_st_n4**, fclk_out_d1_o and cland_fstart_out_d1_o on coll_WN1_d__1.
- The planned SerDes output is fwd_buffer **from source_clock_port clk**, not an assumed450ps internal leaf and not recovered PMA. Its primary tap is1442.88,77.76; forwarded output1705.76,2.656; registered FSTART1714.4,2.656. The planned n4 export source is clk_t27.
- LC metadata supplies K17/depth4/sched_lat2 for u1, not an absolute picosecond clock/FSTART phase contract.

The SerDes clock basis explicitly says parent-budget one-entry regional CTS trial and **publish actual routed mean before release**; TT450/FF380 is a placeholder. Its landing contract is physical_qualified=false, and this exact prepared wave holds hd_serdes rather than publishing a current bound native view. The SerDes source owner confirmed no measured production forwarded-clock/FSTART phase contract exists to supply; shared ot_s81hd_serdes_link→ot_pdie_serdes proves logical clk domain only. S81/Q1/PMA-reset candidates are unselected and supply no substitute authority.

Missing evidence is the actual upstream primary-tap→forward-buffer+seam delay/phase relative to FSTART launch FF/CQ and the receiver reference. Planned source topology is useful, but neither0nor450ps is a measured output-driver arrival. Retain the upstream-source/phase HOLD; do not retime the receiver, insert clock latency, alter reset/IO/period/uncertainty or adopt a new clock variant to clear a readout. A later real-parent/native-source clock window must bind this frame. Conditional DATA cone pricing can proceed without adopting a physical repair; the current589ps START/control tree remains a useful target once the frame is qualified.
