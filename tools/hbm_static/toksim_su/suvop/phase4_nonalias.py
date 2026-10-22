#!/usr/bin/env python3
"""Enumerate encoded VM pin requests and expected pin writes; certify static-image scope."""
import argparse
import bisect
import hashlib
import json
from pathlib import Path

QW = 2422


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('programme', type=Path)
    a = ap.parse_args()
    d = a.programme
    m = json.loads((d / 'programme.json').read_text())
    reads, writes, byword = [], [], {}
    for raw in (d / 'expw.mem').read_text().splitlines():
        edge, q, port, sec, mask = int(raw[:8], 16), int(raw[8], 16), int(raw[9], 16), int(raw[10:14], 16), int(raw[14:16], 16)
        words = [((sec >> 4 & 511) * 512 + q * 128 + (sec & 15) * 8 + k) for k in range(8) if mask >> k & 1]
        row = dict(edge=edge, q=q, port=port, source_sector=sec, mask=mask, words=words)
        writes.append(row)
        for word in words:
            byword.setdefault(word, []).append(edge)
    for events in byword.values():
        events.sort()
    conflicts = []
    rr = m['phases'][0]['RR']
    for edge, raw in enumerate((d / 'prog.mem').read_text().splitlines()):
        value = int(raw, 16)
        for q in range(4):
            vmr = value >> (q * QW + 440) & ((1 << 240) - 1)
            for port in range(8):
                request = vmr >> (port * 30) & ((1 << 30) - 1)
                if not request >> 29:
                    continue
                sec = request >> 13 & 0xffff
                words = [((sec >> 4 & 511) * 512 + q * 128 + (sec & 15) * 8 + k) for k in range(8)]
                # Include command launch, registered request, RR return and the compiler's input capture allowance.
                last = edge + rr + 4
                row = dict(command_edge=edge, latest_return_capture_edge=last, q=q, port=port,
                           source_sector=sec, local_destination_row=request & 511, words=words)
                reads.append(row)
                for word in words:
                    if bisect.bisect_right(byword.get(word, []), last):
                        conflicts.append(dict(read=row, word=word, prior_write_edges=[x for x in byword[word] if x <= last]))
    hashes = {name: hashlib.sha256((d / name).read_bytes()).hexdigest()
              for name in ['prog.mem', 'expw.mem', 'exps.mem', 'tree.mem', 'arith/seed.mem', 'programme.json']}
    result = dict(schema='toksim.hbm.scheduled_vm_pin_nonalias.v1', certificate_pass=not conflicts,
                  runtime_pin_trace_observed=False,
                  scope='Decoded input VM request commands and expected actual-pin writes. Conservative read-return interval. Conditional on runtime programme exactness and the declared RR/capture contract; not an independently observed DUT request trace.',
                  request_records=len(reads), write_records=len(writes), conflicts=conflicts,
                  rr=rr, return_capture_allowance=4, hashes=hashes,
                  reads=reads, writes=writes)
    (d / 'nonalias_certificate.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ['reads', 'writes', 'conflicts']}))
    if conflicts:
        raise SystemExit(f'NONALIAS_FAIL {len(conflicts)}')


if __name__ == '__main__':
    main()
