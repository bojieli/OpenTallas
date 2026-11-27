#!/usr/bin/env python3
"""any_plan_records: every signed-off record on ANY plan, for the explorer (EXPLORER-STORE-R1, OWNER 2026-11-22: the archive
and the explorer cover all closures on any plan; any-plan sign-offs count).

The design index (design_index.py) holds the nodes of the CURRENT die plans.  A signed record of an older plan block (a
superseded type, a retired-plan unit) has no node there, so before this module it was neither listed nor viewable.  Here
each archived signed unit becomes one record:

  id        <die>.<t|c>.<element>   the same id scheme as the design index nodes (tid / cid), with the re-sign suffix
                                    (__a<n>_<hhmm>, __legalrows_<n>) dropped, so a current-plan record IS its node and its
                                    routed-layout pack (layout store elements/<id>/) is shared
  plan      'current'               the id is a node of the current plan, signed there
            'superseded'            older plan block; plan_label says whether the name is still in the current plan
                                    (re-sign pending) or not (retired plan)
  archive   rtx (signed-export-1114 full record), agi (AGIdock INDEX row), status (INDEX status), path
  pack      the layout store entry (design_index.store_entry shape) or None

Sources (read-only): the AGIdock INDEX.tsv text mirrored in archive_index.json (agidock_index_tsv, the archive of record),
the rtx-pro export listing of the same file (export rows), the design index nodes, the layout store.
"""
import os
import re

VARIANT = re.compile(r"__(a\d+_\d{4}|legalrows_\d+)$")   # = count_hourly.VARIANT: a re-sign of the same unit, not a new one
AX = re.compile(r"__ax_[0-9a-f]{10}$")                      # AUTO-EXPORT unit dir suffix (ODB sha)
DIES = ('s81_head', 's81', 'qwen_compute', 'qwen_kvsys', 'hbm')
SIGNED_STATUS = ('ARCHIVED', 'RTX-FULL', 'SHA-DIFFERS')
LABEL = {'current': 'current plan', 'resign': 'superseded: older block of a current-plan design (re-sign pending)',
         'retired': 'superseded: retired plan (name not in the current plan)'}


def load_element_alias(path=None):
    """(die, archived element) -> element from tools/autopilot/archive_element_alias.tsv (ARCHIVE-ALIAS-1124): an archived unit exported under a
    wrong element name maps to its real design; the append-only INDEX itself is never edited.  Missing / unreadable file -> {}."""
    p = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "autopilot", "archive_element_alias.tsv")
    out = {}
    try:
        lines = open(p).read().splitlines()
    except OSError:
        return out
    for ln in lines[1:]:
        f = ln.split("\t")
        if len(f) >= 3 and f[0] and f[1] and f[2]:
            out[(f[0], f[1])] = f[2]
    return out


ALIAS = load_element_alias()


def base_name(el, die=None):
    el = AX.sub('', el or '')
    el = ALIAS.get((die, el), el)
    return VARIANT.sub('', el)


def record_id(die, kind, el, nodes=None, *, use_alias=True):
    """<die>.<t|c>.<base element>; when only the other level is a node of the current plan, that one"""
    b = base_name(el, die if use_alias else None)
    if kind == 'core':   # legacy INDEX spells out the role, including for retired cores
        return '%s.c.%s' % (die, b)
    k = kind if kind in ('t', 'c') else 't'
    nid = '%s.%s.%s' % (die, k, b)
    if nodes is not None and nid not in nodes:
        o = '%s.%s.%s' % (die, 'c' if k == 't' else 't', b)
        if o in nodes: return o
    return nid


def parse_index(tsv):
    """AGIdock INDEX.tsv text -> [row dict] (header line names the columns)"""
    lines = [l for l in (tsv or '').splitlines() if l.strip()]
    if not lines: return []
    head = lines[0].split('\t')
    return [dict(zip(head, l.split('\t'))) for l in lines[1:]]


def indexed_archive_bodies(index_tsv, nodes=None):
    """Exact body identities of normal signed INDEX rows."""
    levels = {'c': 'core', 'core': 'core', 't': 'type', 'type': 'type'}
    for row in parse_index(index_tsv):
        level = levels.get(row.get('kind'))
        if level is None or not row.get('status', '').startswith(('ARCHIVED', 'RTX-FULL')):
            continue
        record, odb_sha = row.get('record', ''), row.get('sha256', '')
        db = row.get('rtx_db') or row.get('db')
        if ((db or '').endswith('/6_final.odb') and re.fullmatch(r'[a-f0-9]{64}', odb_sha)
                and (not record or re.fullmatch(r'[a-f0-9]{64}', record))):
            if nodes is not None:
                rid = record_id(row['die'], row['kind'], row['element'], nodes)
                level = 'core' if rid.split('.', 2)[1] == 'c' else 'type'
            yield row, level, db.rsplit('/', 2)[-2], record, odb_sha


def source_archives(index_tsv, refs):
    """Resolve uniquely recorded native signoffs without joining by module name."""
    if not refs:
        return {}
    result = {}
    ambiguous = set()
    for row, level, unit, record, odb_sha in indexed_archive_bodies(index_tsv):
        if not record:
            continue
        source = re.match(r'^AUTO-EXPORT-1118 ([A-Za-z0-9_.-]+:/\S+/signoff\.json)(?:\s|$)',
                          row.get('src', ''))
        if source is None:
            continue
        key = row.get('die'), level, source[1]
        if key not in refs or key in ambiguous:
            continue
        prev = result.get(key)
        if prev and (prev['record'], prev['odb_sha256']) != (record, odb_sha):
            del result[key]
            ambiguous.add(key)
            continue
        result[key] = dict(agi=True, rtx=bool(row.get('rtx_db') or (prev or {}).get('rtx')),
                           status=row['status'], units=[unit],
                           record=record, odb_sha256=odb_sha)
    return result


def build(nodes, index_tsv, export_rows=None, store_entry=None, *, exact_retired_ids=()):
    """-> {id: record}.  nodes: design index nodes; index_tsv: AGIdock INDEX.tsv text; export_rows: archive_index.json 'export'
    (rtx-pro signed-export-1114 dirs: die, name, path, odb); store_entry(id) -> pack summary or None.
    An explicitly counted retired archive name has priority over its display alias."""
    names = {}   # (die, name) of every current-plan node and type module: a superseded record of such a name is a re-sign backlog
    for n in nodes.values():
        if n.get('level') in ('type', 'core'):
            names[(n['die'], n.get('name'))] = n['id']
            m = (n.get('plan') or {}).get('module')
            if m: names[(n['die'], m)] = n['id']
    out = {}

    def archive_id(die, kind, el):
        if (die, AX.sub('', el or '')) in ALIAS:
            raw = record_id(die, kind, el, use_alias=False)
            if raw in exact_retired_ids:
                return raw
        return record_id(die, kind, el, nodes)

    def add(die, kind, el, arch):
        rid = archive_id(die, kind, el)
        n = nodes.get(rid)
        st = ((n or {}).get('status') or {}).get('state')
        plan = 'current' if st == 'signed' else 'superseded'
        why = 'current' if plan == 'current' else ('resign' if n or (die, base_name(el, die)) in names else 'retired')
        r = out.get(rid)
        if r is None:
            r = out[rid] = dict(id=rid, die=die, level='core' if rid.split('.')[1] == 'c' else 'type', name=rid.split('.', 2)[2], plan=plan,
                                plan_label=LABEL[why], superseded=plan != 'current', node=rid if n else None,
                                node_state=st, archive=dict(agi=False, rtx=False, status=None, units=[]), pack=None)
        a = r['archive']
        a['agi'] = a['agi'] or bool(arch.get('agi')); a['rtx'] = a['rtx'] or bool(arch.get('rtx'))
        if arch.get('status') and not a['status']: a['status'] = arch['status']
        if arch.get('unit') and arch['unit'] not in a['units'] and len(a['units']) < 8: a['units'].append(arch['unit'])
        return r

    for row in parse_index(index_tsv):
        die = row.get('die')
        if die not in DIES or not str(row.get('status') or '').startswith(SIGNED_STATUS): continue
        add(die, row.get('kind'), row.get('element'), dict(agi=True, rtx=bool(row.get('rtx_db')), status=row.get('status'),
                                                          unit=(row.get('rtx_db') or row.get('db') or '').rsplit('/', 2)[-2] if (row.get('rtx_db') or row.get('db')) else row.get('element')))
    for e in export_rows or []:   # rtx-pro full records without an INDEX row (older exports, NO-DB rows whose DB rtx-pro holds)
        if e.get('die') not in DIES or not e.get('odb'): continue
        rid = archive_id(e['die'], 't', e.get('name'))
        if rid in out:
            out[rid]['archive']['rtx'] = True
            continue
        if nodes.get(rid) and (nodes[rid].get('status') or {}).get('state') == 'signed':   # a current-plan sign-off: the rtx-pro copy is its archive
            add(e['die'], 't', e.get('name'), dict(rtx=True, status='RTX-ONLY', unit=e.get('name')))
    for nid, n in nodes.items():   # current-plan sign-offs that no archive holds yet: listed, archive empty
        if n.get('level') in ('type', 'core') and (n.get('status') or {}).get('state') == 'signed' and nid not in out:
            out[nid] = dict(id=nid, die=n['die'], level=n['level'], name=n.get('name'), plan='current', plan_label=LABEL['current'], superseded=False,
                            node=nid, node_state='signed', archive=dict(agi=False, rtx=False, status=None, units=[]), pack=None)
    for rid, r in out.items():
        r['pack'] = (store_entry(rid) if store_entry else None) or ((nodes.get(rid) or {}).get('layout') or {}).get('store')
    return out


def summary(records):
    """per die: any-plan signed / archived / viewable (+ current / superseded split)"""
    out = {}
    for r in records.values():
        d = out.setdefault(r['die'], dict(signed=0, archived=0, viewable=0, current=0, superseded=0, current_viewable=0, superseded_viewable=0))
        d['signed'] += 1
        d['archived'] += 1 if (r['archive']['agi'] or r['archive']['rtx']) else 0
        v = 1 if r.get('pack') else 0
        d['viewable'] += v
        k = 'superseded' if r['superseded'] else 'current'
        d[k] += 1; d[k + '_viewable'] += v
    tot = {k: sum(d[k] for d in out.values()) for k in ('signed', 'archived', 'viewable', 'current', 'superseded', 'current_viewable', 'superseded_viewable')}
    return dict(dies=out, total=tot)
