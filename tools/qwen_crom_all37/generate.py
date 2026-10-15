#!/usr/bin/env python3
"""Expected-only reads from source-pinned checkpoint CROM images; never DUT writes."""
import argparse,pathlib,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
m=json.loads(a.manifest.read_text());pins=m['inputs_sha256'];head_key=next(k for k in pins if k.endswith('/head_final_norm_crom.hex'))
positions=[0,8191,1];actual_pins={};rank_equal={};cycle=0;n=0;contexts=[]
f={name:(a.out/name).open('w')for name in ['rd_hdr.hex','rd_mask.hex','rd_addr.hex','rd_exp.hex','contexts.hex']}
for cohort,pos in enumerate(positions):
 for stage in range(37):
  if stage<36:
   path=pathlib.Path(f'/srv/opentallas-scratch/codex/qwen-native-fulltoken-1014/banks/images/layer{stage}/die0/crom.hex')
   rp=[pins[str(path).replace('/die0/','/die'+str(rank)+'/')]for rank in range(8)];assert len(set(rp))==1;rank_equal[stage]=rp[0];wanted=rp[0]
  else:
   path=pathlib.Path('/srv/opentallas-scratch/claude/qwen-wholetoken-1014/plans/head/image/die0/crom.hex');wanted=pins[head_key]
  raw=path.read_bytes();observed=hashlib.sha256(raw).hexdigest();assert observed==wanted,(path,observed,wanted);actual_pins[str(path)]=observed;words=raw.splitlines()
  bases=([4096+64*j for j in range(10)]+[533121+64*j for j in range(64)]+[537217+64*j for j in range(64)]+[8832,0,8833+64*pos])if stage<36 else [64*j for j in range(64)]
  contexts.append(dict(cycle=cycle,stage=stage,tpos=pos,tok_start=int(stage==0),cohort=cohort,first_read=cycle+400,reads=len(bases)))
  f['contexts.hex'].write(f'{(cycle<<32)|(pos<<7)|((stage==0)<<6)|stage:016x}\n')
  for j,base in enumerate(bases):
   rc=cycle+400+j;f['rd_hdr.hex'].write(f'{(rc<<8)|stage:016x}\n');f['rd_mask.hex'].write('ffffffffffffffff\n')
   for lane in range(64):
    address=base if stage<36 and base==8832 else base+lane;assert address<len(words),(stage,address,len(words));value=int(words[address],16);assert value<1<<64
    f['rd_addr.hex'].write(f'{address:06x}\n');f['rd_exp.hex'].write(f'{value:016x}\n')
   n+=1
  cycle+=400+len(bases)+8
for h in f.values():h.close()
report=dict(schema='opentallas.qwen-crom-all37-expected-only.v1',positions=positions,contexts=contexts,reads=n,lane_comparisons=n*64,clock_roots=24,read_latency=5,fill_window=400,cycles=cycle,reset_policy='One reset before first cohort; none between111contexts',actual_image_sha256=actual_pins,eight_rank_decoder_images_equal_sha256=rank_equal,head_manifest_source=head_key,manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),vector_sha256={name:hashlib.sha256((a.out/name).read_bytes()).hexdigest()for name in f},claim='Standalone R3+CROM+return3 component. Expected values are observers; no generated value writes DUT storage.')
(a.out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(reads=n,lane_comparisons=n*64,contexts=len(contexts),cycles=cycle)))
