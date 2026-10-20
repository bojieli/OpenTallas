#!/bin/bash
# S81-DIE10 10-20: replaces the ROOT-held DIE9 waiter (PID 3852152).  On n32s CLOSED: native CTRL re-export from the
# daemon route (verdict replay, --require-check, --forwarded-clock clk:ck_o); if the CTRL view bytes equal the pre-record
# view already in chain mu6n_pre (12c132d60) -> log "identical, mu6n_pre stands" (no duplicate chain); else commit the
# checked view on claude/s81-die10-1020, push, and launch chain mu6n_rec (ot-run --priority die, unpinned by --dir).
J=/home/ubuntu/.local/state/closure_loop/jobs/s81ctrl_rg2_n32s-n32s-f1f7c42d9.json
LN=/home/ubuntu/claude-takeover-20261007/lanes; L=$LN/s81-die10-mu6n-waiter.log
WT=/home/ubuntu/wt/s81-die10-1020; V=physical/ref_tile/s81ctrl_rg2_n32s/views/dsfd_ctrl_rg2
R=/srv/opentallas-scratch/claude/closure-loop/s81ctrl_rg2_n32s-n32s-f1f7c42d9
X=/srv/opentallas-scratch/claude/s81-die10/ctrlrec
echo "$(date +%H:%M) waiter start pid $$" >> $L
while true; do
  st=$(python3 -c "import json;print(json.load(open('$J'))['status'])" 2>/dev/null)
  case "$st" in
    CLOSED) break ;;
    RUNNING|READY|ECO|QUEUED|WAITING|"") sleep 300 ;;
    *) echo "$(date +%H:%M) n32s terminal $st -> no record chain; mu6n_pre stays a pilot, structural CTRL fix needed" >> $L; exit 3 ;;
  esac
done
echo "$(date +%H:%M) n32s CLOSED" >> $L
ssh ot-epyc5 "mkdir -p $X && cp /srv/opentallas-scratch/claude/s81-die10/ctrlpre/view_export.py /srv/opentallas-scratch/claude/s81-die10/ctrlpre/run_ctrlpre.sh $X/ && sed -i 's#--forwarded-clock clk:ck_o#--forwarded-clock clk:ck_o --require-check#' $X/run_ctrlpre.sh && test -d $R/routes" \
  || { echo "$(date +%H:%M) daemon run dir gone on ep5 -> export from closed_archive by job replay (manual)" >> $L; exit 4; }
/home/ubuntu/bin/ot-run --mem 16 --threads 2 --no-spill --dir $X -- bash $X/run_ctrlpre.sh > $LN/s81-die10-ctrlrec.otrun.log 2>&1
grep -q "ot-run: RAN on .*exit 0" $LN/s81-die10-ctrlrec.otrun.log || { echo "$(date +%H:%M) CTRL record export FAILED (see s81-die10-ctrlrec.otrun.log)" >> $L; exit 5; }
T=$(mktemp -d); rsync -a ot-epyc5:$X/views/ $T/
same=1; for f in dsfd_ctrl_rg2.lef dsfd_ctrl_rg2_tt.lib dsfd_ctrl_rg2_ff.lib dsfd_ctrl_rg2_ss.lib; do cmp -s $T/$f $WT/$V/$f || same=0; done
if [ $same = 1 ]; then echo "$(date +%H:%M) CLOSED-record CTRL view byte-identical (LEF + 3 libs) to mu6n_pre view -> mu6n_pre stands, no second chain" >> $L; rm -rf $T; exit 0; fi
[ "$(git -C $WT rev-parse --show-toplevel)" = "$WT" ] || { echo "WT check failed" >> $L; exit 6; }
rm -rf $WT/$V && mkdir -p $WT/$V && cp -a $T/. $WT/$V/ && rm -rf $T
git -C $WT add $V && git -C $WT commit -q -m "S81-DIE10 mu6n: n32s CTRL view from the CLOSED daemon route (verdict replay, checked, native clk->ck_o)

Gate-Rule: neutral

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git -C $WT push -q origin claude/s81-die10-1020 || { echo "commit/push failed" >> $L; exit 7; }
C=$(git -C $WT rev-parse HEAD); echo "$(date +%H:%M) CTRL record view committed $C -> chain mu6n_rec" >> $L
/home/ubuntu/bin/ot-run --priority die --mem 110 --threads 16 --disk 80 --dir /srv/opentallas-scratch2/claude/s81-die10 -- \
  bash /srv/opentallas-scratch2/claude/s81-die10/run_mu6n.sh chain $C $C mu6n_rec > $LN/s81-die10-mu6n_rec.otrun.log 2>&1
echo "$(date +%H:%M) chain mu6n_rec ot-run rc $?" >> $L
