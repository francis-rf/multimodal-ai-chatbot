// DOM Elements
const chatMessages = document.getElementById("chatMessages");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const modelSelect = document.getElementById("modelSelect");
const statusText = document.getElementById("statusText");
const welcomeScreen = document.getElementById("welcomeScreen");

// Sidebar buttons
const addImageGenBtn = document.getElementById("addImageGenBtn");
const addAudioBtn = document.getElementById("addAudioBtn");
const toggleTTSBtn = document.getElementById("toggleTTSBtn");
const imageUpload = document.getElementById("imageUpload");

// Input buttons
const plusButton = document.getElementById("plusButton");
const voiceButton = document.getElementById("voiceButton");

// State
let isRecording = false;
let selectedModel = "openai";
let ttsEnabled = false;
let currentAudio = null;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  setupEventListeners();
  
  // Configure marked
  if (window.marked) {
    marked.setOptions({
      breaks: true, // Enable GFM line breaks
      gfm: true,
      highlight: function(code, lang) {
        return code; // Can add highlighting lib here later if needed
      }
    });
  }
});

// Event Listeners
function setupEventListeners() {
  // Send message
  if (sendButton) {
    sendButton.addEventListener("click", sendMessage);
  }

  if (messageInput) {
    messageInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // Model selection
  if (modelSelect) {
    modelSelect.addEventListener("change", (e) => {
      selectedModel = e.target.value;
      updateStatus(`Switched to ${e.target.options[e.target.selectedIndex].text}`);
    });
  }

  // Sidebar actions
  if (imageUpload) {
    imageUpload.addEventListener("change", handleImageUpload);
  }

  if (addImageGenBtn) {
    addImageGenBtn.addEventListener("click", () => {
      const userPrompt = window.prompt("Enter image generation prompt:");
      if (userPrompt) {
        handleImageGeneration(userPrompt);
      }
    });
  }

  if (addAudioBtn) {
    addAudioBtn.addEventListener("click", toggleRecording);
  }

  if (toggleTTSBtn) {
    toggleTTSBtn.addEventListener("click", toggleTTS);
  }

  // Input buttons - Plus button for image upload
  if (plusButton && imageUpload) {
    plusButton.addEventListener("click", () => {
      console.log("Plus button clicked!");
      imageUpload.click();
    });
  } else {
    console.error("Plus button or imageUpload not found:", { plusButton, imageUpload });
  }

  if (voiceButton) {
    voiceButton.addEventListener("click", toggleRecording);
  }
}

// Send Message
async function sendMessage() {
  const message = messageInput.value.trim();

  if (message === "") {
    return;
  }

  // Hide welcome screen
  if (welcomeScreen) {
    welcomeScreen.style.display = "none";
  }

  // Add user message
  addMessage(message, "user");

  // Clear input
  messageInput.value = "";

  // Show typing indicator
  updateStatus("AI is thinking...");

  // Call the real API with streaming
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: message,
        model: selectedModel,
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Create a placeholder message with typing indicator
    const messageElement = addMessage("● ● ●", "bot", true);
    const textElement = messageElement.querySelector(".message-text");
    textElement.classList.add("typing-indicator");
    let fullResponse = "";
    let isFirstChunk = true;

    // Read the stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        updateStatus("Ready");
        // Speak the full response if TTS is enabled
        if (fullResponse && ttsEnabled) {
          speakText(fullResponse);
        }
        break;
      }

      // Decode the chunk
      const chunk = decoder.decode(value, { stream: true });

      // Split by lines and process each data event
      const lines = chunk.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6); // Remove 'data: ' prefix but keep spaces!

          if (data.trim() === '[DONE]') {
            updateStatus("Ready");
            break;
          }

          if (data.trim().startsWith('Error:')) {
            textElement.classList.remove("typing-indicator");
            textElement.textContent = data.trim();
            updateStatus("Error occurred");
            break;
          }

          // Skip empty data (but only trim for this check)
          if (!data.trim()) continue;

          // Remove typing indicator on first chunk
          if (isFirstChunk) {
            textElement.classList.remove("typing-indicator");
            textElement.textContent = "";
            isFirstChunk = false;
          }

          // Append the chunk to the message
          fullResponse += data;
          
          // Pre-process to fix common LLM markdown table issues (|| -> |)
          const processedResponse = fullResponse.replace(/\|\|/g, '|');

          if (window.marked) {
            textElement.innerHTML = marked.parse(processedResponse);
          } else {
             textElement.textContent = processedResponse;
          }

          // Auto-scroll to bottom during streaming
          chatMessages.scrollTop = chatMessages.scrollHeight;
        }
      }
    }
  } catch (error) {
    console.error("Error:", error);
    addMessage(
      "Sorry, I couldn't connect to the server. Please try again.",
      "bot",
    );
    updateStatus("Connection error");
  }
}

// Add Message to Chat
function addMessage(text, sender, isHtml = false) {
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${sender}-message`;

  const contentDiv = document.createElement("div");
  contentDiv.className = "message-content";

  const p = document.createElement("p");
  p.className = "message-text";

  if (isHtml) {
    p.innerHTML = text;
  } else if (window.marked) {
    p.innerHTML = marked.parse(text);
  } else {
    p.textContent = text;
  }

  contentDiv.appendChild(p);
  messageDiv.appendChild(contentDiv);
  chatMessages.appendChild(messageDiv);

  // Smooth scroll to bottom
  requestAnimationFrame(() => {
    chatMessages.scrollTo({
      top: chatMessages.scrollHeight,
      behavior: 'smooth'
    });
  });

  return messageDiv;
}

// Handle Image Upload
async function handleImageUpload(e) {
  const file = e.target.files[0];

  if (file) {
    updateStatus(`Processing image: ${file.name}`);

    // Hide welcome screen
    if (welcomeScreen) {
      welcomeScreen.style.display = "none";
    }

    const reader = new FileReader();
    reader.onload = async function (event) {
      // Add image to chat
      const messageDiv = document.createElement("div");
      messageDiv.className = "message user-message";

      const contentDiv = document.createElement("div");
      contentDiv.className = "message-content";

      const img = document.createElement("img");
      img.src = event.target.result;
      img.className = "message-image";
      img.alt = "Uploaded image";

      contentDiv.appendChild(img);
      messageDiv.appendChild(contentDiv);
      chatMessages.appendChild(messageDiv);

      // Smooth scroll to bottom
      requestAnimationFrame(() => {
        chatMessages.scrollTo({
          top: chatMessages.scrollHeight,
          behavior: 'smooth'
        });
      });

      // Send to vision API
      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("prompt", "Describe this image in detail");


        const response = await fetch("/api/vision/analyze", {
          method: "POST",
          body: formData,
        });

        const data = await response.json();

        if (response.ok) {
          addMessage(data.result, "bot");
          // Speak image analysis if TTS is enabled
          if (ttsEnabled) {
            speakText(data.result);
          }
          updateStatus("Ready");
        } else {
          addMessage(
            `Error analyzing image: ${data.detail || "Something went wrong"}`,
            "bot",
          );
          updateStatus("Error");
        }
      } catch (error) {
        console.error("Error:", error);
        addMessage("Sorry, I couldn't analyze the image.", "bot");
        updateStatus("Connection error");
      }
    };

    reader.readAsDataURL(file);
  }

  // Reset file input
  e.target.value = "";
}

// Handle Image Generation
async function handleImageGeneration(prompt) {
  if (!prompt || prompt.trim() === "") {
    return;
  }

  // Hide welcome screen
  if (welcomeScreen) {
    welcomeScreen.style.display = "none";
  }

  addMessage(`Generate image: ${prompt}`, "user");
  updateStatus("Generating image...");

  try {
    const response = await fetch("/api/image/generate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        prompt: prompt,
        steps: 20,
      }),
    });

    const data = await response.json();

    if (response.ok) {
      // Add generated image to chat
      const messageDiv = document.createElement("div");
      messageDiv.className = "message bot-message";

      const contentDiv = document.createElement("div");
      contentDiv.className = "message-content";

      const img = document.createElement("img");
      img.src = data.image_path;
      img.className = "message-image";
      img.alt = "Generated image";

      const p = document.createElement("p");
      p.textContent = data.message;

      contentDiv.appendChild(p);
      contentDiv.appendChild(img);
      messageDiv.appendChild(contentDiv);
      chatMessages.appendChild(messageDiv);

      // Smooth scroll to bottom
      requestAnimationFrame(() => {
        chatMessages.scrollTo({
          top: chatMessages.scrollHeight,
          behavior: 'smooth'
        });
      });

      updateStatus("Ready");
    } else {
      addMessage(
        `Error generating image: ${data.detail || "Something went wrong"}`,
        "bot",
      );
      updateStatus("Error");
    }
  } catch (error) {
    console.error("Error:", error);
    addMessage("Sorry, I couldn't generate the image.", "bot");
    updateStatus("Connection error");
  }
}

// Toggle Voice Recording
function toggleRecording() {
  if (!isRecording) {
    startRecording();
  } else {
    stopRecording();
  }
}

function startRecording() {
  if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
    alert("Speech recognition is not supported in your browser.");
    return;
  }

  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();

  recognition.lang = "en-US";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  recognition.onstart = function () {
    isRecording = true;
    voiceButton.style.color = "#ef4444";
    addAudioBtn.style.borderColor = "#ef4444";
    updateStatus("Listening...");
  };

  recognition.onresult = function (event) {
    const transcript = event.results[0][0].transcript;
    messageInput.value = transcript;
    updateStatus("Voice input captured");
  };

  recognition.onerror = function (event) {
    console.error("Speech recognition error:", event.error);
    updateStatus("Voice input error");
    isRecording = false;
    voiceButton.style.color = "";
    addAudioBtn.style.borderColor = "";
  };

  recognition.onend = function () {
    isRecording = false;
    voiceButton.style.color = "";
    addAudioBtn.style.borderColor = "";
    updateStatus("Ready");
  };

  recognition.start();
  window.currentRecognition = recognition;
}

function stopRecording() {
  if (window.currentRecognition) {
    window.currentRecognition.stop();
  }
}

// Update Status
function updateStatus(message) {
  statusText.textContent = message;
}

// Enhanced Markdown Parser
// Markdown parser replaced by marked.js
function parseMarkdown(text) {
  // Fallback if marked isn't loaded for some reason, though we check window.marked before calling
  return text; 
}

// Toggle Text-to-Speech
function toggleTTS() {
  ttsEnabled = !ttsEnabled;

  const textElement = toggleTTSBtn.querySelector('.action-text');
  if (ttsEnabled) {
    textElement.textContent = 'TTS: On';
    toggleTTSBtn.style.borderColor = '#10b981';
    updateStatus('Text-to-Speech enabled');
  } else {
    textElement.textContent = 'TTS: Off';
    toggleTTSBtn.style.borderColor = '';
    updateStatus('Text-to-Speech disabled');

    // Stop any currently playing audio
    if (currentAudio) {
      currentAudio.pause();
      currentAudio = null;
    }
  }
}

// Speak text using TTS
async function speakText(text) {
  if (!ttsEnabled) return;

  try {
    // Stop any currently playing audio
    if (currentAudio) {
      currentAudio.pause();
    }

    updateStatus('Generating speech...');

    const response = await fetch('/api/speech/synthesize', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text: text,
        voice: 'autumn'
      })
    });

    const data = await response.json();

    if (response.ok && data.audio) {
      // Create audio element from base64
      const audio = new Audio(`data:audio/wav;base64,${data.audio}`);
      currentAudio = audio;

      audio.onplay = () => updateStatus('Playing speech...');
      audio.onended = () => {
        updateStatus('Ready');
        currentAudio = null;
      };
      audio.onerror = () => {
        updateStatus('Speech playback error');
        currentAudio = null;
      };

      await audio.play();
    } else {
      console.error('TTS error:', data);
      updateStatus('TTS generation failed');
    }
  } catch (error) {
    console.error('Error generating speech:', error);
    updateStatus('TTS error');
  }
}
