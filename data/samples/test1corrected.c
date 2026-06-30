#include <stdio.h>
#include <stddef.h>
#include <stdbool.h>
int prec(int a, int b, int c, int d, int e) {
    return ((a & b) == c) | (d << (1 + e));
}
int unspecified(void) {
    int i = 0;
    int r;
    i++;            
    r = i + 1;     
    return r;
}
int size_effect(void) {
    int i = 0;
    size_t s = sizeof(i);    
    (void)i;
    return (int)s;
}
int logical_rhs(const int *p) {
    if (p == NULL) {
        return 0;
    }
    int val = *p;           
    if ((p != NULL) && (val == 42)) {
        return 1;
    }
    return 0;
}
int logical_nonprimary(int a, int b, int c) {
    int left  = a + b;
    int right = c - 1;
    if ((left) && (right)) {
        return 1;
    } else {
        return 0;
    }
}
int main(void) {
    int a = 1, b = 2, c = 3, d = 4, e = 5, x[2] = {42, 7};
    const int *p = x;

    (void)prec(a, b, c, d, e);
    (void)unspecified();
    (void)size_effect();
    (void)logical_rhs(p);
    (void)logical_nonprimary(1, 2, 3);
    return 0;
}