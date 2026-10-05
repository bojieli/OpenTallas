"""Default-off all-PC source enrollment; no constructor or execution GO.
Explicitly selects pinned TokenDriver nongroup kernels and typed addressed
views. Original prefix validator, MRO role proof and V3 restore remain intact.
"""
import hashlib,inspect,json
from pathlib import Path
from h3_ds_connected_provider_r37 import ROOT,peer
from ds_hbm_registered_loader_r57 import registered_sagan

RECORD=ROOT/'results/uarch/ds_hbm_fullscope_enrollment_r60_20261003'

def verify_sources():
    pins=json.loads((RECORD/'source_sha256.json').read_bytes())
    for path,want in pins.items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=want:
            raise ValueError('exact fullscope source changed: '+path)
    return pins


def source_classes(*,opt_in=False):
    if opt_in is not True:raise ValueError('fullscope source enrollment default off')
    verify_sources()
    from h4_c0_ds_runtime_bindings import TypedOperandViewsMixin,BufferPublicationMixin
    from ds_hbm_storage_home_binding_r41 import bound_class
    native=registered_sagan()
    class AddressedProvider(TypedOperandViewsMixin,bound_class()):
        pass
    class NativeDriver(BufferPublicationMixin,native.NativeExecution):
        pass
    # No cloned/edited numeric function. Alias publication is the reviewed
    # data-only mixin, then the literal original TokenDriver.run_buffer.
    driver=peer('h3_deepseek_full_token_driver')
    if NativeDriver.__mro__[2] is not native.NativeExecution or native.NativeExecution.run_buffer is not driver.TokenDriver.run_buffer:
        raise ValueError('literal nongroup kernel source identity required')
    for cls in (*AddressedProvider.__mro__,*NativeDriver.__mro__):
        if cls is not object:inspect.getsource(cls)  # source proof must resolve.
    return AddressedProvider,NativeDriver


def composed_engine_class(*,opt_in=False):
    _,driver=source_classes(opt_in=opt_in)
    from ds_hbm_additive_endpoint_join_r54 import engine_class
    return engine_class(driver,finite_pc10=True,retire_unconsumed=True)


def validate_scope_request(contract,retired):
    # External controller only; no run-scope fields in provider/engine bodies.
    if type(contract.get('first_PC')) is not int or type(contract.get('last_PC')) is not int:
        raise ValueError('exact finite PC scope required')
    first,last=contract['first_PC'],contract['last_PC']
    if not 11<=first<=last<2213 or sorted(retired)!=list(range(first)):
        raise ValueError('actual contiguous producer retirement required')
    if contract.get('native_program_sha256')!='c65a584c1b1cfafcd00391af216870136a44ec142b0d11106df570db7b8eb264':
        raise ValueError('original complete native source required')
    if contract.get('actual_payload_checkpoint_verified') is not True or contract.get('sealed_journal_inventory_verified') is not True:
        raise ValueError('actual producer bytes and immutable journals required')
    if contract.get('source_class_transition_verified') is not True:
        raise ValueError('explicit exact source-class transition proof required; V3 exemptions forbidden')
    costs=contract.get('complete_resource_projection',{})
    required=('fresh_sector_journal_bytes','codec_publication_witness_bytes','checkpoint_metadata_bytes','old_plus_cold_RAM_bytes')
    if any(type(costs.get(k)) is not int or costs[k]<=0 for k in required):
        raise ValueError('complete positive source-sized resources required; component price is not GO')
    if contract.get('constructor_GO') is not True:raise ValueError('complete source/resource constructor admission required')
    return first,last


def construct_scope_provider(contract,retired,manifest,native,dispatch,homes):
    # Never called by this preparation milestone. All preconditions are checked
    # before the actual unchanged checkpoint/provider constructor is invoked.
    validate_scope_request(contract,retired)
    cls,_=source_classes(opt_in=True)
    # Validate complete unchanged arithmetic/dispatch and every regenerated home
    # BEFORE checkpoint locks or port allocation. Scope extension is external.
    from ds_hbm_connected_prepare_r37 import load,sha
    from ds_hbm_storage_home_binding_r41 import bind_storage,canonical
    from h3_ds_connected_provider_r37 import D
    npath=ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz'
    dpath=ROOT/'results/uarch/ds_hbm_bound_engine_r43_20261002/inputs/actual_dispatch_bcf.json.gz'
    if sha(npath)!=contract['native_program_sha256'] or sha(dpath)!=manifest['source_dispatch_sha256']:
        raise ValueError('exact original native and dispatch artifact pins required')
    original=load(npath);original_homes=load(D/'inputs/actual_DeepSeek_homes.json.gz')['homes']
    expected,owned,_,proof=bind_storage(original,original_homes,manifest)
    if canonical(native)!=canonical(expected) or canonical(homes)!=canonical(owned) or canonical(dispatch)!=canonical(load(dpath)):
        raise ValueError('only-home-indices complete native/directory/dispatch regeneration required')
    if len(native['instructions'])!=2213 or len({o['family'] for o in native['instructions']})!=30:
        raise ValueError('all2213PC/30family source required')
    if not proof['arithmetic_unchanged']:raise ValueError('native arithmetic lineage differs')
    provider=cls(manifest,native,dispatch,homes)
    provider.enable_fullgraph_typed_views(native_content_sha256=hashlib.sha256(
        json.dumps(native,sort_keys=True,separators=(',',':')).encode()).hexdigest())
    return provider
