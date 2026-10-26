# Current head source implementation, 2026-10-25

The current 326-partition/16-type plan is a new composition. The old H10b253-tile/17-SerDes testbench is not its provider. The canonical plan, four head dies and no-HBM decision are preserved. `tools/s81_head/head_source_model.py` emits the repo-relative actual component frontier and remaining contracts. It intentionally does not add `asbuilt` or claim G5.

The concrete new control piece is `rtl/dsrom_sys/s81_head/ot_s81hd_xstore_replay.sv`. It implements the80kb x store and continuous paired-stream replay required by the real current `ot_s81hd_bundle` and mini-array witness: A[m%256] and B[m%64] at G+5+m for8192+7*SK edges. The512-bit stage payload is160 words, but the internal bundle stream repeats throughout8269 edges at SK11. The candidate local load ABI is contiguous A then B, low256 then high256; this is an explicit input contract for a future real controller, not a newly invented host record. Storage is256x256 A plus64x256 B,512bits/cycle load and512bits/cycle read. Only control registers reset. Physical SRAM implementation/port timing/placement remain unmeasured.

`load_begin` and `issue` are one-edge commands on statically compiled dates. Load160 valid words after load_begin, with no issue/load overlap. A command without a complete load, excess load, or overlap raises sticky fault. The stored vector can be reused. `busy` describes replay only; it MUST NOT be used as the head's job_active or permit a new head position before argmax retirement. Actual whole-head issue authority remains the compiled START/admission contract, owned separately. No credits/completion schedule the stream.

This source targets canonical tile/bundle G+5, not standalone HEADB4 native-B G+6+a. Opt-in native-B integration requires parent-local alignment and a new source-pinned connection gate. No automatic offset, role, die S or host admission is fabricated.

The admitted4GiB/2-thread Verilator job under `codex-head-xstore-native-1025` used the actual released mini-array xa.hex/xb.hex (copied here). Both positions matched all16538 stream pairs and the G+5 timing; early issue raised fault without go. Wrong B-address mutant was caught at m0. These are transport/control component gates, not numerical whole-head or G5 evidence. The earlier synthetic gate is not used as the native source receipt.

Reproduction inside an admitted/staged repository job:

    bash tools/s81_head/xstore_replay_bench.sh NEW_OUT ACTUAL_XA_HEX ACTUAL_XB_HEX

The next work is concrete source composition: bind this xstore into a real command/admission/argmax controller, preserving native START/GO offsets; define the actual mesh64 record/valid/phase and channel-board515th bit; define host553-bit framing across the frozen276-bit link (N3 or an approved width change); extract the actual current LEP provider; map ROW0/TEN to264slots/253active with real PMA pads/status. The HBC stage's live context, job_active, starter_armed and status pins cannot be tied to fabricate closure.
