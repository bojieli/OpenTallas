#!/usr/bin/env python3
"""Attention relative-SVG model, committed before compiler implementation.

Use independent golden csum8 subruns, not cuts through a live converter.
Every subrun starts/configures, consumes and publishes before the next starts.
No mode/be_mode tail words are deleted; neither pread nor req_lead is a cache read.
"""
from __future__ import annotations
import math


def model(rows_per_sm=64, subrun_rows=8, kv4=False):
    assert subrun_rows == 8, 'first prototype uses one golden csum8 subtree'
    row_bytes = 288 if kv4 else 528
    lines = math.ceil(row_bytes * subrun_rows / 136)
    nsub = math.ceil(rows_per_sm / subrun_rows)
    assert lines <= 64
    return dict(rows_per_sm=rows_per_sm, subrun_rows=subrun_rows,
                encoded_bytes_per_subrun=row_bytes * subrun_rows,
                lines_per_block=lines, descriptors_per_run=2 * nsub,
                hbm_bytes_per_run=2 * nsub * lines * 136,
                packet_bits_per_edge=1099, command_bits_per_edge=192,
                cache_line_bits=1088, svg_word_bits=135, xc_word_bits=173,
                programme_words_capacity=2048, descriptor_capacity=256,
                programme_replicas=2, programme_mux='existing paired 1024x256 SRAMs',
                cache_replicas=1, added_hardware_area_um2=0,
                new_boundary_registers=0, new_routing_tracks=0,
                cache_read_to_command_edges=1, go_to_first_command_edges=7,
                native_landing_padding_edges=8, regional_return_edges_unadopted=7,
                dense_consumer_attention_opt_in='mask dense valid bit25 only at unused dense decode; keep external command and packet/tag checks',
                provider_gap_edges=0, retire='last word after full result tail',
                context=dict(row_off=0,tag_base=0,lstep=0,fl=0,mrel=0,loops=1),
                golden='QK rows exact; each PV node is csum8, merge in original tree order',
                latency='actual compiler calendar length + fixed fetch/x-load/go gaps; measured in receipt',
                adoption='OPEN: residency, descriptor composition, exact RTL, physical parent')
