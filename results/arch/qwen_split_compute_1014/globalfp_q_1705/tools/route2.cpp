// GLOBAL-FP-Q timing-driven variant of the hybrid-capacity negotiated router (route.cpp).
// Same input/output format; extra argv[5] = critical-net file: "<net_index> <root_to_sink_step_limit>" per line.
// Critical nets (ME loop / layer loops) are routed FIRST in every pass, with a hard per-sink tree-depth limit in grid
// steps (stage-preserving detour bound) and a reduced congestion weight; all other nets negotiate around them.
// If a critical sink cannot be reached within its limit, it is routed unconstrained and reported (never hidden).
#include <bits/stdc++.h>
using namespace std;
struct Edge{int a,b,cap,use=0;double occ,hist=0;};
struct Net{int id,w;vector<int>t,edges;int lim=-1,add=0,maxadd=-1;};
struct Item{double f,g;int n;bool operator<(Item const&x)const{return f>x.f;}};
int main(int argc,char**argv){
 if(argc<6){cerr<<"usage: route2 in out passes acceptable critfile [critweight]"<<endl;return 2;}
 ifstream in(argv[1]);int nx,ny,E,K;double B;if(!(in>>nx>>ny>>B>>E>>K)){cerr<<"bad input"<<endl;return 2;}
 int N=nx*ny;vector<Edge>es(E);vector<vector<pair<int,int>>>adj(N);
 for(int i=0;i<E;i++){auto&e=es[i];in>>e.a>>e.b>>e.cap>>e.occ;adj[e.a].push_back({e.b,i});adj[e.b].push_back({e.a,i});}
 vector<Net>ns(K);for(auto&n:ns){int nt;in>>n.id>>n.w>>nt;n.t.resize(nt);for(auto&x:n.t)in>>x;}
 {ifstream cf(argv[5]);string line;while(getline(cf,line)){istringstream ss(line);int k,l,m=-1;if(!(ss>>k>>l))continue;ss>>m;if(k<0||k>=K){cerr<<"bad crit net"<<endl;return 2;}ns[k].lim=l;ns[k].maxadd=m;}}
 double cw=argc>6?atof(argv[6]):0.05;int maxadd=argc>7?atoi(argv[7]):0;
 vector<int>order;for(int k=0;k<K;k++)if(ns[k].lim>=0)order.push_back(k);int ncrit=order.size();for(int k=0;k<K;k++)if(ns[k].lim<0)order.push_back(k);
 vector<double>d(N);vector<int>pe(N),pn(N),stamp(N),tree(N),depth(N),st(N),own(E);int sid=0,tid=0,nid=0;double pf=5;
 int passes=atoi(argv[3]);double acceptable=atof(argv[4]);ofstream log(string(argv[2])+".log");
 long long limfail=0;
 for(int pass=0;pass<passes;pass++){
  int fails=0;limfail=0;auto begin=chrono::steady_clock::now();
  for(int nk:order){
   auto&net=ns[nk];bool crit=net.lim>=0;for(int e:net.edges)es[e].use-=net.w;net.edges.clear();++tid;++nid;
   bool blocked=false;for(int t:net.t){bool ok=false;for(auto[v,ei]:adj[t])if(es[ei].cap>=net.w){ok=true;break;}if(!ok)blocked=true;}
   if(blocked){fails++;continue;}
   vector<int>tn={net.t[0]};tree[net.t[0]]=tid;depth[net.t[0]]=0;bool failed=false;
   for(int target:net.t){if(tree[target]==tid)continue;
    auto heur=[&](int v){return abs(v/ny-target/ny)+abs(v%ny-target%ny);};
    bool hit=false;
    for(int attempt=0;attempt<2&&!hit;attempt++){
     bool limited=crit&&attempt==0;++sid;priority_queue<Item>q;
     for(int s:tn){if(limited&&depth[s]+heur(s)>net.lim+net.add)continue;stamp[s]=sid;d[s]=0;st[s]=depth[s];pe[s]=-1;pn[s]=-1;q.push({double(heur(s)),0,s});}
     while(!q.empty()){auto cur=q.top();q.pop();int u=cur.n;if(stamp[u]!=sid||cur.g>d[u]+1e-8)continue;if(u==target){hit=true;break;}
      for(auto[v,ei]:adj[u]){auto&e=es[ei];if(e.cap<net.w)continue;int sv=st[u]+1;if(limited&&sv+heur(v)>net.lim+net.add)continue;
       double rho=double(e.use+net.w)/e.cap;double over=max(0.0,rho-1);double cg=e.occ*.35+e.hist+pf*pow(rho,4)+pf*100*over*over;double cost=1+(crit?cw:1.0)*cg;double nd=cur.g+cost;
       if(stamp[v]!=sid||nd<d[v]-1e-8){stamp[v]=sid;d[v]=nd;st[v]=sv;pe[v]=ei;pn[v]=u;q.push({nd+heur(v),nd,v});}}
     }
     if(!hit&&limited)limfail++;
    }
    if(!hit){failed=true;break;}
    // walk back; assign depths from the attachment point outward
    vector<int>path;int u=target;while(pe[u]>=0){path.push_back(u);u=pn[u];}
    int base=depth[u];for(int i=(int)path.size()-1,s=1;i>=0;i--,s++){int v=path[i];int ei=pe[v];if(own[ei]!=nid){own[ei]=nid;net.edges.push_back(ei);}if(tree[v]!=tid){tree[v]=tid;depth[v]=base+s;tn.push_back(v);}}
   }
   for(int ei:net.edges)es[ei].use+=net.w;if(failed)fails++;
  }
  long long overflow=0;int bad=0;double worst=0;for(auto&e:es){if(e.cap){worst=max(worst,double(e.use)/e.cap);if(e.use>e.cap){overflow+=e.use-e.cap;bad++;e.hist+=double(e.use-e.cap)/e.cap*10;}}}
  long long relaxed=0;if(maxadd>0)for(auto&n:ns){if(n.lim<0||n.add>=(n.maxadd>=0?n.maxadd:maxadd))continue;for(int e:n.edges)if(es[e].use>es[e].cap){n.add++;relaxed++;break;}}
  double sec=chrono::duration<double>(chrono::steady_clock::now()-begin).count();
  log<<pass<<" failures "<<fails<<" overedges "<<bad<<" overflow "<<overflow<<" worst_gate_ratio "<<worst<<" crit_nets "<<ncrit<<" crit_limit_misses "<<limfail<<" relaxed "<<relaxed<<" seconds "<<sec<<endl;
  if(!fails&&worst<=acceptable)break;pf*=1.4;
 }
 ofstream o(argv[2]);o<<nx<<" "<<ny<<" "<<E<<" "<<K<<"\n";for(int k=0;k<K;k++){auto&n=ns[k];o<<k<<" "<<n.edges.size();for(int e:n.edges)o<<" "<<e;o<<"\n";}o<<"USES\n";for(int e=0;e<E;e++)o<<e<<" "<<es[e].use<<" "<<es[e].cap<<"\n";
}
