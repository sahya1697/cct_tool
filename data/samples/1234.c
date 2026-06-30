#include <stdio.h>
#include <stdarg.h>
int r13_1(int x, int y) {
    if (x = y) {               
        return 1;
    }
    return 0;
}
int r13_2_explicit_zero_test_int(int x) {
    if (x) {                    
        return 1;
    }
    return 0;
}
int r13_2_explicit_zero_test_ptr(int *p) {
    if (p) {                    
        return *p;
    }
    return 0;
}
int r13_3_fp_equality(float f, float g) {
    if (f == g) {               
        return 1;
    } else if (f != 0.0f) {    
        return 2;
    }
    return 0;
}
int r13_4_float_for(void) {
    int count = 0;
    for (float f = 0.0f; f < 3.0f; f += 0.5f) { 
        count++;
    }
    return count;
}
int r13_5_for_side_effects(void) {
    int i, ticks = 0;
    for (i = 0; i < 3; i++, printf("tick\n")) {  
        ticks++;
    }
    return ticks;
}
int r14_1_unreachable(void) {
    return 1;
    printf("unreachable\n");   
}
void r14_2_no_side_effect(void) {
    int a = 10;
    a + 1;           
}
void r14_3_null_stmt(void) {
    int i = 0;
    for (i = 0; i < 2; i++) ; printf("bad\n");    
    if (i) ; printf("also bad\n");               
}
int r14_4_goto(void) {
    int s = 0;
    goto L1;                   
    s = 1;
L1:
    s += 2;
    return s;
}
int r14_5_continue(void) {
    int sum = 0;
    for (int i = 0; i < 6; i++) {
        if (i % 2) continue;   
        sum += i;
    }
    return sum;
}
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
    int a = 1, b = 2, x = 0;
    (void)r13_1(a, b);
    (void)r13_2_explicit_zero_test_int(x);
    (void)r13_2_explicit_zero_test_ptr(&x);
    (void)r13_3_fp_equality(0.1f, 0.2f);
    (void)r13_4_float_for();
    (void)r13_5_for_side_effects();
    (void)r14_1_unreachable();
    r14_2_no_side_effect();
    r14_3_null_stmt();
    (void)r14_4_goto();
    (void)r14_5_continue();
    (void)r15_1_bad_case_scope(0);
    (void)r15_2_missing_break(0);
    (void)r15_3_default_not_final(0);
    (void)r15_4_boolean_switch(0);
    (void)r15_5_only_default(9);
    return 0;
}