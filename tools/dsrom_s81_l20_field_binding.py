#!/usr/bin/env python3
"""Emit the existing canonical I7/I8 controls and literal caller include.

Source metadata only: no checkpoint reads, arithmetic, model build or VM grant.
Compile the emitted l20_field_binding.hpp with the completed stage37 static cut.
"""
import argparse
import hashlib
import json
from pathlib import Path
from dsrom_s81_execution_binding import CanonicalS81Execution
from dsrom_s81_target_field_controls import emit
import v41_fullshape_isa as M


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--owner', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    execution = CanonicalS81Execution(a.owner)
    connectivity = json.loads((a.owner/'results/uarch/dsrom_s81_rd64_connectivity_20261004/canonical_binding_r1/connectivity.json').read_text())
    a.out.mkdir(parents=True, exist_ok=False)
    cpp = ['#pragma once', '#include "s81_minimum_qe.hpp"']
    operations = []
    for pc, producer in ((7, 2478), (8, 2479)):
        node = execution.source.nodes[f'L20.I{pc}']
        if 9+list(execution.source.nodes).index(node['id']) != producer:
            raise ValueError('canonical field producer ordinal changed')
        literal = node['instruction']
        word = M.I.encode(full_shape=True, **{k: tuple(v) if isinstance(v, list) else v
                                            for k, v in literal.items()})
        if hashlib.sha256(word.to_bytes(256, 'little')).hexdigest() != node['template_word_sha256']:
            raise ValueError('source literal changed')
        info = emit(execution, node['id'], 0, a.out/f'I{pc}', connectivity)
        if (info['stage'], info['phase'], info['rows'], info['output_base']) != (
                37, 18 if pc == 7 else 19, 320 if pc == 7 else 128,
                419776 if pc == 7 else 420096):
            raise ValueError('selected full field binding changed')
        cpp += [f'#include "I{pc}/native_field_bindings.hpp"',
                f'inline auto s81_native_field_i{pc}_bindings(uint64_t id)'
                '{return '+info['cpp_binding_symbol']+'(id);}']
        words = ','.join(f'{(word >> (32*i)) & 0xffffffff}u' for i in range(64))
        operations.append('{'+f'{producer},3,"{node["template_word_sha256"]}",'
                          '{'+words+'}}')
    cpp += ['inline std::array<DsromS81PrefixOperation,2> s81_l20_field_operations()'
            '{return {{'+','.join(operations)+'}};}',
            'inline std::vector<unsigned> s81_l20_field_bf_sites(){return {'+
            ','.join(map(str, execution.stage_join.stage_map['BF_site_IDs']))+'};}']
    (a.out/'l20_field_binding.hpp').write_text('\n'.join(cpp)+'\n')


if __name__ == '__main__':
    main()
