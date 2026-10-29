import sys, json
V=json.loads(sys.argv[1]); sys.argv=['x','lanes.json','rows103.json','rows_h8b.json']
import replan_est as R
rect=R.apply_rows({'A':V[0],'C':V[1]})
s=R.score(rect)
moved=[n for n in V[0]+V[1] if abs(rect[n][0]-R.rect0[n][0])>0.01]
print({k:v for k,v in s.items() if k!='edge_over'}, 'edge_over',s['edge_over'])
print('moved NW',len(moved),moved)
for n in V[0]+V[1]: print('  ',n, rect[n][0], '->', round(rect[n][0]+rect[n][2],2))
R.score(rect,verbose=True,only=('FAR','NEAR'))
