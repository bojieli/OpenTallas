# KV-P3-RTL 10-23: START-only HC transport below the OBSX station (no {143'd0,cmd_hc} pad)

Owner rule: no tie-offs and no constants padded into ports (COORD 07:45: "a tie is a tie").
27befae4f narrowed the OBSX HC station to HCW 39, which is START only. The station's 39-bit command then entered the generic
182-bit transport `u_packet.u_ctrl` as `.cmd_hc({143'd0,cmd_hc})`.

## Change (all generated; every edit applies exactly once)
- **`qkd_host_ctrl_token_service_packet_collected_mu`** (`gen_peer_mu.py`, then `hoist_gmu_decls.py --fix` as in KV-PEER13) gets parameter `HCW`.
  - The default, 182, keeps the original logic with behaviour unchanged.
  - `HCW 39` (MU 1 only; any other value hits `$fatal`) is START only:
    - `cmd_hc`, `hc`, `cd`, `cq[4]` and `active` are 39 bits wide.
    - The PW113/DW181 event logic is absent: its event mask `PWDW_EV` is empty at 39. This covers the pulse clears, the abort "retain PW/DW" branch and the queued-abort release.
  - The 512-bit link frame keeps its layout. At HCW 39 the PW/DW field (frame bits 229:87) is reserved. A peer that receives a frame with that field set faults (fail closed) instead of silently truncating it.
  - The other two generated files, codec_mu and tp8_coordinator_mu, are byte-identical after regeneration. The `--pd` fork is untouched because the HCW edits apply only to the main job.
- **`qkd_host_packet_bundle_admission_mu`** (`gen_host_root_mu.py`) gets parameter `HCW`.
  - The default is 182. `cmd_hc`/`hc` are HCW bits wide, and `.HCW(HCW)` passes to `u_ctrl`.
  - The generator now applies the KV-PEER13 hoist itself. As a result `--check` reports OK; before this change it was STALE.
  - `test_host_root_mu.py` is updated (HCW param and `.HCW(HCW)` child string). Its result was 3/4 before, 4/4 now.
- **OBSX** (`gen_host_root_obs.py --ext`): `u_packet #(.MU(1),.HCW(39),...)`, `.cmd_hc(cmd_hc)` at 39 bits, `wire[38:0]transport_hc`.
  - Regenerating OBSX changes only these 3 lines.
  - `hostp_hcw39/check_source.py` now also asserts that the transport pad is gone.

## Benches (Verilator 5.050, localhost)
| bench | before (HEAD ef0304185) | after |
|---|---|---|
| `rtl/test/qwen_host/hc39_equiv/run.sh` **eq**: tb_mu_peer_e2e (8 dies, 4 users x 3 rounds), each of the 8 transports run as REF(182, @27befae4f) + DUT(HCW 39) on the same inputs, all 1670 output bits + hc compared every cycle | n/a | PASS, 8 x 10934 cycles, 0 mismatches, 12 START cmds, 84 root frames |
| same, **eq_abort** (+ABORT, 3 retained users cancelled) | n/a | PASS, 8 x 13611 cycles, 0 mismatches |
| **rsv** (tb_hc39_rsv.sv): peer frame with the PW/DW field set | n/a | PASS: REF takes it, HCW 39 faults |
| mutants m1 (peers drop START), m2 (one cmd field bit corrupted in the queue), m3 (die 0 drops START at grant), m4 (no reserved-field check) | n/a | all 4 CAUGHT (28 / 11 / 4 mismatches; rsv FAIL) |
| `rtl/test/mu_qwen_1018/run_all_peer.sh` (3 MU + 6 existing incl. MU0 + 10 mutants) | 7 PASS, 10 mutants FAIL | same 17 result lines, byte-identical (ex_tsvc / ex_tsvc_mu0 = MU 0 originals still compiling at commit time) |
| `rtl/test/qwen_host/hostp_hcw39/run.sh` (1024 PW + 8 DW, 2 mutants) | PASS | PASS, both mutants FAIL |
| `tools/qwen_kv_die/test_host_root_mu.py` | 3/4 (generated_current stale, hoist) | 4/4 |
| Verilator `-Wall` lint of `qkd_host_root_admission_obsx` (91 files: kv_framepins_1020 list + record_port_mu) | 540 warnings | 539 warnings: the only difference is that `transport_hc[181:39]` UNUSEDSIGNAL is gone |
| `-Wall` lint of the transport alone (TOKEN+SERVICE, STRAPPED) | 58 | 58 at HCW 182, 58 at HCW 39 (same set) |

Coverage gap: the e2e bench never queues a START behind an abort, so the abort-on-load path of the transport (`cq[cr]&~START_EV`) is covered only by construction (the same expression at both widths). An earlier mutant on that line was NOT caught and was replaced (see run.sh).

## Remaining `{143'd0,...}` pads (not on the release OBSX path, not changed)
- `rtl/qwen_sys/mu_qwen_20261018/qkd_host_root_admission_mu.sv:434`: the MU root station `.raw_hc({143'd0,raw_hc[38:0]})`. This is the KV die host root when `OT_KV_HOST_OBS=0`.
- `rtl/qwen_sys/kv_host_obs_20261019/qkd_host_root_admission_obs.sv:176`: the OBS (no-ext) station, same pad. That file is also STALE versus its generator, since KV-PEER13 (pre-existing).
- `rtl/qwen_sys/host_integrated_20261014/qkd_host_control_packet_{admission,observed,capture_localprogram}.sv`: the original sources (MU 0) that the generators read.
- `host_cluster_20261017/`, `host_cluster_cdc_20261018/` and `split_20261014/` have none.
