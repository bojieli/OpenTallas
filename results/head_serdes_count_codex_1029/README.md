KP4 root-count timing candidate (2026-10-29)

Original actual CTS FAIL: ce1[9] -> nrc[5] setup -181.99ps at833ps TT,
60ps uncertainty. Top five paths share the last-chunk mask -> root counter.
Typed pin-clock insertion itself PASS240ps mean vs250 target; this does not
qualify negative setup. Original report/JSON are preserved beside this file.

Candidate55ed628aa is based on current main b5c9faba0. No registers, reset,
port/interface or latency changes. The six nonexistent last-chunk positions
49..54 are counted separately and their subtotal is masked at the final add.
The49 always-valid positions use3:2 carry-save compression. Each compressor
preserves sum modulo64: a+b+c = (a^b^c)+2*((a&b)|(a&c)|(b&c)). The generated
row counts49,33,22,15,10,7,5,4,3,2 cover each incoming vector once. Initial
sum<=49, final sum<=55; modulo64 is therefore the exact six-bit root count.
The existing crc correction-mask expression and nrc output register remain.

Runtime evidence is being collected under intel2:
/srv/opentallas-scratch2/claude/codex-head-count/exact1
unit oth-ubuntu-845443-1793263874,12GB/6threads through ot-run.
The bench compares all actual DCHN outputs cycle-for-cycle to the frozen
b5c9faba0 module and retains the real omitted-Forney-division MUT2 control.
A separate full56-input SAT count miter compares the exact old mask/tree
with the new count, capped300s. A timeout means UNPROVEN, never PASS.

No physical timing improvement, full mapped LEC, route or SIGNED claim.
Original full mapped LEC and kit5 CTS/GRT jobs continue unchanged. The candidate
must receive source review and its own actual mapped timing before adoption.
