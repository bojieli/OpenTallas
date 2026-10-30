"""Small direct Tcl guard controls; no EDA or placement commands are invoked."""
from pathlib import Path
import importlib.util,tkinter
base=Path(__file__).parent
spec=importlib.util.spec_from_file_location('prep',base/'prepare_recipe.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
t=tkinter.Tcl();packet=prep.read_packet(base/'native_candidate.json.gz');t.eval(prep.data(packet))
assert int(t.call('dict','size',t.getvar('ln_pf_ffs')))==8386
assert int(t.call('dict','size',t.getvar('ln_pf_targets')))==109
code=(base/'ln_postff_home.tcl').read_text();assert t.call('info','complete',code)==1
t.eval(code.replace('source /work/ln_postff_data.tcl','',1))
# One real-data-shaped native interface controls master/home/orient/root checks.
master='DFFHQNx1_ASAP7_75t_R';state=dict(master=master,orient='R0',clock='N',x=1000)
objects={'B':{'findInst':'I','findBTerm':'P'},'I':{'getMaster':'M','findITerm':'C','getBBox':'R'},'M':{},'P':{'getNet':'N'},'C':{},'R':{'yMin':2000,'xMax':2080,'yMax':2270}}
def dispatch(obj,method,*args):
    if (obj,method)==('M','getName'):return state['master']
    if (obj,method)==('I','getOrient'):return state['orient']
    if (obj,method)==('C','getNet'):return state['clock']
    if (obj,method)==('R','xMin'):return state['x']
    return objects[obj][method]
t.createcommand('dispatch',dispatch)
for obj in objects:t.eval(f'interp alias {{}} {obj} {{}} dispatch {obj}')
t.eval('proc ln_pf_context {} {return B};set ::ln_pf_ffs {}')
t.call('dict','set','::ln_pf_ffs','ff',t.call('list',master,'R0',1000,2000,2080,2270,'ck_k'))
t.call('ln_pf_check_ffs',1)
for field,bad,reason in [('master','DFFHQNx2_ASAP7_75t_R','master changed'),('orient','MX','orientation changed'),('clock','OTHER','clock changed'),('x',999,'orientation changed')]:
    old=state[field];state[field]=bad
    try:t.call('ln_pf_check_ffs',1)
    except tkinter.TclError as error:assert reason in str(error)
    else:raise AssertionError('guard accepted '+field)
    state[field]=old
print('LN_POSTFF Tcl data8386/109 + master/home/orient/clock negative controls PASS')
# Existing execution trace resolves the wrapped callback by name after rename.
t.eval('set ::events {};proc global_placement args {};proc affinity {command op} {lappend ::events old};trace add execution global_placement enter affinity;rename affinity affinity_base;proc affinity {command op} {affinity_base $command $op;lappend ::events exact_postFF};global_placement')
assert t.splitlist(t.getvar('events'))==('old','exact_postFF')
print('EXISTING_GPL_CALLBACK_THEN_EXACT_HOME_PREP_ORDER_PASS')
