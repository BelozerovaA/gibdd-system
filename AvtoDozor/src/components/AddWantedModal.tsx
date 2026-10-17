import React, { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { Picker } from '@react-native-picker/picker';
import * as api from '../api';
import { getErrorMessage } from '../api/client';
import { DEFAULT_WANTED_REASON } from '../config';
import { colors, radius } from '../theme';
import { notify } from '../utils/notify';
import AppButton from './AppButton';
import ModalCard from './ModalCard';

interface Props {
  visible: boolean;
  onClose: () => void;
  onAdded: () => void;
}

/** Диалог «Добавление данных» (ТЗ, рисунок 4): выпадающий список ГРЗ, кнопки «Добавить» и «Отмена». */
export default function AddWantedModal({ visible, onClose, onAdded }: Props) {
  const [plates, setPlates] = useState<string[]>([]);
  const [selected, setSelected] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!visible) {
      return;
    }
    let cancelled = false;
    setLoading(true);
    setPlates([]);
    setSelected('');
    api
      .fetchAvailablePlates()
      .then(list => {
        if (!cancelled) {
          setPlates(list);
          setSelected(list[0] ?? '');
        }
      })
      .catch(error => {
        if (!cancelled) {
          notify(getErrorMessage(error), true);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [visible]);

  const add = async () => {
    if (!selected) {
      return;
    }
    setSaving(true);
    try {
      await api.addWanted(selected, DEFAULT_WANTED_REASON);
      notify(`Автомобиль ${selected} добавлен в розыск`);
      onAdded();
      onClose();
    } catch (error) {
      notify(getErrorMessage(error), true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalCard visible={visible} title="Добавление данных" onRequestClose={onClose}>
      <View style={styles.pickerRow}>
        <Text style={styles.label}>ГРЗ</Text>
        <View style={styles.pickerBox}>
          {loading ? (
            <ActivityIndicator style={styles.loader} color={colors.primary} />
          ) : plates.length === 0 ? (
            <Text style={styles.empty}>Нет доступных автомобилей</Text>
          ) : (
            <Picker
              testID="plate-picker"
              selectedValue={selected}
              onValueChange={value => setSelected(String(value))}
              style={styles.picker}
              dropdownIconColor={colors.text}>
              {plates.map(plate => (
                <Picker.Item key={plate} label={plate} value={plate} color={colors.text} />
              ))}
            </Picker>
          )}
        </View>
      </View>

      <View style={styles.actions}>
        <View style={styles.button}>
          <AppButton
            title="Добавить"
            variant="primary"
            loading={saving}
            disabled={loading || !selected}
            onPress={add}
          />
        </View>
        <View style={styles.button}>
          <AppButton title="Отмена" disabled={saving} onPress={onClose} />
        </View>
      </View>
    </ModalCard>
  );
}

const styles = StyleSheet.create({
  pickerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 18,
  },
  label: {
    fontSize: 16,
    marginRight: 12,
    color: colors.text,
  },
  pickerBox: {
    flex: 1,
    minHeight: 48,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radius,
    justifyContent: 'center',
  },
  picker: {
    color: colors.text,
  },
  loader: {
    alignSelf: 'center',
  },
  empty: {
    textAlign: 'center',
    color: colors.muted,
    paddingHorizontal: 8,
  },
  actions: {
    flexDirection: 'row',
    gap: 12,
  },
  button: {
    flex: 1,
  },
});
