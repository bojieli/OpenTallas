"""Bind missing native produced-state homes to already charged AW27 storage.
Only home_indices change; templates, operation arithmetic and view identity stay
exact. Original native and failed R39 source remain immutable.
"""
import copy, hashlib, json
from ds_hbm_finite_state_homes_r30 import compile_directory, patch_homes
from h3_ds_source_prefix_provider_r39 import validate_prefix
from h3_ds_connected_provider_r37 import composed_class

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(',',':')).encode()

def bind_storage(native, homes, manifest):
    directory = compile_directory(native, manifest['native_program_sha256'])
    intervals = {}
    def add(rank, base, length, owner):
        end=base+length
        if base<33554432 or end>67108864:raise ValueError('AW27 native state bounds '+owner)
        if any(base<b and a<end for a,b,_ in intervals.get(rank,[])):raise ValueError('native state reservation overlap '+owner)
        intervals.setdefault(rank,[]).append((base,end,owner))
    for r in directory['rows']:
        add(r['rank'],r['base'],r['reservation_bytes'],r['version'])
    for r in manifest['initial_versions']:
        if 'home' in r:
            h=r['home'];add(r['rank'],h['base'],h['reservation_bytes'],r['version'])
    for r in manifest['query_field_homes']['rows']:
        add(r['rank'],r['base'],r['reservation_bytes'],r['version']+'/'+r['field'])
    patched, expanded = patch_homes(native, copy.deepcopy(homes), directory)
    # A conservative word_count permits unchanged R39 sector projection for
    # new state homes; state publisher itself uses exact binding shape/bytes.
    for h in expanded[len(homes):]:h['word_count']=h['binding']['bytes']//4
    restored=copy.deepcopy(patched)
    for old,new in zip(native['instructions'],restored['instructions']):
        for a,b in zip(old['writes'],new['writes']):b['home_indices']=a['home_indices']
    if canonical(restored)!=canonical(native):raise ValueError('binding changed source arithmetic or identity')
    for op in patched['instructions']:
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'):continue
            for w in op['writes']:
                if not any(owned['rank'] in expanded[i]['rank_group'] for i in w['home_indices']):raise ValueError('native output lacks actual rank home')
    report=dict(status='SOURCE_HOME_BINDING_READY',missing_output='DeepSeek.5.window.L0.62',first_PC=5,
        all_state_home_records=len(directory['rows']),added_macro_or_capacity_bytes=0,
        produced_reserved_bytes_by_rank=directory['per_rank_reserved_bytes'],
        total_reserved_bytes_by_rank={str(r):sum(b-a for a,b,_ in v) for r,v in intervals.items()},
        max_reserved_end=max(b for v in intervals.values() for a,b,_ in v),
        effective_native_content_sha256=hashlib.sha256(canonical(patched)).hexdigest(),
        original_native_sha256=manifest['native_program_sha256'],arithmetic_unchanged=True,
        full_token_GO=False,hardware_qualified=False)
    return patched,expanded,directory,report

def bound_class():
    cls=composed_class()
    class Bound(cls):
        def publish(self,identity,fields,source_store_view):
            if identity['generation']!=self.generation:raise ValueError('publication generation')
            op=self.native['instructions'][identity['PC']]
            ws=[w for w in op['writes'] if w['version']==identity['version']]
            if len(ws)!=1 or ws[0]['native_result_binding']!=source_store_view:raise ValueError('exact native source output identity')
            expected=[i for i in ws[0]['home_indices'] if identity['rank'] in self.homes[i]['rank_group']]
            if not expected or expected!=identity['home_indices']:raise ValueError('exact allocated output home identity')
            if (identity['version'],identity['rank']) in self.locations:raise ValueError('duplicate native output publication')
            return super().publish(identity,fields,source_store_view)
    return Bound

def create_bound_provider(manifest,native,dispatch,homes,stop):
    validate_prefix(manifest,native,stop)
    return bound_class()(manifest,native,dispatch,homes)
