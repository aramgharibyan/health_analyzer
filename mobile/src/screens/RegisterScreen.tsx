import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, KeyboardAvoidingView, Platform,
  Alert, ActivityIndicator, ScrollView,
} from 'react-native';
import { StackNavigationProp } from '@react-navigation/stack';
import { authApi } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { AuthStackParams } from '../navigation/AuthStack';

type Props = { navigation: StackNavigationProp<AuthStackParams, 'Register'> };

export function RegisterScreen({ navigation }: Props) {
  const [form, setForm] = useState({
    email: '', password: '', full_name: '',
    age: '', height_cm: '', weight_kg: '', gender: '',
  });
  const [loading, setLoading] = useState(false);
  const { setAuth } = useAuthStore();

  function update(key: string) {
    return (val: string) => setForm((f) => ({ ...f, [key]: val }));
  }

  async function handleRegister() {
    if (!form.email || !form.password) {
      Alert.alert('Error', 'Email and password are required.');
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.register({
        email: form.email.trim(),
        password: form.password,
        full_name: form.full_name || undefined,
        age: form.age ? Number(form.age) : undefined,
        height_cm: form.height_cm ? Number(form.height_cm) : undefined,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : undefined,
        gender: form.gender || undefined,
      });
      const { access_token, user } = res.data;
      await setAuth(user, access_token);
    } catch (err: any) {
      Alert.alert('Registration Failed', err.response?.data?.detail ?? 'Please try again.');
    } finally {
      setLoading(false);
    }
  }

  const field = (
    placeholder: string,
    key: string,
    opts?: Partial<React.ComponentProps<typeof TextInput>>
  ) => (
    <TextInput
      style={styles.input}
      placeholder={placeholder}
      placeholderTextColor="#64748b"
      value={(form as any)[key]}
      onChangeText={update(key)}
      {...opts}
    />
  );

  return (
    <KeyboardAvoidingView
      style={styles.flex}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>Create Account</Text>
        <Text style={styles.subtitle}>Start tracking your health journey</Text>

        {field('Email *', 'email', { autoCapitalize: 'none', keyboardType: 'email-address' })}
        {field('Password *', 'password', { secureTextEntry: true })}
        {field('Full Name', 'full_name')}

        <View style={styles.row}>
          {field('Age', 'age', { keyboardType: 'numeric', style: [styles.input, styles.half] })}
          {field('Gender (M/F/O)', 'gender', { style: [styles.input, styles.half] })}
        </View>
        <View style={styles.row}>
          {field('Height (cm)', 'height_cm', { keyboardType: 'numeric', style: [styles.input, styles.half] })}
          {field('Weight (kg)', 'weight_kg', { keyboardType: 'numeric', style: [styles.input, styles.half] })}
        </View>

        <TouchableOpacity style={styles.button} onPress={handleRegister} disabled={loading}>
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.buttonText}>Create Account</Text>
          }
        </TouchableOpacity>

        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.link}>
            Already have an account? <Text style={styles.linkBold}>Sign in</Text>
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1, backgroundColor: '#0f172a' },
  container: { flexGrow: 1, justifyContent: 'center', padding: 24 },
  title: { color: '#e2e8f0', fontSize: 26, fontWeight: '700', textAlign: 'center', marginBottom: 4 },
  subtitle: { color: '#94a3b8', fontSize: 14, textAlign: 'center', marginBottom: 28 },
  input: {
    backgroundColor: '#1e293b',
    color: '#e2e8f0',
    borderRadius: 10,
    padding: 14,
    fontSize: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#334155',
  },
  row: { flexDirection: 'row', gap: 8 },
  half: { flex: 1 },
  button: {
    backgroundColor: '#0ea5e9',
    borderRadius: 10,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
    marginBottom: 20,
  },
  buttonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
  link: { color: '#94a3b8', textAlign: 'center', fontSize: 14 },
  linkBold: { color: '#0ea5e9', fontWeight: '600' },
});
