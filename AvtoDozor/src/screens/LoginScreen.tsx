import React, { useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AppButton from '../components/AppButton';
import { useAuth } from '../context/AuthContext';
import { getServerHost, saveServerHost } from '../server';
import { colors, radius } from '../theme';
import { notify } from '../utils/notify';

/** Страница авторизации (ТЗ, рисунок 1): логин, пароль, кнопка «Войти». */
export default function LoginScreen() {
  const { signIn } = useAuth();
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const [showServer, setShowServer] = useState(false);
  const [host, setHost] = useState(getServerHost());

  const submit = async () => {
    if (!login.trim() || !password) {
      setError('Введите логин и пароль');
      return;
    }
    setError('');
    setLoading(true);
    try {
      await signIn(login.trim(), password);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Не удалось войти');
      setLoading(false);
    }
  };

  const saveHost = async () => {
    const saved = await saveServerHost(host);
    setHost(saved);
    notify(`Адрес сервера: ${saved}`);
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled">
          <Text style={styles.title}>Вход в систему оперативного розыска транспортных средств</Text>

          <TextInput
            testID="login-input"
            style={styles.input}
            placeholder="Логин"
            placeholderTextColor={colors.muted}
            autoCapitalize="none"
            autoCorrect={false}
            value={login}
            onChangeText={setLogin}
            returnKeyType="next"
          />
          <TextInput
            testID="password-input"
            style={styles.input}
            placeholder="Пароль"
            placeholderTextColor={colors.muted}
            secureTextEntry
            autoCapitalize="none"
            value={password}
            onChangeText={setPassword}
            onSubmitEditing={submit}
            returnKeyType="done"
          />

          {error ? (
            <Text testID="login-error" style={styles.error}>
              {error}
            </Text>
          ) : null}

          <View style={styles.submit}>
            <AppButton title="Войти" variant="primary" loading={loading} onPress={submit} />
          </View>

          <Pressable onPress={() => setShowServer(v => !v)} style={styles.serverToggle}>
            <Text style={styles.serverToggleText}>
              {showServer ? 'Скрыть настройки сервера' : 'Настройки сервера'}
            </Text>
          </Pressable>

          {showServer ? (
            <View style={styles.serverBox}>
              <Text style={styles.hint}>
                Адрес компьютера с backend: для эмулятора 10.0.2.2:8000, для телефона IP компьютера в
                Wi-Fi, например 192.168.0.15:8000
              </Text>
              <TextInput
                testID="server-input"
                style={styles.input}
                placeholder="10.0.2.2:8000"
                placeholderTextColor={colors.muted}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
                value={host}
                onChangeText={setHost}
              />
              <AppButton title="Сохранить адрес" small onPress={saveHost} />
            </View>
          ) : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.background,
  },
  flex: {
    flex: 1,
  },
  content: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: 28,
    paddingVertical: 24,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
    textAlign: 'center',
    color: colors.text,
    marginBottom: 28,
  },
  input: {
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radius,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 16,
    color: colors.text,
    marginBottom: 14,
  },
  error: {
    color: colors.danger,
    textAlign: 'center',
    marginBottom: 12,
  },
  submit: {
    alignSelf: 'center',
    minWidth: 160,
    marginTop: 4,
  },
  serverToggle: {
    alignSelf: 'center',
    marginTop: 28,
    padding: 8,
  },
  serverToggleText: {
    color: colors.primary,
    fontSize: 14,
  },
  serverBox: {
    marginTop: 8,
  },
  hint: {
    fontSize: 12,
    color: colors.muted,
    marginBottom: 10,
  },
});
