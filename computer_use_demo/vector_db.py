"""
Vector database for semantic search over action logs using Annoy and sentence-transformers.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from annoy import AnnoyIndex
from sentence_transformers import SentenceTransformer


class ActionVectorDB:
    """
    Vector database for finding similar action logs based on request text.

    Uses sentence-transformers for embeddings and Annoy for fast similarity search.
    """

    def __init__(
        self,
        recordings_dir: str = "recordings",
        model_name: str = "all-MiniLM-L6-v2",
        n_trees: int = 20,
    ):
        """
        Initialize the vector database.

        Args:
            recordings_dir: Directory containing action log JSON files
            model_name: Sentence transformer model name
            n_trees: Number of trees for Annoy index (more trees = better accuracy, slower)
        """
        self.recordings_dir = Path(recordings_dir)
        self.model_name = model_name
        self.n_trees = n_trees

        # Initialize sentence transformer model
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

        # Initialize Annoy index
        self.index = AnnoyIndex(self.embedding_dim, "angular")

        # Metadata: maps index_id -> {request_text, narrative, timestamp, log_file}
        self.metadata: dict[int, dict[str, Any]] = {}
        self.next_id = 0

        # Index files
        self.index_file = self.recordings_dir / "actions.ann"
        self.metadata_file = self.recordings_dir / "index_metadata.json"

    def build_index_from_logs(self, verbose: bool = True) -> int:
        """
        Build Annoy index from all action log files in recordings directory.

        Deduplicates by request text - keeps only the latest recording for each unique request.

        Returns:
            Number of unique requests indexed
        """
        if not self.recordings_dir.exists():
            raise ValueError(f"Recordings directory not found: {self.recordings_dir}")

        # Collect all valid action logs
        log_files = sorted(self.recordings_dir.glob("action_log_*.json"))

        if not log_files:
            if verbose:
                print("No action log files found")
            return 0

        # Group logs by request text, keeping track of timestamps
        request_to_logs: dict[str, list[dict]] = {}

        for log_file in log_files:
            try:
                with open(log_file) as f:
                    data = json.load(f)

                # Extract request text
                request_text = data.get("request", {}).get("content", {}).get("text")
                if not request_text:
                    if verbose:
                        print(f"Skipping {log_file.name}: no request text found")
                    continue

                # Check if narrative exists
                if "narrative" not in data or not data["narrative"]:
                    if verbose:
                        print(f"Skipping {log_file.name}: no narrative found")
                    continue

                # Parse timestamp
                recorded_at = data.get("recorded_at", "")
                try:
                    timestamp = datetime.fromisoformat(recorded_at)
                except (ValueError, TypeError):
                    timestamp = datetime.min

                # Add to grouped logs
                if request_text not in request_to_logs:
                    request_to_logs[request_text] = []

                request_to_logs[request_text].append({
                    "request_text": request_text,
                    "narrative": data["narrative"],
                    "timestamp": timestamp,
                    "log_file": log_file.name,
                })

            except (json.JSONDecodeError, KeyError) as e:
                if verbose:
                    print(f"Error reading {log_file.name}: {e}")
                continue

        # Deduplicate: keep only the latest log for each request text
        unique_logs = []
        for request_text, logs in request_to_logs.items():
            # Sort by timestamp and take the latest
            latest_log = max(logs, key=lambda x: x["timestamp"])
            unique_logs.append(latest_log)

            if verbose and len(logs) > 1:
                print(f"Deduplicated '{request_text}': kept latest from {latest_log['log_file']}")

        # Build index
        for log in unique_logs:
            self._add_to_index_internal(
                request_text=log["request_text"],
                narrative=log["narrative"],
                timestamp=log["timestamp"].isoformat(),
                log_file=log["log_file"],
            )

        # Build the Annoy index
        if self.next_id > 0:
            self.index.build(self.n_trees)
            if verbose:
                print(f"\nIndexed {self.next_id} unique requests from {len(log_files)} log files")

        return self.next_id

    def _add_to_index_internal(
        self,
        request_text: str,
        narrative: str,
        timestamp: str,
        log_file: str,
    ) -> int:
        """
        Internal method to add an entry to the index (without rebuilding).

        Returns:
            The index ID assigned to this entry
        """
        # Embed the request text
        embedding = self.model.encode(request_text)

        # Add to Annoy index
        idx = self.next_id
        self.index.add_item(idx, embedding)

        # Store metadata
        self.metadata[idx] = {
            "request_text": request_text,
            "narrative": narrative,
            "timestamp": timestamp,
            "log_file": log_file,
        }

        self.next_id += 1
        return idx

    def add_to_index(
        self,
        request_text: str,
        narrative: str,
        log_file: str,
    ) -> int:
        """
        Add a new entry to the index and rebuild.

        Use this after recording a new action log to update the index incrementally.

        Args:
            request_text: The user's request text
            narrative: The generated narrative for this request
            log_file: The filename of the action log

        Returns:
            The index ID assigned to this entry
        """
        timestamp = datetime.now().isoformat()

        # Add to index
        idx = self._add_to_index_internal(
            request_text=request_text,
            narrative=narrative,
            timestamp=timestamp,
            log_file=log_file,
        )

        # Rebuild the index
        self.index.build(self.n_trees)

        return idx

    def query_similar(
        self,
        request_text: str,
        k: int = 1,
        min_similarity: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Query for similar requests and return their narratives.

        Args:
            request_text: The query text
            k: Number of similar results to return
            min_similarity: Minimum cosine similarity threshold (0-1)

        Returns:
            List of dicts with keys: request_text, narrative, similarity, log_file
            Sorted by similarity (highest first)
        """
        if self.next_id == 0:
            return []

        # Embed the query
        query_embedding = self.model.encode(request_text)

        # Search in Annoy
        # Annoy returns (index_ids, distances) where distance is angular distance
        indices, distances = self.index.get_nns_by_vector(
            query_embedding,
            k,
            include_distances=True,
        )

        # Convert angular distance to cosine similarity
        # Angular distance d relates to cosine similarity as: cos_sim = 1 - (d^2 / 2)
        # For small distances, we can approximate: cos_sim ≈ 1 - d^2/2
        results = []
        for idx, distance in zip(indices, distances):
            # More accurate conversion from angular distance to cosine similarity
            cosine_similarity = 1.0 - (distance ** 2) / 2.0

            if cosine_similarity >= min_similarity:
                meta = self.metadata[idx]
                results.append({
                    "request_text": meta["request_text"],
                    "narrative": meta["narrative"],
                    "similarity": cosine_similarity,
                    "log_file": meta["log_file"],
                    "timestamp": meta["timestamp"],
                })

        return results

    def save_index(self) -> bool:
        """
        Save the Annoy index and metadata to disk.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure recordings directory exists
            self.recordings_dir.mkdir(parents=True, exist_ok=True)

            # Save Annoy index
            self.index.save(str(self.index_file))

            # Save metadata
            with open(self.metadata_file, "w") as f:
                json.dump(
                    {
                        "model_name": self.model_name,
                        "embedding_dim": self.embedding_dim,
                        "n_trees": self.n_trees,
                        "next_id": self.next_id,
                        "metadata": self.metadata,
                    },
                    f,
                    indent=2,
                )

            return True
        except Exception as e:
            print(f"Error saving index: {e}")
            return False

    def load_index(self) -> bool:
        """
        Load a previously saved Annoy index and metadata from disk.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if files exist
            if not self.index_file.exists() or not self.metadata_file.exists():
                return False

            # Load metadata first
            with open(self.metadata_file) as f:
                data = json.load(f)

            # Verify model compatibility
            if data["model_name"] != self.model_name:
                print(
                    f"Warning: Loaded index uses different model "
                    f"({data['model_name']} vs {self.model_name})"
                )

            if data["embedding_dim"] != self.embedding_dim:
                raise ValueError(
                    f"Embedding dimension mismatch: "
                    f"{data['embedding_dim']} vs {self.embedding_dim}"
                )

            # Restore metadata
            self.next_id = data["next_id"]
            self.metadata = {int(k): v for k, v in data["metadata"].items()}

            # Load Annoy index
            self.index = AnnoyIndex(self.embedding_dim, "angular")
            self.index.load(str(self.index_file))

            return True
        except Exception as e:
            print(f"Error loading index: {e}")
            return False
