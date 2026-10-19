# S81 per-layer RTL pass on the current die (TOKEN-PASS-S81, 2026-10-18)

**Status: BLOCKED. No layer has been measured on the current die.** The current die is p4l, the landed DV die with
half-cycle hops (bind9: 40 masters, 7,489 instances, strict DIE_PORT_BIND PASS). The 10-13/14 layer vehicle
`tb_s81_die_layer` cannot be moved onto it, because the DV die contains none of that vehicle's masters:

- the hub controller `dsfd_sp_ctrl_e`;
- the HC slab `dsfd_sp_hc_c` and the SU slab `dsfd_sp_su_h`;
- the collective `dsfd_sp_collective_c`;
- gather and capture (`dsfd_sp_gather_c`, `dsfd_sp_capture_c`);
- the hub VM.

In the DV die the SU, HC, norm, capture and Engram mix all run inside the 16 vector slices (`ot_s81sl_slice*`), and the
sequencing comes from the `dsdv_seq_host` calendar (`ot_dsdv_fixed_issue`). No compiler yet writes a DV layer program,
and no DV layer fixtures exist (`record.json` `behavioural_or_missing`).

## Delivered

- `layer_price_p4l.json` / `.txt` (`tools/s81_dv/dv_layer_price.py`) gives the priced layer on the p4l landed
  half-cycle schedule. It uses the same deltas and solve as `dv_price.py` dv_base, which gives AR 1,365.7. Each row is
  the layer's critical-path cycles, with the hub DAG value in brackets:

  | Layer | p4l price (hub DAG) | Note |
  |---|---|---|
  | L0 | 15,475 (14,943) | |
  | L2 | 28,103 (27,484) | |
  | L14 | 28,028 (27,348) | |
  | L20 | 30,429 (29,800) | |
  | MTP draft | 42,458 | |
  | head | 11,334 | separate head die, no DV delta |

- A full-RTL elaboration and idle-run cost probe of `dv_die`:
  - files: `rtl/dsrom_sys/s81_dv/test/tb_dv_die_probe.sv` and `run_dv_die_probe.sh`; `die_probe.f` is the file closure;
  - it measures the Verilator build wall time and RSS, and the simulated die cycles per wall second;
  - these are the inputs to the release-gate fleet-hours estimate;
  - result: see `pending_results.txt`.
- The historical numbers from the hub vehicle are kept in `record.json` for reference only. They were measured on
  superseded masters: L0 7,737, L2 16,358, L14 18,861, L20 34,410.

## Next (vehicle plan, `record.json` `vehicle_plan`)

1. Write `dv_layer_compile.py`. It lowers the layer ops to:
   - the seq_host calendar, CTL templates and host CSR boot stream;
   - the frame cfg7 programs;
   - the svc and gunit jobs;
   - the return calendar.

   It must use the p4l land-plan E values, the rlyh stations and the seq_host fixed latencies.
2. Build per-layer fixtures from the released checkpoint and the 1M shard: ROM frame images, leaf stores and the HBM
   KV image.
3. Write the bench: `dv_die`, a host boot driver, TP4 PMA peers, a golden comparison at the slice h rows, the sticky
   fault checks as the schedule assertions, and mutants with committed fail witnesses.
4. Run L0, L2, L14, L20 and L21 on the fleet.
