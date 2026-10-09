"""W2 full-shaped NO2/NO3 phase locality and real kept hold seats, pre-RTL."""
def model(no=2):
    if no not in (2,3): raise ValueError('actual station shape required')
    words=37+no*4+1+1+5
    delay_inverters=8*64*(3*37+2*(words-37))+8*(no+6)
    return dict(schema='w2_phase_seat_v16',no=no,frame_bits=2328,bank_words=words,
        macs_per_cycle=0,compute_intensity=0,communication_intensity='unchanged frame/receipt metadata',
        memory_ports_bytes_per_cycle=0,replica_count=no+4,
        input_bits_per_cycle=2328+no*265,output_bits_per_cycle=no*2328+265,
        routing_tracks_required=no*2328+265,routing_channel_capacity='existing station pin reservation; physical lint required',
        phase_copies_flops=4*words,local_phase_fault='fanout replicas only; new per-copy equality check removed per binding V16; original enable checks unchanged',
        hold_seat='eight real kept inverters on payload data pipeline connections and bank reset copies; logically identity; no falsepaths',
        delay_inverters=delay_inverters,assumed_inverter_um2=0.04374,
        added_area_um2_estimate=delay_inverters*0.04374+4*words*0.1458,
        core_um=[480,200],baseline_core_um=[440,160],core_area_delta_percent=36.363636,slot_fit='incremental estimate; fullshape mapped inventory and <=60percent physical lint gate',
        fanout='local phase decode supplies each word; four nextphase nets fan out only to FFs; no new copy-check net',
        mux_demux_cost='unchanged data/control muxing',latency_cycles_added=0,
        assumed_hold_delay_ps_range=[48,120],reset_assertion_added_delay='8 inverter propagation delays; recovery/removal measured at actual corners',
        adoption=False,physical_qualified=False,exact_gate='full bank+quarter+crossbank veto and original fault negatives; copy-replica upset is not a new detection requirement')
