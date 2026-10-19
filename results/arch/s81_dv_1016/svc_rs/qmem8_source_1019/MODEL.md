# SVC qmem eight-bank source prototype: pre-code model

Actual parent is dsdv_svc_att at 53ccd5927, storage model 83c2428ca.
8192 useful bits = sixteen 512-bit heads. Each edge can write one whole head
at {f_hdr[448],f_idx[6:4]} when q_word; every edge reads 4'(rc-1).
Eight single-clock ot_sram_1r1w_32x64_m1 banks take identical 5-bit
addresses {0,head}, write enable and mask64=all ones. Each holds one
64-bit slice. Capacity16384 bits; unused rows16..31 never addressed.
Eight native registered outputs replace the existing eq_w register, with
no added payload register: intended added edges0, eight clock contacts,
raw area4419.25632um2. Macro area552.40704um2; shape31.968x17.28um.
Source family b65718325 (and reviewed qualification7549fae73), immutable
behavior/LEF/Lib hashes in storage_model_1019/model.json. This single-clock
behavior reads before writing in one process and explicitly defines OLD.
No dual-clock behavior or repair/ECC promise is substituted.

For edge E: macro and legacy sample address from pre-edge rc-1, then
publish old addressed data after E; engine consumes their published word
at E+1 alongside pre-edge eq_v. Write to that address at E returns old
word after E and new word after E+1 if read address holds. No prefetch,
extra read edge, output holding register, artificial lane stage or wait.
Physical registered boundary is the macro rd_out itself.

Payload is not reset. Reset only cancels parent run/eq_v/q_have/job state;
existing payload remains occupied. Only heads completely written since
job start may be consumed; the actual parent currently checks q_have==16
at GO, not per-head identity. Prototype does not silently strengthen that
parent contract. Bench separately proves unique all-sixteen loading and
shows early/partial consumption fails its lifetime assertion. All reads
before first write are unqualified and excluded, including during reset.
Random arbitrary physical payload (including unused rows) is explicitly
seeded independently; no zero initialization supports correctness.

Minimum bench contains the actual read/write block extracted mechanically
from parent source, the candidate module and immutable native behavior.
No engine arithmetic is copied or rebuilt. It tests all sixteen distinct
nonzero heads, all address wrap transitions, gaps, same-address OLD,
occupied reset with invalidation, and consecutive jobs with fresh payload.
Causal mutants alter actual candidate read address (wrong head/early next
head), delay output one edge, bypass OLD on collision, and overwrite wrong
head; unchanged checks must reject each. Use Verilator5.050 on unpinned fleet.

This is a source prototype, DEFAULT OFF. Other large queues, 32 dense old
SRAMs, SM/G9 destination, all-driver fanout, clock/PG/native timing, legal
43.2-lattice whole-slot packing and throughput/token composition remain
OPEN. No physical gate or full SVC build is authorized by this model.
