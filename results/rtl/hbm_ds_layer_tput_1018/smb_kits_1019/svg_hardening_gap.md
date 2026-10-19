# Relative SVG service qualification gap

The existing SVG is a soft, multi-clock die aggregate. No ref_tile kit for ot_hbm_svc_sm_group(_rel_id) exists in the current physical/ref_tile inventory. Its historical 1036.8 x 228.96 um outline is over 4:1 and has millimetre reaches. A flat gate would not satisfy the current safe-design checklist.

At production LBANKS=4, the minimum existing SRAM inventory is 8 landing 256x256 macros, 5 canonical-cache 128x256 macros, 2 programme 1024x256 macros, and 2 descriptor 128x256 macros: 17 macros before repairing FIFO storage. Source paths: issuer_rel, feed_programmed_rel_id, sm4pc_cdc_rel_id, sm8_landing_bank, static_sm_packed136, calendar_static_x under rtl/hbm_accel.

The issuer boundary has combinational reserve_ready->reserve_v and block_ready/cache_owned->start_v paths; program_start_v is queue/rc combinational logic. Every hardened boundary needs actual registered inputs/outputs and two-stage reset landing, with added cycles reflected in the static compiler slots and model. Preserve relative address, expert id, epoch, bank and tag mutation witnesses.

Each landing response FIFO uses IW=283+LB=285 and DEPTH=8, or 2,280 bits, in a runtime-indexed flop mem in ot_hbm_svc_async_fifo. Eight such FIFOs exceed the >~2kb SRAM rule individually. This requires a reviewed macro-backed CDC implementation and its actual read/capture latency, not a gate waiver or a source-size omission. Do not remove FIFO validity/epoch/duplicate checks.

Partition by native clock domain: stream issuer+programme/relocation, four HBM PC owners, HBM return dispatch, and the eight stream landing banks, plus the canonical-cache consumer. Reuse real hardened leaves where available. Size SRAM corridors on the 43.2 um origin lattice and keep one full-width cell band in each leaf. No unreviewed clock-group/false-path/multicycle masking. A hierarchical parent needs matched hard-child insertion and landed region crossings.

The current attention unit compilers only emit direct SM command/packet/x-write/KV-desc calendars. They have no SVG envelope/read emitter. Their pread at consume-3 is the probability SRAM read in cmd_ext, and req_lead is an observational request, so neither may be shifted to implement PREL. Implement real <=64-line SVG block/descriptor lowering, split calendars without violating fixed GO, and encode each cache read in the SAME word as its packet-valid/tag command. Then prove actual relative SVG+XC+SM packet alignment and price all block-boundary/landing cycles. Existing matvec SMB uses this same-word convention already.
