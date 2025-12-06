import tkinter as tk
from tkinter import scrolledtext
import cv2
import pyttsx3
import easyocr
import numpy as np
import re
import threading
from PIL import Image, ImageTk
import speech_recognition as sr
import os
import platform
import subprocess
from datetime import datetime
from reportlab.pdfgen import canvas
import pytesseract

# ============================
# CONFIGURAR RUTA TESSERACT
# ============================
TES_PATH_1 = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TES_PATH_2 = r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"

if os.path.exists(TES_PATH_1):
    pytesseract.pytesseract.tesseract_cmd = TES_PATH_1
elif os.path.exists(TES_PATH_2):
    pytesseract.pytesseract.tesseract_cmd = TES_PATH_2
else:
    pytesseract.pytesseract.tesseract_cmd = None

# ============================
# CARPETA DE EXPORTADOS
# ============================
EXPORT_FOLDER = "exportados"
if not os.path.exists(EXPORT_FOLDER):
    os.makedirs(EXPORT_FOLDER)

ultimo_texto_leido = ""

# ============================
# EASYOCR
# ============================
try:
    reader = easyocr.Reader(['es'], gpu=True)
except:
    reader = easyocr.Reader(['es'], gpu=False)

ALLOWLIST = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZáéíóúÁÉÍÓÚüÜñÑ0123456789.,:;!?¡¿()[]{}-_/\\&%$#@+*=<> "

# ============================
# CONFIGURACIÓN DE CÁMARA
# ============================
USE_PHONE_CAMERA = False   # True para usar cámara del teléfono, False para webcam
PHONE_CAMERA_URL = "http://10.198.90.84:8080/video"

cap = cv2.VideoCapture(PHONE_CAMERA_URL if USE_PHONE_CAMERA else 0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# ============================
# FUNCIONES DE EXPORTACIÓN
# ============================
def save_text_to_txt(text):
    if not text.strip():
        output_box.insert(tk.END, "⚠️ No hay texto para guardar.\n")
        return
    filename = f"{EXPORT_FOLDER}/ocr_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    output_box.insert(tk.END, f"💾 TXT guardado en: {filename}\n")


def save_text_to_pdf(text):
    if not text.strip():
        output_box.insert(tk.END, "⚠️ No hay texto para guardar.\n")
        return
    filename = f"{EXPORT_FOLDER}/ocr_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
    pdf = canvas.Canvas(filename)
    pdf.setFont("Helvetica", 12)
    y = 800
    for line in text.split("\n"):
        pdf.drawString(30, y, line)
        y -= 20
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 12)
            y = 800
    pdf.save()
    output_box.insert(tk.END, f"📄 PDF guardado en: {filename}\n")


def open_export_folder():
    try:
        if platform.system() == "Windows":
            os.startfile(EXPORT_FOLDER)
        else:
            subprocess.Popen(["open" if platform.system() == "Darwin" else "xdg-open", EXPORT_FOLDER])
    except:
        output_box.insert(tk.END, "❌ Error al abrir carpeta.\n")

# ============================
# PROCESAMIENTO OCR
# ============================
def clean_text(text):
    text = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\.,:;!¡?¿()\[\]{}\-_/&%$#@+*=<>\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def postprocess_text(text):
    return text.strip()


def ocr_tesseract(frame):
    if pytesseract.pytesseract.tesseract_cmd is None:
        return ""
    pil_img = Image.fromarray(frame)
    text = pytesseract.image_to_string(pil_img, config="--psm 6 -l spa")
    return clean_text(postprocess_text(text))


def capture_and_process():
    global ultimo_texto_leido
    ret, frame = cap.read()
    if not ret:
        output_box.insert(tk.END, "❌ No hay frame disponible.\n")
        return

    results = reader.readtext(frame, allowlist=ALLOWLIST)
    textos = [text for _, text, conf in results if conf >= 0.25]
    raw = " ".join(textos).strip()
    if not raw:
        raw = ocr_tesseract(frame)

    texto_final = clean_text(postprocess_text(raw))
    if texto_final:
        ultimo_texto_leido = texto_final
        output_box.insert(tk.END, f"\n✅ Detectado: {texto_final}\n")

        engine = pyttsx3.init()
        engine.setProperty("rate", 160)
        engine.say(texto_final)
        engine.runAndWait()
    else:
        output_box.insert(tk.END, "⚠️ No se detectó texto legible.\n")


def capture_and_process_async():
    threading.Thread(target=capture_and_process, daemon=True).start()

# ============================
# ASISTENTE DE VOZ
# ============================
def voice_listener_sr():
    output_box.insert(tk.END, "🎤 Listo. Di: Capturar, Guardar pdf, Guardar txt, Salir.\n")
    r = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        r.adjust_for_ambient_noise(source, duration=1)
        r.energy_threshold = 2800

    while True:
        with mic as source:
            try:
                audio = r.listen(source, timeout=3, phrase_time_limit=4)
            except:
                continue

        try:
            command = r.recognize_google(audio, language="es-ES").lower()
            output_box.insert(tk.END, f"\n🎙️ Detectado: {command}\n")

            if "capturar" in command:
                output_box.insert(tk.END, "🔧 Ejecutando: CAPTURAR\n")
                capture_and_process_async()
            elif "guardar pdf" in command:
                output_box.insert(tk.END, "🔧 Ejecutando: GUARDAR PDF\n")
                save_text_to_pdf(ultimo_texto_leido)
            elif "guardar txt" in command:
                output_box.insert(tk.END, "🔧 Ejecutando: GUARDAR TXT\n")
                save_text_to_txt(ultimo_texto_leido)
            elif "salir" in command or "cerrar" in command:
                output_box.insert(tk.END, "👋 Cerrando aplicación...\n")
                ventana.quit()
                break
            else:
                output_box.insert(tk.END, "⚠️ Comando no reconocido.\n")

        except sr.UnknownValueError:
            continue
        except Exception as e:
            output_box.insert(tk.END, f"⚠️ Error voz: {e}\n")

# ============================
# INTERFAZ MODERNA COMO EN LA IMAGEN
# ============================
ventana = tk.Tk()
ventana.title("EcoLector")
ventana.geometry("1300x780")
ventana.configure(bg="#121212")

# HEADER
header = tk.Label(
    ventana,
    text="📘 EcoLector: Tecnología de Lectura Asistida para Todos",
    bg="#1F1F1F",
    fg="white",
    font=("Segoe UI", 18, "bold"),
    pady=15
)
header.pack(fill="x")

# MAIN FRAME
main_frame = tk.Frame(ventana, bg="#121212")
main_frame.pack(fill="both", expand=True)

# PANEL IZQUIERDO - CAMARA
left_frame = tk.Frame(main_frame, bg="#121212")
left_frame.pack(side="left", padx=15, pady=10)

camera_border = tk.Frame(left_frame, bg="#00A8E8", padx=3, pady=3)
camera_border.pack()

camera_label = tk.Label(camera_border, width=640, height=480, bg="grey")
camera_label.pack()

# PANEL DERECHO - CONSOLA
right_frame = tk.Frame(main_frame, bg="#121212")
right_frame.pack(side="right", fill="both", expand=True, padx=10)

label_console = tk.Label(
    right_frame,
    text="📄 Consola OCR:",
    bg="#121212",
    fg="#FFFFFF",
    font=("Segoe UI", 14, "bold")
)
label_console.pack(anchor="w")

output_box = scrolledtext.ScrolledText(
    right_frame,
    font=("Consolas", 12),
    bg="#1E1E1E",
    fg="#D4D4D4",
    width=80, height=25
)
output_box.pack(fill="both", expand=True, pady=5)

# FUNCION PARA ACTUALIZAR CAMARA
def update_camera():
    if USE_PHONE_CAMERA or cap.isOpened():
        ret, frame = cap.read()
        if ret:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imgtk = ImageTk.PhotoImage(image=Image.fromarray(rgb))
            camera_label.imgtk = imgtk
            camera_label.configure(image=imgtk)
    ventana.after(80, update_camera)

update_camera()
threading.Thread(target=voice_listener_sr, daemon=True).start()

ventana.mainloop()
cap.release()
