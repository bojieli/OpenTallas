"""Read-only released checkpoint bytes; no allocation, activation or inference.

Reader implementation retained from the source-pinned W2 payload interface.
"""
import json, math, os, struct
from pathlib import Path
SNAPSHOT='dba1be0a40aa45a94ad051997016db3960a90277'
DEFAULT_CHECKPOINT=Path.home()/'.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots'/SNAPSHOT

class Checkpoint:
    """Read exact source bits with pread, without constructing a second 510GB image."""
    def __init__(self, root=DEFAULT_CHECKPOINT):
        self.root=Path(root)
        self.index=json.loads((self.root/'model.safetensors.index.json').read_text())['weight_map']
        self.files={};self.read_bytes=0
    def descriptor(self,tensor):
        shard=self.index[tensor]
        if shard not in self.files:
            fd=os.open(self.root/shard,os.O_RDONLY)
            try:
                n=struct.unpack('<Q',os.pread(fd,8,0))[0]
                header=json.loads(os.pread(fd,n,8))
            except BaseException:
                os.close(fd);raise
            self.files[shard]=(fd,8+n,header)
        fd,base,header=self.files[shard]
        return fd,base,header[tensor]
    def raw(self,tensor,offset,length):
        fd,base,d=self.descriptor(tensor);a,b=d['data_offsets']
        if offset<0 or length<0 or offset+length>b-a:raise ValueError('source byte bounds')
        data=os.pread(fd,length,base+a+offset)
        if len(data)!=length:raise EOFError(tensor)
        self.read_bytes+=length
        return data
    def element(self,tensor,row,col=0):
        _,_,d=self.descriptor(tensor)
        shape=d['shape'];cols=shape[-1] if len(shape)>1 else 1
        count=math.prod(shape)
        i=row*cols+col
        if not 0<=col<cols or not 0<=i<count:raise ValueError('source element bounds')
        width={'F32':4,'BF16':2,'F8_E4M3':1,'F8_E8M0':1,'I8':1,'U8':1}[d['dtype']]
        return int.from_bytes(self.raw(tensor,i*width,width),'little')
    def close(self):
        for fd,_,_ in self.files.values():os.close(fd)
        self.files.clear()

