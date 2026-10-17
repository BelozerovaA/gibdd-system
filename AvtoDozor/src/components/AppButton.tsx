import React from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';
import { colors, radius } from '../theme';

interface Props {
  title: string;
  onPress: () => void;
  variant?: 'outline' | 'primary';
  disabled?: boolean;
  loading?: boolean;
  small?: boolean;
  testID?: string;
}

export default function AppButton({
  title,
  onPress,
  variant = 'outline',
  disabled = false,
  loading = false,
  small = false,
  testID,
}: Props) {
  const primary = variant === 'primary';
  const inactive = disabled || loading;

  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityState={{ disabled: inactive }}
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.button,
        small && styles.small,
        primary ? styles.primary : styles.outline,
        pressed && styles.pressed,
        inactive && styles.inactive,
      ]}>
      {loading ? (
        <ActivityIndicator color={primary ? '#FFFFFF' : colors.text} />
      ) : (
        <Text style={[styles.text, small && styles.textSmall, primary && styles.textPrimary]}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: 44,
    paddingHorizontal: 14,
    borderRadius: radius,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  small: {
    minHeight: 38,
    paddingHorizontal: 10,
  },
  outline: {
    backgroundColor: colors.background,
    borderColor: colors.borderStrong,
  },
  primary: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  pressed: {
    opacity: 0.7,
  },
  inactive: {
    opacity: 0.45,
  },
  text: {
    fontSize: 15,
    color: colors.text,
    fontWeight: '500',
  },
  textSmall: {
    fontSize: 14,
  },
  textPrimary: {
    color: '#FFFFFF',
  },
});
