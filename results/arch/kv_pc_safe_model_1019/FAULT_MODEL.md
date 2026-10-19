# Selected PC boot-return fault integration model

**Source fault closure FAIL; integration MODEL ONLY.** The old split-clock diagnostic wrapper and the selected GEN7 unified wrapper independently omit their real `chain_fault` output. This is an earlier blocker than SRAM migration. No RTL, pin, schedule or gate was changed.

The selected parent is exactly `/srv/opentallas-scratch/claude/qwen-kvsys/kvs14r-4db097403-codexmub/port_bind_v2/die_bound.v`, SHA256 `18464a8b31042bea03b3fc5779d42803ab7b05bebbaab733a4d83d4a714c1ea6`, 19464418 bytes. Its `source_verified.json` identifies clean source commit `4db0974030714ac3f3745ccadd6c0a234dfeb3c4`. The separately identified strict-rebind `7006cbd0` and future GEN8 are not this parent. This selected parent still has its own recorded bind failures; no parent PASS is implied.

Read-only unpinned `ot-run` unit `oth-ubuntu-2170849-1792440055` reused that existing die; final source-receipt and leaf-binding validation unit `oth-ubuntu-2179813-1792440274` emitted `selected_fault_trace.json`: **128 PC objects, 124 `qkd_kvs_pc` and four `qkd_kvs_pc_h`, feeding 32 landing groups.** All 128 PC-field, relay and group core-clock nets match exactly at the RTL connection boundary. The full per-instance clock/reset/net/pin ledger is retained; this does not prove native skew or reset epoch alignment.

The selected leaf is `rtl/qwen_sys/static_kv_die_20261017/qkd_kvs_tiles_hroot_ff_k_mu_ba.sv`, not the older diagnostic `_mu_ds_rl.sv`. Source hashes and executable checks are in `fault_contract_model.json` / `tools/qwen_kv_die/pc_fault_contract_model.py`. For both selected PC variants, `w_pc__chain_fault` and `w_pc__es_merge_fault` occur only in a wire declaration and child output binding. Neither appears in any tile output concatenation. Therefore the selected wrapper really drops these signals; this finding does not rely on the old prototype's dead-input aliases.

The chain's actual path is `land_er[0/259/260] -> ler_v/cr/f -> bfault -> fault`. It captures in `ck`, with local reset `rs_q <= rsi` and asynchronous clear when `rs_q` is low. `fault` and `bfault` set sticky until reset; the three input fields check unexpected read return, returned boot credit, and child landing fault. The other 258 `land_er` data bits are not read by this child. The old native graph has optimized away the whole real checker because the tile does not export `chain_fault`; all 261 native-unused bits cannot collectively be called spare. The two high `land_es` command fields are conditional constant data with unreset first-use/hold behavior, so their native ties receive no registered-pin/invalid-payload waiver.

## Proposed existing registered core-fault field

For ROOT review, extend the existing **core-clock** return-fault pin flop's D equation with the true sticky `chain_fault` level:

```
fault_core <= rs_a && (fault_core_s || fault_core_set || chain_fault);
```

The exact existing source equation lacks the final operand. This proposal uses the existing `u_pc.u_pce.u_path.u_return.fault_core` physical output register, keeps the old return-fault age, and delivers a newly observable chain-fault Q after one core edge. It adds no arithmetic, HBM return, token-data or readiness wait. This is a same-domain sticky fault OR, with no idle/ready/health level mixed in, no asynchronous HBM reduction and no combinational output pin. Its opt-in source interface and default preservation would need a new reviewed exact source fingerprint before implementation. The selected field would become a PC core-terminal-fault aggregate; consumers and cause inventory must explicitly record that expanded meaning.

The actual selected ABI is unified **`o_grp[301]`**, inside 305 bits. It is not the older split prototype's `o_grp[293]`. For all 128 objects, selected-die wiring sends bit301 through bit5 of the high nine-bit slice in one `qkd_rlys_36` into its landing group's `i_pcN[301]`. The group decodes this as `drain__ring_fault_core`, captures it into `u_drain.fault_core_q`, and latches `u_drain.fault`; its output is `o_ctl[17]`. Exact instance identities, source nets and reset nets are retained per PC. The relay is an inherited unreset one-edge register; full reset/first-use/physical landing proof remains required.

For a bad boot-return field sampled at E0, the candidate relative edge ledger is:

| Edge | Registered observation |
|---|---|
| E0 | `ler_v/cr/f` capture the bad input |
| E1 | `bfault` sets |
| E2 | `chain_fault` sets |
| E3 | Existing return-fault output FF exports the chain cause |
| E4 | Selected `qkd_rlys_36` captures bit5 |
| E5 | Landing-group `fault_core_q` captures it |
| E6 | Landing-group sticky fault sets, visible in `o_ctl[17]` |

This ends at the actual landing-group terminal. Subsequent group forwarding includes other relay/landing masters and the hroot/control path; their complete native phase/STATUS/retirement/future-admission bound remains **null**. No assumption that the host already vetoes retirement is made. The host-health model must consume the closed source bound and continuously veto fixed STATUS, host retirement and future admission, while allowing the current fixed schedule to drain.

Restoring the checker needs at least eight real state FF per PC (`ler_v/cr/f` three, `bo` three, `bfault` one, `fault` one): **1024 state FF across 128 PC objects**, before their real input/reset/Boolean fanout copies, restoring other optimized predicates and output-drive costs. Aggregation reuses the existing pin FF; the extra OR and the fully restored logic still require an actual mapped cost/complete census. `rs_q` ancestor fanout increases; no old reset certificate transfers. The new field must have one explicit fixed-face owner in the new kit, native TT/FF matching, <=405-um source/landing stages and fully charged clear/lifecycle timing. Existing 805/25 multi-face data FF need their own source-equivalent face copies and ancestor-load proof.

There are **128 distinct selected chain-fault producer objects** to reconcile with the earlier minimum357 inventory. The selected wrapper also drops 128 ES-merge fault outputs, but their internal embedding-fault/reset lifetime and any already counted cause joins need a separate exact proof. The minimum357 comprises different previously enumerated physical/transport producers; its actual source-ID membership was not supplied to this step. Consequently **no485-source or613-source total is claimed**. Record the chain cause per exact PC identity, then take a real set union with existing producer IDs and cause joins. Keeping the same exported physical bit does not erase a missing cause; counting two causes on one sticky source does not automatically create two unique health-source objects.

Validation: complete source-hash/equation/bit-layout checks pass; all128 actual source→relay→group clocks and fields match the selected die; old native uniform counts and immutable evidence remain retained. Healthy behavior, the three real boot-return fault causes, counter overflow, reset during activity, missing-cause mutants, complete source cost/native reach, and host retirement-bound proof remain required before source adoption or a new gate.
