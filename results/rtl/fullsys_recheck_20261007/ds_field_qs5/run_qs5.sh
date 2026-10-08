#!/bin/bash
# fullsys-recheck 2026-10-07: full-plan PQ1 field (all layers, every region) on the leading q-element QS=5 (QM=5), RTL ba69369aa (1b89b1b6d)
T=/srv/opentallas-scratch/claude/fullsys-recheck; cd $T/wt-qs5
export OT_PQQ_QM=5 OT_PQQ_QS=5 OT_PQQ_DEFINES=QP_CHECK,QT_CHECK
P=/srv/opentallas-scratch/claude/dsrom-field-spine/planv
python3 tools/dsrom_combined_l20.py field --cfg pq1_q10 --field-layers all --work $T/qs5 --plan-pq $P --jobs 32 > $T/qs5_field.out 2>&1
echo $? > $T/qs5_field.rc
python3 tools/dsrom_combined_l20.py qelem-lever --cfg pq1_q10 --work $T/qs5 --plan-pq $P --out $T/field_pq_qelem_qs5.json > $T/qs5_record.out 2>&1
echo $? > $T/qs5.done
