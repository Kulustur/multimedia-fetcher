import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from yt_dlp import YoutubeDL

try:
    import imageio_ffmpeg
    FFMPEG_YOLU = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_YOLU = None  # sistemde ffmpeg kuruluysa yine de çalışır

KALITELER = {
    "Best (mp4)": "bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[vcodec^=vp9]+bestaudio/best",
    "1080p": "bestvideo[height<=1080][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best",
    "720p": "bestvideo[height<=720][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best",
    "480p": "bestvideo[height<=480][vcodec^=avc1]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best",
    "Audio only (m4a)": "bestaudio[ext=m4a]/bestaudio",
}


class IptalEdildi(Exception):
    """Kullanıcı İptal butonuna basınca indirmeyi durdurmak için."""


class Uygulama(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video İndirici")
        self.geometry("560x260")
        self.resizable(False, False)

        self.klasor = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.kalite = tk.StringVar(value="En iyi (mp4)")
        self.indiriliyor = False
        self.iptal_istendi = False

        cerceve = ttk.Frame(self, padding=15)
        cerceve.pack(fill="both", expand=True)

        ttk.Label(cerceve, text="Video linki:").grid(row=0, column=0, sticky="w")
        self.link_kutusu = ttk.Entry(cerceve, width=48)
        self.link_kutusu.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 10))
        ttk.Button(cerceve, text="Yapıştır", command=self.yapistir).grid(
            row=1, column=2, padx=(5, 0), pady=(0, 10)
        )

        ttk.Label(cerceve, text="Kalite:").grid(row=2, column=0, sticky="w")
        ttk.Combobox(
            cerceve, textvariable=self.kalite, values=list(KALITELER),
            state="readonly", width=20,
        ).grid(row=2, column=1, sticky="w", pady=(0, 10))

        ttk.Label(cerceve, text="Kayıt klasörü:").grid(row=3, column=0, sticky="w")
        ttk.Entry(cerceve, textvariable=self.klasor, width=45).grid(row=3, column=1, sticky="we")
        ttk.Button(cerceve, text="Seç", command=self.klasor_sec).grid(row=3, column=2, padx=(5, 0))

        butonlar = ttk.Frame(cerceve)
        butonlar.grid(row=4, column=0, columnspan=3, pady=15, sticky="we")
        butonlar.columnconfigure(0, weight=3)
        butonlar.columnconfigure(1, weight=1)
        self.buton = ttk.Button(butonlar, text="İndir", command=self.baslat)
        self.buton.grid(row=0, column=0, sticky="we")
        self.iptal_butonu = ttk.Button(
            butonlar, text="İptal", command=self.iptal_et, state="disabled"
        )
        self.iptal_butonu.grid(row=0, column=1, sticky="we", padx=(5, 0))

        self.cubuk = ttk.Progressbar(cerceve, maximum=100)
        self.cubuk.grid(row=5, column=0, columnspan=3, sticky="we")

        self.durum = ttk.Label(cerceve, text="Hazır.")
        self.durum.grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))

        cerceve.columnconfigure(1, weight=1)

    def klasor_sec(self):
        secilen = filedialog.askdirectory(initialdir=self.klasor.get())
        if secilen:
            self.klasor.set(secilen)

    def yapistir(self):
        try:
            metin = self.clipboard_get().strip()
        except tk.TclError:
            self.durum.config(text="Panoda yapıştırılacak bir şey yok.")
            return
        self.link_kutusu.delete(0, "end")
        self.link_kutusu.insert(0, metin)

    def iptal_et(self):
        if self.indiriliyor:
            self.iptal_istendi = True
            self.iptal_butonu.config(state="disabled")
            self.durum.config(text="İptal ediliyor...")

    def baslat(self):
        if self.indiriliyor:
            return
        url = self.link_kutusu.get().strip()
        if not url:
            messagebox.showwarning("Eksik", "Lütfen bir video linki gir.")
            return
        self.indiriliyor = True
        self.iptal_istendi = False
        self.buton.config(state="disabled")
        self.iptal_butonu.config(state="normal")
        self.cubuk["value"] = 0
        self.durum.config(text="Başlıyor...")
        threading.Thread(target=self.indir, args=(url,), daemon=True).start()

    def ilerleme(self, d):
        if self.iptal_istendi:
            raise IptalEdildi()
        if d["status"] == "downloading":
            toplam = d.get("total_bytes") or d.get("total_bytes_estimate")
            if toplam:
                yuzde = d["downloaded_bytes"] / toplam * 100
                hiz = d.get("_speed_str", "").strip()
                self.after(0, self.guncelle, yuzde, f"İndiriliyor... %{yuzde:.1f}  {hiz}")
        elif d["status"] == "finished":
            self.after(0, self.guncelle, 100, "İşleniyor / birleştiriliyor...")

    def guncelle(self, yuzde, metin):
        self.cubuk["value"] = yuzde
        self.durum.config(text=metin)

    def indir(self, url):
        ayarlar = {
            "format": KALITELER[self.kalite.get()],
            "outtmpl": str(Path(self.klasor.get()) / "%(title)s.%(ext)s"),
            "progress_hooks": [self.ilerleme],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
        }
        if self.kalite.get() != "Sadece ses (m4a)":
            ayarlar["merge_output_format"] = "mp4"
        if FFMPEG_YOLU:
            ayarlar["ffmpeg_location"] = FFMPEG_YOLU

        try:
            with YoutubeDL(ayarlar) as ydl:
                ydl.download([url])
            self.after(0, self.bitti, "İndirme tamamlandı!")
        except IptalEdildi:
            self.after(0, self.bitti, "İndirme iptal edildi.")
        except Exception as hata:
            if self.iptal_istendi:
                self.after(0, self.bitti, "İndirme iptal edildi.")
                return
            self.after(0, self.bitti, f"Hata: {str(hata)[:150]}")

    def bitti(self, mesaj):
        self.indiriliyor = False
        self.buton.config(state="normal")
        self.iptal_butonu.config(state="disabled")
        self.durum.config(text=mesaj)


if __name__ == "__main__":
    Uygulama().mainloop()
