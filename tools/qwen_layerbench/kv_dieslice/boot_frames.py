#!/usr/bin/env python3
"""TOKj-KV 10-23: boot bundle (kv_boot_v36 / program_target_frames encode_boot_bundle) -> tb_kvslice inputs:
frames.hex (one 528-b class-8 frame per line, bundle order) + expect.txt ("target digest" per image) + epoch."""
import gzip, json, sys
b = json.load(gzip.open(sys.argv[1]) if sys.argv[1].endswith('.gz') else open(sys.argv[1])); o = sys.argv[2]
open(f'{o}/frames.hex', 'w').write('\n'.join(b['frames528']) + '\n')
open(f'{o}/expect.txt', 'w').write(''.join(f"{im['target']} {im['digest']}\n" for im in b['images']))
open(f'{o}/epoch.txt', 'w').write(f"{b['epoch']}\n")
print(f"frames {len(b['frames528'])} images {[ (im['target'], im['program_words']) for im in b['images']]} epoch {b['epoch']} layer_form {b.get('layer_form')}")
