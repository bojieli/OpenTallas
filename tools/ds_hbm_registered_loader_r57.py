"""Default-off source-verified R39 module enrollment before execution.
Original loaders, classes and scope-role proof remain byte-identical.
"""
import hashlib,importlib.util,importlib.machinery,inspect,sys
from pathlib import Path
from h3_ds_connected_provider_r37 import ROOT,peer
NAME='Sagan_committed_r39'
SOURCE=ROOT/'results/uarch/ds_hbm_source_prefix_r39_20261002/inputs/h4_c0_ds_native_execution.py.source'
SHA='2ef4c0ea75bfe1781b58de80346bb6518e9e8bf807e095135e817d189e63bd8e'

def registered_sagan():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SHA:
        raise ValueError('exact retained NativeExecution source required')
    for name in ('h3_deepseek_full_token_driver','h4_c0_ds_tiled_continuation','h4_c0_ds_expected_outputs'):peer(name)
    if NAME in sys.modules:
        m=sys.modules[NAME]
        if Path(m.__file__).resolve()!=SOURCE.resolve() or getattr(m,'_r57_source_sha',None)!=SHA:
            raise ValueError('conflicting NativeExecution module identity')
        if inspect.getmodule(m.NativeExecution) is not m:
            raise ValueError('class module enrollment differs')
        return m
    spec=importlib.util.spec_from_file_location(NAME,SOURCE,loader=importlib.machinery.SourceFileLoader(NAME,str(SOURCE)))
    m=importlib.util.module_from_spec(spec)
    sys.modules[NAME]=m  # Python import contract: enroll BEFORE exec/class construction.
    try:
        spec.loader.exec_module(m)
        m._r57_source_sha=SHA
        if inspect.getmodule(m.NativeExecution) is not m or Path(inspect.getsourcefile(m.NativeExecution)).resolve()!=SOURCE.resolve():
            raise ValueError('exact class source identity required')
        if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SHA:raise ValueError('source changed during load')
    except BaseException:
        if sys.modules.get(NAME) is m:del sys.modules[NAME]
        raise
    return m

def install():
    import ds_hbm_source_prefix_r39 as a
    import ds_hbm_source_prefix_r43 as b
    import ds_hbm_source_prefix_r45 as c
    import json
    pins=json.loads((ROOT/'results/uarch/ds_hbm_registered_loader_r57_20261003/loader_original_pins.json').read_bytes())
    for module in (a,b,c):
        if hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()!=pins[Path(module.__file__).name]:
            raise ValueError('original loader source differs')
        if module.sagan.__module__!=module.__name__:raise ValueError('loader already substituted')
    # Explicit opt-in adapter; only loader selection changes. Driver bodies,
    # constructors, inherited execute/run and scope proof remain original.
    for module in (a,b,c):module.sagan=registered_sagan
    return {'source_sha256':SHA,'module':NAME,'registered_before_exec':True}
