#!/usr/bin/env python3
"""Admitted full-snapshot versus bounded raw-window semantic image binding gate."""
import argparse,hashlib,json
from pathlib import Path
from dsrom_markov_head_bundle_image import build

def run(snapshot,manifest,windows,out):
 out.mkdir(parents=True,exist_ok=False);results=[]
 for die,bundle in [(0,83),(0,84),(2,84)]:
  full=out/f'full_d{die}_b{bundle}';bounded=out/f'window_d{die}_b{bundle}'
  a=build(snapshot,manifest,full,die,bundle);b=build(snapshot,manifest,bounded,die,bundle,windows=windows)
  matches={p.name:hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256((bounded/p.name).read_bytes()).hexdigest() for p in full.glob('*.viamap.hex')}
  passed=len(matches)==18 and all(matches.values()) and a['released_payload_sha256']==b['released_payload_sha256']
  results.append(dict(die=die,bundle=bundle,valid_rows=a['B_VALID_ROWS'],passed=passed,all_18_images_equal=matches,released_head_payload_sha256=a['released_payload_sha256']))
 rec=dict(passed=all(x['passed'] for x in results),scope='native A/B K spans and skew plus local Markov row permutation; full released snapshot equals independently bounded source windows; interior128 and shard tails21/22',results=results,manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('dsrom_markov_head_bundle_image.py'),Path(__file__).with_name('dsrom_markov_head_weight_image.py')]})
 (out/'verdict.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec));return rec['passed']
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--snapshot',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--windows',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();raise SystemExit(0 if run(a.snapshot,a.manifest,a.windows,a.out) else 1)
