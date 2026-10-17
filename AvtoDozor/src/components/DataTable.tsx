import React from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { colors } from '../theme';

export interface Column<T> {
  key: string;
  title: string;
  width: number;
  /** Текст ячейки. */
  value: (row: T) => string;
  /** Цвет текста ячейки (необязательно). */
  color?: (row: T) => string | undefined;
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  keyOf: (row: T) => string | number;
  selectedKey?: string | number | null;
  onRowPress?: (row: T) => void;
  refreshing?: boolean;
  onRefresh?: () => void;
  loading?: boolean;
  emptyText?: string;
}

/**
 * Таблица для узкого экрана: колонки имеют фиксированную ширину, таблица прокручивается
 * по горизонтали, а вниз её можно потянуть для обновления.
 */
export default function DataTable<T>({
  columns,
  rows,
  keyOf,
  selectedKey = null,
  onRowPress,
  refreshing = false,
  onRefresh,
  loading = false,
  emptyText = 'Нет данных',
}: Props<T>) {
  const totalWidth = columns.reduce((sum, c) => sum + c.width, 0);

  return (
    <View style={styles.box}>
      <ScrollView
        testID="table-vertical"
        contentContainerStyle={styles.verticalContent}
        refreshControl={
          onRefresh ? <RefreshControl refreshing={refreshing} onRefresh={onRefresh} /> : undefined
        }>
        <ScrollView horizontal showsHorizontalScrollIndicator nestedScrollEnabled>
          <View style={{ width: totalWidth }}>
            <View style={[styles.row, styles.headerRow]}>
              {columns.map(c => (
                <Text key={c.key} style={[styles.cell, styles.headerCell, { width: c.width }]}>
                  {c.title}
                </Text>
              ))}
            </View>

            {rows.map(row => {
              const key = keyOf(row);
              const selected = selectedKey !== null && key === selectedKey;
              return (
                <Pressable
                  key={key}
                  testID={`row-${key}`}
                  accessibilityRole="button"
                  accessibilityState={{ selected }}
                  disabled={!onRowPress}
                  onPress={() => onRowPress?.(row)}
                  style={[styles.row, selected && styles.selectedRow]}>
                  {columns.map(c => (
                    <Text
                      key={c.key}
                      numberOfLines={2}
                      style={[styles.cell, { width: c.width }, c.color && { color: c.color(row) }]}>
                      {c.value(row)}
                    </Text>
                  ))}
                </Pressable>
              );
            })}
          </View>
        </ScrollView>

        {loading && rows.length === 0 ? (
          <ActivityIndicator style={styles.placeholder} color={colors.primary} />
        ) : null}
        {!loading && rows.length === 0 ? (
          <Text style={[styles.placeholder, styles.emptyText]}>{emptyText}</Text>
        ) : null}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: colors.background,
  },
  verticalContent: {
    flexGrow: 1,
  },
  row: {
    flexDirection: 'row',
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.border,
  },
  headerRow: {
    borderBottomWidth: 1,
    borderBottomColor: colors.borderStrong,
  },
  selectedRow: {
    backgroundColor: colors.highlight,
  },
  cell: {
    paddingHorizontal: 6,
    paddingVertical: 10,
    fontSize: 13,
    color: colors.text,
  },
  headerCell: {
    fontWeight: '700',
  },
  placeholder: {
    marginTop: 24,
  },
  emptyText: {
    textAlign: 'center',
    color: colors.muted,
    fontSize: 14,
  },
});
