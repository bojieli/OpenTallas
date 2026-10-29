set -e
W=/c/wt/die-qc30-1029/results/qc_joint_access_qc30
CEN=/c/die-qc29/formA/census_full/landing_plan.json
CP=/c/codex-qc-mesh5-1029/joint_groups_actual/repair_plan.json
PG=/c/codex-qc-mesh5-1029/census119_h800/pg_rects.json
RP=/c/die-qc29/formA/reserved_power_new.json
python3 $W/phy_stub_plan.py --census $CEN --clock-plan $CP --pg $PG --reserved-power $RP --near-m7 /c/die-qc30/b1/near_phy.json --spacing 0.32 --out /c/die-qc30/b1 > /c/die-qc30/b1/run.log 2>&1 &
python3 $W/phy_notch_plan.py --census $CEN --clock-plan $CP --pg $PG --reserved-power $RP --spacing 0.32 --out /c/die-qc30/b2 > /c/die-qc30/b2.log 2>&1 &
wait
