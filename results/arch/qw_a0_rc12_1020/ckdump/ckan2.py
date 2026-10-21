import sys,re,collections,statistics as st
place={}
for l in open(sys.argv[1]):
  r=l.split(); place[r[1].replace('\\','')]=(float(r[3]),float(r[4]))
def cls(n):
  for k in ('u_qlw2w','u_qlw2e','u_qlr1sw','u_qlr1nw','u_qlr1se','u_qlr1ne','mq_wrom','g_csel','g_tx9.tc','s2_w'):
    if k in n:
      m=re.search(r'g_sl\[(\d)\]',n)
      return k+(('.L'+m.group(1)) if m and k in('u_qlw2w','u_qlw2e','g_tx9.tc') else '')
  return 'other'
for f in sys.argv[2:]:
  C=collections.defaultdict(list); al=[]
  for l in open(f):
    pin,a=l.split(); a=float(a); n=pin.replace('\\','').rsplit('/',1)[0]
    xy=place.get(n,(float('nan'),)*2)
    C[cls(n)].append((a,)+xy); al.append(a)
  print(f,len(al),'all %.1f..%.1f spread %.1f'%(min(al),max(al),max(al)-min(al)))
  for k,v in sorted(C.items()):
    a=[x[0] for x in v]
    print('  %-20s n=%5d arr %6.1f..%6.1f med %6.1f  x %4.0f..%4.0f y %4.0f..%4.0f'%(k,len(v),min(a),max(a),st.median(a),min(x[1] for x in v),max(x[1] for x in v),min(x[2] for x in v),max(x[2] for x in v)))
