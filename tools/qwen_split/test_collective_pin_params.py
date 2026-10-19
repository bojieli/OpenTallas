#!/usr/bin/env python3
"""The release die must elaborate the same registered face form as its physical kit."""
import json
import sys
import tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/qwen_split')]
import die_params as P


def test_gen_registers_collective():
    params, _ = P.gen_params([('io_collective', P.COLL_MASTER)], [])
    assert params[P.COLL_MASTER]['TOK_REG'] == 1
    assert P.COLL_MASTER not in P.gen_params([], [])[0]


def test_audit_refuses_unregistered_or_missing_param():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / 'die.v').write_text('module die;\nendmodule\n')
        (d / 'pb.json').write_text(json.dumps({'masters': {P.COLL_MASTER: {
            'rtl': 'rtl/physical/ot_qfd_collective_static_io_production.sv'}}}))
        for value in (None, 0, 1):
            masters = {} if value is None else {P.COLL_MASTER: {'TOK_REG': value}}
            (d / 'die.v.params.json').write_text(json.dumps({'masters': masters}))
            result = P.audit(d / 'die.v', d / 'pb.json')
            assert result['verdict'] == ('PASS' if value == 1 else 'FAIL'), result
            if value != 1:
                assert any('TOK_REG' in x for x in result['fails'])


if __name__ == '__main__':
    test_gen_registers_collective()
    test_audit_refuses_unregistered_or_missing_param()
    print('COLLECTIVE_PIN_PARAMS PASS')
