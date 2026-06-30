#include <stdio.h>
#include <stdarg.h>
int f(); int m(double,double); int g(int a,int b); int h(int c,int d,int e,int f,int g); int v(int n,...); int r(int n); int s(int z); int k(int v); int u(void); int w(int *p); int q(int a,int b,int c); int tcase(int v); int sbool(int v); int onlydef(int v); int go(void); int cont(void); int ooe(void); int sz(void); int assignb(int x,int y); int ez(int z);
int f(){return 0;}
int m(double c,double d){return c==d;}
int g(int x,int y){return x+y;}
int h(int a,int b,int c,int d,int e){return a&b==c|d<<1+e;}
int v(int n,...){va_list ap;int t=0;va_start(ap,n);for(int i=0;i<n;i++)t+=va_arg(ap,int);va_end(ap);return t;}
int s(int z){if(z); printf(""); return z;}
int k(int v){int r=0;switch(v){default:r=9;break;case 0:r=1;break;}return r;}
int r(int n){if(n<=0)return 0;return r(n-1)+1;}
int u(void){return 1; printf("x");}
int w(int *p){if(p!=0 && *p++==42) return 1; return 0;}
int q(int a,int b,int c){if(a+b && c-1) return 1; else return 0;}
int tcase(int v){int r=0;switch(v){case 0:r=1;case 1:r=2;break;default:r=3;break;}return r;}
int sbool(int v){switch(v>0){case 0:return 0;case 1:return 1;default:return 2;}}
int onlydef(int v){switch(v){default:v++;break;}return v;}
int go(void){int n=0;goto L;n=1;L:n+=2;return n;}
int cont(void){int s=0;for(int i=0;i<5;i++){if(i%2) continue; s+=i;}return s;}
int ooe(void){int i=0;int r=i++ + ++i;return r;}
int sz(void){int i=0;return sizeof(i++);}
int assignb(int x,int y){if(x=y) return 1; return 0;}
int ez(int z){if(z) return 1; return 0;}
int main(void){int a=1;h(1,2,3,4,5);ooe();sz();w(&a);q(1,2,3);assignb(0,1);ez(5);for(float f=0;f<5;f+=0.5) a++;for(int i=0;i<3;i++,printf("t")) a++;u();s(1);go();cont();tcase(0);sbool(-1);onlydef(9);f();m(0.1,0.2);g(1,2);v(2,10,20);r(3);return 0;}