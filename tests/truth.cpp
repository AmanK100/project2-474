#define main solver_cli
#include "verify.cpp"
#undef main
int exact(U a,U b,int lowBound=-100,int highBound=100,bool passed=false) {
 int score=-100;
 for(U x=board&~(a|b);x;x&=x-1) {
  int s=low(x);U f=flip(a,b,s);if(!f)continue;
  score=max(score,-exact(b^f,a|f|bit(s),-highBound,-lowBound));
  lowBound=max(lowBound,score);if(lowBound>=highBound)break;
 }
 if(score!=-100)return score;
 return passed ? pop(a)-pop(b) : -exact(b,a,-highBound,-lowBound,true);
}
int main(){
 init();int v;
 while(cin>>v){
  U a=0,b=0;bool firstCell=true;
  for(U x=board;x;x&=x-1){if(!firstCell)cin>>v;firstCell=false;
   int s=low(x);if(v==1)a|=bit(s);if(v==2)b|=bit(s);}
  for(U x=board&~(a|b);x;x&=x-1){
   int s=low(x);U f=flip(a,b,s);if(!f)continue;
   U opp=b^f,our=a|bit(s)|f;int worst=100,wins=0,total=0;
   for(U y=board&~(opp|our);y;y&=y-1){
    int r=low(y);U f2=flip(opp,our,r);if(!f2)continue;
    int value=exact(our^f2,opp|f2|bit(r));
    worst=min(worst,value);wins+=value>0;total++;
   }
   if(!total)worst=-exact(opp,our);
   cout<<s<<' '<<worst<<' '<<wins<<' '<<total<<' ';
  }
  cout<<endl;
 }
}
