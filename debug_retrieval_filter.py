"""
Debug script to trace rule retrieval and filtering for test files.
"""

import sys
from tools.rag_tools import load_rules, retrieve_rules_for_node, get_rule_types_for_node
from tools.ast_tools import parse_c_file
from agents.relevance_filter import RelevanceFilterAgent
from agents.log_follower import LogFollowerAgent

# Load rules
print("Loading rules...")
all_rules = load_rules("data/rules.json")
print(f"Loaded {len(all_rules)} rules\n")

# Get rules from families 1, 2, 3
fam_1_rules = [r for r in all_rules if str(r.get('rule_id', '')).startswith('1.')]
fam_2_rules = [r for r in all_rules if str(r.get('rule_id', '')).startswith('2.')]
fam_3_rules = [r for r in all_rules if str(r.get('rule_id', '')).startswith('3.')]

print(f"Family 1.x: {len(fam_1_rules)} rules - IDs: {[r.get('rule_id') for r in fam_1_rules]}")
print(f"Family 2.x: {len(fam_2_rules)} rules - IDs: {[r.get('rule_id') for r in fam_2_rules]}")
print(f"Family 3.x: {len(fam_3_rules)} rules - IDs: {[r.get('rule_id') for r in fam_3_rules]}")
print()

# Initialize filter
log_agent = LogFollowerAgent()
filter_agent = RelevanceFilterAgent(log_agent)

# Test files
test_files = [
    "data/tests/one.c",
    "data/tests/two.c", 
    "data/tests/three.c"
]

if len(sys.argv) > 1:
    test_files = sys.argv[1:]

for test_file in test_files:
    print("=" * 80)
    print(f"FILE: {test_file}")
    print("=" * 80)
    
    # Parse file
    nodes = parse_c_file(test_file)
    print(f"Parsed {len(nodes)} AST nodes\n")
    
    # Track which rules reach each stage
    rules_retrieved = set()
    rules_passed_filter = set()
    
    # Analyze each node
    for idx, node in enumerate(nodes):
        print(f"\n--- Node {idx+1}/{len(nodes)}: {node.node_type} (line {node.line}) ---")
        print(f"Code snippet: {node.code[:80].replace(chr(10), ' ')}...")
        
        # Get mapped rule types
        rule_types = get_rule_types_for_node(node.node_type)
        print(f"Mapped rule types: {rule_types}")
        
        # Retrieve rules
        retrieved = retrieve_rules_for_node(all_rules, node.node_type, node.code, max_results=12)
        retrieved_ids = [str(r.get('rule_id', '')) for r in retrieved]
        
        fam_1_ret = [r for r in retrieved_ids if r.startswith('1.')]
        fam_2_ret = [r for r in retrieved_ids if r.startswith('2.')]
        fam_3_ret = [r for r in retrieved_ids if r.startswith('3.')]
        
        print(f"Retrieved {len(retrieved)} rules: {retrieved_ids[:8]}{' ...' if len(retrieved_ids) > 8 else ''}")
        
        if fam_1_ret or fam_2_ret or fam_3_ret:
            print(f"  ✓ Target families retrieved:")
            if fam_1_ret:
                print(f"    1.x: {fam_1_ret}")
            if fam_2_ret:
                print(f"    2.x: {fam_2_ret}")
            if fam_3_ret:
                print(f"    3.x: {fam_3_ret}")
            
            # Track retrieved
            for rid in fam_1_ret + fam_2_ret + fam_3_ret:
                rules_retrieved.add(rid)
        else:
            print(f"  ✗ No target family rules (1.x, 2.x, 3.x) retrieved")
        
        # Apply relevance filter
        if retrieved:
            filtered = filter_agent.filter_rules(node, retrieved)
            filtered_ids = [str(r.get('rule_id', '')) for r in filtered]
            
            fam_1_filt = [r for r in filtered_ids if r.startswith('1.')]
            fam_2_filt = [r for r in filtered_ids if r.startswith('2.')]
            fam_3_filt = [r for r in filtered_ids if r.startswith('3.')]
            
            print(f"After filter: {len(filtered)} rules passed")
            
            if fam_1_filt or fam_2_filt or fam_3_filt:
                print(f"  ✓ Target families passed filter:")
                if fam_1_filt:
                    print(f"    1.x: {fam_1_filt}")
                if fam_2_filt:
                    print(f"    2.x: {fam_2_filt}")
                if fam_3_filt:
                    print(f"    3.x: {fam_3_filt}")
                
                # Track passed filter
                for rid in fam_1_filt + fam_2_filt + fam_3_filt:
                    rules_passed_filter.add(rid)
            else:
                if fam_1_ret or fam_2_ret or fam_3_ret:
                    print(f"  ✗ Target families were FILTERED OUT!")
                    print(f"    Retrieved but filtered: 1.x={fam_1_ret}, 2.x={fam_2_ret}, 3.x={fam_3_ret}")
    
    # Summary for this file
    print("\n" + "=" * 80)
    print(f"SUMMARY FOR {test_file}")
    print("=" * 80)
    print(f"Total nodes processed: {len(nodes)}")
    print(f"Family 1.x rules retrieved: {sorted([r for r in rules_retrieved if r.startswith('1.')])}")
    print(f"Family 2.x rules retrieved: {sorted([r for r in rules_retrieved if r.startswith('2.')])}")
    print(f"Family 3.x rules retrieved: {sorted([r for r in rules_retrieved if r.startswith('3.')])}")
    print()
    print(f"Family 1.x rules PASSED FILTER: {sorted([r for r in rules_passed_filter if r.startswith('1.')])}")
    print(f"Family 2.x rules PASSED FILTER: {sorted([r for r in rules_passed_filter if r.startswith('2.')])}")
    print(f"Family 3.x rules PASSED FILTER: {sorted([r for r in rules_passed_filter if r.startswith('3.')])}")
    print()
    
    # Calculate what's missing
    all_fam_1_ids = set(str(r.get('rule_id', '')) for r in fam_1_rules)
    all_fam_2_ids = set(str(r.get('rule_id', '')) for r in fam_2_rules)
    all_fam_3_ids = set(str(r.get('rule_id', '')) for r in fam_3_rules)
    
    fam_1_never_retrieved = all_fam_1_ids - rules_retrieved
    fam_2_never_retrieved = all_fam_2_ids - rules_retrieved
    fam_3_never_retrieved = all_fam_3_ids - rules_retrieved
    
    fam_1_filtered_out = set([r for r in rules_retrieved if r.startswith('1.')]) - rules_passed_filter
    fam_2_filtered_out = set([r for r in rules_retrieved if r.startswith('2.')]) - rules_passed_filter
    fam_3_filtered_out = set([r for r in rules_retrieved if r.startswith('3.')]) - rules_passed_filter
    
    print("PROBLEMS IDENTIFIED:")
    if fam_1_never_retrieved:
        print(f"  ✗ Family 1.x NEVER RETRIEVED: {sorted(fam_1_never_retrieved)}")
    if fam_2_never_retrieved:
        print(f"  ✗ Family 2.x NEVER RETRIEVED: {sorted(fam_2_never_retrieved)}")
    if fam_3_never_retrieved:
        print(f"  ✗ Family 3.x NEVER RETRIEVED: {sorted(fam_3_never_retrieved)}")
    if fam_1_filtered_out:
        print(f"  ✗ Family 1.x FILTERED OUT: {sorted(fam_1_filtered_out)}")
    if fam_2_filtered_out:
        print(f"  ✗ Family 2.x FILTERED OUT: {sorted(fam_2_filtered_out)}")
    if fam_3_filtered_out:
        print(f"  ✗ Family 3.x FILTERED OUT: {sorted(fam_3_filtered_out)}")
    
    print("\n")

print("=" * 80)
print("DEBUGGING COMPLETE")
print("=" * 80)
