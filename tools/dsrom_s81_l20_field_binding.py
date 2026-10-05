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
    p.add_argument('--connectivity', type=Path, help='Retained canonical return connectivity when staged outside owner')
    p.add_argument('--pcs', default='7,8', help='Existing I7/I8 or opt-in I14 consumer of produced native QR')
    p.add_argument('--fragment', type=int, choices=(0,1), help='Mandatory explicit I14 canonical fragment; no full-output claim')
    a = p.parse_args()
    pcs = [int(pc) for pc in a.pcs.split(',')]
    if pcs not in ([7,8], [14]):
        raise ValueError('selected ordered field scope must be I7/I8 or I14')
    if (pcs==[14]) != (a.fragment is not None):
        raise ValueError('I14 requires an explicit fragment; I7/I8 remain unchanged')
    execution = CanonicalS81Execution(a.owner)
    connectivity = json.loads((a.connectivity or a.owner/'results/uarch/dsrom_s81_rd64_connectivity_20261004/canonical_binding_r1/connectivity.json').read_text())
    a.out.mkdir(parents=True, exist_ok=False)
    cpp = ['#pragma once', '#include "s81_minimum_qe.hpp"']
    operations = []
    for pc in pcs:
        producer = 2471+pc
        node = execution.source.nodes[f'L20.I{pc}']
        if 9+list(execution.source.nodes).index(node['id']) != producer:
            raise ValueError('canonical field producer ordinal changed')
        literal = (execution.dispatch(node['id'],0)['fragments'][a.fragment]['instruction']
                   if a.fragment is not None else node['instruction'])
        word = M.I.encode(full_shape=True, **{k: tuple(v) if isinstance(v, list) else v
                                            for k, v in literal.items()})
        literal_hash=hashlib.sha256(word.to_bytes(256, 'little')).hexdigest()
        if a.fragment is None and literal_hash != node['template_word_sha256']:
            raise ValueError('source literal changed')
        calls = []
        for rank in range(4):
            directory = a.out/f'rank{rank}'/f'I{pc}'
            image=(a.owner/'results/rtl/dsrom_recovery_20261004/immutable_stage_controls/stage37'
                   if a.fragment is not None else None)
            info = emit(execution, node['id'], rank, directory, connectivity,
                        fragment_index=a.fragment,stage_image=image)
            expected = {7:(37,18,320,419776),8:(37,19,128,420096)}
            if pc in expected and (info['stage'], info['phase'], info['rows'], info['output_base']) != expected[pc]:
                raise ValueError('selected full field binding changed')
            if pc == 14 and (info['stage'],info['phase'],info['rows'],info['output_base'],literal['qe_xbase'],literal['qe_nb']) != (
                    (37,20,4608,55744,52928,40) if a.fragment==0 else (37,21,3584,60352,52928,40)):
                raise ValueError('canonical I14 QR-to-Q field dimensions changed')
            if pc==14 and info['instruction'] != literal:
                raise ValueError('rank fragment instruction differs from selected literal')
            # Rank selects source/CFG ownership; the native leaf has no RANK parameter.
            for filename in ('spine_phase.hex', 'spine_stream.hex'):
                if rank and (directory/filename).read_bytes() != (a.out/'rank0'/f'I{pc}'/filename).read_bytes():
                    raise ValueError(f'rank{rank} {filename} differs from the retained rank0 native body')
            symbol = info['cpp_binding_symbol']
            unique = symbol+f'_r{rank}'
            header = directory/'native_field_bindings.hpp'
            header.write_text(header.read_text().replace(symbol, unique))
            cpp.append(f'#include "rank{rank}/I{pc}/native_field_bindings.hpp"')
            calls.append(f'case {rank}:return {unique}(id);')
        cpp.append(f'inline auto s81_native_field_i{pc}_bindings(uint64_t id,unsigned rank)'
                   '{switch(rank){'+''.join(calls)+
                   'default:throw std::runtime_error("field rank outside 0..3");}}')
        words = ','.join(f'{(word >> (32*i)) & 0xffffffff}u' for i in range(64))
        operations.append('{'+f'{producer},3,"{literal_hash}",'
                          '{'+words+'}}')
    cpp += [f'inline std::array<DsromS81PrefixOperation,{len(pcs)}> s81_l20_field_operations()'
            '{return {{'+','.join(operations)+'}};}',
            'inline std::vector<unsigned> s81_l20_field_bf_sites(){return {'+
            ','.join(map(str, execution.stage_join.stage_map['BF_site_IDs']))+'};}']
    if pcs==[14]:
        cpp += [f'inline constexpr unsigned s81_qfield_output_base={literal["qe_obase"]};',
                f'inline constexpr unsigned s81_qfield_output_rows={literal["qe_nout"]};',
                f'inline constexpr unsigned s81_qfield_fragment={a.fragment};']
    (a.out/'l20_field_binding.hpp').write_text('\n'.join(cpp)+'\n')


if __name__ == '__main__':
    main()
