"""Test script to verify all 3 citation types are properly detected."""

import sys

from loguru import logger

from citation import CitationExtractor

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO")


def test_all_citation_types():
    """Test detection of all 3 main citation types."""
    print("=" * 70)
    print("Testing All Citation Types Detection")
    print("=" * 70)

    # Sample text with all 3 citation types
    test_text = """
    Research shows that transformers are effective (Smith et al., 2020).
    Multiple studies confirm this finding (Brown, 2019; Jones et al., 2021).

    Neural networks have been widely studied [1]. Recent advances [2,3]
    demonstrate improved performance. Earlier work [5-8] laid the foundation.

    Language models show promise [LeCun et al.]. The architecture
    [Vaswani and Shazeer] has been influential.

    Early work on attention mechanisms¹ was groundbreaking. Subsequent
    research² expanded these concepts. More recent studies³ have shown
    additional benefits.

    Alternative notation^1 is also used in some papers. Follow-up work^2
    confirmed the initial findings^3.
    """

    print("\n[1/2] Initializing CitationExtractor...")
    extractor = CitationExtractor(context_window=100)
    print("   [OK] CitationExtractor initialized")

    print("\n[2/2] Testing citation extraction on sample text...")
    print("-" * 70)

    try:
        result = extractor.extract(test_text)

        print(f"\n[OK] Total citations found: {result.total_count}")
        print(f"[OK] Unique citations: {len(result.unique_markers)}")

        # Count by type
        type_counts = {}
        for citation in result.citations:
            cite_type = citation.citation_type
            type_counts[cite_type] = type_counts.get(cite_type, 0) + 1

        print(f"\nCitations by type:")
        print(f"   - Parenthetical/Author-Year: {type_counts.get('author-year', 0)}")
        print(f"   - Numerical (brackets): {type_counts.get('numeric', 0)}")
        print(f"   - Named (brackets): {type_counts.get('named', 0)}")
        print(f"   - Footnote/Endnote: {type_counts.get('footnote', 0)}")

        print(f"\nSample citations by type:")

        # Show examples of each type
        for cite_type in ['author-year', 'numeric', 'named', 'footnote']:
            examples = [c.marker for c in result.citations if c.citation_type == cite_type]
            if examples:
                print(f"\n   {cite_type.upper()}:")
                for ex in examples[:3]:  # Show max 3 examples
                    print(f"      - {ex}")

        print("\n" + "=" * 70)

        # Verification
        all_types_present = all([
            type_counts.get('author-year', 0) > 0,
            type_counts.get('numeric', 0) > 0,
            type_counts.get('footnote', 0) > 0
        ])

        if all_types_present:
            print("\n[SUCCESS] All 3 main citation types detected!")
            print("\n  [OK] Parenthetical/Author-Date (APA, MLA, Harvard)")
            print("  [OK] Numerical (IEEE, Vancouver)")
            print("  [OK] Footnote/Endnote (Chicago, Oxford)")
            print("\n[OK] Week 2 Citation Intelligence is fully functional!")
            return 0
        else:
            print("\n[FAILED] Not all citation types were detected")
            missing = []
            if type_counts.get('author-year', 0) == 0:
                missing.append("Parenthetical/Author-Year")
            if type_counts.get('numeric', 0) == 0:
                missing.append("Numerical")
            if type_counts.get('footnote', 0) == 0:
                missing.append("Footnote/Endnote")
            print(f"  Missing types: {', '.join(missing)}")
            return 1

    except Exception as e:
        print(f"\n[ERROR] Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = test_all_citation_types()
    sys.exit(exit_code)
