import sqlite3
from typing import List, Dict, Optional

class ConversationDatabase:
    def __init__(self, db_path: str = "data/databases/conversations.db"):
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id INTEGER,
                    message_id INTEGER,
                    user_input TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (conversation_id, message_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_count (
                    id INTEGER PRIMARY KEY,
                    count INTEGER NOT NULL,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT OR IGNORE INTO conversation_count (id, count)
                VALUES (1, 0)
            ''')
            conn.commit()

    def start_new_conversation(self) -> int:
        """Start a new conversation and return the conversation ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COALESCE(MAX(conversation_id), 0) + 1 FROM conversations')
            new_conversation_id = cursor.fetchone()[0]
            conn.commit()
            return new_conversation_id

    def save_conversation(self, user_input: str, ai_response: str, conv_count_threshold: int, new_conv: Optional[bool] = False) -> (int, int):
        """Save a conversation to the database and return the conversation ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if new_conv:
                conversation_id = self.start_new_conversation()
            else:
                cursor.execute('''
                SELECT COALESCE(MAX(conversation_id), 1) 
                FROM conversations 
                ''')
                conversation_id = cursor.fetchone()[0]
                
            cursor.execute('''
                SELECT COALESCE(MAX(message_id), 0) + 1 
                FROM conversations 
                WHERE conversation_id = ?
            ''', (conversation_id,))
            message_id = cursor.fetchone()[0]
            
            cursor.execute('''
                INSERT INTO conversations (conversation_id, message_id, user_input, ai_response)
                VALUES (?, ?, ?, ?)
            ''', (conversation_id, message_id, user_input, ai_response))
            conn.commit()

            self.increment_conversation_count()
            processed_conversations_count = self.get_conversation_count()
            
            if(processed_conversations_count >= conv_count_threshold):
                self.reset_conversation_count()

            return processed_conversations_count

    def get_messages_from_conversation(self, conversation_id: int, limit: int = 100) -> List[Dict]:
        """Get conversations, optionally filtered by conversation ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT conversation_id, user_input, ai_response, timestamp
                FROM conversations
                WHERE conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                ''', (conversation_id, limit))
            
            rows = cursor.fetchall()
            return [{
                "conversation_id": row[0],
                "user_input": row[1],
                "ai_response": row[2],
                "timestamp": row[3]
            } for row in rows]
    
    def get_message_by_id(self, conversation_id: int, message_id: int) -> Optional[Dict]:
        """Get a specific conversation by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT conversation_id, message_id, user_input, ai_response, timestamp
                FROM conversations
                WHERE conversation_id = ? AND message_id = ?
            ''', (conversation_id, message_id))
            row = cursor.fetchone()
            if row:
                return {
                    "conversation_id": row[0],
                    "message_id": row[1],
                    "user_input": row[2],
                    "ai_response": row[3],
                    "timestamp": row[4]
                }
            return None

    def get_conversation_count(self) -> int:
        """Get the current conversation count."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT count FROM conversation_count WHERE id = 1
            ''')
            result = cursor.fetchone()
            return result[0] if result else 0

    def increment_conversation_count(self):
        """Increment the conversation count and return the new value."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE conversation_count 
                SET count = count + 1, 
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
            ''')
            conn.commit()
    
    def reset_conversation_count(self):
        """Reset the conversation count."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE conversation_count 
                SET count = 0, 
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
            ''')
            conn.commit()
