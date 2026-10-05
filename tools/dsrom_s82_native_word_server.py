#!/usr/bin/env python3
"""Serve the canonical DieROM.read API to the source-selected runtime.

Only requested native words read checkpoint bytes. No second image, numerical
replacement, missing-owner zero, allocator run, or simulated latency credit.
"""
import argparse
import gzip
import importlib
import importlib.machinery
import json
import socket
import struct
import sys
from pathlib import Path
from dsrom_c8_parent_binding import ParentBinding


class SourceOnlyLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        return self.source_to_code(self.get_data(self.path),self.path)


class OwnerSourceFinder:
    def __init__(self,owner):self.owner=owner
    def find_spec(self,fullname,path=None,target=None):
        spec=importlib.machinery.PathFinder.find_spec(fullname,path,target)
        if spec and spec.origin and spec.origin.endswith('.py') and Path(spec.origin).resolve().is_relative_to(self.owner):
            spec.loader=SourceOnlyLoader(fullname,spec.origin)
            return spec
        return None


def receive(sock, count):
    data=b''
    while len(data)<count:
        block=sock.recv(count-len(data))
        if not block:
            if not data:return None
            raise EOFError('partial native ROM request')
        data+=block
    return data


def serve_connection(sock, read_word):
    while (request:=receive(sock,16)) is not None:
        stage,rank,macro,row=struct.unpack('<4I',request)
        try:
            word=read_word(stage,rank,macro,row)
            if type(word) is not int or not 0<=word<1<<274:
                raise ValueError('native word exceeds 274 bits')
        except Exception as e:
            # Status is checked before bytes are consumed; zeros in a rejected
            # reply are never a usable word. Preserve the actual provider error.
            print(json.dumps(dict(status='REJECTED_NATIVE_WORD',stage=stage,rank=rank,macro=macro,row=row,error=str(e))),flush=True)
            sock.sendall(struct.pack('<I',1)+bytes(36))
            return False
        sock.sendall(struct.pack('<I',0)+word.to_bytes(36,'little'))
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--owner',type=Path,required=True);p.add_argument('--selected',required=True)
    p.add_argument('--model-pin',required=True);p.add_argument('--interface-pin',required=True)
    p.add_argument('--checkpoint',type=Path,required=True);p.add_argument('--socket',type=Path,required=True)
    a=p.parse_args()
    binding=ParentBinding(a.owner,a.selected,a.model_pin,a.interface_pin)
    if a.socket.exists():raise FileExistsError(a.socket)
    # Use the owner's established module/dependency tree, not an independent
    # codec. This process is fresh; no module from another checkout is accepted.
    sys.path[:0]=[str(binding.owner/'tools'),str(binding.owner)]
    sys.meta_path.insert(0,OwnerSourceFinder(binding.owner))
    api=importlib.import_module('dsrom_s82_payload_interface')
    if Path(api.__file__).resolve()!=binding.payload_api_path:
        raise ValueError('wrong native payload provider')
    base=binding.owner/binding.selected
    binding._pinned(str(binding.selected/'matrix_map.jsonl.gz'),a.model_pin)
    with gzip.open(base/'matrix_map.jsonl.gz','rt') as f:matrices=[json.loads(s) for s in f]
    providers=json.loads(binding._pinned('results/uarch/dsrom_s82_source_interface_20261003/provider_interfaces.json',a.interface_pin))
    auxiliary=json.loads(binding._pinned(str(binding.selected/'auxiliary_map.json'),a.model_pin))['tensors']
    checkpoint=api.Checkpoint(a.checkpoint);dies={}
    def read(stage,rank,macro,row):
        key=(stage,rank)
        if key not in dies:dies[key]=api.DieROM(stage,rank,matrices,providers,auxiliary)
        return dies[key].read(checkpoint,macro,row)
    try:
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
            listener.bind(str(a.socket));listener.listen(1)
            print(json.dumps(dict(status='NATIVE_PROVIDER_READY',model_pin=a.model_pin,interface_pin=a.interface_pin,checkpoint_bytes_read=checkpoint.read_bytes)),flush=True)
            with listener.accept()[0] as client:accepted=serve_connection(client,read)
            return 0 if accepted else 1
    finally:
        print(json.dumps(dict(status='NATIVE_PROVIDER_TERMINAL',checkpoint_bytes_read=checkpoint.read_bytes)),flush=True)
        checkpoint.close();a.socket.unlink(missing_ok=True)

if __name__=='__main__':raise SystemExit(main())
