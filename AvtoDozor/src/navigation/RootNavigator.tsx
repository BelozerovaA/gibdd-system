import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { BottomTabBarProps, createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { useAuth } from '../context/AuthContext';
import AllWantedScreen from '../screens/AllWantedScreen';
import HistoryScreen from '../screens/HistoryScreen';
import LoginScreen from '../screens/LoginScreen';
import MapScreen from '../screens/MapScreen';
import MyWantedScreen from '../screens/MyWantedScreen';
import ProfileScreen from '../screens/ProfileScreen';
import { colors } from '../theme';
import type { RootStackParamList, TabParamList } from './navigationRef';
import TabBar from './TabBar';

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tabs = createBottomTabNavigator<TabParamList>();

const renderTabBar = (props: BottomTabBarProps) => <TabBar {...props} />;

function MainTabs() {
  return (
    <Tabs.Navigator
      initialRouteName="Profile"
      tabBar={renderTabBar}
      screenOptions={{ headerShown: false }}>
      <Tabs.Screen name="Profile" component={ProfileScreen} />
      <Tabs.Screen name="MyWanted" component={MyWantedScreen} />
      <Tabs.Screen name="AllWanted" component={AllWantedScreen} />
      <Tabs.Screen name="Map" component={MapScreen} />
      <Tabs.Screen name="History" component={HistoryScreen} />
    </Tabs.Navigator>
  );
}

export default function RootNavigator() {
  const { status } = useAuth();

  if (status === 'loading') {
    return (
      <View style={styles.splash}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      {status === 'signedIn' ? (
        // до авторизации кнопок меню нет (ТЗ): вкладки доступны только после входа
        <Stack.Screen name="Main" component={MainTabs} />
      ) : (
        <Stack.Screen name="Login" component={LoginScreen} />
      )}
    </Stack.Navigator>
  );
}

const styles = StyleSheet.create({
  splash: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
  },
});
