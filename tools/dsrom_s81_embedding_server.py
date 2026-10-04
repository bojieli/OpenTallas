#!/usr/bin/env python3
"""Read-only checkpoint service for native embedding DUT addresses.

Request: <Q4I identity, token, prompt position, physical macro, row.
Response: <IQII8I status, echoed identity/macro/row, 256 raw payload bits.
Missing or invalid source closes the connection with a nonzero status.
"""
import argparse, json, socketserver, struct
from pathlib import Path
from dsrom_checkpoint import Checkpoint, DEFAULT_CHECKPOINT
from dsrom_s81_cold_input import CANONICAL, PROMPT, EmbeddingROM

def serve(path,checkpoint,prompt):
    ids=json.loads(prompt.read_text())['token_ids']
    inventory=json.loads((CANONICAL/'inventory.json').read_text())
    # Validate source at startup, before exposing a usable endpoint.
    c=Checkpoint(checkpoint)
    try: EmbeddingROM(c,inventory)
    finally:c.close()
    class Handler(socketserver.BaseRequestHandler):
        def handle(self):
            source=Checkpoint(checkpoint)
            rom=EmbeddingROM(source,inventory)
            try:
                while True:
                    data=b''
                    while len(data)<24:
                        chunk=self.request.recv(24-len(data))
                        if not chunk:
                            if data:raise EOFError('truncated DUT request')
                            return
                        data+=chunk
                    identity,token,position,macro,row=struct.unpack('<Q4I',data)
                    if identity>=1<<47 or position>=len(ids) or ids[position]!=token:
                        raise ValueError('actual prompt/context binding')
                    pair,leaf=divmod(macro,4)
                    word=pair*16384+(leaf//2)*8192+row*2+leaf%2
                    if word//320!=token:raise ValueError('DUT request outside selected token row')
                    payload=rom.read(macro,row)
                    self.request.sendall(struct.pack('<IQII',0,identity,macro,row)+payload)
            except (ValueError,KeyError,EOFError,OSError):
                self.request.sendall(struct.pack('<IQII8I',1,0,0,0,*([0]*8)))
                raise
            finally:source.close()
    class Server(socketserver.ThreadingUnixStreamServer):
        daemon_threads=False
        block_on_close=True
    # Never unlink an existing service/socket, including another live owner.
    with Server(str(path),Handler) as server:
        print(json.dumps(dict(ready=True,socket=str(path),checkpoint=str(checkpoint),
            prompt=str(prompt),scope='DUT-addressed raw embedding only')),flush=True)
        server.serve_forever()

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--socket',type=Path,required=True)
    ap.add_argument('--checkpoint',type=Path,default=DEFAULT_CHECKPOINT)
    ap.add_argument('--prompt',type=Path,default=PROMPT)
    a=ap.parse_args();serve(a.socket,a.checkpoint,a.prompt)
