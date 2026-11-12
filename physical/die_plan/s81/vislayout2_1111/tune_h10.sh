cd /srv/opentallas-scratch2/claude/vislayout2-s81/w; S=/srv/opentallas-scratch2/claude/kw43/src_t51f_pbp_por15c_por36; T=../tools; R=../repo
TS="col_h10_r2__t1__cl1f5d6c2a col_h10_r2__t1__cl99efd374 col_h10_r2__t1__cl8b686b3e col_h10_r2__t1__clac068e56"
cp aug4/plan_h10r2.json aug4/plan_h10r2_t.json
for t in $TS; do python3 -I $T/taptune.py $S aug4/plan_h10r2_t.json $t aug4/plan_h10r2_t.json L | grep legalise; done
for t in $TS; do echo "## $t"; python3 -I $T/taptune.py $S aug4/plan_h10r2_t.json $t aug4/plan_h10r2_t.json 2>&1 | grep -E "^legalise|^now|^round|^final|Trace|Error" | cut -c1-400; done
sha256sum aug4/plan_h10r2_t.json | cut -c1-12; echo TUNE10_DONE
