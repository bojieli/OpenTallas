"""Opt-in connected source provider; no arithmetic callback or full GO implied.
Query/history precede Sagan's source reads in MRO so each owner keeps its codec.
All peer code is exact committed snapshot, with no hidden worktree import.
"""
import ast,hashlib,importlib.util,json,sys
from pathlib import Path
from h3_ds_checkpoint_provider_r34 import Provider as Original
from ds_hbm_collective_continuations_r37 import source_views_class
from ds_hbm_attention_views_r37 import AttentionViewsMixin
from ds_hbm_source_merge_r37 import SourceMergeMixin
from h3_ds_query_provider_r36 import QueryMixin
from h3_ds_history_provider_r36 import HistoryMixin
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002'

def peer(name):
    pins=json.loads((D/'peer_source_pins.json').read_bytes());path=D/'inputs'/(name+'.py')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=pins[str(path.relative_to(ROOT))]['sha256']:raise ValueError('immutable peer source pin')
    if name in sys.modules:
        m=sys.modules[name]
        if not hasattr(m,'__file__') or hashlib.sha256(Path(m.__file__).read_bytes()).hexdigest()!=pins[str(path.relative_to(ROOT))]['sha256']:raise ValueError('peer import collision')
        return m
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m
    try:
        # Load only committed peer dependency snapshots, before their imports.
        for node in ast.walk(ast.parse(path.read_bytes())):
            names=[node.module.split('.')[0]] if isinstance(node,ast.ImportFrom) and node.module else [n.name.split('.')[0] for n in node.names] if isinstance(node,ast.Import) else []
            for dep in names:
                if dep!=name and str((D/'inputs'/(dep+'.py')).relative_to(ROOT)) in pins:peer(dep)
        spec.loader.exec_module(m)
        if name=='h4_c0_model':
            def pinned(source_path,pin=None):
                catalog=json.loads((D/'metadata_source_catalog.json').read_bytes());key=pin+':'+source_path
                if key not in catalog:raise ValueError('unretained peer metadata dependency '+key)
                record=catalog[key];raw=(ROOT/record['path']).read_bytes()
                if hashlib.sha256(raw).hexdigest()!=record['sha256']:raise ValueError('peer metadata snapshot pin')
                return raw
            m.pinned=pinned
    except Exception:sys.modules.pop(name,None);raise
    return m

def composed_class(base=Original):
    pins=json.loads((ROOT/'results/uarch/ds_hbm_history_provider_r36_20261002/source_sha256.json').read_bytes())
    for path,want in pins.items():
        if path.startswith('tools/') and hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=want:raise ValueError('retained r36 provider dependency pin '+path)
    peer('h4_c0_producer_extents');peer('h4_c0_provider_movement');s=peer('h4_c0_ds_source_views')
    source=Path(base._read_one.__code__.co_filename)
    lower=s.provider_class(base,expected_provider_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    class Provider(AttentionViewsMixin,SourceMergeMixin,QueryMixin,HistoryMixin,lower):
        def __init__(self,manifest,native,dispatch,homes):
            super().__init__(manifest,native,dispatch,homes)
            canonical=json.dumps(native,sort_keys=True,separators=(',',':')).encode()
            self.engram_owners={}
            views=source_views_class(s.SourceViews,peer('h4_c0_producer_extents').collective_contract)
            self.C0_source_views=views(self,native_content_sha256=hashlib.sha256(canonical).hexdigest())
        def publish(self,identity,fields,source_store_view):
            op=self.native['instructions'][identity['PC']]
            ids=None
            if op['family']=='engram_fetch':
                import numpy as np
                template=next(r['template'] for r in op['rank_bindings'] if r['rank']==identity['rank'])
                b=op['provider_bindings'][template]['selected_row_ids'];record=self.bindings[f"{op['pc']}/{template}/selected_row_ids"]
                if record['source_binding']!=b or record['generation']!=identity['generation'] or record['checkpoint_revision']!=self.revision or identity['generation']!=self.generation:raise ValueError('accepted Engram row descriptor generation')
                ids=self._locked_auxiliary(record).check()
                if ids.dtype!=np.int64 or ids.shape!=(24,):raise ValueError('accepted source Engram IDs')
                prior=self.engram_owners.get(identity['version'])
                if prior is not None and (identity['rank'] in prior['ranks'] or not np.array_equal(ids,prior['ids']) or identity['generation']!=prior['generation']):raise ValueError('Engram duplicate/mixed row ownership')
            receipt=super().publish(identity,fields,source_store_view)
            if ids is not None:
                if receipt['pending_obligations'] or [e['event'] for e in receipt['events']]!=['software_backing_visible','consumer_accept','validated_reverse_grant']:raise ValueError('actual Engram owned writer completion')
                if identity['version'] not in self.engram_owners:
                    ids=ids.copy();ids.flags.writeable=False
                    self.engram_owners[identity['version']]=dict(version=identity['version'],ids=ids,generation=identity['generation'],ranks=set())
                self.engram_owners[identity['version']]['ranks'].add(identity['rank'])
            return receipt
        def release_version(self,version,generation):
            if version in self.engram_owners and self.engram_owners[version]['ranks']!=set(range(96)):raise ValueError('Engram writer rankset incomplete before release')
            super().release_version(version,generation)
            self.engram_owners.pop(version,None)
        def drain(self,generation):
            if any(row['ranks']!=set(range(96)) for row in self.engram_owners.values()):raise ValueError('partial Engram writer ownership retained')
            super().drain(generation)
            if self.C0_source_views.failed:raise ValueError('failed source bridge cannot complete token')
            self.C0_source_views.receipts.flush()
            return dict(generation=generation,pending_obligations=0,live_consumers=0)
    return Provider

def create_provider(manifest,native,dispatch,homes):
    if manifest.get('full_token_inputs_bound') is not True or manifest.get('full_token_GO') is not True:raise ValueError('full native input GO absent; prepared metadata is not numerical admission')
    return composed_class()(manifest,native,dispatch,homes)
