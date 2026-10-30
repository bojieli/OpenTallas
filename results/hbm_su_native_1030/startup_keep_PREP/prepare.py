from pathlib import Path
import re,json,hashlib
R=Path(__file__).resolve().parents[3];B=R/'physical/die_plan/hbm_arch_cores';O=R/'results/hbm_su_native_1030/startup_keep_PREP';O.mkdir(exist_ok=True);(O/'rtl').mkdir(exist_ok=True)
SUFFIX='__su_startup_keep1030';rows=[]
def inst(s,old,name):
 hits=[]
 for m in re.finditer(r'\b'+old+r'\b',s):
  pos=m.end()
  while s[pos].isspace():pos+=1
  if s[pos]=='#':
   pos+=1
   while s[pos].isspace():pos+=1
   assert s[pos]=='(';level=0
   while pos<len(s):
    c=s[pos];pos+=1
    if c=='(':level+=1
    if c==')':
     level-=1
     if level==0:break
  n=re.match(r'\s*(\w+)\s*\(',s[pos:])
  if n and n[1]==name:hits.append(m.span())
 assert len(hits)==1,(old,name,len(hits))
 a,b=hits[0];return s[:a]+old+SUFFIX+s[b:]
def make(old,edges=(),addition=None,folder='native_1030'):
 p=B/folder/(old+'.sv');s=p.read_text();orig=s;s=s.replace('module '+old,'module '+old+SUFFIX,1)
 for child,i in edges:s=inst(s,child,i)
 if addition:
  before,after=addition;assert s.count(before)==1;s=s.replace(before,after)
 (O/'rtl'/(old+SUFFIX+'.sv')).write_text(s)
 norm=s.replace(SUFFIX,'')
 if addition:norm=norm.replace(addition[1],addition[0])
 assert norm==orig
 rows.append(dict(original=old,specialized=old+SUFFIX,source=str(p.relative_to(R)),original_sha256=hashlib.sha256(orig.encode()).hexdigest(),specialized_sha256=hashlib.sha256(s.encode()).hexdigest(),only_changes='module/child names plus onebit KEEP alias where declared',edges=list(edges),has_keep_alias=bool(addition)))
make('ot_hdc_delay',addition=('reg [W*D-1:0] line;','reg [W*D-1:0] line;\n        if (W == 32 && D == 4) begin : g_startup_preserve\n          (* keep = 1 *) wire [3:0] startup_bits = {line[126],line[94],line[62],line[30]};\n        end'))
make('ot_hdc_w11_cut',addition=('reg [W-1:0] rd;','reg [W-1:0] rd;\n        if (W == 120) begin : g_startup_preserve\n          (* keep = 1 *) wire startup_bit = rd[71];\n        end'))
make('ot_hdc_fp32_add_lat',[('ot_hdc_w11_cut','u_ca')])
make('ot_hdc_fp32_add_lat4i',[('ot_hdc_fp32_add_lat','u')])
make('ot_hdc_qadd_lat',[('ot_hdc_fp32_add_lat4i','u')])
make('ot_hdc_v41x_exp',[('ot_hdc_delay','d_lo'),('ot_hdc_qadd_lat','a_r')],addition=('reg [31:0] a_hi, a_lo;', 'reg [31:0] a_hi, a_lo;\n    (* keep = 1 *) wire startup_lo30 = a_lo[30];'))
make('ot_hbm_su_static_lane',[('ot_hdc_v41x_exp','u_exp')])
make('ot_hbm_su_static_lane_pinreg__static_id',[('ot_hbm_su_static_lane','u_lane')],folder='id_1030')
make('ot_hnx_su_exp__rst3__static_id',[('ot_hbm_su_static_lane_pinreg__static_id','m1')],folder='id_1030')
(O/'graph_identity.json').write_text(json.dumps(dict(status='SOURCE_PREP_NORMALIZED_GRAPH_IDENTICAL',no_logic_or_reset_or_cycle_changes=True,physical_adoption=False,rows=rows),indent=2)+'\n')
print('PREP',len(rows),'module copies; exactly6 startup bits in 3 KEEP aliases; normalized graph identical')
