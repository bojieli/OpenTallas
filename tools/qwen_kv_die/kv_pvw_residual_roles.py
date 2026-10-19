#!/usr/bin/env python3
"""KV-FUNC-OPENS 10-19: exact output contracts for the GEN7 PVW residual roles (fail-closed, die + source SHA pinned).

Adds per-instance spare OUTPUT declarations only for bits that are structurally unused by construction:

 1. Duplicate relay cargo (classes branch_subset_cargo_CP / _X, duplicate_reset_cargo, delay_terminal_cargo,
    age_pv_branch_duplicate).  The bit is an output of a pinned bit-independent standard relay (qkd_rlys_*, one flop per
    bit), it has NO other connection on the die, its same-lane provenance through standard relays ends at a non-constant
    origin bit O, and O reaches a real (non-standard-relay) reader or a die output through ANOTHER relay branch.  The
    bit is therefore a copy of information that is consumed elsewhere; nothing is lost by not reading it.  For PVW frame
    stations the same station bit must also be unreferenced in the pinned generated frame source (qkd_pvw_die_t_ba.sv),
    so the discard is the generator's construction, not a flattening loss.  Zero-origin bits are NOT this class
    (kv_output_pads / kv_pvw_padding own literal padding) and are refused here.
 2. PV pair control outputs (ot_qwen_tp8_pv_wide_ctl_tb, pinned SHA):
      cmd[59:32]  reserved_zero_command: reset and every edge write cmd<=0; no source assignment above bit 31.
      busy, out_age  self_checked_status: busy<=state!=IDLE and out_age<=k_oa+nq are their only writes; the hazards they
                  would describe are checked inside the tile and reported on `fault` (start while not IDLE -> flt; column
                  y_valid off the static out_slot -> flt; every fault exit returns to IDLE), and that fault pin must
                  have a reader on the die.  Static schedule: no consumer may use busy as a ready/backpressure signal.
Every other unread bit is refused (reported, never declared).  Requires the binder's multi_driven=0 on the same die.
"""
import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import kv_output_pads as O
P = O.P
ROOT = O.ROOT
FRAME = 'rtl/qwen_sys/split_20261014/qkd_pvw_die_t_ba.sv'
CTL = 'rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_tb.sv'
SOURCES = {
    FRAME: 'b15daa62c06da889ee7e0db600b08079e45862397208329b9d2e886b26ba5dad',
    'rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv': '4601aa6d6ccb8b201d2f991a028a972d77f505506bc1ea87d5495738f0a7064d',
    'tools/qwen_kv_die/pv_trunk_gen.py': '85e6bb225c010e1758b0dbcf8e24ebb20e1ab562b304c3f159ade8c787ba9458',
    CTL: '707680841087a2a7ef3871e47541843863a1eaa60a9a23e144af266077ed4bba',
    O.RTL: O.RTL_SHA,
}
CTL_MASTER = 'ot_qwen_tp8_pv_wide_ctl_tb'
PARENT = re.compile(r'^(pvw_[01])__(?:g_ok_)?(u_\w+)$')
CLASSES = [
    (re.compile(r'^pvw_[01]__(?:g_ok_)?u_CP\w+_r\d+$'), 'branch_subset_cargo_CP'),
    (re.compile(r'^pvw_[01]__(?:g_ok_)?u_X\d+c\d+_r\d+$'), 'branch_subset_cargo_X'),
    (re.compile(r'^pvw_[01]__(?:g_ok_)?u_S\d+b\d+_r\d+$'), 'duplicate_reset_cargo'),
    (re.compile(r'^pvw_[01]__(?:g_ok_)?u_DL\d+_r\d+$'), 'delay_terminal_cargo'),
    (re.compile(r'^rly_(?:pinfix_)?ks_age_pv_\w+$'), 'age_pv_branch_duplicate'),
]
CTL_FACTS = [  # exact source statements the self_checked_status / reserved_zero contract relies on
    r'if\(!local_rst_n\)cmd<=0;',
    r'else begin\s*cmd<=0;',
    r'if\(!local_rst_n\)begin fault<=0;busy<=0;out_age<=0;out_epoch<=0;end',
    r'fault<=flt;busy<=state!=IDLE;out_epoch<=ep;\s*out_age<=k_oa\+nq;',
    r'else if\(\(start_r&&state!=IDLE\)\|\|\(state!=IDLE&&cbad\)\)begin state<=IDLE;flt<=1;end',
    r'if\(state!=IDLE&&cv_r\[0\]!=out_slot\)cbad=1;',
    r'output reg\[59:0\] cmd',
]


def ranges(bits):
    out = []
    for b in sorted(bits):
        if out and b == out[-1][1] + 1:
            out[-1][1] = b
        else:
            out.append([b, b])
    return out


def check_sources(root, sources):
    for rel, sha in sources.items():
        p = Path(root) / rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            raise ValueError('PVW residual source changed; re-prove ' + rel)


def ctl_facts(text):
    t = re.sub(r'//[^\n]*', '', text)
    for f in CTL_FACTS:
        if not re.search(f, t):
            raise ValueError('pinned PV control fact absent: ' + f)
    hi = [int(m.group(1)) for m in re.finditer(r'\bcmd\[(\d+)(?::\d+)?\]\s*<=', t)]
    if not hi or max(hi) > 31:
        raise ValueError('PV control writes a command bit above 31')
    for sig, n in (('busy', 2), ('out_age', 2)):
        if len(re.findall(r'\b%s\s*<=' % sig, t)) != n:
            raise ValueError('PV control ' + sig + ' has other writes')


def frame_index(text):
    """Generated frame source: wire -> driving relay rows [(inst, lo, hi)], and every other (lo, hi | whole) reference."""
    t = re.sub(r'//[^\n]*', '', text)
    driver, refs = defaultdict(list), defaultdict(list)
    for ln in t.splitlines():
        if re.match(r'\s*wire\b', ln):
            continue   # declarations are not references
        m = re.match(r'\s*qkd_rlys_(\d+)\s+(\w+)\s*\(.*\.b\(\s*(w_\w+)\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*\)\s*\);\s*$', ln)
        if m:
            w = int(m.group(1)); hi = int(m.group(4)) if m.group(4) else w - 1; lo = int(m.group(5)) if m.group(5) else 0
            if hi - lo + 1 != w:
                raise ValueError('frame relay output slice width mismatch: ' + m.group(2))
            if any(not (hi < l or lo > h) for _, l, h in driver[m.group(3)]):
                raise ValueError('frame wire bit driven twice: ' + m.group(3))
            driver[m.group(3)].append((m.group(2), lo, hi))
            ln = ln[:ln.rindex('.b(')]
        for r in re.finditer(r'\b(w_\w+)\b(\s*\[\s*(\d+)\s*(?::\s*(\d+)\s*)?\])?', ln):
            if r.group(2) is None:
                refs[r.group(1)].append(None)
            else:
                hi = int(r.group(3)); lo = int(r.group(4)) if r.group(4) is not None else hi
                refs[r.group(1)].append((min(hi, lo), max(hi, lo)))
    return driver, refs


def frame_unread(index, src_inst, wire, bit):
    """True when the frame source drives wire[bit] from src_inst and nothing else in the frame references wire[bit]."""
    driver, refs = index
    if not any(i == src_inst and lo <= bit <= hi for i, lo, hi in driver.get(wire, ())):
        return False
    return not any(r is None or r[0] <= bit <= r[1] for r in refs.get(wire, ()))


def derive(die, root=ROOT, existing=None, sources=SOURCES):
    check_sources(root, sources)
    ctl_facts((Path(root) / CTL).read_text())
    frame = frame_index((Path(root) / FRAME).read_text())
    die = Path(die)
    sha = hashlib.sha256(die.read_bytes()).hexdigest()
    doc = json.loads(json.dumps(existing or dict(pads={}, instances={})))
    prev = doc.get('source_contract', {}).get('die_sha256')
    if prev and prev != sha:
        raise ValueError('existing pads belong to a different die')
    pads = P.load_pads(doc)
    nets, tin, tout, insts = P.parse_die(str(die))
    conns = defaultdict(list)       # (net, bit) -> [(inst, port, master)]
    portbits = {}                   # (inst, port) -> MSB-first bits
    master_of = {}
    for m, inst, prm, cm in insts:
        if m == '__assign__':
            raise ValueError('unexpected top assignment in bound die')
        master_of[inst] = m
        for pn, e in cm.items():
            bits = P.expr_bits(e, nets) if e else []
            if bits is None:
                raise ValueError(f'{inst}.{pn}: unparsed connection')
            portbits[(inst, pn)] = bits
            for b in bits:
                if b[0] not in ('CONST', 'Z', 'UNDECL'):
                    conns[tuple(b)].append((inst, pn, m))
    drivers, rev = {}, defaultdict(list)
    for m, inst, prm, cm in insts:
        if m not in O.STANDARDS:
            continue
        aa, bb = portbits.get((inst, 'a')), portbits.get((inst, 'b'))
        if prm or aa is None or bb is None or len(aa) != O.STANDARDS[m] or len(bb) != len(aa):
            raise ValueError(f'{inst}: unqualified standard relay')
        for a, b in zip(aa, bb):
            if b[0] in ('CONST', 'Z', 'UNDECL') or tuple(b) in drivers:
                raise ValueError(f'{inst}: nonunique relay output {b}')
            drivers[tuple(b)] = tuple(a)
            rev[tuple(a)].append(tuple(b))

    def spare(inst, port, pbit, width):
        m = master_of[inst]
        key = (m, port, inst) if (m, port, inst) in pads else (m, port)
        return key in pads and pbit in P.pad_bits(pads[key], width)

    def lone(bit):  # only its own driver pin touches it and it is not a die output
        return len(conns.get(bit, ())) == 1 and bit[0] not in tout and bit[0] not in tin

    def origin(bit):
        seen = set()
        while bit in drivers:
            if bit in seen:
                raise ValueError('cycle in relay provenance')
            seen.add(bit); bit = drivers[bit]
        return bit

    reader_cache = {}

    def consumed(o):
        """o (a non-relay-driven bit) reaches a non-standard-relay reader or a die output through relay copies."""
        if o in reader_cache:
            return reader_cache[o]
        stack, seen, ok = [o], {o}, False
        while stack and not ok:
            b = stack.pop()
            if b[0] in tout:
                ok = True; break
            others = [c for c in conns.get(b, ()) if c[2] not in O.STANDARDS]
            # o itself is driven by exactly one non-relay output pin (multi_driven=0); any further non-relay pin reads it
            if len(others) > (1 if b == o and b not in drivers and b[0] not in tin else 0):
                ok = True; break
            for nb in rev.get(b, ()):
                if nb not in seen:
                    seen.add(nb); stack.append(nb)
        reader_cache[o] = ok
        return ok

    add = defaultdict(set)      # inst -> set of b port bits
    cls = Counter(); refused = Counter(); examples = defaultdict(list)
    for m, inst, prm, cm in insts:
        if m not in O.STANDARDS:
            continue
        label = next((lab for rx, lab in CLASSES if rx.match(inst)), None)
        if label is None:
            continue
        bb = portbits[(inst, 'b')]; w = len(bb)
        for k, b in enumerate(bb):
            b = tuple(b); pbit = w - 1 - k
            if not lone(b) or spare(inst, 'b', pbit, w):
                continue
            o = origin(b)
            why = None
            if o[0] in ('CONST', 'Z', 'UNDECL'):
                why = 'constant origin (padding prover scope)'
            elif not consumed(o):
                why = 'origin not consumed by any other branch'
            elif label != 'age_pv_branch_duplicate':
                pm = PARENT.match(inst)
                pre = 'n_' + (pm.group(1) if pm else '') + '__'
                if not pm or not b[0].startswith(pre + 'w_'):
                    why = 'PVW station output not a frame wire'
                elif not frame_unread(frame, pm.group(2), b[0][len(pre):], b[1]):
                    why = 'bit referenced in generated frame source'
            if why:
                refused[why] += 1
                if len(examples[why]) < 5:
                    examples[why].append([inst, pbit, list(b)])
                continue
            add[inst].add(pbit); cls[label] += 1
    ctl_seen = 0
    for m, inst, prm, cm in insts:
        if m != CTL_MASTER:
            continue
        ctl_seen += 1
        fb = portbits.get((inst, 'fault'))
        if not fb or len(fb) != 1 or not (len(conns.get(tuple(fb[0]), ())) > 1 or fb[0][0] in tout):
            raise ValueError(f'{inst}: PV control fault has no die reader; self-checked status contract void')
        for port, want, label in (('cmd', range(32, 60), 'reserved_zero_command'),
                                  ('busy', range(0, 1), 'self_checked_status'),
                                  ('out_age', range(0, 16), 'self_checked_status')):
            bb = portbits.get((inst, port))
            if not bb:
                raise ValueError(f'{inst}.{port} unconnected; open-port scope, not this contract')
            w = len(bb)
            for k, b in enumerate(bb):
                pbit = w - 1 - k
                if pbit not in want or b[0] in ('CONST', 'Z', 'UNDECL') or not lone(tuple(b)):
                    continue
                if spare(inst, port, pbit, w):
                    continue
                add[(inst, port)].add(pbit); cls[label] += 1
    if ctl_seen != 2:
        raise ValueError('expected exactly two PV pair control instances')
    entries = doc.setdefault('instances', {})
    reason = ('KV-FUNC-OPENS pvw_residual_contract: exact source-pinned PVW residual role (duplicate relay cargo consumed '
              'on another branch / reserved-zero command / self-checked status); see kv_pvw_residual_roles.py')
    for key, bits in add.items():
        inst, port = (key, 'b') if isinstance(key, str) else key
        ent = entries.setdefault(inst, dict(master=master_of[inst], reason=reason, ports={}))
        if ent.get('master') != master_of[inst]:
            raise ValueError('existing instance master changed: ' + inst)
        if reason not in ent.get('reason', ''):
            ent['reason'] = (ent.get('reason', '') + '; ' + reason).lstrip('; ')
        w = len(portbits[(inst, port)])
        old = P.pad_bits(ent['ports'][port], w) if port in ent.get('ports', {}) else set()
        ent.setdefault('ports', {})[port] = ranges(old | bits)
    doc['pvw_residual_contract'] = dict(die_sha256=sha, source_sha256=dict(sources), bits=sum(cls.values()),
                                        classes=dict(cls), refused=dict(refused), refused_examples=dict(examples))
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--die', type=Path, required=True)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--existing', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    d = derive(a.die, a.root, json.loads(a.existing.read_text()))
    a.out.write_text(json.dumps(d, indent=1) + '\n')
    c = dict(d['pvw_residual_contract']); c.pop('refused_examples', None)
    print(json.dumps(c))


if __name__ == '__main__':
    main()
