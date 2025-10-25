"""
CLI utility to build or rebuild the vector index from action logs.

Usage:
    python -m computer_use_demo.build_index
"""

import argparse
import sys
from pathlib import Path

from computer_use_demo.vector_db import ActionVectorDB


def main():
    parser = argparse.ArgumentParser(
        description="Build vector index from action logs"
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
        "--trees",
        type=int,
        default=10,
        help="Number of trees for Annoy index (default: 10)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if index exists",
    )

    args = parser.parse_args()

    # Check if recordings directory exists
    recordings_path = Path(args.recordings_dir)
    if not recordings_path.exists():
        print(f"Error: Recordings directory not found: {recordings_path}")
        sys.exit(1)

    # Initialize VectorDB
    print(f"Initializing VectorDB with model: {args.model}")
    vector_db = ActionVectorDB(
        recordings_dir=args.recordings_dir,
        model_name=args.model,
        n_trees=args.trees,
    )

    # Check if index exists
    if vector_db.index_file.exists() and not args.force:
        print(f"\nIndex already exists at: {vector_db.index_file}")
        print("Use --force to rebuild")
        sys.exit(0)

    # Build index
    print(f"\nBuilding index from logs in: {recordings_path}")
    print("-" * 60)

    num_indexed = vector_db.build_index_from_logs(verbose=True)

    if num_indexed == 0:
        print("\nNo valid action logs found to index")
        sys.exit(1)

    # Save index
    print("\nSaving index to disk...")
    if vector_db.save_index():
        print(f"✓ Index saved successfully")
        print(f"  - Index file: {vector_db.index_file}")
        print(f"  - Metadata file: {vector_db.metadata_file}")
        print(f"  - Total entries: {num_indexed}")
    else:
        print("✗ Failed to save index")
        sys.exit(1)

    # Test query
    print("\n" + "=" * 60)
    print("Testing index with sample query...")
    print("=" * 60)

    # Get first request text from metadata to test
    if vector_db.metadata:
        sample_request = list(vector_db.metadata.values())[0]["request_text"]
        print(f"\nQuery: '{sample_request}'")

        results = vector_db.query_similar(sample_request, k=3, min_similarity=0.0)

        print(f"\nTop {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Similarity: {result['similarity']:.3f}")
            print(f"   Request: {result['request_text']}")
            print(f"   Log: {result['log_file']}")

    print("\n✓ Index built and tested successfully!")


if __name__ == "__main__":
    main()
