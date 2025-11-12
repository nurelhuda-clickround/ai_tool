import os
import PyPDF2
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Load embedding model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def extract_text_from_pdf(pdf_path):
    """Extract all text from a PDF file."""
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def build_index(data_folder="data"):
    docs, metadata = [], []

    for file in os.listdir(data_folder):
        if file.endswith(".pdf"):
            text = extract_text_from_pdf(os.path.join(data_folder, file))
            chunks = chunk_text(text, chunk_size=100, overlap= 50)  # smaller chunks

            for chunk in chunks:
                if chunk.strip():
                    docs.append(chunk.strip())
                    metadata.append({"source": file})

    embeddings = embedder.encode(docs, normalize_embeddings=True)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(np.array(embeddings, dtype=np.float32))

    return index, docs, metadata

def chunk_text(text, chunk_size=300, overlap=50):
    """Split text into smaller overlapping chunks."""
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap  # move window forward with overlap

    return chunks

def search(query, index, docs, metadata, top_k=5, similarity_threshold=0.3):
    """Search for the most relevant chunks, ensuring diversity across documents."""
    q_emb = embedder.encode([query], normalize_embeddings=True)
    similarities, indices = index.search(np.array(q_emb, dtype=np.float32), len(docs))  # search all

    results = []
    seen_sources = set()

    # Sort all results by similarity
    sorted_matches = sorted(zip(similarities[0], indices[0]), reverse=True)

    for sim, idx in sorted_matches:
        if idx == -1:
            continue
        source = metadata[idx]['source']

        if sim >= similarity_threshold:
            # Pick one chunk per document first
            if source not in seen_sources or len(results) < top_k:
                results.append({
                    "text": docs[idx],
                    "meta": metadata[idx],
                    "similarity": round(float(sim), 3)
                })
                seen_sources.add(source)

        if len(results) >= top_k:
            break

    # Fallback if no results meet threshold
    if not results:
        for sim, idx in sorted_matches[:top_k]:
            results.append({
                "text": docs[idx],
                "meta": metadata[idx],
                "similarity": round(float(sim), 3)
            })

    return results
