import React, { useEffect, useState, useCallback } from 'react';
import {
  ScrollView, View, Text, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator, Platform, RefreshControl,
} from 'react-native';
import * as WebBrowser from 'expo-web-browser';
import * as Linking from 'expo-linking';
import { integrationApi } from '../services/api';
import { syncToBackend, isHealthKitAvailable } from '../services/healthKit';
import { Integration } from '../types';

WebBrowser.maybeCompleteAuthSession();

const OAUTH_PLATFORMS = ['whoop', 'withings', 'fitbod', 'yazio', 'larq'];

export function IntegrationsScreen() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const res = await integrationApi.status();
      setIntegrations(res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function connectOAuth(platform: string) {
    setSyncing(platform);
    try {
      const { data } = await integrationApi.connect(platform);
      const callbackUrl = Linking.createURL(`/oauth/${platform}/callback`);
      const result = await WebBrowser.openAuthSessionAsync(data.auth_url, callbackUrl);

      if (result.type === 'success') {
        const url = new URL(result.url);
        const code = url.searchParams.get('code') ?? '';
        const state = url.searchParams.get('state') ?? '';
        await integrationApi.callback(platform, code, state);
        await load();
      }
    } catch (err: any) {
      Alert.alert('Connection Failed', err.message ?? 'Could not connect. Try again.');
    } finally {
      setSyncing(null);
    }
  }

  async function connectAppleHealth() {
    if (!isHealthKitAvailable()) {
      Alert.alert('Not Available', 'Apple Health is only available on iOS.');
      return;
    }
    setSyncing('apple_health');
    try {
      const result = await syncToBackend(30);
      Alert.alert('Synced!', `Imported ${result.records_synced} records from Apple Health.`);
      await load();
    } catch (err: any) {
      Alert.alert('Sync Failed', err.message ?? 'Could not sync Apple Health data.');
    } finally {
      setSyncing(null);
    }
  }

  async function syncPlatform(platform: string) {
    setSyncing(platform);
    try {
      await integrationApi.sync(platform, 30);
      Alert.alert('Synced', `${platform} data updated.`);
      await load();
    } catch (err: any) {
      Alert.alert('Sync Failed', err.response?.data?.detail ?? err.message);
    } finally {
      setSyncing(null);
    }
  }

  async function disconnect(platform: string) {
    Alert.alert('Disconnect', `Disconnect ${platform}?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Disconnect', style: 'destructive',
        onPress: async () => {
          setSyncing(platform);
          try {
            await integrationApi.disconnect(platform);
            await load();
          } finally {
            setSyncing(null);
          }
        },
      },
    ]);
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#0ea5e9" />
      </View>
    );
  }

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} tintColor="#0ea5e9" />
      }
    >
      <Text style={styles.info}>
        Connect your devices and apps to aggregate all your health data in one place.
      </Text>

      {integrations.map((integration) => {
        const isBusy = syncing === integration.platform;
        const isOAuth = OAUTH_PLATFORMS.includes(integration.platform);
        const isApple = integration.platform === 'apple_health';

        return (
          <View key={integration.platform} style={styles.card}>
            <View style={styles.cardHeader}>
              <View>
                <Text style={styles.platformName}>{integration.name}</Text>
                <Text style={styles.platformDesc}>{integration.description}</Text>
              </View>
              <View style={[
                styles.badge,
                integration.is_connected ? styles.badgeConnected : styles.badgeDisconnected,
              ]}>
                <Text style={styles.badgeText}>
                  {integration.is_connected ? 'Connected' : 'Off'}
                </Text>
              </View>
            </View>

            {integration.last_synced_at && (
              <Text style={styles.lastSync}>
                Last sync: {new Date(integration.last_synced_at).toLocaleDateString()}
              </Text>
            )}

            <View style={styles.actions}>
              {integration.is_connected ? (
                <>
                  {(isOAuth || isApple) && (
                    <TouchableOpacity
                      style={[styles.btn, styles.btnPrimary]}
                      onPress={() => isApple ? connectAppleHealth() : syncPlatform(integration.platform)}
                      disabled={isBusy}
                    >
                      {isBusy
                        ? <ActivityIndicator color="#fff" size="small" />
                        : <Text style={styles.btnText}>{isApple ? 'Sync Now' : 'Sync'}</Text>
                      }
                    </TouchableOpacity>
                  )}
                  <TouchableOpacity
                    style={[styles.btn, styles.btnDanger]}
                    onPress={() => disconnect(integration.platform)}
                    disabled={isBusy}
                  >
                    <Text style={styles.btnTextDanger}>Disconnect</Text>
                  </TouchableOpacity>
                </>
              ) : (
                <TouchableOpacity
                  style={[styles.btn, styles.btnPrimary, { flex: 1 }]}
                  onPress={() => {
                    if (isApple) connectAppleHealth();
                    else if (isOAuth) connectOAuth(integration.platform);
                    else Alert.alert('Manual Setup', 'Use API key or credentials in Settings.');
                  }}
                  disabled={isBusy}
                >
                  {isBusy
                    ? <ActivityIndicator color="#fff" size="small" />
                    : <Text style={styles.btnText}>
                        {isApple
                          ? (Platform.OS === 'ios' ? 'Connect Apple Health' : 'iOS Only')
                          : `Connect ${integration.name}`}
                      </Text>
                  }
                </TouchableOpacity>
              )}
            </View>
          </View>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#0f172a' },
  content: { padding: 16 },
  center: { flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center' },
  info: { color: '#64748b', fontSize: 13, marginBottom: 16, lineHeight: 20 },
  card: {
    backgroundColor: '#1e293b',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  platformName: { color: '#e2e8f0', fontSize: 16, fontWeight: '600' },
  platformDesc: { color: '#64748b', fontSize: 12, marginTop: 2, maxWidth: 220 },
  badge: { borderRadius: 12, paddingHorizontal: 10, paddingVertical: 3 },
  badgeConnected: { backgroundColor: '#052e16' },
  badgeDisconnected: { backgroundColor: '#1c1917' },
  badgeText: { fontSize: 11, fontWeight: '600', color: '#4ade80' },
  lastSync: { color: '#475569', fontSize: 11, marginBottom: 12 },
  actions: { flexDirection: 'row', gap: 8 },
  btn: { flex: 1, borderRadius: 8, paddingVertical: 10, alignItems: 'center' },
  btnPrimary: { backgroundColor: '#0ea5e9' },
  btnDanger: { backgroundColor: 'transparent', borderWidth: 1, borderColor: '#ef4444' },
  btnText: { color: '#fff', fontWeight: '600', fontSize: 14 },
  btnTextDanger: { color: '#ef4444', fontWeight: '600', fontSize: 14 },
});
