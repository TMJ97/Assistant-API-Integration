from flask import Flask, session, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv
from flask_cors import CORS
from flask_session import Session  # Import session management

app = Flask(__name__)
CORS(app)
load_dotenv()

# Setup session configuration
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

@app.route('/')
def home():
    return "Welcome to the OpenAI integration demo!"

@app.route('/generate', methods=['POST'])
def generate():
    user_prompt = request.json['prompt']
    session['chat_history'] = session.get('chat_history', []) + [f"User: {user_prompt}"]
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant."},
                {"role": "user", "content": user_prompt}
            ]
        )
        reply = response.choices[0].message.content
        session['chat_history'].append(f"AI: {reply}")
        return jsonify({'message': reply, 'chat_history': session['chat_history']})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
