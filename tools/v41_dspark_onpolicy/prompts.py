import gzip, json, sys, copy, hashlib
SNAP='/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/dba1be0a40aa45a94ad051997016db3960a90277'
sys.path.insert(0, SNAP+'/encoding')
from encoding import encode_messages
from transformers import AutoTokenizer
import os
REPO=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
WL=['reasoning_math500','reasoning_aime25','reasoning_humaneval','agentic_bfcl','agentic_tau_bench','agentic_swe_agent','agentic_mind2web','agentic_json_mode','chat_mt_bench']
def build(n_per=4, max_len=4500):
    tok=AutoTokenizer.from_pretrained(SNAP)
    rows=[json.loads(l) for l in gzip.open(REPO+'/results/speculative/raw/prompts.jsonl.gz')]
    out=[]; skipped=[]
    for w in WL:
        k=0
        for r in rows:
            if r['workload']!=w: continue
            msgs=copy.deepcopy(r['messages'])
            if r.get('tools'):
                if msgs[0]['role']!='system': msgs=[{'role':'system','content':''}]+msgs
                msgs[0]['tools']=r['tools']
            mode='thinking' if r['enable_thinking'] else 'chat'
            try:
                text=encode_messages(msgs, thinking_mode=mode)
            except Exception as e:
                skipped.append((r['prompt_id'],'encode_error:'+repr(e)[:80])); continue
            ids=tok.encode(text, add_special_tokens=False)
            if len(ids)>max_len: skipped.append((r['prompt_id'],f'len {len(ids)}')); continue
            out.append(dict(workload=w, prompt_id=r['prompt_id'], prompt_sha256=r['prompt_sha256'], thinking_mode=mode, n_prompt=len(ids), ids=ids, text_sha256=hashlib.sha256(text.encode()).hexdigest()))
            k+=1
            if k==n_per: break
    return out, skipped, tok
if __name__=='__main__':
    n_per=int(sys.argv[1]) if len(sys.argv)>1 else 4
    out,sk,tok=build(n_per)
    for o in out: print(o['workload'],o['prompt_id'],o['thinking_mode'],o['n_prompt'])
    print('skipped',sk); print('total prompt tokens',sum(o['n_prompt'] for o in out))
    print(repr(tok.decode(out[0]['ids'][:80]))); print(repr(tok.decode(out[12]['ids'][-300:])))
    json.dump(dict(items=out,skipped=sk),open('prompts_sel.json','w'))
