cd /srv/opentallas-scratch2/claude/kving8/wt
R=results/kv_ing_vh2_1107/bench/run_ing4.sh; O=../bench; L=../bench_out; : > $L/more.txt
one(){ m=$1; for s in $(seq 5 40); do r=$(REUSE=1 timeout 600 bash $R $O $m +seed=$s +pm=0 +nd=200 +cycles=2000000 2>&1); if ! echo "$r" | tail -1 | grep -qx PASS; then echo "$m DETECTED pm0 nd200 s$s: $(echo "$r" | grep -v PROGRAM | head -1 | cut -c1-100)" >> $L/more.txt; return; fi; done; echo "$m SURVIVE 36 seeds nd200" >> $L/more.txt; }
for m in m_qdblk m_rowfl m_elast m_slraw m_slsc m_slp0 m_mbq; do one $m & done; wait; echo END >> $L/more.txt
