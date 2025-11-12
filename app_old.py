from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings

# 1️⃣ Load the PDF
loader = PyPDFLoader("taxes.pdf")
documents = loader.load()

# 2️⃣ Split into chunks
splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=150)
chunks = splitter.split_documents(documents)

# 3️⃣ Create embeddings (local, free)
embeddings = HuggingFaceEmbeddings(model_name="multi-qa-mpnet-base-dot-v1")

# 4️⃣ Store in FAISS vector database
vectorstore = FAISS.from_documents(chunks, embeddings)

# 5️⃣ Test retrieval
retriever = vectorstore.as_retriever(search_type="mmr",search_kwargs={"k": 3})

query = "what is the COVID-19 vat?"

results = retriever.get_relevant_documents(query)

print("\n🔍 Retrieved Chunks:")
for i, doc in enumerate(results, 1):
    print(f"\n--- Result {i} ---")
    print(doc.page_content[:1000], "...")
