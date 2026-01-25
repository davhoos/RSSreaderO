import json

import feedparser

# Seznam UC ID kanálů
channel_ids = [
    "UCUkRj4qoT1bsWpE_C8lZYoQ",
    "UCajiMK_CY9icRhLepS8_3ug",
    "UCCQ6SXMc7MoJ88jjpn6j-8Q",
    "UCKCTmact-90hXpV2ns8GSsA",
    "UCZNhwA1B5YqiY1nLzmM0ZRg",
    "UCG4pyCrLYfDsSaRUrBH1MKA",
    "UCKQdc0-Targ4nDIAUrlfKiA",
    "UCNl9pCCDFUWqWmvk4sI5WLA",
    "UCQk_kRUoxJQY5vqbJQFgJDA",
    "UC9x0AN7BWHpCDHSm9NiJFJQ",
    "UC8ftoUtWYnN9Cw3w7UTgEug",
    "UCC_NjLEb2Sley94py4vSYTA",
    "UCJQJAI7IjbLcpsjWdSzYz0Q",
    "UC6MXTfIi_pSMxwPQDKT2VGg",
    "UCk_7zwoUPjV4VbofWhHbJZg",
    "UC2UXDak6o7rBm23k3Vv5dww",
    "UCwSM8c1XRH3wLcDmzbV5wAw",
    "UC9H0HzpKf5JlazkADWnW1Jw",
    "UCuKVsDS3oVzTuNjnQ79pEEg",
    "UCR0l-DhuoKVZKJXXccr-2FA",
    "UC8wZnXYK_CGKlBcZp-GxYPA",
    "UCsVELe77-bXS3vCLWbDoibw",
    "UCSPIuWADJIMIf9Erf--XAsA",
]

# Slovník pro výstup
channels_dict = {}

for cid in channel_ids:
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"
    feed = feedparser.parse(feed_url)

    channel_title = feed.feed.title if "title" in feed.feed else "Neznámý kanál"
    channels_dict[channel_title] = cid

# Vytiskne ve formátu JSON / Python slovník
print(json.dumps(channels_dict, indent=4, ensure_ascii=False))

# Volitelně ulož do souboru
with open("youtube_channels.json", "w", encoding="utf-8") as f:
    json.dump(channels_dict, f, indent=4, ensure_ascii=False)
