import re,json,gzip,pathlib,itertools,hashlib
P=pathlib.Path(__file__).parent

def blocks(s,k):
 for m in re.finditer(r'\b'+k+r'\s*\(([^)]*)\)\s*\{',s):
  i=m.end();a=i;d=1
  while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
  yield m[1].strip('" '),s[a:i-1]
def scalar(s,k):
 m=re.search(r'\b'+k+r'\s*:\s*(-?[\d.]+(?:e[-+]?\d+)?)',s,re.I);return float(m[1]) if m else None
def vec(s,k):return [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?',re.search(k+r'\s*\((.*?)\);',s,re.S)[1],re.I)]
def interp(t,x,y):
 xs,ys=t['x'],t['y'];assert xs[0]<=x<=xs[-1] and ys[0]<=y<=ys[-1],(x,y,xs,ys)
 i=min(len(xs)-2,max(0,next((j-1 for j,z in enumerate(xs) if z>=x),len(xs)-2)));j=min(len(ys)-2,max(0,next((j-1 for j,z in enumerate(ys) if z>=y),len(ys)-2)))
 a=(x-xs[i])/(xs[i+1]-xs[i]);b=(y-ys[j])/(ys[j+1]-ys[j]);v=t['v'];w=len(ys)
 return (1-a)*((1-b)*v[i*w+j]+b*v[i*w+j+1])+a*((1-b)*v[(i+1)*w+j]+b*v[(i+1)*w+j+1])
def ranges(c,inp,load):return {k:[min(interp(t,x,y) for x,y in itertools.product(inp,load)),max(interp(t,x,y) for x,y in itertools.product(inp,load))] for k,t in c['tables'].items()}
