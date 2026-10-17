import React from 'react';
import { StatusBar } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AlertProvider } from './src/context/AlertContext';
import { AuthProvider } from './src/context/AuthContext';
import { navigationRef } from './src/navigation/navigationRef';
import RootNavigator from './src/navigation/RootNavigator';

export default function App() {
  return (
    <SafeAreaProvider>
      <StatusBar barStyle="dark-content" />
      <AuthProvider>
        <NavigationContainer ref={navigationRef}>
          <AlertProvider>
            <RootNavigator />
          </AlertProvider>
        </NavigationContainer>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
