"""Separate W15 baseline accepted-pop counter fix; abandoned headreg not selected."""
from dsrom_collective_headreg import _install_selected

ENGINE = 'rtl/rom/ot_w15_rom_oneshot_px_acceptedpop.sv'


def install(sources, output, *, enable=False):
    result = _install_selected(
        sources, output, enable=enable, parameter='COLL_ACCEPTED_POP',
        child_parameter='FIX_ACCEPTED_POP',
        module='ot_w15_rom_oneshot_die_px_acceptedpop', engine_path=ENGINE,
        validation='Source-only baseline correctness fix; original arithmetic/tree/ports retained; no functional or physical qualification claimed')
    result['composed_effect'] = dict(
        added_pipeline_cycles=0, added_state_bits=0, added_external_port_bits=0,
        headreg_selected=False, arithmetic_or_reduction_order_changed=False,
        trigger='pop_red && g_stall: reduction head is offered but actual pop suppressed by held gather output',
        effect='Increment inflight only on pop && pop_red; retirement red_out unchanged; blocked head retains its FIFO/credit until actual acceptance',
        performance_claim=None, SS_FF_qualified=False)
    return result


def install_s81_parent(binding, original_export, output, *, enable=False):
    if binding.stages != 81 or binding.inventory['TP'] != 4:
        raise ValueError('selected S81/TP4 owner allocation required')
    if binding.contract['return_contract']['RD'] != 64:
        raise ValueError('selected active-pair RD64 required')
    r=install(binding.native_sources(original_export),output,enable=enable)
    r.update(selected_stages=binding.stages,pairs_per_rank_die=binding.pairs,return_depth=64)
    return r
