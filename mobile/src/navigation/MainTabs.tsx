import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import { DashboardScreen } from '../screens/DashboardScreen';
import { IntegrationsScreen } from '../screens/IntegrationsScreen';
import { LabTestsScreen } from '../screens/LabTestsScreen';
import { AIAssistantScreen } from '../screens/AIAssistantScreen';
import { SettingsScreen } from '../screens/SettingsScreen';

export type MainTabsParams = {
  Dashboard: undefined;
  Integrations: undefined;
  'Lab Tests': undefined;
  AI: undefined;
  Settings: undefined;
};

const Tab = createBottomTabNavigator<MainTabsParams>();

const ICONS: Record<string, string> = {
  Dashboard: '📊',
  Integrations: '🔗',
  'Lab Tests': '🧪',
  AI: '🤖',
  Settings: '⚙️',
};

export function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: () => (
          <Text style={{ fontSize: 20 }}>{ICONS[route.name]}</Text>
        ),
        tabBarStyle: {
          backgroundColor: '#0f172a',
          borderTopColor: '#1e293b',
        },
        tabBarActiveTintColor: '#0ea5e9',
        tabBarInactiveTintColor: '#64748b',
        headerStyle: { backgroundColor: '#0f172a' },
        headerTintColor: '#e2e8f0',
        headerTitleStyle: { fontWeight: '600' },
      })}
    >
      <Tab.Screen name="Dashboard" component={DashboardScreen} />
      <Tab.Screen name="Integrations" component={IntegrationsScreen} />
      <Tab.Screen name="Lab Tests" component={LabTestsScreen} />
      <Tab.Screen name="AI" component={AIAssistantScreen} options={{ title: 'AI Assistant' }} />
      <Tab.Screen name="Settings" component={SettingsScreen} />
    </Tab.Navigator>
  );
}
