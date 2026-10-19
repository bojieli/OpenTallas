# Actual SYSFACE producer binding extraction — full Stage1 stays OPEN

Source and artifact extraction only. No RTL file, public compiler, programme/profile, metadata, simulation, synthesis, implementation or live job was changed. The exact frozen GEN0 `die.v` SHA is `7b1bdfc5fd26c2e6f17fe6aa5b1d68bd9e2fa05bc3ecf408b9f163eb600bbde7`, read from ep6 `mu-die-qw/dv2f18dh2/out/case`. This matches the earlier consumer packet and `rom_bind.json`. The chain/case_r22k and chain/dieclk netlists were not substituted. The source snapshots are pinned separately to frozen0d4c and selected CALR7e515. `sources.json` hashes every source, and the full GEN0 netlist is retained with deterministic gzip.

Two concrete prerequisites are unresolved: the actual selected source profile does not supply complete L/E calendars, and the GEN0 lane manifest mislabels the TT programme lane's source clock. A valid packing roundtrip does not resolve either. `check.py --extraction-only` passes finite extraction checks; invoking it without that scope exits2 with the connected Stage1 HOLD.

## Real slots and serializer

Actual source `rtl/qwen_split/qfd_sys_face.sv` owns one4096×72 macro. Logical rows0..1023 are PW0..1023 with upper8 bits zero; rows1024..1031 are DW0..7. Boot records begin2048, encoded `{target4[71:68],addr8[67:60],28'b0,data32}`; target15 terminates boot. Unassigned rows are zero. These are SYSFACE config-ROM rows, separate from CALR command entry numbers406/1009 and separate from its two266-bit physical ROMs.

The selected committed ISA hash is cc5bc8fc17d4068ac9a49e8bf79f34e74350d56d114dd7fe5cde433d2ac82796, PW hash a3ee4a0eb1774e3c2dc00ee1bbedb21e723211758e7529bc8466284829d8c07d and descriptor hash1271ecf3f99204e35e07cc7d93a54362241b4a5ffe7358e2bc81cdc083a0c5e1. All400 ISA beats are independently checked: instruction i's beat b is PW16i+b = instruction[64b+:64]. PW400..975 stay zero; the39-word F16 template is not installed. All8 DW values are taken from the unchanged selected CALR descriptor. The calendar remains406 decode/1009 total entries and all original ME/XPF metadata stays unchanged.

Actual source-owned `tools/qwen_split/sys_face_image.py::viamap` maps logical row a/bit b to physical row floor(a/8), column8b+(a mod8), emitting512 rows of144 lowercase hex digits plus LF. The copied actual macro model independently confirms phys_row=a/8 and phys_col=b*8+s. `check.py` inverts all4096×72=294,912 bits using that layout and compares every logical row, PW beat and DW slot. The receipt digest independently derived from the qkd receiver's rotate7/data/address/descriptor ownership is b8de77b060896115.

`new_serialization_PROPOSAL/` is a **distinct newly constructed artifact**, never an original installed image or execution-qualified profile. Its exact hashes are:

| Artifact | SHA256 |
|---|---|
|program.memh|c7bf040bae9da27017db0406e4da947b62b05f9aa1d13ef491b21bf3fe7d1fac|
|logical4096.memh|7bbcc9b6598c01913ab157771c98036c36ab86deb539bd2684f33dbb8f525db9|
|sys_face_cfg.viamap.hex|3de8172e44384db27bdea414beb9527388c91928b6d40c097b84b5a08b6b598e|

The frozen SYSFACE constructor has ROM_VIAMAP empty and ROM_INSTANCE=`sys_face_cfg`; the macro can read `+OT_ROM_DIR/.../sys_face_cfg.viamap.hex`, otherwise VIAMAP, otherwise its zero-initialized array. The extracted GEN0 constructor manifest supplies MU1 but no selected programme via-map identity. Thus the retained source gives a precise installable file/slot contract, while a previously installed selected25-instruction SYSFACE image is **not established by this evidence**. No global filesystem absence claim is made. The old CALR table `expected.hex`1f5b521d… is a different asset; its bytes remain absent/UNKNOWN. The reconstructed be976ca5… and published CALR via-map hashes7e26a346…/9d9b953c… are not relabeled by this SYSFACE serialization.

## Actual source profile is incomplete

The selected metadata pins `compiled_L1/compute_programme/sys_face_events.json` SHA787345b9fc1845e9897f6200eaa5fe0ffd31f08a454ef75911bafb1d8a632d23. It contains T events, first_token1173, D2D first1176 and GO offset3. It contains **L_compiled**, not L; actual L and E keys are absent. Its own L_missing says native59 QSLOT relation to qkv landing is not compiled; E_missing says embedding EMBW/FILL timing is not compiled. The serializer reads `events.get('L',[])` and `events.get('E',[])`; unchanged invocation therefore emits42 boot records with empty L/E calendars. The new artifact preserves that exact behavior and records the incompleteness explicitly. Renaming L_compiled to L, copying the cap1 diagnostic one-END player, inventing an E image or injecting XT1 event data would change the source profile and is refused.

Real INIT/embedding, SU publications and attention return remain distinct producers. This extraction cannot qualify a connected operand stream until their real writes/address/masks/epochs and actual L/E slots are supplied. No `done−16`, extra warmup, delayed runtime waiter or synthetic completion substitutes for them.

## Replay and the two separate PW transport paths

`qfd_sys_face` issues registered rom_ce/rom_a/iss_idx at edge k. The real macro samples k+1, rom_q is captured unchanged in rom_qr at k+2, and dq_prog/dq_idx decode at k+3. On that decode edge the source simultaneously launches `{1,dq_idx[9:0],rom_qr[63:0]}` in tt_pw and the PW field of dh_prog; DW rows launch only dh_prog DW. `seq_dh={dh_prog,dh_run}` remains187 bits. PW valid/address/data stay one bundle at every point.

| Route | Actual GEN0 source path | Destination ownership |
|---|---|---|
|TT PW75|sys_face.tt_pw → rly_sf_tt_pw_0 (`qfd_landh0_75`, source ck_s=n_clk_d2d, destination ck=n_clk_r54)|tt_ctlm.pw → actual hard head PW store and separate u_xpf_pw_face → loader|
|CALR PW/DW187|sys_face.seq_dh → rly_dvw_sys_face_seq_dh_0 (`qfd_rlyh0_187`, ck=n_clk_d2d) → forwarded h1 → rly_dvw_sys_face_seq_dh_1 (`qfd_landh_187`, ck=n_clk_r54)|tt_ctlm.dh → actual dh_q capture → u_cal PW bits118/117:108/107:44 and DW186/185:183/182:119|

The additional `__fo1` branch goes to mu_dhobs, not the calendar's dh destination. Both selected lane manifest entries claim E1/K3; TT has one FIRST landing while DH has a hop0 station and a landing. These are declared model ages, **not newly observed receipt delays or native phase**. In particular `fwd_lanes.json` gives sf_tt_pw.src_ck=`clk_r54`, while actual SYSFACE.ck and landing.ck_s are both `n_clk_d2d`. This is a concrete source-manifest disagreement, retained in analysis.json. Neither that label nor common E1 justifies mixing the head's PW valid with calendar data.

Landing source RTL uses a four-slot ring, wc/rc reset epochs, slot validity and epo checking; K alone does not establish reset-relative first use. Actual SYSFACE reset is n_rst_d2d__fo2__r4__t24. CTLM reset is n_rst_seq_ctlm__t25 (its final reset relay is clocked r55, separately from CTLM r54). The TT landing uses en=t29/rs=t23; DH hop0 en=t14 and landing rs=t19. These are different actual source reset nets. Native insertion/phase, observed transport ages, stopped-clock safety and first-use remain NULL.

## Real commit and withdrawal source

SYSFACE u_record consumes actual prog_auth_slot/prog_rx_v/rx_payload from D2D, not the cap1 event-file control. `qfd_program_auth_rx` accepts kind13, port63, epoch[532:517], reserved fields zero. BEGIN low2 bits01 carries expectedPW[12:2]=1024 and DW[16:13]=8; AUTH low2 bits10 carries digest[65:2]. It registers begin_v/auth_v in the SYSFACE domain. These describe source record bytes; no actual host admission record or epoch7 identity is invented here.

Two actual receiver ledgers observe TT program_obs and calendar cal_program_obs after their own return routes. The sole calendar descriptor observer feeds sink1 directly and sink0 through one additional registered tt_descriptor_obs. Each qkd_program_commit revokes ready/cap on BEGIN before checking AUTH/writes; each requires all1024 PW then8 DW, correct digest/footer, and a later quiet edge with real control_stores_ready before READY. The actual two-sink join also revokes ready/cap on BEGIN and withdraws a completed seal when sink readiness/stores/cap are lost. SYSFACE t_go faults if boot/cal/installed-ready is absent or programme replay remains busy. No receiver withdrawal bug is alleged.

This establishes source priority and ownership only. BEGIN is not an existing same-age sideband of dh_prog/tt_pw, and it is not proven to revoke an independently stopped destination's first use. Its six rst_rec regions, rst_boot and rst_bpay remain distinct. No new auth sideband, F16 store, handle or context record is introduced.

## Private minimum binding proposal

`private_constructor.PROPOSAL.patch` is a reviewable text artifact, not applied RTL. It introduces PRIVATE_CALR=0 at the frozen LPF parent and GI constructor and forwards it to **existing selected7e515** u_cal.CALENDAR_ROM/TABLE_ROM at `qfd_tt_ctlm_dv_lpf_parts.sv:114`. Frozen0d4c qfd_dv_cmd_cal_mu has no such parameters, so the source file selection must explicitly pin7e515 in a private compile manifest; applying the patch against frozen CALD alone is invalid. Require the existing OPSEG1/CTX_DW1 source configuration, NU4/UVM4096/PIDX128/UTAG6 and STAGE_ME1; preserve the exact descriptor CTX mask0, rather than fabricating independent requests. This is no four-user numerical proof. Existing7e515 g_calrom names actual `calendar_m0`/`calendar_m1` ROM files; their exact payload hashes remain required. Public/default paths stay off.

The smallest connected source cone is: actual SYSFACE ROM and original record/commit sinks → both original transport bundles and GI dh_q → selected CALR → original cmd/tl plus u_gi stage start → actual ot_qfd_tt_ctlm_static_hr.u_head (its u_is1 and u_fixed_issue, programme SRAM/real captures) → original relocation/rom_cmd_q IB registers → qfd_dv_hr_pack → actual input/stream/tap cone → one NH8 head with its eight leaves/two epochs → the original first S corridor entry/relay/station/reset cone → ROM_TILE16 W16/G4/PART1 GT3072/MEM_EXTRA8/REGROOT2 tile. Reuse consumer0ad5903e0 source inventory and exact masks; retain fixed source-generated events. Do not elaborate the48-column head array, full16-tile cluster or full die. The hard head is a different component from the selected one XPF head; include both real programme/control paths.

Build admission is not granted by this packet. Before a future private compile: resolve exact L/E producers/calendars and the lane source-clock discrepancy; prove the real installed file manifest and source commit/withdrawal/fixed first-start relation; pin every selected source file and actual constructor; inventory extra hard-head/SYSFACE/record/landing dependencies and size memory from measured prior consumer2.27GB plus actual additional inventory. Preserve original four timing mismatches PC11 543vs672, PC12 2232vs2459, PC16 3883vs3625, PC20 4567vs4447. Original source cycles540/2229/3880/4564 plus HEAD0=3 are checked, never shifted. Proposed right-hand numbers remain unqualified, not a replacement schedule.

No runtime waits on observed done/read/ready may reschedule source events. Missing nodes must keep the full graph UNRESOLVED_FAIL_CLOSED. Native phase/reset/first-use,51 fanout roots,109 age failures, PG/storage geometry, complete publication coverage, authenticated final reads, full-token exactness and SU/MU rate remain independent obligations.
