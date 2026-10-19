# Production programme recovery

The hardware image ABI is a measured blocker. `tb_qready_capacity.sv` instantiates
the exact `0d4c9808f` release `qfd_dv_cmd_cal_mu` with NU4, CTX_DW1, UFOLD1,
UVM_STRIDE4096, PIDX_STRIDE128 and its real two SRAM macros and write observer.
It streams all1024 PW and8 DW in legal order, with ME meta_rows30/base480.
The positive descriptor with248 entries seals ready without a fault. The249-entry
mutant and the recovered390-entry full-decode lower bound both fault at seal,
fault_code0x10 (bit4), image_ready0. This does not execute fabricated commands;
the rejected descriptor cannot seal regardless of entry contents.

The release ABI computes `base + 2*nent <= 976` and `base >= 16*meta_rows`.
Thus248 entries is the maximum at base480. The immutable full lowering at
`4e718c010:results/rtl/qlb_c4b_1018/clayer2/layer_s1.json` contains390 decode
entries and estimates21 boot entries,72 PROG+188 BTAB+528 per-layer CROM chunks,
4 per-token RoPE chunks. Even removing all table payloads leaves at least
480+2*390=1260 PW; the complete archived estimate is13910 PW. Its artifact
remains analytic and old-die scoped; these counts are not a performance claim.
Current TLOAD uses a6-bit row in this same store and rejects rows>=61 and overlap
with ME/calendar regions. A compiler cannot emit that lowering into this ABI.

Required RTL owner work (handed to `qwen_programme_capacity`): a distinct static
calendar/payload source with enough actual macro capacity, source identity and
boot/witness ABI; preserve the ME1024-word image and reserved metadata; give each
layer its exact PROG/BTAB/CROM payload and each token its exact RoPE row; fixed
load-to-use edges and exclusive table write ownership; pin/fetch latency passed
to the compiler. Table-only migration cannot solve the calendar overlap.
No seal bound is relaxed by this change.

`recover_q_trace.py` recovers existing full12-slice native stage logs from
`ot-epyc5:/srv/opentallas-scratch/claude/qw-realstg` read-only. L0 andL1 each
contain512 unique Q seats and64 Q words, bit-exact vs the real P8191 ISA golden,
with all96 Q/K/V output edges matching the same compiled lowering origin.
Their exact words, seat writes, per-beat last producer edges, source input SHA256
values and limitations are committed in `L0_q_trace.json` and `L1_q_trace.json`.
This recovers useful actual RTL data, **not production admission**: QKV/r are
bench-landed real operands, direct slice commands bypass controller PW/DW, the
source predates release and no production layer origin/request calendar exists.

Fleet units: capacity1546858 (2GB/2threads), recovery1550873 (1GB/1thread),
Verilator5.050. Both exit0; logs and version committed. No original run modified.
