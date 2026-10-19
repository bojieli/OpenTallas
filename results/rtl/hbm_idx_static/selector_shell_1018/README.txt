IDX-SMALL 2026-10-18: rtl/test/hbm_idx_static/run_selector.sh OUT MUT 1 (SHELL=1: the pin-registered die master
ot_hbm_idx_selector_static, one clock root clk_ctl, clk_q/clk_mem driven by an unrelated idle net), source commit
6c9f86511 (branch claude/hbm-idx-small-1018), fleet ot-epyc4. 3 full-shape frames (random 10,928 keys / all-equal ties /
partial 4,100), 512 selected each, 12 real 256x256 SRAM models.
s0 MUT0 PASS: errors0, fault0, every frame 867 edges (core 865 + 2 pin-flop edges), first emit 834 (core 832 + 2),
   threshold/selected identical to the core run.
s1 MUT1 (keeps every threshold tie: ky >= threshold) FAIL; s2 MUT2 (corrupts the first emitted ID) FAIL.
