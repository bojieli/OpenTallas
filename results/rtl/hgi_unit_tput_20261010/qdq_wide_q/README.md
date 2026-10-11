# FUSED.QDQ wide, lane-quad structure (ot_hgi_quant_wide_q, WQ=1): exact + rate gate

Source: claude/el1011-hbm-fq 18c0f26d8 (RTL ff0e12c3f). Gate `WQ=1 tools/hgi_unit_tput/run_qdq_wide.sh` (Verilator 5.050, ot-epyc3)
on the 8 DS-shape vectors (`/srv/opentallas-scratch/claude/hgi-tput-1010/vec/qdqvec`, qdq_vectors.py).

| run | role | result |
|---|---|---|
| m0 | design | PASS, 3,328 words exact |
| w3 | forced packet path (control) | PASS |
| m1 | header A-bit mutant | FAIL (fault), as required |
| w1 | lane-to-sector mutant | FAIL (MISMATCH), as required |

Rate: one 32-element beat a cycle, as ot_hgi_quant_wide. Fixed latency +6 cycles a record (n 512: 71 vs 65; n 128: 59 vs 53;
8 records 551 vs 503) from the registered hit-vector decisions, quad gather, write relays and credit relays that make the block
closable across an 800 um lane face. The WQ=0 control on the same tree gives the old 503 cycles and the same PASS / FAIL pattern.
