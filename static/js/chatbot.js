document.addEventListener('DOMContentLoaded', function() {
    const chatToggle = document.createElement('button');
    chatToggle.className = 'chat-toggle';
    chatToggle.innerHTML = '<i class="fas fa-comments"></i>';
    document.body.appendChild(chatToggle);

    const chatContainer = document.createElement('div');
    chatContainer.className = 'chat-container';
    chatContainer.innerHTML = `
        <div class="chat-header">
            <h3>Smart Ticket Assistant</h3>
            <button class="close-chat"><i class="fas fa-times"></i></button>
        </div>
        <div class="chat-messages"></div>
        <div class="chat-input">
            <input type="text" placeholder="Ask me anything about tickets...">
            <button><i class="fas fa-paper-plane"></i></button>
        </div>
    `;
    document.body.appendChild(chatContainer);

    const messagesContainer = chatContainer.querySelector('.chat-messages');
    const chatInput = chatContainer.querySelector('input');
    const sendButton = chatContainer.querySelector('.chat-input button');
    const closeButton = chatContainer.querySelector('.close-chat');

    function toggleChat() {
        chatContainer.style.display = chatContainer.style.display === 'flex' ? 'none' : 'flex';
        if (chatContainer.style.display === 'flex') {
            chatInput.focus();
        }
    }

    function addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
        messageDiv.textContent = message;
        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        addMessage(message, true);
        chatInput.value = '';
        chatInput.disabled = true;
        sendButton.disabled = true;

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            addMessage(data.response);
        } catch (error) {
            addMessage('Sorry, I encountered an error. Please try again.');
        } finally {
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.focus();
        }
    }

    chatToggle.addEventListener('click', toggleChat);
    closeButton.addEventListener('click', toggleChat);
    
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Add initial welcome message
    addMessage('Hello! I\'m your Smart Ticket Assistant. How can I help you today?');
});
