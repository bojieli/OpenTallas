cd /srv/opentallas-scratch/claude/redesign-hbm/smcg4/src
python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 4 --smh --cg --cg-mut-late --cg-gap 300 --build-jobs 12 --workdir /srv/opentallas-scratch/claude/redesign-hbm/smcg4/w_late --out /srv/opentallas-scratch/claude/redesign-hbm/smcg4/late.json > /srv/opentallas-scratch/claude/redesign-hbm/smcg4/late.log 2>&1 &
python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 4 --smh --cg --cg-mut-hold0 --cg-gap 300 --build-jobs 12 --workdir /srv/opentallas-scratch/claude/redesign-hbm/smcg4/w_h0 --out /srv/opentallas-scratch/claude/redesign-hbm/smcg4/h0.json > /srv/opentallas-scratch/claude/redesign-hbm/smcg4/h0.log 2>&1 &
wait
grep -h 'CG_LOCKSTEP' /srv/opentallas-scratch/claude/redesign-hbm/smcg4/w_late/*/runtime.log /srv/opentallas-scratch/claude/redesign-hbm/smcg4/w_h0/*/runtime.log
