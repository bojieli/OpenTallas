"""Prospective sizes of the default-off canonical Qwen KV controller.

Borrows the existing 64KiB scratch service: one source-allocated 1024B stage.
Does not add this gross inventory to the previously reserved bridge inventory.
No external owner, CDC, SRAM or W2 delay is inferred from these local edges.
"""
def model():
    # Exact raw sequential declaration census; no ECC is silently assumed.
    # Row includes distinct publication position and held-reader position.
    writer = 3 + 64 + 20 + 10 + 10 + 5 + 5 + 4*34 + 16 + 272 + 272 + 2
    row = 1 + 13 + 64 + 1 + 64 + 13 + 2 + 2 + 2 + 2
    command = 3 + 64 + 20 + 64 + 64 + 11 + 1 + 4
    capture = 512
    response = 1 + 1 + 3 + 64 + 20 + 64 + 11 + 512 + 64 + 1 + 4
    control = 4 + 1 + 9 + 256 + 1 + 1 + 7
    raw = writer + 72 * row + command + capture + response + control
    return dict(writer_slots=1, reader_rows=72, rank_count=2, SM_count=32,
                stage_useful_bytes=1024, stage_physical_bytes=1024,
                stage_allocation='existing source-allocated 16 aligned shared beats',
                added_SRAM_bytes=0, raw_control_bits=raw,
                protection='not implemented; gross raw control inventory only',
                storage_area_proxy_mm2=raw * .2916 / .5 / 1e6,
                replicas=1, row_select_fanout=72, row_read_ports=1, row_write_ports=1,
                scratch_ports=dict(address_bits=10, SM_bits=5, rank_bits=1, data_bits=512, outstanding=1),
                writer_visible_ports=dict(identity_bits=84, sector_bits=9,
                                          sectors=272, reverse_required=True),
                reader_event_ports=dict(identity_bits=84, stage_bits=1),
                command_bits=command, command_II_min_edges=3,
                local_response_min_edges=2, scratch_roundtrip_count_per_stage_beat=2,
                payload_sector_reads=256, payload_sector_writes=272,
                payload_K_partial_sectors=256, payload_V_full_sectors=16,
                prospective_clock_GHz=1.2, setup_uncertainty_ps=60,
                hold_uncertainty_ps=25, physical_clock_qualified=False,
                external_bounds=dict(scratch=None, payload_owner=None, W2=None,
                                     metadata_visibility=None, consumer=None,
                                     reverse=None, CDC=None, reset_drain=None),
                routing_tracks=None, placed_area_mm2=None, full_token_latency=None)


def price_local(service):
    """Positive prospective service bounds; external services stay explicit.

    Clock edges belong to the streaming domain. Calling this with measured
    service costs does not establish loaded-context timing or whole-token rate.
    Each supplied bound includes contention/CDC and the matching real receipt.
    """
    names = ('shared_write', 'shared_read', 'payload_partial_read',
             'payload_write_visible_reverse', 'metadata_visible',
             'SCORES_accepted_reverse', 'PV_accepted_reverse', 'allcopy_drain')
    if set(service) != set(names) or any(type(v) is not int or v <= 0 for v in service.values()):
        raise ValueError('all actual/prospective finite service bounds must be positive')
    # Conservative serialized local dispatch/response plus external service.
    # 16 stage beats each write and readback. 256 partial K RMW +16 full V.
    stage = 16 * (4 + service['shared_write'] + service['shared_read'])
    commit = 4 + 16 * service['shared_read'] + 256 * service['payload_partial_read'] + 272 * service['payload_write_visible_reverse']
    publish = 4 + 2 * service['metadata_visible']
    consumers = 8 + service['SCORES_accepted_reverse'] + service['PV_accepted_reverse'] + 2 * service['metadata_visible']
    release = 4 + service['allcopy_drain']
    return dict(begin_edges=4, acquire_edges=4, stage_edges=stage,
                commit_edges=commit, publish_edges=publish, consumer_edges=consumers,
                release_edges=release, scope='prospective streaming-domain bounds',
                total_edges=8 + stage + commit + publish + consumers + release,
                headline_adopted=False, physical_qualified=False)
