"""Publish native RTL HIDDEN packets after checking their hardware provenance.
Expected h_in is an oracle only; no Python-generated payload reaches the DUT.
"""
import hashlib,json
from pathlib import Path

def native_packet(gate_dir, token):
    gate_dir=Path(gate_dir)
    record=json.loads((gate_dir/'record.json').read_text())
    if record.get('pass') is not True or record['fixture']['token']!=int(token):
        raise ValueError('missing native embedding gate or wrong token')
    if record['runs']['0']['returncode']!=0 or record['runs']['1']['returncode']==0:
        raise ValueError('missing passing RTL and failing mutant evidence')
    packet=(gate_dir/'hin_m0.mem').read_bytes()
    if hashlib.sha256(packet).hexdigest()!=record['hin_sha256']:
        raise ValueError('native embedding dump hash mismatch')
    rows=[int(s,16) for s in packet.decode().splitlines()]
    if len(rows)!=641 or rows[0]!=0:raise ValueError('native packet framing mismatch')
    return packet,rows[1:]

def publish_mtp0(native_dir, output_dir, mtp_dir, ids):
    import pickle
    import numpy as np
    native_dir,output_dir,mtp_dir=map(Path,(native_dir,output_dir,mtp_dir))
    output_dir.mkdir(parents=True,exist_ok=True)
    outputs=[]
    for i,token in enumerate(ids):
        packet,rows=native_packet(native_dir/f'bankgate{token}',token)
        fx=pickle.loads((mtp_dir/f'hc_chain_M0R{i}.pkl').read_bytes())
        h=np.asarray(fx['chain']['h_in'],np.float32).view(np.uint32)
        if h.shape!=(4,5120) or np.any(h&65535):raise ValueError('invalid expected h_in')
        # Independent scoreboard: compare every lane/copy; do not synthesize output.
        for q,row in enumerate(rows):
            for b in range(8):
                for k in range(4):
                    if ((row>>(16*(b*4+k)))&65535)!=int(h[k,8*q+b]>>16):
                        raise ValueError(f'RTL embedding mismatch row={i},q={q},b={b},copy={k}')
        dest=output_dir/f'hin_M0R{i}.mem';dest.write_bytes(packet)
        outputs.append({'row':i,'token':int(token),'path':str(dest),'sha256':hashlib.sha256(packet).hexdigest()})
    (output_dir/'embedding_native.json').write_text(json.dumps({'source':'native RTL embedding bank + mapped SRAM expansion','outputs':outputs},indent=2)+'\n')
    return outputs
