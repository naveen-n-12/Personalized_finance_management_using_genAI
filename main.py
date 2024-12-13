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

# Initialize Cloud Storage client
storage_client = storage.Client()

# Configure Gemini API
genai.configure(api_key="AIzaSyAZiHrGWqHLR_WuV6ep6W4G_vjni9QJhuM")  # Replace with your actual API key

def upload_to_cloud_storage(file, mime_type='image/png'):
    bucket_name = "bank_transaction_data"  # Replace with your bucket name
    blob_name = f"{uuid.uuid4()}.png"
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_file(file, content_type=mime_type)

    # Construct public URL manually
    return f"https://storage.googleapis.com/{bucket_name}/{blob_name}"



def extract_text_from_pdf(pdf_url):
    """Downloads and extracts text from a PDF using PyPDF2."""
    response = requests.get(pdf_url)
    response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

    pdf_file = io.BytesIO(response.content)
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text += page.extract_text()
    return text


def generate_charts(chart_data):
    """Generates charts using matplotlib and uploads them to cloud storage"""
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

    # Create Monthly Spending Chart
    if "monthly_spending" in chart_json and chart_json["monthly_spending"]:
        months = [item["month"] for item in chart_json["monthly_spending"]]
        spending = []
        for item in chart_json["monthly_spending"]:
            try:
                spending_value = float(item["total_spending"])
            except ValueError:
                spending_value = 0
            spending.append(spending_value)

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

    # Create Spending Category Chart
    if "spending_categories" in chart_json and chart_json["spending_categories"]:
        for item in chart_json["spending_categories"]:
            month = item["month"]
            categories = item["categories"]
            labels = list(categories.keys())

            # Convert values to numbers (handle invalid types)
            try:
                values = [float(value) for value in categories.values()]
            except ValueError:
                print(f"Invalid value found in spending categories for {month}, skipping.")
                continue

            if any(value < 0 for value in values):  # Validate values
                print(f"Negative values found in spending categories for {month}, skipping.")
                continue

            plt.figure(figsize=(10, 5))
            plt.pie(values, labels=labels, autopct='%1.1f%%')
            plt.title(f"Spending Categories - {month}")
            plt.tight_layout()
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_url = upload_to_cloud_storage(buffer)
            image_urls.append(image_url)
            plt.close()

    # Create Monthly Closing Balance Chart
    if "monthly_closing_balance" in chart_json and chart_json["monthly_closing_balance"]:
        months = [item["month"] for item in chart_json["monthly_closing_balance"]]
        try:
            balances = [float(item["closing_balance"]) for item in chart_json["monthly_closing_balance"]]
        except ValueError:
            print("Invalid values found in monthly closing balance, skipping.")
            return image_urls

        plt.figure(figsize=(10, 5))
        plt.plot(months, balances)
        plt.xlabel("Month")
        plt.ylabel("Closing Balance")
        plt.title("Monthly Closing Balance")
        plt.tight_layout()
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        image_url = upload_to_cloud_storage(buffer)
        image_urls.append(image_url)
        plt.close()

    return image_urls





def fetch_gemini_response(file_urls, custom_categories):
    """Fetches the categorized transaction details from Gemini API using public URLs."""
    
    generation_config = {
        "temperature": 0.5,  # Lowered temperature for more focused responses
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 7500, # Increased tokens
        "response_mime_type": "text/plain",
    }
    
    chart_generation_config = {
        "temperature": 0.1,  # Lower temperature for consistent JSON
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 3000,
        "response_mime_type": "application/json",
    }


    print("1. Creating Gemini Generative Model with configuration.")
    
    system_instruction = """
    You are a sophisticated financial analysis tool. 
    Analyze the transaction data from the provided PDF file, categorizing them into Food, Clothes, Housing, etc. 
    If custom categories are provided, use them. 
    For each month, provide:
        - A summary of spending, closing balance, and saving rate.
        - Identification of spending trends and significant changes in categories.
        - Suggest potential investment options and saving strategies, tailored for that month.
        - Spending reduction suggestions for higher spending categories.
        - Provide a comparison with last month expenses, if applicable.
       - Provide feedback based on previous month patterns and saving habits.

    Do not include any conversational tone, just report the summary. 
    Do not include transaction narration/description, just basic information like date, amount, and category.
    Use hyphens ('-') to represent list items.
    Provide all analysis in a clear, structured and report-like format
    """


    if custom_categories:
        system_instruction += f" Use these custom categories: {', '.join(custom_categories)}."
    

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=generation_config,
        system_instruction=system_instruction,
    )

    chart_model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-exp",
        generation_config=chart_generation_config,
        system_instruction="You are a data formatting tool. Your goal is to format data as a valid json that can be used to create charts using python libraries."
    )

    print("2. Extracting text from PDF.")
    all_text_content = ""
    for file_url in file_urls:
        all_text_content += extract_text_from_pdf(file_url)

    max_length = 20000  # Set your preferred max length here (check Gemini documentation for limits)

    if len(all_text_content) > max_length:
        all_text_content = all_text_content[:max_length]
        print (f"Text content was too long, truncated to: {len(all_text_content)}")

    print(f"Text content length: {len(all_text_content)}")
    
    
    user_prompt = """
    Provide the transaction summary, categorized monthly closing balances, potential investment options,
    spending reduction suggestions for each month, and trend analysis over time.
    Present the results in a clear, concise, and report-like format. 
    Do not include conversational content.
    """

    chart_user_prompt = """
        Based on the provided transaction data, provide the json to generate graphs with following structure:
        {
            "monthly_spending": [
               {"month": "Jan 2023", "total_spending": 123.45},
               {"month": "Feb 2023", "total_spending": 456.78}
               ....
            ],
            "spending_categories": [
               { "month": "Jan 2023", "categories": { "Food":12.34, "Clothes":45.67, ...} },
                { "month": "Feb 2023", "categories": { "Food":56.78, "Clothes":78.90, ...} }
               ....
            ],
           "monthly_closing_balance": [
               { "month": "Jan 2023", "closing_balance": 1000.00 },
                { "month": "Feb 2023", "closing_balance": 2000.00 }
               ....
             ]
        }
       Do not include any conversational tone. Do not include any other info other than valid json output.
    """

    print("3. Starting chat session with file content.")
    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [
                     all_text_content,
                      user_prompt
                ],
            }
        ]
    )

    chart_chat_session = chart_model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [
                     all_text_content,
                      chart_user_prompt
                ],
            }
        ]
    )

    print("4. Sending message to chat session.")
    response = chat_session.send_message("Process the uploaded transactions.")
    response_text = response.text.replace("*", " ") # Replace stars with hyphens
    chart_response = chart_chat_session.send_message("Process the uploaded transaction data to build graphs.")
    
    print("5. Received response from chat session.")
    print(response_text)
    print("Chart Response:")
    print(chart_response.text)
    image_urls = generate_charts(chart_response.text)
    return response_text, chart_response.text, image_urls


@app.route('/')
def index():
    return render_template('index2.html')


@app.route('/upload', methods=['POST'])
def upload():
    """Handle file uploads and process transactions via Gemini API."""
    print(f"Request Headers: {request.headers}")
    print(f"Request Files: {request.files}")
    files = request.files.getlist('file')
    custom_categories = request.form.getlist('custom_categories') # Fetch custom categories or set to None if not provided
    print(f"Custom Categories: {custom_categories}")
    if not files:
        print("Error: No file was uploaded.")
        return jsonify({"error": "No file was uploaded.", "response": "No file was uploaded."}), 400

    file_urls = []
    for file in files:
      if file and file.filename.endswith('.pdf'):
        # Upload the file to Cloud Storage and get its public URL
        file_url = upload_to_cloud_storage(file)
        #print(f"File uploaded to Cloud Storage: {file_url}")
        file_urls.append(file_url)
      else:
        print(f"Error: Unsupported file or no file.")
        return jsonify({"error": "Unsupported file format! Only PDFs are allowed.", "response": "Unsupported file format! Only PDFs are allowed."}), 400


    try:
            # Fetch response from Gemini API
            response_text, chart_data, image_urls  = fetch_gemini_response(file_urls, custom_categories)

            # Attempt to parse the response and extract spending information
            try:
                # Parse the Gemini response to JSON
                response_json = json.loads(response_text.strip())

                # Attempt to extract spending_summary. If not there, use empty array.
                spending_summary = response_json.get('spending_summary', [])

            except json.JSONDecodeError:
                # In case Gemini doesn't give a json response, we just create an empty spending summary
                spending_summary = []
            
            return jsonify({"response": response_text, "spending_summary": spending_summary, "chart_data": chart_data, "image_urls": image_urls})


    except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e), "response": str(e)}), 400 # Send the response with error message.


if __name__ == '__main__':
    try:
        if __name__ == '__main__':
            app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=True)
    except Exception as e:
            import traceback
            traceback.print_exc()