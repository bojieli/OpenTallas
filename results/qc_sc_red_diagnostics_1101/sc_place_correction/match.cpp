#include <bits/stdc++.h>
using namespace std;
struct Edge{int to,rev,cap;};
struct Dinic{vector<vector<Edge>> g;vector<int> level,it;Dinic(int n):g(n),level(n),it(n){};
void add(int u,int v,int c){g[u].push_back({v,(int)g[v].size(),c});g[v].push_back({u,(int)g[u].size()-1,0});}
bool bfs(int s,int t){fill(level.begin(),level.end(),-1);queue<int>q;level[s]=0;q.push(s);while(!q.empty()){int u=q.front();q.pop();for(auto e:g[u])if(e.cap&&level[e.to]<0){level[e.to]=level[u]+1;q.push(e.to);}}return level[t]>=0;}
int dfs(int u,int t,int f){if(u==t)return f;for(int &i=it[u];i<(int)g[u].size();i++){auto &e=g[u][i];if(e.cap&&level[e.to]==level[u]+1){int z=dfs(e.to,t,min(f,e.cap));if(z){e.cap-=z;g[e.to][e.rev].cap+=z;return z;}}}return 0;}
int flow(int s,int t){int ans=0;while(bfs(s,t)){fill(it.begin(),it.end(),0);while(int z=dfs(s,t,INT_MAX))ans+=z;}return ans;}};
int main(){ifstream f("points.tsv");string typ,n;double x,y;vector<string>sn,ln;vector<pair<double,double>>sp,lp;while(f>>typ>>n>>x>>y){if(typ=="S"){sn.push_back(n);sp.push_back({x,y});}else{ln.push_back(n);lp.push_back({x,y});}}
int N=sn.size(),L=ln.size(),T=N+L+1;for(int rad:{16,24,32,48,64,80,96,128,160,220}){Dinic d(T+1);long long edges=0;for(int i=0;i<N;i++){d.add(0,1+i,1);for(int j=0;j<L;j++)if(abs(sp[i].first-lp[j].first)+abs(sp[i].second-lp[j].second)<=rad){d.add(1+i,1+N+j,1);edges++;}}for(int j=0;j<L;j++)d.add(1+N+j,T,42);int flow=d.flow(0,T);cout<<"radius "<<rad<<" edges "<<edges<<" flow "<<flow<<" required "<<N<<endl;if(flow!=N)continue;ofstream o("assignment.tsv");o<<"instance\tleaf\tcentre_reach_um\n";for(int i=0;i<N;i++){int k=-1;for(auto e:d.g[1+i])if(e.to> N&&e.to<T&&e.cap==0){if(k!=-1)return 3;k=e.to-N-1;}if(k<0)return 4;double dist=abs(sp[i].first-lp[k].first)+abs(sp[i].second-lp[k].second);o<<sn[i]<<'\t'<<ln[k]<<'\t'<<dist<<'\n';}return 0;}return 2;}
