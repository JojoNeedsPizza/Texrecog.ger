import cv2
import pytesseract
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
from difflib import SequenceMatcher

# Aktivierte Zeile für Windows:
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class VideoOCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video Text Extraktor (Optimiertes OCR)")
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
        preview_frame = tk.LabelFrame(self.root, text="Vorschau des erkannten Textes (Hohe Genauigkeit)", padx=10, pady=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

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
        self.btn_start.config(state=tk.DISABLED)
        self.btn_select.config(state=tk.DISABLED)
        threading.Thread(target=self.process_video, daemon=True).start()

    def is_duplicate(self, new_line, existing_lines, threshold=0.65):
        """Überprüft die Ähnlichkeit. Leicht gesenkt, um minimale OCR-Variationen besser abzufangen."""
        for existing_line in existing_lines:
            similarity = SequenceMatcher(None, new_line.lower(), existing_line.lower()).ratio()
            if similarity >= threshold:
                return True
        return False

    def clean_ocr_text(self, text):
        """Entfernt typischen OCR-Müll (Sonderzeichen-Fragmente)."""
        allowed_chars = "abcdefghijklmnopqrstuvwxyzäöüßABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÜ0123456789.,!?-+/():; "
        cleaned = "".join([c for c in text if c in allowed_chars])
        return cleaned.strip()

    def process_video(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            messagebox.showerror("Fehler", "Video konnte nicht geöffnet werden.")
            self.reset_buttons()
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Jede Sekunde ein Frame analysieren
        frame_interval = max(1, int(fps)) 
        
        unique_text_list = []
        frame_count = 0

        # Tesseract-Konfiguration: PSM 6 geht von einem einzelnen homogenen Textblock aus
        # Das verbessert das Erkennen von Sätzen im Vergleich zum Standard-Modus drastisch
        tesseract_config = r'--psm 6'

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_count % frame_interval == 0:
                percent = int((frame_count / total_frames) * 100)
                self.progress_label.config(text=f"Verarbeite... {percent}%")
                
                # --- BILD-VORVERARBEITUNG FÜR BESSERES OCR ---
                # 1. In Graustufen umwandeln
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # 2. Hochskalieren (Faktor 2), damit kleinere Schriftzüge schärfer für die Engine werden
                gray_resized = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                
                # 3. Otsu-Binarisierung: Berechnet automatisch den besten Schwellenwert,
                # um harten Schwarz-Weiß-Kontrast zu erzeugen (entfernt Grauschleier/Schatten)
                _, thresh = cv2.threshold(gray_resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # OCR ausführen mit optimierter Konfiguration
                try:
                    text = pytesseract.image_to_string(thresh, lang="deu+eng", config=tesseract_config)
                except pytesseract.TesseractError:
                    text = pytesseract.image_to_string(thresh, lang="eng", config=tesseract_config)

                # Zeilen verarbeiten
                for line in text.split("\n"):
                    cleaned_line = self.clean_ocr_text(line)
                    
                    # Nur sinnvolle Zeilen nehmen (länger als 3 Zeichen)
                    if len(cleaned_line) > 3:
                        if not self.is_duplicate(cleaned_line, unique_text_list, threshold=0.65):
                            unique_text_list.append(cleaned_line)

            frame_count += 1

        cap.release()
        
        self.extracted_text = "\n".join(unique_text_list)
        
        # GUI aktualisieren
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
