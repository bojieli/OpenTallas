#!/bin/bash
# after replay_p55.sh: package part 55, commit, push branch, post the numbers. Detached; survives the session limit.
R=/srv/opentallas-scratch2/claude/hbm-cons-2-suk; cd $R/repo || exit 1
for i in $(seq 1 480); do grep -q "REPLAY DONE" $R/logs/replay.log && break; pgrep -f "replay_p55.sh $R/rr" > /dev/null || break; sleep 15; done
F=results/die_hbm_1106/suk_vk; S=NOT_DONE; grep -q "REPLAY DONE" $R/logs/replay.log && S=DONE
PK=not-run
if [ $S = DONE ]; then
  PK=$(bash $F/pack_p55.sh $R/rr 2>&1 | tail -5 | tr '\n' ' ' | cut -c1-300)
  git add physical/die_plan/hbm/plan_of_record/d44v
  git commit -q -m "HBM-CONS-2/SUK: d44v part 55, SU lane edge-column form, packaged after replay

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
  git push -q origin HEAD:refs/heads/claude/hbm-cons-2-suk-1106
fi
SHA=$(git rev-parse --short=10 HEAD)
L="- $(date '+%Y-%m-%d %H:%M') PST STATE [HBM-CONS-2/SUK chain -> HBM-CONS-2, DIE-HBM-83, COORD] script post, nobody has reviewed this. replay=$S branch claude/hbm-cons-2-suk-1106@$SHA pack: $PK G0: $(tr '\n' ';' < $R/rr/g0.txt | cut -c1-900) GEOM: $(tr '\n' ';' < $R/rr/geom.txt | cut -c1-600) [CHECKED intel2 $R/rr/g0.txt geom.txt]. Plan owner must read G0/GEOM before calling this READY."
cd ~/coord && echo "$L" >> lanes/COORD-REVIEW-QUEUE.md && timeout 280 ~/coord/bin/coord-commit.sh "HBM-CONS-2/SUK: chain STATE" lanes/COORD-REVIEW-QUEUE.md
