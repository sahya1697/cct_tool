"""
Threshold Optimizer - Find optimal relevance and critical thresholds.

This script analyzes a C file and rule type to determine the best threshold values
that maximize filtering (reduce LLM calls) while ensuring relevant rules pass through.

Usage:
    python optimize_thresholds.py <c_file> <rule_type>
    python optimize_thresholds.py data/tests/one.c "Language extensions"
    python optimize_thresholds.py data/tests/two.c "Environment"
"""

import sys
import argparse
from collections import defaultdict
from typing import Dict, List, Tuple

from tools.rag_tools import load_rules, retrieve_rules_for_node
from tools.ast_tools import parse_c_file
from agents.relevance_filter import RelevanceFilterAgent
from agents.log_follower import LogFollowerAgent


def analyze_scores(c_file: str, target_rule_type: str = None) -> Dict:
    """
    Analyze relevance scores for all node-rule combinations in a file.
    
    Args:
        c_file: Path to C source file
        target_rule_type: Optional rule type to focus on (e.g., "Environment", "Language extensions")
        
    Returns:
        Dictionary with analysis results
    """
    print("=" * 80)
    print("THRESHOLD OPTIMIZATION ANALYSIS")
    print("=" * 80)
    print(f"File: {c_file}")
    print(f"Target rule type: {target_rule_type or 'ALL'}")
    print()
    
    # Load rules and parse file
    all_rules = load_rules()
    nodes = parse_c_file(c_file)
    
    print(f"Loaded {len(all_rules)} rules")
    print(f"Parsed {len(nodes)} AST nodes")
    
    # Filter rules by type if specified
    if target_rule_type:
        rules = [r for r in all_rules if r.get('rule_type') == target_rule_type]
        print(f"Filtered to {len(rules)} rules of type '{target_rule_type}'")
    else:
        rules = all_rules
    
    # Group rules by family
    rule_families = defaultdict(list)
    for rule in rules:
        rule_id = str(rule.get('rule_id', ''))
        family = rule_id.split('.')[0] if '.' in rule_id else rule_id
        rule_families[family].append(rule)
    
    print(f"Rule families: {dict((k, len(v)) for k, v in rule_families.items())}")
    print()
    
    # Create filter agent
    filter_agent = RelevanceFilterAgent(None)
    
    # Collect all scores
    all_scores = []
    scores_by_family = defaultdict(list)
    scores_by_node_type = defaultdict(list)
    
    print("Calculating relevance scores...")
    print()
    
    for node_idx, node in enumerate(nodes):
        # Retrieve relevant rules for this node
        retrieved = retrieve_rules_for_node(all_rules, node.node_type, node.code, max_results=20)
        
        # Filter to target rules
        if target_rule_type:
            retrieved = [r for r in retrieved if r.get('rule_type') == target_rule_type]
        
        if not retrieved:
            continue
        
        for rule in retrieved:
            rule_id = str(rule.get('rule_id', ''))
            family = rule_id.split('.')[0] if '.' in rule_id else rule_id
            
            # Calculate score
            score, reason = filter_agent._calculate_relevance_score(rule, node)
            
            # Store score
            all_scores.append(score)
            scores_by_family[family].append(score)
            scores_by_node_type[node.node_type].append(score)
    
    print(f"Analyzed {len(all_scores)} node-rule combinations")
    print()
    
    return {
        'all_scores': all_scores,
        'scores_by_family': dict(scores_by_family),
        'scores_by_node_type': dict(scores_by_node_type),
        'rule_families': dict(rule_families),
        'num_nodes': len(nodes),
        'num_rules': len(rules),
    }


def calculate_optimal_thresholds(analysis: Dict, filter_rate_target: float = 0.70) -> Dict:
    """
    Calculate optimal thresholds based on score distribution.
    
    Args:
        analysis: Analysis results from analyze_scores()
        filter_rate_target: Target filter rate (0.0-1.0), e.g., 0.70 means filter 70% of checks
        
    Returns:
        Dictionary with recommended thresholds
    """
    all_scores = sorted(analysis['all_scores'])
    scores_by_family = analysis['scores_by_family']
    
    if not all_scores:
        return {
            'error': 'No scores to analyze',
        }
    
    print("=" * 80)
    print("SCORE DISTRIBUTION ANALYSIS")
    print("=" * 80)
    
    # Overall statistics
    min_score = min(all_scores)
    max_score = max(all_scores)
    mean_score = sum(all_scores) / len(all_scores)
    median_score = all_scores[len(all_scores) // 2]
    
    print(f"\nOverall Statistics:")
    print(f"  Total combinations: {len(all_scores)}")
    print(f"  Min score:  {min_score:.4f}")
    print(f"  Max score:  {max_score:.4f}")
    print(f"  Mean score: {mean_score:.4f}")
    print(f"  Median:     {median_score:.4f}")
    
    # Percentiles
    percentiles = [10, 25, 50, 75, 90, 95, 99]
    print(f"\nScore Percentiles:")
    for p in percentiles:
        idx = int(len(all_scores) * p / 100)
        score = all_scores[min(idx, len(all_scores) - 1)]
        print(f"  {p:2d}th percentile: {score:.4f}")
    
    # Calculate optimal standard threshold
    # Target: filter X% of checks, pass (100-X)%
    filter_idx = int(len(all_scores) * filter_rate_target)
    standard_threshold = all_scores[filter_idx] if filter_idx < len(all_scores) else max_score
    
    print(f"\n" + "=" * 80)
    print(f"RECOMMENDED THRESHOLDS (Target: {filter_rate_target*100:.0f}% filter rate)")
    print("=" * 80)
    
    print(f"\nStandard Threshold: {standard_threshold:.4f}")
    print(f"  → Would filter {filter_rate_target*100:.0f}% of checks")
    print(f"  → Would pass {(1-filter_rate_target)*100:.0f}% to LLM verification")
    
    # Calculate family-specific thresholds
    family_thresholds = {}
    
    print(f"\nFamily-Specific Analysis:")
    for family, scores in sorted(scores_by_family.items()):
        if not scores:
            continue
        
        sorted_scores = sorted(scores)
        fam_min = min(scores)
        fam_max = max(scores)
        fam_mean = sum(scores) / len(scores)
        fam_median = sorted_scores[len(sorted_scores) // 2]
        
        # For critical families (1, 2, 3), use lower threshold
        if family in {'1', '2', '3'}:
            # Use 10th percentile for critical families
            fam_threshold_idx = int(len(sorted_scores) * 0.10)
            fam_threshold = sorted_scores[fam_threshold_idx]
            label = "CRITICAL"
        else:
            # Use target filter rate for other families
            fam_threshold_idx = int(len(sorted_scores) * filter_rate_target)
            fam_threshold = sorted_scores[fam_threshold_idx] if fam_threshold_idx < len(sorted_scores) else fam_max
            label = "STANDARD"
        
        family_thresholds[family] = fam_threshold
        
        print(f"\n  Family {family}.x ({label}):")
        print(f"    Combinations: {len(scores)}")
        print(f"    Min/Max:  {fam_min:.4f} / {fam_max:.4f}")
        print(f"    Mean:     {fam_mean:.4f}")
        print(f"    Median:   {fam_median:.4f}")
        print(f"    → Recommended threshold: {fam_threshold:.4f}")
    
    # Calculate critical threshold (for families 1, 2, 3)
    critical_families = {'1', '2', '3'}
    critical_scores = []
    for family in critical_families:
        if family in scores_by_family:
            critical_scores.extend(scores_by_family[family])
    
    if critical_scores:
        critical_scores = sorted(critical_scores)
        # Use 5th percentile for critical families (very permissive)
        critical_threshold_idx = int(len(critical_scores) * 0.05)
        critical_threshold = critical_scores[critical_threshold_idx]
    else:
        critical_threshold = 0.01
    
    print(f"\n" + "=" * 80)
    print(f"FINAL RECOMMENDATIONS")
    print("=" * 80)
    
    print(f"\nFor config.py or relevance_filter.py:")
    print(f"  RELEVANCE_THRESHOLD = {standard_threshold:.4f}  # Standard threshold")
    print(f"  CRITICAL_THRESHOLD = {critical_threshold:.4f}   # For families 1, 2, 3")
    
    print(f"\nExpected Results:")
    checks_total = len(all_scores)
    checks_filtered = int(checks_total * filter_rate_target)
    checks_passed = checks_total - checks_filtered
    print(f"  Total checks: {checks_total}")
    print(f"  Filtered: {checks_filtered} ({filter_rate_target*100:.0f}%)")
    print(f"  Passed to LLM: {checks_passed} ({(1-filter_rate_target)*100:.0f}%)")
    
    # Calculate actual filter rate with recommended thresholds
    filtered_count = sum(1 for score in all_scores if score < standard_threshold)
    actual_filter_rate = filtered_count / len(all_scores) if all_scores else 0
    
    print(f"\nActual filter rate with standard threshold {standard_threshold:.4f}: {actual_filter_rate*100:.1f}%")
    
    return {
        'standard_threshold': standard_threshold,
        'critical_threshold': critical_threshold,
        'family_thresholds': family_thresholds,
        'statistics': {
            'min': min_score,
            'max': max_score,
            'mean': mean_score,
            'median': median_score,
        },
        'filter_rate_target': filter_rate_target,
        'actual_filter_rate': actual_filter_rate,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Optimize relevance filter thresholds for MISRA C compliance checking',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a specific file for all rule types
  python optimize_thresholds.py data/tests/one.c
  
  # Analyze for specific rule type
  python optimize_thresholds.py data/tests/two.c "Language extensions"
  
  # Analyze with custom filter rate target
  python optimize_thresholds.py data/tests/three.c "Environment" --filter-rate 0.80
  
Available rule types:
  - Environment
  - Language extensions
  - Documentation
  - Functions
  - Expressions
  - Control flow
  - Declarations and definitions
  - Types
  - Pointers and arrays
  (and more - see data/rules.json for complete list)
"""
    )
    
    parser.add_argument(
        'c_file',
        help='Path to C source file to analyze'
    )
    
    parser.add_argument(
        'rule_type',
        nargs='?',
        default=None,
        help='Rule type to focus on (optional, defaults to ALL)'
    )
    
    parser.add_argument(
        '--filter-rate',
        type=float,
        default=0.70,
        help='Target filter rate (0.0-1.0), e.g., 0.70 = filter 70%% of checks (default: 0.70)'
    )
    
    args = parser.parse_args()
    
    # Validate filter rate
    if not 0.0 <= args.filter_rate <= 1.0:
        print(f"Error: filter-rate must be between 0.0 and 1.0")
        return 1
    
    try:
        # Analyze scores
        analysis = analyze_scores(args.c_file, args.rule_type)
        
        if not analysis['all_scores']:
            print("\nNo rules found for the specified criteria.")
            print("Try a different file or rule type.")
            return 1
        
        # Calculate optimal thresholds
        recommendations = calculate_optimal_thresholds(analysis, args.filter_rate)
        
        if 'error' in recommendations:
            print(f"\nError: {recommendations['error']}")
            return 1
        
        print("\n" + "=" * 80)
        print("OPTIMIZATION COMPLETE")
        print("=" * 80)
        print("\nUpdate your agents/relevance_filter.py with the recommended thresholds.")
        
        return 0
        
    except FileNotFoundError:
        print(f"Error: File not found: {args.c_file}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
