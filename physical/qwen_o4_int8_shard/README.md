# Qwen O4 signed-INT8 ROM shard physical probe

This probe places one `ot_rom_8192x266_m8` analytical ASAP7 ROM abstract
beside 32 signed-INT8 product lanes and one post-accumulation row-scale path.
The first 256 ROM output bits provide 32 codes (two 16-lane O4 groups); ten
bits are spare. It runs at the O4 0.92 ns target. The top-level lane selector
keeps all 32 products live while bounding I/O pins; it is a probe-specific
path, not the O4 reduction tree. The shard now registers the ROM output before
INT8 decode, matching `ot_hdc_matvec`'s `mq_wrom` boundary. Request valid,
BF16 activation, and lane select are delayed with their code word. The two
16-lane groups have independent BF16 activation inputs, matching the core's
per-group vector-memory reads. The focused
stream test (`python3 tools/rtl_qwen_o4_int8_shard_pipeline.py`) changes ROM
address, selected lane and activation each cycle and checks 112 exact signed
INT8 products, including 64 consecutive requests, with seven-edge response latency. The
test covers this bounded arithmetic path, not a complete token.

The source-pinned O4 design record requires 6,144 groups × 16 codes =
98,304 code bytes read per die per cycle. If this 256-useful-bit macro were
the building block, 3,072 macros would read concurrently. The target plus
drafter has 9,243,527,168 weight bytes total; split equally, 4,621,763,584
bytes per die. At 262,144 useful bytes per macro, that needs 17,631 macros
per die. The compiler abstract area gives 257.24 mm² per die for these
macros, versus 253.41 mm² per die in the O4 model for target and drafter ROM.
This 3.83 mm² difference alone does not settle the design: banks, word
selection, lane wires, spare bits, power, timing and placement still need a
die floorplan. The macro LEF and Liberty are compiler **analytical views**;
the bitcell was laid out, but the macro periphery and current were assumed.

The registered-ROM grouped probe passes global route, and the worst
macro-output-to-capture setup path has **+36.33 ps** slack at the 0.92 ns
clock. The whole probe still fails setup: its worst path launches from an
activation register into a BF16 product lane at **−1,079.59 ps**. This is
global-route STA, not extracted detailed-route timing. The record and compressed
logs are in `results/physical_hdc/asap7/qwen_o4_int8_shard_pipeline/`.
Activation fanout, multiplier placement and the row-scale path still need
timing repair before claiming the O4 clock.

The probe uses Yosys 0.68 and OpenROAD v2.0-17598-ga008522d8, ASAP7 RVT TT
at 0.7 V. It is a direct placement/route diagnostic with no PDN, DFT,
antenna repair, formal equivalence or chip signoff. The physical record in
`results/physical_hdc/asap7/qwen_o4_int8_shard/` states the exact reached
stage, timing, DRC and source hashes. No full G=6144 tile or die route is
implied by this shard.

Historical direct-flow record (pre-registration, `global_route.json`; its source pins name the unregistered shard RTL, which the registered-ROM change below replaced):

The global-route STA checks the ROM pins directly. The worst ROM-output to
first product register path launches at 794.62 ps and arrives at 2,127.78 ps:
1,333.16 ps after the ROM output, for −1,218.18 ps setup slack at the
0.92 ns target. This path needs a registered ROM-output/code stage or a
different nibble-product schedule before the current BF16 product pipeline.
The full global-route worst path is an internal product stage at −2,347.08 ps;
this direct flow has not repaired slew, so it is a diagnosis, not closure.

To replay the pilot, check out its source commit at
`/tmp/opentallas-qwen-o4-physical-lane`, create
`/tmp/qwen-o4-shard-route`, and run:

```bash
/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys -s physical/qwen_o4_int8_shard/synth.ys
python3 physical/qwen_o4_int8_shard/prepare_mapped.py
openroad -exit physical/qwen_o4_int8_shard/place_route.tcl
openroad -exit physical/qwen_o4_int8_shard/macro_sta.tcl
openroad -exit physical/qwen_o4_int8_shard/detailed_route.tcl
```

Registered-ROM probe (ported from Codex branch `codex/qwen-int8-rom-pipeline`, commit `eadcbcc7`).
To replay this registered-ROM probe and collect its source-pinned record, run:

```bash
python3 tools/qwen_o4_int8_shard_pipeline_physical.py \
    --workdir /tmp/qwen-o4-shard-pipeline-groups-route
```

The runner generates worktree-specific Yosys and OpenROAD scripts, maps the
netlist, places and globally routes the shard, then writes an STA report for
all ROM outputs. It strips signed declarations from the mapped netlist only
because OpenROAD's Verilog reader rejects them; the mapped cell logic is
unchanged. The detailed-route Tcl remains available for a follow-up and is
not part of this record.
