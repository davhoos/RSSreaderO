#!/usr/bin/env python3

import sys
import re
import json
import os
import requests
import feedparser
import webbrowser
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QListWidget, QLabel, QLineEdit, QInputDialog, QMessageBox, QSizePolicy, QScrollArea
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt
from io import BytesIO

CHANNELS_FILE = "RSS_channels.json"

class YoutubeRssReader(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube RSS channels reader")
        self.setGeometry(100, 100, 1200, 800)

        # Hlavní layout - horizontální
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # Levý panel: seznam kanálů + přidat/odebrat kanál
        left_panel = QVBoxLayout()
        main_layout.addLayout(left_panel, 2)

        # Inicializace channel_list a dalších widgetů
        self.channel_list = QListWidget()
        self.channel_list.setFixedHeight(650)  # Fixní výška pro seznam kanálů
        left_panel.addWidget(QLabel("Kanály:"))
        left_panel.addWidget(self.channel_list)

        self.add_channel_btn = QPushButton("Přidat kanál")
        left_panel.addWidget(self.add_channel_btn)

        self.remove_channel_btn = QPushButton("Odebrat vybraný kanál")
        left_panel.addWidget(self.remove_channel_btn)

        # Pravý panel: seznam videí + náhled + popis
        right_panel = QVBoxLayout()
        main_layout.addLayout(right_panel, 5)

        right_panel.addWidget(QLabel("Videa:"))
        
        # Vytvoření scroll area pro seznam videí, aby se objevil posuvník, pokud bude seznam dlouhý
        self.video_list = QListWidget()
        self.video_list.setFixedHeight(200)  # Fixní výška pro seznam videí
        right_panel.addWidget(self.video_list)

        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setFixedHeight(410)  # Fixní výška pro náhled videa
        self.thumbnail_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.thumbnail_label.mousePressEvent = self.on_thumbnail_click  # Přidání obsluhy kliknutí
        right_panel.addWidget(self.thumbnail_label)

        # Text pro popis videa
        self.description_label = QLabel("Vyberte video pro zobrazení podrobností.")
        self.description_label.setWordWrap(True)

        # Vytvoření scroll area pro popis videa, pokud bude text dlouhý
        self.description_scroll_area = QScrollArea()
        self.description_scroll_area.setWidget(self.description_label)
        self.description_scroll_area.setWidgetResizable(True)  # Umožní zvětšení textu s obsahem
        right_panel.addWidget(self.description_scroll_area, 1)

        # Data
        self.channels = {}  # channel_name -> {'id': channel_id, 'entries': [...]}
        self.current_channel = None

        # Signály
        self.add_channel_btn.clicked.connect(self.add_channel)
        self.remove_channel_btn.clicked.connect(self.remove_channel)
        self.channel_list.currentRowChanged.connect(self.channel_changed)
        self.video_list.currentRowChanged.connect(self.video_selected)
        self.video_list.itemDoubleClicked.connect(self.open_video)

        # Načti uložené kanály
        self.load_channels()

        # Nastavení fontu po inicializaci všech widgetů
        self.set_font()

    def set_font(self):
        """Nastaví font pro celé rozhraní"""
        font = QFont("Arial", 12)  # Nastaví font na Arial, velikost 14px (o 2px větší než základní)
        font.setWeight(QFont.Bold)  # Nastaví tučné písmo

        # Nastavení písma pro všechny widgety
        self.setFont(font)
        self.channel_list.setFont(font)
        self.video_list.setFont(font)
        self.description_label.setFont(font)

    def add_channel(self):
        """Přidání nového YouTube kanálu"""
        channel_id, ok = QInputDialog.getText(self, "Zadej channel ID-UC kanal!", "UC kanál ID example (UCxxxxxxxx):")
        
        # Validace, že ID začíná na "UC" a je správného formátu
        if not ok or not channel_id.startswith("UC") or not re.match(r"^UC[\w-]+$", channel_id):
            QMessageBox.warning(self, "Chyba", "Neplatné channel ID, kanál nebude přidán. Ujistěte se, že ID začíná na 'UC' a má správný formát.")
            return

        # Načítání RSS feedu pro kanál
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            QMessageBox.warning(self, "Chyba", "Nepodařilo se načíst videa z tohoto kanálu.")
            return

        # Načtení názvu kanálu a videí
        channel_title = feed.feed.get("title", channel_id)
        self.channels[channel_title] = {"id": channel_id, "entries": feed.entries}

        # Přidání kanálu do seznamu, pokud již neexistuje
        existing_channels = [self.channel_list.item(i).text() for i in range(self.channel_list.count())]
        if channel_title not in existing_channels:
            self.channel_list.addItem(channel_title)

        # Nastavení vybraného kanálu
        idx = self.channel_list.findItems(channel_title, Qt.MatchExactly)[0]
        self.channel_list.setCurrentItem(idx)

        # Uložení kanálů
        self.save_channels()

    def remove_channel(self):
        """Odebrání vybraného kanálu"""
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
            # Odebrání kanálu z dat
            if channel_name in self.channels:
                del self.channels[channel_name]

            # Odebrání kanálu z UI
            self.channel_list.takeItem(current_row)
            self.video_list.clear()
            self.thumbnail_label.clear()
            self.description_label.setText("Vyberte video pro zobrazení podrobností.")
            self.current_channel = None

            # Uložení změn
            self.save_channels()

    def channel_changed(self, index):
        """Změna vybraného kanálu"""
        if index < 0:
            return
        channel_name = self.channel_list.item(index).text()
        self.current_channel = channel_name
        self.load_videos_for_channel(channel_name)

    def load_videos_for_channel(self, channel_name):
        """Načtení videí pro vybraný kanál"""
        self.video_list.clear()
        self.thumbnail_label.clear()
        self.description_label.setText("Vyberte video pro zobrazení podrobností.")

        entries = self.channels[channel_name]["entries"]
        for entry in entries:
            self.video_list.addItem(entry.title)

    def video_selected(self, index):
        """Zobrazení detailů videa"""
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

        # Načtení náhledu videa
        thumbnail_url = None
        if "media_thumbnail" in video:
            thumbnail_url = video.media_thumbnail[0]["url"]
        elif "media_content" in video:
            thumbnail_url = video.media_content[0]["url"]

        if thumbnail_url:
            try:
                response = requests.get(thumbnail_url)
                image = QPixmap()
                image.loadFromData(response.content)
                scaled = image.scaled(self.thumbnail_label.width(), self.thumbnail_label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.thumbnail_label.setPixmap(scaled)
            except Exception:
                self.thumbnail_label.clear()
        else:
            self.thumbnail_label.clear()

    def open_video(self, item):
        """Otevření videa v prohlížeči"""
        index = self.video_list.currentRow()
        if self.current_channel is None or index < 0:
            return

        entries = self.channels[self.current_channel]["entries"]
        video = entries[index]
        webbrowser.open(video.link)

    def on_thumbnail_click(self, event):
        """Obsluha kliknutí na náhled videa"""
        index = self.video_list.currentRow()
        if self.current_channel is None or index < 0:
            return

        entries = self.channels[self.current_channel]["entries"]
        video = entries[index]
        webbrowser.open(video.link)

    def extract_channel_id(self, url):
        """Extrahování ID kanálu z URL"""
        try:
            if not url.endswith("/about"):
                if url.endswith("/"):
                    url += "about"
                else:
                    url += "/about"

            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers)
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
        """Uložení kanálů do souboru"""
        try:
            # Uložíme pouze názvy a id kanálů (videá stáhneme při načtení)
            data_to_save = {name: info["id"] for name, info in self.channels.items()}
            with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Chyba při ukládání kanálů: {e}")

    def load_channels(self):
        """Načtení kanálů ze souboru"""
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
