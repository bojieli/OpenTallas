#!/usr/bin/env python3
"""Additive unified-model sizing for the real Qwen r14 per-PC command leaf."""
import json
import uarch_model as unified


def model():
    ff=8*32+32+64+64
    return dict(schema='opentallas.qwen_ctrl_pc.v1',status='PROPOSED_NOT_ADOPTED',
        model_precedes_rtl=True,source_model='tools/uarch_model.py',replicas=128,
        static_masters=32,replicas_each_master=4,macs_per_cycle=0,
        compute_intensity_macs_per_byte=0,
        memory_ports=[dict(name='command_fifo',depth=8,width=32,write_bytes_per_cycle=4,read_bytes_per_cycle=4)],
        boundary_bits=dict(command_in=33,read_credit_in=3,command_credit_out=1,
            phy_row_out=28,phy_column_out=12,status_out=2),
        replica_mux_cost='one 8:1 x32 command FIFO mux per PC; no cross-PC mux',
        replica_fanout_cost='local descriptor; global broadcast/fence is a separate unclosed block',
        frame_um=[247.536,370.44],tracks_each_face=128,
        tracks_available_each_face=int(370.44/.288),
        area=dict(cell_bound_um2=16000+ff*unified.DFF_UM2,
            basis='conservative reservation; historical r6 was only NCH1 WR_EN0 and is not full-shape evidence',
            frame_fit_at_55pct=(16000+ff*unified.DFF_UM2)<247.536*370.44*.55),
        clock=dict(functional_period_ps=1024,physical_route_target_ps=770,physical_signoff_ps=833.333,
            reason='legacy HBM CK/2 DRAM timing counters remain at976.5625MHz; tighter physical screen does not authorize faster functional clock'),
        latency=dict(input_capture_edges=1,queue_admission_edges=1,phy_output_edges=1,
            minimum_request_to_phy_added_edges=3,composed_worst_case_token_cycles=36*4,
            base_token_cycles=216713,cost_pct=100*(1-216713/(216713+144))),
        remaining=['route all32 PC/parity/refresh-phase elaborations',
            'descriptor fanout and all-PC fence','write payload and tag queue',
            'read landing queue and map','real PHY integration and die STA'])
if __name__=='__main__':print(json.dumps(model(),indent=2))
