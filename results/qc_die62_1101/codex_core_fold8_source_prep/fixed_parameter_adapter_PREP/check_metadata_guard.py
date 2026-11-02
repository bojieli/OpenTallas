"""Finite existing-serializer contract exercise; no Yosys/RTL/view qualification."""
import json,gzip,sys,pathlib,copy,argparse
p=argparse.ArgumentParser();p.add_argument('--tools-root',required=True);p.add_argument('--actual-source-graph',required=True);a=p.parse_args();sys.path.insert(0,str(pathlib.Path(a.tools_root)/'tools/die_plan'));import native_bb as BB
here=pathlib.Path(__file__).resolve().parent;hp=BB.headers_params([here/'ot_coll_fold_slice_bb.v']);assert hp['ot_coll_fold_slice']=={'N':('int',4),'ADD_LAT':('int',7),'SEAM':('int',1)}
g=json.load(gzip.open(a.actual_source_graph));fs=[m for m in g['macro_nodes'].values()if m['type']=='ot_coll_fold_slice'];assert len(fs)==8
expected={'clk':1,'rst_n':1,'red_in':1,'src':512,'sum':128,'v_out':1,'e_out':1}
for f in fs:assert {p:len(b)for p,b in f['connections'].items()}==expected
# Literal contract values below are fixture inputs; actual uncanonicalized
# source override/default resolution remains required before any cut adoption.
rows=[('ot_coll_fold_slice','fixture_top',f['name'],k,'1',format(v,'032b'))for f in fs for k,v in [('N',4),('ADD_LAT',7),('SEAM',1)]]
ys,rep,err=BB.plan(rows,hp);assert not err;bad=[]
for key,value in [('N',8),('ADD_LAT',8),('SEAM',0),('N',None)]:
 rr=copy.deepcopy(rows);i=next(i for i,r in enumerate(rr)if r[3]==key);row=list(rr[i]);row[5]='x'*32 if value is None else format(value,'032b');rr[i]=tuple(row);_,_,e=BB.plan(rr,hp);assert e;bad.append({'parameter':key,'mutant_value':value,'refused':e})
out={'status':'PYTHON_METADATA_GUARD_PREP_ONLY_NOT_ELAB_OR_EQUIVALENCE','actual_retained_instances':len(fs),'actual_all8_ABI_widths':expected,'declared_fixed_profile':{'N':4,'ADD_LAT':7,'SEAM':1},'equal_profile_fixture_serializer_report':rep,'mutant_refusals':bad,'ys_preview':ys,'no_shared_tool_modification':True,'no_source_substitution':True,'unqualified':['Actual8instanceparameter/defaultresolution beforecut','NativeYosysmetadata/hierarchy gate notrun','Currentfunction/reset/clock/viewqualification and fixedhardmasterphysicalABI notclosed']};(here/'METADATA_GUARD_RECEIPT.json').write_text(json.dumps(out,indent=2)+'\n');print(out['status'],len(fs),'ABIchecked;4invalidfixturesrefused')
