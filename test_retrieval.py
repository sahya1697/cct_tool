"""
Test script to debug rule retrieval for specific violations.
"""

import sys
from tools.rag_tools import load_rules, retrieve_rules_for_node, get_rule_types_for_node
from tools.ast_tools import parse_c_file

# Load all rules
print("Loading rules...")
all_rules = load_rules("data/rules.json")
print(f"Loaded {len(all_rules)} rules")

# Check which rule families exist
rule_families = {}
for rule in all_rules:
    rule_id = str(rule.get("rule_id", ""))
    family = rule_id.split(".")[0] if "." in rule_id else rule_id
    if family not in rule_families:
        rule_families[family] = []
    rule_families[family].append(rule_id)

print(f"\nRule families present: {sorted(rule_families.keys())}")
print(f"Family 1.x: {len(rule_families.get('1', []))} rules")
print(f"Family 2.x: {len(rule_families.get('2', []))} rules")
print(f"Family 3.x: {len(rule_families.get('3', []))} rules")

# Show some example rules from families 1, 2, 3
print("\n" + "="*80)
print("SAMPLE RULES FROM FAMILIES 1, 2, 3")
print("="*80)

for fam in ['1', '2', '3']:
    if fam in rule_families:
        print(f"\nFamily {fam}.x:")
        for rule in all_rules[:5]:  # Check first 5 rules
            rule_id = str(rule.get("rule_id", ""))
            if rule_id.startswith(f"{fam}."):
                print(f"  Rule {rule_id}: {rule.get('rule', '')[:80]}...")
                print(f"    rule_type: {rule.get('rule_type', 'NONE')}")
                break

# Test retrieval for different node types
print("\n" + "="*80)
print("TESTING RETRIEVAL FOR COMMON NODE TYPES")
print("="*80)

test_nodes = [
    ("CPPStyleComment", "// This is a comment"),
    ("InlineAssembly", "__asm__(\"NOP\");"),
    ("FunctionCall", "printf(\"test\");"),
    ("PointerDeclaration", "int *ptr;"),
    ("VariableDeclaration", "int x = 0;"),
    ("PreprocessorDirective", "#include <stdio.h>"),
    ("MacroDefinition", "#define MAX 100"),
]

for node_type, code in test_nodes:
    print(f"\nNode Type: {node_type}")
    print(f"Code: {code}")
    
    # Get rule types for this node
    rule_types = get_rule_types_for_node(node_type)
    print(f"Mapped to rule types: {rule_types}")
    
    # Retrieve rules
    retrieved = retrieve_rules_for_node(all_rules, node_type, code, max_results=12)
    print(f"Retrieved {len(retrieved)} rules")
    
    # Show rule IDs
    rule_ids = [str(r.get("rule_id", "")) for r in retrieved]
    print(f"Rule IDs: {rule_ids}")
    
    # Check if any 1.x, 2.x, 3.x rules were retrieved
    family_1 = [rid for rid in rule_ids if rid.startswith("1.")]
    family_2 = [rid for rid in rule_ids if rid.startswith("2.")]
    family_3 = [rid for rid in rule_ids if rid.startswith("3.")]
    
    if family_1:
        print(f"  ✓ Family 1.x rules: {family_1}")
    if family_2:
        print(f"  ✓ Family 2.x rules: {family_2}")
    if family_3:
        print(f"  ✓ Family 3.x rules: {family_3}")
    
    if not (family_1 or family_2 or family_3):
        print(f"  ✗ NO rules from families 1, 2, or 3 retrieved!")

# Parse a test file if provided
if len(sys.argv) > 1:
    test_file = sys.argv[1]
    print("\n" + "="*80)
    print(f"PARSING TEST FILE: {test_file}")
    print("="*80)
    
    nodes = parse_c_file(test_file)
    print(f"Found {len(nodes)} AST nodes")
    
    # Test retrieval for each node
    for node in nodes[:10]:  # First 10 nodes
        print(f"\nNode: {node.node_type} (line {node.line})")
        print(f"Code: {node.code[:60]}...")
        
        retrieved = retrieve_rules_for_node(all_rules, node.node_type, node.code, max_results=12)
        rule_ids = [str(r.get("rule_id", "")) for r in retrieved]
        
        family_1 = [rid for rid in rule_ids if rid.startswith("1.")]
        family_2 = [rid for rid in rule_ids if rid.startswith("2.")]
        family_3 = [rid for rid in rule_ids if rid.startswith("3.")]
        
        print(f"Retrieved {len(retrieved)} rules: {rule_ids[:5]}{'...' if len(rule_ids) > 5 else ''}")
        
        if family_1 or family_2 or family_3:
            print(f"  ✓ Found target families: 1.x={family_1}, 2.x={family_2}, 3.x={family_3}")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
