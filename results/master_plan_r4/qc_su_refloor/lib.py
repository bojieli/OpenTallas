import re,sys
def cells(path,names):
  t=open(path).read();out={}
  for n in names:
    i=t.find('cell (%s)'%n)
    if i<0: i=t.find('cell ("%s")'%n)
    j=t.find('\n  cell (',i+10); blk=t[i:j if j>0 else None]
    cap=float(re.search(r'pin \(A\)\s*\{[^}]*?capacitance : ([\d.]+)',blk,re.S).group(1))
    def tab(kind):
      m=re.search(kind+r' \(\w+\) \{\s*index_1 \("([^"]+)"\);\s*index_2 \("([^"]+)"\);\s*values \((.*?)\);',blk,re.S)
      i1=[float(x) for x in m.group(1).split(',')];i2=[float(x) for x in m.group(2).split(',')]
      rows=[[float(x) for x in r.split(',')] for r in re.findall(r'"([^"]+)"',m.group(3))]
      return i1,i2,rows
    out[n]=dict(cin=cap,rise=tab('cell_rise'),fall=tab('cell_fall'),trise=tab('rise_transition'))
  return out
if __name__=='__main__':
  for c,v in cells(sys.argv[1],sys.argv[2:]).items():
    i1,i2,r=v['rise'];print(c,'cin',v['cin'],'slew',i1[:4],'load',i2);print(' d@slew1',r[1]);print(' tr@slew1',v['trise'][2][1])
