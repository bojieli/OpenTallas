# MU-ADOPT-KV: the per-user KV row wired into the KV die parents (R6, RELEASE_TREE K.STA.MU / MU.QW.KVATT)

Branch `claude/mu-adopt-kv-1019`, based on `claude/mu-qwen-adopt-1019` (06fa3d55b). Every bench ran on the fleet under
Verilator 5.050, the closure daemon's version. The launcher is `rtl/test/mu_qwen_1018/run_all_kv.sh ROOT OUT`, and
`run_mu_kv.sh ROOT OUT CASE` runs one case. `lists/<case>.f` lists every file a case reads. The logs are in `runs/`.

Static schedule only: nothing here adds a ready, credit or stall. The read map is combinational and the write map is a
bit insertion, so both add 0 edges. A single user runs on the same cycles as today.

## 1. Where the stage user comes from: epoch[1:0] = user

Today the KV die never sees hc pos[17:16]:
- The host root builds TAG59 = {epoch16, stage6, token18, position13, segment6} from position[12:0].
- The layer programme gets `{5'd0, cht[18:6]}`.
- The HBM calendar gets `cal_epoch` / `cal_layer` from the closed group tile (`qkd_kvs_grp`, `qkd_static_kv_phase_launch`).

There are two ways to get a per-stage user to the 128 PC calendars and the writer:
- **New user wires.** Root → layer programme → the closed group tile → 128 PC tiles. That means a closed-tile change and about 300 new die bits.
- **Ride in the epoch (chosen).** Every stage word already carries an epoch: the TAG identity of each KVN word and writer word, `cal_epoch` latched at each layer go, and `static_epoch` registered with every calendar command. Under MU the epoch allocator emits **epoch = {seq14, user2}**, with the user taken from the host step (hc pos[17:16]).
  - No die wire and no closed tile change.
  - The user is latched per stage exactly where the epoch is.
  - It survives a later multi-context layer programme, because the user travels with each stage's epoch.
  - The epoch still identifies a step exactly, and the equality checks are unchanged. A user's sequence wraps at 16,384 steps instead of 65,536; the existing wrap fence covers this.

The host-side half of this contract (the allocator and endpoint MU change) is open. See §3.

## 2. Wiring (opt-in: `OT_KV_MU=1` in the die generator, RTL parameter `MU`; default 0 is byte-identical to today)

| side | where | what |
|---|---|---|
| write | `qkd_kvs_ctl` (RTL-only generated parent; its kit `qkd_kvs_ctl` is not closed) | The writer role binds the new drop-in wrapper `rtl/qwen_sys/mu_qwen_20261018/qkd_kv_static_writer_native_mu.sv`. It contains the **unchanged closed** `qkd_kv_static_writer_native` and `qkd_kv_mu_wrow` on its es lanes (user = es identity[44:43]) and on expected_address (user = expected_identity[44:43]). These sit between the writer and the es fan-out (`qkd_kv_es_fan_root2_b`) / the PCs' native expected-address check. A range fault (a write row ≥ 256) becomes sticky `fault` / `fault_code[7]`. |
| read | `qkd_static_kv_pc_path_nc` (RTL-only parent, inside the `qkd_kvs_pc` / `qkd_kvs_pc_h` tiles, whose kits are not closed) | Parameter `MU`, passed down by `qkd_static_kv_pc_path_fan_nc(_b)` and `_emb_nc(_b)`. The `qkd_kv_mu_rrow` map sits inline between `u_calendar.static_cmd` and `u_ctrl.static_cmd`, with user = `static_epoch[1:0]`. Only KV descriptors (op 0 / 3, row < 256) get row[9:8] = user. It is inline so that every existing source list of the parent stays valid. |
| generator | `tools/qwen_kv_die/kv_static.py` (`MU`, `MU_DEPS`), `kv_static_die.py` | Under `OT_KV_MU=1`: the writer role becomes the wrapper with MU=1, every pc_path gets MU=1, the tile file is `qkd_kvs_tiles_<point>_mu.sv`, and the sources include the leaf and the plain writer. At MU 0 the `MU` parameter is kept implicit, so the existing tile files stay byte-identical. Checked: the regenerated `_hroot_ff_k` differs from the committed one only in a pre-existing `qkd_attn_cal_gen D_QK 28→57` line, which is not from this lane. |
| tile file | `rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu.sv` (kit design point + `OT_KV_MU=1`) | Exactly 3 lines differ from the MU 0 generation: `u_wrn` becomes the `_mu` wrapper with MU 1, and `u_pc` in `qkd_kvs_pc` / `qkd_kvs_pc_h` gets `#(.MU(1))`. |

Closed tiles: **none change**. The closed children (`qkd_kv_static_writer_native`, `qkd_controller_hbm_calendar`, and the
`qkd_ctrl_pc_*` cores) are untouched; the glue sits in the unclosed parents. The kits `qkd_kvs_ctl`, `qkd_kvs_pc` and
`qkd_kvs_pc_h` must be regenerated from the `_mu` tile file when the die adopts MU. `qkd_kvs_pc_h_k1-k1-eb7cbd435` was
submitted at MU 0, so a CLOSED MU 0 view would need an `rtl_change` re-close for MU 1.

## 3. Consumers of hc pos (the user strip)

| die | consumer | today with user on pos[17:16] | status |
|---|---|---|---|
| KV (host root) | `qkd_host_native_token_endpoint_cancel` in **`qkd_hr_core_guard`** | `accept` needs `hc_q[17:13]==0`, so users 1-3 cause `protocol_fault` (fail closed). It is also **single-active**: a second outstanding step causes `protocol_fault`. | **BLOCKER (new RTL)**. Under MU it must check only [15:13], strip [17:16] from pos_q / request_pos, and hold 4 contexts (one per step generation). |
| KV (host root) | `qkd_host_ctrl_token_service_packet_collected` in **`qkd_hr_core_peer`** | Forms the request from hc active[17:0]. Its tags use active[12:0], so the strip is implicit there. | Request position must be [15:0] (strip). |
| KV (die0 coordinator) | `ot_qwen_tp8_token_epoch_allocator` (via `qkd_host_lifecycle_collected`) | `request_position >= 8192` sets `identity_fault`. It is single-busy until the terminal. | **BLOCKER (new RTL)**. Under MU: epoch = {seq14, user = position[17:16]}, range check on [15:0], 4 outstanding. |
| KV | `qkd_static_kv_layer_programme` (`qkd_kvs_ctl`) | authority_position = `{5'd0, cht[18:6]}`, i.e. 13 bits, so it is stripped by construction. It runs **one token at a time** (start → stages → done). | The position is fine. Interleaving 4 users' stages on the KV die needs a multi-context layer programme (the KV analogue of compute-die R1). Open, KV die lane. |
| KV | writer `qkd_kv_static_writer` (identity position13), `qkd_kv_native_programme` (position 13 b) | 13-bit positions from TAG / lprg. | Stripped by construction. |
| KV | legacy `ot_qkvd_kv_seq_merged` (`d_pos(hc[17:0])` → `ot_qfd_dctl`) | Reads all 18 bits. | Not on the static die (the die binds `qkd_seq_static_s`). No action unless the legacy die returns. |
| compute | none reads hc | Position arrives from the KV die (seq `dh`/`ds` tp_pos / ctx_t from the layer programme, 13 b). `native_pos` in `qfd_tt_ctlm_dv` / `qfd_native59_*` comes from there. | Stripped at the source. The compute-die user comes from the compiled calendar (R1 `qfd_dv_cmd_cal_mu` start_user / R3 class-7 USER event), never from pos. Q-DIE15 needs no pos mask. If a future path forwards hc pos to the compute die, it must take [12:0] (or [15:0]) and the epoch's user. |
| host | `qkd_host_ctl` → `ot_qfd_pkgctl` d_pos | It is the producer: MU puts the user on hc pos[17:16]. | Already done (MU-QWEN-HOST). |

## 4. Host MU 1 vs closed tiles: per-tile decision (coordinator rule)

| tile | state on main | MU 1 change | decision |
|---|---|---|---|
| `qkd_host_ctl` | CLOSED (`qkd_host_ctl-hc1-71ffdaf23`) | The `ot_qfd_pkgctl` MU calendar replaces the package controller inside the tile, and the hc user goes on the tile's pin flops. | **Re-close** with a committed `rtl_change` receipt when MU 1 is built. The change is the tile's own function (pin-registered hc / res, the package calendar), so no parent or leaf can hold it. MU 0 is behaviour-identical (13/13 host benches identical). |
| `qkd_hr_core_guard` | not closed (r4 route in flight) | Endpoint MU (above) plus the pins / pb2 chain. | Put the MU endpoint into the next gen_cluster regen **before** this core closes. Same-tile RTL; there is no unclosed parent, because the cluster cores are the hardened parents. |
| `qkd_hr_core_peer` | not closed | token_service request strip (+ the pb2 chain). | As for guard: include it in the regen before close. |
| `qkd_hr_core_prompt` | not closed (p5 route in flight) | pb2 MU_OUT FIFO; prompt address {slot2, pos11} (PLB 11). | As for guard. |
| `qkd_hr_core_order`, `_queue`, `_tx` | CLOSED (order r3, queue r4, tx r2/rr1) | Source text only at MU 0. At MU 1 the pb2 / if_pins chain they carry changes behaviour. | **Re-close with an rtl_change receipt at the MU 1 cluster regen.** Until then leave their pinned sources alone: MU 0 needs no re-gate, and the source drift is text-only. |

So the host MU 1 plane is **not** adoptable by moving logic into unclosed parents. The host-root cores are the
parents, and the endpoint / allocator changes in §3 still have to be written. That is one host-root cluster regen with the MU endpoint, allocator and pb2,
plus re-close receipts for the 4 closed tiles. Owner: the KV host-root lane (HKV-HROOT / HOURLY-KV).

## 5. Benches (Verilator 5.050, fleet ot-epyc4 / ot-epyc5)

| bench | verdict |
|---|---|
| `tb_mu_kv_writer_rows` (write side, the wired role) | **PASS**. 4 users × 36 layers × 8,192 positions, interleaved stage by stage, epoch {seq, user}: 4,718,592 KVN words and 9,437,184 sector writes, all unique (2^27 occupancy map). Each write is inverted to {user = row>>8, layer = row[7:0] − 64, pos, K/V, dim} plus the raw bytes. MU 1 equals the plain closed writer on every output except es row[9:8] and expected_address row[9:8]. The MU 0 wrapper equals the plain writer bit for bit. |
| `tb_mu_kv_pc_path_rows` (read side, through `qkd_static_kv_pc_path_nc`) | **PASS**. The compiled die calendar image (stack 0, PC 13), 3 rounds × 4 users on the same layers, cal_epoch / cal_layer driven with junk after each go. 48 ACTs per user, row = 64 + l + 256u exact, the 4 users' (bank, row) sets disjoint. Every other output, and po outside row[9:8], is in lockstep with MU 0 over 253k checks. Real traffic flowed (6,144 reads / landings / front puts / ring returns) with no fault on either path. |
| `lint_mu_kv_tiles` | **PASS**. `qkd_kvs_ctl`, `qkd_kvs_pc` and `qkd_kvs_pc_h` from the `_mu` tile file elaborate with no Error, PINMISSING, PINNOTFOUND or PINCONNECTEMPTY. |
| MU 0 identity: `tools/qwen_kv_die/kvplan_ci_nc_gate.sh` (existing parent bench: pc_path_nc at default MU 0 in lockstep with the original pc_path under the compiled images of PCs 0 / 45 / 127, jitter, pre-traffic and stress; its 3 mutants observed; parents elaborate) | **PASS** (`runs/ex/kvplan_ci_nc_gate.log`) |
| MU 0 / leaf: `tb_qkd_kv_mu_rowoff` (MU-QWEN-HOST) | **PASS** (unchanged) |

Mutants (each applied to a copy of one RTL file by `run_mu_kv.sh`; all FAIL; the witnesses are in `runs/mut/`):

| id | mutation | fail regex (witness) |
|---|---|---|
| mw1 | writer wrapper: user not inserted into the es rows | `FAIL user. layer0 pos0 errors272 nalias8` |
| mw2 | writer wrapper: expected_address keeps today's row | `FAIL user1 layer0 pos0 errors8` |
| mw3 | writer wrapper: user from TAG stage bits [38:37] | `FAIL user. layer0 pos0 errors272` |
| mk1 | pc_path_nc: user not inserted | `FAIL MU_KV_READ_ROWS act_bad=144 disjoint_bad=288` |
| mk2 | pc_path_nc: user from static_epoch[2:1] | `FAIL MU_KV_READ_ROWS act_bad=96` |
| mk3 | pc_path_nc: user from the live cal_epoch pin (not stage-latched) | `FAIL MU_KV_READ_ROWS act_bad=96 disjoint_bad=64` |

## 6. Open (owners named in the lane files)

1. Host root MU 1 RTL (§3, §4): endpoint with 4 contexts and the strip, and the allocator epoch {seq14, user2}. Owner: HKV-HROOT.
2. KV die stage interleave: a multi-context `qkd_static_kv_layer_programme` and writer programme. Owner: KV die lane, the KV analogue of R1. Without it the KV die serves one token's stages at a time, and the static calendar must keep users' KV stages serial on the KV die.
3. KV die GEN under `OT_KV_MU=1`, and a regen of the kits ctl / pc / pc_h from the `_mu` file. Owners: HKV-DIE / KV-KITS.
4. Compiler: `mu_calendar` must state the epoch convention (epoch[1:0] = user) in the bench-case emitter and the kv receipts.
