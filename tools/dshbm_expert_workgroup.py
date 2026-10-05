#!/usr/bin/env python3
"""Source-ID steering and unchanged packed FP4 row streams for the 24-SM workgroup.

No router computation, weight conversion, arithmetic reordering, or expert sum is
performed here. The caller supplies the six source-produced IDs in their golden
ascending order and a read-only released packed-weight row reader.
"""
from dataclasses import dataclass
from numbers import Integral

K = 5120
DIE_ROWS = 24
SM_ROWS = 12
EXPERT_ROWS = 2304
N_EXPERTS = 384


@dataclass(frozen=True)
class Descriptor:
    sm: int
    slot: int
    expert: int
    matrix: str
    row_start: int
    row_stop: int

    @property
    def tensor(self):
        return f"ffn.experts.{self.expert}.{self.matrix}.weight"


def steer(expert_ids, die):
    """Two adjacent SMs per matrix; eight SMs receive no descriptor/start."""
    ids = tuple(expert_ids)
    if (len(ids) != 6 or any(isinstance(x, bool) or not isinstance(x, Integral)
                             or not 0 <= x < N_EXPERTS for x in ids)
            or tuple(sorted(set(ids))) != ids):
        raise ValueError("six distinct source-produced IDs in golden ascending order required")
    if isinstance(die, bool) or not isinstance(die, Integral) or not 0 <= die < 96:
        raise ValueError("die must select one of the 96 actual 24-row partitions")
    return tuple(Descriptor(4 * s + 2 * m + h, s, int(e), matrix,
                            int(die) * DIE_ROWS + h * SM_ROWS,
                            int(die) * DIE_ROWS + (h + 1) * SM_ROWS)
                 for s, e in enumerate(ids) for m, matrix in enumerate(("w1", "w3"))
                 for h in range(2))


def weight_lines(packed, scales):
    """Native 1088-bit FP4 lines, EXACT existing issue_order(12,3,8,True).

    packed is raw uint8 [12,2560] (low nibble first); scales is raw UE8M0
    uint8 [12,160]. No decoding/re-encoding of either released field. Padding
    at group 2 lanes 4..7 is zero, matching the current SM bench.
    """
    import numpy as np
    from rtl_gpu_sm_exact import issue_order
    if packed.dtype != np.uint8 or packed.shape != (SM_ROWS, K // 2):
        raise ValueError("raw packed FP4 rows must be uint8 [12,2560]")
    if scales.dtype != np.uint8 or scales.shape != (SM_ROWS, K // 32):
        raise ValueError("raw UE8M0 rows must be uint8 [12,160]")
    lines = []
    for r, g, t in issue_order(SM_ROWS, 3, 8, True):
        word = 0
        for lane in range(8):
            block = (g * 8 + lane) * 8 + t
            if block < 160:
                payload = int.from_bytes(packed[r, block * 16:(block + 1) * 16].tobytes(), "little")
                word |= payload << (128 * lane)
                word |= int(scales[r, block]) << (1024 + 8 * lane)
        lines.append(word)
    return tuple(lines)


def layout(expert_ids, die, reader):
    """reader(expert, matrix, row_start, row_stop) -> raw packed, raw scales.

    Resolves actual expert identity before reading; never slot0 substitution.
    Output descriptor remains associated with its private stream/result rows.
    """
    return tuple((d, weight_lines(*reader(d.expert, d.matrix, d.row_start, d.row_stop)))
                 for d in steer(expert_ids, die))


def restore_rows(descriptors, results):
    """Restore each matrix's increasing global row order; no expert reduction."""
    if len(descriptors) != 24 or set(results) != {d.sm for d in descriptors}:
        raise ValueError("all and only 24 owned result streams required")
    out = {}
    for d in descriptors:
        values = results[d.sm]
        if len(values) != 12:
            raise ValueError("each SM must retire exactly 12 ordered rows")
        key = (d.slot, d.expert, d.matrix)
        out.setdefault(key, []).extend(zip(range(d.row_start, d.row_stop), values))
    for rows in out.values():
        rows.sort(key=lambda item: item[0])
    return out


def sm_vectors(packed, scales, activation):
    """Existing native seqbench vectors and golden using actual released fields.

    The random generator is intentionally absent: gen_op must never need it on
    this path. NC8/active1 uses the existing 2-beat AR activation load.
    """
    import numpy as np
    import dshbm_matched_sm_seq as M
    x = np.asarray(activation)
    if x.dtype != np.float32 or x.shape != (K,):
        raise ValueError("actual ffn_norm activation must be float32[5120]")
    # Inactive columns are explicitly zero; never expose an invented input as
    # an actual position. The caller runs/compares only active column zero.
    xs = [x] + [np.zeros(K, dtype=np.float32) for _ in range(7)]
    result = M.gen_op("v41_fp4", 12, K, 8, None, X=xs,
                      released_fp4=(packed, scales))
    if tuple(result['lines']) != weight_lines(packed, scales):
        raise AssertionError("native bench packing differs from source row layout")
    return result


def checkpoint_reader(checkpoint, layer):
    """Read exact released tensor row bytes via the existing mmap accessor.

    No full checkpoint construction and no decoded weight cache. Only selected
    packed rows and their scales are copied into the SM staging image.
    """
    import numpy as np
    if layer not in (3, 20):
        raise ValueError("this implementation is enrolled for L3/L20 only")
    def read(expert, matrix, start, stop):
        name = f'layers.{layer}.ffn.experts.{expert}.{matrix}.weight'
        result = []
        for key, wanted_shape, wanted_dtype in (
                (name, (2304,2560), 'I8'),
                (name[:-len('.weight')]+'.scale', (2304,160), 'F8_E8M0')):
            mm, dtype, shape, offset = checkpoint._raw(key)
            if tuple(shape) != wanted_shape or dtype != wanted_dtype:
                raise ValueError(f"released tensor geometry mismatch: {key} {dtype} {shape}")
            view = np.frombuffer(mm, dtype=np.uint8, count=wanted_shape[0]*wanted_shape[1],
                                 offset=offset).reshape(wanted_shape)
            result.append(view[start:stop].copy())
        return tuple(result)
    return read



def export_weight_rows(checkpoint, layer, expert_ids, out):
    """Lossless selected tensor-row export, not inference/weight re-encoding."""
    import json, hashlib
    from pathlib import Path
    steer(expert_ids,0)
    out = Path(out); out.mkdir(parents=True,exist_ok=False)
    record = dict(layer=layer,expert_ids=list(expert_ids),checkpoint=str(checkpoint.snap),
                  scope='released selected FP4/UE8M0 bytes only; no inference',tensors=[])
    read = checkpoint_reader(checkpoint,layer)
    for expert in expert_ids:
        for matrix in ('w1','w3'):
            packed,scales = read(int(expert),matrix,0,2304)
            for kind,data in [('packed',packed),('scale',scales)]:
                name=f'expert{expert}_{matrix}.{kind}'
                raw=data.tobytes(); (out/name).write_bytes(raw)
                record['tensors'].append(dict(file=name,expert=int(expert),matrix=matrix,
                    kind=kind,shape=list(data.shape),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    (out/'source.json').write_text(json.dumps(record,indent=2)+'\n')
    return record


def exported_weight_reader(root,layer,expert_ids):
    import json, hashlib
    from pathlib import Path
    import numpy as np
    root=Path(root); record=json.loads((root/'source.json').read_text())
    if record['layer']!=layer or record['expert_ids']!=list(expert_ids):
        raise ValueError('exported weight ownership does not match actual routed source IDs')
    arrays={}
    for t in record['tensors']:
        p=root/t['file']
        if p.stat().st_size!=t['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=t['sha256']:
            raise ValueError('released raw row export changed: '+str(p))
        arrays[t['expert'],t['matrix'],t['kind']]=np.memmap(p,mode='r',dtype=np.uint8,shape=tuple(t['shape']))
    def read(expert,matrix,start,stop):
        return tuple(arrays[expert,matrix,k][start:stop].copy() for k in ('packed','scale'))
    return read


def run_actual(args):
    """Native unchanged SM bench; real router IDs steer every released row.

    Checks cold and repeated actual row streams separately. The repeat is a
    timing calibration, never credited as another program op or free warm-up.
    """
    import json, hashlib, subprocess
    from pathlib import Path
    import numpy as np
    import hdc_golden as G
    import hdc_golden_v41 as V
    import dshbm_matched_sm_seq as M
    from deepseek_v41_deployment_quality import Checkpoint
    V.set_arith('chunk8')
    x = G.from_bits(np.fromfile(args.activation_u32,dtype='<u4'))
    ids = np.fromfile(args.router_ids_u32,dtype='<u4')
    # Mandatory real-input files; no random fallback or synthetic router.
    descriptors = steer(tuple(int(e) for e in ids), 0)
    if x.shape != (5120,):
        raise ValueError("activation capture must contain exactly 5120 binary32 words")
    root = Path(args.workdir); root.mkdir(parents=True, exist_ok=False)
    if args.weight_rows:
        reader = exported_weight_reader(args.weight_rows,args.layer,tuple(int(e) for e in ids))
    else:
        checkpoint = Checkpoint(args.checkpoint)
        reader = checkpoint_reader(checkpoint,args.layer)
    params = dict(ENABLE=1,SUB=4,LBS=2,LSB=16,NC=8,XDEPTH=128,RMAX=256,LEV=4,XB=2)
    if args.native_receipt:
        receipt=json.loads(Path(args.native_receipt).read_text())
        if receipt['status']!='PASS_COMPILED_ONLY' or receipt['params']!=params:
            raise ValueError('compiled SM bench geometry/terminal not enrolled')
        if any(hashlib.sha256((M.ROOT/p).read_bytes()).hexdigest()!=h
               for p,h in receipt['source_sha256'].items()):
            raise ValueError('compiled SM RTL source mismatch')
        binary=Path(receipt['binary'])
        if hashlib.sha256(binary.read_bytes()).hexdigest()!=receipt['binary_sha256']:
            raise ValueError('compiled SM binary changed')
        run,command=[str(binary)],receipt['command']
    else:
        run, command = M.compile_bench('verilator',params,root/'build',args.jobs)
    record = dict(layer=args.layer,position=args.position,router_ids=[d.expert for d in descriptors[::4]],
                  full_model_inference=False,arithmetic='unchanged SM + existing chunk8 golden',
                  source_scope='12 routed gate/up matrices only; no W2/shared-expert/combine credit',
                  build_command=command,cases=[],status='RUNNING',adopted=False)
    for name in ('activation_u32','router_ids_u32'):
        p = Path(getattr(args,name)); record[name] = dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    record_path = root/'record.json'
    def save(): record_path.write_text(json.dumps(record,indent=2)+'\n')
    save()
    for die in range(96):
        for d in steer(tuple(int(e) for e in ids),die):
            case = root/f'die{die:02}_sm{d.sm:02}'; case.mkdir()
            packed,scales = reader(d.expert,d.matrix,d.row_start,d.row_stop)
            g = sm_vectors(packed,scales,x)
            seq = [12,8,3,2,len(g['lines']),1,1,24]*2
            (case/'seq.hex').write_text('\n'.join(f'{v:08x}' for v in seq)+'\n')
            (case/'lines.hex').write_text('\n'.join(f'{v:0272x}' for v in g['lines']*2)+'\n')
            width = (8*M.XC+2048+3)//4
            (case/'x.hex').write_text('\n'.join(f'{v:0{width}x}' for v in g['xw']*2)+'\n')
            with (case/'runtime.log').open('w') as log:
                proc = subprocess.run(run+[f'+DIR={case.resolve()}','+NOPS=2'],stdout=log,
                                      stderr=subprocess.STDOUT,cwd=case)
            got, meta = {},{}
            if (case/'out.txt').exists():
                for line in (case/'out.txt').read_text().splitlines():
                    if line.startswith('# op'):
                        t = line[2:].split(); meta[int(t[1])] = {t[k]:int(t[k+1]) for k in range(2,len(t)-1,2)}
                    elif not line.startswith('#'):
                        op,row,h = line.split(); got[int(op),int(row)] = int(h,16)&0xffffffff
            mismatches = sum(got.get((op,r)) != int(G.bits(g['gold'][0][r]))
                             for op in range(2) for r in range(12))
            exact = (proc.returncode==0 and len(got)==24 and mismatches==0 and len(meta)==2
                     and all(m['fault']==0 and m['consumed']==288 and m['results']==12 for m in meta.values()))
            rec = dict(die=die,sm=d.sm,slot=d.slot,expert=d.expert,matrix=d.matrix,
                       rows=[d.row_start,d.row_stop],packed_sha256=hashlib.sha256(packed.tobytes()).hexdigest(),
                       scale_sha256=hashlib.sha256(scales.tobytes()).hexdigest(),exact=exact,
                       mismatches=mismatches,exit=proc.returncode,rtl=meta)
            record['cases'].append(rec); save()
            if not exact:
                record['status']='FAIL_ACTUAL_SOURCE';save();return 1
    record['status']='PASS_ACTUAL_SOURCE_ROUTED_GU_ALL_ROWS'; save(); return 0


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    w = p.add_mutually_exclusive_group(required=True)
    w.add_argument('--checkpoint')
    w.add_argument('--weight-rows')
    p.add_argument('--layer',type=int,choices=(3,20),required=True)
    p.add_argument('--position',type=int,choices=(1048575,),required=True)
    p.add_argument('--activation-u32',required=True)
    p.add_argument('--router-ids-u32',required=True)
    p.add_argument('--workdir',required=True)
    p.add_argument('--jobs',type=int,choices=range(1,17),default=8)
    p.add_argument('--native-receipt',help='reuse an exact source/parameter/binary-verified completed bench')
    raise SystemExit(run_actual(p.parse_args()))
