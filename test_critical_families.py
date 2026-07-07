"""
Test that critical rule families (1, 2, 3) are properly retrieved and filtered.
"""

from tools.rag_tools import load_rules, retrieve_rules_for_node
from tools.ast_tools import ASTNode

print("=" * 80)
print("TESTING CRITICAL RULE FAMILIES (1, 2, 3)")
print("=" * 80)

# Load rules
rules = load_rules()
print(f"\nLoaded {len(rules)} rules")

# Get families
fam_1 = [r for r in rules if str(r.get('rule_id', '')).startswith('1.')]
fam_2 = [r for r in rules if str(r.get('rule_id', '')).startswith('2.')]
fam_3 = [r for r in rules if str(r.get('rule_id', '')).startswith('3.')]

print(f"Family 1.x: {len(fam_1)} rules - {[r.get('rule_id') for r in fam_1]}")
print(f"Family 2.x: {len(fam_2)} rules - {[r.get('rule_id') for r in fam_2]}")
print(f"Family 3.x: {len(fam_3)} rules - {[r.get('rule_id') for r in fam_3]}")

# Test nodes that should trigger these rules
test_cases = [
    {
        'name': 'Inline Assembly (should trigger 2.1)',
        'node': ASTNode('InlineAssembly', 8, 0, '__asm__(NOP);', 'test.c', 'func'),
        'expected_families': ['2']
    },
    {
        'name': 'C++ Comment (should trigger 2.2)',
        'node': ASTNode('CPPStyleComment', 12, 0, '// comment', 'test.c', 'func'),
        'expected_families': ['2', '3']
    },
    {
        'name': 'Function Definition (should trigger 1.x, 3.x)',
        'node': ASTNode('FunctionDefinition', 1, 0, 'int main(void) { }', 'test.c', 'main'),
        'expected_families': ['1', '3']
    },
    {
        'name': 'Variable Declaration (should trigger 1.x)',
        'node': ASTNode('VariableDeclaration', 5, 0, 'int x = 0;', 'test.c', 'func'),
        'expected_families': ['1']
    },
]

print("\n" + "=" * 80)
print("RETRIEVAL TESTS")
print("=" * 80)

for test in test_cases:
    print(f"\n{test['name']}")
    print(f"  Node: {test['node'].node_type}")
    print(f"  Code: {test['node'].code}")
    
    # Retrieve rules
    retrieved = retrieve_rules_for_node(rules, test['node'].node_type, test['node'].code, max_results=20)
    retrieved_ids = [str(r.get('rule_id', '')) for r in retrieved]
    
    # Check which families were retrieved
    found = {}
    for fam in ['1', '2', '3']:
        found[fam] = [r for r in retrieved_ids if r.startswith(f'{fam}.')]
    
    print(f"  Retrieved {len(retrieved)} rules total")
    print(f"    Family 1.x: {found['1'] if found['1'] else 'NONE'}")
    print(f"    Family 2.x: {found['2'] if found['2'] else 'NONE'}")
    print(f"    Family 3.x: {found['3'] if found['3'] else 'NONE'}")
    
    # Check if expected families were retrieved
    success = True
    for expected_fam in test['expected_families']:
        if not found[expected_fam]:
            print(f"  ✗ FAIL: Expected family {expected_fam}.x but none retrieved!")
            success = False
    
    if success:
        print(f"  ✓ SUCCESS: All expected families retrieved")

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

print("""
Key Changes:
1. Retrieval: Family 1,2,3 rules get +50 score boost
2. Filter threshold: 0.01 for families 1,2,3 (vs 0.10 for others)
3. Base score: 0.50 given to families 1,2,3 in relevance calculation

This ensures families 1, 2, 3 are:
- Always retrieved in top results
- Almost always pass relevance filter
- Available for LLM verification
""")
