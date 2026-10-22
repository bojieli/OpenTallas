"""Current SUKV lowering: real native CTL words with explicit row ownership.

kv_program.json is a producer/binding receipt, not fixture arithmetic. A job
owns a group of model operations (RMSNorm/RoPE/QDQ are fused in the source).
Every covered operation remains in the compiler report. Dates are absolute
sequencer edges; capture_offset includes the selected CTL/VP path. No unit
latency is treated as a global availability date.
"""
import json
from pathlib import Path

from layer_prog.kv_bank_contract import dispatch, pool_dispatch, sukv_contract
from layer_prog.lower_vs import ctl_payload, row_write, _dvc

OPS = [r'^(?:mtp\.)?attn\.(?:kv_norm\..*|kv_rope_qdq|cmp\.(?:k_norm\..*|norm\..*|k_rope_qdq|row_qdq|pool))$']
UNIT = 'ot_s81sl_kv_leaf / ot_s81_su_kv (KV, GK, CN, IK, CP)'
BENCH = 'results/rtl/s81_rtlgap_codex_2000/SUKV/run2'
KINDS = dict(KV=1, GK=7, CN=12, IK=13, CP=14)
# Measured at the adapter's VLAT4 command boundary, NOT the issuer boundary.
ADAPTER_DONE = dict(KV=1130, GK=1025, CN=1218, IK=1058, CP=390)
# Bench reports count the first pin capture edge: pin-to-done subtracts one.
# ctl_path includes RSTOP2; XRT pin->c_v5 plus DL and VP/KV3 gives +DL+6.


def _integer(v, label, lo=0, hi=None):
    if type(v) is not int or v < lo or (hi is not None and v > hi):
        raise ValueError(f'{label}: integer outside source/calendar bounds')
    return v


def _range(lo, hi):
    _integer(lo, 'row start', 0, 1023)
    _integer(hi, 'row end', lo, 1023)
    return set(range(lo, hi + 1))


def validate(program, sched):
    """Reject omitted fused ops, overlaps, invented input availability and aliases.

    The manifest must explicitly name every operation covered by each physical
    command. Runtime producer rows are recorded by residency, never precomputed
    normalized/quantized outputs. Each residency carries the producing source.
    """
    if program.get('schema') != 'opentallas.s81.kv_program.v1':
        raise ValueError('unsupported KV programme receipt schema')
    ops = {o['id']: o for o in sched['ops']}
    seen, intervals, records, reads = {}, [], {}, []
    for job in program['jobs']:
        kind = job['kind']
        if kind not in KINDS:
            raise ValueError('unsupported SUKV source job')
        covers = job['covers']
        if (kind != 'GK' and (not covers or job['owner'] not in covers)) or (kind == 'GK' and covers) or job['owner'] not in ops or len(covers) != len(set(covers)):
            raise ValueError('physical command needs unique covered operations and an owning operation')
        for oid in covers:
            if oid not in ops or oid in seen:
                raise ValueError('unknown or multiply covered model operation')
            name = ops[oid]['op'].removeprefix('mtp.')
            expected = ('CP' if name == 'attn.cmp.pool' else
                        'IK' if name.startswith('attn.cmp.k_norm.') or name == 'attn.cmp.k_rope_qdq' else
                        'CN' if name.startswith('attn.cmp.norm.') or name == 'attn.cmp.row_qdq' else
                        'KV' if name.startswith('attn.kv_norm.') or name == 'attn.kv_rope_qdq' else None)
            if kind != expected and kind != 'GK':
                raise ValueError('physical job kind does not implement the covered model operation')
            seen[oid] = job
        issue = _integer(job['issue'], 'issue', 0, 2**24-1)
        context = _integer(job['context'], 'context', 0, 3)
        capture = issue + _integer(job['capture_offset'], 'actual CTL/VP capture offset', 1)
        if job['done_age'] != ADAPTER_DONE[kind]:
            raise ValueError('selected VLAT4 source needs its exact measured pin-to-done age')
        done = capture + _integer(job['done_age'], 'measured command-to-done', ADAPTER_DONE[kind])
        release = _integer(job['release_edge'], 'final consumer release', done)
        if not job.get('source_receipt'):
            raise ValueError('source-bound command timing receipt required')
        identifier = job.get('id', job['owner']+'::'+kind)
        if identifier in records:
            raise ValueError('duplicate physical job identity')
        intervals.append((capture, done + 1, identifier))
        outputs = set()
        if kind != 'GK':
            ready = _integer(job['output_ready_edge'], 'native read availability', done + 2)
            _integer(release, 'output lifetime end', ready)
            first_write = _integer(job['first_output_write_edge'], 'first native output write', capture, done + 1)
            expected_first_write = done - 251 if kind == 'CP' else capture + 1030
            if first_write != expected_first_write:
                raise ValueError('first native output commit differs from selected source phase schedule')
            outputs = (_range(job['output_base'], job['output_base']+127) if kind == 'CP' else
                       _range(672, dict(KV=771, CN=863, IK=703)[kind]))
        else:
            ready, first_write = done, done
        records[identifier] = dict(job=job, outputs=outputs, ready=ready, first_write=first_write, done=done)

        if kind == 'CP':
            bases = [job['slot0_base'], job['slot1_base']]
            required = _range(bases[0], bases[0]+255) | _range(bases[1], bases[1]+255)
            pool_dispatch(*bases, job['output_base'])
        else:
            if kind != 'GK' and job.get('parameter_base', 672) != 672:
                raise ValueError('selected source row contract reserves parameter base672')
            pb = _integer(job.get('parameter_base', 672), 'parameter base', 0, 1020 if kind == 'GK' else 1004)
            ob = job.get('operand_base', pb + (4 if kind == 'GK' else 20))
            required = _range(pb, pb + (3 if kind == 'GK' else 19))
            required |= _range(ob, ob + 127)
            dispatch(KINDS[kind], job['gain_set'], job['jid'], job['drain_age'], pb, ob)
            if job['drain_age'] != 1024:
                raise ValueError('selected source proof measures drain1024; another age needs a source replay')
            if kind in ('CN', 'IK') and job['gain_set'] != (3 if kind == 'CN' else 0):
                raise ValueError('CN/IK must select the actual gain bank3/0')
        if kind in ('KV', 'CN', 'IK'):
            gain = job.get('gain_residency', {})
            if gain.get('gain_set') != job['gain_set'] or not gain.get('source_receipt'):
                raise ValueError('actual selected gain-bank residency receipt required')
            if _integer(gain.get('ready_edge'), 'gain ready edge') >= capture:
                raise ValueError('selected gain bank is not ready at command capture')
            _integer(gain.get('release_edge'), 'gain residency end', done)
        available = set()
        for res in job['residency']:
            rows = _range(res['lo'], res['hi'])
            if available & rows:
                raise ValueError('duplicate producer row ownership')
            available |= rows
            if not res.get('producer') or not res.get('source_receipt'):
                raise ValueError('actual row producer and source receipt required')
            if _integer(res['ready_edge'], 'producer ready edge') >= capture:
                raise ValueError('producer rows are not ready before command capture')
            last_read = _integer(res['last_read_edge'], 'actual last input read', capture, done)
            _integer(res['release_edge'], 'producer residency end', last_read + 1)
            if rows & outputs and last_read >= first_write:
                raise ValueError('output overwrite precedes completion of the source input reads')
            reads.append(dict(job=identifier, rows=rows, ready=res['ready_edge'], end=last_read+1,
                              producer_job=res.get('producer_job')))

        if not required <= available:
            raise ValueError('physical job lacks required native input rows')
        if kind == 'IK' and not any(r.get('format') == 'fp32_zero_prefix384' and
                                    r['lo'] == 692 and r['hi'] >= 787 for r in job['residency']):
            raise ValueError('IK requires actual384-element zero prefix in rows692..787')
        for wr in job.get('writes', []):
            _integer(wr['row'], 'static input row', 0, 1023)
            _integer(wr['mask'], 'native mask', 1, 15)
            _integer(int(wr['word128'], 16), 'native input word', 0, 2**128-1)
            if not wr.get('producer') or wr.get('role') not in ('input', 'gain', 'parameter', 'zero_prefix'):
                raise ValueError('CTL writes must be actual producer inputs, gains or parameters')
            write_issue = _integer(wr['issue'], 'native input write issue', 0, 2**24-1)
            commit = _integer(wr['commit_edge'], 'actual native input write commit', write_issue, capture-1)
            intervals.append((commit, commit+1, identifier+'::input_write'))

    # Port ownership ends after the final registered native write, independently
    # of output row leases. CP output can remain live while CN consumes it.
    for a, b in zip(sorted(intervals), sorted(intervals)[1:]):
        if b[0] < a[1]:
            raise ValueError('SUKV port reservation overlaps another command or input write')
    for read in reads:
        producer = read['producer_job']
        if producer is not None:
            if producer not in records or producer == read['job']:
                raise ValueError('unknown or self-referential native row producer')
            record = records[producer]
            if not read['rows'] <= record['outputs'] or read['ready'] < record['ready']:
                raise ValueError('producer does not own these rows or output is not readable yet')
        for identifier, record in records.items():
            if identifier in (read['job'], producer):
                continue
            if read['rows'] & record['outputs'] and max(read['ready'], record['first_write']) < min(read['end'], record['done']+2):
                raise ValueError('another physical job overwrites live native input rows')
        for record in records.values():
            for wr in record['job'].get('writes', []):
                if wr['row'] in read['rows'] and read['ready'] <= wr['commit_edge'] < read['end']:
                    raise ValueError('CTL input write overwrites a live producer row')
    return seen


def lower(die, op, ctx):
    result = dict(status='PARTIAL', unit=UNIT, insts=['u_s_3N.leaf0 (KV_ENABLE/KV_CNIK/KV_CP)'],
                  bench=BENCH, rows=[], templates=[], events=[], files={},
                  gap=dict(module='current SUKV producer/calendar binding', port='u_s_3N leaf0',
                           missing='Real KV/CN/IK/CP source exists; provide kv_program.json with absolute producer rows, '
                                   'contexts, fused operation coverage, measured CTL/VP dates and final consumer lifetimes.'))
    program = ctx.get('kv_program')
    path = Path(ctx['fixtures']) / 'kv_program.json' if ctx.get('fixtures') else None
    if program is None and path and path.exists():
        program = json.loads(path.read_text())
    if program is None:
        return result
    jobs = validate(program, ctx['sched'])
    job = jobs.get(op['id'])
    if job is None:
        result['gap']['missing'] = 'Selected model operation has no explicitly covered physical SUKV command.'
        return result
    C = _dvc()
    cp = C.ctl_path(die, 'u_s_3N')
    if job['capture_offset'] != cp['edges'] + _integer(job['leaf_downrelay'], 'source leaf DL') + 6:
        raise ValueError('capture offset differs from actual CTL/XRT/DL/VP/KV source path')
    sid = die.slices()['u_s_3N']['sid']
    result.update(atomic=True, lifetime_qualified=False,
                  source_contract=sukv_contract(), fused_command=job['owner'])
    if job['owner'] != op['id']:
        result['events'] = [dict(cycle=job['issue']+job['capture_offset']+job['done_age'],
                                inst='u_s_3N', port='(fused completion)', dir='int', kind='KV', tag=op['op'], plan_only=True,
                                payload=f"Physical fused {job['kind']} command owned by {job['owner']}")]
        result['gap']['missing'] = 'Fused operation is explicitly covered by '+job['owner']+'; current source/binding remains unqualified.'
        return result
    def emit(issue, target, body, what):
        ix = len(result['templates'])
        result['templates'].append((what, ctl_payload(1 << sid, target, 1, body)))
        result['rows'].append(dict(eng=C.ENG['VN'], issue=issue, arg=(ix & 127) | (command['context'] << 7), template_index=ix, what=what))
    owned = [j for j in program['jobs'] if j['owner'] == op['id']]
    for command in owned:
        if command['capture_offset'] != cp['edges'] + _integer(command['leaf_downrelay'], 'source leaf DL') + 6:
            raise ValueError('prerequisite capture offset differs from selected source path')
        for wr in command.get('writes', []):
            emit(wr['issue'], 5, row_write(wr['row'], wr['mask'], int(wr['word128'], 16)),
                 f"SUKV input {wr['producer']} row{wr['row']}")
        if command['kind'] == 'CP':
            cmd = pool_dispatch(command['slot0_base'], command['slot1_base'], command['output_base'])
        else:
            cmd = dispatch(KINDS[command['kind']], command['gain_set'], command['jid'], command['drain_age'],
                           command.get('parameter_base', 672), command.get('operand_base'))
        emit(command['issue'], 0, cmd, f"SUKV {command['kind']} jid{command.get('jid', 0)}")
    result.update(native_programme=True, retire_not_before=max(j['release_edge'] for j in owned))
    result['gap']['missing'] = ('Native commands emitted from producer receipt. Current die binding and source timing '
                                'receipt must be qualified before whole-calendar LOWERED status.')
    return result
