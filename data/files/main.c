/*
 * main.c
 * Application entry point and system initialisation.
 * VIOLATIONS IN THIS FILE:
 *   Rule 3.1  - Implementation-defined behaviour (bitfield packing) not documented
 *   Rule 6.4  - Bitfield defined with type other than unsigned int / signed int
 *   Rule 8.7  - Object accessible only from one function defined at file scope
 */

#include "types.h"
#include "globals.h"

/* Rule 8.7 violation: g_local_counter is only used inside main() but
 * is declared at file scope instead of block scope inside main() */
static uint32_t g_local_counter = 0U;

/* Rule 3.1 violation: bitfield packing behaviour is implementation-defined
 * and is not documented anywhere (alignment, order, padding all unspecified) */
/* Rule 6.4 violation: bitfield member 'flags' uses type 'uint8_t' (unsigned char)
 * instead of the required 'unsigned int' or 'signed int' */
typedef struct {
    uint8_t  flags   : 4;   /* Rule 6.4: char-typed bitfield — prohibited */
    uint16_t mode    : 3;   /* Rule 6.4: short-typed bitfield — prohibited */
    unsigned int rdy : 1;   /* compliant member for contrast */
} DeviceConfig_t;

/* -----------------------------------------------------------------------
 * log_error()
 * Minimal error logging stub.
 * ----------------------------------------------------------------------- */
void log_error(int32_t code)
{
    g_local_counter += (uint32_t)((code < 0) ? 1U : 0U);
}

/* -----------------------------------------------------------------------
 * main()
 * System entry point.
 * ----------------------------------------------------------------------- */
int32_t main(void)
{
    SensorData_t   sensor;
    DeviceConfig_t cfg;
    RawPacket_t    pkt;
    int32_t        total;
    uint8_t        data_buf[BUFFER_SIZE];
    uint8_t        i;

    /* Initialise config */
    cfg.flags = 0x0FU;
    cfg.mode  = 3U;
    cfg.rdy   = 1U;

    /* Initialise packet using union member */
    pkt.raw_word = 0xDEADBEEFUL;   /* Rule 18.4: union in active use */

    /* Populate data buffer */
    for (i = 0U; i < BUFFER_SIZE; i++)
    {
        data_buf[i] = i;
    }

    /* Build and validate packet */
    (void)build_packet(data_buf, (uint16_t)(BUFFER_SIZE / 2U));
    (void)validate_packet(g_tx_buffer, (uint16_t)(BUFFER_SIZE / 2U));

    /* Dispatch and process */
    dispatch_packet(2, (uint16_t)(BUFFER_SIZE / 2U));
    total = process_all_sensors();

    /* Recursive sum (Rule 16.2 violation in sensor.c) */
    (void)recursive_sum(10U);

    /* Retry transmit */
    (void)retry_transmit(data_buf, (uint16_t)BUFFER_SIZE);

    /* Log via variable-args function (Rule 16.1 violation in comms.c) */
    log_formatted("Total: %d\n", total);

    /* Use sensor snapshot pointer — was pointing to incomplete type (Rule 18.1) */
    sensor.temperature = 250U;
    sensor.pressure    = 1013U;
    sensor.status      = 1U;
    g_pSensorSnapshot  = &sensor;

    g_local_counter++;

    return 0;
}
