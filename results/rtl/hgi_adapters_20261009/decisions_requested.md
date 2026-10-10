# hgi-adapters: decisions requested (2026-10-09 ~12:00 PT)

## D1 (BLOCKING for SU / FUSED / ATT / HC peers): one VM with two port classes
The generic die has TWO vector memories today: the legacy hfd_vm tiles (wide streaming: x staging 2 x 2,048 b, SU
f_vm / t_vm 2,048 b a quarter, result publication) and the HGI VM (ot_hgi_vm_unit: 1 MiB, 32 banks, PACKET clients,
one sector request outstanding per client, ~5 edges a round trip).  HGI programs address ONE VM (262,144 words).
The engines the remaining peers must feed read VM at full width:
- SU vec (ot_hdc_v41x_vec): every lane reads up to 4 operands + a gather index a cycle (N = 1,024: > 4,000 words a
  cycle); the hub envelopes feed it from the legacy 2,048-b buses.
- FUSED engines (ot_hbm_accel_su_fused_stream, ot_dsrom_su_norm): one N x 32 operand vector a cycle.
- ATT tiles: q / p loads + KV rows (svc PS), outputs 512 b a cycle.
- HC (ot_hdc_v41x_hcp): 8 x / 8 w reads a cycle.
A packet client delivers ~1.6 words a cycle (measured: ARGMAX 37,984 logits in 38,015 cycles; quant ~81 cycles / 32
values).  Gluing these engines to the HGI VM is correct but 100-1,000x slower than their datapaths; gluing them to the
legacy hfd_vm breaks the single address space (a record's operand written by a packet client is invisible to them).
**Proposal:** one VM macro array (the HGI VM's 64 SECDED macros, 32 banks) with BOTH port classes: (a) the packet
clients (as today) and (b) K wide streaming ports (a sector per bank per cycle, address generators per stream:
base / stride / count, the SU / FUSED / x-load / publication / ATT q-p ports), arbitrated per bank; the legacy hfd_vm
tiles retire.  32 banks x 256 b = 8,192 b a cycle peak covers SU N = 256 at 4 operands, or N = 1,024 at 1 operand.
Decision owner: hgi-takeover (VM) + coordinator.  Until then the peers I built use packet clients (exact, slow):
DMA mover, SM x-load, SM publication, ARGMAX, FUSED gain staging.

## D2: SM layout rule (spec 10.3) — what the image builder must write
Lines, not raw rows: SM s's block = rows [s Q, min((s+1) Q, M)) (Q = ceil(M / 32)), written as that SM's weight LINES
in its group-slot ISSUE ORDER (tools/dshbm_matched_sm_seq.gen_op), line = 136 B (DS 1,088-b line) or 160 B (INT8
transport); block s starts at line B.base / LB + s Q LPR (LPR = 8 op_g lines a row, INT8 4 op_g); B.stride = LPR x LB.
hbm-sim's images hold raw K-byte rows (refused by the adapter: hbm-sim must emit the line image).

## D3: DS block-dot x (FP8 / FP4 SM formats)
The SM x store for block-dot formats holds quant_fp8(x) codes + block exponents, not BF16.  The x-load refuses
fmt 1 / 2 until the activation quantiser feeds it (FUSED.QDQ yields dequantised values, not codes): proposal = the
x-load re-encodes QDQ'd values (exact on the E4M3 grid, exponent = the block's UE8M0) — small, or route x through the
quant unit.  Decision: hbm-sim / DS owner.

## D4: ATT controller
The HBM attention tiles are packet pipes ({ld, query} packets).  The ks-row -> ld-packet formatter (RQ-HF-4) and the
q / p loader need the ATT LOAD PROTOCOL (which bank / group a streamed KV row and a query slice land in, QK vs PV
roles) — not defined anywhere in the repo (hbm-forks RQ-HF-4 "open, ATT program owner").  Not glue: a dataflow design
item with exactness consequences (8-entry split, chunk order).  ot_hgi_att_issue emits the job word; the controller is
the open item.
