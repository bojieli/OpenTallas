# qfd_dv_slice2_vm8r (QW2-VM8P4 10-21, Q.STA.SLICE.2; CRITICAL prefix qfd_dv_slice2: gate only, no submit)
P4 structural successor of the P3 gates qfd_dv_slice2_vm8q / vm8qb (in-flow ep6 10-21: ONE clock root over 1.43 mm; parent
flop clock arrival 1.2..2.2 ns vs hard-child insertion 333-485 ps -> post-CTS setup -460 / -522 ps SS on ~9.6k endpoints,
repair inserted 0 buffers = clock skew, not logic).
P4 = LANDED parent (landed-regions standard): flat wires-only parent rtl/qwen_dv/s5/p4/qfd_dv_s5_vm8rf.sv -> tools/landed_parent/lp.py
(spec tools/landed_parent/specs/qfd_dv_s5_vm8r.json) -> rtl/qwen_dv/s5/p4/lp/qfd_dv_s5_vm8r.sv; record
results/arch/qw2_vm8p4_1021/lp/qfd_dv_s5_vm8r_record.json. 10 regional CTS roots: va vb vc pg (row 1 + S band), cl ch bt (row 2,
clock entries on the N face), fc (CROM reads + cr_q capture), fb (BTAB reads + bs_q capture), fv (VM-write broadcast entry).
50 landings (D 4 / E 2, chunk 24, shared rings, 27.6k ring flops), reset depth 5 with kept copies <= 32 loads.
Price vs flat vm8rf (== vm8fh offsets of P3): VM answers +3 (writes +3: write->read distance unchanged), PROG +0, BTAB / CROM +6,
reset release +5.  Kit generator: tools/qwen_dv/s5_vm8r_kit.py.  SAFE review: lanes/QW2-VM8P4.md + spec safe_design_checklist.
Benches (Verilator 5.050, fleet): lp lockstep rtl/qwen_dv/s5/p4/lp/qfd_dv_s5_vm8r_bench.sh (MUT0 PASS, MUT1-4 FAIL, audit PASS,
unland audit FAIL); flat vs vm8fh rtl/qwen_dv/s5/p4/qfd_dv_s5_vm8rf_p3_bench.sh (PASS). Witnesses results/arch/qw2_vm8p4_1021/bench/.
