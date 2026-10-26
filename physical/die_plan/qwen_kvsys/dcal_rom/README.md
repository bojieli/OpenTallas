# KV calibration profile ROM

`ot_rom_64x32_m2` is one content-independent generated ROM shape. Its 64x32 word
image is personalised by via map; the RTL master, LEF and TT/FF timing views do
not vary across schedules. The macro has a synchronous read on `clk` when
`ce_in=1`, address `addr_in[5:0]`, and output `rd_out[31:0]`. It has no reset or ECC.
Its behavioural parameters are `VIAMAP` and `INSTANCE`; synthesis uses the `_bb.v`
view plus the same LEF/Liberty for every content.

| Word address | Content |
|---|---|
| 0..35 | START[0..35], 20 bits zero-extended |
| 36 | PERIOD |
| 37,38 | TX_SEG1,RX_SEG1 |
| 39,40 | TX_SEG2,RX_SEG2 |
| 41,42,43 | ADM_OFS,ADM_LEN,FIRST_OFS |
| 44..63 | reserved zero |

The helper rejects START gaps below two clocks, a token-period wrap gap below
two clocks, admission overlapping the 66-word init stream, and first-token
admission overlap. The controller must prefetch the next START before it is
used; these profiles have minimum consecutive gaps 6,843..8,012 clocks. The ROM
conversion adds no production schedule cycles. Controller/boot integration is
qualified separately; these assets alone make no full-token or physical claim.

Regenerate the shape:

```
python3 tools/mem_compiler/kv_dcal_profile.py --compile-shape --out physical/asap7_memory_macros_v2
```

Generate one content from a generated SV localparam image:

```
python3 tools/mem_compiler/kv_dcal_profile.py --sv rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu.svh --out physical/die_plan/qwen_kvsys/dcal_rom/profiles/cal_mu
```

JSON profile inputs with START[36] and the eight named scalars use the same command
without `--sv`. Per-content manifests contain relative file names and can be checked
with `rom_gen.py verify --manifest ... --image ... --macro physical/asap7_memory_macros_v2/ot_rom_64x32_m2/ot_rom_64x32_m2.json`.
Every committed profile passed all 64 word read-backs and rejected a one-via mutant.
`cal_pair1024` was extracted from the current staged bind source and is explicitly
labelled a diagnostic until that source cohort is committed by the bind lane.

The compiler models an 8.856 x 9.192 um (81.404 um2) outline, TT clk-to-Q 242.899 ps,
and FF clk-to-Q 195.785 ps. These are the existing analytical macro models, not a
routed or transistor-level closure claim. The v2 abstract passed track alignment
for R0/MX/MY/R180 with M4 pins.
