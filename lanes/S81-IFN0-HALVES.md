
## CODEX notes 2026-11-16 10:1x PST
- Took over hw0/he0 unchanged; active GRT FF hold repair at collection. The nominal face-branch hook moved only18 `ot_fcap_*_ff` cells. Actual input-cone census from 3_place.odb:604 input bits and604 first rising flops per half;586 via1 combinational hop,18 direct. Thus the name hook missed586 native input flops.
- Prepared independent successor kits epyc7 /srv/opentallas-scratch2/claude/s81-ifn0-halves/hw1, he1 from stable1-3 checkpoints. Clock hook reads exact604-name ODB list `ifn0_input_flops.txt`, errors on a mismatch; all original geometry/RTL stays. No added cycles.
- Visual review PASS-COND: results/geom_review/ifn0_all_inputs_1116.{png,txt} under lane root. Two central/east ROMs with10um horizontal separation, open west compute field and perimeter routes; actual clock timing remains to measure.
- Launched via ot-run64GB/16threads on epyc7, goal GRT: intel2 clients hw1 PID241701, he1 PID241702; logs ~/s81-ifn0-hw1-codex.log, ~/s81-ifn0-he1-codex.log. Follow604-flop hook count, TT/FF arrivals, GRT overflow and TT>=-42/FF hold before route continuation. hw0/he0 preserved as original experiments.
