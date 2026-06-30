#include <stdio.h>

int assign_bool(int x,int y){if(x=y) return 1; return 0;}
int explicit_zero(int z){if(z) return 1; return 0;}
int eq_double(double a,double b){return a==b;}
int float_for(void){int c=0;for(float f=0.0f;f<3.0f;f+=0.5f)c++;return c;}
int for_side(void){int c=0;for(int i=0;i<3;i++,printf("t")) c++;return c;}

int main(void){
    assign_bool(0,1); explicit_zero(5); eq_double(0.1,0.1);
    float_for(); for_side(); return 0;
}