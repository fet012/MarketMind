import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, TextInput, KeyboardAvoidingView, Platform, ActivityIndicator } from 'react-native';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Audio } from 'expo-av';
import { fetchTransactions } from '../services/api';

export default function DashboardScreen() {
  const router = useRouter();
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [recentTransactions, setRecentTransactions] = useState<any[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  const loadHistory = async () => {
    try {
      // Just fetch a few for preview
      const data = await fetchTransactions('mama_ada', 3);
      setRecentTransactions(data.transactions || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingHistory(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadHistory();
    }, [])
  );

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
        // Navigate to chat and pass URI
        router.push({ pathname: '/chat', params: { initialVoiceUri: uri } });
      }
    } catch (error) {
      console.error('Error stopping recording:', error);
    }
  };

  const handleSendText = () => {
    if (!inputText.trim()) return;
    const textToSend = inputText;
    setInputText('');
    // Navigate to chat and pass text
    router.push({ pathname: '/chat', params: { initialText: textToSend } });
  };

  const formatCurrency = (val: number) => `₦${val?.toLocaleString() || '0'}`;

  return (
    <KeyboardAvoidingView 
      style={{ flex: 1, backgroundColor: '#0F172A' }}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
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
            <View>
              <Text style={styles.greetingText}>Good Morning,</Text>
              <Text style={styles.headerTitle}>Mama Ada</Text>
            </View>
          </View>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <TouchableOpacity style={[styles.iconButton, { marginRight: 12 }]} onPress={() => router.push('/history')}>
              <Ionicons name="time-outline" size={24} color="#38BDF8" />
            </TouchableOpacity>
            <TouchableOpacity style={styles.iconButton}>
              <Ionicons name="notifications-outline" size={24} color="#38BDF8" />
            </TouchableOpacity>
          </View>
        </View>

        {/* Action Area (Mic) */}
        <View style={styles.actionArea}>
          <TouchableOpacity 
            style={[styles.bigMicContainer, isRecording && styles.bigMicActive]}
            onPressIn={startRecording}
            onPressOut={stopRecording}
            activeOpacity={0.8}
          >
            <LinearGradient 
              colors={isRecording ? ['#EA580C', '#C2410C'] : ['#F97316', '#EA580C']} 
              style={styles.bigMicGradient}
            >
              <Ionicons name="mic" size={48} color="#FFFFFF" />
            </LinearGradient>
          </TouchableOpacity>
          <Text style={styles.tapToSpeakText}>
            <Ionicons name="mic-outline" size={18} /> Tap to Speak
          </Text>
          <Text style={styles.hintText}>"Sold 2 bags of rice for ₦45,000"</Text>
          
          <View style={styles.inputContainer}>
            <TextInput 
              style={styles.textInput}
              placeholder="Or type a message..."
              placeholderTextColor="#64748B"
              value={inputText}
              onChangeText={setInputText}
              onSubmitEditing={handleSendText}
            />
            {inputText.trim().length > 0 && (
              <TouchableOpacity style={styles.sendButton} onPress={handleSendText}>
                <Ionicons name="send" size={20} color="#FFFFFF" style={{ marginLeft: 3 }} />
              </TouchableOpacity>
            )}
          </View>
        </View>

        {/* History Preview */}
        <View style={styles.historySection}>
          <View style={styles.historyHeader}>
            <Text style={styles.historyTitle}>Daily History</Text>
            <TouchableOpacity onPress={() => router.push('/history')}>
              <Text style={styles.seeAllText}>See All</Text>
            </TouchableOpacity>
          </View>

          {loadingHistory ? (
            <ActivityIndicator size="small" color="#38BDF8" style={{ marginTop: 20 }} />
          ) : recentTransactions.length === 0 ? (
            <Text style={styles.emptyText}>No recent transactions.</Text>
          ) : (
            recentTransactions.map((tx: any) => (
              <View key={tx.id} style={styles.transactionCard}>
                <LinearGradient
                  colors={['rgba(30, 41, 59, 0.7)', 'rgba(15, 23, 42, 0.4)']}
                  style={styles.transactionInner}
                >
                  <View style={styles.txLeft}>
                    <View style={[styles.txIconContainer, tx.type === 'sale' ? styles.txIconSale : styles.txIconExpense]}>
                      <Ionicons 
                        name={tx.type === 'sale' ? 'arrow-up' : 'arrow-down'} 
                        size={20} 
                        color={tx.type === 'sale' ? '#10B981' : '#F43F5E'} 
                      />
                    </View>
                    <View>
                      <Text style={styles.txItemName}>{tx.item}</Text>
                      <Text style={styles.txQuantity}>{tx.quantity || '1 item'} • {tx.type}</Text>
                    </View>
                  </View>
                  <Text style={[styles.txAmount, tx.type === 'sale' ? styles.txAmountSale : styles.txAmountExpense]}>
                    {tx.type === 'sale' ? '+' : '-'}{formatCurrency(tx.amount)}
                  </Text>
                </LinearGradient>
              </View>
            ))
          )}
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
    paddingTop: 60,
    paddingBottom: 20,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  profilePic: {
    width: 48,
    height: 48,
    borderRadius: 24,
    marginRight: 16,
    borderWidth: 2,
    borderColor: '#38BDF8',
  },
  greetingText: {
    fontSize: 14,
    color: '#94A3B8',
    fontWeight: '500',
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#F8FAFC',
    letterSpacing: 0.5,
  },
  iconButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#1E293B',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#334155',
  },
  actionArea: {
    alignItems: 'center',
    paddingVertical: 40,
    paddingHorizontal: 20,
  },
  bigMicContainer: {
    width: 120,
    height: 120,
    borderRadius: 60,
    shadowColor: '#F97316',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.5,
    shadowRadius: 16,
    elevation: 10,
    marginBottom: 20,
    overflow: 'hidden',
  },
  bigMicActive: {
    transform: [{ scale: 1.05 }],
  },
  bigMicGradient: {
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  tapToSpeakText: {
    fontSize: 22,
    fontWeight: '800',
    color: '#F8FAFC',
    marginBottom: 8,
  },
  hintText: {
    fontSize: 14,
    color: '#94A3B8',
    fontStyle: 'italic',
    marginBottom: 32,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
  },
  textInput: {
    flex: 1,
    backgroundColor: '#1E293B',
    borderWidth: 1,
    borderColor: '#334155',
    borderRadius: 24,
    paddingHorizontal: 20,
    paddingVertical: 14,
    fontSize: 16,
    color: '#F8FAFC',
  },
  sendButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#38BDF8',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 12,
    shadowColor: '#38BDF8',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  historySection: {
    flex: 1,
    paddingHorizontal: 20,
  },
  historyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  historyTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: '#F8FAFC',
  },
  seeAllText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#34D399',
  },
  transactionCard: {
    marginBottom: 12,
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.05)',
  },
  transactionInner: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
  },
  txLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  txIconContainer: {
    width: 44,
    height: 44,
    borderRadius: 22,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 16,
    borderWidth: 1,
  },
  txIconSale: {
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    borderColor: 'rgba(16, 185, 129, 0.2)',
  },
  txIconExpense: {
    backgroundColor: 'rgba(244, 63, 94, 0.1)',
    borderColor: 'rgba(244, 63, 94, 0.2)',
  },
  txItemName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#F8FAFC',
    textTransform: 'capitalize',
    marginBottom: 4,
  },
  txQuantity: {
    fontSize: 13,
    color: '#94A3B8',
    fontWeight: '500',
  },
  txAmount: {
    fontSize: 17,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  txAmountSale: {
    color: '#34D399',
  },
  txAmountExpense: {
    color: '#FB7185',
  },
  emptyText: {
    color: '#64748B',
    textAlign: 'center',
    marginTop: 20,
    fontSize: 15,
  }
});
