#!/usr/bin/env python3
import playsound3
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
cycletime = 6
flash_variance = 25
backdrop_scene = 23
scope = "ugc-image-upload user-read-playback-state user-modify-playback-state user-read-currently-playing app-remote-control streaming"
playlist = "spotify:playlist:37i9dQZF1DWV90ZWj21ygB"
sound_effect = "chill.wav"

# spotify configuration
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
moon = False

# wiz bulb configuration
config = configparser.ConfigParser()
config.read(".wizbulb.ini")
backdrop_bulbs = config["DEFAULT"]["backdrop_bulbs"].split(" ")
overhead_bulbs = config["DEFAULT"]["overhead_bulbs"].split(" ")
battlefield_bulbs = config["DEFAULT"]["battlefield_bulbs"].split(" ")


backdrop_bulb_objs = []
for b in backdrop_bulbs:
    bulb = wizlight(b)
    backdrop_bulb_objs.append(bulb)

battlefield_bulb_objs = []
for b in battlefield_bulbs:
    bulb = wizlight(b)
    battlefield_bulb_objs.append(bulb)

world_bulbs = backdrop_bulb_objs + overhead_bulb_objs + battlefield_bulbs


async def main():
    moon = False
    spotify.start_playback(context_uri=playlist)
    try:
        playsound3.playsound(sound_effect)
    except:
        print(f"likely need to make {sound_effect}")
    for light_bulb in backdrop_bulb_objs:
        dim = int(random.random() * 10)
        delta1 = int(random.random() * 10)
        delta2 = int(random.random() * 10)
        delta3 = int(random.random() * 10)
        await light_bulb.turn_on(
            PilotBuilder(rgb=(delta1, delta2, delta3), brightness=dim)
        )
    for light_bulb in overhead_bulb_objs:
        if moon == False:
            moon = True
            await light_bulb.turn_on(PilotBuilder(rgb=(255, 255, 128), brightness=100))
        else:
            dim = int(random.random() * 10)
            delta1 = int(random.random() * 10)
            delta2 = int(random.random() * 10)
            delta3 = int(random.random() * 10)
            await light_bulb.turn_on(
                PilotBuilder(rgb=(delta1, delta2, 16 + delta3), brightness=dim)
            )
    while True:
        print("start")
        random.shuffle(world_bulbs)
        for light_bulb in world_bulbs:
            if light_bulb in backdrop_bulb_objs:
                dim = int(random.random() * 10)
                delta1 = int(random.random() * 11)
                delta2 = int(random.random() * 10)
                delta3 = int(random.random() * 10)
                await light_bulb.turn_on(
                    PilotBuilder(rgb=(delta1, delta2, delta3), brightness=dim)
                )
            else:
                dim = int(random.random() * 20)
                delta1 = int(random.random() * 30)
                delta2 = int(random.random() * 30)
                delta3 = int(random.random() * 30)
                await light_bulb.turn_on(
                    PilotBuilder(rgb=(delta1, delta2, 16 + delta3), brightness=dim)
                )
            time.sleep(cycletime / len(world_bulbs))
        await light_bulb.turn_on(PilotBuilder(rgb=(255, 255, 128), brightness=100))


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
