# Qwen KV die: the static die's boot paths into HBM (RTL-BUILD-KV/BOOT, 2026-10-18)

Lane RTL-BUILD-KV items P1 + P2. Base: `claude/rtl-build-kv-1018` (= `claude/kvj-g2-1017` 283be4b3a). Status: **RTL and
benches built. This is a design review stop.** No kit was submitted and no gate was run, because no new hard leaf
was added.

## 1. What the legacy paths carried

On the legacy (credit) KV die, every HBM write that was not a runtime KV write went through the per-PC HOST slice.
The slice is `qkd_host_pc_slice_die`, x128, and it sat in series between the landing strip and the controller.

| face | width | legacy producer -> consumer | what it carried |
|---|---|---|---|
| `fi`/`fo` (+ `ci`/`co`, `ai`/`ao` reverse) | 291 | HOST root `chain_f` -> slot chain | **HOST ingest writes**. The host map (`qkd_host_ingest_map`) maps KV sectors (rows 64..99) *and* embedding sectors to `{data, row, col, bank, lpc}`. The station of the matching lpc consumes the word as `host_es`. Credits go back on `co` and real write acks on `ao`. |
| `land_es` | 288 | `qkd_land` strip -> slice | Embedding traffic. This was the **boot writes of the embedding table** (`ot_qfd_emb_strip` BOOT_WR, credit per PC) plus the runtime embedding reads. |
| `ctrl_es` | 288 | slice -> controller `es` | `qkd_hbm_boot_static_completion`. Before boot it carries the **cold-boot scratch check** (`qkd_hbm_boot_pc`: write and read back bank 3, column 2, row 0, twice). After the check passes it carries the `qkd_host_static_pc_emback` 2:1 credit arbitration of {landing, host}. Normal traffic is gated until the check passes. |
| `ctrl_er` / `land_er` | 261 | controller -> slice -> strip | The read-back of the check, controller credits (er[259]) and landing data. |
| `ctrl_completion_v/we` | 1+1 | controller -> slice | The ownership ledger: boot-owned retirements go to the check. Normal retirements become `host_ack` (on the `ao` chain) or `land_ack`. `all_ack` goes on the `sko` status chain to the HOST commit-order ledger (`qkd_host_boot_dispatch`). |
| `bgi`/`bgo`, `sk/sd/so/sf` | 1, 4x32 | chains | `boot_go` and the per-PC {ack, boot_done, boot_ok, boot_fault} status. |

The embedding image went `host -> qkd_host_boot_dispatch` (E >= 2^31 -> `hb`) -> `qkd_embgw_boot` -> `emf_<q>` BOOT_WR ->
strip -> PC `land_es`. The strip counted the words and summed `crc_sector(E, data)` as it issued them. BOOT_END came
back as STATUS on `emr_<q>`, and the gateway raised `est[0]` emb_ready when the sums matched. The HOST dispatcher sends
BOOT_END only after its ledger has retired every boot write's real completion. That retirement comes from `land_ack`,
so it needs the slice. The HOST boot barrier releases the certificate only on emb_ready.

On the static die, `es_merge(writer, embedding read)` drives the controller directly, and the strips and ctrl strips
are gone. As a result, the slice's `land_es` has no producer and its `ctrl_es` / `land_er` have no consumer (P1). The
gateway's `emf/emr` have no far end, so emb_ready can never rise (P2). Four paths into HBM are lost:

1. HOST KV ingest writes.
2. The embedding table load.
3. The cold-boot scratch check, together with its normal-traffic gating.
4. The completion acks that the HOST ledger waits for.

## 2. Candidates

| candidate | verdict |
|---|---|
| (a) Slice in series: es_merge -> `land_es` -> slice -> `ctrl_es` -> controller | **Rejected.** It puts the slice's credit arbitration (`emback`: 4-deep queues, choose / launch, at most 1 launch per 2 edges, a shared credit pool) on the runtime writer and embedding paths. That is a dynamic stall on the production path (owner 10-14). It also adds about 6 edges on es and 4 on er, which would land in the critical return slots. |
| (b) A per-stack static boot writer with its own PC delivery (a new 32-hop chain or a fourth es source) | **Rejected.** Its words would bypass the slice, so the HOST ledger never gets their acks: the dispatcher's 256-outstanding window fills and the marker is never released. A new 288-b x 32-hop chain per stack would also be needed. |
| (c) Retire the gateway and send the image down the HOST ingest chain (the map already maps it) | **Rejected.** It changes `qkd_host_boot_dispatch` inside the hard HOST root. emb_ready would still need a die producer, and the image checksum would be lost. |
| **(d) Slice in PARALLEL as the boot owner + the image on the existing static PC chain** | **Chosen.** No new long wiring, the slice RTL is unchanged, and the runtime paths are bit-identical. |

## 3. The design (d)

```
host hb -> qkd_embgw_boot_s --bw 293--> qkd_kv_es_fan_root2_b (kvs_ctl) --h 784--> qkd_kv_es_fan_stack_b (stack roots)
   --chain 780--> qkd_kv_pc_chain_station_b (x128) --land_es--> HOST slice (unchanged) --ctrl_es--> es_merge_b --> controller
                                                    <-land_er--                       <-ctrl_er/compl-- (boot window only)
host fi chain -------------------------------------------------> HOST slice ingest station (unchanged)
```

* **`qkd_embgw_boot_s`** (successor of `qkd_embgw_boot`) does the strips' boot job at the gateway. It maps E with
  `emb_loc`, the strip's map. It emits one registered boot word per GAP edges, and keeps the count and the CRC sum
  cumulatively from reset, as the strips did. On BOOT_END it drops emb_ready, waits HOLD = 64 edges (the not-ready
  window the HOST barrier must see), and then raises ready iff the sums match. It also has REOPEN: a BOOT_WR that
  arrives while ready drops ready and holds the stream for HOLD edges first. Ports are `hb`/`hb_cr`/`est` as before
  plus `bw`. `emf_*`, `emr_*` and their credits are removed. The `est` layout is unchanged.
* **`qkd_kv_es_fan_root2_b` / `qkd_kv_es_fan_stack_b`**: the boot word rides lane 0's PA / DA / AD fields with a new
  valid bit, `h[783]` and chain bit 779. A writer or expected event on a boot edge latches fault, and the writer keeps
  its fields. With `bw` idle, `h[782:0]` and `d[778:0]` equal the originals'.
* **`qkd_kv_pc_chain_station_b`**: at the matching pc strap it emits the boot word registered on `land_es`, as the
  HOST ABI word `{1, 1, bank, col, row, data, 1}`. `land_er` goes into pin flops and is checked, never waited on:
  * a credit with nothing outstanding is a fault;
  * a landing read return is a fault;
  * the slice fault bit is a fault. It carries the slice's exact landing-queue overflow.
* **`qkd_static_kv_pc_es_merge_b`** adds a third source, the slice's `ctrl_es` (pin flop, then the same select
  register). Ownership is by phase: `own = !emb_boot_ready`, from the `est[0]` every PC already receives.
  * When `own` is set, the controller's er, credits and completions go to the slice (`her` / `hcv` / `hcw`, output
    registers), and the embedding endpoint sees er = 0.
  * When `own` is clear, behaviour is exactly the old merge; her valid / credit / fault and hcv / hcw are 0 (her data bits are ungated, qualified by valid).
  * Faults: two sources on one edge, a slice word in the run phase, or a writer word in the boot window.

  emb_ready rises only after the HOST ledger has retired every boot write's real completion, because BOOT_END waits
  for it. So all slice traffic, credits and completions are home when the face flips.
* **`qkd_static_kv_pc_path_{emb,fan}_nc_b`**: the wires-only parents with the new ports `land_es`, `land_er`, `hes`,
  `her`, `hcompletion_v` and `hcompletion_we`.

All four boot paths are real again:

1. The HOST KV ingest goes through the slice station and the slice host source.
2. The embedding image goes through the gateway, the chain, the slice landing source, the slice's boot-qualified
   arbiter and the merge, then to the controller.
3. The cold-boot check runs through the merge, with its er and completions.
4. Acks flow as `land_ack` / `host_ack` -> `sko` / `ao` -> the HOST ledger, unchanged.

The slice's `emback` credits and queues stay. They are now only in the boot window (the boot boundary), never on the
run path.

**Pricing.**
* Runtime: **0 edges** on the writer -> controller es path, the embedding issue -> controller path and the embedding
  return slot. `return_slots` and the RETIME slots are unchanged. On er -> endpoint the only addition is one AND gate,
  which the endpoint's input path absorbs.
* Boot path (elastic, init only): gateway 1, root pin 1, h 1 + relays, stack head 1, 31 - slot hops, station 1, slice
  (pass-through 3-5), merge 2.
* Area:
  * station: +290 flops;
  * merge: +288 (hes pin flop) + 263 (her / hcv / hcw) flops;
  * root: +293 flops;
  * gateway: the strip link state goes (4 x 4-word receive FIFOs + slots, about 9 kb) and one CRC32 over 288 b plus
    two 32-b sums are added.
* Pins, per PC (kvpc tile face to hsl): +288 + 261 + 288 + 261 + 2 = **1,100**. On the hsl these are its existing
  faces.

**Boot contract** (fault-checked, never stalled):
* Image words arrive in ascending E, one per gateway edge. Each PC then receives one word per 128 sectors. The slice's
  landing queue is 4 deep and the controller's static queue is credit-managed inside the slice.
* HOST KV loads and image re-loads happen only in the boot window: before the first emb_ready, or after REOPEN. The
  HOST stops the static programme before a re-load.
* A HOST word in the run phase is a merge fault. The static controller has no compiled slot for it.

## 4. Evidence (fleet, Verilator 5.050, `tools/qwen_kv_die/kv_boot_gate.sh`)

See `gate.txt` and the `*.log` fail witnesses in this directory.

* `tb_kv_boot_lockstep` (4 x 32 PCs): the current chain against the boot-capable one, with the boot face idle and
  random writer, expected, start, calendar and er traffic. Every edge, the root h, every station output and every
  merge output are equal. A boot / writer collision faults the root and is not delivered. 64 clean boot words each
  reach exactly their station. Mutants:
  * 7, stack strap: FAIL;
  * 1, root with no collision fault: FAIL;
  * 6, station pc[3:0] tap: FAIL.
* `tb_kv_boot_pc`: one stack with the **32 real HOST slices**.
  * Cold boot: 32/32 PCs pass through merge_b.
  * 24 HOST KV writes, with acks and credits per PC.
  * A 6-row image plus scales, about 780 sectors. Stack-2 words go through the slices and the other stacks are
    scoreboarded. The bench waits for the ledger acks, then sends BOOT_END, and `est` goes ready after HOLD.
  * The players read every token in the run phase. Every beat equals the boot data, so the boot map (`emb_loc`) and
    the read map (`qkd_embedding_static_map`) agree end to end.
  * Memory matches the writes exactly.
  * A re-load with REOPEN is then read back with the new data.
  * A run-phase host word faults only its PC, and a wrong checksum faults `est`.

  Mutants 11 to 17 (gateway pc ^ 1, count-only, no REOPEN; merge er not steered, no run-phase fault, completions not
  steered; station pc[3:0]) all FAIL.
* The parent `qkd_static_kv_pc_path_fan_nc_b` elaborates with every pc_path source (lint, no pin errors).

## 5. KV-PLAN3 die wiring changes (kv_static_die / kv_die)

1. `embgw` master: `qkd_embgw_boot` -> `qkd_embgw_boot_s`. Drop the `emf_<q>`, `emf_<q>_cr`, `emr_<q>` and
   `emr_<q>_cr` buses and opens (8 + 8). `hb` (283 + `hb_cr`) and `est` are unchanged.
2. New bus `ks_bw` (`kv_oneway`, 293 b): `embgw.bw` -> `kvs_ctl.fanr__bw`. Both tiles are centre tiles. In the kvs_ctl
   tile generator, `u_fanr` becomes `qkd_kv_es_fan_root2_b` with `.bw(fanr__bw)`, and `h` becomes 784 b.
3. `h` buses to the stack roots: 783 -> 784 b. kvs_hroot: `qkd_kv_es_fan_stack_b`; `qkd_kv_stack_relays` HW = 784,
   which shifts the fan-word slice `dn[HW +: FW]`. `d` is 780 b.
4. PC chain (`i_next`/`o_next` of kvpc / kvpc_h, and the hroot -> PC 31 head): 779 -> 780 b.
5. kvpc / kvpc_h: `u_pc` becomes `qkd_static_kv_pc_path_fan_nc_b`. Its new tile ports, all on the hsl-facing side, are:
   `pc__land_es` (out 288), `pc__land_er` (in 261), `pc__hes` (in 288), `pc__her` (out 261), `pc__hcompletion_v` and
   `pc__hcompletion_we` (out). `pc__er`, `pc__completion_v` and `pc__completion_we` stay as tile exports (o_grp uses
   er[260]), but no longer go to the hsl.
6. Per PC, beside each other, with registered pins at both ends:
   * `les`: `kvpc.pc__land_es` -> `hsl.land_es`
   * `hler`: `hsl.land_er` -> `kvpc.pc__land_er`
   * `hes`: `hsl.ctrl_es` -> `kvpc.pc__hes` (today it points at the nonexistent `pc__wes`)
   * `ler`: `kvpc.pc__her` -> `hsl.ctrl_er`
   * `hcv`/`hcw`: `kvpc.pc__hcompletion_*` -> `hsl.ctrl_completion_*`
   Remove the `hsl_<st>_<k>.land_es` open.
7. **`hlpc_<st>_<k>` = k**, the kvpc pc strap (kv_static.py `pc_<st>_<pc>` strap pc = pc), **not `host_lpc(k)`**. The
   slice's lpc must name the logical PC its controller holds. Otherwise the HOST ledger acks and the ingest station
   targets point at the wrong PC. The HOST ingest map's KV placement and the static writer's dest_pc map must then
   agree. That is a compiler / host-map contract, to be checked by the compiler owner.
8. The compiler records the boot-path ages in item 1 of the section 3 pricing list. They have no runtime effect.
   `return_slots` and the KVJ-C3 writer ages are unchanged.
