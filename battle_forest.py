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

green = 255
red = 15
blue = 15
color_variance = 10
cycletime = 3
flash_variance = 25
scope = "ugc-image-upload user-read-playback-state user-modify-playback-state user-read-currently-playing app-remote-control streaming"
playlist = "spotify:playlist:6FohP6m1ipvNjgllOH4HLt"
sound_effect = "danger.opus"
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
spotify.start_playback(context_uri=playlist)

# wiz bulb configuration
config = configparser.ConfigParser()
config.read(".wizbulb.ini")
backdrop_bulbs = config["DEFAULT"]["backdrop_bulbs"].split(" ")
overhead_bulbs = config["DEFAULT"]["overhead_bulbs"].split(" ")
battlefield_bulbs = config["DEFAULT"]["battlefield_bulbs"].split(" ")

world_bulbs = backdrop_bulbs + overhead_bulbs + battlefield_bulbs
light_bulbs = []
for b in world_bulbs:
    bulb = wizlight(b)
    light_bulbs.append(bulb)


async def main():
    try:
        playsound3.playsound(sound_effect)
    except:
        print(f"likely need to make {sound_effect}")
    for light_bulb in light_bulbs:
        dim = 255 - int(random.random() * 181)
        b = blue + int(random.random() * color_variance)
        r = red + int(random.random() * color_variance)
        await light_bulb.turn_on(PilotBuilder(rgb=(r, green, b), brightness=dim))
    while True:
        print("start")
        random.shuffle(light_bulbs)
        # Pulse the light bulbs red
        for light_bulb in light_bulbs:
            if int(random.random() * 100) > 75:
                print("flash")
                flash_bright = 255 - int(random.random() * flash_variance)
                await light_bulb.turn_on(
                    PilotBuilder(rgb=(255, 64, 64), brightness=flash_bright)
                )
                time.sleep(1)
            dim = 255 - int(random.random() * 181)
            b = blue + int(random.random() * color_variance)
            r = red + int(random.random() * color_variance)
            await light_bulb.turn_on(PilotBuilder(rgb=(r, green, b), brightness=dim))
            time.sleep(cycletime / len(light_bulbs))


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
