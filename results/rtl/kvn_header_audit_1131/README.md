# KVN header audit before the fresh gen1 vehicle run

Scope: one HOST command, user 0, token 1, position 8191, generation 1, epoch 4, CTX 8192, and all 36 layers from the per-layer corpus. This is a source/program header audit, not a token-pass or deadline receipt. No stimulus is derived from receiver expected metadata.

| Field | Actual producer source | Native contract / fresh compiled program | Finding |
|---|---|---|---|
| Record kind | Native TX emits kind 5 | Native RX requires kind 5 | Intentional protocol constant. |
| Tag class | Fixture emits `010` | Transport and native RX require class 2 | Intentional protocol constant. |
| Tag reserved/head field | `tag[7:3]=0`, middle low tag bit 0 | Native writer requires these zeros | Required format, not a missing dynamic field. |
| Word index / K,V half | Fixture pushes j=0,1,2,3, tags 0,1,4,5 | Writer expects `{index[1],0,index[0]}`; fresh C calendar has beats 0..3 in order | Values agree; no receiver field drives producer j. |
| Stage | Producer calendar's zero-based `lay_q + 1` | Native programme stages 1..36; layer is stage-1 | Intentional one-based stage, not an off-by-one constant. |
| Epoch | Actual HOST-token producer input `i_host_token_epoch_q` | Layer programme latches authority epoch; default HOST epoch 4 | Not boot/programme epoch. Native TX carries epoch[12:0] and rejects epoch>=8192. Default 4 agrees. |
| Generation | Same producer HOST_TOKEN_GEN command field | Native programme latches authority generation | Fixed by 1cf1044d9: default 1 now emitted as 1. Old fixture literal 0 was wrong. |
| Position | Producer CTX-1 (8191); HOST_TOKEN_POS defaults to that value | Programme latches authority position | Defaults agree. A separate HOST_TOKEN_POS override inconsistent with CTX is outside this fixture case. |
| Token | Fixture's internal TAG59 still has token 0 | KVN wire format deliberately does not carry token; RX binds token from the declared context | Unused internal placeholder, not a carried mismatch. Actual HOST command token is 1. This is not a multi-token qualification. |
| Segment / user | Internal segment 0; epoch[1:0]=0 for HOST epoch 4 | Programme emits segment 0; writer requires segment 0; MU user comes from epoch[1:0] | Single user 0. No claim for other users or concurrent contexts. |

The exact fresh compiled calendar at `intel1:/srv/opentallas-scratch2/claude/kv-fn-7/veh60/mu/img_bnd/program/calendar.json` has 36 program layers. Its C-side KVN events are:

- Ordinary layer segment: cycles 632,633,634,635; kind 5, port 3, beats 0,1,2,3.
- First-token/L0 segment: cycles 2259,2260,2261,2262; kind 5, port 3, beats 0,1,2,3.
- Fresh writer programme slots are 4,5,6,7, then stop 12. The native programme selects indices 0,1,2,3 at those ordered slots. This establishes field/order agreement; physical landing deadlines remain a separate gate.

Native wire layout is `{epoch[12:8],kind4,stage6,tag11,generation2,epoch[7:0],data512}`. Token, position and segment are explicitly absent from that wire layout. Native RX reconstructs full identity from its installed context; the producer never reads that expected identity to manufacture a matching header.

The native writer checks class/reserved bits and tag/index pairing in `rtl/qwen_sys/static_kv_20261014/qkd_kv_static_writer.sv`; identity/stage/generation are emitted by `qkd_kv_native_programme.sv` from latched producer authority. The native TX/RX source is `rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv`. Existing actual TX/RX generation control in `results/rtl/kvn_generation_1131` passed all four generation values and rejected oldgen0/expected1.

No additional carried-header constant mismatch was found for the stated defaults. A future multi-user, multiple-token, arbitrary-position or different-layer-count test needs an explicit producer stimulus contract; this fixture must not silently claim that support. The compiled token period is 293376 core cycles, so a full-token run needs a deliberate observation bound; the old POST=10000 run was an early-failure probe, not a complete 36-layer run.
