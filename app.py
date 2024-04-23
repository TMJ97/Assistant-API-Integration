from flask import Flask, request, jsonify
from openai import OpenAI
import os
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "Welcome to the OpenAI integration demo!"

@app.route('/generate', methods=['POST'])
def generate():
    user_prompt = request.json['prompt']
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an assistant."},
                {"role": "user", "content": user_prompt}
            ]
        )
        # Access the response using attribute notation
        message_content = response.choices[0].message.content
        return jsonify({'message': message_content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
