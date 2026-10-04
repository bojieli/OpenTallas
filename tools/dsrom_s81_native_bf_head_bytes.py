#!/usr/bin/env python3
"""Synchronous raw-byte bridge to the existing ReleasedHeadByteProvider.

No new images, FP operations, expected-output sources, or ROM allocators.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import socket
import struct
from pathlib import Path


def response(provider, request: bytes) -> bytes:
    if len(request)!=16:
        raise ValueError('BF head request must be four uint32 coordinates')
    rank,row,h,b=struct.unpack('<4I',request)
    try:
        if not (rank<4 and row<32320 and h<40 and b<8):
            raise ValueError('outside released head extent')
        value=provider.native_bf_word(rank,row,h,b)
        if (value['rank'],value['local_row'],value['h'],value['b'])!=(rank,row,h,b):
            raise ValueError('released provider returned a different source coordinate')
        word=value['word274']
        if type(word) is not int or not 0<=word<1<<274:
            raise ValueError('released native word width')
        return struct.pack('<I',0)+request+word.to_bytes(36,'little')
    except (ValueError,KeyError,TypeError):
        return struct.pack('<I',1)+request+bytes(36)


def serve(provider, path: Path, record: Path | None = None) -> None:
    # Caller owns provider and its exact source enrollment; never unlink a
    # preexisting socket/record or replace another running source service.
    if path.exists() or (record is not None and record.exists()):
        raise FileExistsError('preserve existing native head provider output')
    journal=hashlib.sha256();count=0;raw_bytes=0;failed=False
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
        listener.bind(str(path));listener.listen(1)
        try:
            conn,_=listener.accept()
            with conn:
                while True:
                    request=b''
                    while len(request)<16:
                        part=conn.recv(16-len(request))
                        if not part:break
                        request+=part
                    if not request:break
                    if len(request)!=16:raise ValueError('partial live head byte request')
                    reply=response(provider,request)
                    conn.sendall(reply);journal.update(request+reply);count+=1
                    if reply[:4]!=bytes(4):
                        failed=True;break
                    raw_bytes+=256  # eight actual32B source reads, no cache credit
        finally:
            if record is not None:
                record.write_text(json.dumps({'schema':'dsrom.s81.released_native_bf_head_bytes.v1',
                    'requests':count,'raw_source_read_bytes':raw_bytes,
                    'coordinate_payload_journal_sha256':journal.hexdigest(),
                    'failed_source_request':failed,'host_arithmetic':False,
                    'hardware_bandwidth_or_latency_credit':False},indent=2)+'\n')
    # Keep socket pathname as evidence. Cleanup belongs to the run owner.


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--socket',type=Path,required=True)
    parser.add_argument('--record',type=Path,required=True)
    args=parser.parse_args()
    from dsrom_s81_head_source_binding import HeadSourceBinding,ReleasedHeadByteProvider
    with ReleasedHeadByteProvider(HeadSourceBinding(),args.snapshot) as provider:
        serve(provider,args.socket,args.record)

if __name__=='__main__':main()
