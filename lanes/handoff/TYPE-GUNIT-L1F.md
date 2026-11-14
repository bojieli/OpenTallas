# TYPE-GUNIT-L1F (S81 dsdv_gunit_l1f_bf), started 2026-11-14 00:40 PST
Forms: F2 epyc8 s81-cores-2/gunit_f2/dsdv_gunit_l1f_bf_gf5f2 (unit oth-ubuntu-2649106-1794640208); a epyc10 type-gunit-l1f/a (outline 504x201.6); b epyc7 type-gunit-l1f/b (density 0.3, max layer M7).
Launch: ot-run --mem 64 --threads 16 --hosts H --dir KIT -- env OT_HOLD_STRUCTURAL_ADVISORY=1 NONPORT_HOLD=1 bash KIT/run_kit.sh KIT finish; logs ~/type-gunit-logs.
On first pass: add AUTO-RESIGN.tsv row (die s81, name dsdv_gunit_l1f_bf, host, dir of signoff/signoff.json), post RESULT. Cancel the other forms' units by exact unit name.
2026-11-14 15:25 a routed DRC0, setup -250.9; F2 GRT fail; b in repair_timing
2026-11-14 15:27 form c (FWPIPE +1 cycle, 504x201.6) launched epyc10; b and Fable g3 running
2026-11-14 15:59 READY posted a769ba16f6; ba0/ba1 FWPIPE builds queued epyc10 (ba0_fwp, ba0_fwps2, ba1_fwp). bf: b (epyc7), c (epyc10), Fable g3. Need all of bf+ba0+ba1 signed for FWPIPE.
