cd /srv/opentallas-scratch/claude/redesign-hbm/smcg4/src
python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 4 --smh --cg --cg-gap 300 --build-jobs 12 --workdir /srv/opentallas-scratch/claude/redesign-hbm/smcg4/w_gap --out /srv/opentallas-scratch/claude/redesign-hbm/smcg4/gap.json > /srv/opentallas-scratch/claude/redesign-hbm/smcg4/gap.log 2>&1 &
python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 4 --smh --cg --cg-mut-late --cg-gap 300 --build-jobs 12 --workdir /srv/opentallas-scratch/claude/redesign-hbm/smcg4/w_late --out /srv/opentallas-scratch/claude/redesign-hbm/smcg4/late.json > /srv/opentallas-scratch/claude/redesign-hbm/smcg4/late.log 2>&1 &
wait
grep -h 'CG_LOCKSTEP\|CG_MISMATCH' /srv/opentallas-scratch/claude/redesign-hbm/smcg4/w_*/*/runtime.log | head -20
