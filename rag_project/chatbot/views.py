import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_pipeline import load_documents, split_documents, store_embeddings, query_qdrant  # Ensure Django finds rag_pipeline.py

from django.http import JsonResponse
from django.shortcuts import render
from django.core.files.storage import default_storage
from django.conf import settings
from langchain_ollama import OllamaLLM  # ✅ Correct class name

from django.views.decorators.csrf import csrf_exempt



# Load HTML page
def chatbot_interface(request):
    return render(request, "chatbot/index.html")

# Handle PDF file upload
@csrf_exempt
def upload_pdf(request):
    print("entered into upload pdf method")
    if request.method == "POST" and request.FILES.get("pdf"):
        pdf_file = request.FILES["pdf"]
        file_path = os.path.join(settings.MEDIA_ROOT, pdf_file.name)

        # Save the uploaded file
        with open(file_path, "wb+") as destination:
            for chunk in pdf_file.chunks():
                destination.write(chunk)

        # Process the uploaded file (Extract text & create embeddings)
        documents = load_documents(pdf_path=file_path)
        chunks = split_documents(documents)
        store_embeddings(chunks)
        print("processed pdf stored")

        return JsonResponse({"message": f"File '{pdf_file.name}' uploaded and processed successfully!"})

    return JsonResponse({"error": "No file uploaded"}, status=400)

# API for chatbot queries
@csrf_exempt
def chat_query(request):
    if request.method == "POST":
        model = request.POST.get("model", "mistral")  # ✅ Users can select a different model
        query = request.POST.get("query")

        if not query:
            return JsonResponse({"response": "Please enter a query."})

        # Retrieve relevant documents (Always uses Mistral embeddings)
        relevant_docs = query_qdrant(query)
        context = "\n".join(relevant_docs)

        # Ensure the selected model exists in Ollama
        available_models = ["deepseek-r1:7b", "qwen2:latest", "phi:latest", "llama2:latest", "gemma:latest", "mistral:latest"]
        if model not in available_models:
            return JsonResponse({"response": "Selected model is not available."})

        # Generate response using the selected model
        llm = OllamaLLM(model=model)
        response = llm.invoke(f"Based on the following information, answer: {query}\n\n{context}")

        return JsonResponse({"response": response})

    return JsonResponse({"response": "Invalid request method."}, status=400)
