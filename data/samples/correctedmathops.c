int eq_double(double a, double b)
{
    return (a == b) ? 1 : 0;
}
int float_loop(int n)
{
    int count = 0;
    int i;
    for (i = 0; i < (n * 2); i++)     
    {
        count++;
    }
    return count;
}