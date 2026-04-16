import React, { useState, useRef, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  FlatList, StyleSheet, KeyboardAvoidingView,
  Platform, ActivityIndicator, ScrollView,
} from 'react-native';
import { aiApi } from '../services/api';
import { ChatBubble } from '../components/ChatBubble';
import { ChatMessage } from '../types';

export function AIAssistantScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const listRef = useRef<FlatList>(null);

  useEffect(() => {
    aiApi.suggestedQuestions()
      .then((res) => setSuggestions(res.data.slice(0, 4)))
      .catch(() => {});
  }, []);

  async function send(text?: string) {
    const message = (text ?? input).trim();
    if (!message) return;

    const userMsg: ChatMessage = { role: 'user', content: message };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setSuggestions([]);
    setLoading(true);

    try {
      const res = await aiApi.chat(message, messages);
      const aiMsg: ChatMessage = { role: 'assistant', content: res.data.message };
      setMessages((prev) => [...prev, aiMsg]);
    } catch {
      const errMsg: ChatMessage = {
        role: 'assistant',
        content: 'Sorry, I could not reach the AI service. Please try again.',
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  }

  function scrollToEnd() {
    setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
  }

  useEffect(() => {
    if (messages.length > 0) scrollToEnd();
  }, [messages]);

  return (
    <KeyboardAvoidingView
      style={styles.screen}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={88}
    >
      {messages.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyIcon}>🤖</Text>
          <Text style={styles.emptyTitle}>AI Health Assistant</Text>
          <Text style={styles.emptySubtitle}>
            Ask me anything about your health data — I can identify correlations,
            explain trends, and give personalized recommendations.
          </Text>
          {suggestions.length > 0 && (
            <>
              <Text style={styles.suggestionsTitle}>Try asking:</Text>
              {suggestions.map((q) => (
                <TouchableOpacity key={q} style={styles.suggestion} onPress={() => send(q)}>
                  <Text style={styles.suggestionText}>{q}</Text>
                </TouchableOpacity>
              ))}
            </>
          )}
        </View>
      ) : (
        <FlatList
          ref={listRef}
          data={messages}
          keyExtractor={(_, i) => String(i)}
          renderItem={({ item }) => <ChatBubble message={item} />}
          contentContainerStyle={styles.messageList}
          onContentSizeChange={scrollToEnd}
        />
      )}

      {loading && (
        <View style={styles.typingIndicator}>
          <ActivityIndicator size="small" color="#0ea5e9" />
          <Text style={styles.typingText}>Thinking…</Text>
        </View>
      )}

      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          placeholder="Ask about your health data…"
          placeholderTextColor="#64748b"
          value={input}
          onChangeText={setInput}
          multiline
          returnKeyType="send"
          onSubmitEditing={() => send()}
        />
        <TouchableOpacity
          style={[styles.sendBtn, (!input.trim() || loading) && styles.sendBtnDisabled]}
          onPress={() => send()}
          disabled={!input.trim() || loading}
        >
          <Text style={styles.sendIcon}>↑</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#0f172a' },
  messageList: { padding: 16, paddingBottom: 8 },
  emptyState: {
    flex: 1, padding: 24, justifyContent: 'center', alignItems: 'center',
  },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyTitle: { color: '#e2e8f0', fontSize: 20, fontWeight: '700', marginBottom: 8 },
  emptySubtitle: {
    color: '#64748b', fontSize: 14, textAlign: 'center', lineHeight: 22, marginBottom: 24,
  },
  suggestionsTitle: { color: '#94a3b8', fontSize: 13, fontWeight: '600', marginBottom: 10, alignSelf: 'flex-start' },
  suggestion: {
    backgroundColor: '#1e293b', borderRadius: 10, padding: 12, marginBottom: 8,
    borderWidth: 1, borderColor: '#334155', width: '100%',
  },
  suggestionText: { color: '#e2e8f0', fontSize: 14 },
  typingIndicator: {
    flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 8, gap: 8,
  },
  typingText: { color: '#64748b', fontSize: 13 },
  inputRow: {
    flexDirection: 'row', alignItems: 'flex-end', padding: 12,
    borderTopWidth: 1, borderTopColor: '#1e293b', gap: 8,
  },
  input: {
    flex: 1, backgroundColor: '#1e293b', color: '#e2e8f0',
    borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10,
    fontSize: 15, maxHeight: 100, borderWidth: 1, borderColor: '#334155',
  },
  sendBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: '#0ea5e9', alignItems: 'center', justifyContent: 'center',
  },
  sendBtnDisabled: { backgroundColor: '#334155' },
  sendIcon: { color: '#fff', fontSize: 18, fontWeight: '700' },
});
