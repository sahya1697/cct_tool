#include <stdio.h>
int  unreachable(void);
int  no_effect(int a);          
void bad_null(int y);
int  use_goto(void);
int  use_continue(void);
int unreachable(void)
{
    return 1;
}
int no_effect(int a)
{
    a += 1;
    return a;
}
void bad_null(int y)
{
    if (y != 0)
    {
        (void)printf("after\n");
    }
}
int use_goto(void)
{
    int n = 0;
    n += 2;
    return n;
}
int use_continue(void)
{
    int s = 0;
    for (int i = 0; i < 5; i++)
    {
        if ((i % 2) == 0)
        {
            s += i;
        }
    }
    return s;
}
int main(void)
{
    (void)printf("unreachable() -> %d\n", unreachable());
    int inc = no_effect(3);                
    (void)printf("no_effect(3) -> %d\n", inc);
    bad_null(1);                           
    (void)printf("use_goto() -> %d\n", use_goto());
    (void)printf("use_continue() -> %d\n", use_continue());
    return 0;
}