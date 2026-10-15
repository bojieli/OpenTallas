"""Prebuild accounting for actual source3cfd4a1c2, not a measured latency claim."""
def model():
    ports=16
    req_ff=4*14+17
    write_ff=4*542+17
    rsp_ff=4*512+18
    pad_ff=513
    return dict(schema='opentallas.s81.static-su-vm-bridge.v1',
        source='3cfd4a1c2',actual_VM_base='4305ce06f',opt_in_default=False,
        macs_per_cycle=0,ports=ports,
        serial_period_ps=[10000,9],stream_period_ps=[2500,3],related_ratio='3serial/4stream',
        clock_entries_per_port=7,actual_clock_entries=112,raw_reset_entries=112,
        sequential_boundaries_per_port=4,
        declared_FF_per_port=dict(read_x34=req_ff,write_x34=write_ff,read_x43=rsp_ff,stream_return_pad=pad_ff),
        declared_FF_total=ports*(req_ff+write_ff+rsp_ff+pad_ff),
        mapped_FF=None,mapped_area_um2=None,native_outlines=None,
        read_bytes_per_serial_edge=16*64,write_bytes_per_serial_edge=16*64,
        read_bytes_per_stream_edge_epoch_average=12*64,
        write_bytes_per_stream_edge_epoch_average=12*64,
        native_VM_peak_bytes_per_stream_edge_each_direction=32*64,
        boundary_bits=dict(serial_read_request=16*15,serial_write=16*543,
                           stream_read_request=16*15,stream_write=16*543,
                           stream_response=16*513,serial_response=16*513),
        additional_stream_return_pad_edges=1,request_or_write_queue_depth=0,
        transport='three actual fixed-phase banks per CDC; no enqueue, ready, credits or runtime schedule extension',
        source_phases=dict(serial_sample='S=3n+k',request_x34_output='Q=4n+2+k',
            VM_stream_input_sample='P=Q+1',VM_response='P+13=Q+14',
            bridge_pad_output='Q+15',x43_sample='Q+16',
            expected_serial_response='S+15, hypothesis until actual128SRAM dualclock gate passes'),
        write_visibility='UNMEASURED in this bridge composition; capture actual SRAM w_ce separately from returnedK11',
        reset='all seven actual entries released on commonPLL epoch; firstpostresetS/Tedges define0; physicalphi-R/epoch delivery unqualified',
        physical='four primitive boundaries perport require actualclock roots/pins/IO/3:4STA; no aggregatehardwrapper outline or idealclockdelivery',
        canonical='actualSUarithmetic+compilerprogramme join remains open; prepared memorytransport bench is not canonical arithmetic qualification',
        immutable_price_unchanged=True,measured_latency_or_throughput_qualified=False)
