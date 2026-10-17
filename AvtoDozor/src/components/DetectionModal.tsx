import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { DetectionPayload } from '../types';
import { colors } from '../theme';
import AppButton from './AppButton';
import ModalCard from './ModalCard';

interface Props {
  detection: DetectionPayload | null;
  busy: boolean;
  onAccept: () => void;
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value}</Text>
    </View>
  );
}

/** Окно оповещения (ТЗ, рисунок 7): ГРЗ, место, время и дата фиксации, кнопка «Принять». */
export default function DetectionModal({ detection, busy, onAccept }: Props) {
  return (
    <ModalCard visible={detection !== null} title="Оповещение">
      {detection ? (
        <View>
          <Field label="Автомобиль:" value={detection.plate} />
          <Field label="Место:" value={detection.address} />
          <Field label="Время:" value={detection.time} />
          <Field label="Дата:" value={detection.date} />
          <View style={styles.actions}>
            <AppButton title="Принять" variant="primary" loading={busy} onPress={onAccept} />
          </View>
        </View>
      ) : null}
    </ModalCard>
  );
}

const styles = StyleSheet.create({
  field: {
    marginBottom: 10,
  },
  label: {
    fontSize: 13,
    color: colors.muted,
  },
  value: {
    fontSize: 17,
    fontWeight: '600',
    color: colors.text,
  },
  actions: {
    marginTop: 8,
    alignItems: 'flex-end',
  },
});
