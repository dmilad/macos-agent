"""
Interactive test script to query the vector index for similar action logs.

Usage:
    python -m computer_use_demo.test_query
"""

import argparse
import sys
from pathlib import Path

from computer_use_demo.vector_db import ActionVectorDB


def main():
    parser = argparse.ArgumentParser(
        description="Test query vector index for similar action logs"
    )
    parser.add_argument(
        "--recordings-dir",
        type=str,
        default="recordings",
        help="Directory containing action log files (default: recordings)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="all-MiniLM-L6-v2",
        help="Sentence transformer model name (default: all-MiniLM-L6-v2)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of similar results to return (default: 5)",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.0,
        help="Minimum similarity threshold 0-1 (default: 0.0)",
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Query text (if not provided, will prompt interactively)",
    )

    args = parser.parse_args()

    # Check if recordings directory exists
    recordings_path = Path(args.recordings_dir)
    if not recordings_path.exists():
        print(f"Error: Recordings directory not found: {recordings_path}")
        sys.exit(1)

    # Initialize VectorDB
    print(f"Loading VectorDB with model: {args.model}")
    vector_db = ActionVectorDB(
        recordings_dir=args.recordings_dir,
        model_name=args.model,
    )

    # Load existing index
    print("Loading index from disk...")
    if not vector_db.load_index():
        print("\nError: Could not load index. Please build it first:")
        print("    python -m computer_use_demo.build_index")
        sys.exit(1)

    print(f"✓ Index loaded successfully ({vector_db.next_id} entries)")
    print("=" * 70)

    # Query mode: single query or interactive
    if args.query:
        # Single query mode
        query_and_display(vector_db, args.query, args.k, args.min_similarity)
    else:
        # Interactive mode
        print("\nInteractive query mode (type 'quit' or 'exit' to stop)")
        print("=" * 70)

        while True:
            try:
                query_text = input("\nEnter your request: ").strip()

                if query_text.lower() in ["quit", "exit", "q"]:
                    print("\nGoodbye!")
                    break

                if not query_text:
                    print("Please enter a non-empty query")
                    continue

                query_and_display(vector_db, query_text, args.k, args.min_similarity)

            except (KeyboardInterrupt, EOFError):
                print("\n\nGoodbye!")
                break


def query_and_display(
    vector_db: ActionVectorDB,
    query_text: str,
    k: int,
    min_similarity: float,
):
    """Query the vector DB and display results."""
    print(f"\nQuery: '{query_text}'")
    print("-" * 70)

    results = vector_db.query_similar(
        query_text,
        k=k,
        min_similarity=min_similarity,
    )

    if not results:
        print(f"\nNo results found (minimum similarity: {min_similarity})")
        return

    print(f"\nFound {len(results)} similar request(s):\n")

    for i, result in enumerate(results, 1):
        similarity_pct = result['similarity'] * 100

        print(f"{i}. Similarity: {result['similarity']:.4f} ({similarity_pct:.2f}%)")
        print(f"   Request: {result['request_text']}")
        print(f"   Log File: {result['log_file']}")
        print(f"   Timestamp: {result['timestamp']}")

        # Display narrative (truncate if too long)
        narrative = result['narrative']
        if len(narrative) > 200:
            narrative = narrative[:200] + "..."
        print(f"   Narrative: {narrative}")
        print()


if __name__ == "__main__":
    main()
