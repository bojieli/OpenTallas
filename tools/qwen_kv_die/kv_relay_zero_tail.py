#!/usr/bin/env python3
"""KV-FUNC-OPENS 10-19: exact relay WIDTH-PADDING output contract (zero-tail of a standard relay word).

Relays are hardened once at standard widths (qkd_rlys_{1,36,296,528}, the forwarded qkd_rlysh*/qkd_landsh* lanes and the
resettable ASTK face-landed qkd_astk_rly_296_fl).  A narrower logical lane carried in a standard word fills its upper bits
with literal zeros (source examples: qkd_astk_delay `line[0]={{(C*296-W){1'b0}},d}` + `q=line[D][W-1:0]`; generated
pvtap/pvfork/aq/acal words `{N'b0, payload}`).  kv_output_pads.py admits such bits only when the generator routed them to a
private `n_<inst>__spare` wire; the GEN7 generator instead routes them to private line/tap nets, which the strict binder
reports as unread.

A relay output bit b[i] is admitted here ONLY when ALL of the following hold on the exact bound die:
  1. the instance master is one of the pinned bit-independent relay families, without parameters, at its standard width;
  2. following b[i] <- a[i] backwards through such relays (same bit index; pin-repair lanes included) reaches the literal
     1'b0 with no logic, cycle, top port or other driver on the way (forwarded/landing lanes pass payload bits
     independently; the ASTK relay resets to 0, so a zero input gives a zero output in every cycle);
  3. at that origin relay the literal-zero input bits form ONE contiguous MSB tail [k, W) and every bit below k is a live
     (non-constant) payload bit -- i.e. the zeros are width padding of a narrower lane, never a hole in a live word;
     OR (chain-head lane) the origin word is literal zero in every bit and, at the END relay, the unconnected bits form
     one contiguous MSB tail [k, W) with every bit below k read (the consumer's lane width);
  4. the net bit b[i] appears nowhere else in the die (no reader of any direction, not a die port).
No other output (control, clock, fault, tie, status) is ever admitted; any violation is reported, not declared.
Every relay source file is pinned by SHA-256; a changed source or die refuses.
"""
import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import die_port_bind as P  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    'rtl/qwen_sys/kv_rly_std_20261016/qkd_rlys.sv': '62c15fc98ea519674d8f1e606b936b89e6e5718867c571d0939dd9ca985f4d7e',
    'rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv': 'a40160aeeb388dd333b6495f9ce01175bd2117d4086822db1ccd9f46d68af849',
    'rtl/qwen_split/qfd_fwd_lane.sv': '16d2375b15110a3613eaf684c727e50933a1b877b48347364a383ad3c3ef7622',
       # KV-BIND3 10-19: rc1 wrapper (10 kept reset relay copies, ot_rst_relay REGIONS 10; data path b <= a unchanged;
    # previous pin f6e02fd5...).
    'rtl/lib/face_land/qkd_astk_rly_296_fl.sv': '5bc0e385388c96472fa62651c15f8ea489ceda3d4ce12671a07e7a1d63b49904',
    'rtl/qwen_sys/split_20261014/qkd_astk_phys.sv': '5ee9ea58b745976317976492caab21541487c247c7e953733c359f7c9bec18de',
    'rtl/lib/ot_rst_relay.sv': '0071a3d067e72da7a450dd265aa8390b968f0228491ed2245fe8947b499264c5',
}
STANDARDS = {f'qkd_rlys_{w}': w for w in (1, 36, 296, 528)}
FORWARDED = {f'qkd_{f}_{w}': w for f in ('rlysh0', 'rlysh', 'landsh0', 'landsh') for w in (1, 36, 296, 528)}
ASTK = {'qkd_astk_rly_296_fl': 296}
FAMILIES = dict(STANDARDS, **FORWARDED, **ASTK)
RULE = ('relay width padding: unread relay b bit whose same-index relay-only provenance is literal 0, the origin zeros '
        'form the contiguous MSB tail of the origin word over a live low payload, and the net bit has no other connection')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pinned_sources(root, pins=None):
    """Return {rel: sha}; every pin must match (tests may pass replacement pins)."""
    out = {}
    for rel, want in SOURCES.items():
        p = Path(root) / rel
        if not p.is_file():
            raise ValueError('relay source missing: ' + rel)
        got = sha(p)
        want = (pins or {}).get(rel, want)
        if got != want:
            raise ValueError('relay source changed; re-prove the bitwise a -> flop -> b contract: ' + rel)
        out[rel] = got
    # the ASTK core must stay a per-bit registered copy with reset to zero
    core = (Path(root) / 'rtl/qwen_sys/split_20261014/qkd_astk_phys.sv').read_text()
    m = re.search(r'module qkd_astk_rly_296\(.*?endmodule', core, re.S)
    body = re.sub(r'`ifdef KVD_ASTK_RLY_MUT.*?`else', '', m.group(0), flags=re.S) if m else ''
    if not m or "if (!rst_n) b <= 296'd0;" not in body or 'else b <= a;' not in body:
        raise ValueError('qkd_astk_rly_296 is no longer a reset-to-zero per-bit relay')
    return out


def default_only(master, params, root=ROOT):
    """KV-BIND3 10-19: the expanded parameter ledger materialises every parameterised leaf's evaluated parameters on the
    bound instance (#(.MUT(32'sb0))).  A relay family instance stays qualified only when that list is exactly the module's
    own RTL defaults (ASTK wrapper MUT 0); any override, unknown name or unparsable literal refuses."""
    if not params:
        return True
    if master not in ASTK:
        return False
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import kv_expand_parameters as XP
    d = XP.integer_defaults((Path(root) / 'rtl/lib/face_land/qkd_astk_rly_296_fl.sv').read_text(), master)
    for k, lit in params.items():
        m = re.fullmatch(r"32'sb([01]{32})", lit) if isinstance(lit, str) else None
        if k not in d or not m:
            return False
        v = int(m[1], 2) - ((1 << 32) if m[1][0] == '1' else 0)
        if v != d[k]:
            return False
    return True


def derive(die_v, root=ROOT, existing=None, pins=None):
    srcs = pinned_sources(root, pins)
    nets, tin, tout, insts = P.parse_die(str(die_v))
    drivers, conn, uses = {}, {}, defaultdict(int)
    for m, inst, params, cm in insts:
        for pn, ex in cm.items():
            bits = P.expr_bits(ex, nets) if ex else []
            for bt in bits or []:
                if bt[0] not in ('CONST', 'Z', 'UNDECL'):
                    uses[tuple(bt)] += 1
        if m not in FAMILIES:
            continue
        w = FAMILIES[m]
        aa, bb = P.expr_bits(cm.get('a', ''), nets), P.expr_bits(cm.get('b', ''), nets)
        if not default_only(m, params, root) or aa is None or bb is None or len(aa) != w or len(bb) != w:
            raise ValueError(f'{inst}: unqualified relay width/parameters')
        conn[inst] = (m, [tuple(x) for x in aa], [tuple(x) for x in bb])
        for k, b in enumerate(bb):
            b = tuple(b)
            if b[0] in ('CONST', 'Z', 'UNDECL'):
                continue
            if b in drivers:
                raise ValueError(f'{inst}: multiply driven relay payload {b}')
            drivers[b] = (inst, w - 1 - k)
    ports = set()
    for n in list(tin) + list(tout):
        w, lo = nets[n]
        ports.update((n, i) for i in range(lo, lo + w))

    def origin(inst, pbit):
        """follow b[pbit] of inst back to its origin relay; -> (origin_inst, pbit) if literal 0 else None"""
        seen = set()
        while True:
            if (inst, pbit) in seen:
                return None
            seen.add((inst, pbit))
            m, aa, _ = conn[inst]
            a = aa[len(aa) - 1 - pbit]
            if a == ('CONST', 0):
                return inst, pbit
            if a[0] in ('CONST', 'Z', 'UNDECL') or a in ports or a not in drivers:
                return None
            inst, pbit = drivers[a]

    def zero_tail_ok(inst, pbit):
        _, aa, _ = conn[inst]
        w = len(aa)
        lsb = [aa[w - 1 - i] for i in range(w)]         # lsb[i] = a[i]
        k = next((i for i in range(w) if all(x == ('CONST', 0) for x in lsb[i:])), w)
        return pbit >= k and k > 0 and all(x[0] not in ('CONST', 'Z', 'UNDECL') for x in lsb[:k])

    def head_tail_ok(inst, pbit, oinst, opbit):
        """chain-head lane: the origin word is literal zero in EVERY bit (no predecessor feeds this delay line), so the
        lane width is visible only at the consumer: admit b[pbit] only inside the contiguous MSB tail [k, W) of THIS
        end relay's output whose bits are all unconnected elsewhere, while every bit below k is read."""
        _, oaa, _ = conn[oinst]
        if any(x != ('CONST', 0) for x in oaa):
            return False
        _, _, bb = conn[inst]
        w = len(bb)
        lsb = [bb[w - 1 - i] for i in range(w)]
        free = [x[0] not in ('CONST', 'Z', 'UNDECL') and uses[x] == 1 and x not in ports for x in lsb]
        k = next((i for i in range(w) if all(free[i:])), w)
        return pbit >= k and k > 0 and not any(free[:k])

    doc = json.loads(json.dumps(existing or dict(pads={}, instances={})))
    old = P.load_pads(doc)
    entries = doc.setdefault('instances', {})
    admitted, refused, refused_ex = defaultdict(list), defaultdict(int), defaultdict(list)
    for inst, (m, aa, bb) in conn.items():
        w = len(bb)
        key = (m, 'b', inst) if (m, 'b', inst) in old else (m, 'b')
        already = P.pad_bits(old[key], w) if key in old else set()
        for k, b in enumerate(bb):
            pbit = w - 1 - k
            if b[0] in ('CONST', 'Z', 'UNDECL') or pbit in already:
                continue
            if uses[b] != 1 or b in ports:
                continue                                  # read somewhere (or a die port): not a candidate
            o = origin(inst, pbit)
            if o is None:
                refused['dynamic_or_nonzero_origin'] += 1
                refused_ex['dynamic_or_nonzero_origin'].append([inst, pbit])
                continue
            if not zero_tail_ok(*o) and not head_tail_ok(inst, pbit, *o):
                refused['zero_not_msb_width_padding'] += 1
                refused_ex['zero_not_msb_width_padding'].append([inst, pbit, o[0], o[1]])
                continue
            admitted[inst].append(pbit)
    bits = 0
    for inst, sel in sorted(admitted.items()):
        m = conn[inst][0]
        ent = entries.get(inst)
        if ent is not None and ent.get('master') != m:
            raise ValueError(f'{inst}: existing pad entry names another master')
        ent = ent or dict(master=m, reason='', ports={})
        have = P.pad_bits(ent['ports']['b'], FAMILIES[m]) if 'b' in ent['ports'] else set()
        allb = sorted(have | set(sel))
        ranges = []
        for i in allb:
            if ranges and i == ranges[-1][1] + 1:
                ranges[-1][1] = i
            else:
                ranges.append([i, i])
        ent['ports']['b'] = ranges
        ent['reason'] = ((ent['reason'] + '; ') if ent['reason'] else '') + 'KV-FUNC-OPENS ' + RULE
        entries[inst] = ent
        bits += len(sel)
    # Landing tie outputs: qkd_landsh*/qkd_landsh0* drive tie_hi/tie_lo from (* keep *) literal 1'b1/1'b0 wires (local
    # constants offered to neighbouring pad inputs; pinned qkd_rlysh.sv). An unread tie output carries no state.
    rl = (Path(root) / 'rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv').read_text()
    ties = 0
    for m, inst, params, cm in insts:
        if not re.fullmatch(r'qkd_landsh0?_\d+', m):
            continue
        body = re.search(r'module ' + m + r' \(.*?endmodule', rl, re.S).group(0)
        if "wire tie_hi_w = 1'b1;" not in body or "wire tie_lo_w = 1'b0;" not in body \
                or 'assign tie_hi = tie_hi_w;' not in body or 'assign tie_lo = tie_lo_w;' not in body:
            raise ValueError(m + ': landing tie outputs are no longer literal constants')
        for pn in ('tie_hi', 'tie_lo'):
            tb = P.expr_bits(cm.get(pn, ''), nets) if cm.get(pn) else []
            if not tb or len(tb) != 1:
                continue
            b = tuple(tb[0])
            if b[0] in ('CONST', 'Z', 'UNDECL') or uses[b] != 1 or b in ports:
                continue
            ent = entries.setdefault(inst, dict(master=m, reason='', ports={}))
            if ent.get('master') != m:
                raise ValueError(f'{inst}: existing pad entry names another master')
            if pn in ent['ports']:
                continue
            ent['ports'][pn] = [[0, 0]]
            ent['reason'] = ((ent['reason'] + '; ') if ent['reason'] else '') + \
                'KV-FUNC-OPENS unread literal-constant landing tie output ' + pn
            ties += 1
    doc['landing_tie_contract'] = dict(die_sha256=sha(die_v),
                                       source_sha256={'rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv': srcs['rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv']},
                                       rule='unread tie_hi/tie_lo of a pinned landing master whose source drives it from a literal',
                                       admitted_bits=ties)
    doc['relay_zero_tail_contract'] = dict(
        die_sha256=sha(die_v), source_sha256=srcs, rule=RULE, admitted_bits=bits, admitted_instances=len(admitted),
        refused_unread_candidates=dict(refused), refused_unread_bits=dict(refused_ex),
        by_master={m: sum(len(v) for i, v in admitted.items() if conn[i][0] == m) for m in sorted({conn[i][0] for i in admitted})})
    return doc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('die_v', type=Path)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--existing', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    d = derive(a.die_v, a.root, json.loads(a.existing.read_text()) if a.existing else None)
    a.out.write_text(json.dumps(d, indent=1) + '\n')
    print(json.dumps(dict(relay=d['relay_zero_tail_contract'], ties=d['landing_tie_contract'])))


if __name__ == '__main__':
    main()
