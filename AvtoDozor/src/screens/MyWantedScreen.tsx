import React, { useCallback, useMemo, useState } from 'react';
import { Alert, StyleSheet, View } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import * as api from '../api';
import { getErrorMessage } from '../api/client';
import AddWantedModal from '../components/AddWantedModal';
import AppButton from '../components/AppButton';
import DataTable, { Column } from '../components/DataTable';
import Screen from '../components/Screen';
import { useLoader } from '../hooks/useLoader';
import type { WantedRow } from '../types';
import { orDash, statusColor } from '../utils/format';
import { notify } from '../utils/notify';

const COLUMNS: Column<WantedRow>[] = [
  { key: 'plate', title: 'ГРЗ', width: 100, value: r => r.plate },
  { key: 'status', title: 'Статус', width: 90, value: r => r.status, color: r => statusColor(r.status) },
  { key: 'model', title: 'Модель', width: 120, value: r => orDash(r.model) },
  { key: 'color', title: 'Цвет', width: 80, value: r => orDash(r.color) },
  { key: 'time', title: 'Время', width: 80, value: r => orDash(r.fix_time) },
  { key: 'date', title: 'Дата', width: 90, value: r => orDash(r.fix_date) },
  { key: 'address', title: 'Адрес', width: 230, value: r => orDash(r.fix_address) },
];

/** Мой розыск (ТЗ, рисунки 3 и 4): персональный список, добавление и удаление записей. */
export default function MyWantedScreen() {
  const { data: rows, loading, refreshing, reload } = useLoader<WantedRow[]>(api.fetchMyWanted, []);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [addVisible, setAddVisible] = useState(false);

  useFocusEffect(
    useCallback(() => {
      reload();
    }, [reload]),
  );

  const selected = useMemo(() => rows.find(r => r.id === selectedId) ?? null, [rows, selectedId]);

  const remove = () => {
    if (!selected) {
      notify('Сначала выберите строку в таблице');
      return;
    }
    Alert.alert('Удаление из розыска', `Удалить автомобиль ${selected.plate} из вашего списка розыска?`, [
      { text: 'Отмена', style: 'cancel' },
      {
        text: 'Да',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.deleteWanted(selected.plate);
            notify(`Автомобиль ${selected.plate} удалён из розыска`);
            setSelectedId(null);
            reload();
          } catch (error) {
            notify(getErrorMessage(error), true);
          }
        },
      },
    ]);
  };

  return (
    <Screen title="Мой розыск">
      <View style={styles.buttons}>
        <View style={styles.button}>
          <AppButton title="Добавить в розыск" small onPress={() => setAddVisible(true)} />
        </View>
        <View style={styles.button}>
          <AppButton title="Удалить из розыска" small onPress={remove} />
        </View>
      </View>

      <DataTable
        columns={COLUMNS}
        rows={rows}
        keyOf={r => r.id}
        selectedKey={selectedId}
        onRowPress={r => setSelectedId(prev => (prev === r.id ? null : r.id))}
        loading={loading}
        refreshing={refreshing}
        onRefresh={() => reload(true)}
        emptyText="В вашем списке розыска пока нет автомобилей"
      />

      <AddWantedModal
        visible={addVisible}
        onClose={() => setAddVisible(false)}
        onAdded={() => reload()}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  buttons: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 10,
  },
  button: {
    flex: 1,
  },
});
