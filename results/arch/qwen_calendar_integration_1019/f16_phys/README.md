# F16 WTN1 witness controller: SAFE_PHYS structural candidate (QW-F16PROG3, 10-19)

Source: `rtl/qwen_dv/qfd_dv_typed_witness_control.sv` parameter `SAFE_PHYS` (default 0; requires
SAFE_SELECT=SAFE_COMPARE=1). With SAFE_PHYS=0 the legacy always block is byte-identical (generate `gl`).
Hashes: `source.sha256`; netlist/library hashes: `artifacts.sha256`.

## What changed (structure, not tuning)
- **Faces**: every input is pin-registered (+1 edge) and every output is registered (+1 edge). All inputs
  shift together, so every internal relation (PW order, seal, start, publication +1, use +2, retirement)
  is unchanged; every output equals the legacy output delayed by exactly 2 edges. No comb in->out path.
- **Reset**: lands in 2 registered stages (async assert / sync release, rst_n fanout 2), then 3 kept
  leaf copies (install 28, run 25, outputs 17 sync loads; max 26 measured). Data state is unreset and
  qualified by reset control state; select/publish/enable sectors are plain kept registers whose D is
  idle while held in reset. Removes the 899-load raw reset, the 896 tied SETN (no ASR flops left) and
  the 523-load rst_n-gated enable.
- **Template/partial store**: decision -> kept registered write-enable sectors -> write one edge later
  (13 records x 9 sectors <=15 bits; partial 2x4 sectors x16 bits). Reads are >=3 edges later (seal ->
  start -> pick), so no read sees the delay. Template stays 1742 FF bits (<=2048, ROOT choice).
- **Arbiter/counters**: 4 kept rr copies (one per arbitration step), a kept active copy per user that
  only enables the 6 counter copies, and 24 kept start decodes at the pin face (one per counter copy).

## Results (fleet ot-epyc8, Verilator 5.050, ORFS asap7lock Yosys + pinned ASAP7 libs)
- Functional unit oth-ubuntu-83938-1792453279: `F16_SAFE_PHYS_FUNCTIONAL_PASS`. All 28 stimuli paired with
  the legacy controller at LAG 2 on every edge (nominal 65 completions / 5 retirements / 4 live users;
  27 stimulus mutants FAIL); SAFE_SELECT baseline still edge-exact on all 28; EN=0 zero outputs;
  unsigned 8190+255 cache overflow exact; sector coverage 13 groups / 8 banks / 4 users; landed reset clears
  pending/cache/ready ownership. 7 mechanism mutants FAIL (5 inherited + TPL_WRONG + RLEAF_STUCK), see
  `witness_index.json`.
- Native census unit oth-ubuntu-84215-1792453279 (same census.py, all roles, BUF/INV transparent):
  4666 FF / 22596 cells / 2682.33 um2 (seq 1360.78). Max loads: **FF 32, input 5, constant 3**, comb 45.
  Over 32: 5 combinational nets only (36-45: four in the start-accept cone, one bank-3 field match).
  Baseline f16_selects: 51 roots >32 (input 899, constant 896, comb 523, FF 54), 4172 FF, 2661.29 um2.
  Kept-copy survival (`survival.json`): 195 select, 112 publish, 312 counter, 117 template-enable,
  8 partial-enable, 3 reset leaves, 24 start decodes, 4 counter-active copies all distinct.

## SAFE-DESIGN checklist (source level)
1 Pins: PASS (all inputs/outputs registered; reset 2 registered stages + kept leaves).
2 Reach: n/a inside (~2.7k um2 block); parent placement owns.
3 Fanout: PASS for registers (max 32). WAIVED: 5 comb nets 36-45 loads (buffered by repair_design; no
  register > 32; ABC refactors these cones, two restructurings measured 100/113, kept the 45 form).
4 Depth: OPEN (no STA yet); no comb in->out path.
5 Storage: PASS (template 1742 b FF per ROOT <=2 kb; read by one-hot kept selects, no runtime-indexed read).
6 Floorplan / 7 Clock: parent (CTLM region); 4666 sinks.
8 Schedule: +2 edges on witness outputs (template_ready, fault, group_complete, all_witnesses_complete),
  0 SU/token cycles, 0 added PW (WTN1 uses 39 zero PW400..438 of the 1024-PW image), retire/start rules
  unchanged relative to the controller's own inputs. Handed to QW-TOK.

## Still open (not claimed)
Parent instantiation in CTLM/SYSFACE (actual dh_q PW capture, all-copy auth withdrawal, ME/XPF final
read retirement), mapped STA/depth, and a real gate. `tools/qwen_layerbench/ctlm_image.py --wtn1` now
splices the template into the tt_ctlm deployment image (refuses on any PW400..438 collision).
