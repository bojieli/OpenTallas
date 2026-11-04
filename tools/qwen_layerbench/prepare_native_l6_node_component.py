#!/usr/bin/env python3
"""Extract the selected native node faces and actual arithmetic component.

Source preparation only. Distinct native clocks stay explicit; numerical input
must later come from authenticated native TG4 outputs, not reference L6 sums.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def once(pattern, text, label):
    matches = list(re.finditer(pattern, text, re.S))
    if len(matches) != 1:
        raise ValueError('exact selected source span missing: '+label)
    return matches[0].group()


def emit(rp2, logic, node):
    r, l, n = rp2.read_text(), logic.read_text(), node.read_text()
    if 'parameter integer REGROOT = 0' not in r or 'if (REGROOT >= 6)' not in r:
        raise ValueError('native reset selection changed')
    if '.n_va(n_a_q[512])' not in r or 'assign na_x = n_a;' not in l:
        raise ValueError('selected normal native node operand/valid connection changed')
    if 'ot_qwen_w12_tadd #(.LAT(7), .ANR(2))' not in n:
        raise ValueError('actual native node arithmetic profile changed')
    reset = once(r'\(\* keep \*\) reg q;\s*always @\(posedge ck_fa4\) q <= rst_n;\s*assign reset_q = q;', r, 'REGROOT3 reset')
    faces = once(r'\(\* keep \*\) reg \[513:0\] n_a_q,n_b_q;\s*always @\(posedge ck_fa0\) n_a_q<=n_a;\s*always @\(posedge ck_fa1\) n_b_q<=n_b;', r, 'native operand faces')
    tail = once(r'\(\* keep \*\) reg fy_q;\s*reg mis_q;.*?assign n_y=n_y_q;', r, 'native packed result/fault face')
    inner = once(r'ot_qwen_tile_node u_node \(.*?\.t_out\(t_out_nd\), \.t_vout\(t_vout_nd\)\);', l, 'actual selected node instance')
    # The selected BMUT0/CHILD_CLOCKS1 branch is copied exactly. Its ME-result
    # feed-through is independent of arithmetic a/b/y and is an explicit unused
    # component input here; it is not driven with a fabricated ME result.
    sv = '''`timescale 1ns/1fs
// SOURCE ONLY: selected REGROOT3/BMUT0/CHILD_CLOCKS1 native node component.
// Independent clocks remain public. No selected phase or count origin implied.
module qwen_native_l6_node_component (
 input wire ck_fa0, ck_fa1, ck_fa3, ck_fa4, ck_node,
 input wire rst_n,
 input wire [513:0] n_a, n_b,
 input wire [511:0] td_x,
 input wire t_vout_i,
 output wire [513:0] n_y,
 output wire node_fault,
 output wire [511:0] t_out_nd,
 output wire t_vout_nd
);
 localparam integer CHILD_CLOCKS=1;
 wire reset_q;
'''+reset+'\n'+faces+'''
 wire [511:0] na_x=n_a_q[511:0];
 wire n_va=n_a_q[512];
 wire [511:0] ny;
 wire nvy;
 wire clk=ck_node;
 wire rst_n_inner=reset_q;
'''
    # Preserve the selected instance's original pin expressions using a tiny
    # lexical scope for its original local names, without altering clock/data.
    sv += ' generate begin : selected_inner\n'
    sv += ' wire rst_n=rst_n_inner;\n wire [511:0] n_b=n_b_q[511:0];\n wire [511:0] n_y;\n wire n_vy;\n'
    sv += inner+'\n assign ny=n_y;\n assign nvy=n_vy;\n end endgenerate\n'
    sv += tail+'\nendmodule\n'
    return sv, dict(schema='native_l6_node_component_source/1', status='SOURCE_ONLY_NOT_EXECUTED',
                    selected_profile=dict(REGROOT=3, BMUT=0, CHILD_CLOCKS=1, TREE_LAT=7, ANR=2),
                    source_sha256={str(p): sha(p) for p in [rp2, logic, node]},
                    copied_source_spans=dict(reset=reset, operand_faces=faces, inner=inner, packed_output=tail),
                    native_clocks=['ck_fa0','ck_fa1','ck_fa3','ck_fa4','ck_node'],
                    arithmetic='16 actual FP32 pair adders, same input/valid/output and reset relay as selected source',
                    fault='selected outer leg-fault OR/sticky valid mismatch and packed output preserved; inner node_fault separately observable as in source',
                    unused_ME_feedthrough='td_x/t_vout_i remain explicit public inputs, not fabricated executed ME values',
                    usage='reuse complete component for15 source-proven adjacent subtrees per64split L6 after authenticated native TG4 outputs exist',
                    qualification='no build, fabricated L6 response, physical/provider phase, count-origin or global date claim')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('rp2','logic','node','out'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(); sv, manifest=emit(a.rp2,a.logic,a.node)
    a.out.mkdir(parents=True,exist_ok=False)
    (a.out/'qwen_native_l6_node_component.sv').write_text(sv)
    (a.out/'source.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(manifest['status'], 'native_clocks',len(manifest['native_clocks']))


if __name__=='__main__':
    main()
