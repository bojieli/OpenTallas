# MTP fixed-latency links (mtp-fixlat-1011, 2026-10-10)

Follow-up to the ds-1010 latency audit (eff5a6f0a). Two sets of paths were AT RISK of the fixed-latency grant bug that was fixed on the seq<->WFC link.

**(A) The sequencer's partner ends.** These are `rtl/dsrom_sys/mtp/dsfd_mtp_partner_ep.sv`.
- `dsfd_cap_mtp_ep` is the RESULT transmitter (ltx). It launches one flit per grant it has seen, so it is correct at any relay count.
- `dsfd_vm_mtp_ep` has a draft-head step receiver. It is an `ot_dsrom_mtp_lrx_rtt` sized for mtp->vm 11 / vm->mtp 11, with D 26 and SEL 1.
- `dsfd_vm_mtp_ep` also has two transmitters: rows-ready and draft-head result.
- The station counts are head631's pin-to-pin counts, recounted on main e707ff5b3 (`head631_stages.json`).

**(B) The P2 draft-die links.** These are in `rtl/experimental/mtp_p2_ordered_20261009/dsfd_p2_lnk.sv`.
- `dsfd_p2_lnk` sits at the pins of the unchanged rb4 core. It holds:
  - the lane receivers: lane 0 is vm 12/14 with D 30, and lane 1 is collective 8/9 with D 21;
  - the start receiver, D 21;
  - the result-row transmitter (ltx).
- `dsfd_p2_lnk` also has a **transaction gate**. A lane word reaches the core only under the identity of the start that the core accepted. Without the gate, back-to-back transactions fault the core through its identity check.
- `dsfd_coll_p2_ep` is the collective end and `dsfd_vm_p2_ep` is the VM end.
- The station counts are draft A's, from `draftA_stages.json`.

**Gates** (`gates.log`, run on EPYC1):

| Gate | Case | Expected | Result |
|---|---|---|---|
| `tools/mtp_fixlat_gate.py` | pep_s1, pep_s7 | PASS | PASS |
| `tools/mtp_fixlat_gate.py` | pep_lat1, pep_stale | FAIL | FAIL |
| `tools/mtp_fixlat_gate.py` | p2_s1, p2_s5 | PASS | PASS |
| `tools/mtp_fixlat_gate.py` | p2_lat1, p2_naive (the as-is core on the stations), p2_naive_1tx, p2_nogate | FAIL | FAIL |
| `dsrom_mtp_rom_bench` | ep_s0_tr_dspark, ep_s0_tr_forced, ep_s0_hash_u3 | PASS | PASS |
| `dsrom_mtp_rom_bench` | ep_s0_neg_off1 | FAIL | FAIL |

The `ep_s0_*` cases run the full system at the head631 chains with the RTL partner ends.

**Cycles.**
- The seq ends add 0 cycles.
- The P2 link ends add 9 cycles per transaction. This was measured at 0 stations: 6,122 cycles through the link ends against 6,113 with the core driven directly.
- That adds 27 critical cycles in total (`p2.link_ends`).
- The MTP rate moves from 4,199.4 to 4,199.3 tok/s (`results/arch/mtp_step_20261009/ds_rom_step.json`).
