from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, LocationMessage, TextSendMessage
import config
import json
import math

app = Flask(__name__)
line_bot_api = LineBotApi(config.CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(config.CHANNEL_SECRET)

@app.route("/webhook", methods=['POST'])
def webhook():
    # 確保 signature 是字串
    signature = request.headers.get('X-Line-Signature', '')
    signature = str(signature)
    
    if not signature:
        return 'Bad Request: No signature', 400

    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
        return 'OK', 200
    except InvalidSignatureError:
        abort(400)
    except Exception as e:
        print(f"處理 Webhook 時發生錯誤: {e}")
        return 'Internal Server Error', 500

def haversine(lat1, lon1, lat2, lon2):
    """計算地球表面兩點之間的球面距離 (Haversine Formula)。"""
    R = 6371  # 地球半徑，單位: 公里
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance
@handler.add(MessageEvent, message=LocationMessage)
def handle_location_message(event):
    try:
        # Load parking lot data
        with open('parking_data_with_coords_google_maps.json', 'r', encoding='utf-8') as f:
            parking_data = json.load(f)

        # Filter parking lots with valid latitude and longitude
        valid_parking_data = [
            p for p in parking_data
            if p.get('latitude') is not None and p.get('longitude') is not None
        ]

        if not valid_parking_data:
            raise ValueError("No valid parking data available.")

        # User's location
        location = event.message
        user_lat = location.latitude
        user_lon = location.longitude

        # Find nearest parking lot
        nearest_parking = min(
            valid_parking_data,
            key=lambda p: haversine(
                user_lat, user_lon,
                float(p['latitude']),
                float(p['longitude'])
            )
        )

        # Prepare response
        parking_lat = nearest_parking['latitude']
        parking_lon = nearest_parking['longitude']
        parking_name = nearest_parking.get('停車場名稱', 'Unknown')
        parking_address = nearest_parking.get('停車場地址-地號', 'No Address')
        google_maps_link = f"https://www.google.com/maps/dir/?api=1&destination={parking_lat},{parking_lon}"

        reply_message = f"Closest parking lot:\n" \
                        f"Name: {parking_name}\n" \
                        f"Address: {parking_address}\n" \
                        f"Navigation: {google_maps_link}"

        # Reply to the user
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_message)
        )
    except ValueError as ve:
        print(f"Validation error: {ve}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="No valid parking data available.")
        )
    except Exception as e:
        print(f"Error handling location message: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="An error occurred while processing your location.")
        )


@handler.add(MessageEvent)
def handle_message(event):
    if event.message.type != 'location':
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請傳送位置訊息")
        )

if __name__ == "__main__":
    app.run(port=config.PORT, debug=True)