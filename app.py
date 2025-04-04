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

# Set page configuration
st.set_page_config(page_title="AI Einstein Avatar", page_icon="🧠", layout="wide")

# Load environment variables first (before sidebar is rendered)
load_dotenv()

# Get API keys from environment variables with fallbacks to empty strings
default_gemini_api_key = os.getenv("GEMINI_API_KEY", "")
default_heygen_api_key = os.getenv("HEYGEN_API_KEY", "")
default_openai_api_key = os.getenv("ELEVENLABS_API_KEY", "")  # Using ELEVENLABS key as an alternative for OpenAI

# Sidebar configuration
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/3/3e/Einstein_1921_by_F_Schmutzer_-_restoration.jpg", width=250)
    st.markdown("## AI Einstein Configuration")
    
    # API Keys section
    st.markdown("### API Keys")
    
    # Gemini API key for Einstein bot - pre-filled from .env
    gemini_api_key = st.text_input("Gemini API Key", value=default_gemini_api_key, type="password",
                                help="Enter your Gemini API key or use the one from .env file")
    if gemini_api_key:
        os.environ["GEMINI_API_KEY"] = gemini_api_key
    
    # HeyGen API key for avatar - pre-filled from .env
    heygen_api_key = st.text_input("HeyGen API Key", value=default_heygen_api_key, type="password",
                               help="Enter your HeyGen API key or use the one from .env file")
    
    # Avatar configuration
    st.markdown("### Avatar Settings")
    avatar_id = st.text_input("Avatar ID", value="Ann_Therapist_public")
    
    # Language selection
    st.markdown("### Language Settings")
    default_language = st.selectbox(
        "Default Language",
        ["English", "Korean"],
        index=0
    )
    
    # Voice selection based on language
    if default_language == "English":
        voice_id = st.text_input("Voice ID", value="1bd001e7e50f421d891986aad5158bc8")
    else:  # Korean
        voice_id = st.text_input("Voice ID", value="1bd001e7e50f421d891986aad5158bc8")  # Replace with Korean voice ID
    
    # Voice recognition configuration
    st.markdown("### Speech Recognition")
    asr_provider = st.selectbox(
        "Speech Recognition Provider",
        ["Google Speech Recognition", "OpenAI Whisper"]
    )
    
    if asr_provider == "OpenAI Whisper":
        openai_api_key = st.text_input("OpenAI API Key", value=default_openai_api_key, type="password",
                                    help="Enter your OpenAI API key or use the one from .env file")
        if openai_api_key:
            os.environ["OPENAI_API_KEY"] = openai_api_key
    
    # Reload button
    if st.button("Reload with new API settings"):
        for key in ["chat", "session_id", "player_ready", "access_token", "url"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Initialize Einstein bot
def initialize_einstein_bot():
    # Check for Gemini API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        st.error("No Gemini API key found. Please set a Gemini API key in the sidebar.")
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
                st.error(f"Failed to create session: {session_data}")
                return None
                
        except Exception as e:
            st.error(f"Error creating session: {e}")
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
                st.error(f"Failed to start session: {start_data}")
                return False
        except Exception as e:
            st.error(f"Error starting session: {e}")
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
                st.error(f"Failed to send message: {task_data}")
                return None
        except Exception as e:
            st.error(f"Error sending message: {e}")
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
            st.error(f"Error checking task status: {e}")
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
                st.error(f"Failed to stop session: {stop_data}")
                return False
        except Exception as e:
            st.error(f"Error stopping session: {e}")
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
        # You might need to adjust this if you're working with different formats
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
        st.error(f"Error processing audio: {e}")
        return "Error processing audio file"

def whisper_asr(audio_bytes, api_key=None):
    """Recognize speech using OpenAI's Whisper API (automatically detects language)"""
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("No OpenAI API key found. Please set OPENAI_API_KEY in the sidebar.")
            return "No API key available for speech recognition"
    
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
                    st.error(f"Whisper ASR Error: {response.status_code} - {response.text}")
                    return "Error with speech recognition service"
        except Exception as e:
            st.error(f"Whisper ASR Exception: {str(e)}")
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
        st.error(f"Error: {e}")
        # Return bilingual error message
        return "Forgive me, but I cannot answer at this moment. Perhaps we should try another question? / 죄송합니다만, 지금은 답변할 수 없습니다. 다른 질문을 해보시겠어요?"

# WebRTC player component
def create_webrtc_player(url, token):
    """Create a WebRTC player for HeyGen avatar"""
    webrtc_code = f"""
    <div id="video-container" style="width: 100%; height: 480px; background-color: #000;">
        <video id="avatar-video" autoplay playsinline style="width: 100%; height: 100%;"></video>
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
            document.getElementById('video-container').innerHTML = '<div style="color: white; padding: 20px;">Error connecting to video stream. Please check console for details.</div>';
        }}
    }}
    
    // Start the setup process
    setupLiveKit();
    </script>
    """
    
    # Render the HTML component
    return components.html(webrtc_code, height=500)

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

# Main app layout
st.title("🧠 AI Einstein Avatar")

# Create a language toggle in the main interface
language_col1, language_col2 = st.columns([3, 1])
with language_col2:
    app_language = st.radio(
        "Interface Language:", 
        ["🇺🇸 English", "🇰🇷 한국어"],
        horizontal=True
    )

# Set interface language text based on selection
if app_language == "🇰🇷 한국어":
    welcome_text = "과학, 물리학, 철학, 그리고 우주의 신비에 대해 저에게 물어보세요!"
    voice_button_text = "🎤 음성으로 질문하기"
    listen_text = "듣고 있습니다..."
    text_input_label = "과학과 우주에 대해 아인슈타인에게 질문하세요:"
    send_button_text = "보내기"
    start_button_text = "아바타 세션 시작"
    stop_button_text = "아바타 세션 중지"
    session_info_text = "아인슈타인 아바타를 생생하게 만나보세요!"
    conversation_title = "대화"
    audio_record_text = "🎤 녹음 시작"
    audio_stop_text = "⏹️ 녹음 중지"
    file_upload_text = "오디오 파일 업로드"
    audio_not_available = "음성 입력이 현재 버전의 Streamlit에서 지원되지 않습니다. 텍스트로 질문해 주세요."
else:
    welcome_text = "Ask me about science, physics, philosophy, and the mysteries of the universe!"
    voice_button_text = "🎤 Record Voice Input"
    listen_text = "Speak now..."
    text_input_label = "Ask Einstein about science and the universe:"
    send_button_text = "Send"
    start_button_text = "Start Avatar Session"
    stop_button_text = "Stop Avatar Session"
    session_info_text = "Start the avatar session to see Einstein come to life!"
    conversation_title = "Conversation"
    audio_record_text = "🎤 Start Recording"
    audio_stop_text = "⏹️ Stop Recording"
    file_upload_text = "Upload Audio File"
    audio_not_available = "Audio input is not supported in this version of Streamlit. Please ask your questions using text."

# Initialize the Einstein bot
chat = initialize_einstein_bot()

# Avatar session controls
col1, col2 = st.columns(2)

with col1:
    # Check if HeyGen API key is available (either from .env or user input)
    if st.button(start_button_text, disabled=(not heygen_api_key)):
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
            st.error("HeyGen API key is required to start the avatar")

with col2:
    if st.button(stop_button_text, disabled=not st.session_state.session_id):
        if st.session_state.session_id:
            if stop_session(st.session_state.session_id):
                st.session_state.session_id = None
                st.session_state.player_ready = False
                st.rerun()

# Layout design with columns for avatar and chat
col1, col2 = st.columns([2, 1])

with col1:
    # Display the avatar if session is ready
    if st.session_state.player_ready:
        st.subheader("Einstein Avatar")
        create_webrtc_player(st.session_state.url, st.session_state.access_token)
    else:
        st.info(session_info_text)
        
        # Placeholder avatar image when no session is active
        st.image("https://upload.wikimedia.org/wikipedia/commons/3/3e/Einstein_1921_by_F_Schmutzer_-_restoration.jpg", width=400)

with col2:
    # Chat history and interface
    st.subheader(conversation_title)
    
    # Create a container for chat history
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.chat_history:
            if message['role'] == 'user':
                if app_language == "🇰🇷 한국어":
                    st.markdown(f"**나:** {message['content']}")
                else:
                    st.markdown(f"**You:** {message['content']}")
            else:
                if app_language == "🇰🇷 한국어":
                    st.markdown(f"**아인슈타인:** {message['content']}")
                else:
                    st.markdown(f"**Einstein:** {message['content']}")
    
    # Audio input options with file uploader as fallback
    # Check if we have st.audio_input available (from streamlit-nightly)
    audio_tab, text_tab, file_tab = st.tabs(["Voice Input", "Text Input", "File Upload"])
    
with audio_tab:
    if has_audio_input:
        # Using the new streamlit-nightly audio_input feature
        st.write(listen_text)
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
                        
                        # Add user message to chat history
                        st.session_state.chat_history.append({
                            'role': 'user',
                            'content': user_input
                        })
                        
                        # Get Einstein's response
                        response_text = get_einstein_response(chat, user_input)
                        st.session_state.current_response = response_text
                        
                        # Add Einstein's response to chat history
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
            # Show message when audio_input is not available
            st.warning(audio_not_available)
            
            # Suggest file upload as alternative
            st.write("You can use the 'File Upload' tab to upload audio recordings instead.")
    
    with text_tab:
        # Text input
        with st.form(key="message_form", clear_on_submit=True):
            user_input = st.text_input(text_input_label)
            submit = st.form_submit_button(send_button_text)
            
            if submit and user_input:
                # Detect the language of the user input
                detected_language = detect_language(user_input)
                st.session_state.user_language = detected_language
                
                # Add user message to chat history
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': user_input
                })
                
                # Get Einstein's response
                response_text = get_einstein_response(chat, user_input)
                st.session_state.current_response = response_text
                
                # Add Einstein's response to chat history
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': response_text
                })
                
                # If avatar session is active, make the avatar speak
                if st.session_state.player_ready and st.session_state.session_id:
                    with st.spinner("Making Einstein speak..."):
                        task_data = send_message_to_avatar(st.session_state.session_id, response_text)
                
                # Refresh the display
                st.rerun()
                
    with file_tab:
        # File upload option as a fallback
        uploaded_file = st.file_uploader(file_upload_text, type=['wav', 'mp3'])
        
        if uploaded_file is not None:
            audio_bytes = uploaded_file.read()
            
            st.audio(audio_bytes, format="audio/wav")
            
            if st.button("Process Audio"):
                with st.spinner("Processing audio file..."):
                    # Process the uploaded audio with selected ASR provider
                    if asr_provider == "Google Speech Recognition":
                        user_input = google_speech_recognition(
                            audio_bytes, 
                            "Korean" if app_language == "🇰🇷 한국어" else "English"
                        )
                    else:  # OpenAI Whisper
                        user_input = whisper_asr(audio_bytes)
                    
                    if user_input and user_input not in ["Could not understand audio", "Error processing audio", "Error with speech recognition service"]:
                        st.success(f"Transcription: {user_input}")
                        
                        # Detect the language of the user input
                        detected_language = detect_language(user_input)
                        st.session_state.user_language = detected_language
                        
                        # Add user message to chat history
                        st.session_state.chat_history.append({
                            'role': 'user',
                            'content': user_input
                        })
                        
                        # Get Einstein's response
                        response_text = get_einstein_response(chat, user_input)
                        st.session_state.current_response = response_text
                        
                        # Add Einstein's response to chat history
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
                        st.error(f"Failed to process audio: {user_input}")

# Add a footer with version information and upgrade instructions
st.markdown("---")
if not has_audio_input:
    st.info(
        "💡 For better voice input support, upgrade to Streamlit nightly: "
        "`pip install --upgrade streamlit-nightly`"
    )
