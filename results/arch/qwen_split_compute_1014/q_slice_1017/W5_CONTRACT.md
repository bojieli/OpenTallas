# Q-SLICE W-column / slice interface contract (dv2f7, 10-17)

Coordinator decision 0de: the slice lateral direction is a COMPILE-TIME choice. There are two hardened, mirrored variants, with no boot-learned muxes.
Slice RTL: `rtl/qwen_dv/qfd_dv_slice2.sv` (core, parameter DIR) plus the wrappers `qfd_dv_slice2_w` (DIR=W, die W row, R0) and `qfd_dv_slice2_e` (DIR=E, die E row, placed MY). Branch `claude/qslice-1017`.

## Faces
Ports are named `<kind>_<face><dir>`, with face in {w, e} in MASTER coordinates.
- The dn face (toward W5 and the W column) is `w` in the W variant and `e` in the E variant. Under MY it lands on the die W side.
- The up face is the other one.
- Fixed in both variants: `l9_wi`, `l9_eo`, `rs_n0/n1` (N, 514 b: cluster near `rs` / far `rs_o`), `rs_s0/s1` (S), `cw_n0..3` / `cw_s0..3` (516 b), `ck` and `rst_n`.

| kind | dn face | up face | bits | meaning |
|---|---|---|---:|---|
| cmd | in | out | 116 | slice command chain. tt_ctlm feeds W5. |
| hr | in | out | 453 | `{ib 380, xpf 72, v}`. tt_ctlm feeds W5. |
| st | out / in | in / out | 1088 | neighbour stream: `st_dn` leaves on dn, `st_up` arrives on dn |
| sc | out / in | in / out | 48 | scalar chain, both ways |
| arv / ard / arl / arm / art | out | in | 1 / 512 / 1 / 1 / 32 | outbound AR word, exactly the collective `in_valid / in_data / in_last / in_mode / in_tag` |
| rv / rd / rl / rr / re | in | out | 1 / 512 / 1 / 3 / 1 | AR return, exactly the collective `out_valid / out_data / out_last / out_rank / out_err` |
| dd | out | in | 548 | D2D word `{v, kind 2, mask 8, 8 x addr 24, 8 x FP32, 89 x 0}` (kind 0 q/act, 1 K, 2 V) to native59 |
| dr | in | out | 520 | D2D return `{v, group, beat 6, data 512}`. group 0 = attention result, landed at `dd_base`; group 1 = embedding row word, landed at `em_base + 16k` |
| ag | out | in | 10 | status aggregate chain, an OR over the slices: `{stn_busy, any, su, vm, stn, sc, stm, port fault, su_busy, root_busy}`. Zero is the identity. |
| ss | out | - | 107 | this slice's status `{ar_land, tok_val 32, sid 4, any, su, vm, stn, sc, stm, port, su_idle, sc_busy, su_prog 16, su_rows 16, ar_rank 3, ar_last, tok_v, tok_idx 24}` |
| ccv / ccm / ccw / cct | out | - | 1 / 1 / 16 / 32 | collective command, exactly `cmd_v / cmd_mode / cmd_words / cmd_tag`. Issued by cmd kind 0 (XC) |

## New slice functions (Q-SLICE producers)
- **XC (cmd kind 0), sub `[5:4]=0`, COLL.** mode `[6]`, words `[22:7]`, tag `[54:23]`. The addressed slice (W5) registers it onto `ccv/ccm/ccw/cct` for one edge. Other subs raise a port fault. This produces G5: tt_ctlm's command calendar issues every collective command on the same timing base as the slice commands. `cmd_free` stays observation only (sys_face `io_cmd_free`, already wired).
- **AR mode (G4).** Station AR words carry mode 0 (all-reduce). AMAX (kind 6) bit `[6]` = ARX: when the root's die-wide argmax completes, the root emits one AR word with `{v, tag = {8'd0, idx}, mode 1, last 1, data = {.., idx 24 @[55:32], val 32 @[31:0]}}`. This is the q3h K_ARGMAX record.
- **Cross-die argmax gather.** AMAX bit `[7]` = GATHER: the next AR returns (one per rank, in rank order) are merged on every slice, on the return chain, instead of being landed in the VM. The merge picks the strictly greater okey, and on a tie the earlier rank wins, as q3h does. On `rl` (last) the merged index becomes `tok_v/tok_idx` in `ss`. tt_ctlm reads the next token from W5 `ss` (G9 token id).

## W-column masters (re-port owners)
- **native59 (Q-N59):** `dd_i[547:0]` <- W5 `dd_wo`; `dr_o[519:0]` -> W5 `dr_wi`. It also merges the embedding row as group-1 `dr` words: `emb_code_re/addr 24`, `emb_scale_re/addr 18` -> embed_prov; `emb_code_q 512`, `emb_scale_q 16` <- embed_prov. The fetch is triggered by a native_cmd kind from tt_ctlm. The pre-DV `kv_we/kv_waddr/kv_wdata/native_issue/q/q_committed/q_fault/write_commit_*` ports go away.
- **tt_ctlm (Q-CTLM):**
  - outputs `hr[452:0]` and `cmd[115:0]` -> W5 `hr_wi/cmd_wi`;
  - inputs `ss5[106:0]` <- W5 `ss_wo` and `ag5[9:0]` <- W5 `ag_wo`;
  - outputs `emb_start` and `emb_token[17:0]` -> embed_prov `core_start/core_token`;
  - a static command calendar (program-loaded, no readiness) issues the cmd words;
  - the pre-DV am/tc/lc/rf/uf/mx/mee/meok/ld/st/xs/xm/su_*/cp/sel/rsi_me_*/mer/xflt/b2_status ports go away.
- **sys_face (Q-CTLM or Q-SYSF):**
  - `crom_fault_code` / `seq_*` observation come from tt_ctlm (which sees `ag5` and `ss5`);
  - `res_issue_fault` is dropped.
- **io_collective:** unchanged class-A ports: `in_*` <- W5 `ar*_wo`, `out_*` -> W5 `r*_wi`, `cmd_*` <- W5 `cc*_wo`.

## Chain-end idle inputs (rule (c), straps manifest)
- **W5:** `st_wi`, `sc_wi`.
- **E5 (E variant, up face = w):** `arv/ard/arl/arm/art_wi`, `dd_wi`, `st_wi`, `sc_wi`, `ag_wi`.
- `l9_wi` of an unpaired slice.

All are zero = "no word".
