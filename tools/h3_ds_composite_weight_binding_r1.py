"""Default-off, exact native BF16 compressor composite binding successor.
Metadata enrollment and call planning do not admit payload or continuation.
Original r33 expert/wo_a handling and all constructor/MRO guards remain intact.
"""
import hashlib
import inspect
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('results/uarch/ds_composite_weight_binding_20261003')
PCS = (115, 443, 776)
LAYERS = (2, 8, 14)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def source_identity(cls):
    rows = []
    for base in cls.__mro__:
        if base is object:
            continue
        path = Path(inspect.getsourcefile(base)).resolve()
        rows.append(dict(module=base.__module__,qualname=base.__qualname__,
                         path=str(path.relative_to(ROOT)),
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    return rows


def resolve_call(native, enrollment, name, required, owned, spec):
    """Exact emitted owner/template/binding/spec identity, then row projection."""
    if name != 'weight' or required.get('kind') != 'immutable_weight_provider':
        raise ValueError('composite weight operand identity')
    matches = [op for op in native['instructions']
               if any(row is owned for row in op['rank_bindings'])]
    if len(matches) != 1:
        raise ValueError('exact native composite weight call identity required')
    op = matches[0]
    pc = op['pc']
    record = enrollment['operations'].get(str(pc))
    if record is None or pc not in PCS or digest(op) != record['operation_sha256']:
        raise ValueError('enrolled composite native operation identity')
    tid = owned['template']
    if (op['provider_bindings'].get(tid, {}).get(name) != required
            or native['templates'].get(tid, {}).get('providers', {}).get(name) != spec
            or digest(native['templates'][tid]) != record['templates'][tid]):
        raise ValueError('exact emitted composite binding/template/spec')
    src = op['source_op']
    layer = LAYERS[PCS.index(pc)]
    names = [f'layers.{layer}.attn.compressor.{part}.weight' for part in ('wkv', 'wgate')]
    if (op['family'] != 'mv' or src['fn'] != 'mv' or src['fmt'] != 'bf16'
            or src['w'] != names or required['logical_tensor'] != names
            or required['format'] != 'bf16' or src['layer'] != layer
            or src['n'] != 1024 or src['k'] != 5120
            or src['rows'] != required['row_intervals']):
        raise ValueError('source composite order/format/row/K bounds')
    rank = owned['rank']
    if type(rank) is not int or not 0 <= rank < 96:
        raise ValueError('source composite rank')
    lo, hi = owned['row_interval']
    if (required['row_intervals'][rank] != [lo, hi]
            or [lo,hi] != [1024*rank//96,1024*(rank+1)//96]
            or spec['shape'] != [hi-lo,5120] or spec['dtype'] != 'F32'):
        raise ValueError('source composite row ownership/LOAD shape')
    segments = []
    for ordinal, tensor in enumerate(names):
        header = enrollment['components'][tensor]
        if (header['dtype'] != 'BF16' or header['shape'] != [512,5120]
                or header['layout'] != 'safetensors_C_row_major'
                or header['scale_tensor'] is not None
                or header['data_offsets'][1]-header['data_offsets'][0] != 512*5120*2):
            raise ValueError('source composite checkpoint dtype/layout/scale/span')
        first, last = max(lo,ordinal*512), min(hi,(ordinal+1)*512)
        if first >= last:
            continue
        rows = [first-ordinal*512,last-ordinal*512]
        segments.append(dict(component_ordinal=ordinal,tensor=tensor,
            rows=rows,K=[0,5120],destination_rows=[first-lo,last-lo],
            source_dtype='BF16',scale_tensor=None,
            source_bytes=(last-first)*5120*2,shard=header['shard'],
            source_file_byte_interval=[header['data_base']+header['data_offsets'][0]+rows[0]*5120*2,
                                      header['data_base']+header['data_offsets'][0]+rows[1]*5120*2]))
    if sum(s['destination_rows'][1]-s['destination_rows'][0] for s in segments) != hi-lo:
        raise ValueError('complete composite selected-row coverage')
    return dict(PC=pc,rank=rank,template=tid,operand=name,
        logical_tensor=names,rows=[lo,hi],K=[0,5120],shape=spec['shape'],
        dtype=spec['dtype'],segments=segments,checkpoint_revision=enrollment['checkpoint_revision'],
        scale_policy='none: exact BF16 components, no scale read or invented codec',
        caller_order_sha256=record['caller_order_sha256'],
        selected_checkpoint_bytes=(hi-lo)*5120*2,output_bytes=(hi-lo)*5120*4,
        temporary_and_output_bound_bytes=2*(hi-lo)*5120*4)


def load_enrollment():
    raw = (ROOT/OUT/'enrollment-r1.json').read_bytes()
    return json.loads(raw),hashlib.sha256(raw).hexdigest()


def validate_enrollment(native, manifest, cls, *, check_full_native=True):
    enrollment, sha = load_enrollment()
    requested = manifest.get('composite_weight_binding')
    expected = dict(schema='DS_COMPOSITE_BF16_OPT_IN_R1',enabled=True,
        enrollment_sha256=sha,payload_reads_admitted=False)
    # Payload is a separate admission bit; every other metadata field is exact.
    if not isinstance(requested,dict) or set(requested) != set(expected):
        raise ValueError('explicit composite enrollment absent')
    if type(requested['payload_reads_admitted']) is not bool:
        raise ValueError('explicit composite payload admission bool')
    if dict(requested,payload_reads_admitted=False) != expected:
        raise ValueError('exact composite enrollment selection')
    if ((check_full_native and digest(native) != enrollment['native_canonical_sha256'])
            or manifest.get('checkpoint_revision') != enrollment['checkpoint_revision']
            or manifest.get('checkpoint_index_sha256') != enrollment['checkpoint_index_sha256']
            or source_identity(cls) != enrollment['provider_MRO']):
        raise ValueError('composite source/native/checkpoint/MRO identity')
    for path,want in enrollment['source_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != want:
            raise ValueError('composite enrolled source drift: '+path)
    return enrollment


class PayloadNotAdmitted(ValueError):
    def __init__(self, plan):
        super().__init__('composite call metadata accepted; payload reads not admitted')
        self.plan = plan


class CompositeWeightMixin:
    def weight_call_plan(self,name,required,owned,spec):
        enrollment = validate_enrollment(self.native,self.manifest,type(self),check_full_native=False)
        return resolve_call(self.native,enrollment,name,required,owned,spec)

    def weight_view(self,name,required,owned,spec):
        tensor = required.get('logical_tensor')
        if not (isinstance(tensor,list) and all(isinstance(v,str) for v in tensor)):
            return super().weight_view(name,required,owned,spec)
        plan = self.weight_call_plan(name,required,owned,spec)
        if not self.manifest['composite_weight_binding']['payload_reads_admitted']:
            raise PayloadNotAdmitted(plan)
        # This data-only implementation remains unexecuted until payload admission.
        # Existing LockedCheckpoint supplies exact BF16 bits expanded to F32.
        from h3_ds_checkpoint_provider_r30 import LockedCheckpoint
        if type(self.checkpoint) is not LockedCheckpoint:
            raise ValueError('exact locked checkpoint source reader required')
        if self.revision != plan['checkpoint_revision']:
            raise ValueError('composite checkpoint revision')
        # Acquire the existing reader's exact shared locks and stamps before any
        # payload call. Header pins remain bound to the fd used by r30.tensor.
        import fcntl,os,struct
        enrollment,_ = load_enrollment()
        prepared = {}
        try:
            for segment in plan['segments']:
                header = enrollment['components'][segment['tensor']]
                filename = header['shard']
                if self.checkpoint.index.get(segment['tensor']) != filename:
                    raise ValueError('composite selected index mapping')
                if filename in self.checkpoint.files:
                    record = self.checkpoint.files[filename]
                elif filename in prepared:
                    record = prepared[filename]
                else:
                    fd = os.open(self.checkpoint.path/filename,os.O_RDONLY)
                    try:
                        fcntl.flock(fd,fcntl.LOCK_SH|fcntl.LOCK_NB)
                        stamp = os.fstat(fd)
                        count = struct.unpack('<Q',os.pread(fd,8,0))[0]
                        if count != header['data_base']-8:
                            raise ValueError('composite selected shard header extent')
                        raw = os.pread(fd,count,8)
                        if os.fstat(fd) != stamp:
                            raise ValueError('composite shard changed during preflight')
                        record = (fd,json.loads(raw),8+count,stamp,hashlib.sha256(raw).hexdigest())
                        prepared[filename] = record
                    except BaseException:
                        os.close(fd)
                        raise
                if record[4] != header['raw_header_sha256'] or record[2] != header['data_base']:
                    raise ValueError('composite selected locked shard header pin')
            self.checkpoint.files.update(prepared)
        except BaseException:
            for record in prepared.values():
                os.close(record[0])
            raise
        value = np.empty(plan['shape'],dtype=np.dtype('<f4'))
        for segment in plan['segments']:
            data,dtype = self.checkpoint.tensor(segment['tensor'],rows=segment['rows'],cols=segment['K'])
            rows = segment['destination_rows']
            if dtype != 'BF16' or data.dtype != value.dtype or list(data.shape) != [rows[1]-rows[0],5120]:
                raise ValueError('exact composite BF16 selected-row payload')
            value[rows[0]:rows[1]] = data
        value.flags.writeable = False
        return value


def provider_class(base=None):
    """Class enrollment only; no provider constructors or runtime installation."""
    if base is None:
        from h3_ds_connected_provider_r37 import composed_class
        base = composed_class()
    class CompositeProvider(CompositeWeightMixin,base):
        def __init__(self,manifest,native,dispatch,homes):
            validate_enrollment(native,manifest,type(self))
            super().__init__(manifest,native,dispatch,homes)
    return CompositeProvider
