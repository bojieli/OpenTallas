# S81 structural closure benches (CLAUDE s81-blocks, 2026-10-07)

Bench summaries for the opt-in structural variants on branch claude/s81-blocks-20261007 (run on ot-epyc3,
/srv/opentallas-scratch/claude/s81-blocks). bench_summary.txt holds the raw last lines.

| bench | configuration | result |
|---|---|---|
| selector (tools/s81_ph/selt_pipeline_bench.sh, SEARCH_PIPE 1) | base_p1 | PASS, tail mean 127 / max 257 |
| | vA: MRG_PIPE 1 RQPIPE 1 | PASS, 129 / 257 |
| | vB: + PIPE2 1 SLAT 4 CMP_RETIME 1 | PASS, 153 / 285 |
| | vC: vB + SAFE quarter | PASS, 156 / 285 |
| | vD: vB + QIO 1 (control XDX 1) | PASS, 172 / 308 (SAFE 174 / 310) |
| | negatives nB / nB2 / nD (MUT_THRESHOLD, MUT2) | FAIL as required |
| collective TP4 tiled slab (run_coll_bench.sh) | FMT1 + EP PIPE2 | PASS, dut_last 3,012 (base 3,374) |
| | FMT1 + EP PIPE2 + MUT_NOREORDER | FAIL as required |
| VM (run_vm_bench.sh, lockstep vs behavioural array) | TILED_HALF NSLICE 2 seeds 1/2, NSLICE 4 | PASS, 0 mismatches / 56k reads |
| | MUT_ORDER / MUT_MASK | FAIL as required |
| PQ root CAM (tools/s81/pq_root_cam_gate.py, iverilog) | OPC x PAR in {0,1}^2 | PASS CAM384; eight-leaf +4 / +7 / +5 / +8 vs native |
| | wrong_sibling, par_flip (PAR 1), buf_flip (PAR 1) | detected |
