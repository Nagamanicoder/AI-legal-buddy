from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import json
import os
import requests
from datetime import datetime
import sqlite3
import google.generativeai as genai

# Create Flask app with current directory as static folder
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
SCHEMES_FILE = 'schemes.json'
DB_FILE = 'chat_history.db'

# Initialize Gemini
gemini_client = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_client = genai.GenerativeModel(GEMINI_MODEL)
        print("✅ Gemini API initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing Gemini: {str(e)}")
else:
    print("⚠️ GEMINI_API_KEY not set in environment variables")

print("=" * 60)
print("🔍 CHECKING ENVIRONMENT VARIABLES")
print("=" * 60)
print(f"GEMINI_API_KEY: {'✅ Yes (' + str(len(GEMINI_API_KEY)) + ' chars)' if GEMINI_API_KEY else '❌ No - NOT SET!'}")
print(f"GEMINI_MODEL: {GEMINI_MODEL}")

# Load schemes data
def load_schemes():
    try:
        with open(SCHEMES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {SCHEMES_FILE} not found!")
        return []

schemes_data = load_schemes()

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            scheme_id TEXT,
            message TEXT,
            response TEXT,
            sources TEXT,
            language TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Extract categories from schemes
def get_categories():
    categories = set()
    for scheme in schemes_data:
        if 'category' in scheme:
            categories.add(scheme['category'])
    return sorted(list(categories))

# Get scheme by ID
def get_scheme_by_id(scheme_id):
    for scheme in schemes_data:
        if scheme['id'] == scheme_id:
            return scheme
    return None

# Build context for RAG
def build_scheme_context(scheme_id=None, search_query=None):
    context = ""
    sources = []
    
    if scheme_id:
        scheme = get_scheme_by_id(scheme_id)
        if scheme:
            context = format_scheme_details(scheme)
            return context, [scheme.get('official_website', '')]
    
    # If no specific scheme, include relevant schemes
    relevant_schemes = schemes_data
    
    if search_query:
        search_lower = search_query.lower()
        relevant_schemes = [s for s in schemes_data if 
                          search_lower in s['name'].lower() or 
                          search_lower in s['description'].lower() or
                          search_lower in s.get('category', '').lower()]
    
    # Limit to top 3 schemes to avoid context overflow
    for scheme in relevant_schemes[:3]:
        context += format_scheme_details(scheme)
        sources.append(scheme.get('official_website', ''))
    
    return context, sources

def format_scheme_details(scheme):
    details = f"Scheme: {scheme['name']}\n"
    details += f"Category: {scheme.get('category', 'N/A')}\n"
    details += f"Description: {scheme['description']}\n"
    
    if 'eligibility' in scheme and scheme['eligibility']:
        details += "Eligibility: " + "; ".join(scheme['eligibility']) + "\n"
    
    if 'benefits' in scheme:
        details += f"Benefits: {scheme['benefits']}\n"
    
    if 'documents_required' in scheme and scheme['documents_required']:
        details += "Documents: " + ", ".join(scheme['documents_required']) + "\n"
    
    if 'how_to_apply' in scheme and scheme['how_to_apply']:
        details += "How to Apply: " + "; ".join(scheme['how_to_apply']) + "\n"
    
    if 'official_website' in scheme:
        details += f"Website: {scheme['official_website']}\n"
    
    if 'helpline' in scheme:
        details += f"Helpline: {scheme['helpline']}\n"
    
    details += "\n"
    return details

# Call Gemini API
def call_gemini(prompt, language='english'):
    if not gemini_client:
        print("❌ Gemini client not initialized")
        return None
    
    try:
        print(f"📤 Sending request to Gemini API...")
        print(f"Model: {GEMINI_MODEL}")
        print(f"Language: {language}")
        
        # Generate response
        response = gemini_client.generate_content(prompt)
        answer = response.text.strip()
        
        print(f"✅ Received response from Gemini ({len(answer)} characters)")
        
        # If Hindi is requested, translate the response
        if language == 'hindi' and answer:
            print("🔄 Translating to Hindi...")
            translation_prompt = f"Translate this to Hindi, keep scheme names in English:\n\n{answer}"
            
            translate_response = gemini_client.generate_content(translation_prompt)
            answer = translate_response.text.strip()
            print(f"✅ Translation complete ({len(answer)} characters)")
        
        return answer
        
    except Exception as e:
        print(f"❌ Error calling Gemini: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return None

# Save chat to database
def save_chat(user_id, scheme_id, message, response, sources, language):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO chat_history (user_id, scheme_id, message, response, sources, language)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, scheme_id, message, response, json.dumps(sources), language))
        conn.commit()
        conn.close()
        print("✅ Chat saved to database")
    except Exception as e:
        print(f"❌ Error saving chat: {str(e)}")

# ==================== API ROUTES ====================

@app.route('/api/schemes', methods=['GET'])
def get_schemes():
    category = request.args.get('category')
    search = request.args.get('search')
    
    filtered_schemes = schemes_data
    
    if category:
        filtered_schemes = [s for s in filtered_schemes if s.get('category') == category]
    
    if search:
        search_lower = search.lower()
        filtered_schemes = [s for s in filtered_schemes if 
                          search_lower in s['name'].lower() or 
                          search_lower in s['description'].lower()]
    
    return jsonify({
        'success': True,
        'schemes': filtered_schemes
    })

@app.route('/api/categories', methods=['GET'])
def get_categories_route():
    return jsonify({
        'success': True,
        'categories': get_categories()
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '').strip()
        language = data.get('language', 'english')
        user_id = data.get('user_id', 0)
        scheme_id = data.get('scheme_id')
        
        print(f"\n{'='*60}")
        print(f"📨 NEW CHAT REQUEST")
        print(f"{'='*60}")
        print(f"   Message: {message[:100]}...")
        print(f"   Language: {language}")
        print(f"   User ID: {user_id}")
        print(f"   Scheme ID: {scheme_id}")
        print(f"   Gemini Client: {'✅ Initialized' if gemini_client else '❌ NOT INITIALIZED'}")
        print(f"   API Key Set: {'✅ Yes' if GEMINI_API_KEY else '❌ No'}")
        print(f"{'='*60}")
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'}), 400
        
        if not gemini_client:
            error_msg = f'Gemini API not configured. API Key length: {len(GEMINI_API_KEY)}'
            print(f"❌ ERROR: {error_msg}")
            return jsonify({
                'success': False,
                'answer': 'Gemini API key not configured. Please set GEMINI_API_KEY environment variable.',
                'sources': [],
                'debug': error_msg
            })
        
        # Build context with RAG
        context, sources = build_scheme_context(scheme_id, message)
        print(f"📚 Context built ({len(context)} characters, {len(sources)} sources)")
        
        # Create prompt for Gemini
        if context:
            system_prompt = f"""You are AI Legal Buddy, an expert assistant for Indian Government Schemes. 

Based on these government schemes, answer the user's question clearly and concisely:

{context}

Question: {message}

Provide a helpful, accurate answer in a friendly tone. Keep it clear and concise."""
        else:
            system_prompt = f"""You are AI Legal Buddy, an expert assistant for Indian Government Schemes.

Question: {message}

Provide helpful information about Indian government schemes in a friendly, professional tone."""
        
        print(f"📝 Prompt length: {len(system_prompt)} characters")
        
        # Call Gemini
        answer = call_gemini(system_prompt, language)
        
        print(f"🤖 Gemini Response: {answer[:100] if answer else 'None'}...")
        
        if answer:
            # Save to database
            save_chat(user_id, scheme_id, message, answer, sources, language)
            
            response_data = {
                'success': True,
                'answer': answer,
                'sources': sources
            }
            print(f"✅ Sending success response to frontend")
            print(f"   Answer length: {len(answer)} chars")
            print(f"   Sources: {len(sources)} items")
            
            return jsonify(response_data)
        else:
            fallback_message = "I apologize, but I'm having trouble processing your request right now. Please try again." if language == 'english' else "मुझे खेद है, लेकिन मुझे आपके अनुरोध को संसाधित करने में समस्या हो रही है। कृपया पुनः प्रयास करें।"
            
            return jsonify({
                'success': False,
                'answer': fallback_message,
                'sources': []
            })
    
    except Exception as e:
        print(f"❌ Error in chat endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/chat-history/<int:user_id>', methods=['GET'])
def get_chat_history(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message, response, sources, timestamp 
        FROM chat_history 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 50
    ''', (user_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            'message': row[0],
            'response': row[1],
            'sources': json.loads(row[2]) if row[2] else [],
            'timestamp': row[3]
        })
    
    return jsonify({
        'success': True,
        'history': history
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify Gemini connection"""
    gemini_status = "connected" if gemini_client else "not configured"
    
    # Test Gemini API
    test_result = None
    if gemini_client:
        try:
            test_response = call_gemini("Say 'API working'", "english")
            test_result = "working" if test_response else "failed"
        except Exception as e:
            test_result = f"error: {str(e)}"
    
    return jsonify({
        'status': 'running',
        'ai_provider': 'Google Gemini',
        'gemini_status': gemini_status,
        'gemini_test': test_result,
        'gemini_model': GEMINI_MODEL,
        'schemes_loaded': len(schemes_data),
        'api_key_set': bool(GEMINI_API_KEY),
        'api_key_length': len(GEMINI_API_KEY) if GEMINI_API_KEY else 0
    })

# ==================== SERVE FRONTEND FILES ====================

@app.route('/')
def serve_index():
    """Serve the main HTML file"""
    try:
        return send_file('index.html')
    except:
        return "index.html not found", 404

@app.route('/styles.css')
def serve_css():
    """Serve CSS file"""
    try:
        return send_file('styles.css', mimetype='text/css')
    except:
        return "styles.css not found", 404

@app.route('/app.js')
def serve_js():
    """Serve JavaScript file"""
    try:
        return send_file('app.js', mimetype='application/javascript')
    except:
        return "app.js not found", 404

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    print(f"""
    ╔════════════════════════════════════════════╗
    ║   AI Legal Buddy - Flask Backend Server   ║
    ║          Powered by Google Gemini         ║
    ╚════════════════════════════════════════════╝
    
    🚀 Server starting on port {port}
    🤖 AI Provider: Google Gemini
    🔑 API Key: {'✅ Set (' + str(len(GEMINI_API_KEY)) + ' chars)' if GEMINI_API_KEY else '❌ Not set'}
    📊 Model: {GEMINI_MODEL}
    📋 Schemes loaded: {len(schemes_data)}
    
    📍 Frontend:
       - http://localhost:{port}
       - http://127.0.0.1:{port}
    
    📍 API Endpoints:
       - GET  /health
       - GET  /api/schemes
       - GET  /api/categories
       - POST /api/chat
       - GET  /api/chat-history/<user_id>
    
    📁 Files in directory:
       - index.html: {'✅' if os.path.exists('index.html') else '❌'}
       - styles.css: {'✅' if os.path.exists('styles.css') else '❌'}
       - app.js: {'✅' if os.path.exists('app.js') else '❌'}
       - schemes.json: {'✅' if os.path.exists('schemes.json') else '❌'}
    
    ⚠️  IMPORTANT: Set GEMINI_API_KEY environment variable!
    Get your key at: https://makersuite.google.com/app/apikey
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)