#!/usr/bin/env python3
import playsound
import configparser
import asyncio
import time
import random
import spotipy
import webbrowser
from spotipy.oauth2 import SpotifyClientCredentials
from pywizlight import wizlight, PilotBuilder, discovery

green = 15
blue = 15
cycletime = 2
flash_variance = 25
scope = "ugc-image-upload user-read-playback-state user-modify-playback-state user-read-currently-playing app-remote-control streaming"
playlist = "spotify:playlist:2q6tU7SrOYgtSPw2x1cGt0"
sound_effect = "chill.wav"
config = configparser.ConfigParser()
config.read(".spotify.ini")
username = config["DEFAULT"]["username"]
spotify_id = config["DEFAULT"]["client_id"]
spotify_secret = config["DEFAULT"]["client_secret"]
redirectURI = config["DEFAULT"]["redirectURI"]
oauth_object = spotipy.SpotifyOAuth(
    client_id=spotify_id,
    client_secret=spotify_secret,
    redirect_uri=redirectURI,
    scope=scope,
)
token_dict = oauth_object.get_access_token()
token = token_dict["access_token"]
spotify = spotipy.Spotify(auth=token)

office_bulbs = ["192.168.1.165", "192.168.1.159", "192.168.1.160"]

diningroom_bulbs = [
    "192.168.1.156",
    "192.168.1.155",
    "192.168.1.154",
    "192.168.1.158",
    "192.168.1.167",
]

torch_scenes = [5, 28, 31]

office_bulb_objs = []
for b in office_bulbs:
    bulb = wizlight(b)
    office_bulb_objs.append(bulb)

diningroom_bulb_objs = []
for b in diningroom_bulbs:
    bulb = wizlight(b)
    diningroom_bulb_objs.append(bulb)


async def main():
    spotify.start_playback(context_uri=playlist)
    playsound.playsound(sound_effect, False)
    for light_bulb in office_bulb_objs:
        dim = 128 - int(random.random() * 60)
        speed = 10 + int(random.random() * 180)
        scene = random.choice(torch_scenes)
        await light_bulb.turn_on(PilotBuilder(scene=scene, speed=speed, brightness=dim))
    for light_bulb in diningroom_bulb_objs:
        dim = 64 + int(random.random() * 20)
        delta1 = int(random.random() * 30)
        delta2 = int(random.random() * 30)
        delta3 = int(random.random() * 30)
        await light_bulb.turn_on(
            PilotBuilder(rgb=(32 + delta1, 32 + delta2, 32 + delta3), brightness=dim)
        )
    while True:
        print("start")
        random.shuffle(office_bulb_objs)
        if int(random.random() * 100) > 98:
            for light_bulb in office_bulb_objs:
                dim = 128 - int(random.random() * 60)
                speed = 10 + int(random.random() * 180)
                scene = random.choice(torch_scenes)
                await light_bulb.turn_on(
                    PilotBuilder(scene=scene, speed=speed, brightness=dim)
                )
                time.sleep(cycletime / len(office_bulb_objs))
        random.shuffle(diningroom_bulb_objs)
        for light_bulb in diningroom_bulb_objs:
            dim = 32 + int(random.random() * 20)
            delta1 = int(random.random() * 30)
            delta2 = int(random.random() * 30)
            delta3 = int(random.random() * 30)
            await light_bulb.turn_on(
                PilotBuilder(
                    rgb=(32 + delta1, 32 + delta2, 32 + delta3), brightness=dim
                )
            )


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
