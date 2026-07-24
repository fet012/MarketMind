import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { fetchTransactions } from '../services/api';
import { LinearGradient } from 'expo-linear-gradient';

export default function HistoryScreen() {
  const [transactions, setTransactions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const loadData = async () => {
    try {
      const data = await fetchTransactions('mama_ada', 50);
      setTransactions(data.transactions || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadData();
    }, [])
  );

  const formatCurrency = (val: number) => `₦${val?.toLocaleString() || '0'}`;

  // Group transactions by Date
  const groupedTransactions = transactions.reduce((acc: any, tx: any) => {
    const d = tx.date; 
    if (!acc[d]) acc[d] = [];
    acc[d].push(tx);
    return acc;
  }, {});

  const dates = Object.keys(groupedTransactions).sort((a, b) => b.localeCompare(a));
  
  const formatDateHeader = (d: string) => {
    const today = new Date().toISOString().split('T')[0];
    const yesterdayDate = new Date(Date.now() - 86400000).toISOString().split('T')[0];
    if (d === today) return 'Today';
    if (d === yesterdayDate) return 'Yesterday';
    return d;
  };

  if (loading && transactions.length === 0) {
    return (
      <LinearGradient colors={['#0F172A', '#1E293B', '#0F172A']} style={[styles.container, styles.centered]}>
        <ActivityIndicator size="large" color="#10B981" />
      </LinearGradient>
    );
  }

  return (
    <LinearGradient
      colors={['#0F172A', '#1E293B', '#0F172A']}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={styles.container}
    >
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color="#F8FAFC" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Transaction History</Text>
        <View style={{ width: 24 }} /> {/* Spacer */}
      </View>

      {/* Daily History */}
      <ScrollView style={styles.historyList} showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 40, paddingHorizontal: 24 }}>
        {dates.length === 0 ? (
          <Text style={styles.emptyText}>No transactions recorded yet.</Text>
        ) : (
          dates.map((dateKey) => (
            <View key={dateKey}>
              <Text style={styles.dateHeader}>{formatDateHeader(dateKey)}</Text>
              {groupedTransactions[dateKey].map((tx: any) => (
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
                        <Text style={styles.txQuantity}>{tx.quantity || '1 item'}</Text>
                      </View>
                    </View>
                    <Text style={[styles.txAmount, tx.type === 'sale' ? styles.txAmountSale : styles.txAmountExpense]}>
                      {tx.type === 'sale' ? '+' : '-'}{formatCurrency(tx.amount)}
                    </Text>
                  </LinearGradient>
                </View>
              ))}
            </View>
          ))
        )}
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centered: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 60,
    paddingBottom: 20,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.05)',
  },
  backButton: {
    padding: 8,
    marginLeft: -8,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '800',
    color: '#F8FAFC',
    letterSpacing: 0.5,
  },
  historyList: {
    flex: 1,
  },
  dateHeader: {
    fontSize: 13,
    fontWeight: '700',
    color: '#64748B',
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginTop: 24,
    marginBottom: 12,
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
    width: 48,
    height: 48,
    borderRadius: 24,
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
    fontSize: 17,
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
    fontSize: 18,
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
    marginTop: 40,
    fontSize: 16,
  }
});
