Current SYS HC production measurement

Current scalar HC.HC_MIX_POST sustains its unchanged production budget: 540 record-to-retirement cycles / 540 budget cycles = 1.000, within the 1.10 threshold. The existing source-pinned c4 SYS bench includes production DeepSeek D5120 scalar POST case 15 (24 input mixes, 24 output words, one position, 20 Sinkhorn iterations). No new build or vectors were needed.

The complete existing bench passes 18 records with 693 golden output words checked. MP, POST and XL mutants fail with 418, 84 and 255 errors respectively. Source manifest hashes match runtime source commit 550082537 for the 39 listed script, RTL and golden files; generated vector hashes are included. The positive and three negative logs and closure bench handle records are retained.

This qualifies the scalar 24-mix tail (sigmoid/exp/Sinkhorn) throughput and correctness only. It does not establish physical closure, nor qualify residual vector FUSED.HC_POST, full HC_MIX or HC_MIX_ROWS. Existing historical 1.282 throughput evidence remains unchanged. The wrapper parameters are SYS1 W32 RMAX128 SPL4 WMACRO1 XMACRO1 with 32 HBM lanes; the routed bank tile is replicated eight times and contains four hardened HCP lane groups.
