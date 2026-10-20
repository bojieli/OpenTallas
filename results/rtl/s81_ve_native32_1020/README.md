# VE native32 structural experiment — no adoption

Immutable RTL source is `6ad9506a1`; module ot_s81sl_ve, LM5/LA4 production shape. No repository RTL is changed. Fleet location: ot-epyc5 `/srv/opentallas-scratch/claude/codex-s81-ve-native-hook-1020`. Bare synthesis without keep hook is diagnostic only and is not the baseline here.

Production hierarchy + ot_keep_regs.tcl + flattened synthesis + dfflibmap + five exact TT Liberty files + ABC-D770 produces 1919 nonclock roots above32 (max131). The opt-in SCC-safe graph worklist (`8f4aaf874`, parent `cf32860cf`) removes transparent buffers, clones single-output primitives, preserves exact type/polarity/clock/reset fanins, and refuses cloning feedback SCCs. Limit32 emits2194 primitive clones, including1693 additional FF. Emitted and subsequent keep+synth+ABC retention census each report271350 roots, max32 and zero above32. Full compressed actual-root receipts are included; structural ledger is compressed separately. Artifact and Liberty hashes are in candidate_identity.sha256.

Resource model:46297→47990 FF. Summed library cell area33620.50314→32356.5192 um² excludes emitted inverter costs and later physical buffering, and is not a physical area improvement claim. No geometry, reach, PG, depth, or clock qualification is claimed.

Exact imported Yosys0.68 sequential model passed the canonical PDK coupons: ASR544 and HQN128. Inventory is47704 HQN and286 ASR; these are the only sequential primitive types. Coupon scope does not bless other imports or primitive types. The native replication ledger does not establish behavior or equal initial states. Unmodified feedback SCCs remain, so a whole-DAG capture certificate cannot apply. Independent initial-state/first-valid/inflight-reset proof is still required.

Fleet full RTL versus emitted-native miter unit2437682 is RUNNING (client4121125/session85207),128GB/4threads. It uses Verilator5.050 randomized independent unreset state, two fixture seeds, original full production golden, checks control from first released edge and all valid data, then interrupts legal streams with eight differently aged/length resets. Outputs during assertion follow the existing parent's don't-care reset contract; there is no post-release mask. No behavioral PASS is claimed until actual terminal logs are collected. The exact bench/recipe is included. No layout gate, REVIEW, submission, binding, or default adoption is authorized by this record.

## Initial behavioral diagnostic and hardware-view follow-up

Unit2437682 compiled successfully in6m15s (peak RSS7.4GB), then fixture generation stopped because the staged archive omitted tools/hdc_golden.py. This is setup failure, not a design verdict. The completed executable and original failure log remain on the fleet. After adding the exact dependency, unit2575706 ran seeds7/29: each passed the full golden phase and1830 comparison edges including eight in-flight resets. The recovered logs are included.

This first run is DIAGNOSTIC because source inspection found the original ring RTL explicitly initializes wptr to0 inside an ifndef SYNTHESIS block. Its native candidate registers were independently randomized, but the reference pointers were not. Hardware-view unit2575896 now compiles with -DSYNTHESIS to remove that simulation-only initialization and randomize all unreset hardware state on both sides. It uses a separate obj_hw directory and preserves the first build. The exact recipe is included; its terminal result is pending. Neither run establishes an unbounded state-equivalence theorem for remaining feedback SCCs.

## Hardware-view result and binding census

Hardware-view unit2575896 TERMINAL PASS: Verilator5.050 with -DSYNTHESIS removes reference ring-pointer simulation initialization, and independently randomizes unreset state on both sides. Seeds7/29 each pass the production golden12partials+256outputs (reduce129/add44edges) and1830 comparisons across eight interrupted streams/resets. These are bounded simulation witnesses, not an unbounded SCC/state-equivalence theorem. Full build and run logs are included.

Current mandatory actual-Liberty census (tool from main8608a236c, SHA recorded) unit2600612 PASS:271351 roots/max32/zero role errors. The one-root count difference from the historical census is a tool enumeration difference. Actual Liberty roles and source hashes are recorded in the compressed receipt; functional-pin, pin-registration and storage contracts are explicitly NOT_EVALUATED. No physical admission or adoption follows from fanout alone.
