import React, { useEffect } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import * as Linking from 'expo-linking';
import { useAuthStore } from '../store/authStore';
import { AuthStack } from './AuthStack';
import { MainTabs } from './MainTabs';

// Deep link prefix for OAuth callbacks: healthanalyzer://
const prefix = Linking.createURL('/');

const linking = {
  prefixes: [prefix, 'healthanalyzer://'],
  config: {
    screens: {
      // OAuth callbacks are handled imperatively in IntegrationsScreen
      // We just need the prefix registered so the OS passes URLs to the app
    },
  },
};

export function AppNavigator() {
  const { isAuthenticated, isHydrated, hydrate } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, []);

  if (!isHydrated) {
    return (
      <View style={{ flex: 1, backgroundColor: '#0f172a', alignItems: 'center', justifyContent: 'center' }}>
        <ActivityIndicator color="#0ea5e9" size="large" />
      </View>
    );
  }

  return (
    <NavigationContainer linking={linking}>
      {isAuthenticated ? <MainTabs /> : <AuthStack />}
    </NavigationContainer>
  );
}
