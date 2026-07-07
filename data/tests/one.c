#include <stdio.h>

int sensor_data_acquisition_module_A = 0;   /* first 31 chars: "sensor_data_acquisition_module_" */
int sensor_data_acquisition_module_B = 0;   /* first 31 chars: "sensor_data_acquisition_module_" — SAME */

void trigger_nop(void)
{
    __asm__("NOP");   
}

// Commented here // 


int add(int a, int b) { return a + b; }

int test1 (void)
{
    int i = 0;
        return add(i++, i++);  
}

double compute_ratio(double a, double b) 
{
    return a / b;   
}


int main(void)
{
    int x = test1();
    double r = compute_ratio(3.0, 7.0);

/* Suppress unused-variable warnings for clarity */
    (void)x;
    (void)r;
    (void)sensor_data_acquisition_module_A;
    (void)sensor_data_acquisition_module_B;

    trigger_nop();
    return 0;
}