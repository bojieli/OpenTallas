# Actual LM tail fixture for selected-station qualification

This is input/golden preparation, not a station PASS. The selected-station owner must use the actual safe/math source with its sender/receiver, NB parent register and two-sample BTAB path, and prove the three numeric words/index/last/drain/fault behavior. Preserve a causal old-counter failure. No global26 TOK/ARX/XC or upstream MAC claim follows from the two-station cut.

The preserved c50ae63c8 LM trace has a real 48-row tail (rows18944..18991), receiver slice8 and sender9, 3words/K for8K blocks. input.json contains192 valid halfwords combined into168 pin events, both original command words, all receiver BTAB packets, exact tail scale words264..266, three sender NB data words and three receiver scaled result words. No final output was repeated or padded. Every running partial remains the original real trace value.

The expected tail was also computed independently: recreate the original seed1 RNG stream from dv_lower_mat_bench.py, retain the final48 rows of W, then calculate G.matvec(W_tail,x,512) and multiply its BF16 row scales. All48 output bits equal the balanced tree over the trace's final cluster prefixes and real BTAB scales. The generator asserts both this equality and exact scale agreement. Source/event/extractor SHA256s are embedded.

The old timing is not a selected-safe programme proof: raw near words start3290, far starts3304; commands enter3280/3282 and land after the first near words. Protected safe-station configuration requires an explicit quiet earlier CFG and an owner-recorded timing adjustment. The complete selected parent schedule and previous-round drain remain separate obligations; no arbitrary global cycle cost or LP age is claimed here.

Recreate the fixture with the pinned c50 golden source:

```sh
git show c50ae63c8:tools/hdc_golden.py > /tmp/hdc_golden_c50.py
python3 tools/qwen_tokfunc/extract_lm_tail.py \
  --events results/rtl/tokfunc_qw_1021/lm_tail_da610/run/lm/lm_m0.ev.gz \
  --golden-source /tmp/hdc_golden_c50.py --out /tmp/lm_tail_pair_8_9.json
```
