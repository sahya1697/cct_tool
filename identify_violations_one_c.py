"""
Identify actual MISRA C 2004 violations in data/tests/one.c
"""

print("=" * 80)
print("ACTUAL MISRA C 2004 VIOLATIONS IN one.c")
print("=" * 80)

violations = [
    {
        'line': 3,
        'rule': '5.1',
        'severity': 'Required',
        'code': 'int sensor_data_acquisition_module_A = 0;',
        'violation': 'Identifiers shall not rely on significance of more than 31 characters',
        'details': 'sensor_data_acquisition_module_A and sensor_data_acquisition_module_B have same first 31 chars',
        'evidence': 'First 31 chars: "sensor_data_acquisition_module_"'
    },
    {
        'line': 4,
        'rule': '5.1',
        'severity': 'Required',
        'code': 'int sensor_data_acquisition_module_B = 0;',
        'violation': 'Identifiers shall not rely on significance of more than 31 characters',
        'details': 'Same first 31 characters as line 3',
        'evidence': 'First 31 chars: "sensor_data_acquisition_module_"'
    },
    {
        'line': 8,
        'rule': '2.1',
        'severity': 'Required',
        'code': '__asm__("NOP");',
        'violation': 'Assembly language shall be encapsulated and isolated',
        'details': 'Inline assembly should be in macro or separate function',
        'detected': True  # System found this one
    },
    {
        'line': 12,
        'rule': '2.2',
        'severity': 'Required',
        'code': '// Commented here //',
        'violation': 'Source code shall only use /* ... */ style comments',
        'details': 'C++ style comment (//) not allowed in MISRA C 2004',
        'evidence': 'Line uses // instead of /* */'
    },
    {
        'line': 15,
        'rule': '16.9',
        'severity': 'Required',
        'code': 'int add(int a, int b) { return a + b; }',
        'violation': 'A function identifier shall only be used with function call or address-of operator',
        'details': 'Function definition on single line - stylistic issue',
        'note': 'May also violate formatting rules'
    },
    {
        'line': 19,
        'rule': '12.2',
        'severity': 'Required',
        'code': 'return add(i++, i++);',
        'violation': 'The value of an expression shall be the same under any order of evaluation',
        'details': 'Undefined behavior: modifying i twice in same expression',
        'evidence': 'i++ appears twice as function arguments'
    },
    {
        'line': 19,
        'rule': '12.13',
        'severity': 'Advisory',
        'code': 'return add(i++, i++);',
        'violation': 'The increment (++) and decrement (--) operators should not be mixed with other operators',
        'details': 'Increment operators used within function call',
        'evidence': 'i++ used as function arguments'
    },
    {
        'line': 24,
        'rule': '10.3',
        'severity': 'Required',
        'code': 'return a / b;',
        'violation': 'The value of a complex expression of floating type may only be cast to a narrower floating type',
        'details': 'No check for division by zero (b could be 0)',
        'note': 'Potential runtime error, not strict MISRA but safety issue'
    },
]

print("\nIdentified Violations:\n")
for i, v in enumerate(violations, 1):
    detected_mark = "✓ DETECTED" if v.get('detected') else "✗ MISSED"
    print(f"{i}. Line {v['line']}: Rule {v['rule']} [{v['severity']}] {detected_mark}")
    print(f"   Code: {v['code']}")
    print(f"   Violation: {v['violation']}")
    print(f"   Details: {v['details']}")
    if 'evidence' in v:
        print(f"   Evidence: {v['evidence']}")
    if 'note' in v:
        print(f"   Note: {v['note']}")
    print()

print("=" * 80)
print("DETECTION SUMMARY")
print("=" * 80)

detected = [v for v in violations if v.get('detected')]
missed = [v for v in violations if not v.get('detected')]

print(f"\nDetected: {len(detected)} violations")
for v in detected:
    print(f"  ✓ Line {v['line']}: Rule {v['rule']}")

print(f"\nMissed: {len(missed)} violations")
for v in missed:
    print(f"  ✗ Line {v['line']}: Rule {v['rule']} - {v['violation'][:50]}...")

print("\n" + "=" * 80)
print("WHY VIOLATIONS WERE MISSED")
print("=" * 80)

print("""
1. **Rule 5.1 (Line 3-4): Identifier length**
   WHY MISSED: This is a cross-file/cross-line rule
   - Requires comparing MULTIPLE identifier names
   - Current system analyzes ONE LINE at a time
   - Would need special "cross-reference" agent
   - FIX: Add identifier tracking agent

2. **Rule 2.2 (Line 12): C++ style comments**
   WHY MISSED: AST parser may skip comments
   - Comments might not create AST nodes
   - Regex parser looks for code patterns, not comments
   - FIX: Add comment detection in AST parsing

3. **Rule 16.9 (Line 15): Function definition format**
   WHY MISSED: Style rule, not semantic
   - Single-line function is valid C
   - May not be flagged as distinct violation
   - FIX: Add style checking patterns

4. **Rule 12.2 (Line 19): Sequence point violation**
   WHY POTENTIALLY MISSED: Complex semantic analysis
   - Requires tracking variable modifications
   - LLM may not understand "sequence point" concept
   - FIX: Add few-shot examples for 12.2

5. **Rule 12.13 (Line 19): Increment in expression**
   WHY POTENTIALLY MISSED: Advisory rule, lower priority
   - May have low confidence
   - Filtered out by 0.50 threshold
   - FIX: Lower threshold for advisory rules

6. **Rule 10.3 (Line 24): Division by zero**
   WHY MISSED: Not strictly MISRA, more runtime check
   - MISRA focuses on type casting
   - Division by zero is safety issue, not standard rule
   - FIX: Add safety checking patterns
""")

print("\n" + "=" * 80)
print("RECOMMENDED FIXES")
print("=" * 80)

fixes = [
    {
        'priority': 1,
        'issue': 'Missing Rule 12.2 (i++, i++) - Line 19',
        'fix': 'Add few-shot example for sequence point violations',
        'implementation': '''
Add to verification prompt:
"Example: add(i++, i++) violates 12.2 because i is modified twice 
without sequence point between modifications"
        ''',
        'effort': '10 minutes'
    },
    {
        'priority': 2,
        'issue': 'Missing Rule 2.2 (// comments) - Line 12',
        'fix': 'Add comment detection to regex parser',
        'implementation': '''
In tools/ast_tools.py:
CPP_COMMENT = re.compile(r'//.*$')
if CPP_COMMENT.search(ln):
    nodes.append(node("CPPStyleComment"))
        ''',
        'effort': '15 minutes'
    },
    {
        'priority': 3,
        'issue': 'Missing Rule 5.1 (identifier length) - Lines 3-4',
        'fix': 'Add identifier tracking agent',
        'implementation': '''
New agent that:
1. Collects all identifiers from all files
2. Checks for duplicates in first 31 chars
3. Reports violations across files
        ''',
        'effort': '2-3 hours'
    },
    {
        'priority': 4,
        'issue': 'Missing Rule 12.13 (i++ in expression) - Line 19',
        'fix': 'Lower confidence threshold for advisory rules',
        'implementation': '''
Or: Add specific pattern for increment/decrement in function calls
        ''',
        'effort': '30 minutes'
    },
]

for fix in fixes:
    print(f"\n{fix['priority']}. {fix['issue']}")
    print(f"   Fix: {fix['fix']}")
    print(f"   Implementation:{fix['implementation']}")
    print(f"   Effort: {fix['effort']}")

print("\n" + "=" * 80)
print("IMMEDIATE ACTIONS")
print("=" * 80)

print("""
**Quick Wins (30 minutes total):**

1. Add Rule 12.2 Few-Shot Example (10 min)
   → Should catch line 19 violation

2. Add Comment Detection (15 min)
   → Should catch line 12 violation

3. Add Increment Operator Pattern (5 min)
   → Should catch line 19 rule 12.13

**Expected Result:**
- From 1 detected → 3-4 detected violations
- Still missing: Rule 5.1 (requires cross-file analysis)

**Long-term:**
- Build identifier tracking for Rule 5.1
- Add more semantic analysis patterns
- Improve few-shot examples for all rule families
""")

print("\n" + "=" * 80)
