#!/usr/bin/env python3
"""Start genuine table lowering independently as each recovered rank completes.

Thin coordinator: no memory reservation while waiting for raw source. Every
actual lowering runs through ot-run on the bank's host. Failures are retained
and stop that rank instead of being retried against guessed inputs.
"""
import argparse,concurrent.futures,json,subprocess,time
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--remote-root',required=True)
    ap.add_argument('--source-commit',required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--rank-hosts',default='epyc8,epyc8,epyc8,epyc8,epyc7,epyc7,epyc7,epyc7')
    a=ap.parse_args();hosts=a.rank_hosts.split(',')
    if len(hosts)!=8:ap.error('eight exact rank hosts required')
    a.out.mkdir(parents=True,exist_ok=True);status={}
    def save():
        ready=sorted(k for k,v in status.items()if v.get('status')=='COMPLETE_GENUINE_SOURCE_TABLES_CANDIDATE_ONLY')
        x=dict(schema='opentallas.qwen.recovered-eight-rank-source-inventory.v1',
               status='COMPLETE_8_RANKS_36_PLUS_HEAD'if len(ready)==8 else'PARTIAL_RANKS_COMPLETE',
               complete_ranks=ready,missing_ranks=sorted(set(range(8))-set(ready)),ranks=status,
               completion_authority='actual37-stage inventory per rank, not partial chunk receipt labels',
               expected_actual_stage_inventories=8*37,final_bound_adoption=False)
        tmp=a.out/'aggregate.tmp';tmp.write_text(json.dumps(x,indent=2)+'\n');tmp.replace(a.out/'aggregate.json')
    def run(rank):
        host=hosts[rank];base=a.remote_root+'/table_lower_tools'
        check=['ssh','-n','-o','ControlPath=none',host,'cd '+base+' && python3 tools/qwen_code_rom/lower_recovered_rank.py --inventory-only --banks ../banks_native --rank '+str(rank)]
        while True:
            p=subprocess.run(check,text=True,capture_output=True)
            if p.returncode==0:break
            if p.returncode!=2:
                return rank,dict(status='INVENTORY_FAILED',host=host,stderr=p.stderr,stdout=p.stdout)
            time.sleep(30)
        command=['ot-run','--hosts',host,'--mem','4','--threads','1','--dir',base,'--',
                 '../venv/bin/python','tools/qwen_code_rom/lower_recovered_rank.py',
                 '--banks','../banks_native','--rank',str(rank),'--snapshot','../checkpoint/b968826d9c46dd6066d109eabc6255188de91218',
                 '--attention-contract','results/rtl/qc_rope_boundary_1116/attention_owner_candidate.json',
                 '--selected-identity','results/token_pass/qwen_head_local4_1116/selected_source_identity.json',
                 '--lowering-commit',a.source_commit,'--out','../tables_candidate1116/rank'+str(rank)]
        with (a.out/f'rank{rank}.log').open('w')as log:
            p=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
        if p.returncode:return rank,dict(status='LOWERING_FAILED',host=host,exit=p.returncode,log=str(a.out/f'rank{rank}.log'))
        receipt=a.remote_root+'/tables_candidate1116/rank'+str(rank)+'/receipt.json'
        p=subprocess.run(['ssh','-n','-o','ControlPath=none',host,'cat '+receipt],text=True,capture_output=True)
        if p.returncode:return rank,dict(status='COLLECTION_FAILED',host=host,stderr=p.stderr)
        r=json.loads(p.stdout)
        if r['rank']!=rank or r['actual_stages']!=37 or len(r['images'])!=48:raise ValueError('completed actual rank inventory differs')
        (a.out/f'rank{rank}_receipt.json').write_text(json.dumps(r,indent=2)+'\n')
        return rank,dict(status=r['status'],host=host,receipt=receipt,actual_stages=37,masks=48,manifest_sha256=r['manifest_sha256'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=8)as pool:
        for f in concurrent.futures.as_completed([pool.submit(run,r)for r in range(8)]):
            rank,result=f.result();status[rank]=result;save();print('RANK_TABLE_STATUS',rank,result['status'],flush=True)
    save()
if __name__=='__main__':main()
