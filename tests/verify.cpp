#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <iostream>
using namespace std;
using U=__uint128_t;
using Clock=chrono::steady_clock;
const int widths[]={8,10,12,14,14,12,10,8};
int dx[]={1,-1,0,1,-1,1,0,-1}, dy[]={0,1,1,1,0,-1,-1,-1};
U ray[128][8], path[128][128], adjacent[128], anchors, board;
U bit(int s){return U{1}<<s;}
int low(U x){return (uint64_t)x?__builtin_ctzll((uint64_t)x):64+__builtin_ctzll(x>>64);}
int high(U x){return (x>>64)?127-__builtin_clzll(x>>64):63-__builtin_clzll((uint64_t)x);}
int pop(U x){return __builtin_popcountll(x)+__builtin_popcountll(x>>64);}
U flip(U a,U b,int s){
 U f=0;
 if(!(adjacent[s]&b))return 0;
 for(int d=0;d<8;d++){
  U stop=ray[s][d]&~b;if(!stop)continue;
  int t=d<4?low(stop):high(stop);
  if(a&bit(t))f|=path[s][t];
 }
 return f;
}
void init(){
 for(int r=0;r<8;++r)for(int c=(14-widths[r])/2;c<(14+widths[r])/2;++c){
  int s=16*r+c;board|=bit(s);
  for(int d=0;d<8;++d){
   int y=r+dy[d],x=c+dx[d];
   while(y>=0&&y<8&&x>=(14-widths[y])/2&&x<(14+widths[y])/2){
    int t=16*y+x;
    if(!ray[s][d])adjacent[s]|=bit(t);
    path[s][t]=ray[s][d];ray[s][d]|=bit(t);
    x+=dx[d];y+=dy[d];
   }
  }
  bool safe=true;
  for(int d=0;d<4;++d)if(ray[s][d]&&ray[s][d+4])safe=false;
  if(safe)anchors|=bit(s);
 }
}
struct Entry{U a,b;signed char lo,hi;unsigned char best;};
Entry tab[1<<20];
unsigned long long nodes=0;
Clock::time_point deadline;
struct TimedOut{};
int outcome(U a,U b,int alpha,int beta,bool passed=false){
 if((++nodes&8191)==0 && Clock::now()>deadline)throw TimedOut{};
 U empty=board&~(a|b);
 if(!empty)return (pop(a)>pop(b))-(pop(a)<pop(b));
 uint64_t h=(uint64_t)a*0x94d049bb133111ebULL+(uint64_t)(a>>64)*0xbf58476d1ce4e5b9ULL;
 h^=(uint64_t)b*0xd6e8feb86659fd93ULL+(uint64_t)(b>>64)*0xa0761d6478bd642fULL;
 auto& e=tab[((h^(h>>33))*0x9e3779b97f4a7c15ULL)>>(64-20)];
 int prefer=-1;
 if(e.a==a && e.b==b) {
  if(e.lo==e.hi || e.lo>=beta)return e.lo;
  if(e.hi<=alpha)return e.hi;
  prefer=e.best;
 }
 struct Move{U f;int s,k;};Move m[88];int n=0, vacancies=pop(empty);
 for(U x=empty;x;x&=x-1){
  int s=low(x);U f=flip(a,b,s);if(!f)continue;
  int k=(s==prefer?1000:0)+((anchors&bit(s))?100:0);
  if(vacancies>=8){
   U other=b^f,own=a|bit(s)|f;
   for(U y=empty^bit(s);y;y&=y-1){
    int r=low(y);
    if(flip(other,own,r))k-=1+12*bool(anchors&bit(r));
   }
  }
  m[n++]={f,s,k};
 }
 if(!n){
  if(passed)return (pop(a)>pop(b))-(pop(a)<pop(b));
  return -outcome(b,a,-beta,-alpha,true);
 }
 if(vacancies>=8)sort(m,m+n,[](auto x,auto y){return x.k>y.k;});
 int best=-2,bestSq=m[0].s,initial=alpha;
 for(int i=0;i<n;++i){
  auto [f,s,k]=m[i];
  int v=-outcome(b^f,a|bit(s)|f,-beta,-alpha);
  if(v>best){best=v;bestSq=s;}alpha=max(alpha,v);
  if(alpha>=beta)break;
 }
 int lo=best>initial?best:-1,hi=best<beta?best:1;
 if(e.a==a && e.b==b){lo=max(lo,int(e.lo));hi=min(hi,int(e.hi));}
 assert(lo<=hi);
 e={a,b,(signed char)lo,(signed char)hi,(unsigned char)bestSq};return best;
}
int main(){
 init();int limit,ra,ca,rb,cb;
 while(cin>>limit>>ra>>ca>>rb>>cb){
  U a=0,b=0;
  for(U x=board;x;x&=x-1){int v;cin>>v;if(v==1)a|=bit(low(x));if(v==2)b|=bit(low(x));}
  int results[3]={-9,-9,-9};
  int s1=16*(ra-1)+(14-widths[ra-1])/2+ca-1;
  int s2=16*(rb-1)+(14-widths[rb-1])/2+cb-1;
  for(int j=0;j<3;j++){
   if(j==1 && s1==s2){results[1]=results[0];continue;}
   if(j==2 && (results[0]==1 || results[1]==1)){results[2]=1;break;}
   deadline=Clock::now()+chrono::seconds(limit);
   try{
    if(j==2)results[j]=outcome(a,b,-1,1);
    else{int s=j?s2:s1;U f=flip(a,b,s);assert(f);results[j]=-outcome(b^f,a|bit(s)|f,-1,1);}
   }catch(TimedOut&){}
  }
  cout<<results[0]<<' '<<results[1]<<' '<<results[2]<<endl;
 }
 return 0;
}
