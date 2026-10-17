import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors, radius } from '../theme';
import type { TabParamList } from './navigationRef';

export const TAB_LABELS: Record<keyof TabParamList, string> = {
  Profile: 'Личный кабинет',
  MyWanted: 'Мой розыск',
  AllWanted: 'База розыска',
  Map: 'Карта',
  History: 'История оповещений',
};

/**
 * Нижнее меню навигации из пяти кнопок (ТЗ, рисунки 2-9).
 * Кнопка открытой страницы выделена цветом.
 */
export default function TabBar({ state, navigation }: BottomTabBarProps) {
  const insets = useSafeAreaInsets();

  return (
    <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, 8) }]}>
      {state.routes.map((route, index) => {
        const focused = state.index === index;
        const label = TAB_LABELS[route.name as keyof TabParamList] ?? route.name;

        const onPress = () => {
          const event = navigation.emit({
            type: 'tabPress',
            target: route.key,
            canPreventDefault: true,
          });
          if (!focused && !event.defaultPrevented) {
            navigation.navigate(route.name, route.params);
          }
        };

        return (
          <Pressable
            key={route.key}
            testID={`tab-${route.name}`}
            accessibilityRole="button"
            accessibilityState={{ selected: focused }}
            accessibilityLabel={label}
            onPress={onPress}
            style={[styles.tab, focused && styles.tabActive]}>
            <Text style={[styles.label, focused && styles.labelActive]} numberOfLines={2}>
              {label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    paddingHorizontal: 6,
    paddingTop: 8,
    gap: 5,
    backgroundColor: colors.background,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  tab: {
    flex: 1,
    minHeight: 52,
    paddingHorizontal: 2,
    borderRadius: radius,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.background,
  },
  tabActive: {
    backgroundColor: colors.highlight,
  },
  label: {
    fontSize: 11,
    textAlign: 'center',
    color: colors.text,
  },
  labelActive: {
    fontWeight: '700',
  },
});
