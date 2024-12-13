

Personalized Finance Management Using Generative AI

-------------------------------------------------------


Personalized Finance Management Using Generative AI: Leveraging Gemini for Categorized Transaction Insights and Automated Chart Generation

-------------------------------------------------------

Introduction | Overview:

---

Problem Statement:

Managing personal finance can often be a tedious and manual task, especially when dealing with large volumes of financial data. Generating insights from bank transactions, categorizing expenses, and visualizing spending trends are crucial steps for budgeting and financial planning. Traditional methods of manual analysis and chart generation are time-consuming and prone to errors, leading to suboptimal decision-making.
Audience:
This blog is targeted at developers, data analysts, and financial professionals who have basic knowledge of Python and financial analytics. The aim is to provide hands-on guidance for automating financial analysis using Generative AI models like Gemini integrated with cloud services.
Expected Outcome:
By the end of this tutorial, readers will be able to build a system that processes financial PDFs, categorizes transactions, and generates insightful reports along with visualized spending trends. The system will rely on Generative AI for advanced analysis and chart generation, reducing manual efforts and improving the accuracy of financial insights.

---

Design

---
High-level Architecture:
PDF File Upload & Processing: Users upload their financial PDFs containing transaction data.
Text Extraction: Extract relevant transaction data from PDFs using PyPDF2.
Generative AI for Analysis: Use Gemini model to analyze and categorize financial data.
Chart Generation: Generate visual insights using Matplotlib and upload the charts to cloud storage.
Cloud Storage & URLs: Store chart images in Google Cloud Storage for accessibility and easy retrieval.

Design Rationale:
Generative AI Model: The Gemini model offers structured, AI-driven financial analysis by categorizing transactions and generating insights like spending trends, investment recommendations, and savings strategies.
Cloud Storage: Storing charts on Google Cloud ensures scalability, security, and ease of access for further analysis and sharing.

---

Prerequisites:

---

Software & Tools:
Python 3.x
Flask web framework
PyPDF2 library for PDF extraction
Matplotlib for chart generation
Google Cloud SDK for cloud storage interaction

Knowledge:
Basic Python programming.
Familiarity with Generative AI and API integration.
Understanding of financial transactions and data categorization.

Links to Tools:
Python Installation Guide
PyPDF2 Documentation
Google Cloud SDK

Step-by-Step Instructions:

Step 1: Set Up Flask Application
Create a new Flask application and configure it to handle file uploads.
from flask import Flask, render_template, request, jsonify
import os
import requests
import io
import time
from google.cloud import storage
import google.generativeai as genai
import json
import PyPDF2
import matplotlib.pyplot as plt
import base64
import uuid
app = Flask(__name__)
Step 2: Initialize Cloud Storage Client
Configure Google Cloud Storage client for storing chart images.
storage_client = storage.Client()
Step 3: Upload Chart to Cloud Storage
Function to upload the generated charts to Google Cloud Storage.
def upload_to_cloud_storage(file, mime_type='image/png'):
    bucket_name = "bank_transaction_data"  # Replace with your bucket name
    blob_name = f"{uuid.uuid4()}.png"
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_file(file, content_type=mime_type)
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
Step 4: Extract Text from PDF
Extract transaction data from uploaded PDFs.
def extract_text_from_pdf(pdf_url):
    response = requests.get(pdf_url)
    response.raise_for_status()
    pdf_file = io.BytesIO(response.content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text += page.extract_text()
    return text
Step 5: Generate Charts
Using matplotlib, generate spending-related charts and upload them.
def generate_charts(chart_data):
    image_urls = []
    if not chart_data:
        return image_urls
    try:
        chart_json = json.loads(chart_data.strip())
    except json.JSONDecodeError:
        print("Chart data is invalid, skipping")
        return image_urls
    import matplotlib
    matplotlib.use('Agg')  # Use non-interactive backend for matplotlib
    if "monthly_spending" in chart_json and chart_json["monthly_spending"]:
        months = [item["month"] for item in chart_json["monthly_spending"]]
        spending = [float(item["total_spending"]) for item in chart_json["monthly_spending"]]
        plt.figure(figsize=(10, 5))
        plt.bar(months, spending)
        plt.xlabel("Month")
        plt.ylabel("Total Spending")
        plt.title("Monthly Spending")
        plt.tight_layout()
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_url = upload_to_cloud_storage(buffer)
        image_urls.append(image_url)
        plt.close()

---

Result / Demo
Output & Charts:
Once the process is complete, the system will generate:
Categorized transaction summary.
Spending trend analysis.
Charts like monthly spending trends, spending categories, and closing balances.

Example Chart (Monthly Spending):
Chart Example 1: Monthly Spending Breakdown

Example Chart (Spending Categories):
Chart Example 2: Spending Categories Proportion

---

What's Next?
Advanced Custom Categories: Extend the model to support custom categories as per user requirements.
Trend Analysis over Time: Analyze patterns over multiple years for long-term financial planning.
Integration with Financial Tools: Connect this system with budgeting tools or personal finance dashboards for seamless management.
