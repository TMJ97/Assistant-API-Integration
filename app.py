from flask import Flask, session, request, jsonify, send_from_directory
from openai import OpenAI, AssistantEventHandler
import pandas as pd
import json
import os
import logging

from dotenv import load_dotenv
from flask_cors import CORS
from flask_session import Session

###PROJECT DESC. WIP. SAVED. And Archived to use LangGraph in a duplicate project!
# Alright, this project here is dedicated to making a simple integration with an OpenAI Assistant. It has a simple, ugly, but functional website (Flask & Python). It integrates with a specific, custom OpenAI Assistant. It supports sending messages to the Assistant and receiving responses. It displays chat history.
# Currently it doens't work as I made some changes to try and display different outputs (images). It was working with simple messages an chat history, and somewhat with file upload (it seems it couldnt handle big files but that might just be normal context problems). When I made changes to support e.g. displaying an image output, a pie chart, it broke (i modified the end parts of the generate function with "collect and handle responses" and the message list things...)
# It does not, yet, support all types of inputs and outputs.
# It does not yet implement multiple assistants or any kind of workflow.
# Or anything else...


app = Flask(__name__)
CORS(app)
load_dotenv()

# Setup session configuration
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure logging
logging.basicConfig(level=logging.INFO)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
assistant_id = os.getenv('ASSISTANT_ID')
assistant = client.beta.assistants.retrieve(assistant_id)

# # Create an Assistant
# assistant = client.beta.assistants.create(
#   name="Chat Assistant",
#   instructions="You are a helpful assistant. Answer questions and provide information.",
#   model="gpt-3.5-turbo",


@app.route('/')
def home():
    return send_from_directory('static', 'index.html')       

@app.route('/generate', methods=['POST'])
def generate():
    thread_id = session.get('thread_id')
    try:
        if 'file' in request.files:
            file = request.files['file']
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith('.xls') or file.filename.endswith('.xlsx'):
                df = pd.read_excel(file)
            
            # Convert all Timestamps in DataFrame to strings
            df = df.applymap(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if isinstance(x, pd.Timestamp) else x)
            
            # Extract user's text input if provided
            user_text = request.form.get('text', '')
            
            # Construct data JSON including file data, user's text input, and instructions
            data = {
                "data": df.to_dict(orient='records'),
                "text": user_text,  # Include user's text input alongside file data
                "instructions": request.form.get('instructions', 'Analyze the data. Refer to user\'s text input as well.')
            }
            user_prompt_json = json.dumps(data)
        else:
            user_prompt_json = json.dumps({"text": request.form['text']})  # Define user_prompt_json


        # Log the received user prompt
        logging.info(f"Received user prompt: {user_prompt_json}")

        # Update session chat history
        session['chat_history'] = session.get('chat_history', []) + [f"User: {user_prompt_json}"]

        if not thread_id:
            thread = client.beta.threads.create()
            thread_id = thread.id
            session['thread_id'] = thread_id
            logging.info(f"New thread created with ID: {thread_id}")

        logging.info(f"Sending message to thread {thread_id} with Assistant ID: {assistant.id}")
        response = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_prompt_json
        )

        # Collect and handle responses
        event_handler = EventHandler()
        logging.info(f"Starting run with Thread ID: {thread_id}")
        with client.beta.threads.runs.stream(
                thread_id=thread_id,
                assistant_id=assistant.id,
                event_handler=event_handler,
            ) as stream:
            stream.until_done()

        # Handle the collected responses
        messages = event_handler.responses
        images = []
        text_responses = []
        for message in messages:
            if 'image_file' in message:
                image_data = client.files.content(message['image_file']['file_id'])
                images.append(image_data.read())
            elif 'text' in message:
                text_responses.append(message['text']['value'])

        # Returning the collected responses
        return jsonify({'texts': text_responses, 'images': images})

    except Exception as e:
        logging.error(f"Error in generate route: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/check-assistant')
def check_assistant():
    assistant_id = os.getenv('ASSISTANT_ID')  # Make sure this is the same ID used elsewhere in your app
    try:
        assistant = client.beta.assistants.retrieve(assistant_id)
        assistant_details = {
            'id': assistant.id,
            'name': assistant.name,
            'instructions': assistant.instructions,
            'model': assistant.model,
            'tools': serialize_assistant_tool(assistant.tools) if hasattr(assistant, 'tools') else 'No tools configured'
        }
        return jsonify(assistant_details)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# Enhanced error handling in Flask
@app.errorhandler(Exception)
def handle_exception(e):
    response_text = {'error': 'An unexpected error occurred', 'details': str(e)}
    return jsonify(response_text), 500

    
def serialize_assistant_tool(tool):
    if isinstance(tool, dict):
        return {k: serialize_assistant_tool(v) for k, v in tool.items()}
    elif isinstance(tool, list):
        return [serialize_assistant_tool(v) for v in tool]
    elif hasattr(tool, '__dict__'):
        return {k: serialize_assistant_tool(v) for k, v in tool.__dict__.items()}
    else:
        return str(tool)
    
# Create and stream a run       
class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.responses = []

    def on_text_delta(self, delta, snapshot):
        self.responses.append(delta.value)

if __name__ == '__main__':
    app.run(debug=True)
