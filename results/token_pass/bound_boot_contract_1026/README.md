# Current native boot field dependencies

The isolated `bound_boot_contract.resolve(program, timing, source_root, execution=None)` provider resolves the current selected header's **stage=0** from the production wrapper chain, with all five source files checked against the current timing receipt. This is the actual evaluated constant, not the L14 index or a chosen header default:

1. Preferred `portfix178/dsdv_hostb_seqhost_mux` instantiates `dsdv_seq_host_mux` without a STAGE parameter.
2. `dsdv_seq_host_mux` instantiates `dsdv_seq_host_mu #(.NSLOT(47),.SELR(SELR))`, omitting STAGE.
3. The selected `dsdv_seq_host_mu` declares `STAGE=0` and forwards it through `dsdv_seq_host` and `dsdv_sh_sq` into `ot_dsdv_walk_issue`.
4. The actual walker rejects PW header bits [6:0] unequal to that STAGE.

The provider checks these exact source fragments and returns stage 0, while leaving BEGIN and SEAL forbidden. On the actual current 96-command retimed norm programme, **start_phase remains unknown**. A changed wrapper-chain source hash is rejected by the negative control.

Header bits [8:7] supply `start_phase_q`; actual acceptance requires `(phase_q+1) mod4 == start_phase_q`. The KS descriptor carries start/user/token/position, with no phase field. Therefore neither layer number nor command issue dates determine start_phase. The current measured phase-zero injection receipt supplies one accepted KS pin-event class relative to reset release. If `execution` contains this programme's actual `die_sha256`, `reset_release_pin_edge` and `ks_pin_edges`, the provider can recognize that proven class and return candidate phase 0. With absent or mismatched clock booking it returns None. It does not infer alternate phases or qualify global reset transport.

MU initialization depends on records still absent from the current native programme:

| Boot data | Actual dependency |
|---|---|
| 0x15 gaps | Complete source start calendar and matching incoming user/token/position descriptors. These are KS pin-event spacings, not command issue spacings or counts of slices/batches. |
| Slot count | One gap word selects 47 slots; two or more select exactly that table length. Every used slot needs attributes. |
| 0x15 RL | Actual KIT issue plus measured pin-event KS-to-KIT offset minus one input-sampling edge. The current 96 rows contain no KIT, so RL cannot be derived. |
| 0x16 eight events | Real tag/replay allocation for endpoints 7n, 7s, 0n, 0s, event delays and every slot's copy/replay attributes. Eight rows alone do not determine the kind/endpoint allocation. |
| HLOAD/GAIN/NORM/GO readiness | Current source-pinned target5 commit, last HLOAD word, last GAIN word, norm input residency and downstream NX/rstd/XQ dates. ACK at issue+5 is not a store/readiness observation. |
| END | Static row last-use and actual completion/retirement records. No result-driven or guessed END is emitted. |

The machine-readable `contract.json` lists the exact bounds and the field interface expected from the source-qualified entry/NX providers. In particular: min gap > used slots+1; RL > used slots; RL <= complete slot period; each event D in [used slots+2, RL-2]; no periodic endpoint collision or duplicate outstanding user; boot before arming. A kind-0 TX event emits a valid window even when its land bit is zero, so filling rows with arbitrary zero attributes does not disable unknown TX windows safely.

No MU values, KS dates, BEGIN, KIT, END or SEAL are fabricated. No timing rerun, RTL change or new cycle. This is a narrow current-main-based provider; the compiler lane owns integration into `bound_boot`.
