from flask import Flask, session, request, jsonify, send_from_directory
from openai import OpenAI, AssistantEventHandler
import os
from dotenv import load_dotenv
from flask_cors import CORS
from flask_session import Session

app = Flask(__name__)
CORS(app)
load_dotenv()

# Setup session configuration
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

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
    user_prompt = request.json['prompt']
    session['chat_history'] = session.get('chat_history', []) + [f"User: {user_prompt}"]
    try:
        # Manage thread creation or retrieve from session
        thread_id = session.get('thread_id')
        if not thread_id:
            # Create a new thread
            thread = client.beta.threads.create()
            thread_id = thread.id
            session['thread_id'] = thread_id

        # Add a message to the thread
        client.beta.threads.messages.create(
          thread_id=thread_id,
          role="user",
          content=user_prompt
        )

        # Create and stream a run       
        class EventHandler(AssistantEventHandler):
            def __init__(self):
                super().__init__()
                self.responses = []

            def on_text_delta(self, delta, snapshot):
                self.responses.append(delta.value)
        
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
          thread_id=thread_id,
          assistant_id=assistant.id,
          instructions="Answer the user query.",
          event_handler=event_handler,
        ) as stream:
            stream.until_done()

        reply = ''.join(event_handler.responses)
        session['chat_history'].append(f"AI: {reply}")
        return jsonify({'message': reply, 'chat_history': session['chat_history']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)