# Watchdog bench pickup (Codex 10-19 23:11 PT)

Source ec42b1339, staged /srv/opentallas-scratch/claude/s81ctrl-s3-bench2 on ot-epyc5, Verilator 5.050.

- `rg2_exact.log`: nominal PASS, 32 PCs, two phases of 1536 requests; latency max143.25 stream cycles.
- `rg2_pack_wrong_define_NOT_A_MUTANT.log`: historical invalid negative control. Claude launched `S81CTRL_MUT_PACK`; actual RTL tests `S81PH_MUT_PACK`. It passed because no mutation was enabled. Never use this as a fail witness or waive it as equivalent.
- Correct PACK rerun: `S81CTRL_FIFO_IMPL=sram_p192 bash rtl/dsrom_sys/s81_ph/ctrl/run_rg2_bench.sh runs/codex_rg2_mut_pack_correct S81PH_MUT_PACK 1024 1 48 16`. Fleet unit oth-ubuntu-569453-1792476694, client676619, local exec session71899, log /home/ubuntu/scratch/codex-s81-ctrl-coll-pickup-1019/pack_correct.log. Collect actual run.log into rg2_mut_pack.log after terminal FAIL.
- RD/KRDY original clients4131056/4131057 still running; their run.log was empty23:11. Preserve.

No physical or closure claim. Clock kits s3k2/s3k8 still live on ot-pve1; judge all roots. No source RTL changed.
