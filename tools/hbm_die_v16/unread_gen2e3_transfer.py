#!/usr/bin/env python3
"""L2H-GEN2E 10-19: transfer the GEN2e2 unread review candidate (65,066 b; exact transfer of ROOT manifest 2beccb8e) onto
the GEN2e3 die (GEN2e2 + l20c/l20p/l20t/l20s).  Fail-closed exact transfer, never a broadening:

- every one of the 309 entries keeps instance / port / net / width / ranges / classification / reason;
- only entries on re-mastered instances are re-pointed: col_idx (rec, idx256 -> idx256r: rec driver unchanged by l20p) and
  epcal_<q>/vmfc_<q> (ordinal, calendar_f20 -> calendar_f20_role: ordinal is passed through from the same calendar core);
  the new master must declare the same output port and width (checked against the RTL text);
- exact per-bit admission is enforced by die_port_bind's manifest validation (proposal + replay), not here;
- the four fixed held classes are removed; die_line is recomputed from the new die.v.

    unread_gen2e3_transfer.py REVIEW_IN DIE_V CONTRACT PORT_BIND_JSON SOURCE_COMMIT OUT
"""
import hashlib, json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
REPOINT = {
    'ot_hbm_static_cfg_collar_idx256': ('ot_hbm_static_cfg_collar_idx256r',
                                        'rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar_idx256r.sv'),
    'hfd_hgi_vm_calendar_f20': ('hfd_hgi_vm_calendar_f20_role',
                                'rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_f20_role.sv'),
}
FIXED = {'reserved_operand_abi_review', 'selector_optional_readback', 'terminal_chain_control',
         'universal_calendar_capacity_tail_review'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def port_width(src, port):
    t = re.sub(r'//[^\n]*', '', (ROOT / src).read_text())
    m = re.search(r'output\s+(?:wire|reg)?\s*(?:\[(\d+):0\])?\s*' + re.escape(port) + r'\b', t)
    if not m:
        raise SystemExit(f'REFUSED: {src} has no output {port}')
    return int(m.group(1)) + 1 if m.group(1) else 1


def main():
    rin, die, contract, pbj, commit, out = sys.argv[1:7]
    r = json.loads(Path(rin).read_text())
    c = json.loads(Path(contract).read_text())
    pb = json.loads(Path(pbj).read_text())
    lines = Path(die).read_text().splitlines()
    inst_line = {}
    for i, l in enumerate(lines):
        m = re.match(r'\s*(\w+)\s*(?:#\(.*\))?\s+(\w+)\s*\($', l)
        if m:
            inst_line[m.group(2)] = i
    moved = []
    for e in r['approved_entries']:
        ci = c['instances'].get(e['instance'])
        if ci is None:
            raise SystemExit(f'REFUSED: reviewed instance {e["instance"]} absent')
        if ci['master'] != e['master']:
            new = REPOINT.get(e['master'])
            if not new or ci['master'] != new[0] or ci['source'] != new[1]:
                raise SystemExit(f'REFUSED: {e["instance"]} master {ci["master"]} not an allowed re-point of {e["master"]}')
            if port_width(new[1], e['port']) != e['width']:
                raise SystemExit(f'REFUSED: {new[0]}.{e["port"]} width differs')
            moved.append([e['instance'], e['port'], e['master'], new[0]])
            e['master'], e['source'] = new
            e['reason'] = e['reason'] + f' | L2H-GEN2E re-point to {new[0]} (port and driver unchanged)'
        if e['source'] != ci['source']:
            raise SystemExit(f'REFUSED: {e["instance"]} source differs {e["source"]} vs {ci["source"]}')
        i0 = inst_line.get(e['instance'])
        if i0 is None:
            raise SystemExit(f'REFUSED: instance {e["instance"]} not found in die.v')
        for j in range(i0 + 1, min(i0 + 4000, len(lines))):
            if re.match(r'\s*\.' + re.escape(e['port']) + r'\(', lines[j]):
                e['die_line'] = j + 1
                break
            if lines[j].strip() == ');':
                raise SystemExit(f'REFUSED: {e["instance"]}.{e["port"]} not connected in die.v')
    r['inputs'] = {'die_v': {'path': str(die), 'sha256': sha(die)}, 'contract': {'path': str(contract), 'sha256': sha(contract)},
                   'bind_report': {'path': str(pbj), 'sha256': sha(pbj)}}
    r['source_commit'] = commit
    r['reviewer'] = ('L2H-GEN2E (LEAD2-HBM sub-lane, Claude): exact transfer of the GEN2e2 candidate onto the GEN2e3 die '
                     '(l20c/l20p/l20t/l20s); CANDIDATE pending digest admission')
    r['held_classes'] = [h for h in r['held_classes'] if h not in FIXED]
    total = pb['summary']['unread_net_bits']
    r['remaining_unadmitted_bits'] = total - r['approved_bits']
    r['conditions'] = [x for x in r['conditions'] if 'unresolved plus' not in x] + [
        f'{r["remaining_unadmitted_bits"]} unresolved remain strict FAIL; the four held classes are fixed as hardware (l20c/p/t/s)']
    r['delta_review_gen2e3'] = {'repointed_entries': moved, 'fixed_held_classes': sorted(FIXED),
                                'die_unread_bits': total, 'predecessor_review_sha256': sha(rin)}
    Path(out).write_text(json.dumps(r, indent=1) + '\n')
    print('UNREAD_GEN2E3_TRANSFER entries', len(r['approved_entries']), 'repointed', len(moved), 'approved_bits', r['approved_bits'],
          'die_unread', total, 'remaining', r['remaining_unadmitted_bits'], 'sha', sha(out))


if __name__ == '__main__':
    main()
