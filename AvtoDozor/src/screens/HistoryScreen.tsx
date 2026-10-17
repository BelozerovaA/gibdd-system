import React, { useCallback, useEffect, useState } from 'react';
import { Linking, StyleSheet, Text, View } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import { useFocusEffect } from '@react-navigation/native';
import * as api from '../api';
import { getErrorMessage } from '../api/client';
import AppButton from '../components/AppButton';
import DataTable, { Column } from '../components/DataTable';
import ExportModal from '../components/ExportModal';
import Screen from '../components/Screen';
import { useLoader } from '../hooks/useLoader';
import { colors, radius } from '../theme';
import type { AlertRow, ExportFormat, HistoryPeriod } from '../types';
import { alertStatusLabel, PERIODS, statusColor } from '../utils/format';
import { notify } from '../utils/notify';

const COLUMNS: Column<AlertRow>[] = [
  { key: 'plate', title: 'ГРЗ', width: 100, value: r => r.vehicle_plate },
  { key: 'date', title: 'Дата', width: 90, value: r => r.alert_date },
  { key: 'time', title: 'Время', width: 80, value: r => r.alert_time },
  { key: 'address', title: 'Адрес', width: 230, value: r => r.address },
  {
    key: 'status',
    title: 'Статус',
    width: 90,
    value: r => alertStatusLabel(r.reaction_status, r.found_status),
    color: r => statusColor(alertStatusLabel(r.reaction_status, r.found_status)),
  },
];

/** История оповещений (ТЗ, рисунки 9 и 10): выбор периода, «Обновить», «Экспорт». */
export default function HistoryScreen() {
  const [period, setPeriod] = useState<HistoryPeriod>('today');
  const [exportVisible, setExportVisible] = useState(false);
  const [exporting, setExporting] = useState(false);

  const { data: rows, loading, refreshing, reload } = useLoader<AlertRow[]>(
    () => api.fetchHistory(period),
    [],
  );

  // при открытии вкладки
  useFocusEffect(
    useCallback(() => {
      reload();
    }, [reload]),
  );

  // при смене периода
  useEffect(() => {
    reload();
  }, [period, reload]);

  const doExport = async (format: ExportFormat) => {
    setExporting(true);
    try {
      const url = await api.buildExportUrl(format, period);
      await Linking.openURL(url);
      notify('Отчёт откроется в браузере для скачивания', true);
      setExportVisible(false);
    } catch (error) {
      notify(getErrorMessage(error), true);
    } finally {
      setExporting(false);
    }
  };

  return (
    <Screen title="История оповещений">
      <View style={styles.toolbar}>
        <Text style={styles.label}>Период:</Text>
        <View style={styles.pickerBox}>
          <Picker
            testID="period-picker"
            selectedValue={period}
            onValueChange={value => setPeriod(value as HistoryPeriod)}
            style={styles.picker}
            dropdownIconColor={colors.text}>
            {PERIODS.map(p => (
              <Picker.Item key={p.value} label={p.label} value={p.value} color={colors.text} />
            ))}
          </Picker>
        </View>
      </View>
      <View style={styles.buttons}>
        <View style={styles.button}>
          <AppButton title="Обновить" small onPress={() => reload(true)} />
        </View>
        <View style={styles.button}>
          <AppButton title="Экспорт" small onPress={() => setExportVisible(true)} />
        </View>
      </View>

      <DataTable
        columns={COLUMNS}
        rows={rows}
        keyOf={r => r.id}
        loading={loading}
        refreshing={refreshing}
        onRefresh={() => reload(true)}
        emptyText="За выбранный период оповещений нет"
      />

      <ExportModal
        visible={exportVisible}
        busy={exporting}
        onSelect={doExport}
        onClose={() => setExportVisible(false)}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  toolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
  },
  label: {
    fontSize: 15,
    color: colors.text,
    marginRight: 10,
  },
  pickerBox: {
    flex: 1,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radius,
    justifyContent: 'center',
  },
  picker: {
    color: colors.text,
  },
  buttons: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 10,
  },
  button: {
    flex: 1,
  },
});
