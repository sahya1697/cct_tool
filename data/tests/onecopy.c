/*
 * env_violations.c
 *
 * Minimal C file violating MISRA-C:2004 Rules 1.1 – 1.5 (Section 6.1 Environment).
 *
 * Rule 1.1 (required): All code shall conform to ISO/IEC 9899:1990 "Programming
 *                      languages — C", amended by COR1:1995, AMD1:1995, COR2:1996.
 *
 * Rule 1.2 (required): No reliance shall be placed on undefined or unspecified behaviour.
 *
 * Rule 1.3 (required): Multiple compilers and/or languages shall only be used if there
 *                      is a common defined interface standard for object code to which
 *                      the languages/compilers/assemblers conform.
 *
 * Rule 1.4 (required): The compiler/linker shall be checked to ensure that 31-character
 *                      significance and case sensitivity are supported for external
 *                      identifiers.
 *
 * Rule 1.5 (advisory): Floating-point implementations should comply with a defined
 *                      floating-point standard.
 */

#include <stdio.h>

/* ── Rule 1.4 violation ───────────────────────────────────────────────────────
 * External identifiers must be distinct within 31 characters and be
 * case-sensitive. The two names below are identical in the first 31
 * characters, relying on significance beyond 31 characters to distinguish
 * them — which the standard does not require compilers to support.
 *
 * Characters:          1234567890123456789012345678901|23
 *                                                    ^ position 31
 */
int sensor_data_acquisition_module_A = 0;   /* first 31 chars: "sensor_data_acquisition_module_" */
int sensor_data_acquisition_module_B = 0;   /* first 31 chars: "sensor_data_acquisition_module_" — SAME */


/* ── Rule 1.3 violation ───────────────────────────────────────────────────────
 * Inline assembly is used here without any documented common interface standard
 * defining the object-code interface between the C module and the assembly
 * instruction. Mixing languages (C + asm) without such a standard violates 1.3.
 */
void trigger_nop(void)
{
    __asm__("NOP");   /* Rule 1.3: assembly mixed with C, no interface standard documented */
}


/* ── Rule 1.1 violation ───────────────────────────────────────────────────────
 * The // comment style is a C99 extension, not valid in ISO/IEC 9899:1990 (C90).
 * MISRA-C:2004 Rule 1.1 requires code to conform to C90; using C99 features
 * without a deviation violates it. Rule 2.2 also independently prohibits //.
 */
// Rule 1.1 violation: this C99 // comment is not valid ISO C90


/* ── Rule 1.2 violation ───────────────────────────────────────────────────────
 * The order in which function arguments are evaluated is UNSPECIFIED by the
 * C standard (ISO/IEC 9899:1990 §6.3.2.2). The code below relies on a
 * particular evaluation order of `i++` across two arguments — behaviour that
 * is unspecified and may vary between compilers.
 */
int add(int a, int b) { return a + b; }

int rule_1_2_violation(void)
{
    int i = 0;
    /*
     * The standard does not define whether the first or second argument
     * is evaluated first. If the left arg evaluates first: add(0, 1).
     * If the right arg evaluates first: add(1, 1). Result is unspecified.
     * Relying on either outcome is a Rule 1.2 violation.
     */
    return add(i++, i++);   /* Rule 1.2: unspecified evaluation order of i++ */
}


/* ── Rule 1.5 violation ───────────────────────────────────────────────────────
 * Rule 1.5 (advisory) requires that floating-point implementations comply
 * with a defined standard such as IEEE 754 / ANSI/IEEE Std 754.
 * The violation here is two-fold:
 *   (a) No typedef documents the floating-point standard in use (cf. Rule 6.3
 *       which recommends e.g. `typedef float float32_t; /* IEEE 754 */`).
 *   (b) The raw type `double` is used with no documentation of the
 *       underlying floating-point representation, making the implementation
 *       non-conformant to any documented standard.
 *
 * A compliant version would be:
 *     typedef float float32_t;   /* IEEE 754 single-precision */
 */
double compute_ratio(double a, double b)   /* Rule 1.5: raw `double` with no documented FP standard */
{
    return a / b;   /* FP behaviour depends on undocumented implementation */
}


int main(void)
{
    int x = rule_1_2_violation();
    double r = compute_ratio(3.0, 7.0);

    /* Suppress unused-variable warnings for clarity */
    (void)x;
    (void)r;
    (void)sensor_data_acquisition_module_A;
    (void)sensor_data_acquisition_module_B;

    trigger_nop();
    return 0;
}