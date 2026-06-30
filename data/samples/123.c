#include <stdio.h>
#include <stdarg.h>
int r15_1_bad_case_scope(int v) {
    int r = 0;
    switch (v) {
        { case 0: 
            r = 10;
            break;
        }
        default:
            r = -1;
            break;
    }
    return r;
}
int r15_2_missing_break(int v) {
    int r = 0;
    switch (v) {
        case 0:
            r = 1;  
        case 1:
            r = 2;
            break;
        default:
            r = 3;
            break;
    }
    return r;
}
int r15_3_default_not_final(int v) {
    int r = 0;
    switch (v) {
        default: 
            r = -1;
            break;
        case 0:
            r = 0;
            break;
    }
    return r;
}
int r15_4_boolean_switch(int v) {
    int r = 0;
    switch (v == 0) { 


        case 0:
            r = 10;
            break;
        case 1:
            r = 20;
            break;
        default:
            r = 30;
            break;
    }
    return r;
}
int r15_5_only_default(int v) {
    switch (v) {
        default:

            v++;
            break;
    }
    return v;
}
int main(void) {
    (void)r15_1_bad_case_scope(0);
    (void)r15_2_missing_break(0);
    (void)r15_3_default_not_final(0);
    (void)r15_4_boolean_switch(0);
    (void)r15_5_only_default(9);
    return 0;
}