import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { colors } from '../theme';
import AppButton from './AppButton';
import ModalCard from './ModalCard';

interface Props {
  question: { alertId: number; plate: string } | null;
  busy: boolean;
  onAnswer: (found: 'Да' | 'Нет') => void;
}

/** Окно о результате розыска (ТЗ, рисунок 8): «Да» исключает автомобиль из розыска, «Нет» оставляет. */
export default function FoundModal({ question, busy, onAnswer }: Props) {
  return (
    <ModalCard visible={question !== null} title="Результат розыска">
      {question ? (
        <View>
          <Text style={styles.text}>Автомобиль {question.plate} задержан?</Text>
          <View style={styles.actions}>
            <View style={styles.button}>
              <AppButton title="Да" variant="primary" disabled={busy} onPress={() => onAnswer('Да')} />
            </View>
            <View style={styles.button}>
              <AppButton title="Нет" disabled={busy} onPress={() => onAnswer('Нет')} />
            </View>
          </View>
        </View>
      ) : null}
    </ModalCard>
  );
}

const styles = StyleSheet.create({
  text: {
    fontSize: 16,
    textAlign: 'center',
    color: colors.text,
    marginBottom: 16,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
  },
  button: {
    flex: 1,
  },
});
