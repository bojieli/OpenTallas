#!/usr/bin/env python3
"""Portable real-provider station gate. Invoke inside an already admitted job."""
import argparse,hashlib,pathlib,subprocess,sys,tarfile,json
p=argparse.ArgumentParser();p.add_argument('mode',choices=['exact','owner']);p.add_argument('--out',required=True);a=p.parse_args()
root=pathlib.Path(__file__).resolve().parents[5]
archive=root/'results/arch/hbm_native_contention_1014/r12_station_proof.tar.gz'
manifest=json.loads(archive.with_suffix('.json').read_text())
if hashlib.sha256(archive.read_bytes()).hexdigest()!=manifest['sha256']:raise SystemExit('portable station package hash mismatch')
out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
with tarfile.open(archive) as t:t.extractall(out,filter='data')
job=out/('r12p61' if a.mode=='exact' else 'r12m10')
rc=subprocess.call([sys.executable,str(job/'run_frozen.py'),'--smoke'])
log=(job/'run.log').read_text() if (job/'run.log').exists() else ''
if a.mode=='owner':
 if rc==0 or 'FATAL actual SU timeout mode0 seen0/f donef/0 count0/0/0/0' not in log or 'PARKED_POSTS observed224' not in log:raise SystemExit('station owner mutant failed to reach required actual posted-stage observation')
 print('STATION_OWNER_MUTANT_OBSERVED actual_SU_prefill_timeout parked224 sourcehashes_verified')
 sys.exit(rc)
required=['THREEOWNER_DMA_CORE PASS source39f276214 STORE4 FENCE4 native_requests128 words1024',
 'THREEPRODUCER_QUANT_EXACT PASS records32 words13312 cycles192 immutable_price168',
 'all4_three_owner_maskfff handoffs16',
 'THREEPRODUCER_POST_RETENTION PASS write32802 commit32802 read32808 reply32808 parked352',
 'THREEPRODUCER_GLOBAL_MIRROR PASS actual_source_posts2 global_commits2 destination_sectors8 words64',
 'THREEPRODUCER_SMOKE PASS actualSU actualQDQ32 actualDMA_dispatch3 actualq10_STORE4_FENCE4 quantwords13312 phase61 production147_not_run']
if rc or any(x not in log for x in required):raise SystemExit('actual station exact gate failed or required minimum counts absent')
if log.count('THREEPRODUCER_MIRROR_MACRO ')!=8:raise SystemExit('actual station gate requires all eight mirrored macro writes')
print('STATION_EXACT_GATE PASS actual_all4_threeowners native128 golden1024 quant13312 mirror64 parked352 all_sourcehashes_verified')
