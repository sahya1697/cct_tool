#include <stdio.h>
#include <stddef.h>

int prec(int a,int b,int c,int d,int e){return a & b == c | d << 1 + e;}
int unspecified(void){int i=0;int r=i++ + ++i;return r;}
int size_effect(void){int i=0;return (int)sizeof(i++);}
int logical_rhs(int *p){if(p!=0 && *p++==42) return 1; return 0;}
int logical_nonprimary(int a,int b,int c){if(a+b && c-1) return 1; else return 0;}

int main(void){
    int a=1,b=2,c=3,d=4,e=5,x[2]={42,7};int *p=x;
    prec(a,b,c,d,e); unspecified(); size_effect();
    logical_rhs(p); logical_nonprimary(1,2,3);
    return 0;
}