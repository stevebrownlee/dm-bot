#!/usr/bin/env python3
"""Script to index AD&D rule books into ChromaDB.

Run this once to build the vector database:
    python index_rulebooks.py

Or to re-index (clears existing data):
    python index_rulebooks.py --rebuild
"""

import sys
import argparse
from pathlib import Path
from pdf_rag import RuleBookRAG


def main():
    parser = argparse.ArgumentParser(
        description="Index AD&D PDF rule books for RAG system"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Clear existing index and rebuild from scratch"
    )
    parser.add_argument(
        "--pdf-dir",
        default="rule-books",
        help="Directory containing PDF files (default: rule-books)"
    )
    parser.add_argument(
        "--db-dir",
        default="chroma_db",
        help="Directory for ChromaDB storage (default: chroma_db)"
    )
    parser.add_argument(
        "--single-file",
        type=str,
        default=None,
        help="Index only a specific PDF file (e.g., 'players-handbook.pdf')"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=3,
        help="Number of chunks to process at once (default: 3 for memory efficiency)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🎲 AD&D Rule Book Indexer 🎲")
    print("=" * 60)

    # Check if PDF directory exists
    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.exists():
        print(f"\n❌ Error: PDF directory not found: {pdf_dir}")
        print(f"Please create the directory and add your PDF files.")
        sys.exit(1)

    pdf_count = len(list(pdf_dir.glob("*.pdf")))
    if pdf_count == 0:
        print(f"\n❌ Error: No PDF files found in {pdf_dir}")
        sys.exit(1)

    print(f"\n📚 Found {pdf_count} PDF file(s)")

    # Initialize RAG system
    print(f"\n🔧 Initializing RAG system...")
    rag = RuleBookRAG(
        pdf_directory=args.pdf_dir,
        db_directory=args.db_dir
    )

    # Check if we need to rebuild
    if args.rebuild:
        print(f"\n⚠️  Rebuild flag set - clearing existing index...")
        try:
            import shutil
            if Path(args.db_dir).exists():
                shutil.rmtree(args.db_dir)
                print(f"✅ Cleared {args.db_dir}")
            # Reinitialize after clearing
            rag = RuleBookRAG(
                pdf_directory=args.pdf_dir,
                db_directory=args.db_dir
            )
        except Exception as e:
            print(f"❌ Error clearing database: {e}")
            sys.exit(1)

    # Check existing index
    stats = rag.get_collection_stats()
    if stats["total_chunks"] > 0:
        print(f"\n📊 Existing index found: {stats['total_chunks']} chunks")
        response = input("Continue and add more? (y/n): ").strip().lower()
        if response != 'y':
            print("\nIndexing cancelled.")
            sys.exit(0)

    # Run indexing
    if args.single_file:
        print(f"\n🚀 Indexing single file: {args.single_file}")
    else:
        print(f"\n🚀 Starting indexing process...")
        print(f"⏰ This may take 10-20 minutes for 4 books...")
    print(f"💡 Tip: Make sure Ollama is running and nomic-embed-text is pulled!\n")

    try:
        rag.index_pdfs(
            batch_size=args.batch_size,
            single_file=args.single_file
        )

        # Show final stats
        final_stats = rag.get_collection_stats()
        print(f"\n" + "=" * 60)
        print(f"✅ INDEXING COMPLETE!")
        print(f"=" * 60)
        print(f"📊 Total chunks: {final_stats['total_chunks']}")
        print(f"💾 Database: {args.db_dir}/")
        print(f"🔧 Model: {final_stats['embedding_model']}")
        print(f"\n🎉 Your rule books are now searchable!")

    except Exception as e:
        print(f"\n❌ Error during indexing: {e}")
        print(f"\nMake sure:")
        print(f"  1. Ollama is running (ollama serve)")
        print(f"  2. Embedding model is installed (ollama pull nomic-embed-text)")
        sys.exit(1)


if __name__ == "__main__":
    main()
