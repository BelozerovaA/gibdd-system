import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import type { ExportFormat } from '../types';
import { colors } from '../theme';
import AppButton from './AppButton';
import ModalCard from './ModalCard';

interface Props {
  visible: boolean;
  busy: boolean;
  onSelect: (format: ExportFormat) => void;
  onClose: () => void;
}

/** Диалог «Выбор формата» (ТЗ, рисунок 10): сохранение истории в docx или Excel. */
export default function ExportModal({ visible, busy, onSelect, onClose }: Props) {
  return (
    <ModalCard visible={visible} title="Выбор формата" onRequestClose={onClose}>
      <Text style={styles.text}>В каком формате сохранить отчёт?</Text>
      <View style={styles.actions}>
        <View style={styles.button}>
          <AppButton title="Word (docx)" disabled={busy} onPress={() => onSelect('docx')} />
        </View>
        <View style={styles.button}>
          <AppButton title="Excel (xlsx)" disabled={busy} onPress={() => onSelect('xlsx')} />
        </View>
      </View>
      <View style={styles.cancel}>
        <AppButton title="Отмена" small loading={busy} onPress={onClose} />
      </View>
    </ModalCard>
  );
}

const styles = StyleSheet.create({
  text: {
    fontSize: 15,
    textAlign: 'center',
    color: colors.text,
    marginBottom: 16,
  },
  actions: {
    flexDirection: 'row',
    gap: 10,
  },
  button: {
    flex: 1,
  },
  cancel: {
    marginTop: 12,
    alignSelf: 'center',
    minWidth: 140,
  },
});
