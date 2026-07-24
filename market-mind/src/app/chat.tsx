import React, { useState, useRef, useEffect } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Image, TextInput, KeyboardAvoidingView, Platform, ActivityIndicator, Keyboard } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { Audio } from 'expo-av';
import { sendChatMessage, sendVoiceMessage } from '../services/api';
import { LinearGradient } from 'expo-linear-gradient';

type Message = {
  id: string;
  type: 'user' | 'ai';
  text: string;
  isVoice?: boolean;
  time?: string;
  data?: any; // For rich UI components like profit summaries
};

export default function ChatScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { initialText, initialVoiceUri } = useLocalSearchParams();
  const scrollViewRef = useRef<ScrollView>(null);
  const [isKeyboardVisible, setKeyboardVisible] = useState(false);
  
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      type: 'ai',
      text: 'Hello, Mama Ada! I am Gemma. What did you sell or buy today?',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [userId] = useState('mama_ada');

  const addMessage = (msg: Message) => {
    setMessages(prev => [...prev, msg]);
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);
  };

  useEffect(() => {
    const showListener = Keyboard.addListener(
      Platform.OS === 'android' ? 'keyboardDidShow' : 'keyboardWillShow',
      () => setKeyboardVisible(true)
    );
    const hideListener = Keyboard.addListener(
      Platform.OS === 'android' ? 'keyboardDidHide' : 'keyboardWillHide',
      () => setKeyboardVisible(false)
    );

    // Process initial route parameters immediately on mount
    if (initialText && typeof initialText === 'string') {
      handleSendText(initialText, true);
    } else if (initialVoiceUri && typeof initialVoiceUri === 'string') {
      handleSendInitialVoice(initialVoiceUri);
    }

    return () => {
      showListener.remove();
      hideListener.remove();
    };
  }, [initialText, initialVoiceUri]);

  const handleSendInitialVoice = async (uri: string) => {
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    addMessage({ id: Date.now().toString(), type: 'user', text: "Voice Input", isVoice: true, time });
    setIsSending(true);
    try {
      const result = await sendVoiceMessage(uri, userId);
      if (result && result.reply) {
        addMessage({ 
          id: (Date.now() + 1).toString(), 
          type: 'ai', 
          text: result.reply, 
          data: result.data,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
      }
    } catch (error) {
      console.error('Error sending initial voice:', error);
    } finally {
      setIsSending(false);
    }
  };

  const handleSendText = async (textToSend: string = inputText, skipAddUserBubble: boolean = false) => {
    if (!textToSend.trim()) return;
    
    if (!skipAddUserBubble) {
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      addMessage({ id: Date.now().toString(), type: 'user', text: textToSend, time });
    } else {
      // If triggered from initial param, add the bubble but clear the URL param implicitly by doing it once
      const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      addMessage({ id: Date.now().toString(), type: 'user', text: textToSend, time });
    }
    
    setInputText('');
    
    try {
      setIsSending(true);
      const result = await sendChatMessage(textToSend, userId);
      if (result && result.reply) {
        addMessage({ 
          id: (Date.now() + 1).toString(), 
          type: 'ai', 
          text: result.reply, 
          data: result.data,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
      }
    } catch (err) {
      console.error('Error sending text:', err);
    } finally {
      setIsSending(false);
    }
  };

  const startRecording = async () => {
    if (isRecording || recording) return;
    try {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: newRecording } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
      setRecording(newRecording);
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to start recording', err);
    }
  };

  const stopRecording = async () => {
    if (!isRecording || !recording) return;
    const currentRecording = recording;
    setRecording(null);
    setIsRecording(false);
    
    try {
      await currentRecording.stopAndUnloadAsync();
      const uri = currentRecording.getURI();
      if (uri) {
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        addMessage({ id: Date.now().toString(), type: 'user', text: "Voice Input", isVoice: true, time });
        setIsSending(true);
        const result = await sendVoiceMessage(uri, userId);
        if (result && result.reply) {
          addMessage({ 
            id: (Date.now() + 1).toString(), 
            type: 'ai', 
            text: result.reply, 
            data: result.data,
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          });
        }
      }
    } catch (error) {
      console.error('Error stopping or sending recording:', error);
    } finally {
      setIsSending(false);
    }
  };

  const renderAiMessage = (msg: Message) => {
    const hasProfitData = msg.data && msg.data.net_profit !== undefined;
    
    return (
      <View style={styles.aiMessageContainer} key={msg.id}>
        <LinearGradient colors={['#F97316', '#EA580C']} style={styles.aiAvatar}>
          <Text style={styles.aiAvatarText}>G</Text>
        </LinearGradient>
        <LinearGradient colors={['rgba(30,41,59,0.9)', 'rgba(15,23,42,0.8)']} style={styles.aiBubble}>
          <Text style={styles.aiText}>{msg.text}</Text>
          
          {hasProfitData && (
            <View style={styles.richCard}>
              <Text style={styles.richCardTitle}>Your Profit</Text>
              <View style={styles.richCardRow}>
                <Text style={styles.richCardAmount}>₦{msg.data.net_profit.toLocaleString()}</Text>
                <View style={styles.richCardIcon}>
                  <Ionicons name="trending-up" size={20} color="#10B981" />
                </View>
              </View>
              
              <View style={styles.quickSummaryDivider} />
              <View style={styles.quickSummaryRow}>
                <View style={styles.summaryBox}>
                  <Text style={styles.summaryLabel}>SALES</Text>
                  <Text style={styles.summaryValueSale}>₦{msg.data.total_sales.toLocaleString()}</Text>
                </View>
                <View style={styles.summaryBox}>
                  <Text style={styles.summaryLabel}>EXPENSES</Text>
                  <Text style={styles.summaryValueExpense}>₦{msg.data.total_expenses.toLocaleString()}</Text>
                </View>
              </View>
            </View>
          )}
        </LinearGradient>
      </View>
    );
  };

  const renderUserMessage = (msg: Message) => {
    return (
      <View style={styles.userMessageContainer} key={msg.id}>
        <LinearGradient colors={['#10B981', '#059669']} style={styles.userBubble}>
          <Text style={styles.userText}>{msg.text}</Text>
          <Text style={styles.userTime}>
            {msg.isVoice ? '🎙️ Voice Input' : 'Text Input'} • {msg.time}
          </Text>
        </LinearGradient>
      </View>
    );
  };

  const suggestedPrompts = [
    "Wetin I spend pass?",
    "Which thing sell pass?",
    "What is my profit?"
  ];

  return (
    <KeyboardAvoidingView 
      style={{ flex: 1, backgroundColor: '#0F172A' }}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      keyboardVerticalOffset={0}
    >
      <LinearGradient
        colors={['#0F172A', '#1E293B', '#0F172A']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.container}
      >
        {/* Header */}
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <Image source={require('../../assets/images/profile.png')} style={styles.profilePic} />
            <Text style={styles.headerTitle}>Ask Gemma</Text>
          </View>
          <TouchableOpacity style={styles.historyButton} onPress={() => router.push('/history')}>
            <Ionicons name="time-outline" size={24} color="#38BDF8" />
          </TouchableOpacity>
        </View>

        {/* Chat Area */}
        <ScrollView 
          ref={scrollViewRef}
          style={styles.chatArea} 
          contentContainerStyle={styles.chatContent}
          showsVerticalScrollIndicator={false}
        >
          {messages.map(msg => msg.type === 'ai' ? renderAiMessage(msg) : renderUserMessage(msg))}
          {isSending && (
            <View style={styles.typingIndicator}>
              <ActivityIndicator size="small" color="#10B981" />
              <Text style={styles.typingText}>Gemma is typing...</Text>
            </View>
          )}
        </ScrollView>

        {/* Bottom Area */}
        <View style={[styles.bottomArea, { paddingBottom: isKeyboardVisible ? 16 : Math.max(insets.bottom, 16) + 10 }]}>
          {/* Suggested Prompts */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.promptsScroll} contentContainerStyle={{ paddingHorizontal: 16 }}>
            {suggestedPrompts.map((prompt, index) => (
              <TouchableOpacity key={index} style={styles.promptPill} onPress={() => handleSendText(prompt)}>
                <Text style={styles.promptText}>{prompt}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          <View style={styles.inputContainer}>
            <TextInput 
              style={styles.textInput}
              placeholder="Type a message..."
              placeholderTextColor="#64748B"
              value={inputText}
              onChangeText={setInputText}
              onSubmitEditing={() => handleSendText()}
            />
            {inputText.trim().length > 0 ? (
              <TouchableOpacity style={styles.sendButton} onPress={() => handleSendText()}>
                <Ionicons name="send" size={20} color="#FFFFFF" style={{ marginLeft: 3 }} />
              </TouchableOpacity>
            ) : (
              <TouchableOpacity 
                style={[styles.micButton, isRecording && styles.micButtonActive]}
                onPressIn={startRecording}
                onPressOut={stopRecording}
              >
                <LinearGradient colors={isRecording ? ['#EA580C', '#C2410C'] : ['#F97316', '#EA580C']} style={styles.micGradient}>
                  <Ionicons name="mic" size={24} color="#FFFFFF" />
                </LinearGradient>
              </TouchableOpacity>
            )}
          </View>
        </View>
      </LinearGradient>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 56,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.05)',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  profilePic: {
    width: 40,
    height: 40,
    borderRadius: 20,
    marginRight: 12,
    borderWidth: 1,
    borderColor: '#334155',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#F8FAFC',
    letterSpacing: 0.5,
  },
  historyButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#1E293B',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#334155',
  },
  chatArea: {
    flex: 1,
  },
  chatContent: {
    padding: 16,
    paddingBottom: 24,
  },
  userMessageContainer: {
    alignItems: 'flex-end',
    marginBottom: 16,
  },
  userBubble: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 20,
    borderTopRightRadius: 4,
    maxWidth: '80%',
    shadowColor: '#10B981',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 2,
  },
  userText: {
    color: '#FFFFFF',
    fontSize: 16,
    lineHeight: 22,
  },
  userTime: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: 11,
    marginTop: 6,
    textAlign: 'right',
  },
  aiMessageContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: 24,
  },
  aiAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
    shadowColor: '#F97316',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
  },
  aiAvatarText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 14,
  },
  aiBubble: {
    padding: 16,
    borderRadius: 20,
    borderTopLeftRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.05)',
    maxWidth: '85%',
  },
  aiText: {
    color: '#F8FAFC',
    fontSize: 16,
    lineHeight: 24,
    fontWeight: '500',
  },
  richCard: {
    marginTop: 16,
    backgroundColor: '#0F172A',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#334155',
  },
  richCardTitle: {
    fontSize: 13,
    color: '#94A3B8',
    fontWeight: '600',
    marginBottom: 4,
  },
  richCardRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  richCardAmount: {
    fontSize: 28,
    fontWeight: '800',
    color: '#34D399',
  },
  richCardIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.2)',
  },
  quickSummaryDivider: {
    height: 1,
    backgroundColor: '#334155',
    borderStyle: 'dashed',
    marginVertical: 16,
  },
  quickSummaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  summaryBox: {
    flex: 1,
    backgroundColor: '#1E293B',
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
    marginHorizontal: 4,
    alignItems: 'center',
  },
  summaryLabel: {
    fontSize: 11,
    color: '#94A3B8',
    fontWeight: '700',
    marginBottom: 4,
  },
  summaryValueSale: {
    fontSize: 14,
    fontWeight: '800',
    color: '#34D399',
  },
  summaryValueExpense: {
    fontSize: 14,
    fontWeight: '800',
    color: '#FB7185',
  },
  typingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    marginLeft: 40,
  },
  typingText: {
    marginLeft: 8,
    color: '#94A3B8',
    fontSize: 13,
    fontStyle: 'italic',
  },
  bottomArea: {
    paddingTop: 10,
    backgroundColor: 'rgba(15, 23, 42, 0.8)',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.05)',
  },
  promptsScroll: {
    marginBottom: 12,
  },
  promptPill: {
    backgroundColor: '#1E293B',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#334155',
    marginRight: 8,
  },
  promptText: {
    color: '#F8FAFC',
    fontWeight: '600',
    fontSize: 14,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
  },
  textInput: {
    flex: 1,
    backgroundColor: '#1E293B',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 24,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 16,
    marginRight: 12,
    color: '#F8FAFC',
  },
  sendButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#38BDF8',
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#38BDF8',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  micButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#F97316',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 6,
    overflow: 'hidden',
  },
  micGradient: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  micButtonActive: {
    transform: [{ scale: 1.1 }],
  }
});
