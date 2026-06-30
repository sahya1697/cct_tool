#include <stdio.h>

int unreachable(void){return 1; printf("never\n");}
void no_effect(int a){a+1;}
void bad_null(int y){if(y); printf("after\n");}
int use_goto(void){int n=0;goto L; n=1; L: n+=2; return n;}
int use_continue(void){int s=0;for(int i=0;i<5;i++){if(i%2) continue; s+=i;}return s;}

int main(void){
    unreachable(); no_effect(3); bad_null(1); use_goto(); use_continue(); return 0;