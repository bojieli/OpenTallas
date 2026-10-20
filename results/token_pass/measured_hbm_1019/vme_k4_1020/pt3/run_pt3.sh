#!/usr/bin/env bash
# run_pt3.sh N TAG : PRETREE3 primary row (m_pt3_tp8, census --measured --bw 98 --bridge 1) + vmearly OT_VME_N=N, tok/s by tok_from_sched
cd "$(dirname "$0")"
OT_VME_BLDMA=all OT_VME_N="$1" PYTHONPATH=tools python3 -m hgi_sim.toksim_vme_compose_1020 --measured m_pt3_tp8.json --bw 98 --bridge 1 --out out/$2.json > out/$2.log 2>&1
echo "$2 rc=$? $(python3 out/tok_from_sched.py out/$2_jobs)"
