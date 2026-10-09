"""Mutable row credit, fault and launched-packet protection before build."""
def model(dff_um2=.2916):
    from uarch_model_qwen_row_endpoint import model as endpoint
    base=endpoint(dff_um2);extra_bits=2*(32*4+3+843+1)
    added=extra_bits*dff_um2+4000
    return dict(schema='opentallas.qwen-protected-row-endpoint.v1',default_off=True,adopted=False,
        model_precedes_rtl=True,replicas=48,macs_per_cycle=0,memory_ports=[],
        base=base,extra_state_bits=extra_bits,added_cell_area_bound_um2=added,
        cell_area_bound_um2=base['cell_area_bound_um2']+added,
        slot_um=base['slot_um'],
        slot_fit_at_55pct=base['cell_area_bound_um2']+added<=96.768*1200.096*.55,
        boundary_bits_per_cycle=dict(heads=11808,launch=846,reverse_ack=216,return_credit=32),
        mutable_protection='three copies of32credit counters, sticky fault and full three281bit launch packets/valids; disagreement stops all launch and credit updates',
        latency=dict(extra_forward_edges=0,extra_ack_edges=0,
            timing='wide equality guard requires real measuredphysical timing; no relaxedclock'),
        remaining=['actualPC→row protectedrelay links and returnack credits',
            'source-pinned statefault and replay exact gates',
            'Claude structural review BEFORE any newphysical route'])
