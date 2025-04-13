import os
import streamlit as st
import google.generativeai as genai
import requests
import tempfile
import json
import time
import streamlit.components.v1 as components
from io import BytesIO
from dotenv import load_dotenv
import speech_recognition as sr
import uuid
from langdetect import detect

# Set page configuration for tablet
st.set_page_config(
    page_title="AI Einstein", 
    page_icon="🧠", 
    layout="wide",
    initial_sidebar_state="collapsed"  # Hide sidebar by default for more tablet space
)

# Add custom CSS for tablet-friendly UI
st.markdown("""
<style>
    /* Make buttons larger and more touch-friendly */
    .stButton button {
        height: 3rem;
        font-size: 1.2rem;
        padding: 0.5rem 1rem;
        width: 100%;
    }
    
    /* Improve spacing for tablet */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 1000px;
    }
    
    /* Make radio buttons larger and more touch-friendly */
    .stRadio div[role="radiogroup"] label {
        font-size: 1.2rem;
        padding: 0.75rem;
    }
    
    /* Improve header for tablets */
    h1 {
        font-size: 2.5rem !important;
        text-align: center;
        margin-bottom: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Load environment variables
load_dotenv()

# Get API keys from environment variables with fallbacks to empty strings
default_gemini_api_key = os.getenv("GEMINI_API_KEY", "")
default_heygen_api_key = os.getenv("HEYGEN_API_KEY", "")
default_openai_api_key = os.getenv("ELEVENLABS_API_KEY", "")  # Using ELEVENLABS key as an alternative for OpenAI

# Use the environment variables directly
gemini_api_key = default_gemini_api_key
heygen_api_key = default_heygen_api_key
openai_api_key = default_openai_api_key

# Set the API keys to environment variables
if gemini_api_key:
    os.environ["GEMINI_API_KEY"] = gemini_api_key
if openai_api_key:
    os.environ["OPENAI_API_KEY"] = openai_api_key

# Define default settings without sidebar
avatar_id = "a09036af91434e2d8385dc887a7c9a95"
default_language = "English"
voice_id = "1985984feded457b9d013b4f6551ac94"
asr_provider = "Google Speech Recognition"

# Initialize Einstein bot
def initialize_einstein_bot():
    # Check for Gemini API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("Einstein is currently unavailable. Please try again later.")
        return None
    
    genai.configure(api_key=api_key)
    
    # Einstein's context with multilingual support
    einstein_context = """
You are AI Einstein, a friendly science buddy for kids! Your job is to make science super fun and easy to understand. 

How to Talk to Kids:
- Use simple words kids can understand
- Give short, exciting answers
- Make science sound like an amazing adventure
- Use fun examples and comparisons
- Be curious and playful
- Explain complex ideas in a way that makes kids go "Wow!"

Special Rules:
- Keep answers between 2-4 sentences
- Use kid-friendly language
- Get kids excited about learning
- Be patient and encouraging
- Always sound enthusiastic about science

Language Support:
- You are fluent in English and Korean
- Detect the language the user is using and respond in the same language
- If the user speaks in Korean, respond in Korean
- If the user speaks in English, respond in English
- Default to English if language is unclear

For Korean responses:
- Use polite, child-friendly Korean language (반말 대신 존댓말을 사용하세요)
- Keep explanations simple but engaging
- Use Korean examples that children would understand
    """
    
    # Initialize the model for chat
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Create or get chat session
    if "chat" not in st.session_state:
        st.session_state.chat = model.start_chat(history=[
            {
                "role": "user",
                "parts": [einstein_context]
            },
            {
                "role": "model",
                "parts": ["Greetings! I'm Einstein, your scientific guide to the wonders of the universe. What scientific curiosity shall we explore today?"]
            }
        ])
    
    return st.session_state.chat

# Language detection function
def detect_language(text):
    """Detect if text is in Korean or English"""
    try:
        lang = detect(text)
        if lang == 'ko':
            return 'Korean'
        else:
            return 'English'  # Default to English for all other languages
    except:
        return 'English'  # Default to English if detection fails

# HeyGen API Functions
def get_headers():
    """Get headers for HeyGen API requests"""
    return {
        "accept": "application/json",
        "content-type": "application/json",
        "x-api-key": heygen_api_key
    }

def create_session():
    """Create a new HeyGen streaming session"""
    url = "https://api.heygen.com/v1/streaming.new"
    
    payload = {
        "quality": "medium",
        "avatar_id": avatar_id,
        "voice": {
            "voice_id": voice_id,
            "rate": 1
        },
        "video_encoding": "VP8",
        "disable_idle_timeout": False,
        "version": "v2"
    }
    
    with st.spinner("Creating avatar session..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            session_data = response.json()
            
            if 'data' in session_data and 'session_id' in session_data['data']:
                return session_data['data']
            else:
                st.error(f"Failed to create session. Please try again later.")
                return None
                
        except Exception as e:
            st.error(f"Error creating session. Please try again later.")
            return None

def start_session(session_id):
    """Start a HeyGen streaming session"""
    url = "https://api.heygen.com/v1/streaming.start"
    
    payload = {
        "session_id": session_id
    }
    
    with st.spinner("Starting avatar session..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            start_data = response.json()
            
            if start_data.get('code') == 100 or start_data.get('message') == 'success':
                return True
            else:
                st.error(f"Failed to start session. Please try again later.")
                return False
        except Exception as e:
            st.error(f"Error starting session. Please try again later.")
            return False

def send_message_to_avatar(session_id, text):
    """Send a message for the avatar to speak"""
    url = "https://api.heygen.com/v1/streaming.task"
    
    # Simplified payload structure according to documentation
    payload = {
        "session_id": session_id,
        "text": text
    }
    
    with st.spinner("Generating avatar response..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            task_data = response.json()
            
            if task_data.get('code') == 100 and 'data' in task_data and 'task_id' in task_data['data']:
                # Wait for task completion to ensure synchronization
                task_id = task_data['data']['task_id']
                # Monitor task status until completion
                status = check_task_status(session_id, task_id)
                if status:
                    return task_data['data']
                else:
                    st.error("Task wasn't completed successfully")
                    return None
            else:
                st.error(f"Failed to send message. Please try again.")
                return None
        except Exception as e:
            st.error(f"Error sending message. Please try again.")
            return None

def check_task_status(session_id, task_id, max_attempts=10):
    """Check the status of a HeyGen streaming task"""
    url = "https://api.heygen.com/v1/streaming.task_status"
    
    payload = {
        "session_id": session_id,
        "task_id": task_id
    }
    
    attempts = 0
    while attempts < max_attempts:
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            status_data = response.json()
            
            if 'data' in status_data and 'status' in status_data['data']:
                status = status_data['data']['status']
                
                if status == 'complete':
                    return True
                elif status == 'failed':
                    return False
                else:
                    # Status is still 'processing', wait and retry
                    attempts += 1
                    time.sleep(1)
            else:
                return False
        except Exception as e:
            st.error(f"Error checking task status")
            return False
    
    # If we've reached max attempts without completion
    return False

def stop_session(session_id):
    """Stop a HeyGen streaming session"""
    url = "https://api.heygen.com/v1/streaming.stop"
    
    payload = {
        "session_id": session_id
    }
    
    with st.spinner("Stopping avatar session..."):
        try:
            response = requests.post(url, json=payload, headers=get_headers())
            response.raise_for_status()
            stop_data = response.json()
            
            if stop_data.get('code') == 100 or stop_data.get('message') == 'success':
                return True
            else:
                st.error(f"Failed to stop session. Please try again.")
                return False
        except Exception as e:
            st.error(f"Error stopping session. Please try again.")
            return False

def google_speech_recognition(audio_bytes, language_hint=None):
    """Process audio bytes using Google Speech Recognition"""
    recognizer = sr.Recognizer()
    
    # Alternative approach without using tempfile
    import io
    import wave
    
    try:
        # Convert audio bytes to AudioData directly
        # This assumes the audio is in the correct format (WAV)
        with io.BytesIO(audio_bytes) as audio_io:
            with wave.open(audio_io, 'rb') as wave_file:
                frame_rate = wave_file.getframerate()
                audio_data = sr.AudioData(
                    audio_bytes, 
                    frame_rate, 
                    wave_file.getsampwidth()
                )
            
        try:
            # Use language hint if provided
            if language_hint == 'Korean':
                text = recognizer.recognize_google(audio_data, language="ko-KR")
            else:
                text = recognizer.recognize_google(audio_data)
            return text
        except sr.UnknownValueError:
            return "Could not understand audio"
        except sr.RequestError:
            return "Error connecting to Google Speech Recognition service"
    except Exception as e:
        st.error(f"Error processing audio")
        return "Error processing audio file"

def whisper_asr(audio_bytes, api_key=None):
    """Recognize speech using OpenAI's Whisper API (automatically detects language)"""
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("Speech recognition is currently unavailable. Please try again.")
            return "Speech recognition service unavailable"
    
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio.flush()
        
        try:
            with open(temp_audio.name, "rb") as audio_file:
                files = {
                    "file": audio_file,
                    "model": (None, "whisper-1")
                }
                response = requests.post(url, headers=headers, files=files)
                
                if response.status_code == 200:
                    return response.json().get("text", "")
                else:
                    st.error(f"Speech recognition error. Please try voice input again.")
                    return "Error with speech recognition service"
        except Exception as e:
            st.error(f"Error processing audio. Please try again.")
            return "Error processing audio"

# Get Einstein's response to a user message
def get_einstein_response(chat, user_message):
    """Get Einstein's response to a user message"""
    try:
        # Get text response from Gemini
        response = chat.send_message(user_message)
        text_response = response.text
        
        return text_response
    except Exception as e:
        st.error(f"Error communicating with Einstein. Please try again.")
        # Return bilingual error message
        return "Forgive me, but I cannot answer at this moment. Perhaps we should try another question? / 죄송합니다만, 지금은 답변할 수 없습니다. 다른 질문을 해보시겠어요?"

# WebRTC player component with original dimensions
def create_webrtc_player(url, token):
    """Create a WebRTC player for HeyGen avatar with original dimensions"""
    webrtc_code = f"""
    <div id="video-container" style="width: 100%; height: 600px; background-color: #000; border-radius: 12px; overflow: hidden;">
        <video id="avatar-video" autoplay playsinline style="width: 100%; height: 100%; object-fit: contain;"></video>
    </div>
    
    <script>
    // First, load the LiveKit library
    function loadScript(src) {{
        return new Promise((resolve, reject) => {{
            const script = document.createElement('script');
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        }});
    }}
    
    async function setupLiveKit() {{
        try {{
            // Load the LiveKit client library first
            await loadScript('https://unpkg.com/livekit-client/dist/livekit-client.umd.js');
            
            const url = "{url}";
            const token = "{token}";
            
            // Access LiveKit through the global variable created by the UMD build
            const LivekitClient = window.LivekitClient;
            
            const room = new LivekitClient.Room({{
                adaptiveStream: true,
                dynacast: true
            }});
            
            room.on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {{
                if (track.kind === 'video') {{
                    const videoElement = document.getElementById('avatar-video');
                    track.attach(videoElement);
                    console.log('Video track attached');
                }}
                
                if (track.kind === 'audio') {{
                    track.attach();
                    console.log('Audio track attached');
                }}
            }});
            
            await room.connect(url, token);
            console.log('Connected to LiveKit room:', room.name);
            
        }} catch (error) {{
            console.error('Error connecting to LiveKit:', error);
            document.getElementById('video-container').innerHTML = '<div style="color: white; padding: 20px; text-align: center; font-size: 1.2rem;">Error connecting to video stream. Please try again.</div>';
        }}
    }}
    
    // Start the setup process
    setupLiveKit();
    </script>
    """
    
    # Render the HTML component
    return components.html(webrtc_code, height=640)

# Initialize session state variables
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "player_ready" not in st.session_state:
    st.session_state.player_ready = False
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "url" not in st.session_state:
    st.session_state.url = None
if "current_response" not in st.session_state:
    st.session_state.current_response = None
if "user_language" not in st.session_state:
    st.session_state.user_language = "English"  # Default language

# Check if streamlit-nightly's audio_input is available
has_audio_input = hasattr(st, 'audio_input')

# Main app layout - optimized for tablet
st.title("AI Einstein")

# Create a language toggle in the main interface - made more touch-friendly
app_language = st.radio(
    "Interface Language:", 
    ["🇺🇸 English", "🇰🇷 한국어"],
    horizontal=True,
    key="language_selector"
)

# Set interface language text based on selection
if app_language == "🇰🇷 한국어":
    listen_text = "듣고 있습니다..."
    start_button_text = "아바타 세션 시작"
    stop_button_text = "아바타 세션 중지"
    session_info_text = "아인슈타인 아바타를 생생하게 만나보세요!"
    audio_record_text = "🎤 녹음 시작"
    audio_stop_text = "⏹️ 녹음 중지"
    audio_not_available = "음성 입력이 현재 버전의 Streamlit에서 지원되지 않습니다."
else:
    listen_text = "Speak now..."
    start_button_text = "Start Avatar Session"
    stop_button_text = "Stop Avatar Session"
    session_info_text = "Start the avatar session to see Einstein come to life!"
    audio_record_text = "🎤 Start Recording"
    audio_stop_text = "⏹️ Stop Recording"
    audio_not_available = "Audio input is not supported in this version of Streamlit."

# Initialize the Einstein bot
chat = initialize_einstein_bot()

# Avatar session controls - optimized for tablet touch
col1, col2 = st.columns(2)

with col1:
    if st.button(start_button_text, disabled=(not heygen_api_key), key="start_button", use_container_width=True):
        if heygen_api_key:
            # Create and start a new session
            session_data = create_session()
            if session_data:
                st.session_state.session_id = session_data['session_id']
                st.session_state.access_token = session_data['access_token']
                st.session_state.url = session_data['url']
                
                if start_session(st.session_state.session_id):
                    st.session_state.player_ready = True
                    st.rerun()
        else:
            st.error("Avatar service is currently unavailable. Please try again later.")

with col2:
    if st.button(stop_button_text, disabled=not st.session_state.session_id, key="stop_button", use_container_width=True):
        if st.session_state.session_id:
            if stop_session(st.session_state.session_id):
                st.session_state.session_id = None
                st.session_state.player_ready = False
                st.rerun()

# Layout design for avatar - optimized for tablet
if st.session_state.player_ready:
    # Display the avatar in full width with original dimensions
    create_webrtc_player(st.session_state.url, st.session_state.access_token)
else:
    # When no session, show a placeholder and explanation
    st.info(session_info_text)
    
    # Placeholder avatar image when no session is active - centered for tablet
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image("https://upload.wikimedia.org/wikipedia/commons/3/3e/Einstein_1921_by_F_Schmutzer_-_restoration.jpg", use_container_width=True)

# Voice input section - optimized for tablet
if has_audio_input:
    # Using the new streamlit-nightly audio_input feature with larger button for tablet
    st.markdown(f"### {listen_text}")
    audio_bytes = st.audio_input(label=listen_text)
    
    if audio_bytes is not None:
        # Create a unique key for this audio input
        audio_id = str(uuid.uuid4())
        
        # Check if this audio has been processed before
        if "last_processed_audio" not in st.session_state:
            st.session_state.last_processed_audio = None
        
        # Process only if this is new audio data
        current_audio_hash = hash(audio_bytes.read())
        audio_bytes.seek(0)  # Reset file pointer after reading
        
        if current_audio_hash != st.session_state.last_processed_audio:
            with st.spinner("Processing audio..."):
                # Mark this audio as processed
                st.session_state.last_processed_audio = current_audio_hash
                
                # Process the recorded audio with selected ASR provider
                audio_data = audio_bytes.read()  # Get the bytes
                
                if asr_provider == "Google Speech Recognition":
                    user_input = google_speech_recognition(
                        audio_data, 
                        "Korean" if app_language == "🇰🇷 한국어" else "English"
                    )
                else:  # OpenAI Whisper
                    user_input = whisper_asr(audio_data)
                
                if user_input and user_input not in ["Could not understand audio", "Error processing audio", "Error with speech recognition service"]:
                    # Detect the language of the user input
                    detected_language = detect_language(user_input)
                    st.session_state.user_language = detected_language
                    
                    # We still add to chat history internally but don't display it
                    st.session_state.chat_history.append({
                        'role': 'user',
                        'content': user_input
                    })
                    
                    # Get Einstein's response
                    response_text = get_einstein_response(chat, user_input)
                    st.session_state.current_response = response_text
                    
                    # We still track responses internally but don't display them
                    st.session_state.chat_history.append({
                        'role': 'assistant',
                        'content': response_text
                    })
                    
                    # If avatar session is active, make the avatar speak
                    if st.session_state.player_ready and st.session_state.session_id:
                        task_data = send_message_to_avatar(st.session_state.session_id, response_text)
                    
                    # Refresh the display
                    st.rerun()
else:
    # Show message when audio_input is not available - more compact for tablet
    st.warning(audio_not_available)
    st.info("💡 Voice input requires Streamlit nightly: `pip install --upgrade streamlit-nightly`")

# Add a small footer with version info - useful for tablets
st.markdown("""
<div style="text-align: center; margin-top: 20px; opacity: 0.7; font-size: 0.8rem;">
    AI Einstein Avatar v1.0 - Voice-only interface
</div>
""", unsafe_allow_html=True)
