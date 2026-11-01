#!/usr/bin/env python3
"""Small actual-OBS mechanism miter; no production latency or geometry adoption."""
import argparse, hashlib, json, pathlib, subprocess

ap=argparse.ArgumentParser()
ap.add_argument('--source-root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[3])
ap.add_argument('--out',type=pathlib.Path,required=True)
a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
here=pathlib.Path(__file__).resolve().parent
bundle=a.source_root/'physical/die_plan/hbm/bind/r18h5_bundle/rtl'
gold=bundle/'hbm_accel/die_glue/ot_hbm_obs_leaf.sv'
actual_hash=hashlib.sha256(gold.read_bytes()).hexdigest()
assert actual_hash=='eae855ff0a0db74331481be65995ca86dfc4af60face01a151796a58a2abee1f'
sources=[bundle/'lib/ot_rst_relay.sv',gold,here/'obs_delay_candidate.sv',here/'tb_obs_delay.sv']
results=[]
for depth,mut in [(0,0),(20,0),(24,0)]+[(d,m) for d in [20,24] for m in [1,2,3,4]]:
 tag=f'd{depth}_m{mut}';exe=a.out/(tag+'.vvp')
 cmd=['iverilog','-g2012','-s','tb_obs_delay',f'-Ptb_obs_delay.D={depth}',f'-Ptb_obs_delay.MUT={mut}','-o',str(exe),*map(str,sources)]
 build=subprocess.run(cmd,text=True,capture_output=True)
 (a.out/(tag+'.compile.log')).write_text(build.stdout+build.stderr)
 if build.returncode:raise RuntimeError(f'{tag}: compile failed')
 run=subprocess.run(['vvp',str(exe)],text=True,capture_output=True)
 (a.out/(tag+'.log')).write_text(run.stdout+run.stderr)
 passed=run.returncode==0 and 'PASS OBS_DELAY' in run.stdout
 caught=run.returncode!=0 and ('FATAL:' in run.stdout or 'FATAL:' in run.stderr)
 qualified=passed if mut==0 else caught
 row=dict(depth=depth,mutant=mut,returncode=run.returncode,qualified=qualified,
          verdict='PASS' if mut==0 and passed else 'CAUGHT' if mut and caught else 'FAIL',
          output=(run.stdout+run.stderr).strip())
 results.append(row);print(tag,row['verdict'],flush=True)
doc=dict(schema='opentallas.hbm.obs_delay_mechanism.v1',release=False,production_latency_selected=False,
         source_sha256=actual_hash,actual_leaf=dict(N=209,LID=4,SYNC_MASK='0x3ffff0000000000000000000000000000'),
         cases=results,verdict='PASS_MECHANISM_ONLY' if all(x['qualified'] for x in results) else 'FAIL',
         contract='250 payload bits delayed coherently D edges; immediate reset assertion and D-edge local release. r_v compared after reset-epoch history is valid; r_idx/r_d compared only when r_v. No invalid-payload or reset-transition time-shift claim.',
         resets='Cold five-edge window; mid-run833ps/416ps/80ps pulses. No64-edge LOW assumption.',
         model='D0 bypass; D20/D24 are mechanism cases, not production N. Payload250D FF + D release bits outside unchanged leaf. Host observation/readback and observer boot +D edges; compute +0.',
         physical='No placement, route, timing, current core reset realization, or new latency acceptance. Parent owner question and actual peer geometry remain gates.')
(a.out/'result.json').write_text(json.dumps(doc,indent=2))
raise SystemExit(0 if doc['verdict']=='PASS_MECHANISM_ONLY' else 1)
