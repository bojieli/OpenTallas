# TYPE-GUNIT-L1F (S81 dsdv_gunit_l1f_bf), started 2026-11-14 00:40 PST
Forms: F2 epyc8 s81-cores-2/gunit_f2/dsdv_gunit_l1f_bf_gf5f2 (unit oth-ubuntu-2649106-1794640208); a epyc10 type-gunit-l1f/a (outline 504x201.6); b epyc7 type-gunit-l1f/b (density 0.3, max layer M7).
Launch: ot-run --mem 64 --threads 16 --hosts H --dir KIT -- env OT_HOLD_STRUCTURAL_ADVISORY=1 NONPORT_HOLD=1 bash KIT/run_kit.sh KIT finish; logs ~/type-gunit-logs.
On first pass: add AUTO-RESIGN.tsv row (die s81, name dsdv_gunit_l1f_bf, host, dir of signoff/signoff.json), post RESULT. Cancel the other forms' units by exact unit name.
2026-11-14 15:25 a routed DRC0, setup -250.9; F2 GRT fail; b in repair_timing
2026-11-14 15:27 form c (FWPIPE +1 cycle, 504x201.6) launched epyc10; b and Fable g3 running
2026-11-14 15:59 READY posted a769ba16f6; ba0/ba1 FWPIPE builds queued epyc10 (ba0_fwp, ba0_fwps2, ba1_fwp). bf: b (epyc7), c (epyc10), Fable g3. Need all of bf+ba0+ba1 signed for FWPIPE.
2026-11-14 19:40 successor: ba0_fwp/ba0_fwps2/ba1_fwp killed by earlyoom (infra), relaunched epyc9 (logs gunit_*_r2.otrun.log). bf c died GPL-0307 READ15, congestion 2.83 vs a 1.27; c2 (right-sized READ guides, h216) proposed, waits g4 verdict.
2026-11-14 19:50 COORD ruling: g4 counts on R-MINIMAL with OT_S81_GUNIT_FWDOWN in S81 bind defines; if miss, build c2 (READ guides from cell area, h216), max_phi_cof side A/B.
