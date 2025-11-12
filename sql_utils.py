# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from typing import List, Optional
# import requests
# import uuid

# # Initialize FastAPI app
# app = FastAPI(
#     title="HXAssist RAG API",
#     description="API to fetch ERP invoice data from a PHP system and prepare it for RAG processing.",
#     version="1.0.0"
# )

# # PHP API base URL
# PHP_API_URL = "http://192.168.10.82/hxa/get_hxa_data.php"  # Replace with your PHP API URL

# # Pydantic model for RAG-compatible item
# class Item(BaseModel):
#     id: str
#     source: str
#     text: str
#     similarity: float
#     metadata: dict

# # Helper function to fetch invoices from PHP API
# def fetch_invoices():
#     try:
#         response = requests.get(f"{PHP_API_URL}/invoices")
#         response.raise_for_status()
#         return response.json()
#     except requests.RequestException as e:
#         raise HTTPException(status_code=500, detail=f"Failed to fetch invoices: {str(e)}")

# # Helper function to fetch a specific invoice by ID
# def fetch_invoice_by_id(invoice_id: str):
#     try:
#         response = requests.get(f"{PHP_API_URL}/invoices", params={"id": invoice_id})
#         response.raise_for_status()
#         return response.json()
#     except requests.RequestException as e:
#         raise HTTPException(status_code=500, detail=f"Failed to fetch invoice: {str(e)}")

# # Helper function to format invoice data for RAG
# def format_for_rag(invoice):
#     return {
#         "id": invoice["id"],
#         "source": f"invoice_{invoice['invoice_number']}.json",
#         "text": f"Invoice {invoice['invoice_number']} for {invoice['customer_name']}: {invoice['description']}, Amount: ${invoice['amount']}, Date: {invoice['date']}",
#         "similarity": 0.85,  # Placeholder; replace with actual similarity score from RAG
#         "metadata": {
#             "invoice_number": invoice["invoice_number"],
#             "customer_name": invoice["customer_name"],
#             "amount": invoice["amount"],
#             "date": invoice["date"]
#         }
#     }

# # Endpoint to get all items with optional filtering
# @app.get("/items/", response_model=List[Item])
# async def get_items(customer: Optional[str] = None, min_similarity: Optional[float] = 0.3):
#     """
#     Retrieve a list of invoices formatted for RAG, optionally filtered by customer or minimum similarity.
#     """
#     invoices = fetch_invoices()
#     items = [format_for_rag(invoice) for invoice in invoices]
    
#     # Apply filters
#     if customer:
#         items = [item for item in items if customer.lower() in item["metadata"]["customer_name"].lower()]
#     items = [item for item in items if item["similarity"] >= min_similarity]
    
#     if not items:
#         raise HTTPException(status_code=404, detail="No items found matching the criteria.")
    
#     return items

# # Endpoint to get a specific item by ID
# @app.get("/items/{item_id}", response_model=Item)
# async def get_item(item_id: str):
#     """
#     Retrieve a specific invoice by its ID, formatted for RAG.
#     """
#     invoice = fetch_invoice_by_id(item_id)
#     if "error" in invoice:
#         raise HTTPException(status_code=404, detail=invoice["error"])
#     return format_for_rag(invoice)

# # Root endpoint for welcome message
# @app.get("/")
# async def root():
#     """
#     Welcome message for the HXAssist RAG API.
#     """
#     return {
#         "message": "Welcome to HXAssist RAG API! Use /items/ to retrieve data or /items/{item_id} for a specific item.",
#         "docs": "/docs"
#     }