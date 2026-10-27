KV-CORES-R2/INGEST 2026-10-27: qkd_hr_ingest_eng lint unblock + face census (NO P&R)

Outcome: rtl_lint UNBLOCKED; face pin-register gate still FAIL (boundary obligations, not lint).

1. The blocked.tsv reason 'rtl_lint FAIL (const driver/latch); fix not merged' was STALE: it came from the 10-26 01:41
   kvhr kit (cores-kits/kvhr/kits/qkd_hr_ingest_eng__362.88x362.88), generated before ffaea6dce (02:48). The fix is on
   main as b50da0f1b8/6f5bb41d99 and in this branch's rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv. No RTL change.
2. Kit regenerated from this tree (claude/kv-core-slice-1-1027@18c72cf920 sources), slice plan pd_slice_delta/hm_r12.json:
   python3 physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py --core-json <core.json>      --plan results/kv_core_slice_1/pd_slice_delta/hm_r12.json --out <kits> --kit-rtl <dir with kv3_hub_Wi/kit_rtl.json>      --orfs-var SYNTH_MEMORY_MAX_BITS=32768
   core.json = qkd_hr_ingest_eng_core.json here (hr_prep semantics: --hr-elab wrapper qkd_hr_ingest_eng.sv + reached
   repo sources qkd_host_native_engine.sv, rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv, ot_sram_1r1w_32x128_m1_bb.v).
   kit_rtl_kv3_hub_Wi.json = minimal macro map (repo LEF/libs, md5-identical to the 10-26 kit copies); the epyc1
   ~/scratch/kv-g3/kit_rtl tree no longer exists on the fleet. 1396 pins, clock ck, 1 reset, macro ot_sram_1r1w_32x128_m1.
3. rtl_lint PASS (yosys proc + check -assert, 0 problems; was 2). Remaining 'Latch inferred' warnings are only for the
   scoped for-loop index variables (fordecl ob/oh/l), which have no readers; synth netlist has 0 latch cells.
   sdc_lint PASS, SELRANGE PASS (0 unwaived), DONT_USE check PASS.
4. Face census (face_census.sh = run_kit_kv.sh front half through core_preflight; ot-run unit oth-ubuntu-2834199-1793088055
   intel2): face_guard FAIL checked 1394 ok 1: unregistered 290, shared 797, dropped 306, feedthrough 0; ODB netlist same.
   port_gate PASS 1396/1396.
5. hr_face_ports recut (zero-cycle mechanism) on the same core.json: private_out 41 bits (done_tag 8, n_sectors 32, r_v 1;
   0 cycles); equiv post rc=0, mutant rc=1. It leaves (complete lists in hr_face_ports.json):
   unregistered outputs 324 bits / 7 buses: busy, d_rdy, in_rdy, w_v (comb ready/valid), r_addr 32, w_addr 32, w_data 256
   multi-capture inputs 772 bits / 6 buses: in_data 512, d_data 256, in_v, d_v, rd_v, w_rdy
   dropped inputs 256: rd_data[255:0] (no load at QKV=1)
   -> NOT zero-cycle. Under the kv_core_hr_price rules: +1 cycle per bus on 7 output + 6 input buses; the three
   combinational ready outputs (in_rdy, d_rdy, w_rdy path) need a skid/landing redesign, not just a flop.
   rd_data = declared dead-input pin drop candidate (0 cycles) if PATH-KV confirms the read port unused.
No timing, P&R or sign-off claim.
   emitted_v round-trip proof was still running at commit time (eq_rc.txt has post/mut only); kit RTL for a build is the hr-face-ports output only after eq_rc = post rc=0 mut rc=1 emitted_v rc=0.
   UPDATE: emitted_v proof hit the 2400 s docker timeout (no rc line; eq_rc = post rc=0 mut rc=1 only) -> the generator refuses --hr-face-ports on this DIR; rerun hr_face_ports.sh with a longer limit (>=2 h) before a recut build.
