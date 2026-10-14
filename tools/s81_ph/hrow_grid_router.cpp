#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <iostream>
#include <queue>
#include <string>
#include <vector>
using namespace std;
struct Edge { int d,y,x; };
struct Net {int bits,ax,ay,bx,by,af,bf,limit; vector<Edge> path;};
int nx,ny; vector<double> ch,cv,uh,uv,cwh,cwv,uwh,uwv;
int hi(int y,int x){return y*(nx-1)+x;} int vi(int y,int x){return y*nx+x;}
array<int,2> normals[4]={{{1,0}},{{-1,0}},{{0,1}},{{0,-1}}};
void adjust(const vector<Edge>&path,int delta){for(auto e:path){if(e.d==0){uh[hi(e.y,e.x)]+=delta;for(int y=max(0,e.y-4);y<=min(e.y,ny-5);y++)uwh[hi(y,e.x)]+=delta;}else{uv[vi(e.y,e.x)]+=delta;for(int x=max(0,e.x-4);x<=min(e.x,nx-5);x++)uwv[e.y*(nx-4)+x]+=delta;}}}
double cost(Edge e,int bits){double r,w=0;if(e.d==0){r=(uh[hi(e.y,e.x)]+bits)/ch[hi(e.y,e.x)];for(int y=max(0,e.y-4);y<=min(e.y,ny-5);y++)w=max(w,(uwh[hi(y,e.x)]+bits)/cwh[hi(y,e.x)]);}else{r=(uv[vi(e.y,e.x)]+bits)/cv[vi(e.y,e.x)];for(int x=max(0,e.x-4);x<=min(e.x,nx-5);x++)w=max(w,(uwv[e.y*(nx-4)+x]+bits)/cwv[e.y*(nx-4)+x]);}return 1+.1*r*r+1e6*pow(max(0.,w-.595),2)+1e6*pow(max(0.,r-.995),2);}
vector<Edge> route(const Net&n){int s=n.ay*nx+n.ax,t=n.by*nx+n.bx;if(s==t)return {};vector<double> dist(nx*ny,1e100);vector<int> prev(nx*ny,-1);priority_queue<pair<double,int>,vector<pair<double,int>>,greater<pair<double,int>>> q;dist[s]=0;q.push({abs(n.ax-n.bx)+abs(n.ay-n.by),s});int dx[4]={1,-1,0,0},dy[4]={0,0,1,-1};
while(!q.empty()){auto [f,a]=q.top();q.pop();int x=a%nx,y=a/nx;double h=abs(x-n.bx)+abs(y-n.by);if(f>dist[a]+h+1e-7)continue;if(a==t)break;for(int k=0;k<4;k++){int xx=x+dx[k],yy=y+dy[k];if(xx<0||xx>=nx||yy<0||yy>=ny)continue;int b=yy*nx+xx;if(a==s && dx[k]*normals[n.af][0]+dy[k]*normals[n.af][1]<0)continue;if(b==t && dx[k]*normals[n.bf][0]+dy[k]*normals[n.bf][1]>0)continue;Edge e=k==0?Edge{0,y,x}:k==1?Edge{0,y,x-1}:k==2?Edge{1,y,x}:Edge{1,y-1,x};double d=dist[a]+cost(e,n.bits);if(d+1e-9<dist[b]){dist[b]=d;prev[b]=a;q.push({d+abs(xx-n.bx)+abs(yy-n.by),b});}}}
if(prev[t]<0)throw runtime_error("No normal-escape grid path");vector<Edge> out;for(int a=t;a!=s;){int b=prev[a],x=a%nx,y=a/nx,xx=b%nx,yy=b/nx;out.push_back(y==yy?Edge{0,y,min(x,xx)}:Edge{1,min(y,yy),x});a=b;}reverse(out.begin(),out.end());return out;}
vector<Edge> bounded_route(const Net&n){
 int direct=abs(n.ax-n.bx)+abs(n.ay-n.by);if(n.limit<direct)throw runtime_error("Physical pin escape leaves insufficient500um grid budget");
 int margin=(n.limit-direct)/2,lx=max(0,min(n.ax,n.bx)-margin),rx=min(nx-1,max(n.ax,n.bx)+margin),ly=max(0,min(n.ay,n.by)-margin),ry=min(ny-1,max(n.ay,n.by)+margin),w=rx-lx+1,h=ry-ly+1,N=w*h;
 int start=(n.ay-ly)*w+n.ax-lx,target=(n.by-ly)*w+n.bx-lx;vector<double> distance(N*(n.limit+1),1e100);vector<int> previous(distance.size(),-1);priority_queue<pair<double,int>,vector<pair<double,int>>,greater<pair<double,int>>> queue;distance[start]=0;queue.push({double(direct),start});int result=-1,dx[4]={1,-1,0,0},dy[4]={0,0,1,-1};
 while(!queue.empty()){auto [f,state]=queue.top();queue.pop();int steps=state/N,node=state%N,x=node%w+lx,y=node/w+ly;double heuristic=abs(x-n.bx)+abs(y-n.by);if(f>distance[state]+heuristic+1e-7)continue;if(node==target){result=state;break;}if(steps==n.limit)continue;
  for(int k=0;k<4;k++){int xx=x+dx[k],yy=y+dy[k];if(xx<lx||xx>rx||yy<ly||yy>ry||steps+1+abs(xx-n.bx)+abs(yy-n.by)>n.limit)continue;if((yy-ly)*w+xx-lx==start)continue;if(node==start&&dx[k]*normals[n.af][0]+dy[k]*normals[n.af][1]<0)continue;if(xx==n.bx&&yy==n.by&&dx[k]*normals[n.bf][0]+dy[k]*normals[n.bf][1]>0)continue;Edge edge=k==0?Edge{0,y,x}:k==1?Edge{0,y,x-1}:k==2?Edge{1,y,x}:Edge{1,y-1,x};int next=(steps+1)*N+(yy-ly)*w+xx-lx;double value=distance[state]+cost(edge,n.bits);if(value+1e-9<distance[next]){distance[next]=value;previous[next]=state;queue.push({value+abs(xx-n.bx)+abs(yy-n.by),next});}}
 }
 if(result<0)throw runtime_error("No normal-escape route within per-pair physical wire budget");vector<Edge> out;for(int state=result;state!=start;){int prev=previous[state],a=state%N,b=prev%N,x=a%w+lx,y=a/w+ly,xx=b%w+lx,yy=b/w+ly;out.push_back(y==yy?Edge{0,y,min(x,xx)}:Edge{1,min(y,yy),x});state=prev;}reverse(out.begin(),out.end());return out;
}
array<double,3> maxima(){double a=0,b=0,c=0;for(int i=0;i<(int)uwh.size();i++)a=max(a,uwh[i]/cwh[i]);for(int i=0;i<(int)uwv.size();i++)b=max(b,uwv[i]/cwv[i]);for(int i=0;i<(int)uh.size();i++)c=max(c,uh[i]/ch[i]);for(int i=0;i<(int)uv.size();i++)c=max(c,uv[i]/cv[i]);return {a,b,c};}
int main(int argc,char**argv){ifstream in(argv[1]);int nn;in>>nx>>ny>>nn;ch.resize(ny*(nx-1));cv.resize((ny-1)*nx);uh.resize(ch.size());uv.resize(cv.size());for(auto *v:{&ch,&cv,&uh,&uv})for(auto &x:*v)in>>x;vector<Net> nets(nn);for(auto &n:nets)in>>n.bits>>n.ax>>n.ay>>n.bx>>n.by>>n.af>>n.bf>>n.limit;cwh.resize((ny-4)*(nx-1));uwh.resize(cwh.size());cwv.resize((ny-1)*(nx-4));uwv.resize(cwv.size());for(int y=0;y<ny-4;y++)for(int x=0;x<nx-1;x++)for(int j=0;j<5;j++){cwh[hi(y,x)]+=ch[hi(y+j,x)];uwh[hi(y,x)]+=uh[hi(y+j,x)];}for(int y=0;y<ny-1;y++)for(int x=0;x<nx-4;x++)for(int j=0;j<5;j++){cwv[y*(nx-4)+x]+=cv[vi(y,x+j)];uwv[y*(nx-4)+x]+=uv[vi(y,x+j)];}
vector<int> order(nn);for(int i=0;i<nn;i++)order[i]=i;
for(int pass=0;pass<16;pass++){if(pass)sort(order.begin(),order.end(),[&](int a,int b){double ca=0,cb=0;for(auto e:nets[a].path)ca=max(ca,cost(e,nets[a].bits));for(auto e:nets[b].path)cb=max(cb,cost(e,nets[b].bits));return ca>cb;});for(int i:order){auto &n=nets[i];adjust(n.path,-n.bits);try{n.path=n.limit>=0?bounded_route(n):route(n);}catch(const exception&e){cerr<<"BOUND_INFEASIBLE group "<<i<<" "<<e.what()<<endl;return 2;}adjust(n.path,n.bits);}auto m=maxima();cerr<<"ASTAR pass "<<pass+1<<" windows "<<m[0]<<" "<<m[1]<<" edge "<<m[2]<<endl;if(m[0]<=.6&&m[1]<=.6&&m[2]<=1)break;}
ofstream out(argv[2]);out<<nn<<'\n';for(auto &n:nets){out<<n.path.size();for(auto e:n.path)out<<' '<<e.d<<' '<<e.y<<' '<<e.x;out<<'\n';}return 0;}
