#!/usr/bin/env python3
import collections,csv,gzip,json,re
from pathlib import Path
p=Path(__file__).parent
x=json.load(gzip.open(p/'source_clock_ownership.json.gz'))['contacts']
y=list(csv.DictReader(gzip.open(p/'actual_contacts.tsv.gz','rt'),delimiter='\t'))
def source(r):
 return (re.sub(r'\.D_DFF.*','',r['instance']).replace(chr(92),''),r['pin'],r['root'],r['master'])
def actual(r):
 return (re.sub(r'/Q\$_DFF.*','',r['terminal'].rsplit('/',1)[0]).replace(chr(92),''),r['pin'],r['root'],r['master'])
a=collections.Counter(map(source,x)); b=collections.Counter(map(actual,y))
assert not a-b, list((a-b).items())
assert b-a==collections.Counter({('ot_prs_00000_ff','CLK','ck_hr','DFFASRHQNx1_ASAP7_75t_R'):1}),list((b-a).items())
print('PASS matched',sum(a.values()),'additional physical pin clone',list((b-a).items()))
