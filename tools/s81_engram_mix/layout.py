#!/usr/bin/env python3
"""Constructive MIX4 physical row view, with no numerical data or preload.

Actual native producer/consumer translators must implement this view before it
can qualify a program. The field/capture, HOP and HC paths are not rebound by
this algebraic witness. All counts are whole512-bit rows.
"""
import json


def row(address, color):
    if not 0 <= address < 512 or not 0 <= color < 32:
        raise ValueError('bank address/color out of range')
    return (address << 5) | (color ^ (address & 31))


def bank(physical_row):
    return (physical_row & 31) ^ (((physical_row >> 5) & 7) << 2)


def operand(kind, copy, beat, lane=0):
    if not 0 <= copy < 4 or not 0 <= beat < 160:
        raise ValueError('MIX shape is four copies of160beats')
    if kind in ('h','o'):
        if lane: raise ValueError('packed H has one row per beat')
        return row(beat, 5*copy)
    if kind not in ('k','w','v') or lane not in (0,1):
        raise ValueError('FP32 operands have two rows per beat')
    return row(beat+(160 if kind=='v' else 0), 5*copy+(3 if kind=='w' else 1)+lane)


def hidden_view(logical_row):
    if not 0 <= logical_row < 640: raise ValueError('H logical row out of range')
    return operand('h',logical_row//160,logical_row%160)


def witness():
    occupied={}
    for copy in range(4):
        for beat in range(160):
            for kind in ('h','k','w','v'):
                for lane in range(1 if kind=='h' else 2):
                    physical=operand(kind,copy,beat,lane)
                    if physical in occupied: raise ValueError(('alias',physical,occupied[physical]))
                    occupied[physical]=(kind,copy,beat,lane)
    for beat in range(160):
        for kinds in (('h','k','w'),('h','v')):
            reads=[operand(kind,copy,beat,lane) for copy in range(4)
                   for kind in kinds for lane in range(1 if kind=='h' else 2)]
            if len(set(map(bank,reads)))!=len(reads):raise ValueError(('read collision',beat,kinds))
        # Physical return quarter follows rowlow2. The fixed rotation preserves
        # the original20 logical lane identities without an arbitration queue.
        slots=[color^(beat&3) for color in range(20)]
        if set(slots)!=set(range(20)):raise ValueError('return permutation')
        for color,slot in enumerate(slots):
            if row(beat,color)%4 != slot%4:raise ValueError('return quarter')
    for width in (2,8):
        for start in range(0,640,width):
            if len({bank(hidden_view(i)) for i in range(start,start+width)})!=width:
                raise ValueError(('HC read bank conflict',width,start))
    if 20 in occupied:raise ValueError('descriptor slot20 overlaps data')
    return dict(schema='opentallas.s81.mix4.physical_view.v1',native_qualified=False,
                integration_ready=False,physical_row_formula='(address<<5)|(color^(address&31))',
                bank_formula='row[4:0] XOR {row[7:5],2b00}',copies=4,beats_per_copy=160,
                occupied_rows=len(occupied),descriptor_row=20,
                reduction_reads_per_edge=20,add_reads_per_edge=12,packed_writes_per_edge=4,
                V_replication='Actual shared V producer must write four physical copies:1280rows; no duplicate fixture preload qualifies',
                HC_logical_view='row n maps to address=n%160,color=5*(n//160); aligned2/8-row bursts have distinct banks',
                read_return_slot='logical_color XOR (address&3); inverse fixed delayed rotation',
                max_physical_row=max(occupied),
                missing=['actual field/constant/HOP ingress translators and V replication hardware',
                         'actual HC/HCP consumer row translators',
                         'MIX20 native request/return mapper and compile-time lane map',
                         'source-pinned fixed service/commit/calendar and physical phases'])


if __name__=='__main__':
    print(json.dumps(witness(),indent=1))
