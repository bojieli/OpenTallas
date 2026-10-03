"""Source/control components; NONE qualifies released-checkpoint PC0-1 smoke."""
import json,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_remote_controller_r67 as R


def test_local_runtime_refused_before_allocation(tmp_path):
    plan=dict(host_alias='local')
    with pytest.raises(ValueError,match='remote host only'):
        R.fresh_admission(plan)
    assert not (tmp_path/'run').exists()


def test_exact_saved_bytes_and_mutant_without_golden():
    import numpy as np
    import ds_hbm_per_pc_r67 as P
    class H:
        @staticmethod
        def read_tree(v,payload):return v
    a=np.arange(16,dtype=np.float32)
    encoded={'array':[0,a.nbytes,a.dtype.str,list(a.shape),True]}
    P.exact_saved_tree(H,encoded,a,a.tobytes())
    wrong=a.copy();wrong[3]+=1
    with pytest.raises(ValueError,match='array bytes'):
        P.exact_saved_tree(H,encoded,wrong,a.tobytes())


def test_one_PC_child_calls_inherited_execute_and_guards_boundaries():
    import ast
    tree=ast.parse((ROOT/'tools/ds_hbm_per_pc_r67.py').read_text())
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    calls=[n for n in ast.walk(main) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='execute_operation']
    assert len(calls)==1 and ast.unparse(calls[0])=='e.execute_operation(op)'
    assert 'capture_atomic' in ast.unparse(main) and 'restore_cold' in ast.unparse(main)
    assert 'verify_actual_restore' in ast.unparse(main)


def test_actual_component_atomic_capture_and_restore_byte_comparison(tmp_path):
    # Original real finite provider component. It is NOT the production2213PC
    # checkpoint-backed NativeExecution and NOT an actual PC0-1 smoke receipt.
    import ast
    script=next(ast.literal_eval(n.value) for n in ast.parse((ROOT/'tests/test_ds_hbm_checkpointed_prefix_r55.py').read_text()).body
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SCRIPT' for t in n.targets))
    script=script.replace("receipt=C.capture_quiescent(e,p,w,boundary_pc=0,destination=dest,source_contract=contract)",
        "import ds_hbm_atomic_checkpoint_r67 as A\nresult=A.capture_atomic(C,e,p,w,boundary_pc=0,destination=dest,source_contract=contract,enabled=True)\nreceipt=result['checkpoint_receipt']")
    script=script.replace("assert restored['retired']==[0] and e2.retired=={0}",
        "import ds_hbm_per_pc_r67 as P\nproof=P.verify_actual_restore(C,dest,p2,e2)\nassert proof['actual_payload_exact'] and proof['retired_PCs']==[0]\nassert restored['retired']==[0] and e2.retired=={0}")
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path),'success'],cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


def test_physical_parent_RAM_refuses_despite_large_guest(tmp_path,monkeypatch):
    import time,hashlib
    price=dict(projection_complete=True,required_RAM_bytes=2000,required_disk_bytes=100)
    out=tmp_path/'run';proof=tmp_path/'parent.json';now=time.time_ns()
    proof.write_text(json.dumps(dict(reviewed=True,guest_alias='ot-pve1',
        source_projection_sha256=hashlib.sha256(R.canonical(price)).hexdigest(),
        measured_ns=now-1000000000,valid_until_ns=now+1000000000,
        MemAvailable_bytes=1999,other_owned_reservations_and_live_growth_bytes=0)))
    monkeypatch.setattr(R.socket,'gethostname',lambda:'ot-pve1')
    with pytest.raises(ValueError,match='physical-parent aggregate RAM'):
        R.fresh_admission(dict(host_alias='ot-pve1',output_root=str(out),resolved_output_root=str(out),resource_projection=price,physical_parent_admission=str(proof)))
    assert not out.exists()


def test_unenrolled_child_refuses_before_import_or_allocation(tmp_path):
    p=tmp_path/'plan.json';p.write_text('{}')
    with pytest.raises(ValueError,match='reviewed remote enrollment'):
        R.validate_child(p,0,False)


def test_changed_actual_input_refuses_enrollment(tmp_path):
    payload=tmp_path/'actual.bin';payload.write_bytes(b'actual')
    index=tmp_path/'index.json';index.write_text(json.dumps(dict(paths={str(payload):dict(bytes=6,sha256=R.sha(payload))},checkpoint_path=str(tmp_path))))
    plan=dict(immutable_input_index=str(index),immutable_input_index_sha256=R.sha(index))
    assert R.verify_inputs(plan)
    payload.write_bytes(b'oracle')
    with pytest.raises(ValueError,match='absent or changed'):R.verify_inputs(plan)
