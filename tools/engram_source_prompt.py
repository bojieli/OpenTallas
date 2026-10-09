#!/usr/bin/env python3
"""Emit actual typed SOURCE host commands from released prepared token records.

Input {revision,tokenizer_sha256,tokens:[[raw IDs]],token_types:[[TEXT=-1/image0..3]]}.
Missing token_types means released text-only forward(None); no inference from rawID.
"""
import argparse,hashlib,json
from pathlib import Path
REV='dba1be0a40aa45a94ad051997016db3960a90277'
TOK_SHA='c90dfa01249db1be4245780a052ede752e1361c612ac6d08e2bdada7d599476b'
def field(n,bits):
    if type(n)!=int or not 0<=n<1<<bits:raise ValueError('SOURCE field bounds')
    return n
def word(op,tag,user,pos,token,token_type):
    return field(op,2)|(field(tag,8)<<2)|(field(user,8)<<10)|(field(pos,21)<<18)|(field(token,21)<<39)|(field(token_type,3)<<60)
def commands(record,gen_len=1,tag=1,max_len=1048576,prompt_limit=8):
    if record.get('revision')!=REV or record.get('tokenizer_sha256')!=TOK_SHA:raise ValueError('released prepared token identity')
    rows=record['tokens']
    if not 1<=len(rows)<=64 or not rows[0] or any(len(r)!=len(rows[0]) for r in rows):raise ValueError('SOURCE users/prompt shape')
    size=len(rows[0])
    if size>prompt_limit or type(gen_len)!=int or gen_len<1 or size+gen_len-1>max_len:raise ValueError('SOURCE installed prompt/run bounds')
    types=record.get('token_types')
    if types is None:types=[[-1]*size for _ in rows]
    if len(types)!=len(rows) or any(len(t)!=size for t in types):raise ValueError('released token type shape')
    out=[word(3,tag,0,max_len,2,7)]
    for user,(row,trow) in enumerate(zip(rows,types)):
        for pos,(token,typ) in enumerate(zip(row,trow)):
            if type(token)!=int or not 0<=token<129280:raise ValueError('released rawtoken bounds')
            if type(typ)!=int or typ not in (-1,0,1,2,3) or (typ!=-1 and token!=129264):raise ValueError('released image token type/raw pair')
            out.append(word(1,tag,user,pos,token,7 if typ==-1 else typ))
    out.append(word(2,tag,len(rows),size,gen_len,7))
    return out
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--gen-len',type=int,default=1);p.add_argument('--tag',type=int,default=1);p.add_argument('--max-len',type=int,default=1048576);p.add_argument('--prompt-limit',type=int,default=8);a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    payload=a.input.read_bytes();values=commands(json.loads(payload),a.gen_len,a.tag,a.max_len,a.prompt_limit)
    a.output.write_text(''.join(f'{w:016x}\n' for w in values))
    print(json.dumps(dict(schema='opentallas.engram-source-commands.v1',input_sha256=hashlib.sha256(payload).hexdigest(),output_sha256=hashlib.sha256(a.output.read_bytes()).hexdigest(),commands=len(values),source='released preparedtoken types, native64-bit SOURCE host port; bootstrap RAW independent')))
if __name__=='__main__':main()
