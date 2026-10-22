# QW-GEN2: successor GEN + die chain of the Qwen MU compute die dv2f18dh2 (LEAD2-QW, 10-19)

The owner rule is to run die-level integration early and often with stand-ins, so this run reverses Codex's 14:42 HOLD
("until every kit is qualified"). This is a PILOT_NOT_A_GATE die run. Every stand-in is declared below. Strict bind must
still pass: no stubs, no ties, dh_user driven.

Branch claude/qw-gen2-1019 = claude/mu-die-qw2-1019 4d2cb6301 + claude/qw-dieclk-1019 bbe250fb5 + this commit.

## Carried fixes (already in base 0d4c9808f / 4d2cb6301, first die run that reaches them)
- e0218f16e: reset release into foreign clocks (Q.STA.GEN.7)
- 3c133b609: chain fclk payload contract; the 87 relays are forwarded (Q.STA.RLY)
- QW-DIEFIX fdcf1a1c6: hr pack + HR_CONTRACT, die ROM bind + audit, heads N-far, redstn2 last-k; 4180abc13/3432055d8
  slice2 kit last-k (Q.STA.GEN.9)
- 4d2cb6301 QW-L1SEAM: layer_compile takes the seam from record_bundles. The chain runs with
  OT_RELAY_SCHEDULE=compiled_L1/relay_schedule/compute_compiled.json, so RELAY_CHECK is no longer SKIPPED.
- dhuser k3 closure record (qfd_sys_face_mu_dhuser-k3-46980a0f6) is in the tree. The die drives tt_ctlm.dh_user from
  mu_dhobs, with no strap.

## New in this commit
- rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu.svh is recompiled with
  D2D_MU=1 tools/qwen_split/d2d_cal_image_production.sh and stages 2,2,2,3,2,2/11,11,9,9,9,9,9. It now gives
  TXDP C [8,3,1,10] (0x0a010308) / K [21,4,3,3] (0x03030415). The stale copy had C [8,3,1,9] / K23, while
  qfd_sys_face #(MU 1) read it and qfd_d2d_static's TXDP came from the non-MU image [8,3,1,10].
- Die clock: OT_DIE_CLOCK_MODE=regional (tools/qwen_split/chain_dieclk.sh) runs the QW-DIECLK regional topology
  inside the chain (OT_DIE_CLOCK_VARIANT=rA). It builds local region trees fed by one forwarded unpadded spine, with a
  per-region judge in regional_verdict.json. The 446 owed landings (QW-DIECLK2 lane) are NOT in this GEN, so the
  verdict's landed term is expected to FAIL. The chain continues to GRT/STA anyway (diagnostic of everything else).
- die_chain.sh: the root-owned dieclk clock.odb and GRT outputs are copied, not hard-linked. dv2f18dh2 died on
  ORD-0007 Permission denied at this ln.
- bind_view_select_r9j.json: variant B binds the newest closed qfd_d2d_static view (r9j, in the r6 view dir).

## Runs (ot-epyc6, /srv/opentallas-scratch/claude/mu-die-qw/)
- dv2f19g2 (A): d2d view r5 (= dh2 binding; the relay schedule matches). This is the run of record.
- dv2f19g2j (B, PARALLEL): d2d view r9j via OT_BIND_VIEW_SELECT. RELAY_CHECK runs diagnostic only
  (OT_BIND_DIAGNOSTIC=1), because the compiled_L1 table is from the r5 frame.

## Declared stand-ins (the new safe kit is not closed, so the last closed view or the generated abstract is bound)
| element | new safe kit (state 10-19 16:30) | bound in this GEN |
|---|---|---|
| qfd_d2d_static (+OVL) | qfd_d2d_static_ovl_sf, views sf5/sf5w: gate FAIL lowfill, 268 roots >32, SAFE6 owner | closed r5 (A) / r9j (B); no OVL ports |
| qfd_native59_dv_service | r1 / safe3 / safe3b genuine FAIL; safe3c CTS live | generated abstract (never closed) |
| qfd_sys_face | bc2l terminal FAIL TT -57.9 ps, PG HOLD | closed MU0 rs3 view, RTL MU=1 |
| qfd_tt_ctlm_dv (+dhuser OPSEG leaf) | ctlm safe2 DPL FAIL; safe2n diagnostic | generated abstract; dhuser k3 view is its child, not bound at die level |
| qfd_sys_face_mu_dhobs | d1 not approved (comb in->out, 1% util) | generated abstract (drives dh_user) |
| qfd_dv_slice2_e / _w | slice2 regional / SAFE-QW-SLICE FIXING | generated abstract |
| qfd_c_b16_dv | CB16 landed parent HOLD | generated abstract |
| landh/rlyh0 non-1-bit classes | not closed | generated abstract (1-bit EN/EW/NE/NS/SW closed views bound) |

## Next GEN obligations (not in this run)
- 446 qfd_landh0 landings (QW-DIECLK2, land_owed_rA.json)
- OVL sequencer ports for qfd_d2d_static_ovl_sf
- MU-DQ-BOOTCTX claude/mu-dq-bootctx2-1019 600df51cd (mu_ctxrx + CTX_SRC), which is not merged here
- the safe kits above, once they close
