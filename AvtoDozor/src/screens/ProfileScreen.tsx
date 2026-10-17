import React, { useCallback } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import * as api from '../api';
import AppButton from '../components/AppButton';
import Screen from '../components/Screen';
import { useAuth } from '../context/AuthContext';
import { useLoader } from '../hooks/useLoader';
import { colors, radius } from '../theme';
import type { Employee } from '../types';
import { orDash } from '../utils/format';

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
    </View>
  );
}

/** Личный кабинет (ТЗ, рисунок 2): ФИО, дата рождения, телефон, служебная почта, подразделение. */
export default function ProfileScreen() {
  const { user, signOut } = useAuth();
  const { data: profile, loading, reload } = useLoader<Employee | null>(api.fetchProfile, null);

  useFocusEffect(
    useCallback(() => {
      reload();
    }, [reload]),
  );

  const position = profile?.position || user?.position || 'Оперуполномоченный';

  return (
    <Screen title="Личный кабинет">
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.card} testID="profile-card">
          <Text style={styles.cardTitle}>{position}</Text>
          <Row label="ФИО:" value={orDash(profile?.full_name ?? user?.fullName)} />
          <Row label="Дата рождения:" value={orDash(profile?.birth_date)} />
          <Row label="Номер телефона:" value={orDash(profile?.phone)} />
          <Row label="Служебная почта:" value={orDash(profile?.email ?? user?.email)} />
          <Row label="Подразделение:" value={orDash(profile?.department_name)} />
          {loading && !profile ? <Text style={styles.loading}>Загрузка...</Text> : null}
        </View>

        <View style={styles.logout}>
          <AppButton title="Выйти из системы" onPress={signOut} />
        </View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: {
    paddingTop: 16,
  },
  card: {
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radius * 2,
    padding: 18,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    textAlign: 'center',
    color: colors.text,
    marginBottom: 14,
  },
  row: {
    marginBottom: 12,
  },
  label: {
    fontSize: 13,
    color: colors.muted,
  },
  value: {
    fontSize: 16,
    color: colors.text,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
    paddingVertical: 4,
  },
  loading: {
    textAlign: 'center',
    color: colors.muted,
    marginTop: 4,
  },
  logout: {
    marginTop: 24,
    alignSelf: 'center',
    minWidth: 200,
  },
});
