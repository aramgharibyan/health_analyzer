import React, { useState } from 'react';
import {
  ScrollView, View, Text, TextInput, TouchableOpacity,
  StyleSheet, Alert, ActivityIndicator,
} from 'react-native';
import { authApi } from '../services/api';
import { useAuthStore } from '../store/authStore';

export function SettingsScreen() {
  const { user, updateUser, logout } = useAuthStore();
  const [form, setForm] = useState({
    full_name: user?.full_name ?? '',
    age: user?.age ? String(user.age) : '',
    height_cm: user?.height_cm ? String(user.height_cm) : '',
    weight_kg: user?.weight_kg ? String(user.weight_kg) : '',
    gender: user?.gender ?? '',
  });
  const [saving, setSaving] = useState(false);

  function update(key: string) {
    return (val: string) => setForm((f) => ({ ...f, [key]: val }));
  }

  async function save() {
    setSaving(true);
    try {
      const res = await authApi.updateMe({
        full_name: form.full_name || undefined,
        age: form.age ? Number(form.age) : undefined,
        height_cm: form.height_cm ? Number(form.height_cm) : undefined,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : undefined,
        gender: form.gender || undefined,
      });
      await updateUser(res.data);
      Alert.alert('Saved', 'Your profile has been updated.');
    } catch (err: any) {
      Alert.alert('Error', err.response?.data?.detail ?? 'Could not save profile.');
    } finally {
      setSaving(false);
    }
  }

  function confirmLogout() {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: logout },
    ]);
  }

  const field = (label: string, key: string, opts?: Partial<React.ComponentProps<typeof TextInput>>) => (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        style={styles.input}
        placeholderTextColor="#64748b"
        value={(form as any)[key]}
        onChangeText={update(key)}
        {...opts}
      />
    </View>
  );

  return (
    <ScrollView style={styles.screen} contentContainerStyle={styles.content}>
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Email</Text>
          <Text style={styles.infoValue}>{user?.email}</Text>
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Profile</Text>
        {field('Full Name', 'full_name')}
        <View style={styles.row}>
          {field('Age', 'age', { keyboardType: 'numeric', style: [styles.input, styles.half] })}
          {field('Gender', 'gender', { style: [styles.input, styles.half] })}
        </View>
        <View style={styles.row}>
          {field('Height (cm)', 'height_cm', { keyboardType: 'numeric', style: [styles.input, styles.half] })}
          {field('Weight (kg)', 'weight_kg', { keyboardType: 'numeric', style: [styles.input, styles.half] })}
        </View>
        <TouchableOpacity style={styles.saveBtn} onPress={save} disabled={saving}>
          {saving
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.saveBtnText}>Save Profile</Text>
          }
        </TouchableOpacity>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Version</Text>
          <Text style={styles.infoValue}>1.0.0</Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>AI Model</Text>
          <Text style={styles.infoValue}>Claude</Text>
        </View>
      </View>

      <TouchableOpacity style={styles.logoutBtn} onPress={confirmLogout}>
        <Text style={styles.logoutText}>Sign Out</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#0f172a' },
  content: { padding: 16 },
  section: {
    backgroundColor: '#1e293b', borderRadius: 12, padding: 16, marginBottom: 16,
  },
  sectionTitle: {
    color: '#94a3b8', fontSize: 11, fontWeight: '700',
    textTransform: 'uppercase', letterSpacing: 1, marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#334155',
  },
  infoLabel: { color: '#94a3b8', fontSize: 14 },
  infoValue: { color: '#e2e8f0', fontSize: 14, fontWeight: '500' },
  field: { marginBottom: 12 },
  label: { color: '#94a3b8', fontSize: 12, marginBottom: 4 },
  input: {
    backgroundColor: '#0f172a', color: '#e2e8f0', borderRadius: 8,
    padding: 12, fontSize: 15, borderWidth: 1, borderColor: '#334155',
  },
  row: { flexDirection: 'row', gap: 8 },
  half: { flex: 1 },
  saveBtn: {
    backgroundColor: '#0ea5e9', borderRadius: 10, padding: 14,
    alignItems: 'center', marginTop: 4,
  },
  saveBtnText: { color: '#fff', fontWeight: '700', fontSize: 15 },
  logoutBtn: {
    backgroundColor: '#1e293b', borderRadius: 12, padding: 16,
    alignItems: 'center', borderWidth: 1, borderColor: '#ef4444',
  },
  logoutText: { color: '#ef4444', fontWeight: '700', fontSize: 15 },
});
