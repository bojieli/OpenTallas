#!/usr/bin/env python3
"""Controls for gb_hard_params.py (TOK-ALL-16): positive restore + 3 fail-closed mutants."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gb_hard_params import restore

REF = "    ot_s81_cfg7_seq #(.PQ(1), .LAYOUT(1), .PINREG(1)) u_s0 (.lc(a), .go_e(b));\n" \
      "    ot_s81_cfg7_seq_bfp #(.LAYOUT(1), .PINREG(1)) u_s1 (.lc(c));\n"
ACT = "    ot_s81_cfg7_seq u_s0 (.lc(a), .go_e(b));\n    ot_s81_cfg7_seq_bfp u_s1 (.lc(c));\n"
HP = {'masters': {'ot_s81_cfg7_seq': {'LAYOUT': '1', 'PINREG': '1', 'PQ': '1'},
                  'ot_s81_cfg7_seq_bfp': {'LAYOUT': '1', 'PINREG': '1'}, 'dsfd_bf_col': {}}}


def raises(f):
    try:
        f()
    except ValueError:
        return True
    return False


def main():
    out, r = restore(ACT, REF, HP)
    assert r['restored_calls'] == 2 and '.PQ(1)' in out and '(.lc(a), .go_e(b))' in out, out
    assert raises(lambda: restore(ACT, REF.replace('.PQ(1)', '.PQ(0)'), HP)), 'canonical disagreement not caught'
    assert raises(lambda: restore(ACT.replace('ot_s81_cfg7_seq u_s0', 'ot_s81_cfg7_seq #(.PQ(0)) u_s0'), REF, HP)), \
        'actual disagreement not caught'
    assert raises(lambda: restore(ACT.replace('u_s0', 'u_s9'), REF, HP)), 'absent canonical call not caught'
    print('gb_hard_params tests PASS (1 positive, 3 controls caught)')


if __name__ == '__main__':
    main()
