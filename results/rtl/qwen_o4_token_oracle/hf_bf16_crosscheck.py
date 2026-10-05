import torch, json
from transformers import AutoModelForCausalLM, AutoTokenizer
p='/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/b968826d9c46dd6066d109eabc6255188de91218'
tok=AutoTokenizer.from_pretrained(p)
m=AutoModelForCausalLM.from_pretrained(p,torch_dtype=torch.bfloat16)
with torch.no_grad():
    lg=m(torch.tensor([[0]])).logits[0,-1].float()
v,i=lg.topk(5)
print(json.dumps({'top5':i.tolist(),'vals':v.tolist(),'tok0':tok.decode([0]),'decoded':[tok.decode([x]) for x in i.tolist()], 'oracle_token_text':tok.decode([50994])}))
