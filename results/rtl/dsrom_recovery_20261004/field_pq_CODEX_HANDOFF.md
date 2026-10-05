# DS-ROM recovery lever "field" (PQ): handoff to Codex

## Status
- Verdict REJECT, in `levers/field.json`. Under the owner rule the spine must close SS at 1.2 GHz first.
- The RTL is final, exact and on main:
  - `rtl/v41die/ot_v41_{spine,field,pair,fieldtop}_pq_w17w10.sv`, `ot_v41_pair_pq_ld.sv`;
  - `rtl/v41rom/ot_v41_rom_elem_pq_w10.sv`, `ot_v41_elem_pq_tags.sv`;
  - vehicle `tools/dsrom_recovery_field.py`.
- Exactness: 6,016 of 6,016 node-region runs are bit-exact. That is 170,528 rows over 7 layers and every region.
- Measured gain if adopted:
  - AR 1,612.7 to 1,943.1 tok/s (+20.5%);
  - MTP 4,462.1 to 5,211.0 tok/s (+16.8%).
  - Node times are in `field_pq.json`. For example, wo_a goes from 1.73 to 0.65 us.

## What closes
The per-pair hardware closes when routed:
- `ot_v41_pq_pair_screen`, at SS +140.0 ps and FF +5.0 ps;
- with 0 GRT overflow and a worst 4x4 window of 0.73.

## What does not close (the remaining work, which is spine RTL, not routing)
- `ot_v41_pq_spine_screen`, routed on ot-epyc2:
  - R=16: SS -722.8 ps;
  - R=128: SS -905.9 ps and FF -10.3 ps;
  - the PQ=0 baseline of the same wrapper: SS -684.1 ps.
- Violations by register class are in `field_pq_phys/spw*_ss_violations_by_register.json`. The worst are:
  - `sw` (the stream-ROM word loop: `sw` -> need vs `have` -> `s_ok` -> next ROM address -> `sw`);
  - `w_addr` and `w_data` (row write: tag-indexed base + row + pos*ops, format select);
  - `bt_q*` and `bt_d` (beat assembly from the x buffers);
  - `since1`/`since2` and `sm_i` (the stream-end cone);
  - `s_rl` and `ga` (the row-count tree).
- Most of these loops are inherited from the pinned `ot_v41_spine_w17w10`.

## Suggested fixes
1. Prefetch stream words two ahead, so the ROM read leaves the `s_ok` loop.
2. Register the root inputs and compute `w_addr`/`w_data` one cycle later. This costs +1 cycle per node, so re-run the campaign.
3. Register `since1`/`since2` from a registered stream-end pulse.
4. Pipeline the beat-assembly buffer read.

Each change that alters a cycle needs this sequence:
1. Re-run the exactness campaign: `tools/dsrom_recovery_field.py build/run/record --plan-dir planv`.
2. Re-run the screens: `physical/dsrom_recovery_field/phys.sh`.
3. Write a NEW lever record.

The REJECT record is never overwritten.

## Physical cost (in `field_pq_ssff.json` `physical_cost`)
- Area added:
  - 818.6 um2 per element;
  - 15,458 um2 per region;
  - 1.979 mm2 per layer die;
  - 641 mm2 over 324 dies.
- No dies are added. The die fits the reticle margin: 18.76 mm2 before, 16.78 mm2 after.
- The S81 full-die rerun is needed because of the larger element abstract, one more BF site in region 93 (R93) and a broadcast 2 bits wider.
