#!/usr/bin/env python3
"""Ordinary GPU row-owner placement alternative; analytical only, no RTL/adoption.

Whole rows retain their existing die/SM owner and numerical reduction recipe.
Each SM uses an ordinary base-pointer descriptor to read a page-aligned weight
shard on the corresponding quadrant stack. No memory-network bandwidth is free.
"""
import math


def quad(sm): return (sm//16)*2+(sm%8)//4


def striped_lines(base,size):
    if size==0:return [0]*4
    first,last=base//128,(base+size-1)//128
    return [max(0,(last-s)//4-(first-1-s)//4) for s in range(4)]


def compare(manifest):
    rows=[]
    for d in manifest['matrix_weight_demand_instances']:
        slots=[];old_local=old_cross=old_cross_commands=0;new_lines=capacity=0
        for sm in range(32):
            first=d['output_rows']*sm//32;last=d['output_rows']*(sm+1)//32
            size=(last-first)*d['K'];q=quad(sm)
            lines=striped_lines(d['code_base']+first*d['K'],size)
            old_local+=lines[q];old_cross+=sum(lines)-lines[q]
            old_cross_commands+=sum(math.ceil(n*4/32) for stack,n in enumerate(lines) if stack!=q)
            allocated=math.ceil(size/4096)*4096
            capacity+=allocated;new_lines+=math.ceil(size/128)
            slots.append(dict(SM=sm,quad=q,stack=q,row_interval=[first,last],valid_code_bytes=size,
                              page_aligned_capacity_bytes=allocated,page_bytes=4096,
                              ordinary_descriptor_bytes=32,additional_RF_pointer_regs=2))
        assert old_cross==sum(d['candidate_cross_quad_code_line_requests_by_stack'])
        assert old_local==sum(d['candidate_local_code_line_requests_by_stack'])
        rows.append(dict(graph_op=d['id'],die=d['die'],weight=d['weight'],SM_row_ownership=slots,
                         arithmetic_changed=False,die_TP_changed=False,golden_split=d['golden_split'],
                         existing_uncached_local_lines=old_local,existing_uncached_cross_quad_lines=old_cross,
                         existing_cross_quad_fraction=old_cross/(old_cross+old_local),
                         existing_cross_quad_return_sectors=old_cross*4,
                         existing_cross_quad_command_packets_lower_bound=old_cross_commands,
                         existing_cross_quad_wire_bytes_lower_bound=(old_cross*4+old_cross_commands)*40,
                         candidate_weight_code_cross_quad_return_sectors=0,
                         candidate_uncached_code_lines=new_lines,
                         candidate_valid_code_bytes=d['weight_INT8_bytes'],
                         candidate_page_capacity_bytes=capacity,
                         candidate_padding_bytes=capacity-d['weight_INT8_bytes'],
                         descriptor_bytes_charged_per_invocation=1024,
                         descriptor_read_commands_per_invocation=32,
                         descriptor_worst_case_cross_quad_wire_bytes=32*2*40,
                         scales_activation_results_collectives='Remain explicit full-program demand; not eliminated or assigned zero by code placement.',
                         service_calendar='Both options pay actual valid weight payload,32B sectors,750B/fast-cycle combined read/write per quad, finite queues/PC arbitration, RF/shared/CDC/credits; command lower bounds do not prove loaded service.',
                         latency_credit=0,hardware_adopted=False))
    return dict(schema='opentallas.w13.ordinary-gpu-row-placement.v1',rows=rows,
                total_existing_cross_quad_wire_bytes_lower_bound=sum(r['existing_cross_quad_wire_bytes_lower_bound'] for r in rows),
                total_descriptor_worst_case_cross_quad_wire_bytes=sum(r['descriptor_worst_case_cross_quad_wire_bytes'] for r in rows),
                total_added_page_padding_bytes=sum(r['candidate_padding_bytes'] for r in rows),
                total_descriptor_bytes=sum(r['descriptor_bytes_charged_per_invocation'] for r in rows),
                organisation='Ordinary GPU thread-block/row-owner placement and per-SM base descriptors; no ROM-specific mechanism.',
                missing=['fullprogram typed request/return/writecommit service calendar','descriptor/cursor issue and RF live-register budget','per-stack capacity allocation including unchanged scales/KV/activations','bank/PC coalescing and hotspots','existing source recipe exactness after address mapping','actual contextualSSFF'],
                modeled_token_cycles=None,rate_credit=0,physical_build_ready=False,hardware_adopted=False)
