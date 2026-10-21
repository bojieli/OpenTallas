# PC sr11b clock distribution successor

Recursive geometric independent spines for ck/hck replace sr10b sink-driven CTS. RTL/params/macros/pins unchanged, zero added edges. sr10b terminal exact gate is preserved separately: GRT overflow0, clock ck TT116.2/FF105.0ps FAIL; hck59.2/53.8.

SAFE review before gate:
1 Pins PASS unchanged RTL pin stages; two-stage face reset.
2 Reach existing waiver: same 267.84x300.24 outline; prior few 405-465um feedthroughs accepted, actual timing decides.
3 Fanout PASS source-identical r8/r9 census max32; mapped data cone unchanged; new clock buffers measure separately in CTS.
4 Depth PASS/WARN prior placement TT setup+140.6ps, actual gate/route timing decides.
5 Storage PASS 23 native SRAMs, no new storage.
6 Floorplan PASS same23-bank column split, continuous std rows; fill33% pin-bound frame waiver.
7 Clock FIXED structurally: independent spatial distribution+measured leaf padding for ck/hck, no cross-clock data change; TT/FF spread <=80 pending gate; hold margin0.03.
8 Schedule PASS static, no added data cycles or changed port semantics.

# qkd_kvs_pc_sr10b (KV-PC11 10-21, PARALLEL fallback of qkd_kvs_pc_sr10; bind whichever closes first)

Why: the sr10 CTS gate images (ep9 ref_gate qkd_kvs_pc_sr10-20261020-193847, placed dump) show column B (x 172.8) as a
7-bank stack (CDC up 5 + tag queue 2) over the 6-bank CDC down stack with only a 10.8 um gap.  Under the M5 layer cap no
horizontal wire crosses a bank (M2/M4 blocked), so every wire between the centre logic and the dense E-face logic
(er / her / hes / land_er / land_es) must pass that gap or the stack ends -- the same barrier that failed the sr9 route in
column A (FF hold -57 from a detoured H-tree tap net; DRC 5 on a stacked-bank net).  sr10 trial GRT also needed 24+ extra
congestion iterations.
Fix (floorplan only; RTL = r8 528d8460a, kit = sr10 otherwise): column A unchanged (MY, 3/2/3/2 groups, channels 21.5-23.6);
column B split 4/4/3 (down 0-3 | down 4-5 + up 0-1 | up 2-4; bases y 23.76 / 114.48 / 205.2) with two 21.4 um channels
(3/3/3/2 with three >= 20 um channels does not fit the 2.16 grid between the 20 um N / S pin-face keepouts); the 2-bank tag
queue leaves column B for its own stack at x 108.0 (MY, read face E toward the centre; y 241.92..276.6), >= 32 um from
both columns.

## SAFE-DESIGN checklist
1 Pins: PASS (= sr9/sr10: RTL pin stages; reset lands in 2 registered stages, 2 RESETN loads per port).
2 Reach: PASS by sr9 pin order (placed reach on PC_H sr9: 8 pairs 405-465 um feed-through, accepted); recheck on gate.
3 Fanout: PASS, native census r8/r9 max 32 (same RTL); this gate's census is the receipt.
4 Depth: = sr9/sr10 (textbook ~607-622 ps WARN, timing decides; TT setup +53..+137 on sr9 route/gate).
5 Storage: PASS (23 SRAM banks).
6 Floorplan: FIXED: column B no longer a 13-bank wall (two 21.4 um channels + 4-bank max), tq at x 108.0 (21.6 half
  lattice; gen macro_grid / channel / macro_edge PASS); util ~33 % waived (pin-bound die frame, fill_reason).
7 Clock: H-tree taps have a channel within ~35 um in both columns; io_hold_margin 0.03; spread checked on the CTS gate.
8 Schedule: static, 0 added edges.
Benches: = sr9 r8 receipts results/rtl/qwen_kv_die/kvpc_sram_sr9_1020 (Verilator 5.050, same RTL).
