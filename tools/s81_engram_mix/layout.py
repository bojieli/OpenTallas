#!/usr/bin/env python3
"""Constructive MIX4 physical row view, with no numerical data or preload.

Actual native producer/consumer translators must implement this view before it
can qualify a program. The field/capture, HOP and HC paths are not rebound by
this algebraic witness. All counts are whole512-bit rows.
"""
import json

# H LAYOUT (S-FUNC main 5e562b628, dsfd_engram_mix4_c HLAYOUT=1, production): H/output rows are HC hidden rows; HC row
# n = 4b+q holds elements 8n..8n+7 of all four copies and MIX beat b reads/writes HC rows 4b..4b+3 (cluster q -> 4b+q).
# Physical slots: address b, colour HCOL[b&1][q].  Even beats keep the H colours 0,5,10,15; odd beats use 20..23,
# because bank(address b+1) = bank(address b) ^ 5 for the same colour and {0,5,10,15}^5 = {0,5,10,15}: with one colour
# set every aligned 8-row HC burst (beats 2m, 2m+1) would hit each bank twice.  {20..23}^5 is disjoint from
# {0,5,10,15} and from the K/W colours, so REDUCE/ADD/WRITE per-beat sets stay bank-distinct.  HLAYOUT=0 = 10-14 view.
HLAYOUT=1
HCOL=((0,5,10,15),(20,21,22,23))


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
        if HLAYOUT: return hidden_view(4*beat+copy)
        return row(beat, 5*copy)
    if kind not in ('k','w','v') or lane not in (0,1):
        raise ValueError('FP32 operands have two rows per beat')
    if kind=='v':
        # ONE shared V copy (dsfd_engram_mix4_c reads V once on cluster0 lanes1,2 and broadcasts it): address
        # 160+beat, colors 1,2 for every copy.  (160+beat)&31 == beat&31 and bits[2:0] agree, so V lands on the
        # banks of colors1,2 at that beat: disjoint from the four H colors 0,5,10,15 read in the same ADD edge.
        return row(beat+160, 1+lane)
    return row(beat, 5*copy+(3 if kind=='w' else 1)+lane)


def hidden_view(logical_row):
    if not 0 <= logical_row < 640: raise ValueError('H logical row out of range')
    if HLAYOUT:
        b,q=divmod(logical_row,4)
        return row(b,HCOL[b&1][q])
    return operand('h',logical_row//160,logical_row%160)


def witness():
    occupied={}
    for copy in range(4):
        for beat in range(160):
            for kind in ('h','k','w','v'):
                if kind=='v' and copy: continue          # the single shared V copy
                for lane in range(1 if kind=='h' else 2):
                    physical=operand(kind,copy,beat,lane)
                    if physical in occupied: raise ValueError(('alias',physical,occupied[physical]))
                    occupied[physical]=(kind,copy,beat,lane)
    for beat in range(160):
        reduce_reads=[operand(kind,copy,beat,lane) for copy in range(4)
                      for kind in ('h','k','w') for lane in range(1 if kind=='h' else 2)]
        add_reads=[operand('h',copy,beat) for copy in range(4)]+[operand('v',0,beat,lane) for lane in (0,1)]
        writes=[operand('o',copy,beat) for copy in range(4)]
        for name,acc,n in (('reduce',reduce_reads,20),('add',add_reads,6),('write',writes,4)):
            if len(acc)!=n or len(set(map(bank,acc)))!=n:raise ValueError((name+' bank collision',beat))
        # Physical return quarter follows rowlow2. The fixed rotation preserves
        # the original20 logical lane identities without an arbitration queue.
        slots=[color^(beat&3) for color in range(20)]
        if set(slots)!=set(range(20)):raise ValueError('return permutation')
        for color,slot in enumerate(slots):
            if row(beat,color)%4 != slot%4:raise ValueError('return quarter')
        for name,acc in (('reduce',reduce_reads),('add',add_reads)):
            groups=[r%4 for r in acc]
            if max(groups.count(g) for g in range(4))>8:raise ValueError((name+' scatter lane group >8',beat))
        for copy in range(4):   # H return quarter = logical H lane 5*copy's slot quarter (odd-beat colours 20+copy)
            if operand('h',copy,beat)%4 != ((5*copy)^(beat&3))%4:raise ValueError(('H return quarter',beat,copy))
    for width in (2,4,8):
        for start in range(0,640,width):
            if len({bank(hidden_view(i)) for i in range(start,start+width)})!=width:
                raise ValueError(('HC read bank conflict',width,start))
    if 20 in occupied:raise ValueError('descriptor slot20 overlaps data')
    return dict(schema='opentallas.s81.mix4.physical_view.v1',native_qualified=False,
                integration_ready=False,physical_row_formula='(address<<5)|(color^(address&31))',
                hlayout=HLAYOUT,H_colours=('even beats 0,5,10,15; odd beats 20..23' if HLAYOUT else '5*copy'),
                bank_formula='row[4:0] XOR {row[7:5],2b00}',copies=4,beats_per_copy=160,
                occupied_rows=len(occupied),descriptor_row=20,
                reduction_reads_per_edge=20,add_reads_per_edge=6,packed_writes_per_edge=4,
                V_copies=1,V_rows='320 rows: address 160..319, colors 1,2 (read once by cluster0 lanes1,2, broadcast in dsfd_engram_mix4_c)',
                vm_service=dict(read_lanes=20,write_lanes=4,reduce_edge_reads=20,add_edge_reads=6,edge_writes=4,
                                bank_rule='each edge: <=1 read and <=1 write per bank (1R1W); proven per beat above'),
                HC_logical_view=('HLAYOUT=1: HC row n=4b+q -> address b, colour HCOL[b&1][q]; aligned 2/4/8-row bursts have distinct banks' if HLAYOUT else 'row n maps to address=n%160,color=5*(n//160); aligned2/8-row bursts have distinct banks'),
                read_return_slot='logical_color XOR (address&3); inverse fixed delayed rotation',
                max_physical_row=max(occupied),
                missing=['actual field/constant/HOP ingress translators (V written once: no replication)',
                         'actual HC/HCP consumer row translators',
                         'MIX20 native request/return mapper and compile-time lane map',
                         'source-pinned fixed service/commit/calendar and physical phases'])


if __name__=='__main__':
    print(json.dumps(witness(),indent=1))
