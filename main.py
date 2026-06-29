import cv2
import pytesseract
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
from PIL import Image

# HINWEIS FÜR WINDOWS-NUTZER:
# Wenn Tesseract nicht im PATH ist, entferne das '#' am Anfang der nächsten Zeile und passe den Pfad an:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class VideoOCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Text Extraktor (OCR)")
        self.root.geometry("650x550")
        self.root.minsize(500, 400)

        self.video_path = ""
        self.extracted_text = ""

        self.create_widgets()

    def create_widgets(self):
        # --- Datei-Auswahl Bereich ---
        file_frame = tk.Frame(self.root, pady=10)
        file_frame.pack(fill=tk.X, padx=10)

        self.btn_select = tk.Button(file_frame, text="Video auswählen", command=self.select_video, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.btn_select.pack(side=tk.LEFT, padx=5)

        self.lbl_video_path = tk.Label(file_frame, text="Keine Datei ausgewählt", fg="gray", wraplength=400, anchor="w", justify=tk.LEFT)
        self.lbl_video_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # --- Steuerungs-Bereich ---
        control_frame = tk.Frame(self.root, pady=5)
        control_frame.pack(fill=tk.X, padx=10)

        self.btn_start = tk.Button(control_frame, text="Texterkennung starten", command=self.start_ocr_thread, state=tk.DISABLED, bg="#2196F3", fg="white", font=("Arial", 10, "bold"))
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.progress_label = tk.Label(control_frame, text="", fg="blue")
        self.progress_label.pack(side=tk.LEFT, padx=10)

        # --- Vorschau-Bereich (Preview) ---
        preview_frame = tk.LabelFrame(self.root, text="Vorschau des erkannten Textes", padx=10, pady=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, tbody=10)

        self.txt_preview = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD, font=("Courier New", 10))
        self.txt_preview.pack(fill=tk.BOTH, expand=True)

        # --- Speicher-Bereich ---
        save_frame = tk.Frame(self.root, pady=10)
        save_frame.pack(fill=tk.X, padx=10)

        self.btn_save = tk.Button(save_frame, text="Als .txt speichern", command=self.save_to_txt, state=tk.DISABLED, bg="#FF9800", fg="white", font=("Arial", 10, "bold"))
        self.btn_save.pack(side=tk.RIGHT, padx=5)

    def select_video(self):
        file_types = [("Video-Dateien", "*.mp4 *.avi *.mkv *.mov"), ("Alle Dateien", "*.*")]
        self.video_path = filedialog.askopenfilename(title="Video auswählen", filetypes=file_types)
        
        if self.video_path:
            self.lbl_video_path.config(text=self.video_path, fg="black")
            self.btn_start.config(state=tk.NORMAL)
            self.btn_save.config(state=tk.DISABLED)
            self.txt_preview.delete("1.0", tk.END)

    def start_ocr_thread(self):
        # Threading verhindert, dass die GUI während der Verarbeitung einfriert
        self.btn_start.config(state=tk.DISABLED)
        self.btn_select.config(state=tk.DISABLED)
        threading.Thread(target=self.process_video, daemon=True).start()

    def process_video(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            messagebox.showerror("Fehler", "Video konnte nicht geöffnet werden.")
            self.reset_buttons()
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Um die Performance zu verbessern, analysieren wir standardmäßig z. B. alle 1 Sekunde (alle 'fps' Frames)
        # Wenn du eine präzisere Erkennung willst, verringere das Frame-Intervall (z.B. alle 0.5 Sekunden)
        frame_interval = max(1, int(fps)) 
        
        seen_lines = set()
        unique_text_list = []
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                # GUI-Fortschritt aktualisieren
                percent = int((frame_count / total_frames) * 100)
                self.progress_label.config(text=f"Verarbeite... {percent}%")
                
                # Vorverarbeitung für besseres OCR (Graustufen)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # OCR ausführen (Sprachauswahl standardmäßig Englisch + Deutsch mit 'eng+deu')
                # Falls 'deu' Fehler wirft, lade die deutsche Tesseract-Datei herunter oder nutze nur 'eng'
                try:
                    text = pytesseract.image_to_string(gray, lang="deu+eng")
                except pytesseract.TesseractError:
                    # Fallback auf Standard (Englisch), falls Deutsch nicht installiert ist
                    text = pytesseract.image_to_string(gray, lang="eng")

                # Text säubern und Duplikate filtern
                for line in text.split("\n"):
                    cleaned_line = line.strip()
                    # Ignoriere zu kurze Fragmente oder bereits erkannte Zeilen
                    if len(cleaned_line) > 3 and cleaned_line not in seen_lines:
                        seen_lines.add(cleaned_line)
                        unique_text_list.append(cleaned_line)

            frame_count += 1

        cap.release()
        
        # Ergebnis zusammenführen
        self.extracted_text = "\n".join(unique_text_list)
        
        # GUI nach Verarbeitung aktualisieren
        self.progress_label.config(text="Fertig!")
        self.txt_preview.delete("1.0", tk.END)
        self.txt_preview.insert(tk.END, self.extracted_text)
        
        self.btn_save.config(state=tk.NORMAL)
        self.btn_select.config(state=tk.NORMAL)

    def save_to_txt(self):
        if not self.extracted_text.strip():
            messagebox.showwarning("Warnung", "Es wurde kein Text zum Speichern gefunden.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Textdateien", "*.txt")],
            title="Textdatei speichern"
        )
        
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    # Liest den aktuellen Inhalt aus dem Vorschaufeld (falls der User noch etwas editiert hat)
                    current_text = self.txt_preview.get("1.0", tk.END).strip()
                    f.write(current_text)
                messagebox.showinfo("Erfolgreich", "Datei wurde erfolgreich gespeichert!")
            except Exception as e:
                messagebox.showerror("Fehler", f"Datei konnte nicht gespeichert werden:\n{e}")

    def reset_buttons(self):
        self.btn_start.config(state=tk.NORMAL)
        self.btn_select.config(state=tk.NORMAL)
        self.progress_label.config(text="")


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoOCRApp(root)
    root.mainloop()
