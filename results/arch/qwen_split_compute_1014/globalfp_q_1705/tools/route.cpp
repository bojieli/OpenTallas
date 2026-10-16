#include <bits/stdc++.h>
using namespace std;
struct Edge{int a,b,cap,use=0;double occ,hist=0;};
struct Net{int id,w;vector<int>t,edges;};
struct Item{double f,g;int n;bool operator<(Item const&x)const{return f>x.f;}};
int main(int argc,char**argv){ifstream in(argv[1]);int nx,ny,E,K;double B;if(!(in>>nx>>ny>>B>>E>>K)||nx<1||ny<1||E<1||K<1){cerr<<"Missing or invalid route input"<<endl;return 2;}int N=nx*ny;vector<Edge>es(E);vector<vector<pair<int,int>>>adj(N);for(int i=0;i<E;i++){auto&e=es[i];in>>e.a>>e.b>>e.cap>>e.occ;adj[e.a].push_back({e.b,i});adj[e.b].push_back({e.a,i});}vector<Net>ns(K);for(auto&n:ns){int nt;in>>n.id>>n.w>>nt;n.t.resize(nt);for(auto&x:n.t)in>>x;}
vector<double>d(N);vector<int>pe(N),pn(N),stamp(N),tree(N),own(E);int sid=0,tid=0,nid=0;double pf=5;int passes=argc>3?atoi(argv[3]):15;double acceptable=argc>4?atof(argv[4]):1.0;ofstream log(string(argv[2])+".log");
for(int pass=0;pass<passes;pass++){
 int fails=0;auto begin=chrono::steady_clock::now();
 for(int nk=0;nk<K;nk++){
  auto&net=ns[nk];for(int e:net.edges)es[e].use-=net.w;net.edges.clear();++tid;++nid;bool blocked=false;for(int t:net.t){bool ok=false;for(auto[v,ei]:adj[t])if(es[ei].cap>=net.w){ok=true;break;}if(!ok)blocked=true;}if(blocked){fails++;continue;}vector<int>tn={net.t[0]};tree[net.t[0]]=tid;bool failed=false;
  for(int target:net.t){if(tree[target]==tid)continue;++sid;priority_queue<Item>q;
   auto heur=[&](int v){return abs(v/ny-target/ny)+abs(v%ny-target%ny);};
   for(int s:tn){stamp[s]=sid;d[s]=0;pe[s]=-1;pn[s]=-1;q.push({double(heur(s)),0,s});}
   bool hit=false;
   while(!q.empty()){auto cur=q.top();q.pop();int u=cur.n;if(stamp[u]!=sid||cur.g>d[u]+1e-8)continue;if(u==target){hit=true;break;}
    for(auto[v,ei]:adj[u]){auto&e=es[ei];if(e.cap<net.w)continue;double rho=double(e.use+net.w)/e.cap;double over=max(0.0,rho-1);double cost=1+e.occ*.35+e.hist+pf*pow(rho,4)+pf*100*over*over;double nd=cur.g+cost;
     if(stamp[v]!=sid||nd<d[v]-1e-8){stamp[v]=sid;d[v]=nd;pe[v]=ei;pn[v]=u;q.push({nd+heur(v),nd,v});}
    }
   }
   if(!hit){failed=true;break;}
   int u=target;while(pe[u]>=0){int ei=pe[u];if(own[ei]!=nid){own[ei]=nid;net.edges.push_back(ei);}if(tree[u]!=tid){tree[u]=tid;tn.push_back(u);}u=pn[u];}if(tree[u]!=tid){tree[u]=tid;tn.push_back(u);}
  }
  for(int ei:net.edges)es[ei].use+=net.w;if(failed)fails++;
 }
 long long overflow=0;int bad=0;double worst=0;for(auto&e:es){if(e.cap){worst=max(worst,double(e.use)/e.cap);if(e.use>e.cap){overflow+=e.use-e.cap;bad++;e.hist+=double(e.use-e.cap)/e.cap*10;}}}
 double sec=chrono::duration<double>(chrono::steady_clock::now()-begin).count();log<<pass<<" failures "<<fails<<" overedges "<<bad<<" overflow "<<overflow<<" worst_gate_ratio "<<worst<<" seconds "<<sec<<endl;cerr<<pass<<" failed "<<fails<<" over "<<bad<<" bits "<<overflow<<" worst "<<worst<<" sec "<<sec<<endl;
 if(!fails&&worst<=acceptable)break;pf*=1.4;
}
ofstream o(argv[2]);o<<nx<<" "<<ny<<" "<<E<<" "<<K<<"\n";for(int k=0;k<K;k++){auto&n=ns[k];o<<k<<" "<<n.edges.size();for(int e:n.edges)o<<" "<<e;o<<"\n";}o<<"USES\n";for(int e=0;e<E;e++)o<<e<<" "<<es[e].use<<" "<<es[e].cap<<"\n";
}
