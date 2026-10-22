"""Source-bound DS PV probability input plans, using actual SU drain addresses only.

This does not lower ATT.PV arithmetic or invent a per-page clear/read calendar.
No probability values or fixture outputs are accepted by the planner.
"""
from pathlib import Path
import hashlib
from hbm_layer_vehicle import sm_images as SI

SOURCE_HASHES = {
    'rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_cl2.sv': 'ac8e1c63b455c745de62e6cab65e3dfdbe014bda163d3bec7800c66bd11e36af',
    'rtl/hbm_accel/generic/peers/ot_hgi_sm_xload_static_xql.sv': '8eb7bd27d513f130ed4010d98f4b2d6318b0dbc79e9106d8809724039a70df76',
}
ROW_INTERVAL = 256  # tested source3a855; 80/81 are latency, not sustainable II
COMMAND_TO_WRITE = 81
TABLE_CAPACITY = 128


def source_contract(source_root, contract):
    root = Path(source_root)
    for rel, want in SOURCE_HASHES.items():
        if hashlib.sha256((root/rel).read_bytes()).hexdigest() != want:
            raise ValueError(f'actual probability-producer source mismatch: {rel}')
    p = contract['instances']['xl_SW_ctl']['params']
    if p != dict(PMAX=8, RD_LAT=[37,40,27,29,53,55,43,45], NR=32, LEAD=8):
        raise ValueError('selected SW RLM55/LEAD8 probability timing contract required')
    return dict(sources=SOURCE_HASHES, parameters=p, pair_control_T=0,
                source_qualification='existing VM-boundary component proof only; physical and SU join open')


def command(physical_word, row):
    if type(physical_word) is not int or not 0 <= physical_word < 65536:
        raise ValueError('actual SW physical FP32 word address required')
    if type(row) is not int or not 0 <= row < 128:
        raise ValueError('pstore row outside one real128-row page')
    v = SI._put(0, 0, 40, physical_word, 'x_base')
    v = SI._put(v, 40, 21, 1, 'x_n')
    v = SI._put(v, 61, 4, 1, 'x_p')
    v = SI._put(v, 97, 2, 2, 'x_space')
    return SI._put(v, 101, 7, row, 'x_xb')


def plan(*, logical_words, producer_entry, producer_record, contract, source_root):
    """Addresses come from emitted runtime drains; values are never read from expect[].value.

    Page payloads remain refused as a complete ATT.PV lowering until real consumer
    pread/clear/retirement and CP launch->command edges are bound. No launch is emitted.
    """
    profile = source_contract(source_root, contract)
    if producer_entry.get('status') not in ('emitted', 'blocked:emitted') or 'programme' not in producer_entry:
        raise ValueError('actual emitted SU producer programme required')
    if producer_entry.get('tag') != 'attend.bf16_p':
        raise ValueError('actual attend.bf16_p producer required')
    mapping = {}
    for drain in producer_record['expect']:
        for lane, word in enumerate(drain.get('words', [])):
            if drain['mask'] >> lane & 1:
                mapping[word] = 8*drain['sector']+lane
    missing = [w for w in logical_words if w not in mapping]
    if missing:
        raise ValueError(f'actual SU producer join open: {len(missing)} probability words have no runtime drain')
    pages = []
    for page_no, offset in enumerate(range(0, len(logical_words), TABLE_CAPACITY)):
        words = logical_words[offset:offset+TABLE_CAPACITY]
        entries, footprints = [], []
        for row, logical in enumerate(words):
            physical = mapping[logical]
            slot = 64+row*ROW_INTERVAL
            entries.append((slot, command(physical, row)))
            sector0 = physical//8
            sectors = [sector0+((bank-sector0)%8) for bank in range(8)]
            footprints.append(dict(row=row, logical_word=logical, physical_word=physical,
                command_slot=slot, source_client=2, vm_sectors_by_bank=sectors,
                client_request_after_command=[3+55-d for d in profile['parameters']['RD_LAT']],
                physical_bank_calendar='OPEN exact request-pad ages; require full input-stage exclusive owner2 epoch',
                xw_after_command=80, pstore_write_after_command=COMMAND_TO_WRITE))
        table = SI.cmd_table_rows(entries, SI.XL_CW)
        pages.append(dict(page=page_no, first_global_probability=offset, rows=len(words),
            table_target=100, table_window=SI.CMD_WIN_TABLE, table_rows=table,
            descriptor=dict(base=0,limit=len(words),loops=1),
            first_command_slot=64, last_write_slot=64+(len(words)-1)*ROW_INTERVAL+COMMAND_TO_WRITE,
            fixed_input_kernel_stream_edges=len(words)*ROW_INTERVAL,
            command_to_write_latency=COMMAND_TO_WRITE, tested_command_interval=ROW_INTERVAL,
            VM_read_bytes=len(words)*256,xw_transport_bytes=len(words)*256,pstore_write_bytes=len(words)*32,
            footprints=footprints, clear_read_reuse_calendar='OPEN real PV consumer and static retirement required'))
    return dict(status='PARTIAL_PSTORE_INPUT_PLAN_CONSUMER_CALENDAR_OPEN', full_ATT_PV_lowered=False,
        hardware_executed=False, runtime_SU_producer_join_qualified=False, physical_views_qualified=False,
        source_contract=profile, producer_programme=producer_entry['programme'],
        producer_commit_serial=producer_entry['compiled_commit_serial'],
        producer_ready_stream=(4*producer_entry['compiled_commit_serial']+2)//3,
        probability_rows=len(logical_words),pages_required=len(pages),real_table_capacity=TABLE_CAPACITY,
        pages=pages,probability_M_events=0, probability_values_accepted=False,
        fixed_input_kernel_stream_edges=sum(p['fixed_input_kernel_stream_edges'] for p in pages),
        price_scope='actual tested256-edge row slots only; CP install, consumer, clear/reuse cost still OPEN; no layer/token rate',
        refusal='ATT.PV consumer programme, paddr page offsets, clear/read retirement, CP command anchor and actual SU join remain OPEN')
