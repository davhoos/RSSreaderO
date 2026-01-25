import json
import xml.etree.ElementTree as ET
from datetime import datetime

INPUT_JSON = "RSS_channels.json"
OUTPUT_OPML = "youtube.opml"

YOUTUBE_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id="

with open(INPUT_JSON, "r", encoding="utf-8") as f:
    channels = json.load(f)

# OPML root
opml = ET.Element("opml", version="1.0")

head = ET.SubElement(opml, "head")
ET.SubElement(head, "title").text = "YouTube Subscriptions"
ET.SubElement(head, "dateCreated").text = datetime.utcnow().isoformat()

body = ET.SubElement(opml, "body")

# jedna složka pro YouTube
folder = ET.SubElement(
    body,
    "outline",
    text="YouTube",
    title="YouTube"
)

for name, channel_id in channels.items():
    ET.SubElement(
        folder,
        "outline",
        type="rss",
        text=name,
        title=name,
        xmlUrl=YOUTUBE_RSS + channel_id
    )

# uložit OPML
tree = ET.ElementTree(opml)
tree.write(OUTPUT_OPML, encoding="utf-8", xml_declaration=True)

print(f"✅ Hotovo! OPML uložen jako {OUTPUT_OPML}")
