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
cycletime = 12
flash_variance = 25
scope = "ugc-image-upload user-read-playback-state user-modify-playback-state user-read-currently-playing app-remote-control streaming"
playlist = "spotify:playlist:5Q8DWZnPe7o7GA96SARmOK"
sound_effect = "dooropen.wav"
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
# ['Ocean', 'Romance', 'Sunset', 'Party', 'Fireplace', 'Cozy', 'Forest', 'Pastel Colors', 'Wake up', 'Bedtime', 'Warm White', 'Daylight', 'Cool white', 'Night light', 'Focus', 'Relax', 'True colors', 'TV time', 'Plantgrowth', 'Spring', 'Summer', 'Fall', 'Deepdive', 'Jungle', 'Mojito', 'Club', 'Christmas', 'Halloween', 'Candlelight', 'Golden white', 'Pulse', 'Steampunk', 'Rhythm']

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
    playsound.playsound(sound_effect, True)
    spotify.start_playback(context_uri=playlist)
    for light_bulb in office_bulb_objs:
        dim = 255 - int(random.random() * 181)
        delta1 = int(random.random() * 20)
        delta2 = int(random.random() * 20)
        await light_bulb.turn_on(
            PilotBuilder(rgb=(128 + delta1, 128 + delta2, 128 + delta1), brightness=dim)
        )
    for light_bulb in diningroom_bulb_objs:
        dim = 255 - int(random.random() * 60)
        speed = 10 + int(random.random() * 180)
        scene = random.choice(torch_scenes)
        await light_bulb.turn_on(PilotBuilder(scene=scene, speed=speed, brightness=dim))
    while True:
        print("start")
        random.shuffle(office_bulb_objs)
        for light_bulb in office_bulb_objs:
            if int(random.random() * 100) > 95:
                print("flash")
                flash_bright = 255 - int(random.random() * flash_variance)
                await light_bulb.turn_on(
                    PilotBuilder(rgb=(255, 255, 255), brightness=flash_bright)
                )
                time.sleep(1)
            dim = 255 - int(random.random() * 181)
            delta1 = int(random.random() * 30)
            delta2 = int(random.random() * 30)
            await light_bulb.turn_on(
                PilotBuilder(
                    rgb=(158 + delta1, 158 + delta2, 158 + delta1), brightness=dim
                )
            )
            time.sleep(cycletime / len(office_bulb_objs))
        random.shuffle(diningroom_bulb_objs)
        for light_bulb in diningroom_bulb_objs:
            dim = 255 - int(random.random() * 60)
            speed = 10 + int(random.random() * 180)
            scene = random.choice(torch_scenes)
            await light_bulb.turn_on(
                PilotBuilder(scene=scene, speed=speed, brightness=dim)
            )
            time.sleep(cycletime / len(diningroom_bulb_objs))


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
