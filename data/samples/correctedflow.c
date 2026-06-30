int process(int x)
{
    int y = x;
    if (y < 0)
    {
        y = 0;
    }
    if (y >= 0)
    {
        y = y + 1;
    }
    if (y == 0)
    {
        y = y + 2;
    }
    else
    {
        /* MISRA  */
    }
    return y;
}
int sw_case(int a)
{
    int r = 0;
    switch (a % 3)
    {
        case 0:
        {
            r = 10;
            break;      /* FIX: added missing break */
        }
        case 1:
        {
            r = 20;
            break;
        }
        default:
        {
            r = 30;
            break;
        }
    }
    return r;
}