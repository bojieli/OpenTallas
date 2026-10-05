"""Opt-in data-only native operand views acquired from real addressed producers.

Preserves original providers/primitive arithmetic. No oracle payload, home move,
execution admission, new journal capacity, or hardware qualification is supplied.
Kepler composes this above the existing provider only in a fresh reviewed stage.
"""
import hashlib
import json
import math
import re
import numpy as np

DTYPES = {'F32':np.dtype('<f4'),'U32':np.dtype('<u4'),'I64':np.dtype('<i8')}
FULL = {'full source value reshaped to declared LOAD shape',
        'fullK with BF16 at explicit instruction','source-local valid extent',
        'full384','lo=384*rank//96,hi=384*(rank+1)//96',
        'lo=2304*rank//96,hi=2304*(rank+1)//96'}
SPECIAL_FAMILIES = {'all_gather','all_reduce','attend','topk_merge'}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def recipe(binding, spec, location):
    """Reject guessed slices, codecs, truncation and non-declared shape changes."""
    if binding['kind'] != 'versioned_operand': raise ValueError('versioned source required')
    dtype = DTYPES[spec['dtype']]
    if np.dtype(location['dtype']) != dtype: raise ValueError('source codec conversion forbidden')
    source_count = math.prod(location['shape']); count = math.prod(spec['shape'])
    address = binding['native_address_view']
    if address in FULL:
        if count != source_count: raise ValueError('full source extent cannot truncate or pad')
        lo, hi = 0, source_count
    else:
        match = re.fullmatch(r'flat\[(\d+):(\d+)\](?: reshape4x5120)?',address)
        if not match: raise ValueError('unsupported explicit source view '+address)
        lo,hi = map(int,match.groups())
        if not 0 <= lo < hi <= source_count or hi-lo != count:
            raise ValueError('declared flat slice outside actual producer extent')
        if address.endswith(' reshape4x5120') and spec['shape'] != [4,5120]:
            raise ValueError('actual HC key reshape')
    words = dtype.itemsize//4
    return dict(source_elements=[lo,hi],source_word_interval=[lo*words,hi*words],
                shape=list(spec['shape']),dtype=dtype.str,byte_count=count*dtype.itemsize,
                words_per_element=words,arithmetic_or_conversion=False)


def ordinary(op,name,binding):
    if op['family'] in SPECIAL_FAMILIES: return False
    if binding['kind'] != 'versioned_operand': return False
    if op['family']=='index_scores' and name in ('keys','key_codes','key_exp'): return False
    if name in ('route_weight','expert_outputs','query_codes','query_exp'): return False
    return binding['native_address_view'] in FULL or binding['native_address_view'].startswith('flat[')


def concat_rows(names,shapes,rows,spec):
    if not isinstance(names,list) or len(names)!=2 or not all(isinstance(n,str) for n in names):
        raise ValueError('explicit ordered two-matrix source names required')
    if any(len(s)!=2 for s in shapes) or shapes[0][1]!=shapes[1][1]:
        raise ValueError('source concat K geometry')
    lo,hi=rows;total=sum(s[0] for s in shapes)
    if not 0<=lo<hi<=total or spec['shape']!=[hi-lo,shapes[0][1]] or spec['dtype']!='F32':
        raise ValueError('actual ordered concat row/shape binding')
    pieces=[];base=0
    for name,shape in zip(names,shapes):
        left=max(lo,base);right=min(hi,base+shape[0])
        if left<right:pieces.append(dict(tensor=name,rows=[left-base,right-base]))
        base+=shape[0]
    return pieces


class TypedOperandViewsMixin:
    """Lease before each accepted addressed read; defer specialist ownership."""
    def enable_fullgraph_typed_views(self, *, native_content_sha256):
        if hasattr(self,'fullgraph_source_sha'): raise ValueError('already bound')
        actual = hashlib.sha256(canonical(self.native)).hexdigest()
        if actual != native_content_sha256 or self.C0_source_views.source_sha != actual:
            raise ValueError('exact effective native and reviewed source bridge required')
        self.fullgraph_source_sha=actual; self.fullgraph_source_failed=False

    def weight_view(self,name,required,owned,spec):
        names=required['logical_tensor']
        if not (isinstance(names,list) and all(isinstance(n,str) for n in names)):
            return super().weight_view(name,required,owned,spec)
        if not hasattr(self,'fullgraph_source_sha'):
            return super().weight_view(name,required,owned,spec)
        if self.fullgraph_source_failed:raise ValueError('failed source acquisition; no retry')
        if name!='weight' or required['format']!='bf16' or required['row_intervals'][owned['rank']]!=owned['row_interval']:
            raise ValueError('actual BF16 concat rank/K source binding')
        shapes=[]
        for tensor in names:
            empty,codec=self.checkpoint.tensor(tensor,rows=[0,0])
            # Read only header geometry before choosing actual owned source rows.
            header=self.checkpoint.files[self.checkpoint.index[tensor]][1][tensor]
            if codec!='BF16' or empty.dtype!=np.float32:raise ValueError('released concat BF16 codec')
            shapes.append(header['shape'])
        pieces=concat_rows(names,shapes,owned['row_interval'],spec)
        arrays=[]
        for piece in pieces:
            a,codec=self.checkpoint.tensor(piece['tensor'],rows=piece['rows'])
            if codec!='BF16' or a.dtype!=np.float32:raise ValueError('owned concat codec changed')
            arrays.append(a)
        out=np.concatenate(arrays,axis=0);out.flags.writeable=False
        return out

    def _read_one(self,op,owned,key,bindings,generation,collective=None):
        if not hasattr(self,'fullgraph_source_sha'):
            return super()._read_one(op,owned,key,bindings,generation,collective)
        if self.fullgraph_source_failed: raise ValueError('failed source acquisition; no retry')
        if generation != self.generation: raise ValueError('source owner generation')
        if hashlib.sha256(canonical(self.native)).hexdigest() != self.fullgraph_source_sha:
            raise ValueError('bound native changed')
        targets = {n:b for n,b in bindings.items() if ordinary(op,n,b)}
        specs=self.native['templates'][key]['providers']; rank=owned['rank']; plans={}
        for name,b in targets.items():
            # Initializers keep their committed source/checkpoint acquisition.
            loc=self.locations.get((b['version'],rank))
            if loc is None:
                if (b['version'],rank) in self.source_images or (b['version'],rank) in self.published:
                    continue
                raise ValueError('actual addressed producer unavailable '+b['version'])
            plans[name]=recipe(b,specs[name],loc)
        result=super()._read_one(op,owned,key,{n:b for n,b in bindings.items() if n not in plans},generation,collective)
        # Parent registers this same dictionary in the normal view lease table.
        for name,plan in plans.items():
            b=bindings[name]
            result[name]=dict(field=name,rank=rank,generation=generation,kind=b['kind'],
                version=b['version'],leased_versions=[b['version']],source_ranks=[rank],
                view_contract=b['native_address_view'],provenance_certified=False,data=None)
        try:
            for name,plan in plans.items():
                b=bindings[name];lo,hi=plan['source_word_interval']
                raw=np.empty(hi-lo,dtype='<u4');receipts=[]
                # 128 words per accepted fragment: I64 retains both ordered halves.
                for first in range(lo,hi,128):
                    words,loc,receipt=self.C0_source_views._read_words(b['version'],rank,
                        np.arange(first,min(first+128,hi),dtype=np.int64))
                    if receipt.get('software_reverse_drained') is not True:
                        raise ValueError('source fragment reverse not drained')
                    raw[first-lo:first-lo+len(words)]=words;receipts.append(receipt)
                data=raw.view(DTYPES[specs[name]['dtype']]).reshape(plan['shape'])
                data.flags.writeable=False
                result[name].update(data=data,provenance_certified=True,
                    source_binding=b,source_journal_spans=receipts,source_acquisition=plan,
                    hardware_qualified=False)
            return result
        except Exception:
            self.fullgraph_source_failed=True
            # Retain owners/evidence on refusal; no retry or partial release.
            raise


def buffer_writers(op,primary_writes):
    """Publish every declared source alias of this exact collective result."""
    if len(primary_writes)!=1:raise ValueError('exact primary source buffer writer required')
    primary=primary_writes[0]
    if primary not in op['writes']:raise ValueError('foreign primary buffer writer')
    view=primary['native_result_binding'];buffer=view.get('buffer')
    if buffer is None:raise ValueError('declared collective result buffer required')
    writers=[w for w in op['writes'] if w['native_result_binding'].get('buffer')==buffer]
    if any(w['native_result_binding']['result']!=view['result'] for w in writers):
        raise ValueError('collective alias result identity differs')
    if len({w['version'] for w in writers})!=len(writers):raise ValueError('duplicate source alias')
    return writers


class BufferPublicationMixin:
    """Opt-in fresh driver: same primitive result, all declared owned writers."""
    def run_buffer(self,op,owned,template,bindings,views,writes):
        if owned.get('buffer_programs'):
            candidates=[b for b in owned['buffer_programs'] if b['template']==template and
                len(writes)==1 and b['write_version']==writes[0]['version']]
            if len(candidates)!=1:raise ValueError('actual independent source buffer identity')
            writes=buffer_writers(op,writes)
        return super().run_buffer(op,owned,template,bindings,views,writes)


class VersionLeaseClosureMixin:
    """Retain actual specialist versions before acquisition, including primary.

    Older source-view records can declare additional_versions=[]; that must not
    erase the primary version lease. This adds owner bookkeeping, never ACKs.
    """
    def _read_one(self,op,owned,key,bindings,generation,collective=None):
        if not hasattr(self,'fullgraph_source_sha'):
            return super()._read_one(op,owned,key,bindings,generation,collective)
        if self.fullgraph_source_failed:raise ValueError('failed source acquisition; no retry')
        if generation!=self.generation:raise ValueError('source owner generation')
        selected={n:b for n,b in bindings.items() if n in ('route_weight','expert_outputs','query_codes','query_exp') and b['kind']=='versioned_operand'}
        if not selected:return super()._read_one(op,owned,key,bindings,generation,collective)
        guard={name:dict(version=b['version'],leased_versions=sorted({b['version'],*b.get('additional_versions',[])})) for name,b in selected.items()}
        guard_key=(op['pc'],owned['rank'],generation,id(guard))
        self.views[guard_key]=guard
        try:
            result=super()._read_one(op,owned,key,bindings,generation,collective)
            for name,v in guard.items():
                if name not in result:raise ValueError('source specialist failed to return actual leased view')
                result[name]['leased_versions']=v['leased_versions']
            self.views.pop(guard_key)
            return result
        except Exception:
            self.fullgraph_source_failed=True
            # Keep full producer owner set on failed reads, never grant by timestamp.
            raise
