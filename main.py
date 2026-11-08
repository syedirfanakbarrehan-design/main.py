import os
from flask import Flask, jsonify, request
import google.generativeai as genai
import requests

app = Flask(__name__)

# Load credentials from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "my_secret_verify_token")

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


# 1. Meta Webhook Verification (Required by Meta)
@app.route("/webhook", methods=["GET"])
def verify_webhook():
  mode = request.args.get("hub.mode")
  token = request.args.get("hub.verify_token")
  challenge = request.args.get("hub.challenge")

  if mode == "subscribe" and token == VERIFY_TOKEN:
    return challenge, 200
  return "Verification failed", 403


# 2. Receive incoming message & respond via Gemini
@app.route("/webhook", methods=["POST"])
def receive_message():
  data = request.get_json()

  try:
    # Check if request contains a valid incoming text message
    entry = data["entry"][0]["changes"][0]["value"]
    if "messages" in entry:
      incoming_msg = entry["messages"][0]["text"]["body"]
      sender_number = entry["messages"][0]["from"]

      # Pass incoming text to Google Gemini AI
      response = model.generate_content(
          "You are a helpful 24/7 business AI assistant. Keep responses brief"
          f" and professional. User message: {incoming_msg}"
      )
      reply_text = response.text

      # Send Gemini's answer back to customer's WhatsApp
      send_whatsapp(sender_number, reply_text)

  except Exception as e:
    print("Error processing webhook:", e)

  return jsonify({"status": "received"}), 200


def send_whatsapp(to_number, text):
  url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
  headers = {
      "Authorization": f"Bearer {WHATSAPP_TOKEN}",
      "Content-Type": "application/json",
  }
  payload = {
      "messaging_product": "whatsapp",
      "to": to_number,
      "type": "text",
      "text": {"body": text},
  }
  requests.post(url, json=payload, headers=headers)


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5000)