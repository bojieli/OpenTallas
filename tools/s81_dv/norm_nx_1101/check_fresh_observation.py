#!/usr/bin/env python3
"""Strict fresh-gold observation of unchanged binary with obsolete SV literal.

The native exit1/bad16 stays a recorded harness failure, never nativePASS. Every
DUT payload, delivery, root, output value and fault remains independently checked.
"""
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_network import check


def observe(book,transport,partials,log,gold):
    result=check(book,transport,partials,log,expected_rstd=gold,require_native_pass=False)
    matches=re.findall(r'NX_NET_RSTD sid(\d+) cycle(\d+) word([0-9a-f]+)',log)
    summary=re.search(r'NX_NET_RESULT count(\d+) seen([0-9a-f]+) bad(\d+) xf_fault([0-9a-f]+) r_fault([0-9a-f]+) mut(\d+)',log)
    if len(matches)!=16 or len({int(s)for s,c,d in matches})!=16:result['errors'].append(dict(kind='RSTD_COUNT_OR_DUPLICATE'))
    if not summary or [int(summary[1]),summary[2],int(summary[3]),summary[4],summary[5]]!=[16,'ffff',16,'0000','0000']:
        result['errors'].append(dict(kind='NATIVE_SUMMARY_NOT_EXACT_KNOWN_STALE_LITERAL'))
    if 'NX_NET_PASS'in log or 'NX_NET_FAIL'not in log:result['errors'].append(dict(kind='NATIVE_HARNESS_OBSERVATION_CLASS_DIFFERS'))
    result.update(status='PASS_UNCHANGED_NATIVE_OBSERVATION_FRESH_EXTERNAL_GOLD'if not result['errors']else'FAIL_UNCHANGED_NATIVE_OBSERVATION_FRESH_EXTERNAL_GOLD',
        native_harness_pass=False,native_harness_expected_exit=1,native_harness_failure='obsolete hardcoded40ca3c85; bad16 preserved',
        independent_fresh_expected_RSTD=gold,byte_identical_hardware_observation_required=True,
        actual_source_images_or_arrival_residency=False,full_token=False)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('book','transport','partials','log','gold','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('fresh output required')
    gold=json.loads(a.gold.read_text());r=observe(json.loads(a.book.read_text()),json.loads(a.transport.read_text()),[int(s,16)for s in a.partials.read_text().split()],a.log.read_text(),gold['RSTD']);a.out.write_text(json.dumps(r,indent=1)+'\n');print(r['status'],r['errors']);raise SystemExit(0 if not r['errors']else 1)
