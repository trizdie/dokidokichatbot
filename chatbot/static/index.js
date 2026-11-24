/**
 * DDLC Chatbot — Frontend logic
 *
 * Dialogue flow (matches original game):
 *   1. Name popup → user enters name → character select
 *   2. User selects character → chat opens, greeting shows with typewriter
 *   3. CTC "OK" appears → user clicks to dismiss
 *   4. User types message → message appears in textbox with typewriter
 *   5. CTC "OK" appears → user clicks to skip/advance
 *   6. Bot responds → bot reply appears in textbox with typewriter
 *   7. CTC "OK" appears → user clicks to continue
 *   8. Cycle repeats (step 4)
 *
 * Typewriter: text appears character by character (~30ms/char).
 * Click textbox or CTC button to skip typewriter instantly.
 * CTC button pulses to indicate it's clickable.
 */

// ===================== DOM References =====================
const namePopupOverlay = document.getElementById('name-popup-overlay');
const nameInput        = document.getElementById('name-input');
const nameOkBtn        = document.getElementById('name-ok-btn');
const characterSelect  = document.getElementById('character-select');
const chatContainer    = document.getElementById('chat-container');
const chatLogPanel     = document.getElementById('chat-log-panel');
const chatLog          = document.getElementById('chat-log');
const logContent       = document.getElementById('log-content');
const ddlcTextbox      = document.getElementById('ddlc-textbox');
const ddlcNamebox      = document.getElementById('ddlc-namebox');
const ddlcDialogue     = document.getElementById('ddlc-dialogue');
const ctcContainer     = document.getElementById('ctc-container');
const ctcButton        = document.getElementById('ctc-button');
const userInput        = document.getElementById('user-input');
const sendButton       = document.getElementById('send-button');
const buttonIcon       = document.getElementById('button-icon');
const inputArea        = document.getElementById('input-area');

// Quick-menu buttons
const logBtn   = document.getElementById('log-btn');
const clearBtn = document.getElementById('clear-btn');
const backBtn  = document.getElementById('back-btn');

// Character select
const charBtns      = document.querySelectorAll('.character-btn');
const selectBackBtn = document.getElementById('select-back-btn');
const logCloseBtn   = document.getElementById('log-close-btn');

// ===================== State =====================
let playerName        = 'You';
let selectedCharacter = null;
let messageHistory    = [];
let isTyping          = false;
let typewriterTimer   = null;
let skipRequested     = false;
let waitingForCTC     = false;
let dialoguePhase     = 'idle'; // 'idle' | 'user-typing' | 'user-ctc' | 'bot-typing' | 'bot-ctc'

// ===================== Character Data =====================
const CHARACTERS = {
  sayori:  { name: 'Sayori',  greeting: 'Hi there! Ehehe~ I\'m so glad you came to talk to me!' },
  natsuki: { name: 'Natsuki', greeting: 'H-hey! Don\'t think I\'m happy to see you or anything...' },
  yuri:    { name: 'Yuri',    greeting: 'Oh... hello. I\'m happy you decided to talk with me.' },
  monika:  { name: 'Monika',  greeting: 'Hey there! I\'m so happy you chose to talk to me. Just Monika~' },
};

// ===================== Name Popup =====================
function showNamePopup() {
  namePopupOverlay.style.display = 'flex';
  nameInput.value = '';
  nameInput.focus();
}

function hideNamePopup() {
  namePopupOverlay.style.display = 'none';
  characterSelect.style.display = 'flex';
}

nameOkBtn.addEventListener('click', () => {
  const name = nameInput.value.trim();
  if (name === '') {
    nameInput.focus();
    return;
  }
  playerName = name;
  hideNamePopup();
});

nameInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') nameOkBtn.click();
});

// ===================== Character Selection =====================
charBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const charKey = btn.getAttribute('data-char');
    selectedCharacter = charKey;
    const charData = CHARACTERS[charKey];

    // Switch views
    characterSelect.style.display = 'none';
    chatContainer.style.display = 'flex';

    // Clear previous chat
    chatLog.innerHTML = '';
    messageHistory = [];
    dialoguePhase = 'idle';

    // Show greeting in DDLC textbox with typewriter
    dialoguePhase = 'bot-typing';
    showDDLCDialogue(charData.name, charData.greeting, () => {
      addMessageToLog(charData.name, charData.greeting);
      dialoguePhase = 'bot-ctc';
    });
  });
});

selectBackBtn.addEventListener('click', () => {
  characterSelect.style.display = 'none';
  showNamePopup();
});

// ===================== Send Message =====================
sendButton.addEventListener('click', sendMessage);
userInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendMessage();
});

function sendMessage() {
  const message = userInput.value.trim();
  if (message === '' || isTyping || waitingForCTC || dialoguePhase !== 'idle') return;

  userInput.value = '';

  // Show user message in DDLC textbox with typewriter
  dialoguePhase = 'user-typing';
  showDDLCDialogue(playerName, message, () => {
    addMessageToLog(playerName, message);
    dialoguePhase = 'user-ctc';
  });
}

function onUserCTCClicked() {
  // User clicked CTC after their own message — now get bot reply
  dialoguePhase = 'bot-typing';
  showLoading();

  callChatAPI(messageHistory[messageHistory.length - 1].text).then(reply => {
    hideLoading();
    const charName = CHARACTERS[selectedCharacter]?.name || 'Bot';

    showDDLCDialogue(charName, reply, () => {
      addMessageToLog(charName, reply);
      dialoguePhase = 'bot-ctc';
    });
  }).catch(err => {
    hideLoading();
    showDDLCDialogue('Error', 'Something went wrong. Please try again.', () => {
      dialoguePhase = 'bot-ctc';
    });
  });
}

// ===================== API Call =====================
async function callChatAPI(message) {
  const body = {
    messages: [
      { role: 'system', content: `You are ${CHARACTERS[selectedCharacter]?.name || 'Monika'} from Doki Doki Literature Club. Stay in character. Be friendly, cute, and sometimes witty. Keep responses under 2-3 sentences unless asked for more.` },
      ...messageHistory.map(m => ({
        role: m.sender === playerName ? 'user' : 'assistant',
        content: m.text
      })),
      { role: 'user', content: message }
    ]
  };

  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body)
  });

  const data = await response.json();

  if (data.choices && data.choices[0]) {
    return data.choices[0].message.content;
  }
  throw new Error(data.error || 'No response from API');
}

// ===================== DDLC Dialogue (Typewriter) =====================
function showDDLCDialogue(name, text, onComplete) {
  stopTypewriter();
  skipRequested = false;
  waitingForCTC = false;

  // Show textbox, hide CTC
  ddlcTextbox.style.display = 'block';
  ctcContainer.style.display = 'none';

  // Set name in namebox
  ddlcNamebox.textContent = name;
  ddlcDialogue.innerHTML = '';

  // Typewriter effect — ~30ms per character like DDLC
  isTyping = true;
  let charIndex = 0;

  typewriterTimer = setInterval(() => {
    if (skipRequested) {
      // Skip to end — show full text immediately
      stopTypewriter();
      ddlcDialogue.innerHTML = escapeHTML(text);
      isTyping = false;
      showCTC(onComplete);
      return;
    }

    if (charIndex < text.length) {
      ddlcDialogue.innerHTML = escapeHTML(text.substring(0, charIndex + 1));
      charIndex++;
    } else {
      // Typewriter finished — show CTC
      stopTypewriter();
      isTyping = false;
      showCTC(onComplete);
    }
  }, 30);
}

function stopTypewriter() {
  if (typewriterTimer) {
    clearInterval(typewriterTimer);
    typewriterTimer = null;
  }
}

function showCTC(onComplete) {
  waitingForCTC = true;
  ctcContainer.style.display = 'flex';

  // Clone CTC button to remove old event listeners
  const oldBtn = document.getElementById('ctc-button');
  const newCtcBtn = oldBtn.cloneNode(true);
  oldBtn.parentNode.replaceChild(newCtcBtn, oldBtn);

  newCtcBtn.addEventListener('click', () => {
    waitingForCTC = false;
    ctcContainer.style.display = 'none';
    skipRequested = false;

    if (onComplete) onComplete();

    // After CTC, check if we need to transition dialogue phases
    if (dialoguePhase === 'user-ctc') {
      onUserCTCClicked();
    }
    // If 'bot-ctc', we just go back to 'idle' (user can type again)
    if (dialoguePhase === 'bot-ctc') {
      dialoguePhase = 'idle';
    }
  });
}

// Clicking textbox advances/skips
ddlcTextbox.addEventListener('click', () => {
  if (isTyping) {
    skipRequested = true;
  } else if (waitingForCTC) {
    const btn = document.getElementById('ctc-button');
    if (btn) btn.click();
  }
});

// ===================== Chat Log =====================
function addMessageToLog(sender, text) {
  messageHistory.push({ sender, text });

  const msgDiv = document.createElement('div');
  msgDiv.classList.add('chat-message');
  msgDiv.classList.add(sender === playerName ? 'user-message' : 'bot-message');

  const senderSpan = document.createElement('div');
  senderSpan.classList.add('msg-sender');
  senderSpan.textContent = sender;

  const bubbleDiv = document.createElement('div');
  bubbleDiv.classList.add('msg-bubble');
  bubbleDiv.textContent = text;

  msgDiv.appendChild(senderSpan);
  msgDiv.appendChild(bubbleDiv);
  chatLog.appendChild(msgDiv);

  chatLog.scrollTop = chatLog.scrollHeight;
}

// ===================== Loading Indicator =====================
function showLoading() {
  const loader = document.createElement('div');
  loader.classList.add('chat-message', 'bot-message');
  loader.id = 'loading-indicator';

  const senderSpan = document.createElement('div');
  senderSpan.classList.add('msg-sender');
  senderSpan.textContent = CHARACTERS[selectedCharacter]?.name || 'Bot';

  const dotsDiv = document.createElement('div');
  dotsDiv.classList.add('msg-bubble');
  dotsDiv.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';

  loader.appendChild(senderSpan);
  loader.appendChild(dotsDiv);
  chatLog.appendChild(loader);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function hideLoading() {
  const loader = document.getElementById('loading-indicator');
  if (loader) loader.remove();
}

// ===================== Quick Menu =====================
logBtn.addEventListener('click', () => {
  chatContainer.style.display = 'none';
  chatLogPanel.style.display = 'flex';

  logContent.innerHTML = '';
  messageHistory.forEach(entry => {
    const div = document.createElement('div');
    div.classList.add('log-entry');

    const name = document.createElement('div');
    name.classList.add('log-name');
    name.textContent = entry.sender;

    const text = document.createElement('div');
    text.classList.add('log-text');
    text.textContent = entry.text;

    div.appendChild(name);
    div.appendChild(text);
    logContent.appendChild(div);
  });
});

logCloseBtn.addEventListener('click', () => {
  chatLogPanel.style.display = 'none';
  chatContainer.style.display = 'flex';
});

clearBtn.addEventListener('click', () => {
  chatLog.innerHTML = '';
  messageHistory = [];
  ddlcTextbox.style.display = 'none';
  ctcContainer.style.display = 'none';
  isTyping = false;
  waitingForCTC = false;
  dialoguePhase = 'idle';
  stopTypewriter();

  const charData = CHARACTERS[selectedCharacter];
  if (charData) {
    dialoguePhase = 'bot-typing';
    showDDLCDialogue(charData.name, charData.greeting, () => {
      addMessageToLog(charData.name, charData.greeting);
      dialoguePhase = 'bot-ctc';
    });
  }
});

backBtn.addEventListener('click', () => {
  stopTypewriter();
  isTyping = false;
  waitingForCTC = false;
  dialoguePhase = 'idle';
  ddlcTextbox.style.display = 'none';
  ctcContainer.style.display = 'none';
  chatContainer.style.display = 'none';
  chatLogPanel.style.display = 'none';
  characterSelect.style.display = 'flex';
  selectedCharacter = null;
  messageHistory = [];
  chatLog.innerHTML = '';
});

// ===================== Helpers =====================
function escapeHTML(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ===================== Init =====================
// Show name popup on load
showNamePopup();
