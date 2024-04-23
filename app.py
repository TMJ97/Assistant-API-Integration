import openai
import os

from dotenv import load_dotenv
from flask import Flask, request, jsonify

# Load environment variables
load_dotenv()

# Set up the OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

app = Flask(__name__)

@app.route('/')
def home():
    return "Welcome to the OpenAI integration demo!"

@app.route('/generate', methods=['POST'])
def generate():
    prompt = request.json['prompt']
    response = openai.Completion.create(
        model="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=150
    )
    return jsonify(response['choices'][0]['text'])

if __name__ == '__main__':
    app.run(debug=True)
