import cv2
import time
import speech_recognition as sr
import google.generativeai as genai
from PIL import Image
from ultralytics import YOLOWorld
from elevenlabs.client import ElevenLabs
from elevenlabs.play import play
import serial
import os

from solana.rpc.api import Client
from solders.keypair import Keypair
from solders.transaction import Transaction
from solders.instruction import Instruction
from solders.pubkey import Pubkey
import time

from dotenv import load_dotenv

# ==========================================
# 1. API & HARDWARE CONFIGURATIONS
# ==========================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
SECRET_PASSWORD = os.getenv("SECRET_PASSWORD")
# ELEVENLABS_API_KEY = "sk_765905069abc9ca2a4910b70bdf81768a65a9291e6a6f239"
SECRET_PASSWORD = "open"

# --- SERIAL PORT CONFIGURATION ---
# Replace this with your actual Arduino port (e.g., 'COM3' or '/dev/cu.usbmodem1234')
SERIAL_PORT = 'COM3' 

try:
    xiao = serial.Serial(SERIAL_PORT, 9600, timeout=1)
    print(f"[HARDWARE] Successfully connected to XIAO on {SERIAL_PORT}")
    time.sleep(2) # Give the microcontroller a second to reset after connecting
except Exception as e:
    print(f"[HARDWARE WARNING] Could not connect to XIAO on {SERIAL_PORT}. Running in software-only mode. Error: {e}")
    xiao = None

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.5-flash') 
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

print("[SYSTEM] Loading YOLO-World...")
yolo_model = YOLOWorld('yolov8s-world.pt')
yolo_model.set_classes(["person", "cardboard box", "delivery package"])

# ==========================================
# 2. THE AI FUNCTIONS
# ==========================================
def verify_intent_with_gemini(frame):
    print("[THINKING] YOLO triggered. Verifying delivery intent with Gemini...")
    color_corrected = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(color_corrected)
    
    prompt = """
    Look at this image from a security camera. A person is holding a cardboard box or package.
    Are they facing the camera or interacting with it?
    Since this is a hackathon demo, ANY person holding a box and looking at/facing the camera should be approved as a delivery.
    
    Respond with ONLY ONE WORD:
    - "CONFIRMED" (if a person is holding a box and reasonably facing the camera)
    - "FALSE_ALARM" (if there is no box, or they are walking away/ignoring the camera)
    """
    try:
        response = gemini_model.generate_content([prompt, pil_image])
        return response.text.strip().upper() == "CONFIRMED"
    except Exception as e:
        print(f"[API ERROR] Vision check failed: {e}")
        return False

def ask_gemini_package_status(mailman_speech):
    print(f"[THINKING] Analyzing speech intent: '{mailman_speech}'")
    prompt = f"""
    You are the brain of a robot mail-receiver. The mailman just said: "{mailman_speech}"
    Determine if the mailman is indicating the package is too big to fit inside the robot, or if they are done putting it in.
    Respond with ONLY ONE WORD:
    - "TOO_BIG" (if they say it won't fit, it's too large, etc.)
    - "DONE" (if they say thanks, okay, it's in, or anything positive)
    - "UNKNOWN" (if the text is gibberish)
    """
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip().upper()
    except Exception as e:
        print(f"[API ERROR] Text check failed: {e}")
        return "UNKNOWN"

def speak(text, mode="friendly"):
    print(f"\n[SAURON]: {text}")
    # Replace with your actual ElevenLabs Voice IDs
    voice_id = "JBFqnCBsd6RMkjVDRZzb" if mode == "friendly" else "pNInz6obpgDQGcFmaJgB" 
    try:
        audio = elevenlabs_client.text_to_speech.convert(
            text=text, voice_id=voice_id, model_id="eleven_multilingual_v2", output_format="mp3_44100_128"
        )
        play(audio)
    except Exception as e:
        print(f"[VOICE ERROR]: {e}")

def listen_for_speech():
    recognizer = sr.Recognizer()
    
    recognizer.energy_threshold = 3000 
    recognizer.dynamic_energy_threshold = True

    with sr.Microphone() as source:
        print("\n[MIC] Adjusting for background noise (wait 1 second)...")
        # Increased duration to get a better read on the room's background noise
        recognizer.adjust_for_ambient_noise(source, duration=1.0) 
        
        print("[MIC] 🟢 LISTENING NOW! Speak clearly...")
        try:
            # timeout=8: It will wait up to 8 seconds for you to START making noise
            # phrase_time_limit=10: It will record for up to 10 seconds once you start talking
            audio = recognizer.listen(source, timeout=8, phrase_time_limit=10)
            
            print("[MIC] Processing audio with Google...")
            text = recognizer.recognize_google(audio)
            print(f"[MIC] Heard: '{text}'")
            return text.lower()
            
        except sr.UnknownValueError:
            print("[MIC ERROR] I heard noise, but could not understand the words.")
            return ""
        except sr.WaitTimeoutError:
            print("[MIC ERROR] Timed out. I didn't hear anything loud enough to trigger.")
            return ""
        except Exception as e:
            print(f"[MIC ERROR] System error: {e}")
            return ""
        
def log_intrusion_to_solana():
    print("\n[WEB3] Initiating Immutable Security Log on Solana...")
    
    try:
        # 1. Connect to Solana Devnet (The free testing network)
        solana_client = Client("https://api.devnet.solana.com")
        
        # 2. Generate a random burner wallet for the robot
        sauron_wallet = Keypair()
        
        # 3. Request free "Devnet SOL" to pay for the transaction fee
        print("[WEB3] Requesting Devnet SOL for transaction fees...")
        solana_client.request_airdrop(sauron_wallet.pubkey(), 1_000_000_000) 
        time.sleep(5) # Wait for the blockchain to process the fake money
        
        # 4. Create the Memo Instruction
        # This is the official Solana Memo Program address
        memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
        
        # The message we are cementing into the blockchain forever
        log_message = f"SAURON_SECURITY_ALERT: Intruder detected at Unix Timestamp {time.time()}."
        
        instruction = Instruction(
            program_id=memo_program_id,
            accounts=[],
            data=log_message.encode('utf-8')
        )
        
        # 5. Build and send the transaction
        transaction = Transaction().add(instruction)
        result = solana_client.send_transaction(transaction, sauron_wallet)
        
        # 6. Get the transaction signature (The receipt!)
        tx_sig = result.value
        print(f"\n✅ [WEB3 SUCCESS] Intrusion logged permanently on Solana!")
        print(f"🔗 View the receipt here: https://explorer.solana.com/tx/{tx_sig}?cluster=devnet\n")
        
        return str(tx_sig)
        
    except Exception as e:
        print(f"[WEB3 ERROR] Failed to log to Solana: {e}")
        return None

# ==========================================
# 3. MAIN LOGIC LOOP
# ==========================================
def main():
    cap = cv2.VideoCapture(0)
    state = "IDLE"
    consecutive_detections = 0 
    
    # --- NEW: Tracking why we are guarding ---
    guard_mode = None 
    guard_start_time = 0 
    
    print("\n[SYSTEM] Sauron is online and watching the door. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret: continue
        frame_height = frame.shape[0]
        
        # --- STATE: IDLE (Watching) ---
        if state == "IDLE":
            results = yolo_model.predict(frame, conf=0.15, verbose=False)
            names_seen = [yolo_model.names[int(cls)] for cls in results[0].boxes.cls.tolist()]
            
            if "person" in names_seen and ("cardboard box" in names_seen or "delivery package" in names_seen):
                consecutive_detections += 1
            else:
                consecutive_detections = 0 
                
            if consecutive_detections >= 5:
                if verify_intent_with_gemini(frame):
                    speak("Delivery detected. Please state the delivery password.", mode="friendly")
                    state = "VERIFYING"
                else:
                    print("[ACTION] False alarm. Pausing for 10 seconds to save quota.")
                    time.sleep(10) 
                consecutive_detections = 0 
                
        # --- STATE: VERIFYING (Password) ---
        elif state == "VERIFYING":
            spoken_text = listen_for_speech()
            
            if SECRET_PASSWORD in spoken_text:
                speak("Password accepted. Opening hatch. Please tell me if the package is too big.", mode="friendly")
                state = "RECEIVING"
            elif spoken_text != "":
                speak("Incorrect password. I am entering guard mode. Step away.", mode="aggressive")
                
                # --- NEW: Set temporary guarding ---
                guard_mode = "wrong_password"
                guard_start_time = time.time()
                state = "GUARDING"
            else:
                state = "IDLE" 
                
        # --- STATE: RECEIVING (Package check) ---
        elif state == "RECEIVING":
            print("[SYSTEM] Hatch is open. Waiting for input...")
            spoken_text = listen_for_speech()
            
            if spoken_text:
                gemini_decision = ask_gemini_package_status(spoken_text)
                if gemini_decision == "TOO_BIG":
                    speak("Understood. Closing hatch. Place the package next to me and I will guard it.", mode="friendly")
                    
                    # --- NEW: Set indefinite guarding ---
                    guard_mode = "package_guard"
                    state = "GUARDING"
                    
                elif gemini_decision in ["DONE", "UNKNOWN"]:
                    speak("Thank you for the delivery. Have a safe route!", mode="friendly")
                    time.sleep(5) 
                    state = "IDLE"
            else:
                speak("Hatch closing. Thank you!", mode="friendly")
                time.sleep(3)
                state = "IDLE"

        # --- STATE: GUARDING (Attack Mode) ---
        elif state == "GUARDING":
            # --- NEW: Check if the 10-second penalty is over ---
            if guard_mode == "wrong_password" and (time.time() - guard_start_time > 10):
                print("[SYSTEM] 10-second penalty over. Returning to IDLE.")
                state = "IDLE"
                continue # Skip the rest of the loop and go back to watching

            # Run YOLO to look for intruders
            results = yolo_model.predict(frame, conf=0.3, verbose=False)
            for box in results[0].boxes:
                if yolo_model.names[int(box.cls[0])] == "person":
                    box_height = box.xyxy[0].tolist()[3] - box.xyxy[0].tolist()[1]
                    
                    if box_height > (frame_height * 0.50):
                        # --- NEW: Randomized Aggressive Warnings ---
                        import random
                        warnings = [
                            "WARNING! You are entering a restricted zone!",
                            "Step away immediately! I am calling the police!",
                            "Intruder detected. You are being recorded.",
                            "Leave the premises now or defensive measures will be deployed!"
                        ]
                        speak(random.choice(warnings), mode="aggressive")
                        log_intrusion_to_solana()
                        
                        if xiao:
                            print("[HARDWARE] Sending ATTACK signal to XIAO!")
                            xiao.write(b"ATTACK\n")
                            xiao.flush() 
                            
                        print("[SYSTEM] Waiting for 12-second attack sequence to finish...")
                        time.sleep(12) 
                        
                        # Reset the timer so it doesn't instantly time out right after an attack
                        if guard_mode == "wrong_password":
                            guard_start_time = time.time()
                            
                        break 

        # --- DISPLAY ---
        display_frame = results[0].plot() if state in ["IDLE", "GUARDING"] else frame
        cv2.putText(display_frame, f"STATE: {state}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow('Sauron Vision', display_frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    if xiao:
        xiao.close()

if __name__ == "__main__":
    main()