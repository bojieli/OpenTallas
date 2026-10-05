"""Source-schema shared-journal reservation; no simulated producer payloads.

This covers the added shared sector journals only. Existing RF movement,
comparison records and large native group-call records need their own composed
projection before a launcher can admit disk. No physical port cycle credit.
"""
import hashlib,json
from pathlib import Path
from ds_hbm_pc10_engine_r44 import resource_model
from h4_hbm_w19_pc10_endpoints import inputs


def model():
    import hbm_provider_microvm_r21 as sector
    raw=inputs()['sector.py']
    if hashlib.sha256(Path(sector.__file__).read_bytes()).digest()!=hashlib.sha256(raw).digest():
        raise ValueError('retained sector schema source mismatch')
    defaults=sector.SectorProvider({})  # inspect finite parameters; accept ZERO requests
    # Upper-bounded integers include ticks, tags, serials and generations; fixed
    # source fields and actual owner template length are retained. Union of
    # every success-event extra is conservative for each serialized event.
    U=(1<<64)-1
    record=dict(event='software_service_phases_reserved',tick=U,stack=U,local_sector31=U,
        identity=dict(target='DeepSeek',rank=95,epoch=U,pc=10,serial=U,sector=U),
        tag=U,generation=U,hardware=False,resident=U,phase_costs=dict(defaults.costs),
        allocation_identity=dict(PC=10,rank=95,SM=31,generation=U,tile=63,
            template='f'*64,die=95,address_class='shared'))
    size=len(json.dumps(record,sort_keys=True,separators=(',',':')).encode())
    x=resource_model();journals=x['ranks']*x['SMs_per_rank'];events=8
    amount=journals*131072+x['sector32_transactions']*events*8*(size+64)
    c=defaults.costs
    forward=sum(c[k] for k in ('admission','forward_CDC','owner_lookup','held_accept'))
    reverse=sum(c[k] for k in ('consume','reverse_CDC','owner_lookup','held_accept','reverse_grant','retire'))
    write=forward+c['write_visibility']+defaults.write_ticks+reverse
    read=forward+defaults.read_ticks+reverse
    return dict(schema='DS_PC10_SHARED_JOURNAL_RESERVATION_R44',
        software_write_owner_hold_ticks=write,software_read_owner_hold_ticks=read,
        software_per_SM_serial_sector_ticks=288*(write+read),
        software_all_serial_sector_ticks=x['sector32_transactions']//2*(write+read),
        physical_critical_path_edges=None,
        independent_calendar_ticks_are_not_parallel_hardware_service=True,
        source_sector_sha256=hashlib.sha256(raw).hexdigest(),
        accepted_requests_for_schema_derivation=0,events_per_successful_sector_upper=events,
        per_event_source_schema_upper_bytes=size,conservative_union_schema=record,
        sector_transactions=x['sector32_transactions'],maximum_allocated_shared_journals=journals,
        fixed_reservation_per_journal_bytes=131072,shared_only_journal_reservation_bytes=amount,
        full_projection_complete=False,
        missing=['retained RF movement reservation', '1664 observation records',
                 '96 actual group-call record envelopes including 512 source receipts per call'],
        physical_clock_or_rate_qualified=False)
