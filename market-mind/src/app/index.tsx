import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, Image, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Ionicons } from '@expo/vector-icons';

export default function WelcomeScreen() {
  const [name, setName] = useState('');
  const [language, setLanguage] = useState<'english' | 'pidgin'>('english');
  const router = useRouter();

  useEffect(() => {
    // Check if user is already logged in
    const checkLoginStatus = async () => {
      try {
        const storedName = await AsyncStorage.getItem('user_name');
        if (storedName) {
          router.replace('/dashboard');
        }
      } catch (error) {
        console.error('Error checking login status:', error);
      }
    };
    checkLoginStatus();
  }, []);

  const handleStartTrading = async () => {
    if (!name.trim()) return;
    try {
      await AsyncStorage.setItem('user_name', name.trim());
      await AsyncStorage.setItem('user_language', language);
      router.replace('/dashboard');
    } catch (error) {
      console.error('Error saving login details:', error);
    }
  };

  return (
    <KeyboardAvoidingView 
      style={{ flex: 1 }} 
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.container}>
        
        {/* Logo Section */}
        <View style={styles.logoContainer}>
          <Image 
            source={require('../../assets/images/logo.png')} 
            style={styles.logo} 
            resizeMode="contain"
          />
        </View>

        {/* Header Text */}
        <View style={styles.headerContainer}>
          <Text style={styles.title}>Welcome to your Market Ledger</Text>
          <Text style={styles.subtitle}>Keep track of every kobo, every customer.</Text>
        </View>

        {/* Input Section */}
        <View style={styles.inputSection}>
          <Text style={styles.label}>What is your name?</Text>
          <View style={styles.inputContainer}>
            <Ionicons name="person-outline" size={20} color="#6B7280" style={styles.inputIcon} />
            <TextInput
              style={styles.input}
              placeholder="e.g., Mama Ada"
              placeholderTextColor="#9CA3AF"
              value={name}
              onChangeText={setName}
              autoCapitalize="words"
            />
          </View>
        </View>

        {/* Language Toggle */}
        <View style={styles.languageSection}>
          <Text style={styles.label}>Choose Language</Text>
          <View style={styles.toggleContainer}>
            <TouchableOpacity 
              style={[styles.toggleButton, language === 'english' && styles.toggleButtonActive]}
              onPress={() => setLanguage('english')}
            >
              <Text style={[styles.toggleText, language === 'english' && styles.toggleTextActive]}>English</Text>
            </TouchableOpacity>
            <TouchableOpacity 
              style={[styles.toggleButton, language === 'pidgin' && styles.toggleButtonActive]}
              onPress={() => setLanguage('pidgin')}
            >
              <Text style={[styles.toggleText, language === 'pidgin' && styles.toggleTextActive]}>Pidgin</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Slogan */}
        <View style={styles.sloganContainer}>
          <Text style={styles.sloganText}>"Keep your records easy, for Nigerian market!"</Text>
        </View>

        {/* Action Button */}
        <TouchableOpacity 
          style={[styles.button, !name.trim() && styles.buttonDisabled]} 
          onPress={handleStartTrading}
          disabled={!name.trim()}
        >
          <Text style={styles.buttonText}>Start Trading  <Ionicons name="arrow-forward" size={18} color="#FFF" /></Text>
        </TouchableOpacity>

        {/* Footer */}
        <View style={styles.footerContainer}>
          <Text style={styles.footerText}>No Login Required  •  Your Data Stays Local</Text>
        </View>

      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    backgroundColor: '#FAFAFA', // Light background matching mockup
    paddingHorizontal: 24,
    paddingTop: 80,
    paddingBottom: 40,
    alignItems: 'center',
  },
  logoContainer: {
    marginBottom: 40,
  },
  logo: {
    width: 80,
    height: 80,
  },
  headerContainer: {
    alignItems: 'center',
    marginBottom: 40,
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: '#111827',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#6B7280',
    textAlign: 'center',
  },
  inputSection: {
    width: '100%',
    marginBottom: 32,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#374151',
    marginBottom: 8,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#E5E7EB',
    borderRadius: 12,
    paddingHorizontal: 16,
    height: 56,
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    fontSize: 16,
    color: '#111827',
    height: '100%',
  },
  languageSection: {
    width: '100%',
    marginBottom: 40,
  },
  toggleContainer: {
    flexDirection: 'row',
    backgroundColor: '#F3F4F6',
    borderRadius: 12,
    padding: 4,
  },
  toggleButton: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderRadius: 8,
  },
  toggleButtonActive: {
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  toggleText: {
    fontSize: 16,
    fontWeight: '500',
    color: '#6B7280',
  },
  toggleTextActive: {
    color: '#111827',
    fontWeight: '600',
  },
  sloganContainer: {
    backgroundColor: '#ECFDF5', // Light green background
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 20,
    marginBottom: 40,
    width: '100%',
  },
  sloganText: {
    color: '#059669', // Dark green text
    textAlign: 'center',
    fontWeight: '500',
    fontSize: 14,
  },
  button: {
    backgroundColor: '#065F46', // Deep green
    width: '100%',
    paddingVertical: 16,
    borderRadius: 16,
    alignItems: 'center',
    marginBottom: 24,
  },
  buttonDisabled: {
    backgroundColor: '#A7F3D0', // Light green for disabled state
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
  },
  footerContainer: {
    marginTop: 'auto',
  },
  footerText: {
    color: '#9CA3AF',
    fontSize: 12,
  },
});
