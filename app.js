// Global state
let currentUser = {
    id: 0,
    username: 'Guest'
};
let currentLanguage = 'english';
let selectedSchemeId = null;

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 App initialized');
    // Chat-only app: show chat interface by default
    document.getElementById('infoSection') && (document.getElementById('infoSection').style.display = 'none');
    const app = document.getElementById('appContainer');
    if (app) app.style.display = 'flex';
    document.getElementById('userGreeting').textContent = `Welcome! Ask about government schemes`;

    loadChatHistory();
    loadSchemes();
    loadCategories();
    setupEventListeners();
});

// Authentication removed — chat-only app

function showThinkingIndicator() {
    document.getElementById('thinkingIndicator').style.display = 'flex';
}

function hideThinkingIndicator() {
    document.getElementById('thinkingIndicator').style.display = 'none';
}

// Chat Functions
async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    addMessageToChat(message, 'user');
    input.value = '';
    
    showThinkingIndicator();
    
    console.log(`📤 Sending message with language: '${currentLanguage}'`);
    console.log(`📝 Message: ${message}`);
    console.log(`🆔 User ID: ${currentUser.id}`);
    console.log(`📋 Scheme ID: ${selectedSchemeId}`);
    
    try {
        const requestBody = {
            message,
            language: currentLanguage,
            user_id: currentUser.id,
            scheme_id: selectedSchemeId
        };
        
        console.log('📦 Request body:', requestBody);
        
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        console.log('📊 Response status:', response.status);
        
        const data = await response.json();
        console.log('📥 Response data:', data);
        
        hideThinkingIndicator();
        
        if (data.success) {
            console.log('✅ Success! Answer received');
            console.log('💬 Answer:', data.answer);
            console.log('🔗 Sources:', data.sources);
            addMessageToChat(data.answer, 'assistant', data.sources);
        } else {
            console.error('❌ API returned success=false');
            console.error('Error details:', data);
            const errorMsg = data.answer || data.error || 'Sorry, I could not generate a response. Please try again.';
            addMessageToChat(errorMsg, 'assistant');
        }
    } catch (error) {
        console.error('❌ Error in sendMessage:', error);
        hideThinkingIndicator();
        addMessageToChat('Error connecting to server. Please try again.', 'assistant');
    }
}

function formatMessage(message) {
    // Preserve bold markdown formatting with proper content
    message = message.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Preserve italic markdown formatting with proper content
    message = message.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    
    // Format lists with bullet points (preserve numbering)
    message = message.replace(/^- /gm, '• ');
    message = message.replace(/^\* /gm, '• ');
    
    // Break lines
    message = message.split('\n').join('<br>');
    
    return message;
}

function addMessageToChat(message, role, sources = []) {
    const chatMessages = document.getElementById('chatMessages');
    const welcome = chatMessages.querySelector('.welcome-message');
    if (welcome) welcome.remove();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message ' + role;
    
    const formattedMessage = formatMessage(message);
    let html = '<div class="message-content">' + formattedMessage;
    
    if (sources && sources.length > 0 && role === 'assistant') {
        html += '<div class="message-sources"><div class="sources-header">Official Resources</div><div class="sources-badges">';
        sources.forEach(source => {
            try {
                const url = new URL(source);
                const domain = url.hostname.replace('www.', '').toUpperCase();
                html += '<a href="' + source + '" target="_blank" class="source-badge">' + domain + '</a>';
            } catch (e) {
                console.warn('Invalid source URL:', source);
            }
        });
        html += '</div></div>';
    }
    
    html += '</div>';
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    console.log('💬 Message added to chat:', role, message.substring(0, 50) + '...');
}

function clearChat() {
    document.getElementById('chatMessages').innerHTML = '<div class="welcome-message"><h2>Welcome to AI Legal Buddy! </h2><p>Get instant answers about Indian government schemes</p><ul><li>Browse schemes by category</li><li>Ask questions in English or Hindi</li><li>Access official resources</li></ul></div>';
    console.log('🗑️ Chat cleared');
}

function setLanguage(lang) {
    currentLanguage = lang;
    console.log(`🌐 Language changed to: '${currentLanguage}'`);
    document.querySelectorAll('.lang-btn').forEach(btn => btn.classList.remove('active'));
    const langBtn = document.querySelector('[data-lang="' + lang + '"]');
    if (langBtn) {
        langBtn.classList.add('active');
    }
}

async function loadSchemes() {
    try {
        console.log('📋 Loading schemes...');
        const response = await fetch('/api/schemes');
        const data = await response.json();
        if (data.success) {
            console.log(`✅ Loaded ${data.schemes.length} schemes`);
            displaySchemes(data.schemes);
        }
    } catch (error) {
        console.error('❌ Error loading schemes:', error);
    }
}

async function loadCategories() {
    try {
        console.log('📁 Loading categories...');
        const response = await fetch('/api/categories');
        const data = await response.json();
        if (data.success) {
            console.log(`✅ Loaded ${data.categories.length} categories`);
            displayCategories(data.categories);
        }
    } catch (error) {
        console.error('❌ Error loading categories:', error);
    }
}

function displayCategories(categories) {
    const container = document.getElementById('categoriesList');
    container.innerHTML = '';
    categories.forEach(category => {
        const btn = document.createElement('button');
        btn.className = 'category-btn';
        btn.textContent = category;
        btn.onclick = (e) => filterSchemesByCategory(category, e);
        container.appendChild(btn);
    });
}

function displaySchemes(schemes) {
    const container = document.getElementById('schemesList');
    container.innerHTML = '';
    schemes.forEach(scheme => {
        const item = document.createElement('div');
        item.className = 'scheme-item';
        item.innerHTML = '<h4>' + scheme.name + '</h4><p>' + scheme.description.substring(0, 60) + '...</p>';
        item.onclick = () => selectScheme(scheme, item);
        container.appendChild(item);
    });
}

function selectScheme(scheme, element) {
    selectedSchemeId = scheme.id;
    console.log(`📌 Selected scheme: ${scheme.name} (ID: ${scheme.id})`);
    document.getElementById('selectedSchemeTitle').textContent = scheme.name;
    document.getElementById('selectedSchemeDesc').textContent = scheme.description;
    document.querySelectorAll('.scheme-item').forEach(item => item.classList.remove('active'));
    element.classList.add('active');
}

function filterSchemesByCategory(category, evt) {
    console.log(`🔍 Filtering by category: ${category}`);
    document.querySelectorAll('.category-btn').forEach(btn => btn.classList.remove('active'));
    if (evt && evt.currentTarget) evt.currentTarget.classList.add('active');
    loadFilteredSchemes(category);
}

async function loadFilteredSchemes(category) {
    try {
        const response = await fetch('/api/schemes?category=' + category);
        const data = await response.json();
        if (data.success) displaySchemes(data.schemes);
    } catch (error) {
        console.error('❌ Error loading filtered schemes:', error);
    }
}

async function loadChatHistory() {
    try {
        console.log('📜 Loading chat history...');
        const response = await fetch('/api/chat-history/0');
        const data = await response.json();
        if (data.success && data.history.length > 0) {
            console.log(`✅ Loaded ${data.history.length} chat messages`);
            data.history.reverse().forEach(item => {
                addMessageToChat(item.message, 'user');
                addMessageToChat(item.response, 'assistant', item.sources);
            });
        } else {
            console.log('📭 No chat history found');
        }
    } catch (error) {
        console.error('❌ Error loading chat history:', error);
    }
}

function setupEventListeners() {
    document.getElementById('searchInput').addEventListener('input', (e) => {
        const search = e.target.value;
        if (search) {
            fetch('/api/schemes?search=' + search)
                .then(r => r.json())
                .then(data => { if (data.success) displaySchemes(data.schemes); });
        } else {
            loadSchemes();
        }
    });
    
    document.getElementById('chatInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    console.log('✅ Event listeners setup complete');
}