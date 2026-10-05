"""Default explicit r36 history adapter over actual r34 writer/read endpoints.
Sagan owns producer extent/sparse/ordered views: compose this mixin above that
provider when reviewed, without changing either owner's source files.
"""
import numpy as np
from h3_ds_checkpoint_provider_r34 import Provider as Base
from ds_hbm_history_store_r36 import History
from ds_hbm_history_codec_r36 import encode

class HistoryMixin:
    def __init__(self,manifest,*args):
        super().__init__(manifest,*args)
        receipt=manifest['history_source_receipt']
        if receipt['status']!='PASS_EXACT_ENTERING_STATE_DIGEST' or receipt['actual_state_sha256']!=receipt['expected_state_sha256'] or receipt['actual_state_sha256']!='b59a99c8294625778d28306924067d5bbf706979068579280d6ee40cb24e6782':raise ValueError('verified complete source history digest required')
        self.history=History(manifest['history_images'],manifest['generation']);self.history_view_leases={}

    def publish(self,identity,fields,source_store_view):
        ops=[o for o in self.native['instructions'] if o['pc']==identity['PC']]
        if len(ops)!=1:raise ValueError('unique source writer PC')
        op=ops[0];writes=[w for w in op['writes'] if w['version']==identity['version']]
        if len(writes)!=1:raise ValueError('exact source writer version')
        w=writes[0];extent=w.get('producer_extent');append=op['family']=='compressor' and isinstance(extent,dict) and 'append_global_group' in extent
        if append:
            if set(fields)!={'data'}:raise ValueError('source append data only')
            layer=op['source_op']['layer'];kind=1 if '.compressed.L' in identity['version'] else 2 if '.index_keys.L' in identity['version'] else None;group=extent['append_global_group'];row=fields['data']
            if kind is None or op['source_op']['group']!=group:raise ValueError('source compressor paired version/group')
            self.history.prevalidate(layer,kind,group,identity['version'],identity['generation'],identity['rank'],row)
            # Codec refuses unsupported payload BEFORE source backing mutation.
            encode(row.reshape(1,-1),'FP4E4' if kind==1 else 'FP4E8')
        receipt=super().publish(identity,fields,source_store_view)
        if append:self.history.accept(layer,kind,group,identity['version'],identity['generation'],identity['rank'],row,receipt)
        return receipt

    def _read_one(self,op,owned,key,bindings,generation,collective=None):
        special={'keys','key_codes','key_exp'} if op['family']=='index_scores' else {'selected_ckv_codes','selected_ckv_scales','selected_row_ids'} if op['family']=='kv_gather' else set()
        if not special.intersection(bindings):return super()._read_one(op,owned,key,bindings,generation,collective)
        remaining={n:b for n,b in bindings.items() if n not in special};result=super()._read_one(op,owned,key,remaining,generation,collective)
        view_key=(op['pc'],owned['rank'],generation,id(result));leases=[]
        try:
            layer=op['source_op']['src'];rank=owned['rank']
            if op['family']=='index_scores':
                n=op['source_op']['n'];blocks=np.arange(rank,(n+7)//8,96,dtype=np.int64);ids=(blocks[:,None]*8+np.arange(8,dtype=np.int64)).reshape(-1);ids=ids[ids<n];version=bindings['keys']['version'];kind=2
            else:
                ids=result['sel']['data'];versions=bindings['selected_ckv_codes']['identity_from_versions']
                if versions[0]!=result['sel']['version'] or versions!=bindings['selected_ckv_scales']['identity_from_versions'] or versions!=bindings['selected_row_ids']['identity_from_versions']:raise ValueError('selected descriptors and paired history identity')
                version=versions[1];kind=1
            rows,lease=self.history.read(layer,kind,ids,version,generation);leases.append((lease,version,generation))
            packed,scales=encode(rows,'FP4E4' if kind==1 else 'FP4E8');arrays={'selected_ckv_codes':packed,'selected_ckv_scales':scales,'selected_row_ids':ids} if kind==1 else {'keys':rows,'key_codes':packed,'key_exp':scales}
            for name,a in arrays.items():
                spec=self.native['templates'][key]['providers'][name]
                if list(a.shape)!=spec['shape'] or a.dtype!={'F32':np.float32,'U32':np.uint32,'I64':np.int64}[spec['dtype']]:raise ValueError('exact dynamic history LOAD shape/type '+name)
                a=a.view();a.flags.writeable=False
                result[name]=dict(field=name,rank=rank,generation=generation,kind=bindings[name]['kind'],data=a,version=version,source_binding=bindings[name],leased_versions=[version],source_ranks=sorted(set(((ids//8)%96).tolist())),provenance_certified=True)
            self.history_view_leases[id(result)]=leases
            return result
        except Exception:
            for lease,v,g in leases:self.history.release(lease,v,g)
            self.views.pop(view_key,None)
            raise

    def release_views(self,pc,rank,generation,views):
        # Existing provider validates full view identity before changing leases.
        super().release_views(pc,rank,generation,views)
        for lease,v,g in self.history_view_leases.pop(id(views),[]):self.history.release(lease,v,g)

class Provider(HistoryMixin,Base):pass

def create_provider(manifest,native,dispatch,homes):return Provider(manifest,native,dispatch,homes)
