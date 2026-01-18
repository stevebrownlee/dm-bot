"""PDF RAG System for AD&D Rule Books.

This module handles:
- Extracting text from PDF rule books
- Chunking text into searchable segments
- Generating embeddings using Ollama
- Storing in ChromaDB vector database
- Querying for relevant rule sections
"""

import chromadb
import gc
from pathlib import Path
from typing import List, Dict, Optional
from chromadb.api.types import QueryResult
from chromadb.config import Settings
from pypdf import PdfReader
from ollama import Client


class RuleBookRAG:
    """RAG system for AD&D v1 rule books."""

    def __init__(
        self,
        pdf_directory: str = "rule-books",
        db_directory: str = "chroma_db",
        embedding_model: str = "nomic-embed-text",
        collection_name: str = "adnd_rules"
    ):
        """Initialize the RAG system.

        Args:
            pdf_directory: Directory containing PDF files
            db_directory: Directory for ChromaDB storage
            embedding_model: Ollama embedding model to use
            collection_name: Name for the ChromaDB collection
        """
        self.pdf_directory = Path(pdf_directory)
        self.db_directory = Path(db_directory)
        self.embedding_model = embedding_model
        self.collection_name = collection_name

        # Initialize Ollama client
        self.ollama = Client()

        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.db_directory),
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name
        )

    def process_page_streaming(self, pdf_path: Path, page_num: int) -> Optional[Dict[str, any]]:
        """Extract text from a single page without loading entire PDF.

        Args:
            pdf_path: Path to the PDF file
            page_num: Page number to extract (1-indexed)

        Returns:
            Dictionary with page text and metadata, or None if error/empty
        """
        try:
            reader = PdfReader(pdf_path)
            page = reader.pages[page_num - 1]
            text = page.extract_text()

            # CRITICAL: Skip pages with minimal or NO content
            # Many PDFs are scanned images without embedded text
            if not text or len(text.strip()) < 100:
                return None

            page_data = {
                "text": text.strip(),
                "page_number": page_num,
                "book_name": pdf_path.stem,
                "source": pdf_path.name
            }

            # Explicitly delete reader to free memory
            del reader
            gc.collect()

            return page_data

        except Exception as e:
            print(f"      ⚠️  Error on page {page_num}: {e}")
            return None

    def get_pdf_page_count(self, pdf_path: Path) -> int:
        """Get total pages in PDF without loading all content."""
        try:
            reader = PdfReader(pdf_path)
            count = len(reader.pages)
            del reader
            gc.collect()
            return count
        except Exception as e:
            print(f"   ❌ Cannot read PDF: {e}")
            return 0


    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for embedding.

        Args:
            text: Text to chunk
            chunk_size: Target size for each chunk in characters
            overlap: Number of characters to overlap between chunks

        Returns:
            List of text chunks
        """
        # Handle empty or very short text
        if not text or len(text.strip()) <= chunk_size:
            return [text.strip()] if text and len(text.strip()) > 50 else []

        chunks = []
        start = 0
        text_len = len(text)
        min_advance = max(50, chunk_size // 10)  # Minimum 50 chars or 10% advance

        while start < text_len:
            # Get chunk from start to start + chunk_size
            end = min(start + chunk_size, text_len)
            chunk = text[start:end]

            # If not at the end, try to break at a sentence or paragraph
            if end < text_len:
                # Look for paragraph break first
                last_para = chunk.rfind('\n\n')
                if last_para > chunk_size // 2:  # At least halfway through
                    chunk = chunk[:last_para]
                    end = start + last_para
                else:
                    # Look for sentence break
                    last_period = chunk.rfind('. ')
                    if last_period > chunk_size // 2:
                        chunk = chunk[:last_period + 1]
                        end = start + last_period + 1

            chunk = chunk.strip()
            if len(chunk) > 50:
                chunks.append(chunk)

            # Calculate next start with overlap, ensuring forward progress
            next_start = end - overlap

            # CRITICAL: Ensure we always move forward at least min_advance
            if next_start <= start:
                next_start = start + min_advance

            start = next_start

        return chunks


    def index_pdfs(self, batch_size: int = 3, single_file: Optional[str] = None) -> None:
        """Extract and index PDFs with minimal memory footprint.

        Args:
            batch_size: Number of chunks to process before saving (default: 3 for memory)
            single_file: Optional specific PDF filename to index
        """
        if not self.pdf_directory.exists():
            print(f"❌ PDF directory not found: {self.pdf_directory}")
            return

        pdf_files = list(self.pdf_directory.glob("*.pdf"))
        if not pdf_files:
            print(f"❌ No PDF files found in {self.pdf_directory}")
            return

        # Filter to single file if specified
        if single_file:
            pdf_files = [p for p in pdf_files if p.name == single_file]
            if not pdf_files:
                print(f"❌ File not found: {single_file}")
                return

        print(f"\n🚀 Starting memory-efficient indexing...")
        print(f"📍 Model: {self.embedding_model}")
        print(f"💾 Batch size: {batch_size} chunks")
        print(f"📚 Files: {len(pdf_files)}")
        print()

        total_chunks = 0
        batch_documents = []
        batch_embeddings = []
        batch_metadatas = []
        batch_ids = []

        for pdf_path in pdf_files:
            print(f"\n📖 {pdf_path.name}")

            # Get page count without loading full PDF
            page_count = self.get_pdf_page_count(pdf_path)
            if page_count == 0:
                print(f"⚠️  Cannot read PDF")
                continue

            print(f"📄 {page_count} pages")

            # Process ONE page at a time
            for page_num in range(1, page_count + 1):
                print(f"  Processing page {page_num}...", end="", flush=True)

                # Extract single page (memory-efficient)
                page_data = self.process_page_streaming(pdf_path, page_num)

                if not page_data:
                    print(" [SKIP: no text]")
                    continue

                print(f" [{len(page_data['text'])} chars]", end="", flush=True)

                # Chunk the page
                chunks = self.chunk_text(page_data["text"])

                if not chunks:
                    print(" [SKIP: no chunks]")
                    continue

                print(f" -> {len(chunks)} chunks", end="", flush=True)

                # Process each chunk immediately
                for chunk_idx, chunk_text in enumerate(chunks):
                    chunk_id = f"{page_data['book_name']}_p{page_num}_c{chunk_idx}"

                    try:
                        print(".", end="", flush=True)

                        # Generate embedding immediately
                        embedding_response = self.ollama.embeddings(
                            model=self.embedding_model,
                            prompt=chunk_text
                        )
                        embedding = embedding_response["embedding"]

                        # Add to batch
                        batch_documents.append(chunk_text)
                        batch_embeddings.append(embedding)
                        batch_metadatas.append({
                            "book_name": page_data["book_name"],
                            "page_number": page_num,
                            "source": page_data["source"],
                            "chunk_index": chunk_idx
                        })
                        batch_ids.append(chunk_id)

                        # Save when batch full
                        if len(batch_documents) >= batch_size:
                            self.collection.add(
                                documents=batch_documents,
                                embeddings=batch_embeddings,
                                metadatas=batch_metadatas,
                                ids=batch_ids
                            )
                            total_chunks += len(batch_documents)

                            # Aggressive memory cleanup
                            batch_documents = []
                            batch_embeddings = []
                            batch_metadatas = []
                            batch_ids = []
                            del embedding_response, embedding
                            gc.collect()

                            print(f" ✓{total_chunks}", end="", flush=True)

                    except Exception as e:
                        print(f"\n    ❌ Error on chunk {chunk_id}: {e}")
                        continue

                # Clean up page data
                del page_data, chunks
                gc.collect()
                print()  # New line after page

            # Save any remaining chunks after each book
            if batch_documents:
                self.collection.add(
                    documents=batch_documents,
                    embeddings=batch_embeddings,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                total_chunks += len(batch_documents)
                batch_documents = []
                batch_embeddings = []
                batch_metadatas = []
                batch_ids = []
                gc.collect()
                print(f"    💾 Book complete: {total_chunks} total chunks")

        print(f"\n✅ Indexing complete!")
        print(f"📊 Total chunks: {total_chunks}")
        print(f"💾 Location: {self.db_directory}")


    def query_rules(
    self,
    query: str,
    n_results: int = 3,
    book_filter: Optional[str] = None
) -> List[Dict[str, any]]:
        """Search for relevant rule sections using semantic similarity.

        Args:
            query: Search query (e.g., "How does combat work?")
            n_results: Number of results to return
            book_filter: Optional filter by book name (e.g., "players-handbook")

        Returns:
            List of dictionaries containing matched text and metadata
        """
        # Check if collection has any data
        if self.collection.count() == 0:
            print("⚠️  No indexed data found. Run index_pdfs() first!")
            return []

        try:
            # Generate embedding for the query
            query_embedding = self.ollama.embeddings(
                model=self.embedding_model,
                prompt=query
            )["embedding"]

            # Build where clause for filtering
            where_clause = None
            if book_filter:
                where_clause = {"book_name": book_filter}

            # Query ChromaDB
            results: QueryResult = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_clause
            )

            # Format results
            formatted_results = []
            if results["documents"] and results["documents"][0]:
                for idx, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][idx]
                    distance = results["distances"][0][idx] if "distances" in results else None

                    formatted_results.append({
                        "text": doc,
                        "book_name": metadata.get("book_name"),
                        "page_number": metadata.get("page_number"),
                        "source": metadata.get("source"),
                        "relevance_score": 1 - distance if distance else None  # Convert distance to similarity
                    })

            return formatted_results

        except Exception as e:
            print(f"❌ Error querying rules: {e}")
            return []


    def get_collection_stats(self) -> Dict[str, any]:
        """Get statistics about the indexed collection."""
        count = self.collection.count()
        return {
            "total_chunks": count,
            "collection_name": self.collection_name,
            "embedding_model": self.embedding_model
        }
