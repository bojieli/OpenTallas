"""Fail closed on restored source profiles for a saved-case physical diagnosis."""
import hashlib,json,os,re,sys
from decimal import Decimal
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def validate(root):
 root=Path(root).resolve();c=json.loads((root/'physical_profile_contract.json').read_text())
 for key,value in c['expected_environment'].items():
  if os.environ.get(key)!=value:raise ValueError('missing/wrong original physical environment: '+key)
 for rel,digest in c['sha256'].items():
  p=(root/rel).resolve()
  if not p.is_relative_to(root) or sha(p)!=digest:raise ValueError('physical profile provenance differs: '+rel)
 run=(root/'original_gen_contract/run.sh').read_text()
 for token in ('OT_SPLIT_PHY_TALL=1','OT_SPLIT_PHY_NFACE=1','OT_SPLIT_UCIE_PHY_CLK=${UCIE_PHY_CLK:-1}'):
  if token not in run:raise ValueError('original GEN flag evidence absent: '+token)
 selector=Path(os.environ.get('OT_BIND_VIEW_SELECT','')).resolve()
 if selector!=root/'physical_view_select.json':raise ValueError('explicit source profile selector absent/differs')
 views=json.loads(selector.read_text())['views'];emitted=(root/'out/case/elements.lef').read_text()
 for master,row in c['profiles'].items():
  if views.get(master)!=row['directory']:raise ValueError('source profile fallback prohibited: '+master)
  lef=(root/'src'/row['directory']/(master+'.lef')).read_text()
  def block(t):
   hits=re.findall(r'(?ms)^MACRO '+re.escape(master)+r'\n.*?^END '+re.escape(master)+r'\s*$',t)
   if len(hits)!=1:raise ValueError('actual same-master PHY absent/duplicate: '+master)
   return hits[0]
  source=block(lef);actual=block(emitted)
  def size(t):return tuple(map(Decimal,re.search(r'SIZE ([\d.]+) BY ([\d.]+)',t).groups()))
  if size(source)!=size(actual):raise ValueError('actual PHY outline mismatch: '+master)
  for pin in ('VDD','VSS'):
   p=re.search(r'(?ms)^  PIN '+pin+r'\n.*?^  END '+pin+r'\s*$',source)
   if not p or set(re.findall(r'LAYER (\w+)',p[0]))!={'M4'}:raise ValueError('actual M4 source power profile required: '+master+'.'+pin)
  if row.get('requires_lclk') and not re.search(r'\bPIN lclk\b',source):raise ValueError('actual modeled lclk absent')
 return {'status':'EXACT_ORIGINAL_PHY_PROFILE_IDENTITY_PASS','scope':'source profile/environment only; ASSUMED analog/PG/native clock insertion/package qualifications remain separate','profiles':list(c['profiles']),'native_R_inferred':False,'original_GEN_exit':1,'compiler':'FAIL','release_eligible':False}
if __name__=='__main__':
 try:print(json.dumps(validate(sys.argv[1]),indent=2))
 except (ValueError,OSError,KeyError)as e:raise SystemExit(str(e))
