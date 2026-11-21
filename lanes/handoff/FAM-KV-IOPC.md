# FAM-KV-IOPC handoff (11-20 23:5x PST)
Work dir epyc8 /srv/opentallas-scratch2/claude/fam-kv-iopc (br1 = bank_reset_delta io_cor_v1 on D27c plan 19af3841ef74; bd.sh/pk.sh scripts; tree_a1 = linked private tree).
Rep: kv3_io_cor_v1. Fix = plan reset.bank_taps 41 rows (br1/plan_out.json, report.json), hop max 165.7 um.
Pipeline: bd.sh a1 (private bind) -> pk.sh a1 kv3_io_cor_v1 <plan> cts (kit-rtl needs green global bind) -> read post-hook CTS.
Then rows to KV-PLAN-R3 (D27/D28), siblings: kv3_io_cor (cancelled), pc rows are KV-PLAN-R3-owned (held until D27 apply).
