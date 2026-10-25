#include <algorithm>
#include <climits>
extern "C" int norm_finish_root(const int *dl) {
  const int NV=80,NVP=128,LAV=6,INF=INT_MAX/4;
  bool add[256]={}; int vd[256],iss[256],pick[16];
  std::fill(vd,vd+256,INF); std::fill(iss,iss+256,INF);std::fill(pick,pick+16,-1);
  for(int n=1;n<NVP;n++){int floor=0,x=n;while(x>>=1)floor++;int H=7-floor;add[n]=(((2*n+1)<<(H-1))-NVP)<NV;}
  for(int b=0;b<16;b++) for(int k=0;k<5;k++)vd[NVP+5*b+k]=dl[b]+2;
  int c=*std::min_element(dl,dl+16);
  auto valid=[&](int n,int at){while(n<NVP&&!add[n])n*=2;return vd[n]<=at;};
  for(int step=0;step<4096;step++,c++){
    bool ready[128]={};
    for(int n=1;n<NVP;n++)ready[n]=add[n]&&valid(2*n,c)&&valid(2*n+1,c)&&iss[n]>c;
    int win=-1;for(int g=0;g<16;g++)if(pick[g]>=0){if(iss[pick[g]]>c)win=pick[g];break;}
    if(win>=0){iss[win]=c+1;int wb=c+1+LAV;vd[win]=wb+1;if(win==1)return wb;}
    std::fill(pick,pick+16,-1);
    for(int n=1;n<NVP;n++)if(ready[n]&&pick[n/8]<0)pick[n/8]=n;
  }
  return -1;
}
