#!/usr/bin/env python3
"""Opt-in R5 QXPQ go-boundary lowering; legacy calendars and frames stay unchanged.

The GB primitive captures GO/TAG by one edge. A dated LC calendar therefore
moves only GO bit0 earlier by one edge. CFG/date/X payload bits stay identical.
The dynamic legacy spine couples GO and stream start; this helper does NOT
claim that provider supports the new contract. Supply an independently dated
GO provider and an actual earliest-legal-GO trace before adopting the result.
"""
import argparse
import copy
import json
import re
from pathlib import Path

LEGACY = 'ot_v41_rom_elem_q_qxpq_w10'
GB = LEGACY + '_gb'
GB_LEF = 'physical/die_plan/s81/cores/elem_boundary/' + GB + '.lef'
GB_PINS = 'inputs/core_pins/' + GB + '.json'


def contract():
    return dict(legacy_module=LEGACY, module=GB, legacy_pins=739, pins=737,
                removed_inputs=['xs_sv[0]', 'xs_sv[1]'],
                GO_BOUNDARY=1, CGR=8, go_capture_edges=1,
                go_issue_advance_edges=1, cfg_shift_edges=0, x_shift_edges=0,
                return_shift_edges=0, return_basis='conditional on the primitive and dated-GO composition gates',
                native_dynamic_spine_qualified=False)


def lower_lc_words(words, earliest_go, *, enabled=False):
    """Dense source LC words sampled one per edge; earliest_go is measured at THIS LC input boundary.
    Missing timing is an error. Adjacent launches and before-reset/before-load launches are rejected.
    No tags are stored in LC: the actual CFG7 sequencer generates the op tag from its GO counter.
    """
    if not enabled:
        return list(words), dict(contract='legacy', changed_edges=[])
    if not words or any(type(w) is not int or w < 0 for w in words):
        raise ValueError('nonempty unsigned native LC words required')
    go = [t for t, w in enumerate(words) if w & 1]
    if len(earliest_go) != len(go) or any(type(t) is not int or t < 0 for t in earliest_go):
        raise ValueError('one actual earliest-legal-GO edge per pulse is required')
    if any(t == 0 or (t + 1 < len(words) and words[t + 1] & 1) or (t > 0 and words[t - 1] & 1) for t in go):
        raise ValueError('GO must be an isolated one-edge pulse with an earlier source edge')
    out = list(words)
    for t, legal in zip(go, earliest_go):
        if t - 1 < legal:
            raise ValueError(f'GB GO at {t-1} precedes actual reset/load-ready edge {legal}')
        out[t] &= ~1
        out[t-1] |= 1
    assert all((a & ~1) == (b & ~1) for a, b in zip(words, out))
    return out, dict(contract=contract(), changed_edges=[dict(old=t, new=t-1) for t in go],
                     earliest_go=list(earliest_go), qualification='dated-LC transformation only; native provider gate still required')


def _group(s, start):
    if s[start] != '(':
        raise ValueError('expected balanced parenthesized group')
    depth, quote, esc = 0, False, False
    for i in range(start, len(s)):
        c = s[i]
        if quote:
            if esc: esc = False
            elif c == '\\': esc = True
            elif c == '"': quote = False
        elif c == '"': quote = True
        elif c == '(': depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0: return i + 1
    raise ValueError('unclosed source group')


def _named(s):
    """Named parameter/port spans, parsed with nesting rather than a regex over expressions."""
    spans = {}
    pos = 0
    while pos < len(s):
        m = re.search(r'\.\s*(\w+)\s*\(', s[pos:])
        if not m: break
        begin = pos + m.start(); p = pos + m.end() - 1; end = _group(s, p)
        if m.group(1) in spans: raise ValueError('duplicate named connection: ' + m.group(1))
        spans[m.group(1)] = (begin, end, s[p+1:end-1].strip())
        pos = end
    return spans


def lower_frame_text(text):
    """Swap only actual QXPQ instances; drop the proved-unused xs_sv input connection, preserving its upstream driver wires.
    Parameter expressions and all other connections are byte-preserved. This changes the GO input contract;
    callers must select the matching calendar explicitly. No automatic canonical source writes.
    """
    edits, removed, instances = [], set(), []
    pattern = re.compile(r'(?m)^[ \t]*' + re.escape(LEGACY) + r'\s*#\s*\(')
    for m in pattern.finditer(text):
        p0 = text.find('(', m.start()); p1 = _group(text, p0)
        nm = re.match(r'\s*(\w+)\s*\(', text[p1:])
        if not nm: raise ValueError('unsupported QXPQ instance syntax')
        c0 = p1 + nm.end() - 1; c1 = _group(text, c0)
        params = _named(text[p0+1:p1-1]); ports = _named(text[c0+1:c1-1])
        if params.get('NB', (None,None,None))[2] != '2':
            raise ValueError('GB737 contract requires the actual NB2 instance')
        for key, value in (('PP','1'), ('PQ','1'), ('QX','10')):
            if params.get(key, (None,None,None))[2] != value:
                raise ValueError('unqualified GB input-elision profile: ' + key)
        for key, value in (('GO_BOUNDARY','1'), ('CGR','8')):
            if key in params and params[key][2] != value:
                raise ValueError('conflicting explicit parameter ' + key)
        body = text[c0+1:c1-1]
        if 'xs_sv' in ports:
            a,b,expr = ports['xs_sv']; nets = re.findall(r'\b[A-Za-z_]\w*\b', expr)
            if re.sub(r'[\s{},A-Za-z_0-9]', '', expr):
                raise ValueError('xs_sv is not a simple unused net bundle')
            left, right = body[:a], body[b:]
            if right.lstrip().startswith(','):
                right = re.sub(r'^\s*,', '', right, count=1)
            elif left.rstrip().endswith(','):
                left = re.sub(r',\s*$', '', left, count=1)
            body = left + right
        add = ''.join(', .%s(%s)' % (k,v) for k,v in (('GO_BOUNDARY','1'),('CGR','8')) if k not in params)
        prefix = text[m.start():p0].replace(LEGACY, GB, 1)
        replacement = prefix + '(' + text[p0+1:p1-1] + add + ')' + text[p1:c0+1] + body + ')'
        edits.append((m.start(),c1,replacement)); instances.append(nm.group(1))
    if not edits: raise ValueError('no actual legacy NB2 QXPQ instances')
    for a,b,r in reversed(edits): text = text[:a] + r + text[b:]
    return text, dict(instances=instances, dropped_inputs=['xs_sv'], upstream_wires_preserved=True, contract=contract(),
                      qualified=False, blockers=['dated GO provider and primitive/frame composition gates required'])


def lower_plan(raw, ready_types):
    """Candidate plan only, explicitly selected SOURCE-qualified types; never attach an unsigned timing library."""
    out = copy.deepcopy(raw); changed = []
    if not ready_types: raise ValueError('explicit ready type selection required; no whole-plan implicit adoption')
    for name in ready_types:
        t = out['partition_types'][name]; count = 0
        for hc in t.get('hard_cores', []):
            if hc.get('module') != LEGACY: continue
            if hc.get('lib'): raise ValueError('replacing a signed view needs an explicit re-sign analysis')
            hc.update(module=GB, lef=GB_LEF, pins_file=GB_PINS)
            count += 1
        if not count: raise ValueError('ready type has no legacy QXPQ: ' + name)
        changed.append(dict(type=name, hard_core_declarations=count))
    return out, dict(changed=changed, contract=contract(), qualified=False,
                      blockers=['new GB view/centre-clock abstract and dated GO frame gate required before route'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rtl',type=Path);p.add_argument('--plan',type=Path)
    p.add_argument('--types',nargs='+');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if bool(a.rtl)==bool(a.plan):p.error('choose exactly one source RTL or candidate plan')
    if a.rtl:
        text,receipt=lower_frame_text(a.rtl.read_text());a.out.write_text(text)
    else:
        result,receipt=lower_plan(json.loads(a.plan.read_text()),a.types);a.out.write_text(json.dumps(result,indent=1)+'\n')
    a.out.with_suffix(a.out.suffix+'.contract.json').write_text(json.dumps(receipt,indent=1)+'\n')

if __name__=='__main__':main()
