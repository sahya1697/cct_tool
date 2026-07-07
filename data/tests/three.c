#include <stdio.h>    
#include <string.h>   

typedef unsigned int   uint32_t;
typedef unsigned char  uint8_t;
typedef signed   int   int32_t;

#pragma pack(push, 1)    
#pragma optimize("s", on) 

typedef struct
{
    uint8_t  flags  : 4;   
    uint8_t  mode   : 3;   
    uint8_t  status : 1;  
} DeviceRegister_t;        

static const char UNIT_LABEL[] = "Temp: 25°C";  
                                                 

int32_t arithmetic_shift_right(int32_t value, uint32_t bits)
{
       return value >> bits;   
}

int32_t divide_signed(int32_t numerator, int32_t denominator)
{
       return numerator / denominator;   
}

void report_result(int32_t value)
{
    char buf[32];

    sprintf(buf, "Result: %d\n", (int)value);

   
    if (strlen(buf) > 0U)
    {
       
        printf("%s", buf);
    }
}


int main(void)
{
    DeviceRegister_t reg;
    int32_t          result;

    reg.flags  = 0x0FU;
    reg.mode   = 3U;
    reg.status = 1U;
    (void)reg;

   
    result = arithmetic_shift_right(-256, 2U);

    
    result = divide_signed(result, -3);

   
    (void)UNIT_LABEL;

    report_result(result);

    return 0;
}