import json
import os
import time
from contextlib import asynccontextmanager
from functools import lru_cache
from random import randint
from typing import Any, Optional

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import APIKeyHeader
from fastapi_mqtt import FastMQTT, MQTTConfig
from gmqtt import Client as MQTTClient
from pydantic import BaseModel

load_dotenv()

# from threading import Thread
mqtt_config = MQTTConfig(
    host="192.168.1.110",
    port=1883,
    keepalive=60,
    username="erik",
    password="Xz1b33!Pof",
)

fast_mqtt = FastMQTT(config=mqtt_config)


colour = None

devices = [

    {
        "name": "led_strip",
        "topic": "zigbee2mqtt/hue_barnrum/set",
        "type": "zigbee",
    },
    # {"name": "wled", "topic": "wled/5m/col", "colour": convert_to_hex(colour)},
]

colour_values = [
    # {"colour": "dark red", "value": "174,0,0"},
    # {"colour": "red", "value": "255,0,0"},
    # {"colour": "orange-red", "value": "255,102,0"},
    # {"colour": "yellow", "value": "255,239,0"},
    # {"colour": "chartreuse", "value": "153,255,0"},
    # {"colour": "lime", "value": "40,255,0"},
    # {"colour": "aqua", "value": "0,255,242"},
    # {"colour": "sky blue", "value": "0,122,255"},
    # {"colour": "blue", "value": "5,0,255"},
    # {"colour": "blue", "value": "71,0,237"},
    # {"colour": "indigo", "value": "99,0,178"},
    # {"colour": "violet", "value": "139,0,255"},
    # {"colour": "purple", "value": "255,0,255"},
    # {"colour": "pink", "value": "255,0,128"},
    # {"colour": "white", "value": "255,255,255"},
    {"colour": "dark red", "value": "174,0,0"},
    {"colour": "red", "value": "255,0,0"},
    {"colour": "orange-red", "value": "255,102,0"},
    {"colour": "chartreuse", "value": "153,255,0"},
    {"colour": "green", "value": "0,255,0"},
    {"colour": "blue", "value": "0,0,255"},
    {"colour": "yellow", "value": "255,255,0"},
    {"colour": "cyan", "value": "0,255,255"},
    {"colour": "magenta", "value": "255,0,255"},
    {"colour": "gray", "value": "128,128,128"},
    {"colour": "maroon", "value": "128,0,0"},
    {"colour": "olive", "value": "128,128,0"},
    {"colour": "purple", "value": "128,0,128"},
    {"colour": "teal", "value": "0,128,128"},
    {"colour": "navy", "value": "0,0,128"},
    {"colour": "silver", "value": "192,192,192"},
    {"colour": "lime", "value": "0,255,0"},
    {"colour": "aqua", "value": "0,255,255"},
    {"colour": "fuchsia", "value": "255,0,255"},
    {"colour": "orange", "value": "255,165,0"},
    {"colour": "brown", "value": "165,42,42"},
    {"colour": "pink", "value": "255,192,203"},
    {"colour": "gold", "value": "255,215,0"},
    {"colour": "light gray", "value": "211,211,211"},
    {"colour": "dark gray", "value": "169,169,169"},
    {"colour": "indigo", "value": "75,0,130"},
    {"colour": "violet", "value": "238,130,238"},
    {"colour": "salmon", "value": "250,128,114"},
    {"colour": "crimson", "value": "220,20,60"},
    {"colour": "khaki", "value": "240,230,140"},
    {"colour": "turquoise", "value": "64,224,208"},
    {"colour": "coral", "value": "255,127,80"},
    {"colour": "lavender", "value": "230,230,250"},
    {"colour": "plum", "value": "221,160,221"},
    {"colour": "orchid", "value": "218,112,214"},
    {"colour": "sienna", "value": "160,82,45"},
    {"colour": "peach puff", "value": "255,218,185"},
    {"colour": "mint cream", "value": "245,255,250"},
    {"colour": "sky blue", "value": "135,206,235"},
    {"colour": "steel blue", "value": "70,130,180"},
    {"colour": "forest green", "value": "34,139,34"},
    {"colour": "lime green", "value": "50,205,50"},
    {"colour": "midnight blue", "value": "25,25,112"},
    {"colour": "chocolate", "value": "210,105,30"},
    {"colour": "tomato", "value": "255,99,71"},
    {"colour": "dodger blue", "value": "30,144,255"},
    {"colour": "slate gray", "value": "112,128,144"},
    {"colour": "rosy brown", "value": "188,143,143"},
    {"colour": "sea green", "value": "46,139,87"},
    {"colour": "pale violet red", "value": "219,112,147"}   
]



# Configuration model
class SpotifyConfig:
    def __init__(self):
        # Load from environment variables
        self.client_id = os.environ.get("SPOTIFY_CLIENT_ID")
        self.client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set as environment variables")

# Token model
class SpotifyToken(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    scope: Optional[str] = ""
    expires_at: float = 0  # Timestamp when token expires

class SpotifyAuthRequest(BaseModel):
    code: str
    redirect_uri: str

class SpotifyUserToken(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    scope: str
    expires_at: float = 0

# Spotify client with token management
class SpotifyClient:
    def __init__(self, config: SpotifyConfig):
        self.config = config
        self._token: Optional[SpotifyToken] = None
        self._http_client = httpx.Client(timeout=10.0)
    
    async def get_token(self) -> SpotifyToken:
        """Get a valid Spotify token, refreshing if necessary"""
        # If we don't have a token or it's expired (with 60s buffer), get a new one
        current_time = time.time()
        if not self._token or self._token.expires_at <= current_time + 60:
            await self._refresh_token()
        print(self._token)
        return self._token
    
    async def _refresh_token(self):
        """Get a new token from Spotify API"""
        url = "https://accounts.spotify.com/api/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret
        }
        
        try:
            response = await httpx.AsyncClient().post(url, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            # Calculate absolute expiration time and store it
            current_time = time.time()
            token_data["expires_at"] = current_time + token_data["expires_in"]
            
            self._token = SpotifyToken(**token_data)
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Failed to obtain Spotify token: {str(e)}")
    
    async def make_authenticated_request(self, method, url, **kwargs):
        """Make a request to Spotify API with a valid token"""
        token = await self.get_token()
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {token.access_token}"
        kwargs["headers"] = headers
        
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **kwargs)
            print(response)
            response.raise_for_status()
            return response.json()
        
    async def get_user_token(self, code: str, redirect_uri: str) -> SpotifyUserToken:
        """Exchange authorization code for user token"""
        url = "https://accounts.spotify.com/api/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret
        }
        
        try:
            response = await httpx.AsyncClient().post(url, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            # Calculate absolute expiration time and store it
            current_time = time.time()
            token_data["expires_at"] = current_time + token_data["expires_in"]
            
            return SpotifyUserToken(**token_data)
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f"Failed to obtain user token: {str(e)}")

# Dependency injection
@lru_cache()
def get_spotify_config():
    return SpotifyConfig()

def get_spotify_client(config: SpotifyConfig = Depends(get_spotify_config)):
    return SpotifyClient(config)


def get_device_payload(colour) -> str:
    return json.dumps(
        {
            "state": "ON",
            "brightness": 255,
            "transition": 0.001,
            "color_mode": "rgb",
            "color": {"rgb": colour},
        }
    )


def change_colour() -> dict[str, str]:
    number = randint(0, len(colour_values) - 1)
    return colour_values[number]


def get_spotify_token() -> dict[str, Any]:
    url = 'https://accounts.spotify.com/api/token'
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": "f79b9c61ce2040edb05c4dbccf06d345",
        "client_secret": "75063d31681343a98ceb8dd270bcef1f"
    }
    
    response = httpx.post(url, headers=headers, data=data)
    response.raise_for_status()  # Raise exception for 4XX/5XX responses
    
    return response.json()


def get_spotify_audio_breakdown() -> dict[str, Any]:
    url = "https://api.spotify.com/v1/audio-analysis/2ZfaBbRMcEgSF8JnJIaEBP"

    payload = {}
    headers = {
    'Authorization': 'Bearer BQBn1bM8oHtQOHzrIiNvJ_DDgIsYaDP9xs61lmjkPP_LGaG_j5bheH-P8oDfQkx3Z6bjpP_AwiVFochE0VMBl_BHhdtOVJZUDV8VjfSHxFELgOn4CyU'
    }

    response = httpx.get(url, headers=headers, params=payload)
    print(response)
    return response.json()


# @asynccontextmanager
# async def _lifespan(_app: FastAPI):
#     await fast_mqtt.mqtt_startup()
#     yield
#     await fast_mqtt.mqtt_shutdown()


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    # Initialize the Spotify client and get the first token
    config = get_spotify_config()
    client = SpotifyClient(config)
    await client.get_token()
    print("Spotify client initialized with a fresh token")
    yield


app = FastAPI(lifespan=_lifespan)
#app = FastAPI()



@fast_mqtt.on_connect()
def connect(client: MQTTClient, flags: int, rc: int, properties: Any):
    client.subscribe("/mqtt")  # subscribing mqtt topic
    print("Connected: ", client, flags, rc, properties)

@fast_mqtt.subscribe("/zigbee2mqtt/hue_barnrum/", qos=1)
async def home_message(client: MQTTClient, topic: str, payload: bytes, qos: int, properties: Any):
    print("temperature/humidity: ", topic, payload.decode(), qos, properties)

@fast_mqtt.on_message()
async def message(client: MQTTClient, topic: str, payload: bytes, qos: int, properties: Any):
    print("Received message: ", topic, payload.decode(), qos, properties)

@fast_mqtt.subscribe("my/mqtt/topic/#", qos=2)
async def message_to_topic_with_high_qos(
    client: MQTTClient, topic: str, payload: bytes, qos: int, properties: Any
):
    print(
        "Received message to specific topic and QoS=2: ", topic, payload.decode(), qos, properties
    )

@fast_mqtt.on_disconnect()
def disconnect(client: MQTTClient, packet, exc=None):
    print("Disconnected")

@fast_mqtt.on_subscribe()
def subscribe(client: MQTTClient, mid: int, qos: int, properties: Any):
    print("subscribed", client, mid, qos, properties)



@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/current")
async def get_current(spotify_client: SpotifyClient = Depends(get_spotify_client)):
    url = "https://api.spotify.com/v1/me/player/currently-playing"
    payload = {}
    try:
        result = await spotify_client.make_authenticated_request(
            "GET",
            url,
            params=payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test")
async def func():
    colour_dict = change_colour()
    colour = colour_dict["value"]

    fast_mqtt.publish("zigbee2mqtt/hue_barnrum/set", get_device_payload(colour))  # publishing mqtt topic
    
    return {"result": True, "message": "Published"}




@app.get("/test2")
def d():
    huh = get_spotify_audio_breakdown()
    for i, beat in enumerate(huh["beats"]):
        print(beat)
        colour_dict = change_colour()
        colour = colour_dict["value"]
        # print(beat["start"])
        # await asyncio.sleep(beat["start"])
        time.sleep(beat["start"])
        print(f"beat {i}")
        print("colour", colour)
        fast_mqtt.publish("zigbee2mqtt/hue_barnrum/set", get_device_payload(colour))  # publishing mqtt topic
    
    return {"result": True, "message": "Published"}


@app.get("/test3")
def d3():
    huh = get_spotify_audio_breakdown()
    sections = huh["sections"]

    for i, section in enumerate(sections):
        if i == 0:
            time.sleep(section["duration"])
        else:
            bpm = float(section["tempo"])
            duration = round(section["duration"])
            for i in range(0, round(duration*1000), round(60/bpm)*1000):
                colour_dict = change_colour()
                colour = colour_dict["value"]
                print(f"section {i}")
                print("colour", colour)
                fast_mqtt.publish("zigbee2mqtt/hue_barnrum/set", get_device_payload(colour))

    # for i in range(0, round(duration*1000), round(60/bpm)*1000):
    #     colour_dict = change_colour()
    #     colour = colour_dict["value"]
    #     print("colour", colour)
    #     print(f"beat {i}")
    #     time.sleep(60/bpm)
        #fast_mqtt.publish("zigbee2mqtt/hue_barnrum/set", get_device_payload(colour))

@app.get("/test4")
def d3():
    huh = get_spotify_audio_breakdown()
    bpm = float(huh["track"]["tempo"])
    duration = round(huh["track"]["duration"])

    for i in range(0, round(duration*1000), round(60/bpm)*1000):
        colour_dict = change_colour()
        colour = colour_dict["value"]
        print("colour", colour)
        print(f"beat {i}")
        time.sleep(60/bpm)
        #fast_mqtt.publish("zigbee2mqtt/hue_barnrum/set", get_device_payload(colour))

    # for i, beat in enumerate(huh["beats"]):
    #     print(beat)
    #     colour_dict = change_colour()
    #     colour = colour_dict["value"]
    #     # print(beat["start"])
    #     # await asyncio.sleep(beat["start"])
    #     time.sleep(beat["start"])
    #     print(f"beat {i}")
    #     print("colour", colour)
    #     fast_mqtt.publish("zigbee2mqtt/hue_barnrum/set", get_device_payload(colour))  # publishing mqtt topic
    
    return {"result": True, "message": "Published"}


# brightness

# @app.get("/disco")
# async def root2():
#     colour_dict = change_colour()
#     color = colour_dict["value"]
#     device = devices[0]
#     client.publish(
#                 device["topic"], get_device_config(device["type"], color)
#                     )
    
# app.run(host='0.0.0.0',debug=True)

# mic_input.close()
# p.terminate()# p.terminate()# p.terminate()# p.terminate()