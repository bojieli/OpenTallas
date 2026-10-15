# Historical sizing function, source 3ee14f399; successor changes only pin landing, +0 cycles.
DFF_UM2=0.2916  # pinned unified-model DFFHQNx1 area
def dsrom_window_source_ctl_margin_model():
    """Margin-first price of the WINDOW source control leaf (takeover-ds, 2026-10-06).

    Cut: ot_dsrom_window_source_ctl = writer + tag mirror + stream engine + job
    FSM; the staging array (ot_dsrom_window_stage_pipeline + 68 columns) and the
    row merge are separate hardened neighbours, the HBM wmux belongs to the HBM
    service.  MARGIN=1 makes every boundary register-to-register: configuration,
    status and response inputs are flopped at the pin, the three command
    channels and the K-port write request pass 2-entry skid buffers with a
    registered ready, every output is a flop.  Priced before the RTL.
    """
    awh, tagw, userw, posw = 30, 16, 10, 21
    skid = lambda w: 2*w + 2
    ff = dict(region=2*awh,
              prime_skid=skid(userw+posw), blk_skid=skid(userw+posw+4+256+8),
              start_skid=skid(userw+posw+8),
              m_slice=skid(awh+4+tagw+1+256+32), m_wr_done=4,
              s_response=4*(1+tagw+4+256),            # dead refill path in this caller
              stage_status=1+12+1, merge_status=3, merge_start=1, stream_go=1,
              staged=1, status_out=1+1+5+32)
    total_ff = sum(ff.values())
    # Cycle cost.  Own-row write: per block one skid edge on blk and, for each of
    # its two sector writes (codes, scale), one request-slice edge and one
    # registered write-done edge.  Window job: start skid, all_rows, merge start,
    # merge done and staged/go each add at most one edge.
    write_cycles = 16*(1 + 2*(1+1))
    stream_cycles = 6
    per_layer = write_cycles + stream_cycles
    layers, clk_hz, ar_us = 61, 1.2e9, 592.466   # results/rtl/dsrom_recovery_20261004/composition.json AR_us
    charge_us = per_layer*layers/clk_hz*1e6
    return dict(block='ot_dsrom_window_source_ctl', parameter='MARGIN', default=0,
                added_FF=ff, added_FF_total=total_ff, added_FF_area_um2=total_ff*DFF_UM2,
                MACs_per_cycle=0, arithmetic_changed=False,
                added_cycles=dict(own_row_write_upper=write_cycles, window_job_upper=stream_cycles,
                                  per_layer_upper=per_layer),
                conservative_serial_charge_us=charge_us,
                AR_fraction_upper=charge_us/ar_us,
                pre_approved_cap_fraction=0.02,
                within_cap=charge_us/ar_us <= 0.02,
                basis='serial write plus stream charge per layer x 61 layers; the own-row write overlaps index traffic in the S81 calendar, so this is an upper bound',
                boundary=dict(inputs_flopped=['region_*', 'm_wr_done', 's_*', 'stage all_rows/landed/fault',
                                              'merge ready/done/fault', 'stream_go'],
                              skid_registered_ready=['prime', 'blk', 'start', 'm_* request'],
                              ready_inputs_into_local_enable=['m_rdy (slice pop)', 'wl_req_rdy (stream engine request register)'],
                              outputs_from_flops='all'),
                physical_closed=False, headline_changed=False)

