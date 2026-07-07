#include <stdio.h>

typedef unsigned int  uint32_t;
typedef unsigned char uint8_t;

void configure_hardware(uint32_t base_addr)
{
    uint32_t reg = base_addr + 0x10U;

    __asm__("CPSID i");   

    reg |= 0x01U;
    (void)reg;

    __asm__("CPSIE i");   
}


uint32_t compute_value(uint32_t x)
{
    uint32_t result;

    result = x * 2U;   

    result += 1U;      

    return result;
}


void process_data(uint8_t *buf, uint32_t len)
{
    uint32_t i;

    /* Main processing loop
     /* Rule 2.3 violation: /* sequence embedded inside this comment block */
    for (i = 0U; i < len; i++)
    {
        buf[i] = (uint8_t)(buf[i] + 1U);
    }
}


void transmit_packet(uint8_t *buf, uint32_t len)
{
    (void)len;

    /*
     * Rule 2.4 violation: live code commented out with block comment markers.
     * validate_checksum(buf, len);
     * log_packet(buf);
     * retry_count = 0;
     */

    buf[0] = 0xAAU;
}


int main(void)
{
    uint8_t data[4] = {1U, 2U, 3U, 4U};

    configure_hardware(0x40000000U);
    (void)compute_value(10U);
    process_data(data, 4U);
    transmit_packet(data, 4U);

    return 0;
}