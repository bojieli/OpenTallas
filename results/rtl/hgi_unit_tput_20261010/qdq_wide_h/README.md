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

## c43d6a389 (el1011-hbm-fq 10-12 [idle1012-qw]): registered face (class 3 fix of ha/hb-adc3fb5d8 EARLY_FAIL_HOLD)
Pure face flops on every input (incl. rst_n -> reset relay) and output, child pins fed only from face/staging flops, unconditional command shift, two-stage tile event relays; ot_hgi_quant_unit WQ=2 waits one more state for idle. Same gate (WQ=2, Verilator 5.032, ot-epyc4): m0 PASS 3,328 words exact (743 cycles / 8 records, priced 168), w3 PASS (2,319), m1 FAIL (record 0 fault), w1 FAIL (2,898 of 3,328 words mismatch) -> QDQ_WIDE_TPUT GATE PASS. +56 cycles over 8 records (+7 a record of fixed latency: face flops on go / requests / responses / credits / write beats / grants and the second event relay); rate one beat a cycle unchanged. Logs in this directory are the c43d6a389 run.
