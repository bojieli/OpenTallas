"""Lossless native HOST CSR images with dimensions derived from actual bytes.

This is a serializer, not a scheduler or a source/retirement qualification. The
104-row entry-page encoder is deliberately unchanged. Production initialization
must be supplied explicitly; no slot/event configuration is invented here.
"""


def _integer(x, bits, what):
    if type(x) is not int or not 0 <= x < 1 << bits:
        raise ValueError(what + ' outside actual field width')
    return x


def _host(op, value=0):
    return ((op | value) << 1) | 1


def decode_image(words):
    words = list(words)
    cells = {}; templates = {}; cf = {}; order = []; begin = []; seal = []; lengths = []
    for word in words:
        _integer(word, 513, 'active CSR HOST word')
        if not word & 1:
            raise ValueError('inactive HOST word')
        d = word >> 1; op = d & 255
        if op == 0x11:
            n = d >> 32 & 255; lengths.append(n); order.append(('length',))
            mask = 255 | (255 << 32)
        elif op == 0x10:
            a = d >> 96 & 127; v = d >> 32 & ((1 << 28)-1); part = v >> 26
            mask = 255 | (((1 << 28)-1) << 32) | (127 << 96)
            if part == 3:
                if a: raise ValueError('header address must be zero')
                (seal if v & (1 << 25) else begin).append(v)
                order.append(('seal' if v & (1 << 25) else 'begin',))
            else:
                if (a, part) in cells: raise ValueError('duplicate calendar row part')
                cells[a, part] = v & ((1 << 26)-1); order.append(('row', a, part))
        elif op == 0x13:
            a = d >> 8 & 127; payload = d >> 16 & ((1 << 186)-1)
            mask = 255 | (127 << 8) | (((1 << 186)-1) << 16)
            if a in templates: raise ValueError('duplicate template address')
            templates[a] = payload; order.append(('template', a))
        elif op == 0x14:
            a = d >> 8 & 1023; payload = d >> 32 & ((1 << 256)-1)
            mask = 255 | (1023 << 8) | (((1 << 256)-1) << 32)
            if a in cf: raise ValueError('duplicate CF address')
            cf[a] = payload; order.append(('CF', a))
        else:
            raise ValueError('image body requires calendar/template/CF CSR; initializer must be explicit and separate')
        if d & ~mask: raise ValueError('reserved CSR bits are nonzero')
    if len(lengths) != 1 or not 1 <= lengths[0] <= 128 or len(begin) != 1 or len(seal) != 1:
        raise ValueError('one actual LEN/BEGIN/SEAL and1..128 rows required')
    n = lengths[0]
    if (begin[0] ^ seal[0]) != 1 << 25 or ((begin[0] >> 9) & 255) != n:
        raise ValueError('BEGIN/SEAL dimensions differ from LEN')
    if set(cells) != {(i, p) for i in range(n) for p in range(3)}:
        raise ValueError('incomplete or extra calendar dimensions')
    if not order.index(('length',)) < order.index(('begin',)) < order.index(('seal',)):
        raise ValueError('SEAL precedes BEGIN')
    rows = []
    for i in range(n):
        v = sum(cells[i, p] << (26*p) for p in range(3)); _integer(v, 76, 'calendar row')
        rows.append(dict(issue=v >> 28 & 0xffffff, done=v >> 52,
                         engine=v >> 24 & 15, arg=v & 0xffffff))
    image = dict(nops=n, stage=begin[0] & 127, start_phase=begin[0] >> 7 & 3,
                 rows=rows, templates=templates, CF=cf, order=order,
                 status='SOURCE_BYTES_ONLY', global_schedule_booked=False, lifetime_qualified=False)
    # This also checks row/header write ordering and all decoded dimensions.
    if encode_image(image) != list(words): raise ValueError('noncanonical image bytes')
    return image


def encode_image(image):
    n = image['nops']; _integer(n, 8, 'LEN')
    if not 1 <= n <= 128 or len(image['rows']) != n:
        raise ValueError('declared and actual row dimensions differ')
    stage = _integer(image['stage'], 7, 'stage'); phase = _integer(image['start_phase'], 2, 'start phase')
    rows = []
    for r in image['rows']:
        rows.append((_integer(r['done'], 24, 'done') << 52) |
                    (_integer(r['issue'], 24, 'issue') << 28) |
                    (_integer(r['engine'], 4, 'engine') << 24) | _integer(r['arg'], 24, 'arg'))
    out = []; seen = set(); begun = sealed = False
    for record in image['order']:
        record = tuple(record)
        if record in seen: raise ValueError('duplicate record in image order')
        seen.add(record); kind = record[0]
        if kind == 'length': out.append(_host(0x11, n << 32))
        elif kind in ('begin', 'seal'):
            if kind == 'begin':
                if begun or sealed: raise ValueError('repeated BEGIN')
                begun = True
            else:
                if not begun or sealed: raise ValueError('invalid SEAL ordering')
                sealed = True
            h = (3 << 26) | ((kind == 'seal') << 25) | (n << 9) | (phase << 7) | stage
            out.append(_host(0x10, h << 32))
        elif kind == 'row':
            if not begun or sealed: raise ValueError('row write outside BEGIN/SEAL')
            _, a, p = record
            if not 0 <= a < n or p not in range(3): raise ValueError('row part outside dimensions')
            out.append(_host(0x10, (a << 96) | ((((rows[a] >> (26*p)) & ((1 << 26)-1)) | (p << 26)) << 32)))
        elif kind == 'template':
            a = _integer(record[1], 7, 'template address')
            if a not in image['templates']: raise ValueError('template record outside decoded dimensions')
            out.append(_host(0x13, (a << 8) | (_integer(image['templates'][a], 186, 'template') << 16)))
        elif kind == 'CF':
            a = _integer(record[1], 10, 'CF address')
            if a not in image['CF']: raise ValueError('CF record outside decoded dimensions')
            out.append(_host(0x14, (a << 8) | (_integer(image['CF'][a], 256, 'CF') << 32)))
        else: raise ValueError('unsupported image record')
    expected = {('length',), ('begin',), ('seal',)} | {('row', i, p) for i in range(n) for p in range(3)}
    expected |= {('template', a) for a in image['templates']} | {('CF', a) for a in image['CF']}
    if seen != expected: raise ValueError('image order omits or adds decoded dimensions')
    return out


def with_initializer(image, initializer_words, decode_initialization):
    """Caller supplies the complete actual MU codec/initializer, never defaults.

    The existing native_mu_calendar.decode_initialization callback checks all8
    events and every slot attribute. Its result is not global/source approval.
    """
    if not initializer_words or not callable(decode_initialization):
        raise ValueError('explicit complete MU initializer and existing decoder required')
    config = decode_initialization(initializer_words)
    return list(initializer_words) + encode_image(image), dict(config=config,
        status='SOURCE_BYTES_ONLY', global_schedule_booked=False, lifetime_qualified=False)


def compatibility(images):
    """Report necessary constraints without retiming/reindexing actual rows."""
    if not images: raise ValueError('actual native images required')
    jobs = []; kits = []
    for i, image in enumerate(images):
        encode_image(image)
        k = [r['issue'] for r in image['rows'] if r['engine'] == 14]
        lower = max((r['done'] for r in image['rows'] if r['engine'] < 14), default=0) + 1
        ki = next((j for j, r in enumerate(image['rows']) if r['engine'] == 14), None)
        after = sum(r['engine'] < 14 for r in image['rows'][ki+1:]) if ki is not None else 0
        jobs.append(dict(job=i, rows=image['nops'], templates=len(image['templates']), CF=len(image['CF']),
                         HOST_words=len(image['order']), KIT=k, row_done_only_KIT_lower_bound=lower,
                         normal_rows_after_KIT=after, marker_reordering_would_shift_row_tags=bool(after),
                         existing_KIT_before_row_done_bound=bool(k and k[0] < lower)))
        kits.extend(k)
    return dict(jobs=jobs, shared_KIT_row_done_only_lower_bound=max(j['row_done_only_KIT_lower_bound'] for j in jobs),
                existing_KIT_values=sorted(set(kits)), single_armed_RL_compatible=len(set(kits)) == 1 and all(len(j['KIT']) == 1 for j in jobs),
                retiming_performed=False, V_row_indices_preserved=True, lifecycle_qualified=False,
                required_contracts=['complete selected resource slot/event initialization', 'source/reset/global HOST/KS booking',
                                    'actual store/consumer retirement and row-tag preservation for any marker changes'])
