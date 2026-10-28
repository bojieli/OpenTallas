# DIE-HBM-10 (3): one-owner VM crossing read + dead-by-schedule ties (die-local RTL)
Basis: COORD 09:30 (HBM die owner writes the RTL; bench that catches a mutant + LEC + token check; relief counts only
after that); plan C21 `c21_side.json` planned_links vmx_W2E / vmx_E2W (u_vmb_Q1 <-> u_vmb_Q5, 4096 b, 3 relay regs,
latency 4); DIE-HBM-9 (6) (half-local VM banks, shared tensors = one-owner crossing reads, no double writes).

## Estimate before build (one page)
- Form: the owner half issues the read on its OWN bank port with the record (static schedule). No request crosses the
  hub. The response (q0_faces rr: [256] valid + 256 b data, response at n+6+PIN) streams over a register chain to the
  far half: fixed LX = 4 edges (3 relay sites at plan regs_um + far capture). Far station sees it at n+6+PIN+LX.
- Width: 16 lanes x 257 b = 4,112 b per direction per hub (plan says 4,096 b: +16 valid bits, +0.4 %, UNCHECKED
  against the face budget).
- Cells: 16 x 257 x 4 = 16,448 flops per direction per hub (synth: 32,961 ASAP7 cells incl. 16,448 DFFHQNx1 + 16
  AND2 reset gates), x 2 directions x 2 hubs ~ 132k cells, split over 4 relay sites per direction (~8.2k cells per site
  per direction). Fits the <=400k/run cap. Area UNCHECKED (~5k um2 of flops per direction per hub at ~0.29 um2/flop).
- Latency: +LX = 4 cycles on owner-issued shared-tensor reads. tok/s already priced in DIE-HBM-9 (6) (+0.36..0.72 %
  streamed); UNCHECKED here.
- Ties (dead-by-schedule): the far client's request pins toward the owner bank group (rq<g>, 17 b) are TIELO 0 at the
  bank pin, response pins unconnected. Bank master unchanged (no type split). Declared in `xread_ties.json` (form);
  the per-instance pin list needs the hub glue client->bank-group map bound (UNRESOLVED).
- Clock: each stage has its own clock pin (`clk_stage[s]` = hub comb tap at relay site s). All 4 relay sites are
  inside the hub region (one comb tree), so the hops are in-region related pairs, not CA crossings. Per-hop STA owed.

## RTL (new, opt-in; no existing instance changes, so default behaviour is byte-identical)
- `rtl/hbm_accel/generic/vm/static/xread/hfd_vms_xread_link.sv`: LANES (16), LX (4), MUT bench hooks (0 = production).
  Only valid bits are reset.
- `rtl/hbm_accel/generic/vm/static/xread/tb_vms_xread_link.sv` + `run_xread.sh`: 8 REAL q0_faces owner banks + 1 far
  bank whose group-2 request pins are the tie.

## Evidence (CHECKED, intel2 2026-10-28)
- Bench `run_xread.sh` (iverilog): positive PASS (1,755 owner-issued crossing reads, exact edge and SRAM row; 256
  far-half local reads in the same cycles; tied group never answers; no FAULT). Mutants all rejected:
  link_short (LX-1) FATAL valid phase; link_swap (lanes 0/1) FATAL data; link_bitflip (lane 7 bit 255) FATAL data;
  tie_live (live request on the tied pin) FATAL bank fault. Logs in `bench/`.
- LEC `tools/die_plan/lec.py` on a mini kit (LANES 16, LX 4, yosys ASAP7 RVT map): **EQUIVALENT**, 20,560 compare
  points proved, 0 differs (`lec/lec.json`).
- Token check: NOT RUN. The HBM token pass (tools/hbm_layer_vehicle/tok_func_hbm.sh) is die-level. It needs (a) the
  link in the die contract, (b) the compiler schedule issuing every shared-tensor read from the owner half (half-local
  VM allocation is not in the compiler yet). Until it runs, the cross-half relief stays NOT counted.

## Remaining
1. Bind the tie instance list from the hub glue (client -> bank group per half) and add it to `xread_ties.json`.
2. Compiler: half-local VM allocation + owner-issued crossing reads (static schedule), then the token pass.
3. Wire the link into the hub glue / die contract (plan event); per-hop STA at the comb taps.
