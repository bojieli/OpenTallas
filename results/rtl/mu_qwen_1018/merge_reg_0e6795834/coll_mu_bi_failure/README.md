# Unexpected coll_mu_bi positive failure

The completed 0e6795834 regression is **40 as expected / 1 unexpected / 3 active** at the pickup snapshot. No retry or rebuild was launched. This evidence is separate from the passing SAFE source/fixture.

Both MU30 and user0-only11 fail from message0 word2. MU has61424/61440 mismatches; user0 reference22512/22528. Issuer command checks are clean, all eight dies latch transport/collective faults. Message0 issue99, first input slot100, expected first output641; first logged bad word2 therefore corresponds to643. This is derived from the saved compiler program; the old log does not print cycle, actual payload, header/tag, or the first fault edge. First command expected tag0 (non-SEQSU message index), no observed header proof exists. The first source-calendar command is absolute251676,user2,L18,allreduce1, shifted to99; the single-user reference also fails.

The final sticky state identifies face2 (SerDes0) unexpected RX frame cause0x08, face4 (SerDes2) missing RX frame cause0x04, and RX CDC write faults on both. It cannot order the first event. The first failure precedes command1 at1623, so cross-user overlap is not required for the saved symptom.

`comparison.json` pins every source hash to the regression commit and compares the passing SAFE hard1 record. The old dv2f14bi fixture measures TX/RX port0→2 as6/6 and port2→0 as7/2; current dv2f18dh2 measures3/7 and8/3. Its landing K straps differ (oldTX0=2,RX0=2,TX2=7,RX2=6; new3,3,0,7), despite equal N/profile LU53/LS378. Issuer depth31 versus8 and six changed RTL/test sources are also real differences. The ring core, issuer, CDC ring and arithmetic source hashes are unchanged. No sum-of-ages substitution qualifies either fixture.

This establishes an obsolete fixture/source combination relative to current SAFE evidence, **not** that the MU bug is fixed or stale-only. Current-source MU behavior remains unresolved until a controlled comparison with exact fixture/phase/header receipt is authorized. Preserve the positive failure and its source recipe; do not relabel it expected.

The current SAFE branch cases.py recipe remains byte-identical to0e6795834 and still selects cal_dv2f14bi for mu_bi. Passing SAFE direct bench runs explicitly select dv2f18dh2. The recipe/fixture mismatch is therefore still present in that branch; it has not been silently updated or qualified. Exact old fixture and recipe hashes are preserved.
