import React from 'react';
import { Modal, StyleSheet, Text, View } from 'react-native';
import { colors, radius } from '../theme';

interface Props {
  visible: boolean;
  title: string;
  children: React.ReactNode;
  /** Нажатие кнопки «Назад» на Android. По умолчанию окно закрыть нельзя: на оповещение нужно ответить. */
  onRequestClose?: () => void;
}

/** Диалоговое окно по центру экрана (оповещение, добавление, выбор формата). */
export default function ModalCard({ visible, title, children, onRequestClose }: Props) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent
      onRequestClose={onRequestClose ?? (() => {})}>
      <View style={styles.overlay}>
        <View style={styles.card}>
          <Text style={styles.title} accessibilityRole="header">
            {title}
          </Text>
          {children}
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: colors.overlay,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  card: {
    width: '100%',
    maxWidth: 420,
    backgroundColor: colors.background,
    borderRadius: radius * 1.5,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    padding: 18,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    textAlign: 'center',
    color: colors.text,
    marginBottom: 14,
  },
});
