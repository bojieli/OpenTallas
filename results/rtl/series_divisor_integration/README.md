# Integrating the prior session's series-divider tuning

This commit retains the existing workspace RTL changes without modifying their
arithmetic or default step size. Both exponential engines derive divisor width
from `SERIES_TERMS + 2` and expose `DIV_BITS_PER_STEP`, default 10. Default 56-term
series therefore use six divisor bits; larger supported series retain sufficient
width. The previous committed engines used nine bits unconditionally.

Validation:

- `python3 -m pytest -q tests/compiler/test_series_divisor_width.py`: both positive
  and nonpositive engines compared with nine-bit reference variants, series
  lengths 56/64/254 at step10 and 56 at step4. Tests compare handshake timing,
  result and certification; exp(±1) also has an independent expected result.
- Positive exponential: pinned Verilator 5.050, `tb_a3_exp_pos`, with sources
  `ot_wide_mul_seq`, `ot_wide_div_small_seq`, and `ot_a3_fp32_exp_pos_cr_rne`.
  Generate vectors with `tools/build_a3_exp_pos_vectors.py --out <directory>`;
  run the executable from that directory. Vectors and log are retained here.
- Full exp/sigmoid: `../small_divider_scratch_reset/transcendental.log` records
  4,200 cases and 6,637,132 checks. Its RTL/vector source hashes match this
  integration exactly; the test-harness Python file subsequently changed and
  is not used as proof of arithmetic source identity.

The positive corpus covers correctly rounded finite exponentials and four
refusal/overflow checks. It does not add reset/backpressure coverage to the
positive engine. Full exp/sigmoid testing includes reset and output stalls.
This integration does not claim a new physical clock: current engine routes
remain pending and source/configuration specific.
