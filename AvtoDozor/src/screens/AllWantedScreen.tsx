import React, { useCallback } from 'react';
import * as api from '../api';
import DataTable, { Column } from '../components/DataTable';
import Screen from '../components/Screen';
import { useFocusEffect } from '@react-navigation/native';
import { useLoader } from '../hooks/useLoader';
import type { WantedRow } from '../types';
import { orDash, statusColor } from '../utils/format';

const COLUMNS: Column<WantedRow>[] = [
  { key: 'plate', title: 'ГРЗ', width: 100, value: r => r.plate },
  { key: 'status', title: 'Статус', width: 90, value: r => r.status, color: r => statusColor(r.status) },
  { key: 'color', title: 'Цвет', width: 80, value: r => orDash(r.color) },
  { key: 'employee', title: 'Сотрудник', width: 170, value: r => orDash(r.employee_name) },
  { key: 'time', title: 'Время', width: 80, value: r => orDash(r.fix_time) },
  { key: 'date', title: 'Дата', width: 90, value: r => orDash(r.fix_date) },
  { key: 'address', title: 'Адрес', width: 230, value: r => orDash(r.fix_address) },
];

/** База розыска (ТЗ, рисунок 5): полный список всех разыскиваемых ТС, только просмотр. */
export default function AllWantedScreen() {
  const { data: rows, loading, refreshing, reload } = useLoader<WantedRow[]>(api.fetchAllWanted, []);

  useFocusEffect(
    useCallback(() => {
      reload();
    }, [reload]),
  );

  return (
    <Screen title="База розыска">
      <DataTable
        columns={COLUMNS}
        rows={rows}
        keyOf={r => r.id}
        loading={loading}
        refreshing={refreshing}
        onRefresh={() => reload(true)}
        emptyText="В базе розыска нет автомобилей"
      />
    </Screen>
  );
}
