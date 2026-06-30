#include <stdarg.h>

int varsum(int n,...){va_list ap;int t=0;va_start(ap,n);for(int i=0;i<n;i++)t+=va_arg(ap,int);va_end(ap);return t;}
int rec(int n){if(n<=0) return 0; return rec(n-1)+1;}
int m(double,double);                 /* prototype with no parameter identifiers */
int m(double x,double y){return x==y;}
int n(int a,int b);                   /* identifiers differ from definition */
int n(int x,int y){return x+y;}
int f();                              /* no-parameter function without 'void' */
int f(){return 0;}

int main(void){varsum(2,10,20); rec(3); m(0.1,0.2); n(1,2); f(); return 0;}
