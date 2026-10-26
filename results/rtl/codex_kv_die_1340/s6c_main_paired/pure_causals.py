
import os,sys,json
sys.path.insert(0,'tools/qwen_kv_die')
import kv_grp_safe2 as G
checks=[]
def yes(label,fn):
 assert fn(),label;checks.append(label)
def no(label,fn):
 try:fn()
 except ValueError:checks.append(label);return
 raise AssertionError(label+' accepted')
g=G.MASTERS['grp'];h=G.MASTERS['grp_h']
parent=lambda m,est='a[0:0]',ctl='c[193:0]':m+' u (.x__est('+est+'), .i_ctl('+ctl+'));'
yes('actual selected master identity',lambda:G.MASTERS==({'grp':'qkd_kvs_grp_s6c','grp_h':'qkd_kvs_grp_h_s6c'}if os.getenv('OT_KV_GRP_S6C')=='1'else{'grp':'qkd_kvs_grp_s2','grp_h':'qkd_kvs_grp_h_s2'}))
yes('real selected private slice',lambda:G.frame_port_widths(h,{'x__est':13,'i_ctl':271,'untouched':7},parent(h))=={'x__est':1,'i_ctl':194,'untouched':7})
yes('already private frame idempotent',lambda:G.frame_port_widths(g,{'x__est':1},parent(g))=={'x__est':1})
no('wrong frame refused',lambda:G.frame_port_widths(g,{'x__est':12},parent(g)))
no('missing frame port refused',lambda:G.frame_port_widths(g,{},parent(g)))
no('unsliced EST refused',lambda:G.frame_port_widths(g,{'x__est':13},parent(g,est='a')))
no('unsliced HCTL refused',lambda:G.frame_port_widths(h,{'x__est':13,'i_ctl':271},parent(h,ctl='c')))
no('wrong private HCTL cut refused',lambda:G.frame_port_widths(h,{'x__est':13,'i_ctl':271},parent(h,ctl='c[194:0]')))
no('missing actual instance refused',lambda:G.frame_port_widths(g,{'x__est':13},''))
d={'x__est':13,'i_ctl':271}
yes('unselected/default master unchanged',lambda:G.frame_port_widths('qkd_kvs_grp',d,'')is d)
print(json.dumps({'checks':checks,'count':len(checks),'verdict':'PASS'}))
