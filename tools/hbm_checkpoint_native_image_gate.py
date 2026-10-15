#!/usr/bin/env python3
"""Software installation-input gate; actual command ACK is independently required."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,'tools')
from hbm_checkpoint_native_readback import check
p=argparse.ArgumentParser();p.add_argument('--directory',required=True);a=p.parse_args();base=Path(a.directory);names=['wkv_l1_rank0_sm0_fullsource','wkv_l14_rank0_sm0','fp4_l0_expert383_sm0','woa_rank0_sm8','markov_rank95_sm31'];proof=[]
for n in names:
 d=base/n;positive=check(d);lines=(d/'physical.hex').read_text().splitlines(True)
 bad=base/(n+'.wrongaddr.hex');bad.write_text('@00000000\n'+''.join(lines[1:]))
 try:check(d,bad)
 except ValueError:wrong=True
 else:raise AssertionError('wrong-address mutant survived')
 drop=base/(n+'.drop.hex');drop.write_text(''.join(lines[:-2]))
 try:check(d,drop)
 except ValueError:dropped=True
 else:raise AssertionError('drop mutant survived')
 proof.append(dict(image=n,positive=positive,wrong_address_rejected=wrong,dropped_sector_rejected=dropped))
(base/'source_image_verification.json').write_text(json.dumps(dict(scope='software source image inverse-address/payload only; no command ACK claim',images=proof),indent=2)+'\n')
print(json.dumps(dict(images=len(proof),sectors=sum(x['positive']['sectors'] for x in proof),both_mutants_rejected_all=True)))
