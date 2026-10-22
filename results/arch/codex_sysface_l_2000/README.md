# Opt-in sys_face L-context source candidate

Baseline dae8d7e02 selects qfd_sys_face_ovl_fault1, SHA b4acf28e39429d29e0dd4f926746f7496538332f55d200c283b37955fc4cbb94. The original file is unchanged. New master qfd_sys_face_ovl_lctx1 has default L_CONTEXTS=0, retaining single-base calendar playback. L_CONTEXTS=1 selects source segment 0 for STAGE 1 and source segment 1 for STAGE 2..36. An L-starting MARK or stage outside that range faults without launching L; observations never select or delay a start.

Compiler mapping is explicit: paired D2D segment 1 (token/L0) maps to source L segment 0; paired D2D segment 0 (decode/L1) maps to source L segment 1. These are different namespaces. Target-4 boot configuration retains the existing 32-entry table: entry address bits 4:0, reserved bits 6:5 zero, bit 7 selects the segment-1 base register. The compiler must write that base, fit both images in the combined table, and preserve the existing prefetch/config-settle, restart, reset and halt rules. A start while running still faults; no execution is stretched or rescheduled.

The compiler owner reports a current shape bound of seven compressed entries per pattern (one contiguous 32-beat QSLOT, four KVSLOT, two VIS/complete), at most fourteen combined, within NE32. Actual dates/collisions are not yet available and remain compiler obligations. No second programme or normalized-pattern equivalence is supplied here.

Model delta: no extra calendar entries, storage, clocks, external pins, memory ports, events per cycle or execution pipeline edges. Existing 32x32-bit L storage and one-event-per-edge player remain; the successor adds only static stage range decode, a segment-select signal into the existing prefetched-first-word mux and an invalid-start fault term. Added token latency is zero edges. Area/fanout/pin reach and SS/FF timing remain unmeasured until native-first MAIN/ALT gates. This is a correctness repair capability, with no performance-rate promotion.

The smallest selector test drives the actual successor's event wires and checks all 8192 valid/class/argument combinations in both modes. Icarus -i intentionally omits child engines. It rejects wrong-context and invalid-launch mutants. This establishes only selector semantics; it is not a calendar playback, full-master, actual programme, native fanout, or physical proof. Actual compiler tables, selected GEN parameter/source receipts, and matching MAIN/ALT physical results are still required.

Run: python3 tools/qwen_split/test_sys_face_lctx_select.py

## Measured native failure and structural source intermediate

The historical-image diagnostic stopped before floorplan with actual native FAIL: maximum1965,238violations (80sequential,158combinational). Dominant roots are T.ptr1=1965, L.seg1[1]=1028, L.ptr1=999, T.ptr0=967, reset rr_q1=578, E.ptr1=517. Raw and compact receipts are retained in native2.

Distinct master qfd_sys_face_ovl_lctx2 keeps the same L_CONTEXTS ABI and replaces all three generic calendar binary-index reads with the existing source ot_qwen_d2d_cal_sysface32 one-hot/local read engine through a functional adapter. Pointer/segment one-hot groups have16bits and table-read halves16bits. This adds existing local pointer/segment publication state without execution edges. Calendar component comparison against the original passes NE16/32/64 including both segments, prefetch settle, bursts, invalid start/config, halt priority and reset. Test words are component stimuli and supply no final programme dates.

The new reset forest has one first-stage flop, two second-stage branches and38third-stage leaves. Root asynchronous reset drives one terminal; each parent drives at most32 child reset terminals. Release remains the original third edge, and assertion propagates asynchronously. The38outputs match the original release/assertion in the30-edge minimum reset test. Fifteen original functional regions are retained;23additional leaf publications feed individual calendar reset groups of at most32functional FFs. Other inherited record/control reset groups remain unpartitioned and their native fanout is still an explicit closure obligation.

The source adapter's repeated cfg_data/start/segment wires are functional aliases, not claimed independent native publications. Full mapped census must measure remaining loads before any physical work. No whole-face native PASS, performance, actual-programme, view reuse or timing qualification is claimed. The source remains an intermediate until measured control/reset replacements close.
