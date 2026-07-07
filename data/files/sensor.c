/*
 * sensor.c
 * Sensor acquisition and processing module.
 * VIOLATIONS IN THIS FILE:
 *   Rule 1.2  - Reliance on undefined behaviour (signed overflow in checksum)
 *   Rule 2.1  - Inline assembly not encapsulated in a macro or function
 *   Rule 2.2  - C99 // style comments used
 *   Rule 5.2  - Inner scope identifier hides outer scope identifier
 *   Rule 6.1  - plain char used for numeric storage
 *   Rule 8.1  - Function called without visible prototype
 *   Rule 8.2  - Object declared without explicit type
 *   Rule 9.1  - Automatic variable used before being assigned
 *   Rule 13.6 - Loop counter modified inside for-loop body
 *   Rule 14.1 - Unreachable code after unconditional return
 *   Rule 16.2 - Recursive function call
 */

#include "types.h"
#include "globals.h"

/* Outer-scope variable 'index' — will be hidden by inner declaration (Rule 5.2) */
static uint16_t index = 0U;

/* Rule 8.2 violation: no explicit type on declaration (implicit int) */
static status;    /* should be: static int32_t status; */

/* -----------------------------------------------------------------------
 * read_sensor_raw()
 * Reads a raw sensor value from hardware register.
 * Rule 2.1 violation: inline asm not isolated in macro/function
 * Rule 16.8 violation: non-void function missing return on some paths
 * ----------------------------------------------------------------------- */
uint16_t read_sensor_raw(uint8_t channel)
{
    uint16_t raw_val;

    /* Rule 2.1 violation: bare inline assembly, not encapsulated */
    asm("NOP");
    asm("NOP");

    if (channel < MAX_SENSORS)
    {
        raw_val = (uint16_t)(channel * 100U);
    }
    /* Rule 16.8 violation: if channel >= MAX_SENSORS, no return value provided */
    return raw_val;
}

/* -----------------------------------------------------------------------
 * compute_checksum()
 * Computes a simple additive checksum over a byte buffer.
 * Rule 1.2 violation: relies on signed integer overflow (undefined behaviour)
 * Rule 8.1 violation: calls log_error() without a visible prototype here
 *                     (prototype is in types.h but not included at point of call
 *                      due to conditional include being removed for demo)
 * ----------------------------------------------------------------------- */
int32_t compute_checksum(uint8_t *buf, uint16_t len)
{
    /* Rule 6.1 violation: plain char used to store a numeric accumulator */
    char  accum = 0;
    uint16_t i;

    for (i = 0U; i < len; i++)
    {
        /* Rule 1.2 violation: signed char overflow is undefined behaviour */
        accum = (char)(accum + (char)buf[i]);
    }

    if (accum < 0)
    {
        /* Rule 8.1 violation: log_error has no prototype visible in this
         * translation unit at this point in a standalone build */
        log_error((int32_t)accum);
    }

    return (int32_t)accum;
}

/* -----------------------------------------------------------------------
 * scale_reading()
 * Applies linear scaling to a raw sensor reading.
 * Rule 5.2 violation: local 'index' hides file-scope 'index'
 * Rule 9.1 violation: 'result' used before assignment on error path
 * Rule 2.2 violation: C99 // comments used throughout
 * ----------------------------------------------------------------------- */
int32_t scale_reading(uint16_t raw, uint8_t sensor_id)
{
    int32_t  result;       /* Rule 9.1: not initialised */
    // Rule 2.2 violation: C99 // comment style (not permitted in C90)

    /* Rule 5.2 violation: local 'index' hides file-scope static 'index' */
    uint16_t index = sensor_id;  /* shadows outer 'index' */

    if (index < MAX_SENSORS)
    {
        result = (int32_t)raw * 10;
    }
    /* No else: if index >= MAX_SENSORS, result is uninitialised but returned */

    // Rule 2.2: another C99 comment
    return result;   /* Rule 9.1: undefined value returned on error path */
}

/* -----------------------------------------------------------------------
 * process_all_sensors()
 * Iterates over all sensors and accumulates readings.
 * Rule 13.6 violation: loop counter 'i' modified inside the for body
 * Rule 14.1 violation: unreachable code after return
 * ----------------------------------------------------------------------- */
int32_t process_all_sensors(void)
{
    uint8_t  i;
    int32_t  total = 0;
    uint16_t raw;

    for (i = 0U; i < MAX_SENSORS; i++)
    {
        raw    = read_sensor_raw(i);
        total += scale_reading(raw, i);

        /* Rule 13.6 violation: numeric loop counter 'i' modified in body */
        if (raw > 900U)
        {
            i++;    /* skip next channel — modifies loop counter */
        }
    }

    return total;

    /* Rule 14.1 violation: code below is unreachable */
    total = 0;
    return total;
}

/* -----------------------------------------------------------------------
 * recursive_sum()
 * Rule 16.2 violation: function calls itself recursively
 * ----------------------------------------------------------------------- */
uint32_t recursive_sum(uint8_t n)
{
    if (n == 0U)
    {
        return 0U;
    }
    /* Rule 16.2 violation: direct recursion */
    return (uint32_t)n + recursive_sum((uint8_t)(n - 1U));
}
