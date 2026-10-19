R6 bounded component source generator

This is a separate numerical testbench. The production R-mode guard remains
unchanged. No numerical simulation, synthesis, timing or physical PASS is
claimed by this source commit.

Generate only on a fleet host under the parent's unpinned ot-run admission:

    python3 tests/hbm_record6_component/generate.py \
      --inventory record6_inventory_final.json --front-words front_words.json \
      --operands operands.npz --source-binding source_binding.json OUTPUT

Runtime imports: NumPy; tools/hbm_static/{su_arith_generate,su_arith_compile,
su_programme_compile}.py; tools/hbm_layer_vehicle/layer_images.py and its imports
su_bench, hdc_golden and the hgi_sim package. Use the frozen cached tools package;
do not replace a live runtime package. The generator checks original A SHA,
authentic R, per-bank programme row identities/128-row capacity, all 160 sectors,
24 native bank identities and exact 1280-word coverage. Second-episode input is
an exact power-of-two scaling with a separately evaluated FP32 canonical tree.

Compile generated tb.sv with exact scoped_d4g/pgslice.sv SHA32e68, the new station41
module, ROOT_OPERAND qcore opt-in, unchanged qcore dependencies, actual stree
leaf/root and directional relay masters, native q0 VM face/core/body, programme
pslice_c5, host leaf and F20 calendar, CKgen/release and functional PLL. The scoped
pgslice includes its scoped arithmetic/store dependencies; do not also compile
the generic pgslice master with the same top name.

Initial source includes two serialized episodes, actual CP programme installation,
host descriptor rearm and full OLD-sector observation. Source-stage age assertions,
reset-abort/reinstall and causal mutant coverage are still required; this initial
bench cannot qualify the complete grant. Calendar phases/latencies remain source
predictions until the fleet run measures them. Coherent RF physical storage,
clock/reach/fanout/native timing and parent transport H remain HOLD.
