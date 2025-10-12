#!/usr/bin/env python3
import sys
import re
import json
import os
import requests
import feedparser
import webbrowser
import urllib3
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QListWidget, QLabel, QInputDialog, QMessageBox, QSizePolicy, QScrollArea
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt

CHANNELS_FILE = "RSS_channels.json"

# Potlačení warningu při ověřování SSL, pokud verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class YoutubeRssReader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube RSS channels reader")
        self.setGeometry(100, 100, 1200, 800)
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)
        # Levý panel (kanály)
        left_panel = QVBoxLayout()
        main_layout.addLayout(left_panel, 2)
        self.channel_list = QListWidget()
        self.channel_list.setFixedHeight(650)
        left_panel.addWidget(QLabel("Kanály:"))
        left_panel.addWidget(self.channel_list)
        self.add_channel_btn = QPushButton("Přidat kanál")
        left_panel.addWidget(self.add_channel_btn)
        self.remove_channel_btn = QPushButton("Odebrat vybraný kanál")
        left_panel.addWidget(self.remove_channel_btn)
        # Pravý panel (videa a detaily)
        right_panel = QVBoxLayout()
        main_layout.addLayout(right_panel, 5)
        right_panel.addWidget(QLabel("Videa:"))
        self.video_list = QListWidget()
        self.video_list.setFixedHeight(200)
        right_panel.addWidget(self.video_list)
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setFixedHeight(410)
        self.thumbnail_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.thumbnail_label.mousePressEvent = self.on_thumbnail_click
        right_panel.addWidget(self.thumbnail_label)
        self.description_label = QLabel("Vyberte video pro zobrazení podrobností.")
        self.description_label.setWordWrap(True)
        self.description_scroll_area = QScrollArea()
        self.description_scroll_area.setWidget(self.description_label)
        self.description_scroll_area.setWidgetResizable(True)
        right_panel.addWidget(self.description_scroll_area, 1)
        self.channels = {}
        self.current_channel = None
        # Signály
        self.add_channel_btn.clicked.connect(self.add_channel)
        self.remove_channel_btn.clicked.connect(self.remove_channel)
        self.channel_list.currentRowChanged.connect(self.channel_changed)
        self.video_list.currentRowChanged.connect(self.video_selected)
        self.video_list.itemDoubleClicked.connect(self.open_video)
        # Načti uložené kanály
        self.load_channels()
        self.set_font()

    def set_font(self):
        font = QFont("Arial", 12)
        font.setWeight(QFont.Bold)
        self.setFont(font)
        self.channel_list.setFont(font)
        self.video_list.setFont(font)
        self.description_label.setFont(font)

    def add_channel(self):
        channel_id, ok = QInputDialog.getText(self, "Zadej channel ID-UC kanal!", "UC kanál ID example (UCxxxxxxxx):")
        if not ok or not channel_id.startswith("UC") or not re.match(r"^UC[\w-]+$", channel_id):
            QMessageBox.warning(self, "Chyba", "Neplatné channel ID, kanál nebude přidán. Ujistěte se, že ID začíná na 'UC' a má správný formát.")
            return
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            QMessageBox.warning(self, "Chyba", "Nepodařilo se načíst videa z tohoto kanálu.")
            return
        channel_title = feed.feed.get("title", channel_id)
        self.channels[channel_title] = {"id": channel_id, "entries": feed.entries}
        existing_channels = [self.channel_list.item(i).text() for i in range(self.channel_list.count())]
        if channel_title not in existing_channels:
            self.channel_list.addItem(channel_title)
        idx = self.channel_list.findItems(channel_title, Qt.MatchExactly)[0]
        self.channel_list.setCurrentItem(idx)
        self.save_channels()

    def remove_channel(self):
        current_row = self.channel_list.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Odebrat kanál", "Nejprve vyber kanál k odebrání.")
            return
        channel_name = self.channel_list.item(current_row).text()
        confirm = QMessageBox.question(
            self, "Potvrzení odebrání",
            f"Opravdu chceš odebrat kanál:\n{channel_name}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            if channel_name in self.channels:
                del self.channels[channel_name]
            self.channel_list.takeItem(current_row)
            self.video_list.clear()
            self.thumbnail_label.clear()
            self.description_label.setText("Vyberte video pro zobrazení podrobností.")
            self.current_channel = None
            self.save_channels()

    def channel_changed(self, index):
        if index < 0:
            return
        channel_name = self.channel_list.item(index).text()
        self.current_channel = channel_name
        self.load_videos_for_channel(channel_name)

    def load_videos_for_channel(self, channel_name):
        self.video_list.clear()
        self.thumbnail_label.clear()
        self.description_label.setText("Vyberte video pro zobrazení podrobností.")
        entries = self.channels[channel_name]["entries"]
        for entry in entries:
            self.video_list.addItem(entry.title)

    def video_selected(self, index):
        if index < 0 or self.current_channel is None:
            self.thumbnail_label.clear()
            self.description_label.setText("Vyberte video pro zobrazení podrobností.")
            return
        entries = self.channels[self.current_channel]["entries"]
        if index >= len(entries):
            return
        video = entries[index]
        title = video.get("title", "Bez názvu")
        published = video.get("published", "")
        summary = video.get("summary", "")
        self.description_label.setText(f"<b>{title}</b>\n{published}\n\n{summary}")

        thumbnail_url = None
        if "media_thumbnail" in video and video.media_thumbnail:
            thumbnail_url = video.media_thumbnail[0]["url"].replace('&amp;', '&')
        elif "media_content" in video and video.media_content:
            thumbnail_url = video.media_content[0]["url"].replace('&amp;', '&')
        else:
            # Fallback na oficiální YouTube thumbnail podle video_id
            video_id_match = re.search(r'v=([\w-]+)', video.link)
            if not video_id_match:
                video_id_match = re.search(r'(?:/videos/|/embed/|/shorts/)([a-zA-Z0-9_-]+)', video.link)
            if video_id_match:
                video_id = video_id_match.group(1)
                thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

        if thumbnail_url:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36"
                }
                response = requests.get(thumbnail_url, timeout=10, headers=headers, verify=False)
                if response.status_code == 200:
                    image = QPixmap()
                    ok = image.loadFromData(response.content)
                    if ok:
                        scaled = image.scaled(self.thumbnail_label.width(), self.thumbnail_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        self.thumbnail_label.setPixmap(scaled)
                    else:
                        self.thumbnail_label.setText("Nelze načíst obrázek.")
                else:
                    self.thumbnail_label.setText(f"Chyba načtení thumbnailu ({response.status_code}).")
            except Exception as e:
                self.thumbnail_label.setText(f"Chyba obrázku: {e}")
        else:
            self.thumbnail_label.setText("Náhled není dostupný.")

    def open_video(self, item):
        index = self.video_list.currentRow()
        if self.current_channel is None or index < 0:
            return
        entries = self.channels[self.current_channel]["entries"]
        video = entries[index]
        webbrowser.open(video.link)

    def on_thumbnail_click(self, event):
        index = self.video_list.currentRow()
        if self.current_channel is None or index < 0:
            return
        entries = self.channels[self.current_channel]["entries"]
        video = entries[index]
        webbrowser.open(video.link)

    def extract_channel_id(self, url):
        try:
            if not url.endswith("/about"):
                if url.endswith("/"):
                    url += "about"
                else:
                    url += "/about"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, verify=False)
            html = response.text
            match = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]+)"', html)
            if match:
                return match.group(1)
            match2 = re.search(r'<meta\s+itemprop="channelId"\s+content="(UC[\w-]+)"', html)
            if match2:
                return match2.group(1)
            match3 = re.search(r'<meta\s+property="og:url"\s+content="https://www\.youtube\.com/channel/(UC[\w-]+)"', html)
            if match3:
                return match3.group(1)
            scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, flags=re.DOTALL)
            for script in scripts:
                if 'channelId' in script:
                    json_matches = re.findall(r'("channelId":"(UC[\w-]+)")', script)
                    if json_matches:
                        return json_matches[0][1]
            return None
        except Exception as e:
            print(f"Chyba při získávání channel_id:", e)
            return None

    def save_channels(self):
        try:
            data_to_save = {name: info["id"] for name, info in self.channels.items()}
            with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Chyba při ukládání kanálů: {e}")

    def load_channels(self):
        try:
            if os.path.exists(CHANNELS_FILE):
                with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                    saved_channels = json.load(f)
                for channel_name, channel_id in saved_channels.items():
                    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                    feed = feedparser.parse(rss_url)
                    if feed.entries:
                        self.channels[channel_name] = {"id": channel_id, "entries": feed.entries}
                        self.channel_list.addItem(channel_name)
        except Exception as e:
            print(f"Chyba při načítání kanálů: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YoutubeRssReader()
    window.show()
    sys.exit(app.exec_())