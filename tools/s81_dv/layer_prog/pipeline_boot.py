#!/usr/bin/env python3
"""Compile booked native HOST/KS payloads for the accepted S81 position graph.

Consumes existing dv_layer_compile outputs and explicit per-region transport
bookings. It never turns a calendar owner reservation into an issuer command,
or substitutes an equal-SPAN KS6 programme for the position graph. Payloads use
only existing HOST CSR/PW and HBE1v2 encoders. Missing native jobs, phase dates,
context lifecycle or unit lowerings leave production enablement refused.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import dv_layer_compile as D
from hostb_envelope import Context, encode_boot, crc32c
from ks_descriptor import decode as decode_ks


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def uint(obj, key, bits=48):
    x = obj[key]
    if type(x) is not int or not 0 <= x < 1 << bits:
        raise ValueError(f'{key}: explicit unsigned {bits}-bit value required')
    return x


def native_job(directory, job_index=0):
    """Read actual compiler PW bytes, checking them against calendar.json rows."""
    directory = Path(directory)
    cp = directory / 'prog/calendar.json'
    cal = json.loads(cp.read_text())
    jobs = cal.get('job')
    if not jobs or not 0 <= job_index < len(jobs):
        raise ValueError('existing native compiler calendar.job is required')
    job = jobs[job_index]
    manifest = json.loads((directory / 'manifest.json').read_text())
    hp = directory / 'prog'
    if len(jobs) != 1:
        hp /= f'job{job_index}'
    hp /= 'host_boot.memh'
    words = [int(x, 16) for x in hp.read_text().split()]
    cells, begin, seal, lengths = {}, [], [], []
    for index, word in enumerate(words):
        if not 0 <= word < 1 << 515 or not word & 1 or word >> 513:
            raise ValueError('native boot contains inactive or non-CSR host word')
        data = word >> 1
        op = data & 255
        if op == 0x11:
            lengths.append((data >> 32) & 255)
        elif op == 0x10:
            addr, value = (data >> 96) & 127, (data >> 32) & ((1 << 28)-1)
            part = value >> 26
            if part == 3:
                (seal if value & (1 << 25) else begin).append((index, value))
            else:
                key = (addr, part)
                if key in cells:
                    raise ValueError('duplicate native PW row part')
                cells[key] = value & ((1 << 26)-1)
        elif op not in (0x13, 0x14):
            raise ValueError(f'unsupported native boot CSR 0x{op:02x}')
    rows = job['rows']
    if not rows or len(rows) > D.NOPS or lengths != [len(rows)] or len(begin) != 1 or len(seal) != 1:
        raise ValueError('native length, BEGIN, SEAL and real command rows required')
    if begin[0][0] >= seal[0][0] or (begin[0][1] ^ seal[0][1]) != 1 << 25:
        raise ValueError('native BEGIN/SEAL contract differs')
    if len(cells) != 3 * len(rows):
        raise ValueError('missing or extra native PW row parts')
    decoded = []
    for index, row in enumerate(rows):
        value = sum(cells[index, part] << (26*part) for part in range(3))
        expected = D.pack_row(row['done'], row['issue'], row['engine'], row['arg'])
        if value != expected or value != int(row['row76'], 16):
            raise ValueError('actual boot PW differs from native calendar row ' + str(index))
        decoded.append(dict(i=index, issue=(value >> 28) & 0xffffff,
                            done=(value >> 52) & 0xffffff, engine=(value >> 24) & 15,
                            arg=value & 0xffffff, row76=f'{value:019x}'))
    commands = [r for r in decoded if r['engine'] < D.ENG['KIT']]
    if not commands:
        raise ValueError('native programme has no real command; owner window is not a programme')
    if decoded[-1]['engine'] != D.ENG['END']:
        raise ValueError('actual native END row required')
    # Identity derives from the exact emitted payload, not a model receipt/tag.
    raw = b''.join(w.to_bytes(65, 'big') for w in words)
    digest = hashlib.sha256(raw).hexdigest()
    lowering = directory / 'lowering.json'
    for path in (hp, cp, lowering):
        rel = str(path.relative_to(directory))
        if not path.exists() or manifest.get('files', {}).get(rel) != sha(path):
            raise ValueError('native compiler manifest differs from emitted file '+rel)
    low = json.loads(lowering.read_text())
    complete = bool(low.get('ops')) and all(x['status']=='LOWERED' for x in low['ops']) and not low.get('die_gaps')
    return dict(words=words, rows=decoded, commands=commands, nops=len(rows),
                issuer_stage=seal[0][1] & 127,
                all_stage_ops_lowered=complete, lowering_status_counts=low.get('status_counts'),
                native_die_sha256=manifest.get('die_v_sha256'),
                first_row_issue=decoded[0]['issue'], first_command_issue=commands[0]['issue'],
                end_issue=decoded[-1]['issue'], seal_phase=(seal[0][1] >> 7) & 3,
                seal_word_index=seal[0][0], programme_payload_sha256=digest,
                programme_id64=int(digest[:16], 16), programme_tag32=int(digest[:8], 16),
                native_calendar_sha256=sha(cp), host_file=str(hp), host_file_sha256=sha(hp),
                compiler_lowering_sha256=sha(lowering) if lowering.exists() else None,
                sealed_programme_held=job.get('sealed_programme_held', True),
                native_job=job_index, native_job_count=len(jobs), reload_direct_edges=len(words) * D.HOST_SLOT)


# Source-selected capability from the matched nativeA/B receiver proof, not
# caller-advertised limits. Original fixed417 source remains the fallback.
RECEIVER_CAPABILITY_SHA256 = {
    '6f412d849bba44378b24ffa5e72fed96f256ab33806a6a3da05aa53d1017493f',  # matched component/native A/B
    '7a19861e4bd7874cd82e04892030668bbefe306bd81276c297164f30438333a9',  # same receiver plus elaborated R4D assembly
}


def receiver_capability(contract, root):
    if not contract.get('capability_receipt'):
        return None
    receipt = Path(root) / contract['capability_receipt']
    if sha(receipt) not in RECEIVER_CAPABILITY_SHA256:
        raise ValueError('receiver capability is not the qualified source-selected receipt')
    cap = json.loads(receipt.read_text())
    if cap['schema'] != 'opentallas.s81.hostb.receiver_capability.v1':
        raise ValueError('unsupported selected receiver capability schema')
    source = Path(root) / contract['capability_source_root']
    for name, digest in cap['source_hashes'].items():
        if sha(source/name) != digest:
            raise ValueError('selected receiver RTL differs from capability source '+name)
    actual = cap['component_parameters']
    if actual != dict(ENABLE=1,VARIABLE_WORDS=1,ALLOW_RELOAD=1,HOSTB_ENABLE=1,STATIC_KS6=0):
        raise ValueError('receiver capability selected parameters differ')
    for key, value in actual.items():
        if contract.get('selected_parameters',{}).get(key) != value:
            raise ValueError('booking must select the exact qualified receiver parameters '+key)
    wrapper='rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_source.sv'
    if contract['source_sha256'] != cap['source_hashes'][wrapper]:
        raise ValueError('receiver wrapper and full capability source closure differ')
    return dict(receipt_sha256=sha(receipt), **cap)


def hbc_payload(context, booking, host_slots, nwords, ks_date):
    """Pack existing HBC1 fields and LOAD/body/COMMIT, never infer reset epochs."""
    book = booking['hbc_book']
    first = host_slots[0]['receiver_header_edge']
    for i, slots in enumerate(host_slots):
        if slots['receiver_header_edge'] != first+16*i or slots['receiver_body_capture_edge'] != first+16*i+4:
            raise ValueError('selected HBC affine book requires actual stride16 and body gap4')
    fields = [
        ('transaction_id',context.transaction_id,16), ('user',context.user,10),
        ('position',context.position,21), ('token',context.token,21),
        ('epoch_identity',context.epoch_identity,32), ('programme_id64',context.programme_id64,64),
        ('local_epoch_at_config_body_capture',uint(book,'local_epoch_at_config_body_capture'),48),
        ('first_NEXT_header',first,48), ('NEXT_header_stride',16,12),
        ('HOST_word_count',nwords,10), ('target_body_gap',4,8), ('transit_body_gap',4,8),
        ('KS_capture',ks_date,48), ('PREV_return_input_capture',uint(book,'prev_return_input_capture'),48),
        ('local_status_sample',uint(book,'local_status_sample'),48),
        ('local_return_send',uint(book,'local_return_send'),48),
        ('expected_data_stage',uint(book,'expected_data_stage',8),8),
        ('expected_data_rank',uint(book,'expected_data_rank',2),2), ('flags',0,12)]
    raw, offset = 0, 0
    for name, value, width in fields:
        uint({name:value},name,width)
        raw |= value << offset; offset += width
    assert offset == 512
    if not book['local_status_sample'] < book['local_return_send'] < book['prev_return_input_capture']:
        raise ValueError('HBC local status/send/PREV dates are not ordered')
    h = uint(book,'boot_header_edge'); commit = uint(book,'boot_commit_edge')
    if commit <= h+6:
        raise ValueError('HBC COMMIT must follow real body capture and CRC processing')
    clock_id = uint(book,'clock_reset_id64',64)
    if not clock_id:
        raise ValueError('HBC actual clock/reset identity cannot be zero')
    crc = crc32c(raw.to_bytes(64, 'little'))
    def header(op, edge, words, bits):
        return (0x31434248 | 1<<32 | op<<36 | context.stage_id<<40 | context.rank<<48 |
                words<<50 | bits<<66 | crc<<82 | clock_id<<114 |
                context.programme_id64<<178 | edge<<242)
    return dict(body512=f'{raw:0128x}', body_crc32c=f'{crc:08x}',
                fields={name:value for name,value,_ in fields},
                records=[dict(receiver_boot_capture_edge=h,payload512=f'{header(0,h+4,0,512):0128x}'),
                         dict(receiver_boot_capture_edge=h+4,payload512=f'{raw:0128x}'),
                         dict(receiver_boot_capture_edge=commit,payload512=f'{header(1,commit,1,0):0128x}')])


def compile_pipeline(calendar, bookings, root, out):
    """Emit actual booked packets; report every missing full-production authority."""
    graph = calendar.get('pipeline_graph')
    if not graph or graph.get('positions') != 6 or calendar['checker']['result'] != 'PASS':
        raise ValueError('accepted six-position causal pipeline calendar PASS required')
    if calendar.get('mode') != 'mtp' or calendar.get('job_contexts') != 1:
        raise ValueError('current one-context MTP pipeline required')
    stages = {s['stage']: s for s in graph['stages']}
    slots = {s['user']: s for s in calendar['slots']}
    if bookings.get('tp_ranks') != [0, 1, 2, 3]:
        raise ValueError('release S81 requires all four actual TP ranks explicitly')
    expected = {(stage, user, p, rank) for stage in stages for user in slots
                for p in range(6) for rank in bookings['tp_ranks']}
    covered, coverage, compiled, gaps = set(), {}, [], []
    root = Path(root)
    out = Path(out); out.mkdir(parents=True, exist_ok=False)
    for index, booking in enumerate(bookings['jobs']):
        stage = booking['stage']; user = uint(booking, 'user', 10)
        pos = uint(booking, 'position_index', 3)
        rank = uint(booking['context'], 'rank', 2)
        key = (stage, user, pos, rank)
        if key not in expected:
            raise ValueError('unexpected graph position booking ' + str(key))
        job = native_job(root / booking['native_programme'], booking.get('native_job', 0))
        chain = coverage.setdefault(key, dict(calendar_sha256=job['native_calendar_sha256'],
                                              total=job['native_job_count'], jobs=set()))
        if chain['calendar_sha256'] != job['native_calendar_sha256'] or job['native_job'] in chain['jobs']:
            raise ValueError('native split-job chain duplicates or mixes different compiler calendars')
        chain['jobs'].add(job['native_job'])
        if chain['jobs'] == set(range(chain['total'])):
            covered.add(key)
        descriptor_path = root / booking['descriptor_file']
        descriptor_words = descriptor_path.read_text().split()
        if len(descriptor_words) != 1:
            raise ValueError('one actual incoming KS descriptor file required')
        ks = int(descriptor_words[0], 16); identity = decode_ks(ks)
        if identity['user'] != user:
            raise ValueError('actual incoming KS user differs from calendar booking')
        ctx = dict(booking['context'])
        for name in ('user', 'token', 'position'):
            if ctx[name] != identity[name]:
                raise ValueError('actual descriptor identity differs from HBE context')
        if ctx['stage_id'] != int(stage[1:]):
            raise ValueError('HBE stage differs from exact graph stage')
        ctx['programme_id64'] = job['programme_id64']
        context = Context(**ctx)
        contract = booking['receiver_contract']
        # Selected source9c5e + dsdv_hostb_rx: all dates are actual sampled
        # posedges. BODY B -> RX visible B+2 -> landing B+3 -> seq capture B+4.
        # KS header K -> RX visible afterK -> landing K+1 -> seq capture K+2.
        if contract['host_body_to_seq_capture_edges'] != 4 or contract['ks_header_to_seq_capture_edges'] != 2:
            raise ValueError('selected actual HBE RX + one landing capture ages required')
        if uint(contract, 'issuer_stage', 7) != job['issuer_stage']:
            raise ValueError('native seven-bit stage differs from actual local issuer STAGE strap')
        for name in ('source_sha256', 'clock_reset_identity'):
            if not contract.get(name):
                raise ValueError('receiver source and clock/reset identity are explicit')
        ks_slots = booking['ks_slots']
        seq_ks = uint(ks_slots, 'receiver_edge') + 2
        first_cmd = seq_ks + D.SEQ['job_to_age0'] + job['first_command_issue']
        if first_cmd != uint(booking, 'first_command_edge'):
            raise ValueError('actual native first command differs from booked first-command anchor')
        if booking.get('issuer_phase_convention') != 'preedge_phase_q':
            raise ValueError('issuer phase book must name preedge phase_q explicitly')
        # Core accepts at K+3 and compares preedge phase_q+1;
        # phase(E)+(K+3-E)+1 == phase(E)+K-E (mod4).
        epoch = uint(booking, 'phase_epoch_edge')
        phase = uint(booking, 'issuer_phase_at_epoch', 2)
        if seq_ks < epoch or (phase + seq_ks - epoch) % 4 != job['seal_phase']:
            raise ValueError('actual KS/issuer phase differs from native sealed start phase')
        graph_epoch = uint(booking, 'graph_epoch_receiver_edge')
        a, b = stages[stage]['position_windows'][pos]
        shift = slots[user]['shift']
        window = [graph_epoch + shift + a, graph_epoch + shift + b]
        end_edge = seq_ks + 4 + job['end_issue']
        if first_cmd < window[0] or end_edge > window[1]:
            gaps.append(dict(job=index, cause='native_commands_or_END_outside_pipeline_window',
                             native=[first_cmd,end_edge], graph_window=window))
        host_slots = booking['host_slots']
        if len(host_slots) != len(job['words']):
            raise ValueError('every actual native HOST word needs its explicit transport booking')
        seal_capture = host_slots[job['seal_word_index']]['receiver_body_capture_edge'] + 4
        # Exact walker seal scanning: fixed128 rows; earliest KS capture+132.
        earliest_ks = seal_capture + D.NOPS + 4
        if seq_ks < earliest_ks:
            gaps.append(dict(job=index, cause='native_seal_scan_not_complete',
                             seq_ks=seq_ks, earliest_seq_ks=earliest_ks))
        last_host_capture = max(s['receiver_body_capture_edge'] + 4 for s in host_slots)
        if last_host_capture >= seq_ks:
            raise ValueError('actual HOST/template writes overlap booked KS launch')
        packets = encode_boot(job['words'], context, host_slots, ks53=ks, ks_slots=ks_slots,
                              transit_route=booking.get('transit_route', []))
        hbc = hbc_payload(context, booking, host_slots, len(job['words']), ks_slots['receiver_edge'])
        if booking['hbc_book']['local_status_sample'] < end_edge+4:
            gaps.append(dict(job=index,cause='status_sample_before_actual_busy_clears',
                             actual_END=end_edge,earliest_status_sample=end_edge+4,
                             booked_status_sample=booking['hbc_book']['local_status_sample']))
        # Existing HBC1 is417 words, one immutable active context. Do not
        # silently claim it reloads identities or accepts arbitrary native H.
        capability = receiver_capability(contract, root)
        if capability is None:
            gaps.append(dict(job=index,cause='receiver_capability_not_source_bound',
                             selected_contract='legacy417/no-reload until exact bound extension receipt'))
        supports_words = (capability['word_count']['minimum'] <= len(job['words']) <= capability['word_count']['maximum']
                          if capability else len(job['words']) == 417)
        if not supports_words:
            gaps.append(dict(job=index, cause='receiver_host_word_count_mismatch',
                             actual=len(job['words']), receiver=capability['word_count'] if capability else 417))
        if not contract.get('die_v_sha256') or contract['die_v_sha256'] != job['native_die_sha256']:
            gaps.append(dict(job=index,cause='native_programme_not_current_strict_die',
                             native_die_sha256=job['native_die_sha256'], receiver_die_sha256=contract.get('die_v_sha256')))
        if not capability or not capability['die_instance_bound'] or not capability['production_clock_book_bound']:
            gaps.append(dict(job=index, cause='HBC_context_load_commit_lifecycle_not_bound'))
        if capability and not capability['full_assembly_elaborated']:
            gaps.append(dict(job=index,cause='selected_receiver_full_assembly_not_elaborated'))
        if job['sealed_programme_held']:
            gaps.append(dict(job=index, cause='native_compiler_row_lifetimes_held'))
        if not job['all_stage_ops_lowered']:
            gaps.append(dict(job=index, cause='full_stage_native_lowerings_incomplete'))
        path = out / f'{stage}_r{rank}_u{user}_p{pos}_j{job["native_job"]}'
        path.mkdir()
        (path/'host_boot.memh').write_text(D.memh(job['words'], 515))
        (path/'hfwd512.memh').write_text(''.join(p['payload512']+'\n' for p in packets))
        record = dict(stage=stage, user=user, position_index=pos,
            copy=slots[user]['copy'].get(stage, 'A'), context=asdict(context),
            programme={k:v for k,v in job.items() if k not in ('words',)},
            descriptor_file_sha256=sha(descriptor_path), ks53=f'{ks:014x}',
            sampled_edge_convention='posedge sampled, NBA outputs visible only after that edge',
            seq_ks_capture=seq_ks, seq_first_command=first_cmd, seq_END_command=end_edge,
            native_seal_seq_capture=seal_capture, earliest_seq_ks=earliest_ks,
            earliest_status_sample=end_edge+4,
            first_host_seq_capture=host_slots[0]['receiver_body_capture_edge']+4,
            last_host_seq_capture=last_host_capture,
            native_direct_reload_edges=job['reload_direct_edges'],
            HBE_reload_seq_capture_span=last_host_capture-host_slots[0]['receiver_header_edge'],
            pipeline_window=window, receiver_contract=contract, receiver_capability=capability,
            static_ks6_enabled=False, inline_ARM_emitted=False, hbc=hbc, packets=packets)
        (path/'programme.json').write_text(json.dumps(record,indent=1)+'\n')
        compiled.append(dict(stage=stage,rank=rank,user=user,position_index=pos,
                             native_job=job['native_job'],dir=path.name,
                             programme_payload_sha256=job['programme_payload_sha256'],
                             programme_tag32=f'{job["programme_tag32"]:08x}',
                             first_command_edge=first_cmd,end_command_edge=end_edge))
    # A later job cannot load PW/template data until the old real END has
    # propagated through busy status to RX (body >= END+2, seq capture >= END+6).
    physical = {}
    for item in compiled:
        rec = json.loads((out/item['dir']/'programme.json').read_text())
        physical.setdefault((item['stage'], rec['copy'], rec['context']['rank']), []).append(rec)
    for resource, jobs in physical.items():
        jobs.sort(key=lambda x:x['seq_ks_capture'])
        for prev, nxt in zip(jobs, jobs[1:]):
            old = prev['hbc']['fields']
            earliest_reload = max(prev['seq_END_command']+4,
                old['PREV_return_input_capture']+3,old['local_return_send']+3,
                prev['seq_ks_capture'],prev['last_host_seq_capture'])
            # A BOOT-counter header date is not a seeded receiver-epoch date.
            # The actual transport book must supply both, with source identity.
            reload_edge = nxt['receiver_contract'].get('reload_header_receiver_capture_edge')
            if reload_edge is None or reload_edge < earliest_reload:
                gaps.append(dict(cause='HBC_reload_before_old_context_static_drain',
                    resource=resource,earliest_receiver_header=earliest_reload,
                    booked_receiver_header=reload_edge))
            if nxt['first_host_seq_capture'] < prev['seq_END_command']+6:
                gaps.append(dict(cause='native_reload_overlaps_previous_job_or_delayed_busy',
                                 resource=resource, previous_END=prev['seq_END_command'],
                                 next_HOST_seq_capture=nxt['first_host_seq_capture']))
    for key, chain in coverage.items():
        if len(chain['jobs']) != chain['total']:
            gaps.append(dict(cause='native_split_job_chain_incomplete',stage=key[0],user=key[1],
                             position_index=key[2],rank=key[3],
                             missing_native_jobs=sorted(set(range(chain['total']))-chain['jobs'])))
    missing = sorted(expected-covered)
    result = dict(schema='opentallas.s81.pipeline_native_boot.v1',
        status='READY_FOR_RTL' if not gaps and not missing else 'PARTIAL',
        calendar_source_sha256=calendar['checker']['source_sha256'],
        graph_positions=6, expected_stage_positions=len(expected), emitted=len(compiled),
        missing_stage_positions=[dict(stage=s,user=u,position_index=p,rank=r) for s,u,p,r in missing],
        jobs=compiled, gaps=gaps, production_enabled=False,
        full_token=False, full_pipeline_RTL=False,
        next='Execute emitted real HOST/KS packets on the selected receiver/issuer; bind missing native stages and lifecycle')
    (out/'manifest.json').write_text(json.dumps(result,indent=1)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--calendar',type=Path,required=True)
    p.add_argument('--bookings',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    book=json.loads(a.bookings.read_text())
    result=compile_pipeline(json.loads(a.calendar.read_text()),book,a.bookings.parent,a.out)
    print(result['status'],result['emitted'],'real native jobs,',len(result['missing_stage_positions']),
          'missing stage positions,',len(result['gaps']),'production gaps')
    return 0 if result['status']=='READY_FOR_RTL' else 2


if __name__=='__main__':
    sys.exit(main())
