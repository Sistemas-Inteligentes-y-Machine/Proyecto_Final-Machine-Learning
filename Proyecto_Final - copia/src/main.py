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

# === Configuración OCR ===
try:
    reader = easyocr.Reader(['es'], gpu=True)
except:
    reader = easyocr.Reader(['es'], gpu=False)

# === Configuración de cámara ===
USE_PHONE_CAMERA = False
PHONE_CAMERA_URL = "http://192.168.0.105:8080/video"
ALLOWLIST = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZáéíóúÁÉÍÓÚüÜñÑ0123456789.,:;!?¡¿()[]{}-_/\\&%$#@+*=<> "

cap = cv2.VideoCapture(PHONE_CAMERA_URL if USE_PHONE_CAMERA else 0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

# === Funciones auxiliares ===
def resize_for_ocr(img, target_w=600):
    h, w = img.shape[:2]
    if w >= target_w:
        return img
    scale = target_w / float(w)
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

def clean_text(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9áéíóúÁÉÍÓÚüÜñÑ\.,:;!¡?¿()\[\]{}\-_/&%$#@+*=<>\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def postprocess_text(text):
    replacements = {
        '0':'O','1':'I','2':'Z','3':'E','4':'A',
        '5':'S','6':'G','7':'T','8':'B','9':'g',
        '|':'I','@':'a'
    }
    for wrong, right in replacements.items():
        text = text.replace(wrong, right)
    return re.sub(r'\s+', ' ', text).strip()

# === Funciones de OCR y cámara ===
def update_camera():
    ret, frame = cap.read()
    if ret:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)
        camera_label.imgtk = imgtk
        camera_label.configure(image=imgtk)
    ventana.after(80, update_camera)

def capture_and_process():
    ret, frame = cap.read()
    if not ret:
        output_box.insert(tk.END, "❌ No hay frame disponible.\n")
        return

    resized = resize_for_ocr(frame, target_w=600)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    results = reader.readtext(cv2.cvtColor(th, cv2.COLOR_GRAY2BGR), allowlist=ALLOWLIST)
    textos = [text for _, text, conf in results if conf >= 0.2]
    raw_text = " ".join(textos)

    texto_final = clean_text(postprocess_text(raw_text))

    if texto_final:
        output_box.insert(tk.END, f"✅ Texto detectado: {texto_final}\n")
    else:
        output_box.insert(tk.END, "⚠️ No se detectó texto legible.\n")

    try:
        if texto_final:
            engine = pyttsx3.init()
            engine.setProperty('rate', 160)
            engine.say(texto_final)
            engine.runAndWait()
            engine.stop()
    except Exception as e:
        output_box.insert(tk.END, f"⚠️ Error TTS: {e}\n")

def capture_and_process_async():
    threading.Thread(target=capture_and_process, daemon=True).start()

# === Asistente de voz usando SpeechRecognition ===
def voice_listener_sr():
    output_box.insert(tk.END, "🎤 Asistente de voz activo. Di 'capturar' o 'salir'.\n")
    r = sr.Recognizer()
    mic = sr.Microphone()

    # Ajustar ruido ambiental
    with mic as source:
        r.adjust_for_ambient_noise(source)

    while True:
        with mic as source:
            audio = r.listen(source, phrase_time_limit=5)
        try:
            command = r.recognize_google(audio, language="es-ES").lower()
            if command:
                output_box.insert(tk.END, f"🎙️ Comando detectado: {command}\n")
                if "capturar" in command:
                    capture_and_process_async()
                elif "salir" in command or "cerrar" in command:
                    output_box.insert(tk.END, "👋 Cerrando aplicación por comando de voz...\n")
                    ventana.quit()
                    break
        except sr.UnknownValueError:
            pass  # No se entendió
        except sr.RequestError as e:
            output_box.insert(tk.END, f"⚠️ Error reconocimiento de voz: {e}\n")

# === Interfaz Tkinter ===
ventana = tk.Tk()
ventana.title("OCR con EasyOCR + Cámara + Asistente de Voz")
ventana.geometry("1000x750")
ventana.configure(bg="#1e1e1e")

frame_camera = tk.Frame(ventana, bg="#1e1e1e")
frame_camera.pack(pady=5)
camera_label = tk.Label(frame_camera, bg="black", width=480, height=320)
camera_label.pack()

frame_output = tk.Frame(ventana, bg="#1e1e1e")
frame_output.pack(pady=10, fill="both", expand=True)
output_box = scrolledtext.ScrolledText(
    frame_output,
    font=("Consolas", 12),
    width=120,
    height=20,
    bg="#252526",
    fg="#D4D4D4",
    insertbackground="white"
)
output_box.pack(pady=10, fill="both", expand=True)

# Iniciar cámara y asistente de voz (en hilo)
update_camera()
threading.Thread(target=voice_listener_sr, daemon=True).start()

ventana.mainloop()
cap.release()



