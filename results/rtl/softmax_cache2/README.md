# Two-entry exact exponential reuse

The candidate keeps the last two successful service results. New evaluations
shift the prior newest entry into the second slot. Cache hits do not reorder
entries. A bit-identical offset selects the newest matching entry, otherwise the
second; operation and arithmetic configuration remain immutable. Errors never
install results, and reset invalidates both slots. The second payload bank is
unreset and inaccessible until its validity bit is set.

The real numerical corpus reduces four service evaluations and 5,768 cycles.
This is corpus-specific: it does not establish model-level throughput. Mapped
area rises 0.36%, while whole-block prelayout slack worsens. Production remains
unchanged pending an integrated timing/throughput decision.

Run `python3 -m pytest -q tests/test_softmax_exp_reuse.py` for the protocol
checks. The real numerical run uses tb_a3_softmax_block with the source list in
sources.json and working directory build/softmax_exp_reuse_vectors. The baseline
log and exact source inventory are retained in small_divider_step4_current.
