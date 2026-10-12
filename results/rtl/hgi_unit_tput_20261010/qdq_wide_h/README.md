# FUSED.QDQ wide, hierarchical (ot_hgi_quant_wide_h, WQ=2): exact + rate gate

Source: claude/el1011-hbm-fq 53eba91c4 (command relay + registered status pins + per-half write relays; the f1728b0d2 run gave 85 cyc at n 512). Gate `WQ=2 tools/hgi_unit_tput/run_qdq_wide.sh` (Verilator 5.050, ot-epyc3) on the 8
DS-shape vectors (`/srv/opentallas-scratch/claude/hgi-tput-1010/vec/qdqvec`).

| run | role | result |
|---|---|---|
| m0 | design | PASS, 3,328 words exact |
| w3 | forced packet path (control) | PASS |
| m1 | header A-bit mutant | FAIL (fault), as required |
| w1 | lane-to-sector mutant | FAIL (MISMATCH), as required |

Rate: one 32-element beat a cycle (unchanged). Fixed latency +20 cycles a record against ot_hgi_quant_wide (n 512: 87 vs 65;
n 128: 73 vs 53; 8 records 663 vs 503): relay registers on the long seams, registered tile seams, 2-level gather OR, the
decode tile's input/output flops and the SRAM result FIFO's read + capture.


## adc3fb5d8 (el1011-hbm-fq 10-11 23:58): vector credit checks, write-head lookahead, registered SRAM read issue
Same gate (WQ=2, Verilator 5.032, ot-epyc4): m0 PASS 3,328 words exact, w3 PASS, m1 FAIL (fault), w1 FAIL (MISMATCH) -> QDQ_WIDE_TPUT GATE PASS. 8 records 687 cycles (was 663 at 53eba91c4: +3 a record of fixed latency), rate one beat a cycle unchanged. Logs in this directory are the adc3fb5d8 run.
