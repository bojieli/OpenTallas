#!/usr/bin/env python3
"""S81 minimum-component word service. Retain codec and wire API, reject wrong owners."""
import argparse
import fcntl
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import socket
import subprocess
import sys
import time

from dsrom_c8_parent_binding import ParentBinding
from dsrom_s82_native_word_server import serve_connection
import dsrom_s82_payload_interface as API

ROOT = Path(__file__).resolve().parents[1]
PIN = '57e3f45e3473e9e36b052f558a3b65ab71b1d6d1'
SELECTED = 'results/uarch/dsrom_s81_released_binding_20261004/canonical'
RETURN = 'results/uarch/dsrom_s81_rd64_connectivity_20261004/canonical_binding_r1'
MATRIX_SHA = '1d3f5077217e5627aa4f6c318bd97d2fa86f622790163d17fa7b7c8c624d7a8f'


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SelectedWord:
    def __init__(self, matrix, source, codec=API.matrix_word):
        if (matrix['stage'],matrix['compiled_NP'],matrix['alias'],matrix['format'],
            matrix['conversion'],matrix['K'],matrix['rows']) != (0,2417,'wq_a','fp8','native',5120,320):
            raise ValueError('wrong S81 phase0 matrix or non-native conversion')
        if matrix['plans'][0] != [0,0,0,1,128,0,160]:
            raise ValueError('wrong selected pair0 plan')
        self.matrix,self.source,self.codec=matrix,source,codec
        self.requests=0
        self.digest=hashlib.sha256()

    def __call__(self, stage, rank, macro, row):
        if any(type(v) is not int for v in (stage,rank,macro,row)):
            raise ValueError('integer address required')
        if stage != 0 or rank != 0 or macro not in range(4) or row not in range(4096):
            raise ValueError('outside admitted stage0/rank0/pair0 component')
        # Existing inverse decoder checks the phase0 plan's actual word ownership,
        # including both banks/parity. Nothing from historical S82 DieROM is used.
        word=self.codec(self.matrix,self.source,rank,macro,row)
        if type(word) is not int or not 0 <= word < (1<<274):
            raise ValueError('invalid native payload word')
        self.requests+=1
        self.digest.update(bytes([macro])+row.to_bytes(4,'little')+word.to_bytes(36,'little'))
        return word


def prepare(selection):
    binding=ParentBinding(ROOT,SELECTED,PIN,PIN,released_return_binding=RETURN)
    params=binding.field_parameters(0,0)
    if (params['field_pairs'],params['BF_pairs'],params['ROM_R'],params['physical_macros']) != (2417,519,128,9668):
        raise ValueError('not actual S81 field')
    if 0 not in binding.stage_map['BF_site_IDs']:
        raise ValueError('pair0 must be physical BF site, with FP8 operation')
    raw=binding._pinned(SELECTED+'/matrix_map.jsonl.gz',PIN)
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:
        first=json.loads(next(f))
        count=1+sum(1 for _ in f)
    if count!=46671 or sha(json.dumps(first,separators=(',',':')).encode())!=MATRIX_SHA:
        raise ValueError('canonical matrix census/first-source identity mismatch')
    providers=json.loads(binding._pinned(SELECTED+'/providers.json',PIN))
    if any(p['stage']==0 and 0 in p['pairs'] for p in providers):
        raise ValueError('selected matrix overlaps raw immutable provider')
    if (selection['stage'],selection['rank'],selection['pair'],selection['phase'],
        selection['go_bf'],selection['source_format'],selection['source_matrix_sha256']) != (0,0,0,0,0,'fp8',MATRIX_SHA):
        raise ValueError('caller selection not admitted component')
    # Pin actual imported codec/dependency sources; never another checkout or cached pyc.
    for module in tuple(sys.modules.values()):
        name=getattr(module,'__file__',None)
        if not name:
            continue
        p=Path(name).resolve()
        if p.is_relative_to(ROOT) and p.suffix=='.py' and p!=Path(__file__).resolve():
            binding._pinned(str(p.relative_to(ROOT)),PIN)
    return binding,first,params


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--selection',type=Path,required=True)
    ap.add_argument('--checkpoint',type=Path,required=True)
    ap.add_argument('--socket',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.output.exists():
        raise FileExistsError('preserve previous output: '+str(a.output))
    a.output.mkdir(parents=True)
    start=time.monotonic()
    checkpoint=None
    bound=False
    record={}
    with Path(str(a.socket)+'.owner.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            if a.socket.exists():
                raise FileExistsError('existing socket must not be replaced')
            selected_raw=a.selection.read_bytes()
            binding,matrix,params=prepare(json.loads(selected_raw))
            if a.checkpoint.resolve().name!=API.SNAPSHOT:
                raise ValueError('released checkpoint snapshot required')
            checkpoint=API.Checkpoint(a.checkpoint)
            index_sha=sha((a.checkpoint/'model.safetensors.index.json').read_bytes())
            descriptors={}
            for tensor in (matrix['tensor'],matrix['source_scale_tensor']):
                fd,base,d=checkpoint.descriptor(tensor)
                st=os.fstat(fd)
                descriptors[tensor]=dict(shard=checkpoint.index[tensor],data_base=base,descriptor=d,
                     file_identity=dict(device=st.st_dev,inode=st.st_ino,bytes=st.st_size,mtime_ns=st.st_mtime_ns))
            if descriptors[matrix['tensor']]['descriptor']['dtype']!='F8_E4M3' or descriptors[matrix['source_scale_tensor']]['descriptor']['dtype']!='F8_E8M0':
                raise ValueError('released native FP8/UE8M0 tensors required')
            word=SelectedWord(matrix,checkpoint)
            # One native source-read readiness check, not a simulation or reference.
            probe=API.matrix_word(matrix,checkpoint,0,0,0)
            record=dict(status='S81_NATIVE_PROVIDER_READY',pid=os.getpid(),
                process_start_ticks=int(Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]),
                source_root=str(ROOT),source_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                model_pin=PIN,interface_pin=PIN,source_sha256=binding.receipts,
                server_sha256=sha(Path(__file__).read_bytes()),selection_sha256=sha(selected_raw),
                socket=str(a.socket),protocol='16-byte LE stage/rank/macro/row; status32+36-byte LE native word',
                scope='stage0/rank0/pair0/phase0; BF physical model FP8 operation; no fullphase/token credit',
                field_parameters=params,matrix_count=46671,matrix_sha256=MATRIX_SHA,
                checkpoint=str(a.checkpoint.resolve()),checkpoint_index_sha256=index_sha,
                checkpoint_descriptors=descriptors,readiness_word_sha256=sha(probe.to_bytes(36,'little')),
                readiness_checkpoint_bytes=checkpoint.read_bytes,
                startup_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                startup_seconds=time.monotonic()-start)
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as listener:
                listener.bind(str(a.socket));bound=True;listener.listen(1)
                (a.output/'ready.json').write_text(json.dumps(record,indent=2)+'\n')
                print(json.dumps(record),flush=True)
                with listener.accept()[0] as client:
                    accepted=serve_connection(client,word)
            terminal=dict(status='S81_NATIVE_PROVIDER_CLIENT_CLOSED' if accepted else 'S81_NATIVE_PROVIDER_REJECTED',
                requests=word.requests,request_word_digest=word.digest.hexdigest(),
                checkpoint_bytes_read=checkpoint.read_bytes,elapsed_seconds=time.monotonic()-start,
                scope='transport lifecycle only, not component numerical PASS')
            (a.output/'terminal.json').write_text(json.dumps(terminal,indent=2)+'\n')
            print(json.dumps(terminal),flush=True)
            return 0 if accepted else 1
        except BaseException as e:
            (a.output/'failure.json').write_text(json.dumps(dict(error=repr(e),elapsed_seconds=time.monotonic()-start),indent=2)+'\n')
            raise
        finally:
            if checkpoint is not None:
                checkpoint.close()
            if bound:
                a.socket.unlink()


if __name__=='__main__':
    raise SystemExit(main())
