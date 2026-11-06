Optional native XOR SAT dependency
==================================

`lec.py` already calls `xor_sat` after ABC leaves a compare cone undecided.
It retains the complete original AIG CNF and adds redundant exact XOR
identities. This staging change does not change proof algorithms or gates.

Use the pinned Python 3.10 wheel
`pycryptosat-5.17.0-cp310-cp310-manylinux_2_34_x86_64.whl`, SHA256
`15dff341a2b98368497f54f85326e0e8056684d73fbb5867998152fd7cf58746`.
Acquire it with pip download for the image ABI, then stage a local copy:

```
python3 tools/die_plan/stage_lec_xor.py WHEEL OUTDIR
export OT_LEC_SOLVER=/absolute/path/to/OUTDIR
```

The extracted extension and its bundled `.libs` directory must stay together.
The wheel is cp310/x86_64 and requires glibc 2.34; it was import-tested in
`openroad/orfs:latest` Python 3.10. A different image ABI needs a separately
measured artifact, not this wheel. No global pip install or image mutation is
needed. Leaving OT_LEC_SOLVER unset preserves current behavior.

Measured 2026-11-06: q3_link rightwidth synthesis LEC had 10949 compare points,
10948 proved, 0 differs, 1 undecided (g_rxpre.ne_q; 612 matched support inputs).
The saved miter output 6590, with 612 support inputs, was reconstructed using the
unchanged Aig normalizer and proved by unchanged xor_sat 5.17.0 in 44.908 seconds:
38825 cone variables,12653 redundant XOR identities. This diagnostic does not
replace canonical full-kit LEC or routed LEC. Full canonical proof remains
required before adoption.

Diagnostic evidence:
epyc2:/srv/opentallas-scratch2/claude/codex-q3-crc-1106/direct_xor.py
intel2:/srv/opentallas-scratch2/claude/codex-q3-crc-1106/log/direct_xor.otrun.log
Original failed records and active full proof remain untouched.
