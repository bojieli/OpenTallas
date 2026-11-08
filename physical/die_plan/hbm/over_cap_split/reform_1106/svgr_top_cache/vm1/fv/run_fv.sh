#!/bin/bash
cd "$(dirname "$0")" || exit 2
for s in prod cache issuer issuer_inv; do yosys -q -l $s.log $s.ys >/dev/null 2>&1; echo "FV $s rc=$?"; grep -E "SUCCESS|FAIL|failed|proven|Found|unproven|Induction step proven|ERROR" $s.log | tail -4; done
